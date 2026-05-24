"""
base.py — Classe abstrata para parsers de extrato bancário.

Cada formato/banco (Nubank CSV, Nubank OFX, Itaú PDF, etc) tem um parser
próprio que implementa parse() e retorna lista de dicionários no formato:

    {
        "data":                "YYYY-MM-DD",
        "descricao":           str,
        "valor":               float,   # positivo=entrada, negativo=saída
        "identificador_unico": str,     # do banco (UUID/FITID) ou hash gerado
    }

Esses dicts são consumidos por extrato_banco_model.importar() que insere
no banco com dedup baseado em (conta_banco_id, identificador_unico).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ExtratoParser(ABC):
    """Estratégia para extrair lançamentos de um arquivo de extrato.

    Atributos:
        nome_formato: identificador curto ('nubank_csv', 'itau_pdf', ...).
        extensoes:    extensões de arquivo suportadas ('.csv', '.pdf').
    """

    nome_formato: str = "desconhecido"
    extensoes:    tuple[str, ...] = ()

    @abstractmethod
    def parse(self, caminho: str | Path) -> list[dict]:
        """Lê o arquivo e retorna lista de lançamentos.

        Cada item DEVE conter: data, descricao, valor, identificador_unico.
        """
        ...

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} formato={self.nome_formato!r}>"
