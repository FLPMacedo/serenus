"""
regras_categoria_model.py — Regras de categorização automática.

Cada regra mapeia um padrão de texto (substring case-insensitive) para uma
categoria fixa, separado por tipo (entrada/saída):

  Regra: padrão='LANCHONETE'    tipo=saida   → plano_conta_id=alimentação
  Regra: padrão='REMUNERACAO'   tipo=entrada → fonte_receita_id=salário_clt

Quando o extrato é importado, casar_regras() é chamado para cada lançamento
e preenche o campo de categoria correspondente. Lançamentos sem match ficam
sem categoria e o usuário categoriza depois manualmente.

Casamento:
  - 'padrão' é uma substring case-insensitive (NÃO regex).
  - 'tipo' filtra: regras de saída só se aplicam a valores negativos, e
    regras de entrada só a valores positivos.
  - Se múltiplas regras casam o mesmo lançamento, vence a de maior
    prioridade. Empate de prioridade: vence a mais recente (maior id).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from database import conectar

log = logging.getLogger(__name__)


_TIPOS_VALIDOS = {"entrada", "saida"}


@dataclass
class RegraCategoria:
    id:               int
    padrao:           str
    tipo:             str
    plano_conta_id:   Optional[int]
    fonte_receita_id: Optional[int]
    prioridade:       int
    ativa:            bool
    nome_categoria:   str        # resolvido via JOIN


def _validar(dados: dict) -> None:
    padrao = (dados.get("padrao") or "").strip()
    if not padrao:
        raise ValueError("padrão é obrigatório")

    tipo = dados.get("tipo")
    if tipo not in _TIPOS_VALIDOS:
        raise ValueError(f"tipo inválido: {tipo!r}")

    plano = dados.get("plano_conta_id")
    fonte = dados.get("fonte_receita_id")
    if tipo == "saida":
        if not plano:
            raise ValueError("saída exige plano_conta_id")
        if fonte:
            raise ValueError("saída não deve ter fonte_receita_id")
    else:
        if not fonte:
            raise ValueError("entrada exige fonte_receita_id")
        if plano:
            raise ValueError("entrada não deve ter plano_conta_id")


def salvar_regra(dados: dict) -> int:
    """Cria uma regra. Retorna o id."""
    _validar(dados)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute(
            """
            INSERT INTO regras_categoria
                (padrao, tipo, plano_conta_id, fonte_receita_id,
                 prioridade, ativa, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados["padrao"].strip(),
                dados["tipo"],
                dados.get("plano_conta_id"),
                dados.get("fonte_receita_id"),
                int(dados.get("prioridade", 0)),
                1 if dados.get("ativa", True) else 0,
                agora,
            ),
        )
        return cur.lastrowid


def atualizar_regra(id_: int, dados: dict) -> None:
    _validar(dados)
    with conectar() as conn:
        conn.execute(
            """
            UPDATE regras_categoria
               SET padrao           = ?,
                   tipo             = ?,
                   plano_conta_id   = ?,
                   fonte_receita_id = ?,
                   prioridade       = ?,
                   ativa            = ?
             WHERE id = ?
            """,
            (
                dados["padrao"].strip(),
                dados["tipo"],
                dados.get("plano_conta_id"),
                dados.get("fonte_receita_id"),
                int(dados.get("prioridade", 0)),
                1 if dados.get("ativa", True) else 0,
                id_,
            ),
        )


def excluir_regra(id_: int) -> None:
    with conectar() as conn:
        conn.execute("DELETE FROM regras_categoria WHERE id = ?", (id_,))


def _carregar(rows) -> list[RegraCategoria]:
    return [
        RegraCategoria(
            id=r["id"],
            padrao=r["padrao"],
            tipo=r["tipo"],
            plano_conta_id=r["plano_conta_id"],
            fonte_receita_id=r["fonte_receita_id"],
            prioridade=r["prioridade"] or 0,
            ativa=bool(r["ativa"]),
            nome_categoria=r["nome_categoria"] or "",
        )
        for r in rows
    ]


def listar_regras(apenas_ativas: bool = False) -> list[RegraCategoria]:
    where = "WHERE rc.ativa = 1" if apenas_ativas else ""
    with conectar() as conn:
        rows = conn.execute(
            f"""
            SELECT rc.*,
                   COALESCE(pc.nome, fr.nome, '') AS nome_categoria
              FROM regras_categoria rc
              LEFT JOIN plano_contas    pc ON pc.id = rc.plano_conta_id
              LEFT JOIN fontes_receita  fr ON fr.id = rc.fonte_receita_id
              {where}
             ORDER BY rc.prioridade DESC, rc.id DESC
            """
        ).fetchall()
    return _carregar(rows)


def casar_regras(itens: list[dict]) -> list[dict]:
    """Aplica regras ativas a uma lista de itens (dicts) do extrato.

    Cada item recebe plano_conta_id ou fonte_receita_id preenchido se alguma
    regra casa. Mutação não destrutiva: retorna nova lista com cópias.

    O tipo da regra (entrada/saida) é cruzado com o sinal do valor:
      - valor > 0  → só regras tipo='entrada'
      - valor < 0  → só regras tipo='saida'
    """
    regras = listar_regras(apenas_ativas=True)
    if not regras:
        return [dict(i) for i in itens]

    # Pré-divide regras por tipo, mantendo ordem (já vem por prioridade DESC)
    regras_entrada = [r for r in regras if r.tipo == "entrada"]
    regras_saida   = [r for r in regras if r.tipo == "saida"]

    resultado: list[dict] = []
    for item in itens:
        novo = dict(item)
        valor = float(novo.get("valor", 0.0))
        desc_lower = (novo.get("descricao") or "").lower()

        candidatas = regras_entrada if valor > 0 else regras_saida
        for r in candidatas:
            if r.padrao.lower() in desc_lower:
                if valor > 0:
                    novo["fonte_receita_id"] = r.fonte_receita_id
                else:
                    novo["plano_conta_id"] = r.plano_conta_id
                break  # primeira regra que casa (já está ordenada por prioridade)

        resultado.append(novo)

    return resultado
