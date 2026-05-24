"""
will.py — Parser do PDF de fatura Will Bank.

Layout do PDF (extraído via pypdf):

  Gastos
  Parcelamentos
  Lançamentos em parcelas cobradas mês a mês.
  R$ 16,58
  <linha vazia>
  IG*edzcronogra Parcela 4 de 12 12/04/2026
   Cartão 6458 R$ 16,58
  Recebidos               <- a partir daqui é pagamento/crédito, ignorar
  Valores recebidos
  ...
  PAG FATURA COM PIX 15/04/2026 +R$ 564,01

Cada compra ocupa duas linhas:
  Linha N:   "<desc> [Parcela X de Y] DD/MM/AAAA"
  Linha N+1: " Cartão NNNN R$ valor"

Marcador único: "Will Financeira" ou "willbank.com.br" (CNPJ do emissor).
"""

from __future__ import annotations

import logging
import re

from views.cartoes.pdf_parsers.base import PDFParser

log = logging.getLogger(__name__)


_MARCADOR_WILL = re.compile(
    r"Will\s+Financeira|willbank\.com\.br",
    re.IGNORECASE,
)

# Início da seção de compras (gastos)
_INICIO_GASTOS = re.compile(r"^\s*Gastos\s*$", re.IGNORECASE)

# Fim da seção de gastos — pulamos pagamentos e tudo que vem depois
_FIM_GASTOS = re.compile(
    r"^\s*(?:Recebidos|Os valores em detalhes|Pr[óo]xima fatura|Tim-tim"
    r"|Limites de cr[ée]dito|Encargos cobrados|Formas de pagamento)",
    re.IGNORECASE,
)

# Linha com descrição + parcela opcional + data no final
_LINHA_DESC = re.compile(
    r"^(?P<desc>.+?)"
    r"(?:\s+Parcela\s+(?P<parc_n>\d+)\s+de\s+(?P<parc_m>\d+))?"
    r"\s+(?P<data>\d{2}/\d{2}/\d{4})\s*$"
)

# Linha com cartão + R$ valor (sem o "+" — esse é pagamento, ignorar)
_LINHA_CARTAO_VALOR = re.compile(
    r"^\s*Cart[ãa]o\s+\d+\s+R\$\s*(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})\s*$",
    re.IGNORECASE,
)


def _parse_valor_br(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


class WillParser(PDFParser):
    """Parser do PDF de fatura Will Bank."""

    nome_layout = "will"

    def reconhece(self, texto: str) -> bool:
        return bool(_MARCADOR_WILL.search(texto))

    def extrair(self, texto: str) -> list[dict]:
        linhas = texto.splitlines()
        itens: list[dict] = []
        em_gastos = False
        i = 0

        while i < len(linhas):
            s = linhas[i].strip()

            if _INICIO_GASTOS.match(s):
                em_gastos = True
                i += 1
                continue

            if em_gastos and _FIM_GASTOS.match(s):
                em_gastos = False
                i += 1
                continue

            if not em_gastos or not s:
                i += 1
                continue

            m_desc = _LINHA_DESC.match(s)
            if not m_desc:
                i += 1
                continue

            # Procura o valor na próxima linha não-vazia
            j = i + 1
            while j < len(linhas) and not linhas[j].strip():
                j += 1

            if j >= len(linhas):
                break

            m_val = _LINHA_CARTAO_VALOR.match(linhas[j])
            if not m_val:
                # Não bateu — pode ser outra linha de descrição, segue
                i += 1
                continue

            descricao = m_desc.group("desc").strip()
            descricao = re.sub(r"\s+", " ", descricao)
            if not descricao:
                i = j + 1
                continue

            parcela_str = ""
            if m_desc.group("parc_n") and m_desc.group("parc_m"):
                parcela_str = f"{m_desc.group('parc_n')}/{m_desc.group('parc_m')}"

            valor = _parse_valor_br(m_val.group("valor"))
            if valor <= 0:
                i = j + 1
                continue

            itens.append({
                "descricao":       descricao,
                "estabelecimento": "",
                "categoria":       "",
                "parcela":         parcela_str,
                "valor":           round(valor, 2),
            })

            i = j + 1

        log.info("WillParser.extrair: %d itens encontrados", len(itens))
        return itens
