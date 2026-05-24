"""
extrato_banco_model.py — Lançamentos bancários importados de extratos.

Cada linha vem de um parser (CSV, OFX, PDF). A importação:
  1. Aplica regras de categorização automática (regras_categoria_model).
  2. Insere no banco com dedup por (conta_banco_id, identificador_unico).
  3. Retorna estatísticas (novos, duplicados, total).

Conciliação:
  - marcar_conciliado(id) — usuário revisou e confirma que está OK.
  - vincular_conta_pagar(id, conta_pagar_id) — bate com uma conta_pagar
    existente (evita contar duas vezes no fluxo).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from database import conectar

log = logging.getLogger(__name__)


@dataclass
class LancamentoBanco:
    id:                  int
    conta_banco_id:      int
    data:                str           # YYYY-MM-DD
    descricao:           str
    valor:               float         # +entrada, -saida
    identificador_unico: str
    plano_conta_id:      Optional[int]
    fonte_receita_id:    Optional[int]
    conciliado:          bool
    conta_pagar_id:      Optional[int]
    observacao:          str
    importado_em:        str
    nome_categoria:      str           # resolvido via JOIN
    nome_conta_banco:    str           # resolvido via JOIN


@dataclass
class ResultadoImportacao:
    novos:       int
    duplicados:  int
    com_regra:   int           # quantos foram categorizados por regra automática
    total:       int           # novos + duplicados


def _aplicar_regras(itens: list[dict]) -> list[dict]:
    """Tenta categorizar cada item usando regras_categoria.

    Retorna a lista enriquecida com plano_conta_id ou fonte_receita_id quando
    casa alguma regra. Itens sem match ficam sem categoria (usuário
    categoriza depois).
    """
    from views.fluxo_caixa.regras_categoria_model import casar_regras
    return casar_regras(itens)


def importar(conta_banco_id: int, itens: list[dict]) -> ResultadoImportacao:
    """Importa lançamentos para uma conta bancária com dedup automático.

    `itens` é a lista de dicts retornada por um parser (data, descricao,
    valor, identificador_unico). Aplica regras de categorização e insere
    no banco, ignorando duplicados via UNIQUE constraint.
    """
    if not itens:
        return ResultadoImportacao(novos=0, duplicados=0, com_regra=0, total=0)

    itens = _aplicar_regras(itens)
    com_regra = sum(
        1 for i in itens
        if i.get("plano_conta_id") or i.get("fonte_receita_id")
    )

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    novos = 0
    duplicados = 0

    with conectar() as conn:
        for item in itens:
            try:
                conn.execute(
                    """
                    INSERT INTO lancamentos_banco
                        (conta_banco_id, data, descricao, valor,
                         identificador_unico, plano_conta_id, fonte_receita_id,
                         conciliado, importado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        conta_banco_id,
                        item["data"],
                        item["descricao"],
                        float(item["valor"]),
                        item.get("identificador_unico", ""),
                        item.get("plano_conta_id"),
                        item.get("fonte_receita_id"),
                        agora,
                    ),
                )
                novos += 1
            except Exception as e:
                # IntegrityError de UNIQUE → duplicado, ignora
                msg = str(e).lower()
                if "unique" in msg or "constraint" in msg:
                    duplicados += 1
                else:
                    raise
        conn.commit()

    log.info(
        "importar: conta=%s novos=%d duplicados=%d com_regra=%d",
        conta_banco_id, novos, duplicados, com_regra,
    )
    return ResultadoImportacao(
        novos=novos, duplicados=duplicados, com_regra=com_regra,
        total=novos + duplicados,
    )


def _carregar(rows) -> list[LancamentoBanco]:
    return [
        LancamentoBanco(
            id=r["id"],
            conta_banco_id=r["conta_banco_id"],
            data=r["data"],
            descricao=r["descricao"],
            valor=r["valor"],
            identificador_unico=r["identificador_unico"] or "",
            plano_conta_id=r["plano_conta_id"],
            fonte_receita_id=r["fonte_receita_id"],
            conciliado=bool(r["conciliado"]),
            conta_pagar_id=r["conta_pagar_id"],
            observacao=r["observacao"] or "",
            importado_em=r["importado_em"],
            nome_categoria=r["nome_categoria"] or "",
            nome_conta_banco=r["nome_conta_banco"] or "",
        )
        for r in rows
    ]


_BASE_SELECT = """
    SELECT lb.*,
           COALESCE(pc.nome, fr.nome, '') AS nome_categoria,
           cb.nome AS nome_conta_banco
      FROM lancamentos_banco lb
      LEFT JOIN plano_contas    pc ON pc.id = lb.plano_conta_id
      LEFT JOIN fontes_receita  fr ON fr.id = lb.fonte_receita_id
      LEFT JOIN contas_banco    cb ON cb.id = lb.conta_banco_id
"""


def listar_lancamentos_mes(
    mes: int,
    ano: int,
    conta_banco_id: int | None = None,
) -> list[LancamentoBanco]:
    """Lista lançamentos do mês, opcionalmente filtrando por conta."""
    inicio = f"{ano:04d}-{mes:02d}-01"
    fim    = f"{ano + 1:04d}-01-01" if mes == 12 else f"{ano:04d}-{mes + 1:02d}-01"

    where = "WHERE lb.data >= ? AND lb.data < ?"
    params: list = [inicio, fim]
    if conta_banco_id is not None:
        where += " AND lb.conta_banco_id = ?"
        params.append(conta_banco_id)

    with conectar() as conn:
        rows = conn.execute(
            f"{_BASE_SELECT} {where} ORDER BY lb.data DESC, lb.id",
            tuple(params),
        ).fetchall()
    return _carregar(rows)


def listar_nao_conciliados(conta_banco_id: int) -> list[LancamentoBanco]:
    """Lista lançamentos da conta que ainda não foram conciliados."""
    with conectar() as conn:
        rows = conn.execute(
            f"{_BASE_SELECT} WHERE lb.conta_banco_id = ? AND lb.conciliado = 0"
            f"  ORDER BY lb.data, lb.id",
            (conta_banco_id,),
        ).fetchall()
    return _carregar(rows)


def obter_lancamento(id_: int) -> Optional[LancamentoBanco]:
    with conectar() as conn:
        row = conn.execute(
            f"{_BASE_SELECT} WHERE lb.id = ?", (id_,)
        ).fetchone()
    if not row:
        return None
    return _carregar([row])[0]


def categorizar(
    id_: int,
    plano_conta_id: int | None = None,
    fonte_receita_id: int | None = None,
) -> None:
    """Define a categoria de um lançamento.

    Use plano_conta_id se for saída (valor negativo), fonte_receita_id se
    entrada. Ambos None desfaz a categorização.
    """
    with conectar() as conn:
        conn.execute(
            """
            UPDATE lancamentos_banco
               SET plano_conta_id   = ?,
                   fonte_receita_id = ?
             WHERE id = ?
            """,
            (plano_conta_id, fonte_receita_id, id_),
        )


def marcar_conciliado(id_: int, conciliado: bool = True) -> None:
    """Marca o lançamento como revisado pelo usuário."""
    with conectar() as conn:
        conn.execute(
            "UPDATE lancamentos_banco SET conciliado = ? WHERE id = ?",
            (1 if conciliado else 0, id_),
        )


def vincular_conta_pagar(id_: int, conta_pagar_id: int | None) -> None:
    """Vincula este lançamento bancário a uma conta_pagar existente.

    Quando vinculado + conciliado=1, indica que esta saída do banco JÁ ESTÁ
    representada por aquela conta_pagar no fluxo de caixa — evita duplicar
    no relatório consolidado.
    """
    with conectar() as conn:
        conn.execute(
            "UPDATE lancamentos_banco SET conta_pagar_id = ? WHERE id = ?",
            (conta_pagar_id, id_),
        )


def excluir_lancamento(id_: int) -> None:
    """Remove um lançamento bancário (silencioso se não existe)."""
    with conectar() as conn:
        conn.execute("DELETE FROM lancamentos_banco WHERE id = ?", (id_,))


def excluir_lancamentos_conta(conta_banco_id: int) -> int:
    """Apaga TODOS os lançamentos importados de uma conta. Retorna o count."""
    with conectar() as conn:
        cur = conn.execute(
            "DELETE FROM lancamentos_banco WHERE conta_banco_id = ?",
            (conta_banco_id,),
        )
        return cur.rowcount


@dataclass
class ContaPagarCandidata:
    """Sugestão de conta_pagar pra vincular com um lançamento bancário."""
    id:              int
    data_vencimento: str
    descricao:       str
    valor:           float
    status:          str
    nome_categoria:  str


def candidatas_para_vincular(
    data: str,
    valor: float,
    dias_tolerancia: int = 5,
    valor_tolerancia: float = 0.01,
) -> list[ContaPagarCandidata]:
    """Retorna contas_pagar que poderiam ser conciliadas com este lançamento.

    Filtra por:
    - data_vencimento entre (data - dias) e (data + dias)
    - |valor da conta - valor absoluto do lançamento| <= valor_tolerancia
    - status != 'cancelado'

    Ordena por proximidade da data, depois pelo valor mais próximo.
    """
    from datetime import datetime, timedelta
    try:
        d = datetime.strptime(data, "%Y-%m-%d").date()
    except ValueError:
        return []

    d_min = (d - timedelta(days=dias_tolerancia)).isoformat()
    d_max = (d + timedelta(days=dias_tolerancia)).isoformat()
    alvo  = abs(valor)

    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT cp.id, cp.data_vencimento, cp.descricao, cp.valor, cp.status,
                   COALESCE(pc.nome, '') AS nome_categoria
              FROM contas_pagar cp
              LEFT JOIN plano_contas pc ON pc.id = cp.plano_conta_id
             WHERE cp.data_vencimento BETWEEN ? AND ?
               AND cp.status != 'cancelado'
               AND ABS(cp.valor - ?) <= ?
             ORDER BY ABS(julianday(cp.data_vencimento) - julianday(?)),
                      ABS(cp.valor - ?)
             LIMIT 20
            """,
            (d_min, d_max, alvo, valor_tolerancia, data, alvo),
        ).fetchall()

    return [
        ContaPagarCandidata(
            id=r["id"],
            data_vencimento=r["data_vencimento"],
            descricao=r["descricao"] or "",
            valor=r["valor"],
            status=r["status"],
            nome_categoria=r["nome_categoria"],
        )
        for r in rows
    ]


def reaplicar_regras(
    conta_banco_id: int | None = None,
    apenas_sem_categoria: bool = True,
) -> int:
    """Re-aplica as regras de categorização ativas aos lançamentos já importados.

    Quando o usuário cadastra uma regra NOVA depois de importar extratos,
    os lançamentos antigos ficam sem categoria. Essa função roda
    casar_regras() em todos eles e persiste as categorias encontradas.

    - `conta_banco_id`: limita a uma conta específica (None = todas).
    - `apenas_sem_categoria`: se True, ignora lançamentos que JÁ têm
      categoria (padrão, pra não sobrescrever escolhas manuais do user).
      Se False, re-aplica em TODOS — útil quando o user atualiza uma
      regra existente e quer que reflita no histórico.

    Retorna a quantidade de lançamentos que ganharam categoria nova.
    """
    from views.fluxo_caixa.regras_categoria_model import casar_regras

    where = []
    params: list = []
    if conta_banco_id is not None:
        where.append("conta_banco_id = ?")
        params.append(conta_banco_id)
    if apenas_sem_categoria:
        where.append("plano_conta_id IS NULL AND fonte_receita_id IS NULL")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with conectar() as conn:
        rows = conn.execute(
            f"SELECT id, data, descricao, valor FROM lancamentos_banco {where_sql}",
            tuple(params),
        ).fetchall()

        # Converte pra dicts no formato esperado por casar_regras
        itens = [
            {"id": r["id"], "data": r["data"], "descricao": r["descricao"],
             "valor": r["valor"], "identificador_unico": ""}
            for r in rows
        ]
        resultado = casar_regras(itens)

        n_atualizados = 0
        for item in resultado:
            if item.get("plano_conta_id"):
                conn.execute(
                    "UPDATE lancamentos_banco SET plano_conta_id = ? WHERE id = ?",
                    (item["plano_conta_id"], item["id"]),
                )
                n_atualizados += 1
            elif item.get("fonte_receita_id"):
                conn.execute(
                    "UPDATE lancamentos_banco SET fonte_receita_id = ? WHERE id = ?",
                    (item["fonte_receita_id"], item["id"]),
                )
                n_atualizados += 1
        conn.commit()

    log.info("reaplicar_regras: %d lançamentos atualizados (conta=%s)",
             n_atualizados, conta_banco_id)
    return n_atualizados


def resumo_conta(conta_banco_id: int) -> dict:
    """Estatísticas da conta: total entradas/saídas, % conciliado etc."""
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*)                                                AS total,
                SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END)          AS entradas,
                SUM(CASE WHEN valor < 0 THEN -valor ELSE 0 END)         AS saidas,
                SUM(CASE WHEN conciliado = 1 THEN 1 ELSE 0 END)         AS conciliados,
                SUM(CASE WHEN plano_conta_id IS NULL
                          AND fonte_receita_id IS NULL
                         THEN 1 ELSE 0 END)                             AS sem_categoria
              FROM lancamentos_banco
             WHERE conta_banco_id = ?
            """,
            (conta_banco_id,),
        ).fetchone()
    return {
        "total":         row["total"] or 0,
        "entradas":      round(row["entradas"] or 0.0, 2),
        "saidas":        round(row["saidas"] or 0.0, 2),
        "saldo_mov":     round((row["entradas"] or 0.0) - (row["saidas"] or 0.0), 2),
        "conciliados":   row["conciliados"] or 0,
        "sem_categoria": row["sem_categoria"] or 0,
    }
