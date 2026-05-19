"""
itau.py — Parser de fatura PDF do Itaú (cartões VISA, MASTERCARD, etc.).

Layout observado (extraído via pypdf após desbloqueio com senha):

  Pagamentos efetuados                 ← seção a IGNORAR (negativos)
  DATA VALOR EM R$
  17/03 PAGAMENTO DEB AUTOMATIC -1.096,14

  Lançamentos: compras e saques        ← inclui (à vista)
  DATA ESTABELECIMENTO VALOR EM R$
  13/03 DM*SpotifySAO PAULOBRA 12,90
  outros  SAO PAULO                    ← linha de categoria/local, pular

  Lançamentos: produtos e serviços     ← inclui (parceladas)
  DATA PRODUTOS/SERVIÇOS VALOR EM R$
  14/11 PIX MERCADO PA 05/12 168,73
  Principal (R$ 112,66) + Juros (R$ 56,07)   ← detalhamento, pular

  Total dos lançamentos atuais 1.048,87  ← fim da captura

  Compras parceladas - próximas faturas  ← seção a IGNORAR (projeção)
  ...

Formato da linha de transação:
  DD/MM  DESCRIÇÃO   [NN/MM]   VALOR
                       ^opcional (parcela)
"""

from __future__ import annotations

import logging
import re

from views.cartoes.pdf_parsers.base import PDFParser

log = logging.getLogger(__name__)


# Marcador único: cabeçalho "Lançamentos:" não aparece em outros bancos.
_MARCADOR_ITAU = re.compile(
    r"Lan[çc]amentos:\s+(?:compras e saques|produtos e servi[çc]os)",
    re.IGNORECASE,
)

# Inícios de seções RELEVANTES (passa a capturar)
_INICIO_LANC = re.compile(
    r"^Lan[çc]amentos:\s+(?:compras e saques|produtos e servi[çc]os)",
    re.IGNORECASE,
)

# Fins de captura (qualquer um encerra a seção atual)
_FIM_CAPTURA = re.compile(
    r"^(?:Total dos lan[çc]amentos atuais"
    r"|Lan[çc]amentos no cart[ãa]o"
    r"|Lan[çc]amentos produtos e servi[çc]os"
    r"|Compras parceladas\s*-\s*pr[óo]ximas faturas"
    r"|Encargos cobrados nesta fatura"
    r"|Limites de cr[ée]dito\b"
    r"|Pagamentos efetuados)",
    re.IGNORECASE,
)

# Cabeçalho da tabela ("DATA ESTABELECIMENTO VALOR EM R$" ou similar) — pular
_HEADER_TABELA = re.compile(r"^DATA\s+", re.IGNORECASE)

# Linhas de detalhamento que NÃO são transações
_LINHA_AUXILIAR = re.compile(
    r"^(?:Principal\s*\(|outros\b|FILIPE\b|Compras parceladas|Total\b)",
    re.IGNORECASE,
)

# Linha de transação Itaú:
#   "DD/MM  DESCRIÇÃO  [NN/MM]  VALOR"
# Captura: data, descrição (greedy mínima), parcela opcional, valor BR.
_TRANSACAO = re.compile(
    r"^(?P<data>\d{2}/\d{2})\s+"
    r"(?P<desc>.+?)"
    r"(?:\s+(?P<parcela>\d{1,2}/\d{1,2}))?"
    r"\s+(?P<valor>-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
)


def _parse_valor_br(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


class ItauParser(PDFParser):
    """Parser do PDF de fatura Itaú — funciona pra VISA e MASTERCARD."""

    nome_layout = "itau"

    def reconhece(self, texto: str) -> bool:
        return bool(_MARCADOR_ITAU.search(texto))

    def extrair(self, texto: str) -> list[dict]:
        itens: list[dict] = []
        em_lancamentos = False

        for linha in texto.splitlines():
            s = linha.strip()
            if not s:
                continue

            # Encerra captura ao bater num delimitador conhecido (mesmo se
            # não estivermos em modo captura — limpa estado).
            if _FIM_CAPTURA.match(s):
                em_lancamentos = False
                continue

            if _INICIO_LANC.match(s):
                em_lancamentos = True
                continue

            if not em_lancamentos:
                continue

            if _HEADER_TABELA.match(s) or _LINHA_AUXILIAR.match(s):
                continue

            m = _TRANSACAO.match(s)
            if not m:
                continue

            valor = _parse_valor_br(m.group("valor"))
            if valor <= 0:
                continue  # pagamentos, créditos etc.

            descricao = m.group("desc").strip()
            descricao = re.sub(r"\s+", " ", descricao)
            parcela_str = m.group("parcela") or ""

            itens.append({
                "descricao":       descricao,
                "estabelecimento": "",
                "categoria":       "",
                "parcela":         parcela_str,
                "valor":           round(valor, 2),
            })

        log.info("ItauParser.extrair: %d itens encontrados", len(itens))
        return itens
