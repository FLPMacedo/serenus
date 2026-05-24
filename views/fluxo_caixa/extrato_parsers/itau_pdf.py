"""
itau_pdf.py — Parser de extrato Itaú em PDF (semestral).

Layout do PDF (extraído via pypdf):

  saldo em conta Limite da Conta utilizado ...
  extrato conta / lançamentos
  período de visualização: 01/01/2026 até 30/06/2026
  data lançamentos valor (R$) saldo (R$)
  19/05/2026 SALDO DO DIA -6.210,95
  18/05/2026 FATURA PAGA CARTAO LUIZA -329,44
  18/05/2026 FATURA PAGA Itau Uniclas -1.170,31
  18/05/2026 CREDITO LIBERAD PIX 8514 1.245,37
  ...

Cada linha de transação: DD/MM/AAAA DESCRICAO VALOR
Linhas "SALDO DO DIA" são apenas saldo do dia, NÃO transações — pular.

Itaú não fornece identificador único; geramos hash determinístico a partir
de (data, descricao, valor) pra dedup. Importação repetida do mesmo período
não duplica linhas.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from views.fluxo_caixa.extrato_parsers.base import ExtratoParser

log = logging.getLogger(__name__)


# Transação: DATA DESCRIÇÃO VALOR (sem segundo valor — saldo vem em outra linha)
_TRANSACAO = re.compile(
    r"^(?P<data>\d{2}/\d{2}/\d{4})\s+"
    r"(?P<desc>.+?)\s+"
    r"(?P<valor>-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
)

# Linhas que NÃO são transações reais (saldo informativo, header)
_LIXO = re.compile(
    r"SALDO\s+DO\s+DIA|^\s*data\s+lan[çc]amentos\b",
    re.IGNORECASE,
)


def _parse_valor_br(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _parse_data_br(s: str) -> str:
    """Converte 'DD/MM/AAAA' -> 'YYYY-MM-DD'."""
    d, m, a = s.split("/")
    return f"{a}-{m}-{d}"


def _hash_id(data: str, descricao: str, valor: float, indice: int) -> str:
    """Identificador determinístico pra dedup.

    Inclui um índice ordinal porque o mesmo (data, desc, valor) PODE aparecer
    legitimamente várias vezes no mesmo dia (ex: 2 PIX iguais pra mesma pessoa)
    — sem o índice, dedup descartaria o segundo erroneamente. O índice é
    relativo à posição no extrato, então re-importar o MESMO arquivo continua
    deduplicando perfeitamente.
    """
    chave = f"itau|{data}|{descricao}|{valor:.2f}|{indice}"
    return hashlib.sha1(chave.encode("utf-8")).hexdigest()[:16]


class ItauPDFParser(ExtratoParser):
    """Parser de extrato Itaú em PDF."""

    nome_formato = "itau_pdf"
    extensoes    = (".pdf",)

    def parse(self, caminho: str | Path) -> list[dict]:
        # Reusa o extrator de texto que já temos no módulo de cartões
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf

        texto = extrair_texto_pdf(str(caminho))
        itens: list[dict] = []

        # Conta ocorrências por (data, desc, valor) pra gerar índice estável
        # quando há duplicatas legítimas no mesmo dia.
        ocorrencias: dict[tuple, int] = {}

        for linha in texto.splitlines():
            s = linha.strip()
            if not s:
                continue
            if _LIXO.search(s):
                continue

            m = _TRANSACAO.match(s)
            if not m:
                continue

            try:
                data_iso = _parse_data_br(m.group("data"))
                valor    = _parse_valor_br(m.group("valor"))
            except ValueError:
                continue

            descricao = re.sub(r"\s+", " ", m.group("desc")).strip()
            if not descricao:
                continue

            chave = (data_iso, descricao, round(valor, 2))
            idx = ocorrencias.get(chave, 0)
            ocorrencias[chave] = idx + 1

            itens.append({
                "data":                data_iso,
                "descricao":           descricao,
                "valor":               round(valor, 2),
                "identificador_unico": _hash_id(data_iso, descricao, valor, idx),
            })

        log.info("ItauPDFParser: %d itens extraídos de %s",
                 len(itens), Path(caminho).name)
        return itens
