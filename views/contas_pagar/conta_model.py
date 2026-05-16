"""
conta_model.py — Lógica de negócio para Plano de Contas e Contas a Pagar.
Toda interação com o banco passa por aqui.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
import sqlite3

from database import conectar


# ---------------------------------------------------------------------------
# Plano de Contas
# ---------------------------------------------------------------------------

@dataclass
class PlanoContaItem:
    id:         int
    nome:       str
    tipo_custo: str
    categoria:  str
    ativa:      bool
    criado_em:  str
    padrao:     int = 0


def listar_plano_contas(apenas_ativas: bool = False) -> list[PlanoContaItem]:
    sql = "SELECT * FROM plano_contas"
    if apenas_ativas:
        sql += " WHERE ativa = 1"
    sql += " ORDER BY nome"
    with conectar() as conn:
        rows = conn.execute(sql).fetchall()
    return [PlanoContaItem(**dict(r)) for r in rows]


def salvar_plano_conta(nome: str, tipo_custo: str, categoria: str,
                       id: Optional[int] = None) -> int:
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        if id is not None:
            conn.execute(
                "UPDATE plano_contas SET nome=?, tipo_custo=?, categoria=? WHERE id=?",
                (nome, tipo_custo, categoria, id)
            )
            return id
        else:
            cur = conn.execute(
                "INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, criado_em) VALUES (?,?,?,1,?)",
                (nome, tipo_custo, categoria, agora)
            )
            return cur.lastrowid


def alternar_ativa_plano(id: int, ativa: bool):
    with conectar() as conn:
        conn.execute("UPDATE plano_contas SET ativa=? WHERE id=?", (int(ativa), id))


def tem_lancamentos_plano(id: int) -> bool:
    with conectar() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM contas_pagar WHERE plano_conta_id=?", (id,)
        ).fetchone()[0]
    return n > 0


def excluir_plano_conta(id: int) -> tuple[bool, str]:
    """
    Exclui permanentemente uma conta sem lançamentos.
    Retorna (True, "") em caso de sucesso ou (False, motivo) se bloqueado.
    """
    with conectar() as conn:
        if not conn.execute("SELECT 1 FROM plano_contas WHERE id=?", (id,)).fetchone():
            return False, "Conta não encontrada."
        vinculadas = conn.execute(
            "SELECT COUNT(*) FROM contas_pagar WHERE plano_conta_id=?", (id,)
        ).fetchone()[0]
        if vinculadas:
            return False, "Esta conta possui lançamentos. Inative-a em vez de excluir."
        conn.execute("DELETE FROM plano_contas WHERE id=?", (id,))
    return True, ""


# ---------------------------------------------------------------------------
# Contas a Pagar
# ---------------------------------------------------------------------------

@dataclass
class ContaPagar:
    id:              int
    plano_conta_id:  Optional[int]
    descricao:       str
    valor:           float
    data_vencimento: str
    data_pagamento:  Optional[str]
    status:          str
    recorrente:      bool
    observacao:      str
    criado_em:       str
    # campos joined (não persistidos)
    plano_nome:      str = ""
    plano_tipo:      str = ""


def listar_contas(mes: int, ano: int,
                  status: Optional[str] = None,
                  tipo_custo: Optional[str] = None) -> list[ContaPagar]:
    inicio = f"{ano:04d}-{mes:02d}-01"
    # último dia do mês
    if mes == 12:
        fim = f"{ano+1:04d}-01-01"
    else:
        fim = f"{ano:04d}-{mes+1:02d}-01"

    params: list = [inicio, fim]
    sql = """
        SELECT cp.*,
               COALESCE(pc.nome, '')       AS plano_nome,
               COALESCE(pc.tipo_custo, '') AS plano_tipo
        FROM   contas_pagar cp
        LEFT JOIN plano_contas pc ON pc.id = cp.plano_conta_id
        WHERE  cp.data_vencimento >= ? AND cp.data_vencimento < ?
    """
    if status:
        sql += " AND cp.status = ?"
        params.append(status)
    if tipo_custo:
        sql += " AND pc.tipo_custo = ?"
        params.append(tipo_custo)

    sql += " ORDER BY cp.data_vencimento, cp.id"

    with conectar() as conn:
        rows = conn.execute(sql, params).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        pn = d.pop("plano_nome")
        pt = d.pop("plano_tipo")
        obj = ContaPagar(**d)
        obj.plano_nome = pn
        obj.plano_tipo = pt
        result.append(obj)
    return result


def salvar_conta(dados: dict, meses: int = 1) -> list[int]:
    """
    Salva uma conta a pagar. Se recorrente e meses > 1,
    insere uma entrada por mês. Retorna lista de IDs inseridos.
    """
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ids = []
    venc_base = date.fromisoformat(dados["data_vencimento"])

    with conectar() as conn:
        for i in range(meses):
            # avança N meses
            mes = venc_base.month + i
            ano = venc_base.year + (mes - 1) // 12
            mes = ((mes - 1) % 12) + 1
            try:
                venc = venc_base.replace(year=ano, month=mes)
            except ValueError:
                # dia inexistente no mês (ex: 31 em fev) → usa último dia
                import calendar
                ultimo = calendar.monthrange(ano, mes)[1]
                venc = venc_base.replace(year=ano, month=mes, day=ultimo)

            cur = conn.execute(
                """INSERT INTO contas_pagar
                   (plano_conta_id, descricao, valor, data_vencimento,
                    data_pagamento, status, recorrente, observacao, criado_em)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    dados.get("plano_conta_id"),
                    dados.get("descricao", ""),
                    dados["valor"],
                    venc.isoformat(),
                    dados.get("data_pagamento") or None,
                    dados.get("status", "pendente"),
                    int(dados.get("recorrente", False)),
                    dados.get("observacao", ""),
                    agora,
                ),
            )
            ids.append(cur.lastrowid)

    return ids


def atualizar_conta(id: int, dados: dict):
    with conectar() as conn:
        conn.execute(
            """UPDATE contas_pagar
               SET plano_conta_id=?, descricao=?, valor=?,
                   data_vencimento=?, data_pagamento=?,
                   status=?, recorrente=?, observacao=?
               WHERE id=?""",
            (
                dados.get("plano_conta_id"),
                dados.get("descricao", ""),
                dados["valor"],
                dados["data_vencimento"],
                dados.get("data_pagamento") or None,
                dados.get("status", "pendente"),
                int(dados.get("recorrente", False)),
                dados.get("observacao", ""),
                id,
            ),
        )


def atualizar_recorrentes_futuros(conta_id: int, dados: dict) -> int:
    """
    Atualiza o registro conta_id + todos os registros pendentes futuros
    com o mesmo plano_conta_id e recorrente=1.
    Altera apenas valor, descricao e observacao (preserva datas e status).
    Retorna o número de registros atualizados.
    """
    with conectar() as conn:
        row = conn.execute(
            "SELECT plano_conta_id, data_vencimento FROM contas_pagar WHERE id=?",
            (conta_id,),
        ).fetchone()
        if not row:
            return 0
        pid  = row["plano_conta_id"]
        desc = dados.get("descricao", "")
        val  = dados["valor"]
        obs  = dados.get("observacao", "")
        venc = row["data_vencimento"]
        if pid is None:
            cur = conn.execute(
                """UPDATE contas_pagar
                   SET descricao=?, valor=?, observacao=?
                   WHERE plano_conta_id IS NULL AND recorrente=1
                     AND status='pendente' AND data_vencimento >= ?""",
                (desc, val, obs, venc),
            )
        else:
            cur = conn.execute(
                """UPDATE contas_pagar
                   SET descricao=?, valor=?, observacao=?
                   WHERE plano_conta_id=? AND recorrente=1
                     AND status='pendente' AND data_vencimento >= ?""",
                (desc, val, obs, pid, venc),
            )
        return cur.rowcount


def marcar_pago(id: int):
    hoje = date.today().isoformat()
    with conectar() as conn:
        conn.execute(
            "UPDATE contas_pagar SET status='pago', data_pagamento=? WHERE id=?",
            (hoje, id)
        )


def excluir_conta(id: int):
    with conectar() as conn:
        conn.execute("DELETE FROM contas_pagar WHERE id=?", (id,))


def buscar_contas_pagar(texto: str,
                        status: Optional[str] = None,
                        mes: Optional[int] = None,
                        ano: Optional[int] = None) -> list[ContaPagar]:
    """
    Busca contas a pagar por texto livre (descrição ou nome do plano).
    Filtros opcionais: status, mes+ano de vencimento.
    """
    params: list = []
    sql = """
        SELECT cp.*,
               COALESCE(pc.nome, '')       AS plano_nome,
               COALESCE(pc.tipo_custo, '') AS plano_tipo
        FROM   contas_pagar cp
        LEFT JOIN plano_contas pc ON pc.id = cp.plano_conta_id
        WHERE  1=1
    """
    if texto:
        sql += " AND (LOWER(cp.descricao) LIKE ? OR LOWER(pc.nome) LIKE ?)"
        like = f"%{texto.lower()}%"
        params += [like, like]
    if status:
        sql += " AND cp.status = ?"
        params.append(status)
    if mes and ano:
        inicio = f"{ano:04d}-{mes:02d}-01"
        fim    = f"{ano:04d}-{mes+1:02d}-01" if mes < 12 else f"{ano+1:04d}-01-01"
        sql += " AND cp.data_vencimento >= ? AND cp.data_vencimento < ?"
        params += [inicio, fim]

    sql += " ORDER BY cp.data_vencimento, cp.id"

    with conectar() as conn:
        rows = conn.execute(sql, params).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        pn = d.pop("plano_nome")
        pt = d.pop("plano_tipo")
        obj = ContaPagar(**d)
        obj.plano_nome = pn
        obj.plano_tipo = pt
        result.append(obj)
    return result


def totais_periodo(mes: int, ano: int) -> dict:
    contas = listar_contas(mes, ano)
    pendente = sum(c.valor for c in contas if c.status == "pendente")
    pago     = sum(c.valor for c in contas if c.status == "pago")
    total    = sum(c.valor for c in contas)
    return {"pendente": pendente, "pago": pago, "total": total}
