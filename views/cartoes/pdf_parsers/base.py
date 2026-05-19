"""
base.py — Classe abstrata para parsers de PDF de fatura.

Cada layout (Nubank, Itaú, Inter, Digio, etc.) deve herdar de PDFParser
e implementar reconhece() e extrair(). Os parsers ficam em arquivos
separados (nubank.py, itau.py, ...) e são registrados em __init__.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PDFParser(ABC):
    """Estratégia para extrair itens de fatura de um layout específico.

    Atributos:
        nome_layout: identificador curto ('nubank', 'itau_visa', 'generico', ...).
                     Usado em logs e mensagens.

    Métodos:
        reconhece(texto): True se este parser sabe ler o layout.
        extrair(texto):   lista de dicts no schema padrão da pipeline
                          {descricao, estabelecimento, categoria, parcela, valor}.
    """

    nome_layout: str = "desconhecido"

    @abstractmethod
    def reconhece(self, texto: str) -> bool:
        """Determina se este parser identifica o layout do texto fornecido."""
        ...

    @abstractmethod
    def extrair(self, texto: str) -> list[dict]:
        """Extrai itens. Cada item: descricao, estabelecimento, categoria, parcela, valor."""
        ...

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} layout={self.nome_layout!r}>"
