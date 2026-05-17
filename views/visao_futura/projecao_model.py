"""
projecao_model.py — Visão Futura: projeção mês a mês (até 60 meses).
Cruza: contas_pagar reais + despesas fixas projetadas + parcelas_cartao + dívidas + receitas.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date

from database import conectar
from views.receitas.receita_model import listar_fontes, listar_receitas_especiais
from views.visao_longo_prazo.divida_model import listar_dividas


@dataclass
class MesProjecao:
    indice:          int    # 0 = mês atual
    ano:             int
    mes_num:         int    # 1-12
    label:           str    # "Mai/2026"
    receitas:        float
    desp_fixas:      float
    desp_variaveis:  float
    parcelas_cartao: float
    dividas:         float
    total_saidas:    float
    saldo:           float
    is_futuro:       bool   # True se mês ainda não chegou


def _base_fixas_projecao() -> float:
    """Valor base de despesas fixas do mês mais recente com lançamentos."""
    with conectar() as conn:
        row = conn.execute("""
            SELECT SUM(cp.valor) AS total
            FROM   contas_pagar cp
            JOIN   plano_contas pc ON pc.id = cp.plano_conta_id
            WHERE  pc.tipo_custo = 'fixo'
              AND  cp.status != 'cancelado'
              AND  strftime('%Y-%m', cp.data_vencimento) = (
                       SELECT strftime('%Y-%m', data_vencimento)
                       FROM   contas_pagar cp2
                       JOIN   plano_contas pc2 ON pc2.id = cp2.plano_conta_id
                       WHERE  pc2.tipo_custo = 'fixo'
                         AND  cp2.status != 'cancelado'
                       ORDER BY data_vencimento DESC
                       LIMIT 1
                   )
        """).fetchone()
    return float(row["total"] or 0) if row else 0.0


def _desp_reais_mes(ano: int, mes_num: int) -> tuple[float, float]:
    """Retorna (fixas, variaveis) reais do banco para o mês dado.

    Exclui despesas cuja categoria é 'Cartão de Crédito' — essas já são contadas
    em `_parcelas_cartao_mes()` via tabela `parcelas_cartao`. Contá-las também
    aqui causaria dupla contagem em `total_saidas`.
    """
    inicio = f"{ano:04d}-{mes_num:02d}-01"
    fim = f"{ano:04d}-{mes_num+1:02d}-01" if mes_num < 12 else f"{ano+1:04d}-01-01"
    with conectar() as conn:
        rows = conn.execute("""
            SELECT pc.tipo_custo, COALESCE(SUM(cp.valor), 0) AS total
            FROM   contas_pagar cp
            JOIN   plano_contas pc ON pc.id = cp.plano_conta_id
            WHERE  cp.status != 'cancelado'
              AND  cp.data_vencimento >= ? AND cp.data_vencimento < ?
              AND  COALESCE(pc.categoria,'') != 'Cartão de Crédito'
            GROUP BY pc.tipo_custo
        """, (inicio, fim)).fetchall()
    fixas = variaveis = 0.0
    for r in rows:
        if r["tipo_custo"] == "fixo":
            fixas = float(r["total"])
        elif r["tipo_custo"] == "variavel":
            variaveis = float(r["total"])
    return fixas, variaveis


def _receitas_vendas_mes(ano: int, mes_num: int) -> float:
    """Soma vendas à vista pagas + recebíveis quitados neste mês."""
    inicio = f"{ano:04d}-{mes_num:02d}-01"
    fim    = f"{ano:04d}-{mes_num+1:02d}-01" if mes_num < 12 else f"{ano+1:04d}-01-01"
    try:
        with conectar() as conn:
            avista = conn.execute("""
                SELECT COALESCE(SUM(valor_liquido), 0)
                FROM vendas
                WHERE tipo_pagamento='avista' AND status='paga'
                  AND data_venda >= ? AND data_venda < ?
            """, (inicio, fim)).fetchone()[0]
            aprazo = conn.execute("""
                SELECT COALESCE(SUM(valor), 0)
                FROM contas_a_receber
                WHERE status='recebido'
                  AND data_recebimento >= ? AND data_recebimento < ?
            """, (inicio, fim)).fetchone()[0]
        return float(avista or 0) + float(aprazo or 0)
    except Exception:
        return 0.0


def _parcelas_cartao_mes(mes_ref: str) -> float:
    """Soma das parcelas_cartao para um mes_referencia ('YYYY-MM')."""
    with conectar() as conn:
        row = conn.execute("""
            SELECT COALESCE(SUM(valor), 0) AS total
            FROM   parcelas_cartao
            WHERE  mes_referencia = ? AND status != 'cancelado'
        """, (mes_ref,)).fetchone()
    return float(row["total"] or 0) if row else 0.0


def projetar(meses: int = 60, inicio_offset: int = 0) -> list[MesProjecao]:
    """
    Projeta `meses` meses a partir de (hoje + inicio_offset meses).
    inicio_offset negativo = começar no passado.
    indice=0 sempre corresponde ao mês atual, independente do offset.
    """
    hoje       = date.today()
    fontes     = listar_fontes(apenas_ativas=True)
    dividas    = listar_dividas(apenas_ativas=True)
    especiais  = listar_receitas_especiais()

    esp_por_mes: dict[int, float] = {}
    for e in especiais:
        esp_por_mes[e.mes] = esp_por_mes.get(e.mes, 0.0) + e.valor

    base_fixas = _base_fixas_projecao()
    hoje_primeiro = date(hoje.year, hoje.month, 1)

    resultado: list[MesProjecao] = []
    for i in range(meses):
        # indice real em relação ao mês atual (pode ser negativo = passado)
        indice = inicio_offset + i
        mes_abs = hoje.month - 1 + indice
        ano     = hoje.year + mes_abs // 12
        mes_num = mes_abs % 12 + 1
        mes_ref = f"{ano:04d}-{mes_num:02d}"
        alvo    = date(ano, mes_num, 1)
        is_futuro = alvo > hoje_primeiro

        # Receitas
        rec = 0.0
        for f in fontes:
            if f.periodicidade == "mensal":
                rec += f.valor_mensal
            elif f.periodicidade == "bimestral":
                rec += f.valor_mensal / 2
            elif f.periodicidade == "anual":
                rec += f.valor_mensal / 12
        rec += esp_por_mes.get(mes_num - 1, 0.0)
        if not is_futuro:
            rec += _receitas_vendas_mes(ano, mes_num)

        # Despesas: usa dados reais para passado/atual, projeção para futuro
        if not is_futuro:
            fixas, variaveis = _desp_reais_mes(ano, mes_num)
        else:
            fixas, variaveis = base_fixas, 0.0

        # Parcelas cartão (reais para qualquer mês)
        parc_cartao = _parcelas_cartao_mes(mes_ref)

        # Dívidas: só para meses futuros (no passado já estão em contas_pagar)
        # indice representa meses a partir do mês atual
        if is_futuro:
            divs = sum(d.parcela_mensal for d in dividas
                       if indice < d.parcelas_restantes)
        else:
            divs = 0.0

        total_saidas = fixas + variaveis + parc_cartao + divs
        saldo        = rec - total_saidas

        from datetime import datetime
        lbl = datetime(ano, mes_num, 1).strftime("%b/%Y")

        resultado.append(MesProjecao(
            indice          = indice,
            ano             = ano,
            mes_num         = mes_num,
            label           = lbl,
            receitas        = rec,
            desp_fixas      = fixas,
            desp_variaveis  = variaveis,
            parcelas_cartao = parc_cartao,
            dividas         = divs,
            total_saidas    = total_saidas,
            saldo           = saldo,
            is_futuro       = is_futuro,
        ))

    return resultado


# ---------------------------------------------------------------------------
# Detalhe por sub-item (para expansão das linhas)
# ---------------------------------------------------------------------------

@dataclass
class DetalheProjecao:
    """Valores por sub-item para cada mês da projeção. {nome: [val_mes0, …]}"""
    receitas:        dict[str, list[float]] = field(default_factory=dict)
    desp_fixas:      dict[str, list[float]] = field(default_factory=dict)
    desp_variaveis:  dict[str, list[float]] = field(default_factory=dict)
    parcelas_cartao: dict[str, list[float]] = field(default_factory=dict)
    dividas_items:   dict[str, list[float]] = field(default_factory=dict)


def carregar_detalhes(projecao: list[MesProjecao]) -> DetalheProjecao:
    """Busca breakdown por sub-item para todos os meses da projeção."""
    n = len(projecao)
    if n == 0:
        return DetalheProjecao()

    mes_refs = [f"{m.ano:04d}-{m.mes_num:02d}" for m in projecao]
    mr_idx   = {mr: i for i, mr in enumerate(mes_refs)}

    # ── Receitas ──────────────────────────────────────────────────────────
    fontes   = listar_fontes(apenas_ativas=True)
    especiais = listar_receitas_especiais()
    receitas: dict[str, list[float]] = {}

    for m_i, m in enumerate(projecao):
        for f in fontes:
            v = 0.0
            if f.periodicidade == "mensal":
                v = f.valor_mensal
            elif f.periodicidade == "bimestral":
                v = f.valor_mensal / 2
            elif f.periodicidade == "anual":
                v = f.valor_mensal / 12
            if v > 0:
                receitas.setdefault(f.nome, [0.0] * n)
                receitas[f.nome][m_i] += v
        for e in especiais:
            if e.mes == m.mes_num - 1:   # e.mes é 0-indexed
                receitas.setdefault(e.nome, [0.0] * n)
                receitas[e.nome][m_i] += e.valor

    # ── Vendas e Serviços (meses reais) ──────────────────────────────────
    try:
        vendas_vals = [0.0] * n
        for m_i, m in enumerate(projecao):
            if not m.is_futuro:
                v = _receitas_vendas_mes(m.ano, m.mes_num)
                if v > 0:
                    vendas_vals[m_i] = v
        if any(v > 0 for v in vendas_vals):
            receitas["Vendas e Serviços"] = vendas_vals
    except Exception:
        pass

    # ── Despesas reais (passado e futuro com lançamentos) ─────────────────
    first, last = projecao[0], projecao[-1]
    dt_start = f"{first.ano:04d}-{first.mes_num:02d}-01"
    dt_end   = (f"{last.ano + 1:04d}-01-01" if last.mes_num == 12
                else f"{last.ano:04d}-{last.mes_num + 1:02d}-01")

    desp_fixas:     dict[str, list[float]] = {}
    desp_variaveis: dict[str, list[float]] = {}

    with conectar() as conn:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', cp.data_vencimento) AS mes_ref,
                   pc.nome, pc.tipo_custo,
                   COALESCE(SUM(cp.valor), 0) AS total
            FROM   contas_pagar cp
            JOIN   plano_contas pc ON pc.id = cp.plano_conta_id
            WHERE  cp.status != 'cancelado'
              AND  cp.data_vencimento >= ? AND cp.data_vencimento < ?
              AND  COALESCE(pc.categoria,'') != 'Cartão de Crédito'
            GROUP  BY mes_ref, pc.id
            ORDER  BY total DESC
        """, (dt_start, dt_end)).fetchall()

    for r in rows:
        fi = mr_idx.get(r["mes_ref"])
        if fi is None:
            continue
        nome = r["nome"]
        val  = float(r["total"])
        if r["tipo_custo"] == "fixo":
            desp_fixas.setdefault(nome, [0.0] * n)
            desp_fixas[nome][fi] += val
        elif r["tipo_custo"] == "variavel":
            desp_variaveis.setdefault(nome, [0.0] * n)
            desp_variaveis[nome][fi] += val

    # ── Parcelas de cartão ────────────────────────────────────────────────
    parcelas_cartao: dict[str, list[float]] = {}

    with conectar() as conn:
        rows = conn.execute("""
            SELECT pc.mes_referencia,
                   ct.nome AS cartao_nome,
                   cc.descricao,
                   COALESCE(SUM(pc.valor), 0) AS total
            FROM   parcelas_cartao pc
            JOIN   compras_cartao  cc ON cc.id = pc.compra_id
            JOIN   cartoes         ct ON ct.id = pc.cartao_id
            WHERE  pc.status != 'cancelado'
              AND  pc.mes_referencia >= ? AND pc.mes_referencia <= ?
            GROUP  BY pc.mes_referencia, cc.id
            ORDER  BY ct.nome, cc.descricao
        """, (mes_refs[0], mes_refs[-1])).fetchall()

    for r in rows:
        fi = mr_idx.get(r["mes_referencia"])
        if fi is None:
            continue
        nome = f"{r['cartao_nome']} · {r['descricao']}"
        val  = float(r["total"])
        parcelas_cartao.setdefault(nome, [0.0] * n)
        parcelas_cartao[nome][fi] += val

    # ── Dívidas (projeção futura apenas) ──────────────────────────────────
    dividas_items: dict[str, list[float]] = {}

    for d in listar_dividas(apenas_ativas=True):
        vals = [0.0] * n
        for fi, m in enumerate(projecao):
            if m.is_futuro and m.indice < d.parcelas_restantes:
                vals[fi] = d.parcela_mensal
        if any(v > 0 for v in vals):
            dividas_items[d.nome] = vals

    return DetalheProjecao(
        receitas        = receitas,
        desp_fixas      = desp_fixas,
        desp_variaveis  = desp_variaveis,
        parcelas_cartao = parcelas_cartao,
        dividas_items   = dividas_items,
    )
