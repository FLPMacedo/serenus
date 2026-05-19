"""
generico.py — Parser fallback heurístico de fatura PDF.

Tenta extrair linhas com padrão "DD/MM  descrição  R$ valor" ou
"DD MMM  descrição  valor". Não é confiável para totais ou parcelas —
use só quando nenhum parser específico reconhecer o layout.
"""

from __future__ import annotations

import re

from views.cartoes.pdf_parsers.base import PDFParser


# Captura linhas no formato "01/05 LOJA EXEMPLO  45,80" ou
# "12 MAR  AMAZON BR  R$ 199,90". Descrição: 4..60 chars de letras,
# números e separadores comuns. Valor BR com 2 decimais obrigatórios.
_PADRAO = re.compile(
    r"(?P<data>\d{1,2}[/ ][A-Za-z]{3}|\d{1,2}/\d{1,2})\s+"
    r"(?P<desc>[A-Za-zÀ-ÿ0-9*\.&\-'/ ]{4,60}?)\s+"
    r"(?:R\$\s*)?(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})",
    re.IGNORECASE,
)


class GenericoParser(PDFParser):
    """Fallback — sempre reconhece, mas pode extrair menos que parsers específicos."""

    nome_layout = "generico"

    def reconhece(self, texto: str) -> bool:
        return True  # sempre — é o último da fila

    def extrair(self, texto: str) -> list[dict]:
        itens: list[dict] = []
        for m in _PADRAO.finditer(texto):
            valor_str = m.group("valor").replace(".", "").replace(",", ".")
            try:
                valor = float(valor_str)
            except ValueError:
                continue
            if valor <= 0:
                continue
            itens.append({
                "descricao":       m.group("desc").strip(),
                "estabelecimento": "",
                "categoria":       "",
                "parcela":         "",
                "valor":           valor,
            })
        return itens
