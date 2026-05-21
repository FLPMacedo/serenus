"""
catalogo.py — Catálogo de itens sugeridos para Compras de Casa.

Parseia uma vez o arquivo docs/Lista de itens de compras.txt (formato:
'Nome — Marca1, Marca2, Marca3.' em seções numeradas '1) Categoria')
e mantém em memória pra autocomplete no form_item.

API pública:
    listar_itens_sugeridos() -> list[dict] (nome, categoria, marcas)
    listar_marcas_sugeridas(nome_item) -> list[str]
    popular_marcas_iniciais() -> int  (seed para a 1ª execução)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from database import conectar

log = logging.getLogger(__name__)


_CAMINHO_TXT = (
    Path(__file__).parent.parent.parent / "docs" / "Lista de itens de compras.txt"
)

# Tokens que NÃO devem ser tratados como marca real (vêm em itens hortifruti,
# padaria, locais, marca do açougue etc.)
_TOKENS_NAO_MARCA = {
    "hortifruti", "padaria", "local", "marca do açougue",
    "padaria/local", "frigorífico regional", "frigorifico regional",
    "marcas regionais",
}


def _eh_marca_real(token: str) -> bool:
    t = token.strip().lower()
    if not t:
        return False
    if t in _TOKENS_NAO_MARCA:
        return False
    # tokens com / são padaria/local etc.
    if "/" in t and any(p in t for p in ("local", "regional", "padaria")):
        return False
    if "regional" in t and len(t.split()) <= 2:
        return False
    return True


def _parsear_linha_item(linha: str) -> dict | None:
    """Tenta extrair {nome, marcas} de uma linha do txt.

    Formatos aceitos:
        'Arroz branco — Camil, Tio João, Prato Fino.'
        'Arroz — marcas: Camil, Tio João.'
        'Tomate — hortifruti.'
        'Pão francês — padaria/local.'
    """
    # Divide por travessão "—" (U+2014) ou hífen normal
    m = re.match(r"^([^—\-]+)[—\-]\s*(.+?)\.?\s*$", linha)
    if not m:
        return None
    nome = m.group(1).strip()
    direita = m.group(2).strip()
    if not nome:
        return None

    # Remove prefixo "marcas:"
    direita = re.sub(r"^marcas?\s*:\s*", "", direita, flags=re.IGNORECASE)
    # Split por vírgula
    tokens = [t.strip() for t in direita.split(",") if t.strip()]
    marcas = [t for t in tokens if _eh_marca_real(t)]
    return {"nome": nome, "marcas": marcas}


@lru_cache(maxsize=1)
def listar_itens_sugeridos() -> list[dict]:
    """Lê o txt uma vez e devolve a lista de itens com categoria + marcas.

    Cache permanente (módulo-level via lru_cache) — chamado quantas vezes
    quiser, mas só parseia o arquivo na primeira chamada.
    """
    if not _CAMINHO_TXT.exists():
        log.warning("Catálogo não encontrado: %s", _CAMINHO_TXT)
        return []

    itens: list[dict] = []
    categoria_atual = "Outros"
    try:
        texto = _CAMINHO_TXT.read_text(encoding="utf-8")
    except Exception as e:
        log.warning("Falha lendo catálogo: %s", e)
        return []

    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue

        # Cabeçalho de seção: "1) Alimentos básicos e carboidratos"
        m_sec = re.match(r"^\d+\)\s*(.+)$", linha)
        if m_sec:
            categoria_atual = m_sec.group(1).strip()
            continue

        # Header do arquivo "Lista de 500 itens"
        if linha.lower().startswith("lista de "):
            continue

        parsed = _parsear_linha_item(linha)
        if parsed is None:
            continue
        parsed["categoria"] = categoria_atual
        itens.append(parsed)

    log.info("Catálogo: %d itens em %d categorias", len(itens),
              len({i["categoria"] for i in itens}))
    return itens


def listar_marcas_sugeridas(nome_item: str) -> list[str]:
    """Retorna as marcas pré-cadastradas no catálogo para esse item.
    Busca case-insensitive pelo nome exato."""
    if not nome_item:
        return []
    alvo = nome_item.strip().lower()
    for it in listar_itens_sugeridos():
        if it["nome"].lower() == alvo:
            return list(it["marcas"])
    return []


def _todas_marcas_do_catalogo() -> set[str]:
    """Set de TODAS as marcas únicas do catálogo (case-preserving).

    Usado pra popular_marcas_iniciais na 1ª execução.
    """
    todas: set[str] = set()
    for it in listar_itens_sugeridos():
        for m in it["marcas"]:
            todas.add(m)
    return todas


def popular_marcas_iniciais() -> int:
    """Insere as marcas do catálogo na tabela `marcas`.

    Idempotente: usa INSERT OR IGNORE (graças ao UNIQUE em marcas.nome).
    Retorna quantas linhas FORAM inseridas (excluindo as que já existiam).
    """
    marcas = _todas_marcas_do_catalogo()
    if not marcas:
        return 0
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM marcas")
        antes = cur.fetchone()[0]
        for nome in sorted(marcas):
            conn.execute(
                "INSERT OR IGNORE INTO marcas (nome, criado_em) VALUES (?, ?)",
                (nome, agora),
            )
        cur = conn.execute("SELECT COUNT(*) FROM marcas")
        depois = cur.fetchone()[0]
    return depois - antes
