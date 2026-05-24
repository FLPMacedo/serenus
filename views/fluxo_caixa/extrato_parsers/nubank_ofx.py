"""
nubank_ofx.py — Parser de extrato Nubank em formato OFX (Open Financial Exchange).

OFX é um padrão internacional de extratos bancários. Esse parser cobre OFX
1.0.2 (SGML, sem fechamento de tags), que é o usado pelo Nubank.

Estrutura relevante:

    <BANKTRANLIST>
      <STMTTRN>
        <TRNTYPE>CREDIT</TRNTYPE>
        <DTPOSTED>20260106000000[-3:BRT]</DTPOSTED>
        <TRNAMT>10.00</TRNAMT>
        <FITID>695cdf0f-9873-...</FITID>
        <MEMO>Transferência recebida pelo Pix - FILIPE...</MEMO>
      </STMTTRN>
      <STMTTRN>
        ...
      </STMTTRN>
    </BANKTRANLIST>

Não usamos um parser XML porque OFX 1.0.2 é SGML (tags sem fechamento).
Regex é suficiente — a estrutura é fixa e bem-comportada.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from views.fluxo_caixa.extrato_parsers.base import ExtratoParser

log = logging.getLogger(__name__)


# Pega um bloco <STMTTRN>...</STMTTRN> inteiro (case-insensitive, multilinha)
_BLOCO = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.IGNORECASE | re.DOTALL)

# Dentro do bloco, extrai cada tag (valor entre > e a próxima tag/linha)
_TAG = lambda nome: re.compile(
    rf"<{nome}>\s*([^<\n\r]+?)\s*(?=<|$)",
    re.IGNORECASE | re.MULTILINE,
)

_RE_TRNAMT   = _TAG("TRNAMT")
_RE_DTPOSTED = _TAG("DTPOSTED")
_RE_FITID    = _TAG("FITID")
_RE_MEMO     = _TAG("MEMO")


def _parsear_dtposted(s: str) -> str:
    """Converte '20260106000000[-3:BRT]' (ou só '20260106') em 'YYYY-MM-DD'."""
    # Pega só os 8 primeiros caracteres de dígito (AAAAMMDD)
    digitos = "".join(c for c in s if c.isdigit())[:8]
    if len(digitos) != 8:
        raise ValueError(f"data OFX inválida: {s!r}")
    return f"{digitos[0:4]}-{digitos[4:6]}-{digitos[6:8]}"


class NubankOFXParser(ExtratoParser):
    """Parser de extrato Nubank em OFX."""

    nome_formato = "nubank_ofx"
    extensoes    = (".ofx",)

    def parse(self, caminho: str | Path) -> list[dict]:
        caminho = Path(caminho)
        # OFX header é ASCII; conteúdo declara CHARSET=UTF-8 (ou similar).
        # Lemos como utf-8 com fallback latin-1 em caso de banco antigo.
        try:
            texto = caminho.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            texto = caminho.read_text(encoding="latin-1")

        itens: list[dict] = []
        for m_bloco in _BLOCO.finditer(texto):
            bloco = m_bloco.group(1)

            m_data  = _RE_DTPOSTED.search(bloco)
            m_valor = _RE_TRNAMT.search(bloco)
            m_fitid = _RE_FITID.search(bloco)
            m_memo  = _RE_MEMO.search(bloco)

            if not (m_data and m_valor and m_memo):
                continue

            try:
                data_iso = _parsear_dtposted(m_data.group(1))
                valor    = float(m_valor.group(1).strip())
            except ValueError as e:
                log.warning("Bloco STMTTRN inválido ignorado (%s)", e)
                continue

            itens.append({
                "data":                data_iso,
                "descricao":           m_memo.group(1).strip(),
                "valor":               round(valor, 2),
                "identificador_unico": (m_fitid.group(1).strip() if m_fitid else ""),
            })

        log.info("NubankOFXParser: %d itens extraídos de %s", len(itens), caminho.name)
        return itens
