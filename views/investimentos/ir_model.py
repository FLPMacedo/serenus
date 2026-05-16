"""
ir_model.py — Cálculo de IR estimado sobre ganhos de capital em investimentos.

Regras simplificadas (BR 2024):
  Ação / ETF de ações  → 15% sobre lucro
  FII / ETF de FIIs    → 20% sobre lucro
  CDB / Tesouro / Fundo → tabela regressiva por prazo (dias)
      ≤ 180 d  → 22,5%
      181-360  → 20,0%
      361-720  → 17,5%
      > 720 d  → 15,0%
  Cripto               → 15% (simplificado)
  Outro                → 15%

NOTA: este modelo é uma ESTIMATIVA educacional.
Não considera isenção de R$20k/mês para ações, come-cotas, etc.
Consulte um contador para declaração oficial.
"""
from __future__ import annotations

from database import conectar

# ─────────────────────────────────────────────────────────────────────────────
# Alíquotas
# ─────────────────────────────────────────────────────────────────────────────

_ALIQUOTA_SIMPLES = {
    "acao":   0.15,
    "etf":    0.15,
    "fii":    0.20,
    "cripto": 0.15,
    "outro":  0.15,
}

_NOTA_SIMPLIFICADO = (
    "Estimativa. Não inclui isenção mensal, come-cotas nem regimes especiais."
)


def _aliquota_rf(dias: int) -> float:
    if dias <= 180:
        return 0.225
    if dias <= 360:
        return 0.20
    if dias <= 720:
        return 0.175
    return 0.15


# ─────────────────────────────────────────────────────────────────────────────
# Funções públicas
# ─────────────────────────────────────────────────────────────────────────────

def calcular_ir_estimado(lucro_realizado: float, tipo: str,
                         dias_aplicacao: int = 0) -> dict:
    """
    Calcula IR estimado sobre lucro realizado de um ativo.

    Parâmetros
    ----------
    lucro_realizado : lucro bruto realizado (negativo = prejuízo → IR = 0)
    tipo            : tipo do ativo ("acao", "fii", "cdb", etc.)
    dias_aplicacao  : dias desde a aplicação (usado para RF regressiva)

    Retorna dict com: ir_devido, aliquota, base_calculo, nota
    """
    base = max(0.0, round(lucro_realizado, 2))

    if base == 0.0:
        return {
            "ir_devido":    0.0,
            "aliquota":     0.0,
            "base_calculo": 0.0,
            "nota":         "Sem lucro — IR = R$ 0,00.",
        }

    tipo_norm = tipo.lower()

    if tipo_norm in ("cdb", "tesouro", "fundo"):
        aliquota = _aliquota_rf(max(0, dias_aplicacao))
        nota = f"RF regressiva ({dias_aplicacao}d). " + _NOTA_SIMPLIFICADO
    else:
        aliquota = _ALIQUOTA_SIMPLES.get(tipo_norm, 0.15)
        nota = _NOTA_SIMPLIFICADO

    ir = round(base * aliquota, 2)
    return {
        "ir_devido":    ir,
        "aliquota":     aliquota,
        "base_calculo": base,
        "nota":         nota,
    }


def resumo_ir_carteira() -> dict:
    """
    Agrega IR estimado de todos os ativos com lucro realizado > 0.
    Retorna: total_lucro, total_ir, detalhes (lista por ativo).
    """
    with conectar() as conn:
        rows = conn.execute("""
            SELECT a.codigo, a.nome, a.tipo,
                   a.vencimento,
                   pc.lucro_realizado
            FROM   posicao_cache pc
            JOIN   ativos a ON a.id = pc.ativo_id
            WHERE  pc.lucro_realizado > 0
            ORDER  BY a.tipo, a.codigo
        """).fetchall()

    detalhes = []
    total_lucro = 0.0
    total_ir    = 0.0

    for r in rows:
        from datetime import date
        dias = 0
        if r["vencimento"]:
            try:
                venc = date.fromisoformat(r["vencimento"])
                dias = (venc - date.today()).days
                dias = max(0, abs(dias))  # usa distância absoluta como proxy
            except Exception:
                dias = 0

        calc = calcular_ir_estimado(r["lucro_realizado"], r["tipo"], dias)
        total_lucro += r["lucro_realizado"]
        total_ir    += calc["ir_devido"]
        detalhes.append({
            "codigo":   r["codigo"],
            "nome":     r["nome"],
            "tipo":     r["tipo"],
            "lucro":    r["lucro_realizado"],
            "aliquota": calc["aliquota"],
            "ir":       calc["ir_devido"],
        })

    return {
        "total_lucro": round(total_lucro, 2),
        "total_ir":    round(total_ir, 2),
        "detalhes":    detalhes,
    }
