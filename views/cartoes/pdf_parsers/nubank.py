"""
nubank.py — Parser de fatura PDF do Nubank.

Layout observado (extraído via pypdf):

  TRANSAÇÕES DE 09 ABR A 09 MAI

  ── Padrão A (uma linha) ──
    14 ABR
     •••• 9541 Netflix.Com R$ 44,90

  ── Padrão B (multi-linha + parcela) ──
    09 ABR
     ITAU UNIBANCO HOLDING S.A. - Parcela 3/5
     Total a pagar: R$ 1.289,62 (...)
    R$ 257,93

  ── Padrão C (pagamentos negativos a IGNORAR) ──
    17 ABR Pagamento em 17 ABR −R$ 1.428,32
    16 ABR Crédito de atraso −R$ 655,00

  Caracteres especiais:
    - Sinal negativo é '−' (U+2212), não '-' (U+002D).
    - Datas: dia + mês em 3 letras maiúsculas pt-BR (ABR, MAI, JUN...).
"""

from __future__ import annotations

import logging
import re

from views.cartoes.pdf_parsers.base import PDFParser

log = logging.getLogger(__name__)


# Marcador único do Nubank no texto da fatura.
# IMPORTANTE: precisa ser "Nu Pagamentos S.A." (CNPJ do emissor) e não só
# "Nu Pagamentos" porque outras faturas (Magazine Luiza/Luizacred) listam
# transações tipo "PIX NU PAGAMENTOS" como estabelecimento, causando
# falso-positivo no detect_layout.
_MARCADOR_NUBANK = re.compile(r"Nu\s+Pagamentos\s+S\.?\s*A\.?", re.IGNORECASE)

# Cabeçalho da seção de transações
_INICIO_TRANSACOES = re.compile(r"TRANSAÇÕES DE\s+\d", re.IGNORECASE)

# Data: "DD MMM" no início da linha (após strip)
_MESES_NUBANK = r"JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ"
_DATA = re.compile(rf"^(\d{{1,2}}\s+(?:{_MESES_NUBANK}))\b\s*(.*)$",
                    re.IGNORECASE)

# Captura valor BR no final da string: "R$ 1.234,56", "−R$ 100,00", "100,00"
# Reconhece tanto '−' (U+2212) quanto '-' como sinal negativo.
_VALOR = re.compile(
    r"([−\-]?)\s*R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
)

# Linha que é APENAS o valor (sem mais nada)
_LINHA_VALOR = re.compile(
    r"^[−\-]?\s*R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}\s*$"
)

# Identifica "Parcela N/M" em qualquer lugar da descrição
_PARCELA = re.compile(r"Parcela\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)

# Linhas de cabeçalho de página que devem ser puladas
_LIXO_PAGINA = re.compile(
    r"^(\d+\s+de\s+\d+|FATURA\b.*EMISSÃO|TRANSAÇÕES DE)",
    re.IGNORECASE,
)


def _parse_valor_br(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _eh_valor_negativo(linha: str) -> bool:
    """True se a linha contém um valor com sinal negativo (−R$ ou -R$)."""
    return bool(re.search(r"[−\-]\s*R?\$?\s*\d", linha))


def _extrair_valor_final(linha: str) -> tuple[float, str] | None:
    """Extrai o valor que estiver no final da linha.
    Retorna (valor_float, texto_sem_valor) ou None se não houver."""
    m = _VALOR.search(linha)
    if not m:
        return None
    sinal, num = m.group(1), m.group(2)
    valor = _parse_valor_br(num)
    if sinal in ("−", "-"):
        valor = -valor
    texto_sem_valor = linha[: m.start()].rstrip()
    return valor, texto_sem_valor


class NubankParser(PDFParser):
    """Parser estrutural baseado no layout do PDF da fatura Nubank."""

    nome_layout = "nubank"

    def reconhece(self, texto: str) -> bool:
        return bool(_MARCADOR_NUBANK.search(texto))

    def extrair(self, texto: str) -> list[dict]:
        linhas = texto.splitlines()
        itens: list[dict] = []
        em_transacoes = False
        i = 0

        while i < len(linhas):
            linha = linhas[i].strip()

            if _INICIO_TRANSACOES.search(linha):
                em_transacoes = True
                i += 1
                continue

            if not em_transacoes or not linha:
                i += 1
                continue

            # Pula cabeçalhos de página (não impede continuar processando)
            if _LIXO_PAGINA.match(linha):
                i += 1
                continue

            # Linha começa com data?
            m_data = _DATA.match(linha)
            if not m_data:
                # Linha sem data (provavelmente agregador tipo
                # "Filipe M Macedo R$ 44,90" ou texto residual): ignora.
                i += 1
                continue

            resto = m_data.group(2).strip()

            # Caso A: valor está na mesma linha
            captura = _extrair_valor_final(resto)
            if captura is not None:
                valor, descricao = captura
                if valor > 0:
                    item = self._montar_item(descricao, valor)
                    if item:
                        itens.append(item)
                i += 1
                continue

            # Caso B/D: valor virá em linha posterior — junta descrição até
            # encontrar uma linha que (a) seja só valor, (b) tenha valor no
            # final junto com descrição, ou (c) seja uma nova data.
            desc_partes: list[str] = []
            if resto:
                desc_partes.append(resto)
            j = i + 1
            valor_final: float | None = None
            while j < len(linhas):
                prox = linhas[j].strip()

                if not prox:
                    j += 1
                    continue
                if _LIXO_PAGINA.match(prox):
                    j += 1
                    continue
                if _DATA.match(prox):
                    break  # nova transação — sai sem consumir esta linha

                # Tenta extrair valor do FINAL desta linha
                captura = _extrair_valor_final(prox)
                if captura is not None:
                    valor_temp, texto_sem_valor = captura
                    # Se sobrou texto antes do valor, é descrição + valor juntos
                    # (caso "•••• 9541 Netflix.Com R$ 44,90"). Adiciona a
                    # parte textual à descrição.
                    if texto_sem_valor:
                        desc_partes.append(texto_sem_valor)
                    valor_final = valor_temp
                    j += 1
                    break

                # Sem valor — é só descrição
                desc_partes.append(prox)
                j += 1

            descricao = " ".join(desc_partes).strip()

            if valor_final is None:
                # Não conseguiu valor — pula
                i = j
                continue

            if valor_final > 0:
                item = self._montar_item(descricao, valor_final)
                if item:
                    itens.append(item)

            i = j

        log.info("NubankParser.extrair: %d itens encontrados", len(itens))
        return itens

    def _montar_item(self, descricao: str, valor: float) -> dict | None:
        """Constrói o dict no schema padrão. Retorna None se descrição vazia."""
        descricao = descricao.strip(" -·•").strip()
        if not descricao:
            return None

        # Corta o detalhamento longo de parcela ("Total a pagar: R$ X (valor da
        # transação de R$ Y + R$ Z de IOF + R$ W de juros) ...") — fica só o
        # nome do estabelecimento antes desse texto.
        descricao = re.split(r"\s+Total a pagar:", descricao, maxsplit=1)[0]

        # Extrai parcela "N/M" se presente
        parcela_str = ""
        m_p = _PARCELA.search(descricao)
        if m_p:
            parcela_str = f"{m_p.group(1)}/{m_p.group(2)}"
            descricao = _PARCELA.sub("", descricao).strip(" -·").strip()

        # Limpa marcadores de cartão tipo "•••• 9541"
        descricao = re.sub(r"•+\s*\d{4}\s*", "", descricao).strip()

        # Colapsa espaços múltiplos
        descricao = re.sub(r"\s+", " ", descricao).strip()

        return {
            "descricao":       descricao,
            "estabelecimento": "",
            "categoria":       "",
            "parcela":         parcela_str,
            "valor":           round(valor, 2),
        }
