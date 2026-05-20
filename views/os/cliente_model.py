"""
cliente_model.py — Cadastro de clientes do módulo OS.

Espelha o padrão dos models do projeto: dataclass + funções módulo-nível
(salvar/listar/obter/excluir/buscar), conexões via `conectar()` do
database.py, schema padronizado com os outros models do projeto.

Cliente tem FK opcional em ordens_servico.cliente_id — uma OS pode ter
solicitante texto-livre OU cliente cadastrado (ou ambos pra compat).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from database import conectar

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class Cliente:
    id:         int
    nome:       str
    documento:  str
    telefone:   str
    whatsapp:   str
    email:      str
    cep:        str
    endereco:   str
    observacao: str
    criado_em:  str


def _row_to_cliente(r) -> Cliente:
    d = dict(r)
    return Cliente(
        id=d["id"],
        nome=d["nome"],
        documento=d.get("documento") or "",
        telefone=d.get("telefone") or "",
        whatsapp=d.get("whatsapp") or "",
        email=d.get("email") or "",
        cep=d.get("cep") or "",
        endereco=d.get("endereco") or "",
        observacao=d.get("observacao") or "",
        criado_em=d["criado_em"],
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def salvar_cliente(dados: dict, id: int | None = None) -> int:
    """Cria ou atualiza um cliente. Retorna o id."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nome = (dados.get("nome") or "").strip()
    if not nome:
        raise ValueError("Nome do cliente é obrigatório.")
    with conectar() as conn:
        if id:
            conn.execute(
                "UPDATE clientes SET nome=?, documento=?, telefone=?, whatsapp=?,"
                " email=?, cep=?, endereco=?, observacao=? WHERE id=?",
                (
                    nome,
                    dados.get("documento", ""),
                    dados.get("telefone", ""),
                    dados.get("whatsapp", ""),
                    dados.get("email", ""),
                    dados.get("cep", ""),
                    dados.get("endereco", ""),
                    dados.get("observacao", ""),
                    id,
                ),
            )
            return id
        cur = conn.execute(
            "INSERT INTO clientes (nome, documento, telefone, whatsapp,"
            " email, cep, endereco, observacao, criado_em)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (
                nome,
                dados.get("documento", ""),
                dados.get("telefone", ""),
                dados.get("whatsapp", ""),
                dados.get("email", ""),
                dados.get("cep", ""),
                dados.get("endereco", ""),
                dados.get("observacao", ""),
                agora,
            ),
        )
        return cur.lastrowid


def obter_cliente(id: int) -> Optional[Cliente]:
    with conectar() as conn:
        row = conn.execute(
            "SELECT * FROM clientes WHERE id=?", (id,)
        ).fetchone()
    return _row_to_cliente(row) if row else None


def listar_clientes() -> list[Cliente]:
    """Lista todos ordenados alfabeticamente (case-insensitive)."""
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM clientes ORDER BY nome COLLATE NOCASE"
        ).fetchall()
    return [_row_to_cliente(r) for r in rows]


def excluir_cliente(id: int) -> tuple[bool, str]:
    """Remove um cliente. Bloqueia se houver OS vinculada (mesma sistemática
    de excluir_produto e excluir_conta)."""
    with conectar() as conn:
        usado = conn.execute(
            "SELECT COUNT(*) FROM ordens_servico WHERE cliente_id=?", (id,)
        ).fetchone()[0]
        if usado > 0:
            return False, (
                "Este cliente tem ordens de serviço vinculadas e não pode ser excluído. "
                "Exclua ou desvincule as OS antes."
            )
        conn.execute("DELETE FROM clientes WHERE id=?", (id,))
    return True, ""


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------

def buscar_clientes(texto: str | None) -> list[Cliente]:
    """Busca em nome, documento e email. Case-insensitive (LIKE).

    Texto vazio ou None retorna todos os clientes (mesmo que listar_clientes).
    Escapa os wildcards LIKE (% e _) do texto digitado pra que sejam tratados
    como caracteres literais.
    """
    if not texto:
        return listar_clientes()
    # Escapa wildcards do LIKE: \, %, _
    escapado = (texto.lower()
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_"))
    alvo = f"%{escapado}%"
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM clientes WHERE"
            " (LOWER(nome)      LIKE ? ESCAPE '\\'"
            " OR LOWER(documento) LIKE ? ESCAPE '\\'"
            " OR LOWER(email)     LIKE ? ESCAPE '\\')"
            " ORDER BY nome COLLATE NOCASE",
            (alvo, alvo, alvo),
        ).fetchall()
    return [_row_to_cliente(r) for r in rows]
