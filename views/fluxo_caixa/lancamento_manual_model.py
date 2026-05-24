"""
lancamento_manual_model.py — Lançamentos manuais de caixa.

Um lançamento manual é uma entrada/saída pontual de dinheiro que NÃO vem de
contas_pagar (despesa programada) nem das automações (fontes_receita, vendas,
investimentos). Casos típicos:
  - Recebi R$ 50 em espécie de alguém.
  - Paguei lanche em dinheiro.
  - Transferência entre contas próprias.
  - Receita/despesa one-off que não vale criar categoria.

Regras:
  - Categoria é obrigatória.
  - Tipo 'saida'   → exige plano_conta_id (FK pra plano_contas).
  - Tipo 'entrada' → exige fonte_receita_id (FK pra fontes_receita).
  - Valor > 0 sempre (o sinal é dado pelo tipo).
  - NÃO entram em projeção de Visão Futura (são avulsos).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from database import conectar

log = logging.getLogger(__name__)


@dataclass
class LancamentoManual:
    id:               int
    data:             str         # YYYY-MM-DD
    descricao:        str
    tipo:             str         # 'entrada' | 'saida'
    plano_conta_id:   Optional[int]
    fonte_receita_id: Optional[int]
    valor:            float
    observacao:       str
    nome_categoria:   str         # resolvido via JOIN (plano_contas.nome OU fontes_receita.nome)


_TIPOS_VALIDOS = {"entrada", "saida"}


def _validar(dados: dict) -> None:
    tipo = dados.get("tipo")
    if tipo not in _TIPOS_VALIDOS:
        raise ValueError(f"tipo inválido: {tipo!r} (use 'entrada' ou 'saida')")

    descricao = (dados.get("descricao") or "").strip()
    if not descricao:
        raise ValueError("descrição é obrigatória")

    valor = float(dados.get("valor") or 0.0)
    if valor <= 0:
        raise ValueError("valor deve ser maior que zero")

    plano = dados.get("plano_conta_id")
    fonte = dados.get("fonte_receita_id")

    if tipo == "saida":
        if not plano:
            raise ValueError("saída exige plano_conta_id (categoria de despesa)")
        if fonte:
            raise ValueError("saída não deve receber fonte_receita_id")
    else:  # entrada
        if not fonte:
            raise ValueError("entrada exige fonte_receita_id (categoria de receita)")
        if plano:
            raise ValueError("entrada não deve receber plano_conta_id")


def salvar_lancamento(dados: dict) -> int:
    """Cria um lançamento manual. Retorna o id criado.

    Levanta ValueError se dados forem inválidos (categoria errada, valor <= 0,
    descrição vazia, tipo inválido).
    """
    _validar(dados)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with conectar() as conn:
        cur = conn.execute(
            """
            INSERT INTO lancamentos_manuais
                (data, descricao, tipo, plano_conta_id, fonte_receita_id,
                 valor, observacao, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados["data"],
                dados["descricao"].strip(),
                dados["tipo"],
                dados.get("plano_conta_id"),
                dados.get("fonte_receita_id"),
                float(dados["valor"]),
                (dados.get("observacao") or "").strip(),
                agora,
            ),
        )
        log.info("Lançamento manual criado: id=%s tipo=%s valor=%.2f",
                 cur.lastrowid, dados["tipo"], dados["valor"])
        return cur.lastrowid


def atualizar_lancamento(id_: int, dados: dict) -> None:
    """Atualiza um lançamento manual existente. Mesmas validações de salvar."""
    _validar(dados)
    with conectar() as conn:
        conn.execute(
            """
            UPDATE lancamentos_manuais
               SET data             = ?,
                   descricao        = ?,
                   tipo             = ?,
                   plano_conta_id   = ?,
                   fonte_receita_id = ?,
                   valor            = ?,
                   observacao       = ?
             WHERE id = ?
            """,
            (
                dados["data"],
                dados["descricao"].strip(),
                dados["tipo"],
                dados.get("plano_conta_id"),
                dados.get("fonte_receita_id"),
                float(dados["valor"]),
                (dados.get("observacao") or "").strip(),
                id_,
            ),
        )


def excluir_lancamento(id_: int) -> None:
    """Remove um lançamento manual pelo id. Silencioso se não existir."""
    with conectar() as conn:
        conn.execute("DELETE FROM lancamentos_manuais WHERE id = ?", (id_,))


def _carregar(rows) -> list[LancamentoManual]:
    return [
        LancamentoManual(
            id=r["id"],
            data=r["data"],
            descricao=r["descricao"],
            tipo=r["tipo"],
            plano_conta_id=r["plano_conta_id"],
            fonte_receita_id=r["fonte_receita_id"],
            valor=r["valor"],
            observacao=r["observacao"] or "",
            nome_categoria=r["nome_categoria"] or "",
        )
        for r in rows
    ]


def listar_lancamentos_mes(mes: int, ano: int) -> list[LancamentoManual]:
    """Lista lançamentos manuais de um mês/ano específico (YYYY-MM)."""
    inicio = f"{ano:04d}-{mes:02d}-01"
    fim    = f"{ano + 1:04d}-01-01" if mes == 12 else f"{ano:04d}-{mes + 1:02d}-01"
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT lm.id, lm.data, lm.descricao, lm.tipo,
                   lm.plano_conta_id, lm.fonte_receita_id,
                   lm.valor, lm.observacao,
                   COALESCE(pc.nome, fr.nome, '') AS nome_categoria
              FROM lancamentos_manuais lm
              LEFT JOIN plano_contas    pc ON pc.id = lm.plano_conta_id
              LEFT JOIN fontes_receita  fr ON fr.id = lm.fonte_receita_id
             WHERE lm.data >= ? AND lm.data < ?
             ORDER BY lm.data, lm.id
            """,
            (inicio, fim),
        ).fetchall()
    return _carregar(rows)


def obter_lancamento(id_: int) -> Optional[LancamentoManual]:
    """Retorna um lançamento manual pelo id, ou None."""
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT lm.id, lm.data, lm.descricao, lm.tipo,
                   lm.plano_conta_id, lm.fonte_receita_id,
                   lm.valor, lm.observacao,
                   COALESCE(pc.nome, fr.nome, '') AS nome_categoria
              FROM lancamentos_manuais lm
              LEFT JOIN plano_contas    pc ON pc.id = lm.plano_conta_id
              LEFT JOIN fontes_receita  fr ON fr.id = lm.fonte_receita_id
             WHERE lm.id = ?
            """,
            (id_,),
        ).fetchone()
    if not row:
        return None
    return _carregar([row])[0]
