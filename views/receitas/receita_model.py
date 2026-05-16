"""
receita_model.py — Lógica de negócio para Fontes de Receita e Receitas Especiais.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from database import conectar


# ---------------------------------------------------------------------------
# Fontes de Receita
# ---------------------------------------------------------------------------

@dataclass
class FonteReceita:
    id:               int
    nome:             str
    tipo:             str
    valor_mensal:     float
    ativa:            bool
    observacao:       str
    criado_em:        str
    # campos extras por tipo
    dia_pagamento:    Optional[int]  = None
    fgts_aniversario: bool           = False
    fgts_mes:         Optional[int]  = None
    fgts_valor:       Optional[float]= None
    periodicidade:    str            = "mensal"
    origem:           str            = ""
    padrao:           int            = 0


def _row_to_fonte(r) -> FonteReceita:
    d = dict(r)
    return FonteReceita(
        id               = d["id"],
        nome             = d["nome"],
        tipo             = d["tipo"],
        valor_mensal     = d["valor_mensal"],
        ativa            = bool(d["ativa"]),
        observacao       = d.get("observacao") or "",
        criado_em        = d.get("criado_em") or "",
        dia_pagamento    = d.get("dia_pagamento"),
        fgts_aniversario = bool(d.get("fgts_aniversario", 0)),
        fgts_mes         = d.get("fgts_mes"),
        fgts_valor       = d.get("fgts_valor"),
        periodicidade    = d.get("periodicidade") or "mensal",
        origem           = d.get("origem") or "",
        padrao           = int(d.get("padrao") or 0),
    )


def listar_fontes(apenas_ativas: bool = False) -> list[FonteReceita]:
    sql = "SELECT * FROM fontes_receita"
    if apenas_ativas:
        sql += " WHERE ativa = 1"
    sql += " ORDER BY nome"
    with conectar() as conn:
        rows = conn.execute(sql).fetchall()
    return [_row_to_fonte(r) for r in rows]


def salvar_fonte(dados: dict, id: Optional[int] = None) -> int:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        if id is not None:
            conn.execute("""
                UPDATE fontes_receita
                SET nome=?, tipo=?, valor_mensal=?, observacao=?,
                    dia_pagamento=?, fgts_aniversario=?, fgts_mes=?,
                    fgts_valor=?, periodicidade=?, origem=?
                WHERE id=?
            """, (
                dados["nome"], dados["tipo"], dados["valor_mensal"],
                dados.get("observacao", ""),
                dados.get("dia_pagamento"),
                int(dados.get("fgts_aniversario", False)),
                dados.get("fgts_mes"),
                dados.get("fgts_valor"),
                dados.get("periodicidade", "mensal"),
                dados.get("origem", ""),
                id,
            ))
            return id
        else:
            cur = conn.execute("""
                INSERT INTO fontes_receita
                (nome, tipo, valor_mensal, ativa, observacao,
                 dia_pagamento, fgts_aniversario, fgts_mes,
                 fgts_valor, periodicidade, origem, criado_em)
                VALUES (?,?,?,1,?,?,?,?,?,?,?,?)
            """, (
                dados["nome"], dados["tipo"], dados["valor_mensal"],
                dados.get("observacao", ""),
                dados.get("dia_pagamento"),
                int(dados.get("fgts_aniversario", False)),
                dados.get("fgts_mes"),
                dados.get("fgts_valor"),
                dados.get("periodicidade", "mensal"),
                dados.get("origem", ""),
                agora,
            ))
            return cur.lastrowid


def alternar_ativa_fonte(id: int, ativa: bool):
    with conectar() as conn:
        conn.execute("UPDATE fontes_receita SET ativa=? WHERE id=?",
                     (int(ativa), id))


def excluir_fonte(id: int):
    """Soft delete — desativa a fonte."""
    alternar_ativa_fonte(id, False)


# ---------------------------------------------------------------------------
# Receitas Especiais
# ---------------------------------------------------------------------------

@dataclass
class ReceitaEspecial:
    id:               int
    nome:             str
    mes:              int   # 0=jan ... 11=dez
    valor:            float
    tipo:             str
    recorrente_anual: bool
    observacao:       str


def listar_receitas_especiais(mes: Optional[int] = None) -> list[ReceitaEspecial]:
    """Lista receitas especiais. Se mes informado, filtra pelo mês (0–11)."""
    sql = "SELECT * FROM receitas_especiais"
    params = []
    if mes is not None:
        sql += " WHERE mes = ?"
        params.append(mes)
    sql += " ORDER BY mes, nome"
    with conectar() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        ReceitaEspecial(
            id               = r["id"],
            nome             = r["nome"],
            mes              = r["mes"],
            valor            = r["valor"],
            tipo             = r["tipo"],
            recorrente_anual = bool(r["recorrente_anual"]),
            observacao       = dict(r).get("observacao") or "",
        )
        for r in rows
    ]


def salvar_receita_especial(dados: dict, id: Optional[int] = None) -> int:
    with conectar() as conn:
        if id is not None:
            conn.execute("""
                UPDATE receitas_especiais
                SET nome=?, mes=?, valor=?, tipo=?, recorrente_anual=?, observacao=?
                WHERE id=?
            """, (
                dados["nome"], dados["mes"], dados["valor"],
                dados.get("tipo", "outro"),
                int(dados.get("recorrente_anual", True)),
                dados.get("observacao", ""),
                id,
            ))
            return id
        else:
            cur = conn.execute("""
                INSERT INTO receitas_especiais
                (nome, mes, valor, tipo, recorrente_anual, observacao)
                VALUES (?,?,?,?,?,?)
            """, (
                dados["nome"], dados["mes"], dados["valor"],
                dados.get("tipo", "outro"),
                int(dados.get("recorrente_anual", True)),
                dados.get("observacao", ""),
            ))
            return cur.lastrowid


def excluir_receita_especial(id: int):
    with conectar() as conn:
        conn.execute("DELETE FROM receitas_especiais WHERE id=?", (id,))


def _gerar_especiais_clt(fonte_id: int, nome_fonte: str,
                          salario: float, fgts: bool,
                          fgts_mes: Optional[int], fgts_valor: Optional[float]):
    """
    Ao cadastrar fonte CLT gera automaticamente:
    - 13º Salário em dezembro (mês 11)
    - Férias + 1/3 em junho (mês 5)
    - FGTS aniversário se marcado
    Não duplica se já existir receita especial com o mesmo nome.
    """
    with conectar() as conn:
        existentes = {
            r["nome"]
            for r in conn.execute("SELECT nome FROM receitas_especiais").fetchall()
        }

    to_create = []
    nome_13 = f"13º Salário — {nome_fonte}"
    nome_ferias = f"Férias + 1/3 — {nome_fonte}"

    if nome_13 not in existentes:
        to_create.append({
            "nome": nome_13, "mes": 11,
            "valor": salario, "tipo": "clt", "recorrente_anual": True,
        })
    if nome_ferias not in existentes:
        to_create.append({
            "nome": nome_ferias, "mes": 5,
            "valor": round(salario * 4 / 3, 2),  # salário + 1/3
            "tipo": "clt", "recorrente_anual": True,
        })
    if fgts and fgts_mes is not None and fgts_valor:
        nome_fgts = f"FGTS Aniversário — {nome_fonte}"
        if nome_fgts not in existentes:
            to_create.append({
                "nome": nome_fgts, "mes": fgts_mes,
                "valor": fgts_valor, "tipo": "outro", "recorrente_anual": True,
            })

    for d in to_create:
        salvar_receita_especial(d)


# ---------------------------------------------------------------------------
# Cálculos para Visão Mensal
# ---------------------------------------------------------------------------

def receita_mensal_base() -> float:
    """Soma das fontes ativas com periodicidade mensal."""
    fontes = listar_fontes(apenas_ativas=True)
    total = 0.0
    for f in fontes:
        if f.periodicidade == "mensal":
            total += f.valor_mensal
        elif f.periodicidade == "bimestral":
            total += f.valor_mensal / 2
        elif f.periodicidade == "anual":
            total += f.valor_mensal / 12
    return total


def total_previsto_mes(mes_0: int, ano: int) -> dict:
    """
    Retorna dicionário com receitas do mês (mes_0 = 0-11).
    Inclui fontes recorrentes + especiais do mês.
    """
    fontes = listar_fontes(apenas_ativas=True)
    especiais = listar_receitas_especiais(mes=mes_0)

    linhas_fontes = []
    total_fontes = 0.0
    for f in fontes:
        val = f.valor_mensal
        if f.periodicidade == "bimestral":
            val /= 2
        elif f.periodicidade == "anual":
            val /= 12
        linhas_fontes.append({"fonte": f, "valor_mes": val})
        total_fontes += val

    total_especiais = sum(e.valor for e in especiais)

    return {
        "fontes":          linhas_fontes,
        "especiais":       especiais,
        "total_fontes":    total_fontes,
        "total_especiais": total_especiais,
        "total":           total_fontes + total_especiais,
    }
