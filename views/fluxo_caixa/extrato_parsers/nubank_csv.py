"""
nubank_csv.py — Parser de extrato Nubank em formato CSV.

Formato (cabeçalho na primeira linha):

    Data,Valor,Identificador,Descrição
    06/01/2026,10.00,695cdf0f-9873-...,Transferência recebida pelo Pix - FILIPE...
    06/01/2026,-10.00,695cdfd2-a50e-...,Transferência enviada pelo Pix - Ana...

- Data:          DD/MM/AAAA
- Valor:         decimal com PONTO (não vírgula), positivo=entrada, negativo=saída
- Identificador: UUID v4 — usado pra dedup
- Descrição:    texto livre, pode conter vírgulas (CSV escapa com aspas)
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from views.fluxo_caixa.extrato_parsers.base import ExtratoParser

log = logging.getLogger(__name__)


def _parsear_data_br(s: str) -> str:
    """Converte 'DD/MM/AAAA' para 'YYYY-MM-DD'."""
    s = s.strip()
    partes = s.split("/")
    if len(partes) != 3:
        raise ValueError(f"data inválida: {s!r}")
    dia, mes, ano = partes
    if len(ano) == 2:
        ano = "20" + ano
    return f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"


class NubankCSVParser(ExtratoParser):
    """Parser de extrato Nubank em CSV."""

    nome_formato = "nubank_csv"
    extensoes    = (".csv",)

    def parse(self, caminho: str | Path) -> list[dict]:
        caminho = Path(caminho)
        itens: list[dict] = []

        with caminho.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Robustez: tolera diferentes capitalizações dos cabeçalhos
                data_str  = row.get("Data")  or row.get("data")  or ""
                valor_str = row.get("Valor") or row.get("valor") or "0"
                fitid     = (row.get("Identificador") or row.get("identificador") or "").strip()
                desc      = (row.get("Descrição") or row.get("Descricao")
                             or row.get("descrição") or row.get("descricao") or "").strip()

                if not data_str or not desc:
                    continue

                try:
                    data_iso = _parsear_data_br(data_str)
                    valor = float(valor_str)
                except ValueError as e:
                    log.warning("Linha CSV inválida ignorada (%s): %s", e, row)
                    continue

                itens.append({
                    "data":                data_iso,
                    "descricao":           desc,
                    "valor":               round(valor, 2),
                    "identificador_unico": fitid,
                })

        log.info("NubankCSVParser: %d itens extraídos de %s", len(itens), caminho.name)
        return itens
