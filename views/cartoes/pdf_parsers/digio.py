"""
digio.py — Parser do PDF de fatura Digio.

Layout do PDF (extraído via pypdf):

  Demonstrativo - 11/04/26 a 08/05/26
  Digio físico Final 6359 - Filipe
  Gold
  Data Descrição Parcela Valor (R$)
  19/04/2026 SUPERMERCADO POUPY 1/2 142,48
  22/04/2026 MS AGROPECUARIA 50,00
  06/05/2026 SOLANGE MODAS 1/3 88,30

Datas vêm com ano completo (DD/MM/AAAA), valores sem prefixo R$.
Marcador único: "digio.com.br" ou "Cartão Digio" (não aparecem em outros).
"""

from __future__ import annotations

import logging
import re

from views.cartoes.pdf_parsers.base import PDFParser

log = logging.getLogger(__name__)


_MARCADOR_DIGIO = re.compile(r"digio\.com\.br|Cart[ãa]o Digio", re.IGNORECASE)

# Demonstrativo: marca o início da seção de transações
_INICIO_DEMONSTRATIVO = re.compile(r"^Demonstrativo\s*-", re.IGNORECASE)

# Linhas que terminam a seção (totais, rodapé, próxima fatura)
_FIM_CAPTURA = re.compile(
    r"^(?:Total de juros|Sobre essas opera|Taxas e cobran|Detalhe de parcelamento"
    r"|Central de Relacionamento|Boleto banc|Pr[óo]xima fatura"
    r"|Demais faturas|Pagamento m[íi]nimo|Encargos)",
    re.IGNORECASE,
)

# DD/MM/AAAA DESC [N/M] VALOR
_TRANSACAO = re.compile(
    r"^(?P<data>\d{2}/\d{2}/\d{4})\s+"
    r"(?P<desc>.+?)"
    r"(?:\s+(?P<parcela>\d{1,2}/\d{1,2}))?"
    r"\s+(?P<valor>-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
)


def _parse_valor_br(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


class DigioParser(PDFParser):
    """Parser do PDF de fatura Digio."""

    nome_layout = "digio"

    def reconhece(self, texto: str) -> bool:
        return bool(_MARCADOR_DIGIO.search(texto))

    def extrair(self, texto: str) -> list[dict]:
        itens: list[dict] = []
        em_demonstrativo = False

        for linha in texto.splitlines():
            s = linha.strip()
            if not s:
                continue

            if _INICIO_DEMONSTRATIVO.match(s):
                em_demonstrativo = True
                continue

            if em_demonstrativo and _FIM_CAPTURA.match(s):
                em_demonstrativo = False
                continue

            if not em_demonstrativo:
                continue

            m = _TRANSACAO.match(s)
            if not m:
                continue

            valor = _parse_valor_br(m.group("valor"))
            if valor <= 0:
                continue

            descricao = m.group("desc").strip()
            descricao = re.sub(r"\s+", " ", descricao)
            if not descricao:
                continue

            parcela_str = m.group("parcela") or ""

            itens.append({
                "descricao":       descricao,
                "estabelecimento": "",
                "categoria":       "",
                "parcela":         parcela_str,
                "valor":           round(valor, 2),
            })

        log.info("DigioParser.extrair: %d itens encontrados", len(itens))
        return itens
