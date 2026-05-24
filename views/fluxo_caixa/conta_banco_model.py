"""
conta_banco_model.py — CRUD de contas bancárias do usuário.

Conta bancária = onde o usuário tem dinheiro físico/digital (conta corrente
Nubank, conta Itaú, poupança Caixa, etc). Cada conta tem extratos que podem
ser importados em PDF/CSV/OFX, gerando linhas em lancamentos_banco.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from database import conectar

log = logging.getLogger(__name__)


_TIPOS_VALIDOS = {"corrente", "poupanca", "digital", "salario", "outra"}


@dataclass
class ContaBanco:
    id:            int
    nome:          str
    banco:         str
    tipo:          str          # corrente | poupanca | digital | salario | outra
    agencia:       str
    numero:        str
    saldo_inicial: float
    ativa:         bool


def _validar(dados: dict) -> None:
    nome = (dados.get("nome") or "").strip()
    if not nome:
        raise ValueError("nome da conta é obrigatório")
    tipo = dados.get("tipo", "corrente")
    if tipo not in _TIPOS_VALIDOS:
        raise ValueError(f"tipo inválido: {tipo!r}")


def salvar_conta(dados: dict) -> int:
    """Cria uma conta bancária. Retorna o id."""
    _validar(dados)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute(
            """
            INSERT INTO contas_banco
                (nome, banco, tipo, agencia, numero, saldo_inicial, ativa, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados["nome"].strip(),
                (dados.get("banco") or "").strip(),
                dados.get("tipo", "corrente"),
                (dados.get("agencia") or "").strip(),
                (dados.get("numero") or "").strip(),
                float(dados.get("saldo_inicial") or 0.0),
                1 if dados.get("ativa", True) else 0,
                agora,
            ),
        )
        log.info("Conta banco criada: id=%s nome=%s", cur.lastrowid, dados["nome"])
        return cur.lastrowid


def atualizar_conta(id_: int, dados: dict) -> None:
    """Atualiza conta bancária. Mesmas validações de salvar."""
    _validar(dados)
    with conectar() as conn:
        conn.execute(
            """
            UPDATE contas_banco
               SET nome          = ?,
                   banco         = ?,
                   tipo          = ?,
                   agencia       = ?,
                   numero        = ?,
                   saldo_inicial = ?,
                   ativa         = ?
             WHERE id = ?
            """,
            (
                dados["nome"].strip(),
                (dados.get("banco") or "").strip(),
                dados.get("tipo", "corrente"),
                (dados.get("agencia") or "").strip(),
                (dados.get("numero") or "").strip(),
                float(dados.get("saldo_inicial") or 0.0),
                1 if dados.get("ativa", True) else 0,
                id_,
            ),
        )


def excluir_conta(id_: int) -> tuple[bool, str]:
    """Exclui conta bancária. ON DELETE CASCADE remove lancamentos_banco.

    Retorna (sucesso, mensagem). Sucesso=False se há contas_pagar/receita
    conciliadas que perderiam o vínculo (FK check). Hoje só checa se foi
    deletada.
    """
    with conectar() as conn:
        cur = conn.execute("DELETE FROM contas_banco WHERE id = ?", (id_,))
        if cur.rowcount == 0:
            return False, "Conta não encontrada."
    return True, "Conta excluída."


def _carregar(rows) -> list[ContaBanco]:
    return [
        ContaBanco(
            id=r["id"],
            nome=r["nome"],
            banco=r["banco"] or "",
            tipo=r["tipo"],
            agencia=r["agencia"] or "",
            numero=r["numero"] or "",
            saldo_inicial=r["saldo_inicial"] or 0.0,
            ativa=bool(r["ativa"]),
        )
        for r in rows
    ]


def listar_contas(apenas_ativas: bool = False) -> list[ContaBanco]:
    """Lista contas bancárias cadastradas."""
    where = "WHERE ativa = 1" if apenas_ativas else ""
    with conectar() as conn:
        rows = conn.execute(
            f"SELECT * FROM contas_banco {where} ORDER BY nome"
        ).fetchall()
    return _carregar(rows)


def obter_conta(id_: int) -> Optional[ContaBanco]:
    """Retorna conta por id, ou None."""
    with conectar() as conn:
        row = conn.execute(
            "SELECT * FROM contas_banco WHERE id = ?", (id_,)
        ).fetchone()
    if not row:
        return None
    return _carregar([row])[0]


def saldo_atual_conta(id_: int) -> float:
    """Saldo inicial + soma dos lancamentos_banco da conta."""
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT cb.saldo_inicial + COALESCE(SUM(lb.valor), 0.0) AS saldo
              FROM contas_banco cb
              LEFT JOIN lancamentos_banco lb ON lb.conta_banco_id = cb.id
             WHERE cb.id = ?
             GROUP BY cb.id
            """,
            (id_,),
        ).fetchone()
    return round(row["saldo"] if row else 0.0, 2)
