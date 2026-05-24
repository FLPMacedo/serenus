"""
mercadolivre.py — Parser do PDF de fatura Cartão Mercado Pago / Mercado Livre.

Layout do PDF (extraído via pypdf):

  Movimentações na fatura                <- seção a IGNORAR (pagamentos, juros)
  Data Movimentações Valor em R$
  16/04 Pagamento da fatura de abril/2026 R$ 2.574,20
  10/05 Juros de mora R$ 0,86
  ...

  Cartão Visa [************9812]         <- inclui (compras)
  Data Movimentações Valor em R$
  13/01 MERCADOLIVRE*5PRODUTOS Parcela 16 de 18 R$ 57,68
  13/05 MP*4PRODUTOS Parcela 12 de 12 R$ 93,06
  11/04 FARMACIA INDIANA 98 PO R$ 85,14
  Total R$ 1.407,67                      <- fim da tabela

  Cartão Visa [************6232]         <- segundo cartão, continua incluindo
  ...

Cabeçalho "Cartão Visa [...]" e "Total R$ ..." podem se repetir em cada página,
mas as transações em si não duplicam.

Marcador único: "Mercado Pago" (CNPJ emissor) ou padrão MERCADOLIVRE*/MP*.
"""

from __future__ import annotations

import logging
import re

from views.cartoes.pdf_parsers.base import PDFParser

log = logging.getLogger(__name__)


_MARCADOR_ML = re.compile(
    r"Mercado\s+Pago|MERCADOLIVRE\*",
    re.IGNORECASE,
)

# Início de tabela de compras (cartão)
_INICIO_CARTAO = re.compile(
    r"^Cart[ãa]o\s+(?:Visa|Master|Mastercard)\b",
    re.IGNORECASE,
)

# Início de tabela de pagamentos (ignorar)
_INICIO_MOVIMENTACOES = re.compile(
    r"^Movimenta[çc][õo]es\s+na\s+fatura",
    re.IGNORECASE,
)

# Cabeçalho de tabela (pular)
_HEADER_TABELA = re.compile(r"^Data\s+Movimenta", re.IGNORECASE)

# Fim de tabela (Total R$ ...) — encerra captura
_FIM_TABELA = re.compile(r"^Total\s+R\$", re.IGNORECASE)

# Transação: DD/MM DESCRICAO [Parcela X de Y] R$ valor
_TRANSACAO = re.compile(
    r"^(?P<data>\d{2}/\d{2})\s+"
    r"(?P<desc>.+?)"
    r"(?:\s+Parcela\s+(?P<parc_n>\d+)\s+de\s+(?P<parc_m>\d+))?"
    r"\s+R\$\s*(?P<valor>-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
)


def _parse_valor_br(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


class MercadoLivreParser(PDFParser):
    """Parser do PDF de fatura Cartão Mercado Pago."""

    nome_layout = "mercadolivre"

    def reconhece(self, texto: str) -> bool:
        return bool(_MARCADOR_ML.search(texto))

    def extrair(self, texto: str) -> list[dict]:
        itens: list[dict] = []
        # Estados: None (fora), "cartao" (capturar), "movimentacoes" (pular)
        modo: str | None = None
        vistos: set[tuple] = set()  # dedup por (data, desc, parcela, valor)

        for linha in texto.splitlines():
            s = linha.strip()
            if not s:
                continue

            if _INICIO_CARTAO.match(s):
                modo = "cartao"
                continue
            if _INICIO_MOVIMENTACOES.match(s):
                modo = "movimentacoes"
                continue
            if _FIM_TABELA.match(s):
                modo = None
                continue
            if _HEADER_TABELA.match(s):
                continue
            if modo != "cartao":
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

            parcela_str = ""
            if m.group("parc_n") and m.group("parc_m"):
                parcela_str = f"{m.group('parc_n')}/{m.group('parc_m')}"

            chave = (m.group("data"), descricao, parcela_str, round(valor, 2))
            if chave in vistos:
                continue
            vistos.add(chave)

            itens.append({
                "descricao":       descricao,
                "estabelecimento": "",
                "categoria":       "",
                "parcela":         parcela_str,
                "valor":           round(valor, 2),
            })

        log.info("MercadoLivreParser.extrair: %d itens encontrados", len(itens))
        return itens
