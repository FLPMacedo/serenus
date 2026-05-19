"""
Registry de parsers de PDF de fatura.

Parsers específicos (NubankParser, ItauParser, etc.) ficam à frente do
GenericoParser na ordem de detecção, garantindo que o fallback seja
sempre o último a ser consultado.

Uso:
    from views.cartoes.pdf_parsers import detectar_layout
    parser = detectar_layout(texto)
    itens = parser.extrair(texto)
"""

from __future__ import annotations

from views.cartoes.pdf_parsers.base import PDFParser
from views.cartoes.pdf_parsers.generico import GenericoParser


# Lista mutável de parsers em ordem de prioridade.
# O parser GenericoParser é o último (fallback).
_PARSERS: list[PDFParser] = [GenericoParser()]


def registrar(parser: PDFParser) -> None:
    """Adiciona um parser ao registry.

    Parsers específicos são inseridos antes do GenericoParser para que ele
    permaneça como fallback final. Re-registrar um nome_layout substitui
    o anterior (idempotente).

    Importante: mutação **in-place** de _PARSERS — testes e outros consumidores
    podem capturar a referência uma vez e ainda ver as alterações.
    """
    # Remove existente com mesmo nome_layout (mutação in-place)
    _PARSERS[:] = [p for p in _PARSERS if p.nome_layout != parser.nome_layout]

    if parser.nome_layout == "generico":
        _PARSERS.append(parser)
    else:
        idx_generico = next(
            (i for i, p in enumerate(_PARSERS) if p.nome_layout == "generico"),
            len(_PARSERS),
        )
        _PARSERS.insert(idx_generico, parser)


def todos_parsers() -> list[PDFParser]:
    """Retorna cópia dos parsers registrados na ordem de prioridade."""
    return list(_PARSERS)


def detectar_layout(texto: str) -> PDFParser:
    """Retorna o primeiro parser que reconhece o texto.

    GenericoParser é o fallback final (sempre reconhece). Se por algum motivo
    a lista de parsers estiver vazia, levanta PDFLayoutDesconhecidoError.
    """
    for p in _PARSERS:
        if p.reconhece(texto):
            return p
    from views.cartoes.importar_fatura_pdf_model import PDFLayoutDesconhecidoError
    raise PDFLayoutDesconhecidoError("Nenhum parser reconheceu o layout do PDF.")
