"""
imprimir_lista.py — Exportar a lista de compras para PDF e para
texto formatado (uso no botão "Enviar pelo WhatsApp").

PDF usa xhtml2pdf (já presente no projeto via gerar_pdfs.py e imprimir_os).
Texto pra WhatsApp é puro Markdown light (negrito com *).
"""

from __future__ import annotations

import html
import logging
import urllib.parse
from datetime import date
from pathlib import Path

from views.compras_casa.casa_model import ItemEstoque

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Texto formatado pra WhatsApp / clipboard
# ---------------------------------------------------------------------------

def formatar_texto_lista(itens: list[ItemEstoque],
                          titulo: str = "Lista de Compras") -> str:
    """Formata a lista como texto plain (compatível com WhatsApp):

        *Lista de Compras — 20/05/2026*

        *Mercearia*
        • Arroz Camil — 2 kg (atual 1, mín 3)
        • Feijão Kicaldo — 1 kg

        *Limpeza*
        • Detergente — 3 un
    """
    if not itens:
        return f"*{titulo}*\n\n✅ Nada precisa ser comprado."

    linhas: list[str] = [f"*{titulo} — {date.today().strftime('%d/%m/%Y')}*", ""]

    # Agrupa por categoria
    grupos: dict[str, list[ItemEstoque]] = {}
    for it in itens:
        grupos.setdefault(it.categoria or "Sem categoria", []).append(it)

    for cat in sorted(grupos):
        linhas.append(f"*{cat}*")
        for it in grupos[cat]:
            marca = f" {it.marca}" if it.marca else ""
            un = f" {it.unidade}" if it.unidade else ""
            qty = f"{it.quantidade_a_comprar:g}".replace(".", ",")
            atual = f"{it.estoque_atual:g}".replace(".", ",")
            minimo = f"{it.estoque_minimo:g}".replace(".", ",")
            linhas.append(
                f"• {it.nome}{marca} — comprar {qty}{un} "
                f"(atual {atual}, mín {minimo})"
            )
        linhas.append("")

    linhas.append(f"_Total: {len(itens)} itens_")
    return "\n".join(linhas).strip() + "\n"


def gerar_link_whatsapp(texto: str, numero: str = "") -> str:
    """Monta uma URL wa.me com o texto pré-preenchido.

    numero: opcional, formato livre (com ou sem +55, com ou sem máscara).
            Se vazio, gera link sem destinatário (o WhatsApp abre vazio
            pedindo pra escolher o contato).
    """
    so_digitos = "".join(c for c in numero if c.isdigit())
    base = f"https://wa.me/{so_digitos}" if so_digitos else "https://wa.me/"
    return f"{base}?text={urllib.parse.quote(texto)}"


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _safe(s) -> str:
    if s is None or s == "":
        return "&nbsp;"
    return html.escape(str(s))


def _construir_html(itens: list[ItemEstoque]) -> str:
    if not itens:
        corpo = (
            "<p style='text-align:center; padding:40px; color:#16A34A;'>"
            "<b>✅ Nada precisa ser comprado.</b></p>"
        )
    else:
        grupos: dict[str, list[ItemEstoque]] = {}
        for it in itens:
            grupos.setdefault(it.categoria or "Sem categoria", []).append(it)
        partes = []
        for cat in sorted(grupos):
            partes.append(
                f"<div class='cat-titulo'>{_safe(cat)}</div>"
            )
            partes.append("<table class='tab-itens'>")
            partes.append(
                "<tr><th>Item</th><th>Marca</th>"
                "<th class='c-num'>Comprar</th>"
                "<th class='c-num'>Atual</th>"
                "<th class='c-num'>Mínimo</th></tr>"
            )
            for it in grupos[cat]:
                un = f" {it.unidade}" if it.unidade else ""
                qty = f"{it.quantidade_a_comprar:g}".replace(".", ",")
                atual = f"{it.estoque_atual:g}".replace(".", ",")
                minimo = f"{it.estoque_minimo:g}".replace(".", ",")
                partes.append(
                    "<tr>"
                    f"<td>{_safe(it.nome)}</td>"
                    f"<td>{_safe(it.marca)}</td>"
                    f"<td class='c-num'>{qty}{_safe(un)}</td>"
                    f"<td class='c-num'>{atual}{_safe(un)}</td>"
                    f"<td class='c-num'>{minimo}{_safe(un)}</td>"
                    "</tr>"
                )
            partes.append("</table>")
        corpo = "\n".join(partes)

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  @page {{ size: A4; margin: 1.5cm; }}
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #1F2937; }}
  .header {{
    background: #16A34A; color: #FFFFFF;
    text-align: center; padding: 10px;
    font-size: 14pt; font-weight: bold; letter-spacing: 1px;
  }}
  .sub {{ text-align: center; color: #6B7280; margin: 8px 0 18px; }}
  .cat-titulo {{
    background: #E0F2FE; color: #075985;
    padding: 6px 10px; font-weight: bold;
    margin-top: 12px; border-left: 4px solid #16A34A;
  }}
  .tab-itens {{
    width: 100%; border-collapse: collapse; margin: 4px 0 12px;
  }}
  .tab-itens th {{
    background: #F3F4F6; border: 1px solid #9CA3AF;
    padding: 4px 8px; text-align: left;
  }}
  .tab-itens td {{
    border: 1px solid #9CA3AF; padding: 4px 8px;
  }}
  .c-num {{ text-align: right; white-space: nowrap; }}
  .rodape {{
    margin-top: 20px; text-align: right;
    color: #6B7280; font-size: 9pt;
  }}
</style>
</head>
<body>
  <div class="header">🛒 LISTA DE COMPRAS</div>
  <div class="sub">{date.today().strftime('%d/%m/%Y')} &middot; {len(itens)} item(ns)</div>
  {corpo}
  <div class="rodape">Gerado pelo Serenus</div>
</body>
</html>
"""


def imprimir_lista_pdf(itens: list[ItemEstoque], caminho: str | Path) -> Path:
    """Gera PDF da lista de compras. Lança RuntimeError em falha."""
    try:
        from xhtml2pdf import pisa
    except ImportError as e:
        raise RuntimeError(
            "Biblioteca xhtml2pdf não está instalada. "
            "Instale com: pip install xhtml2pdf"
        ) from e

    import os as _os
    import tempfile as _tempfile
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    html_str = _construir_html(itens)

    # Escrita atômica: tmp + rename (mesma estratégia de imprimir_os)
    fd, tmp_path = _tempfile.mkstemp(
        suffix=".pdf", prefix=".tmp_", dir=str(destino.parent),
    )
    try:
        with _os.fdopen(fd, "wb") as f:
            resultado = pisa.CreatePDF(html_str, dest=f, encoding="utf-8")
        if resultado.err:
            raise RuntimeError("Falha ao gerar PDF da lista de compras.")
        _os.replace(tmp_path, destino)
        tmp_path = None
    finally:
        if tmp_path is not None:
            try:
                _os.unlink(tmp_path)
            except OSError:
                pass
    log.info("imprimir_lista_pdf: %d itens em %s", len(itens), destino)
    return destino
