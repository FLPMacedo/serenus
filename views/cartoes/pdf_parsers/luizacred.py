"""
luizacred.py — Parser do PDF de fatura Magazine Luiza / Luizacred.

Luizacred é a financeira do grupo Magazine Luiza, processada via Itaú.
Layout é similar ao Itaú, mas com duas diferenças importantes:

1. A parcela pode aparecer COLADA na descrição, sem espaço:
     "10/04 ANUIDADE DIFERENCI08/12 14,99"
     "13/03 PIX NU PAGAMENTOS 02/05 299,11"   <- aqui tem espaço (normal)

2. O texto extraído pelo pypdf NÃO preserva a separação visual entre
   "Lançamentos atuais" e "Compras parceladas - próximas faturas" —
   as transações vêm todas juntas num bloco, e os títulos de seção
   aparecem depois, em outra coluna. Como não dá pra distinguir com
   confiabilidade qual transação pertence a qual seção a partir só
   do texto, este parser extrai TODAS as transações e deixa o usuário
   filtrar no modal de import.

Marcador único: "LUIZACRED" (CNPJ/razão social do emissor — não aparece
em fatura Itaú normal).
"""

from __future__ import annotations

import logging
import re

from views.cartoes.pdf_parsers.base import PDFParser

log = logging.getLogger(__name__)


_MARCADOR_LUIZACRED = re.compile(r"\bLUIZACRED\b", re.IGNORECASE)

# Transação Luizacred. Suporta parcela colada na descrição:
#   "10/04 ANUIDADE DIFERENCI08/12 14,99"  -> desc="ANUIDADE DIFERENCI", parc="08/12"
#   "13/03 PIX NU PAGAMENTOS 02/05 299,11" -> desc="PIX NU PAGAMENTOS", parc="02/05"
#   "09/05 ENCARGOS DE ATRASO 1,91"        -> desc="ENCARGOS DE ATRASO",  parc=""
# Estratégia: capturar greedy mínima a descrição, parcela opcional (com ou
# sem espaço antes), valor BR no fim.
_TRANSACAO = re.compile(
    r"^(?P<data>\d{2}/\d{2})\s+"
    r"(?P<desc>.+?)"
    r"(?P<parcela>\d{2}/\d{2})?"
    r"\s+(?P<valor>-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
)


def _parse_valor_br(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


class LuizacredParser(PDFParser):
    """Parser do PDF de fatura Magazine Luiza (emissora Luizacred S/A SCFI)."""

    nome_layout = "luizacred"

    def reconhece(self, texto: str) -> bool:
        return bool(_MARCADOR_LUIZACRED.search(texto))

    def extrair(self, texto: str) -> list[dict]:
        itens: list[dict] = []

        for linha in texto.splitlines():
            s = linha.strip()
            if not s:
                continue

            m = _TRANSACAO.match(s)
            if not m:
                continue

            valor = _parse_valor_br(m.group("valor"))
            if valor <= 0:
                continue  # pagamentos / créditos

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

        log.info("LuizacredParser.extrair: %d itens encontrados", len(itens))
        return itens
