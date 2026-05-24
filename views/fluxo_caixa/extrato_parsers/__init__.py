"""
Registry de parsers de extrato bancário.

Cada parser sabe um formato específico (Nubank CSV, OFX; Itaú PDF; etc).
Uso típico:

    from views.fluxo_caixa.extrato_parsers import detectar_parser
    parser = detectar_parser("extrato.csv", banco="nubank")
    itens = parser.parse("extrato.csv")
"""

from __future__ import annotations

from pathlib import Path

from views.fluxo_caixa.extrato_parsers.base import ExtratoParser
from views.fluxo_caixa.extrato_parsers.itau_pdf import ItauPDFParser
from views.fluxo_caixa.extrato_parsers.nubank_csv import NubankCSVParser
from views.fluxo_caixa.extrato_parsers.nubank_ofx import NubankOFXParser


# Lista de parsers conhecidos. Adicionar novos aqui ao implementar (Bradesco,
# Santander, Caixa, etc).
_PARSERS: list[ExtratoParser] = [
    NubankCSVParser(),
    NubankOFXParser(),
    ItauPDFParser(),
]


def todos_parsers() -> list[ExtratoParser]:
    """Retorna cópia da lista de parsers em ordem de registro."""
    return list(_PARSERS)


def registrar(parser: ExtratoParser) -> None:
    """Adiciona um parser ao registry (mutação in-place)."""
    _PARSERS[:] = [p for p in _PARSERS if p.nome_formato != parser.nome_formato]
    _PARSERS.append(parser)


def detectar_parser(caminho: str | Path,
                    banco: str | None = None) -> ExtratoParser | None:
    """Detecta o parser apropriado para o arquivo.

    Estratégia:
      1. Filtra parsers compatíveis com a extensão do arquivo.
      2. Se `banco` foi informado (ex: 'nubank', 'itau'), prefere parsers
         cujo nome_formato contém o banco.
      3. Se houver mais de um candidato e nenhum filtro de banco, retorna
         o primeiro.
      4. Retorna None se nenhum parser bate.
    """
    ext = Path(caminho).suffix.lower()
    candidatos = [p for p in _PARSERS if ext in p.extensoes]
    if not candidatos:
        return None

    if banco:
        banco_l = banco.lower()
        preferidos = [p for p in candidatos if banco_l in p.nome_formato.lower()]
        if preferidos:
            return preferidos[0]

    return candidatos[0]
