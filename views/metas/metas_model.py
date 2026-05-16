"""
metas_model.py — Módulo de Metas Financeiras do Serenus.

Cada meta tem: nome, valor_alvo, valor_atual, prazo (opcional), descricao.
Campos calculados em runtime: progresso_pct, concluida, dias_restantes,
economia_mensal_necessaria.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from database import conectar


@dataclass
class Meta:
    id:          int
    nome:        str
    valor_alvo:  float
    valor_atual: float
    prazo:       Optional[str]  # ISO YYYY-MM-DD ou None
    descricao:   str
    criado_em:   str

    # calculados
    progresso_pct:               float = 0.0
    concluida:                   bool  = False
    dias_restantes:              Optional[int]   = None
    economia_mensal_necessaria:  Optional[float] = None


def _calcular(meta: Meta) -> Meta:
    alvo = meta.valor_alvo
    atual = meta.valor_atual

    if alvo > 0:
        meta.progresso_pct = min(100.0, round(atual / alvo * 100, 1))
    else:
        meta.progresso_pct = 0.0

    meta.concluida = atual >= alvo

    if meta.prazo:
        try:
            prazo_d = date.fromisoformat(meta.prazo)
            meta.dias_restantes = (prazo_d - date.today()).days
            meses = meta.dias_restantes / 30.0
            faltando = max(0.0, alvo - atual)
            if meses > 0:
                meta.economia_mensal_necessaria = round(faltando / meses, 2)
            else:
                meta.economia_mensal_necessaria = faltando
        except Exception:
            pass

    return meta


# ─────────────────────────────────────────────────────────────────────────────

def listar_metas() -> list[Meta]:
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM metas_financeiras ORDER BY criado_em DESC"
        ).fetchall()
    return [_calcular(Meta(
        id=r["id"], nome=r["nome"],
        valor_alvo=r["valor_alvo"], valor_atual=r["valor_atual"],
        prazo=r["prazo"], descricao=r["descricao"] or "",
        criado_em=r["criado_em"],
    )) for r in rows]


def salvar_meta(dados: dict, id: Optional[int] = None) -> int:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        if id is not None:
            conn.execute("""
                UPDATE metas_financeiras
                SET nome=?, valor_alvo=?, valor_atual=?, prazo=?, descricao=?
                WHERE id=?
            """, (dados["nome"], dados["valor_alvo"], dados.get("valor_atual", 0),
                  dados.get("prazo") or None, dados.get("descricao", ""), id))
            return id
        cur = conn.execute("""
            INSERT INTO metas_financeiras
              (nome, valor_alvo, valor_atual, prazo, descricao, criado_em)
            VALUES (?,?,?,?,?,?)
        """, (dados["nome"], dados["valor_alvo"], dados.get("valor_atual", 0),
              dados.get("prazo") or None, dados.get("descricao", ""), agora))
        return cur.lastrowid


def atualizar_valor_meta(id: int, valor_atual: float) -> None:
    with conectar() as conn:
        conn.execute(
            "UPDATE metas_financeiras SET valor_atual=? WHERE id=?",
            (valor_atual, id),
        )


def excluir_meta(id: int) -> None:
    with conectar() as conn:
        conn.execute("DELETE FROM metas_financeiras WHERE id=?", (id,))
