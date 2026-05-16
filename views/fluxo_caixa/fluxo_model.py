"""
fluxo_model.py — Módulo 4: Fluxo de Caixa.
Projeta receita vs compromissos mês a mês cruzando:
  - fontes_receita (recorrentes + periodicidade)
  - receitas_especiais (13º, férias, FGTS, etc.)
  - dividas ativas (parcelas mensais)
  - contas_pagar tipo_custo='fixo' recorrentes (despesas fixas)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from database import conectar
from views.receitas.receita_model import listar_fontes, listar_receitas_especiais
from views.visao_longo_prazo.divida_model import listar_dividas


# ---------------------------------------------------------------------------
# Estrutura de um mês projetado
# ---------------------------------------------------------------------------

@dataclass
class MesFluxo:
    indice:         int          # 0 = mês atual, 1 = próximo, ...
    mes_0:          int          # 0-11
    ano:            int
    label:          str          # "Mai/2025"
    receita:        float
    parcelas:       float        # total dívidas ativas nesse mês
    despesas_fixas: float
    saldo_livre:    float
    especiais:      list         # lista de ReceitaEspecial do mês
    status:         str          # "verde" | "amarelo" | "vermelho"


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _base_despesas_fixas() -> float:
    """
    Calcula o valor base mensal de despesas fixas a partir de:
    1. contas_pagar recorrentes com plano_conta tipo_custo='fixo' (histórico)
    2. Fallback: média das últimas 3 entradas por conta fixa distinta
    Retorna 0 se não houver dados.
    """
    with conectar() as conn:
        # Busca a soma das contas fixas recorrentes do mês mais recente que tiver dados
        row = conn.execute("""
            SELECT strftime('%Y-%m', data_vencimento) AS periodo,
                   SUM(cp.valor) AS total
            FROM   contas_pagar cp
            JOIN   plano_contas pc ON pc.id = cp.plano_conta_id
            WHERE  pc.tipo_custo = 'fixo'
              AND  cp.status != 'cancelado'
            GROUP BY periodo
            ORDER BY periodo DESC
            LIMIT 1
        """).fetchone()

        if row and row["total"]:
            return float(row["total"])

        # Sem histórico: soma dos planos fixos ativos sem valor cadastrado → R$ 0
        return 0.0


def _despesas_fixas_mes(mes_0: int, ano: int, base: float) -> float:
    """
    Para meses passados/correntes: usa valor real de contas_pagar fixo.
    Para meses futuros: usa a base calculada acima.
    """
    mes_num = mes_0 + 1  # 1-12
    hoje = date.today()
    alvo = date(ano, mes_num, 1)
    atual = date(hoje.year, hoje.month, 1)

    if alvo <= atual:
        # Mês já passou ou é o corrente: busca real
        inicio = f"{ano:04d}-{mes_num:02d}-01"
        if mes_num == 12:
            fim = f"{ano+1:04d}-01-01"
        else:
            fim = f"{ano:04d}-{mes_num+1:02d}-01"

        with conectar() as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(cp.valor), 0) AS total
                FROM   contas_pagar cp
                JOIN   plano_contas pc ON pc.id = cp.plano_conta_id
                WHERE  pc.tipo_custo = 'fixo'
                  AND  cp.status != 'cancelado'
                  AND  cp.data_vencimento >= ? AND cp.data_vencimento < ?
            """, (inicio, fim)).fetchone()
            if row and row["total"]:
                return float(row["total"])

    return base


def _parcelas_mes(dividas, indice: int) -> float:
    """Soma das parcelas de dívidas ativas para o mês `indice` a partir de hoje."""
    total = 0.0
    for d in dividas:
        if indice < d.parcelas_restantes:
            total += d.parcela_mensal
    return total


def _receita_mes(fontes, especiais_por_mes: dict, mes_0: int) -> tuple[float, list]:
    """
    Receita total do mês:
    - Fontes recorrentes (ajustadas por periodicidade)
    - Receitas especiais do mês
    Retorna (total, lista_especiais)
    """
    total = 0.0
    for f in fontes:
        if not f.ativa:
            continue
        if f.periodicidade == "mensal":
            total += f.valor_mensal
        elif f.periodicidade == "bimestral":
            total += f.valor_mensal / 2
        elif f.periodicidade == "anual":
            total += f.valor_mensal / 12

    especiais = especiais_por_mes.get(mes_0, [])
    for e in especiais:
        if e.recorrente_anual or True:  # inclui todas
            total += e.valor

    return total, especiais


# ---------------------------------------------------------------------------
# Projeção principal
# ---------------------------------------------------------------------------

def projetar_fluxo(meses: int) -> list[MesFluxo]:
    hoje    = date.today()
    fontes  = listar_fontes(apenas_ativas=True)
    dividas = listar_dividas(apenas_ativas=True)

    todas_especiais = listar_receitas_especiais()
    # Agrupa por mês (0-11)
    especiais_por_mes: dict[int, list] = {}
    for e in todas_especiais:
        especiais_por_mes.setdefault(e.mes, []).append(e)

    base_fixas = _base_despesas_fixas()

    resultado: list[MesFluxo] = []
    for i in range(meses):
        mes_abs = hoje.month - 1 + i        # 0-based
        ano     = hoje.year + mes_abs // 12
        mes_0   = mes_abs % 12              # 0-11
        mes_num = mes_0 + 1                 # 1-12

        lbl = date(ano, mes_num, 1).strftime("%b/%Y")

        receita, especiais = _receita_mes(fontes, especiais_por_mes, mes_0)
        parcelas    = _parcelas_mes(dividas, i)
        desp_fixas  = _despesas_fixas_mes(mes_0, ano, base_fixas)
        saldo       = receita - parcelas - desp_fixas

        if saldo < 0:
            status = "vermelho"
        elif saldo < 500:
            status = "amarelo"
        else:
            status = "verde"

        resultado.append(MesFluxo(
            indice         = i,
            mes_0          = mes_0,
            ano            = ano,
            label          = lbl,
            receita        = receita,
            parcelas       = parcelas,
            despesas_fixas = desp_fixas,
            saldo_livre    = saldo,
            especiais      = especiais,
            status         = status,
        ))

    return resultado


# ---------------------------------------------------------------------------
# Cards de resumo
# ---------------------------------------------------------------------------

def resumo_fluxo(projecao: list[MesFluxo]) -> dict:
    if not projecao:
        return {}

    mes_atual = projecao[0]

    # Receita mensal base (sem especiais do mês, só fontes recorrentes)
    fontes = listar_fontes(apenas_ativas=True)
    receita_base = sum(
        f.valor_mensal if f.periodicidade == "mensal"
        else f.valor_mensal / 2 if f.periodicidade == "bimestral"
        else f.valor_mensal / 12
        for f in fontes
    )

    dividas        = listar_dividas(apenas_ativas=True)
    total_parcelas = sum(d.parcela_mensal for d in dividas if d.parcelas_restantes > 0)

    meses_vermelho = sum(1 for m in projecao if m.status == "vermelho")
    meses_amarelo  = sum(1 for m in projecao if m.status == "amarelo")

    return {
        "receita_base":    receita_base,
        "total_parcelas":  total_parcelas,
        "saldo_livre_mes": mes_atual.saldo_livre,
        "meses_vermelho":  meses_vermelho,
        "meses_amarelo":   meses_amarelo,
        "total_meses":     len(projecao),
    }
