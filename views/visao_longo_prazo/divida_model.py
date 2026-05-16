"""
divida_model.py — Lógica de negócio para Dívidas e projeções de longo prazo.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date
import calendar

from database import conectar


# ---------------------------------------------------------------------------
# Entidade
# ---------------------------------------------------------------------------

@dataclass
class Divida:
    id:             int
    nome:           str
    tipo:           str
    saldo_atual:    float
    parcela_mensal: float
    total_parcelas: int
    parcelas_pagas: int
    dia_vencimento: Optional[int]
    taxa_juros:     float
    observacao:     str
    ativa:          bool
    criado_em:      str

    @property
    def parcelas_restantes(self) -> int:
        return max(0, self.total_parcelas - self.parcelas_pagas)

    @property
    def fim_previsto(self) -> Optional[date]:
        """Data estimada de quitação (sem juros)."""
        if self.parcelas_restantes == 0:
            return None
        hoje = date.today()
        mes  = hoje.month + self.parcelas_restantes - 1
        ano  = hoje.year + (mes - 1) // 12
        mes  = ((mes - 1) % 12) + 1
        ultimo = calendar.monthrange(ano, mes)[1]
        dia = min(self.dia_vencimento or hoje.day, ultimo)
        return date(ano, mes, dia)

    @property
    def fim_previsto_str(self) -> str:
        d = self.fim_previsto
        if d is None:
            return "Quitado"
        return f"{d.strftime('%b/%Y')}"


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def _row_to_divida(r) -> Divida:
    d = dict(r)
    return Divida(
        id             = d["id"],
        nome           = d["nome"],
        tipo           = d["tipo"],
        saldo_atual    = d["saldo_atual"],
        parcela_mensal = d["parcela_mensal"],
        total_parcelas = d["total_parcelas"],
        parcelas_pagas = d["parcelas_pagas"],
        dia_vencimento = d.get("dia_vencimento"),
        taxa_juros     = d.get("taxa_juros") or 0.0,
        observacao     = d.get("observacao") or "",
        ativa          = bool(d["ativa"]),
        criado_em      = d.get("criado_em") or "",
    )


def listar_dividas(apenas_ativas: bool = False) -> list[Divida]:
    sql = "SELECT * FROM dividas"
    if apenas_ativas:
        sql += " WHERE ativa = 1"
    sql += " ORDER BY nome"
    with conectar() as conn:
        rows = conn.execute(sql).fetchall()
    return [_row_to_divida(r) for r in rows]


def salvar_divida(dados: dict, id: Optional[int] = None) -> int:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        if id is not None:
            conn.execute("""
                UPDATE dividas
                SET nome=?, tipo=?, saldo_atual=?, parcela_mensal=?,
                    total_parcelas=?, parcelas_pagas=?, dia_vencimento=?,
                    taxa_juros=?, observacao=?
                WHERE id=?
            """, (
                dados["nome"], dados["tipo"], dados["saldo_atual"],
                dados["parcela_mensal"], dados["total_parcelas"],
                dados.get("parcelas_pagas", 0), dados.get("dia_vencimento"),
                dados.get("taxa_juros", 0.0), dados.get("observacao", ""),
                id,
            ))
            return id
        else:
            cur = conn.execute("""
                INSERT INTO dividas
                (nome, tipo, saldo_atual, parcela_mensal, total_parcelas,
                 parcelas_pagas, dia_vencimento, taxa_juros, observacao, ativa, criado_em)
                VALUES (?,?,?,?,?,?,?,?,?,1,?)
            """, (
                dados["nome"], dados["tipo"], dados["saldo_atual"],
                dados["parcela_mensal"], dados["total_parcelas"],
                dados.get("parcelas_pagas", 0), dados.get("dia_vencimento"),
                dados.get("taxa_juros", 0.0), dados.get("observacao", ""),
                agora,
            ))
            return cur.lastrowid


def alternar_ativa_divida(id: int, ativa: bool):
    with conectar() as conn:
        conn.execute("UPDATE dividas SET ativa=? WHERE id=?", (int(ativa), id))


# ---------------------------------------------------------------------------
# Projeções
# ---------------------------------------------------------------------------

def projetar_evolucao(dividas: list[Divida], meses: int) -> list[dict]:
    """
    Retorna lista de dicts com saldo total por mês para o gráfico de linha.
    Cada dict: { 'mes': 0..N, 'label': 'Mai/25', 'saldo': float }
    Vai até o mês em que todas as dívidas zeram (mesmo que além do horizonte).
    """
    hoje   = date.today()
    # Calcula o mês máximo necessário (até a última dívida quitar)
    max_parcelas = max((d.parcelas_restantes for d in dividas), default=0)
    n_meses = max(meses, max_parcelas) + 1

    resultado = []
    for i in range(n_meses + 1):
        saldo = 0.0
        for d in dividas:
            restantes = d.parcelas_restantes
            if i < restantes:
                # Saldo reduz linearmente (simplificação sem juros compostos)
                saldo += max(0.0, d.saldo_atual - d.parcela_mensal * i)
            # Após quitar: contribuição = 0
        mes_abs = hoje.month + i - 1
        ano     = hoje.year + mes_abs // 12
        mes     = mes_abs % 12 + 1
        label   = date(ano, mes, 1).strftime("%b/%Y")
        resultado.append({"mes": i, "label": label, "saldo": saldo})
        # Só interrompe após o mínimo de meses solicitados para não truncar o gráfico
        if saldo <= 0 and i >= meses:
            break

    return resultado


def calcular_quitacao_total(dividas: list[Divida]) -> str:
    """Retorna mês/ano em que a última dívida ativa é quitada."""
    if not dividas:
        return "—"
    max_parcelas = max((d.parcelas_restantes for d in dividas), default=0)
    if max_parcelas == 0:
        return "Quitado"
    hoje    = date.today()
    mes_abs = hoje.month + max_parcelas - 1
    ano     = hoje.year + (mes_abs - 1) // 12
    mes     = ((mes_abs - 1) % 12) + 1
    return date(ano, mes, 1).strftime("%b/%Y")


def status_horizonte(dividas: list[Divida], meses: int) -> list[dict]:
    """
    Para cada dívida, calcula o status dentro do horizonte.
    Retorna lista de dicts com progresso, saldo restante e se zerará.
    """
    resultado = []
    for d in dividas:
        restantes = d.parcelas_restantes
        pagas_no_horizonte = min(restantes, meses)
        zerado = restantes <= meses

        # Progresso em relação ao total da dívida
        total_pago_periodo = pagas_no_horizonte * d.parcela_mensal
        saldo_restante = max(0.0, d.saldo_atual - total_pago_periodo)
        pct_quitado_total = (d.parcelas_pagas + pagas_no_horizonte) / d.total_parcelas * 100

        resultado.append({
            "divida":          d,
            "pagas_horizonte": pagas_no_horizonte,
            "zerado":          zerado,
            "saldo_restante":  saldo_restante,
            "pct":             min(100.0, pct_quitado_total),
        })
    return resultado


def dados_barras_empilhadas(dividas: list[Divida], meses: int) -> dict:
    """
    Retorna estrutura para gráfico de barras empilhadas.
    { 'labels': ['Mai/25', ...], 'series': [{'nome': str, 'valores': [float,...]}] }
    """
    hoje   = date.today()
    labels = []
    for i in range(meses):
        mes_abs = hoje.month + i - 1
        ano     = hoje.year + mes_abs // 12
        mes     = mes_abs % 12 + 1
        labels.append(date(ano, mes, 1).strftime("%b/%Y"))

    series = []
    for d in dividas:
        valores = []
        for i in range(meses):
            if i < d.parcelas_restantes:
                valores.append(d.parcela_mensal)
            else:
                valores.append(0.0)
        series.append({"nome": d.nome, "valores": valores})

    return {"labels": labels, "series": series}


def resumo_dividas(dividas: list[Divida]) -> dict:
    """Cards de resumo do dashboard."""
    ativas = [d for d in dividas if d.ativa]
    return {
        "total_saldo":    sum(d.saldo_atual for d in ativas),
        "total_parcelas": sum(d.parcela_mensal for d in ativas),
        "qtd_ativas":     len(ativas),
        "quitacao_total": calcular_quitacao_total(ativas),
    }
