"""
casa_model.py — Model do módulo Compras de Casa.

MVP: cadastro de itens de estoque doméstico, ajuste de estoque atual
(set absoluto ou delta), e geração automática da lista de compras
(itens onde estoque_atual <= estoque_minimo, ignorando itens sem
controle de mínimo).

Sem histórico de movimentações nesta versão — decisão do usuário no
plano inicial (MVP). Pode ser adicionado em v2 com tabela
movimentacoes_estoque.
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
class ItemEstoque:
    id:              int
    nome:            str
    categoria:       str
    unidade:         str
    marca:           str
    estoque_atual:   float
    estoque_minimo:  float
    observacao:      str
    ativo:           bool
    criado_em:       str

    @property
    def precisa_repor(self) -> bool:
        """True se estoque atual está no/abaixo do mínimo (e mínimo > 0)."""
        return self.estoque_minimo > 0 and self.estoque_atual <= self.estoque_minimo

    @property
    def quantidade_a_comprar(self) -> float:
        """Quanto comprar para alcançar o mínimo (zero se não precisa)."""
        diff = self.estoque_minimo - self.estoque_atual
        return max(0.0, round(diff, 4))


def _row_to_item(r) -> ItemEstoque:
    d = dict(r)
    return ItemEstoque(
        id=d["id"],
        nome=d["nome"],
        categoria=d.get("categoria") or "",
        unidade=d.get("unidade") or "",
        marca=d.get("marca") or "",
        estoque_atual=float(d.get("estoque_atual") or 0),
        estoque_minimo=float(d.get("estoque_minimo") or 0),
        observacao=d.get("observacao") or "",
        ativo=bool(d.get("ativo", 1)),
        criado_em=d["criado_em"],
    )


# ---------------------------------------------------------------------------
# Marcas — catalogo global (find-or-create, case-insensitive)
# ---------------------------------------------------------------------------

@dataclass
class Marca:
    id:        int
    nome:      str
    criado_em: str


def _row_to_marca(r) -> Marca:
    d = dict(r)
    return Marca(id=d["id"], nome=d["nome"], criado_em=d["criado_em"])


def salvar_marca(nome: str) -> int:
    """Cria a marca se não existir, ou devolve o id da existente
    (find-or-create, case-insensitive).

    Retorna 0 se o nome for vazio (no-op silencioso) — caller pode
    confiar que id>0 sempre significa marca real.
    """
    n = (nome or "").strip()
    if not n:
        return 0
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        # Primeiro tenta achar (case-insensitive)
        row = conn.execute(
            "SELECT id FROM marcas WHERE LOWER(nome) = LOWER(?)", (n,)
        ).fetchone()
        if row:
            return int(row["id"])
        cur = conn.execute(
            "INSERT INTO marcas (nome, criado_em) VALUES (?, ?)", (n, agora),
        )
        return cur.lastrowid


def listar_marcas() -> list["Marca"]:
    """Todas as marcas em ordem alfabética case-insensitive."""
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM marcas ORDER BY nome COLLATE NOCASE"
        ).fetchall()
    return [_row_to_marca(r) for r in rows]


def buscar_marcas(prefixo: str) -> list["Marca"]:
    """Marcas cujo nome começa com `prefixo` (case-insensitive).
    Útil pra autocomplete no form."""
    p = (prefixo or "").strip().lower()
    if not p:
        return listar_marcas()
    # Escapa wildcards do LIKE
    seguro = p.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM marcas WHERE LOWER(nome) LIKE ? ESCAPE '\\'"
            " ORDER BY nome COLLATE NOCASE",
            (f"{seguro}%",),
        ).fetchall()
    return [_row_to_marca(r) for r in rows]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def salvar_item(dados: dict, id: int | None = None) -> int:
    """Cria ou atualiza um item de estoque. Retorna o id."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nome = (dados.get("nome") or "").strip()
    if not nome:
        raise ValueError("Nome do item é obrigatório.")
    estoque_atual  = float(dados.get("estoque_atual", 0) or 0)
    estoque_minimo = float(dados.get("estoque_minimo", 0) or 0)
    if estoque_atual < 0:
        raise ValueError("Estoque atual não pode ser negativo.")
    if estoque_minimo < 0:
        raise ValueError("Estoque mínimo não pode ser negativo.")

    marca = (dados.get("marca") or "").strip()
    # Se a marca for nova, persiste no catálogo (find-or-create)
    if marca:
        salvar_marca(marca)

    with conectar() as conn:
        if id:
            conn.execute(
                "UPDATE itens_estoque SET nome=?, categoria=?, unidade=?,"
                " marca=?, estoque_atual=?, estoque_minimo=?, observacao=?, ativo=?"
                " WHERE id=?",
                (
                    nome,
                    dados.get("categoria", ""),
                    dados.get("unidade", ""),
                    marca,
                    estoque_atual,
                    estoque_minimo,
                    dados.get("observacao", ""),
                    int(bool(dados.get("ativo", True))),
                    id,
                ),
            )
            return id
        cur = conn.execute(
            "INSERT INTO itens_estoque (nome, categoria, unidade, marca,"
            " estoque_atual, estoque_minimo, observacao, ativo, criado_em)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (
                nome,
                dados.get("categoria", ""),
                dados.get("unidade", ""),
                marca,
                estoque_atual,
                estoque_minimo,
                dados.get("observacao", ""),
                int(bool(dados.get("ativo", True))),
                agora,
            ),
        )
        return cur.lastrowid


def obter_item(id: int) -> Optional[ItemEstoque]:
    with conectar() as conn:
        row = conn.execute(
            "SELECT * FROM itens_estoque WHERE id=?", (id,)
        ).fetchone()
    return _row_to_item(row) if row else None


def listar_itens(incluir_inativos: bool = False,
                  categoria: str | None = None,
                  busca: str | None = None) -> list[ItemEstoque]:
    """Lista itens ordenados alfabeticamente (case-insensitive).

    - incluir_inativos: por padrão lista só ativos
    - categoria: filtra por categoria exata
    - busca: LIKE case-insensitive em nome (filtragem em Python)
    """
    sql    = "SELECT * FROM itens_estoque"
    conds  = []
    params: list = []
    if not incluir_inativos:
        conds.append("ativo = 1")
    if categoria:
        conds.append("categoria = ?")
        params.append(categoria)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY nome COLLATE NOCASE"
    with conectar() as conn:
        rows = conn.execute(sql, params).fetchall()
    itens = [_row_to_item(r) for r in rows]
    if busca:
        b = busca.lower()
        itens = [i for i in itens if b in i.nome.lower()]
    return itens


def excluir_item(id: int) -> tuple[bool, str]:
    """Exclui o item. itens_estoque não tem FKs externas, então o delete
    sempre passa — assinatura (bool, str) por consistência com outros
    excluir_* do projeto (futuro: poderia ter FK para movimentacoes)."""
    with conectar() as conn:
        conn.execute("DELETE FROM itens_estoque WHERE id=?", (id,))
    return True, ""


# ---------------------------------------------------------------------------
# Ajuste de estoque
# ---------------------------------------------------------------------------

def ajustar_estoque(id: int,
                     novo_valor: float | None = None,
                     delta: float | None = None) -> None:
    """Ajusta o estoque_atual de um item.

    - novo_valor: define o estoque como esse valor exato (não pode ser <0)
    - delta: soma esse valor ao estoque atual; clampa em 0 (não vai negativo)

    Exatamente uma das opções deve ser passada.
    """
    if (novo_valor is None) == (delta is None):
        raise ValueError("Passe exatamente um de novo_valor ou delta.")

    with conectar() as conn:
        atual = conn.execute(
            "SELECT estoque_atual FROM itens_estoque WHERE id=?", (id,)
        ).fetchone()
        if atual is None:
            return  # item não existe — no-op
        if novo_valor is not None:
            if novo_valor < 0:
                raise ValueError("Estoque não pode ser negativo.")
            valor = float(novo_valor)
        else:
            valor = max(0.0, float(atual["estoque_atual"]) + float(delta))
        conn.execute(
            "UPDATE itens_estoque SET estoque_atual=? WHERE id=?",
            (round(valor, 4), id),
        )


# ---------------------------------------------------------------------------
# Lista de compras
# ---------------------------------------------------------------------------

def listar_lista_compras() -> list[ItemEstoque]:
    """Itens que precisam ser comprados: ativos, com estoque_minimo > 0
    e estoque_atual <= estoque_minimo. Ordenados alfabeticamente."""
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM itens_estoque"
            " WHERE ativo = 1 AND estoque_minimo > 0"
            " AND estoque_atual <= estoque_minimo"
            " ORDER BY nome COLLATE NOCASE"
        ).fetchall()
    return [_row_to_item(r) for r in rows]
