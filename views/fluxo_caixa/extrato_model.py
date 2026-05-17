"""
extrato_model.py — Fluxo de Caixa: extrato de transações mês a mês.
Cruza contas_pagar (débitos) + fontes_receita + receitas_especiais (créditos).
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date

from database import conectar
from views.receitas.receita_model import listar_fontes, listar_receitas_especiais


@dataclass
class LinhaExtrato:
    data:      str    # YYYY-MM-DD (para ordenação)
    descricao: str
    categoria: str
    debito:    float
    credito:   float
    saldo:     float  # saldo acumulado até esta linha
    tipo:      str    # "receita" | "despesa"
    status:    str    # "pago" | "pendente" | "cancelado" | ""


def _creditos_mes(mes: int, ano: int) -> list[dict]:
    """Gera linhas de crédito para o mês a partir de fontes_receita e receitas_especiais."""
    linhas = []
    fontes = listar_fontes(apenas_ativas=True)

    for f in fontes:
        dia = f.dia_pagamento or 1
        # Garante que o dia é válido para o mês
        import calendar
        ultimo = calendar.monthrange(ano, mes)[1]
        dia = min(dia, ultimo)
        data_str = f"{ano:04d}-{mes:02d}-{dia:02d}"

        valor = f.valor_mensal
        if f.periodicidade == "bimestral":
            valor = f.valor_mensal / 2
        elif f.periodicidade == "anual":
            valor = f.valor_mensal / 12

        linhas.append({
            "data":      data_str,
            "descricao": f.nome,
            "categoria": "Receita",
            "debito":    0.0,
            "credito":   round(valor, 2),
            "tipo":      "receita",
            "status":    "",
        })

    # Receitas especiais: mes no model é 0-based (0=jan)
    mes_0 = mes - 1
    especiais = listar_receitas_especiais(mes=mes_0)
    for e in especiais:
        linhas.append({
            "data":      f"{ano:04d}-{mes:02d}-01",
            "descricao": e.nome,
            "categoria": "Receita especial",
            "debito":    0.0,
            "credito":   e.valor,
            "tipo":      "receita",
            "status":    "",
        })

    return linhas


def _debitos_mes(mes: int, ano: int) -> list[dict]:
    """Busca contas_pagar do mês como débitos."""
    inicio = f"{ano:04d}-{mes:02d}-01"
    fim = f"{ano:04d}-{mes+1:02d}-01" if mes < 12 else f"{ano+1:04d}-01-01"
    with conectar() as conn:
        rows = conn.execute("""
            SELECT cp.data_vencimento, cp.descricao, cp.valor, cp.status,
                   COALESCE(pc.nome, 'Sem categoria') AS categoria
            FROM   contas_pagar cp
            LEFT JOIN plano_contas pc ON pc.id = cp.plano_conta_id
            WHERE  cp.data_vencimento >= ? AND cp.data_vencimento < ?
              AND  cp.status != 'cancelado'
            ORDER BY cp.data_vencimento, cp.id
        """, (inicio, fim)).fetchall()

    return [
        {
            "data":      r["data_vencimento"],
            "descricao": r["descricao"] or r["categoria"],
            "categoria": r["categoria"],
            "debito":    r["valor"],
            "credito":   0.0,
            "tipo":      "despesa",
            "status":    r["status"],
        }
        for r in rows
    ]


def _creditos_investimento_mes(mes: int, ano: int) -> list[dict]:
    """Retorna entradas de investimento (venda, resgate, rendimentos) do mês."""
    try:
        from views.investimentos.investimento_model import rendimentos_financeiros_mes
        return rendimentos_financeiros_mes(mes, ano)
    except Exception:
        return []


def _creditos_vendas_mes(mes: int, ano: int) -> list[dict]:
    """Retorna entradas do módulo de vendas para o mês.

    Inclui:
    - Vendas à vista com status='paga' cuja data_venda cai no mês.
    - Parcelas de contas_a_receber quitadas (status='recebido') no mês.
    Garante que nenhuma venda a prazo entra antes da quitação efetiva.
    """
    inicio = f"{ano:04d}-{mes:02d}-01"
    fim    = f"{ano:04d}-{mes + 1:02d}-01" if mes < 12 else f"{ano + 1:04d}-01-01"
    linhas: list[dict] = []

    with conectar() as conn:
        avista = conn.execute("""
            SELECT data_venda AS data,
                   COALESCE(NULLIF(descricao,''), 'Venda') AS descricao,
                   valor_liquido AS credito
            FROM vendas
            WHERE tipo_pagamento = 'avista' AND status = 'paga'
              AND data_venda >= ? AND data_venda < ?
            ORDER BY data_venda
        """, (inicio, fim)).fetchall()

        aprazo = conn.execute("""
            SELECT data_recebimento AS data,
                   descricao || '' AS descricao,
                   valor AS credito
            FROM contas_a_receber
            WHERE status = 'recebido'
              AND data_recebimento >= ? AND data_recebimento < ?
            ORDER BY data_recebimento
        """, (inicio, fim)).fetchall()

    for r in [*avista, *aprazo]:
        linhas.append({
            "data":      r["data"],
            "descricao": r["descricao"],
            "categoria": "Vendas",
            "debito":    0.0,
            "credito":   float(r["credito"]),
            "tipo":      "receita",
            "status":    "recebido",
        })
    return linhas


def extrato_mes(mes: int, ano: int) -> list[LinhaExtrato]:
    """
    Retorna as linhas do extrato do mês ordenadas por data.
    Saldo acumulado calculado: créditos primeiro dentro do mesmo dia.
    """
    linhas_raw = (
        _creditos_mes(mes, ano)
        + _creditos_investimento_mes(mes, ano)
        + _creditos_vendas_mes(mes, ano)
        + _debitos_mes(mes, ano)
    )

    # Ordena: por data, créditos antes de débitos no mesmo dia
    linhas_raw.sort(key=lambda r: (r["data"], 0 if r["tipo"] == "receita" else 1))

    saldo = 0.0
    resultado = []
    for r in linhas_raw:
        saldo += r["credito"] - r["debito"]
        resultado.append(LinhaExtrato(
            data      = r["data"],
            descricao = r["descricao"],
            categoria = r["categoria"],
            debito    = r["debito"],
            credito   = r["credito"],
            saldo     = round(saldo, 2),
            tipo      = r["tipo"],
            status    = r["status"],
        ))

    return resultado


def resumo_extrato(linhas: list[LinhaExtrato]) -> dict:
    total_credito = sum(l.credito for l in linhas)
    total_debito  = sum(l.debito  for l in linhas)
    return {
        "credito": round(total_credito, 2),
        "debito":  round(total_debito,  2),
        "saldo":   round(total_credito - total_debito, 2),
    }


def filtrar_extrato(linhas: list[LinhaExtrato],
                    texto: str,
                    tipo: str = "") -> list[LinhaExtrato]:
    """
    Filtra linhas do extrato em memória.
    texto — busca case-insensitive em descrição e categoria.
    tipo  — "receita" | "despesa" | "" (todos).
    """
    texto_l = texto.lower()
    resultado = []
    for l in linhas:
        if tipo and l.tipo != tipo:
            continue
        if texto_l and texto_l not in l.descricao.lower() \
                   and texto_l not in l.categoria.lower():
            continue
        resultado.append(l)
    return resultado
