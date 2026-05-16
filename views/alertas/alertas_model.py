"""
alertas_model.py — Alertas e notificações do Serenus.

Fontes verificadas:
- contas_pagar vencidas ou a vencer em até 7 dias (status=pendente)
- parcelas_cartao pendentes no mês corrente
- ativos de renda fixa com vencimento em até 30 dias
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta

from database import conectar

_JANELA_CONTA_DIAS = 7
_JANELA_RF_DIAS    = 30


@dataclass
class Alerta:
    tipo:      str   # "conta_vencida" | "conta_proxima" | "fatura_cartao" | "vencimento_rf"
    descricao: str
    data:      str   # ISO YYYY-MM-DD ou YYYY-MM
    urgencia:  str   # "alta" | "media" | "baixa"
    valor:     float = 0.0


def alertas_pendentes() -> list[Alerta]:
    """Retorna todos os alertas ativos, ordenados por urgência (alta → media → baixa)."""
    alertas: list[Alerta] = []
    alertas += _contas_pagar()
    alertas += _faturas_cartao()
    alertas += _vencimentos_rf()

    _ordem = {"alta": 0, "media": 1, "baixa": 2}
    alertas.sort(key=lambda a: _ordem[a.urgencia])
    return alertas


# ─────────────────────────────────────────────────────────────────────────────

def _contas_pagar() -> list[Alerta]:
    hoje    = date.today()
    limite  = (hoje + timedelta(days=_JANELA_CONTA_DIAS)).isoformat()
    hoje_s  = hoje.isoformat()

    with conectar() as conn:
        rows = conn.execute("""
            SELECT cp.descricao, cp.valor, cp.data_vencimento,
                   COALESCE(pc.nome, '') AS plano
            FROM   contas_pagar cp
            LEFT JOIN plano_contas pc ON pc.id = cp.plano_conta_id
            WHERE  cp.status = 'pendente'
              AND  cp.data_vencimento <= ?
            ORDER BY cp.data_vencimento
        """, (limite,)).fetchall()

    alertas = []
    for r in rows:
        venc = r["data_vencimento"]
        nome = r["descricao"] or r["plano"] or "Despesa"
        if venc < hoje_s:
            alertas.append(Alerta(
                tipo="conta_vencida",
                descricao=f"{nome} — venceu em {_fmt(venc)}",
                data=venc,
                urgencia="alta",
                valor=r["valor"],
            ))
        else:
            dias = (date.fromisoformat(venc) - hoje).days
            sufixo = "hoje" if dias == 0 else f"em {dias} dia{'s' if dias > 1 else ''}"
            alertas.append(Alerta(
                tipo="conta_proxima",
                descricao=f"{nome} — vence {sufixo}",
                data=venc,
                urgencia="media",
                valor=r["valor"],
            ))
    return alertas


def _faturas_cartao() -> list[Alerta]:
    mes_atual = date.today().strftime("%Y-%m")

    with conectar() as conn:
        rows = conn.execute("""
            SELECT c.nome AS cartao, SUM(p.valor) AS total
            FROM   parcelas_cartao p
            JOIN   cartoes c ON c.id = p.cartao_id
            WHERE  p.mes_referencia = ?
              AND  p.status = 'pendente'
            GROUP BY p.cartao_id
        """, (mes_atual,)).fetchall()

    return [
        Alerta(
            tipo="fatura_cartao",
            descricao=f"Fatura {r['cartao']} — {mes_atual}",
            data=mes_atual,
            urgencia="media",
            valor=r["total"],
        )
        for r in rows
    ]


def _vencimentos_rf() -> list[Alerta]:
    hoje   = date.today()
    limite = (hoje + timedelta(days=_JANELA_RF_DIAS)).isoformat()
    hoje_s = hoje.isoformat()

    with conectar() as conn:
        rows = conn.execute("""
            SELECT a.codigo, a.nome, a.vencimento
            FROM   ativos a
            WHERE  a.ativo = 1
              AND  a.vencimento IS NOT NULL
              AND  a.vencimento <= ?
            ORDER BY a.vencimento
        """, (limite,)).fetchall()

    alertas = []
    for r in rows:
        venc = r["vencimento"]
        nome = f"{r['codigo']} — {r['nome']}"
        if venc < hoje_s:
            desc = f"{nome}: venceu em {_fmt(venc)}"
        else:
            dias = (date.fromisoformat(venc) - hoje).days
            desc = f"{nome}: vence em {dias} dia{'s' if dias != 1 else ''}"
        alertas.append(Alerta(
            tipo="vencimento_rf",
            descricao=desc,
            data=venc,
            urgencia="media",
        ))
    return alertas


def _fmt(iso: str) -> str:
    """YYYY-MM-DD → DD/MM/AAAA"""
    try:
        d = date.fromisoformat(iso)
        return d.strftime("%d/%m/%Y")
    except Exception:
        return iso
