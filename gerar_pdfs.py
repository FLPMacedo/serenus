"""
gerar_pdfs.py — Converte os manuais em Markdown para PDF.

Lê:
    docs/MANUAL_USUARIO.md
    docs/PLAYBOOK.md
Gera:
    docs/MANUAL_USUARIO.pdf
    docs/PLAYBOOK.pdf

Resolve caminhos relativos de imagens (screenshots/*) para absolutos
para o xhtml2pdf encontrá-las. CSS embutido garante leitura
agradável: fontes legíveis, tabelas listradas, código com fundo,
quebra de página entre seções de nível 2.
"""
from __future__ import annotations

import sys
from pathlib import Path

import markdown
from xhtml2pdf import pisa

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT     = Path(__file__).parent
DOCS_DIR = ROOT / "docs"

ARQUIVOS = [
    ("MANUAL_USUARIO.md", "MANUAL_USUARIO.pdf", "Serenus — Manual do Usuário"),
    ("PLAYBOOK.md",       "PLAYBOOK.pdf",       "Serenus — Playbook Prático"),
]

CSS = """
@page {
    size: A4;
    margin: 1.4cm 1.4cm 1.6cm 1.4cm;
    @frame footer_frame {
        -pdf-frame-content: footer_content;
        left: 50pt; width: 500pt; top: 805pt; height: 22pt;
    }
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    color: #1F2937;
    line-height: 1.35;
}
h1 {
    color: #1A56DB;
    font-size: 20pt;
    margin: 0 0 4pt 0;
    padding-bottom: 4pt;
    border-bottom: 2px solid #DBEAFE;
    -pdf-keep-with-next: true;
}
h2 {
    color: #1A56DB;
    font-size: 14pt;
    margin: 14pt 0 4pt 0;
    padding-bottom: 2pt;
    border-bottom: 1px solid #E5E7EB;
    -pdf-keep-with-next: true;
}
h3 {
    color: #075985;
    font-size: 12pt;
    margin: 10pt 0 3pt 0;
    -pdf-keep-with-next: true;
}
h4 {
    color: #374151;
    font-size: 10.5pt;
    margin: 8pt 0 2pt 0;
    -pdf-keep-with-next: true;
}
p { margin: 3pt 0; }
ul, ol { margin: 3pt 0 3pt 16pt; padding: 0; }
li { margin: 1pt 0; }
strong { color: #111827; }
em { color: #374151; }
code {
    font-family: "Courier New", monospace;
    font-size: 9pt;
    background-color: #F3F4F6;
    padding: 1pt 3pt;
    color: #6D28D9;
}
pre {
    font-family: "Courier New", monospace;
    font-size: 9pt;
    background-color: #F3F4F6;
    border-left: 3px solid #1A56DB;
    padding: 5pt 8pt;
    margin: 4pt 0;
    color: #111827;
    line-height: 1.25;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 5pt 0;
    font-size: 9pt;
}
th {
    background-color: #1A56DB;
    color: #FFFFFF;
    padding: 4pt 6pt;
    text-align: left;
    border: 1px solid #1A56DB;
}
td {
    padding: 3pt 6pt;
    border: 1px solid #E5E7EB;
    vertical-align: top;
}
tr:nth-child(even) td { background-color: #F9FAFB; }
img {
    max-width: 92%;
    margin: 4pt 0;
    border: 1px solid #E5E7EB;
}
blockquote {
    border-left: 3px solid #1A56DB;
    background-color: #EFF6FF;
    padding: 4pt 10pt;
    margin: 5pt 0;
    color: #1E3A8A;
    font-style: italic;
}
hr {
    border: none;
    border-top: 1px solid #E5E7EB;
    margin: 8pt 0;
}
a { color: #1A56DB; text-decoration: underline; }
.subtitle {
    color: #6B7280;
    font-size: 10pt;
    margin: 0 0 10pt 0;
}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{titulo}</title>
<style>{css}</style>
</head>
<body>
<h1>{titulo}</h1>
<div class="subtitle">Versão 2.3.0 · Documentação oficial</div>
{conteudo}
<div id="footer_content" style="text-align: center; color: #9CA3AF; font-size: 9pt;">
Página <pdf:pagenumber/> de <pdf:pagecount/> — Serenus
</div>
</body>
</html>
"""


def converter(md_path: Path, pdf_path: Path, titulo: str) -> bool:
    print(f"  · {md_path.name} → {pdf_path.name}")
    md_texto = md_path.read_text(encoding="utf-8")

    # Resolve caminhos de imagens relativas para absolutos
    base = md_path.parent.resolve()
    md_texto = md_texto.replace(
        "](screenshots/",
        f"]({base.as_posix()}/screenshots/",
    )

    html_corpo = markdown.markdown(
        md_texto,
        extensions=["tables", "fenced_code", "attr_list", "sane_lists"],
    )

    html_completo = HTML_TEMPLATE.format(
        titulo=titulo, css=CSS, conteudo=html_corpo,
    )

    with open(pdf_path, "wb") as f:
        result = pisa.CreatePDF(html_completo, dest=f, encoding="utf-8")

    if result.err:
        print(f"    ! Erros na conversão: {result.err}")
        return False
    return True


def main() -> int:
    print("Gerando PDFs...")
    for md_nome, pdf_nome, titulo in ARQUIVOS:
        md_path  = DOCS_DIR / md_nome
        pdf_path = DOCS_DIR / pdf_nome
        if not md_path.exists():
            print(f"  ! Arquivo não encontrado: {md_path}")
            continue
        converter(md_path, pdf_path, titulo)

    print("\nFeito! Arquivos em:")
    for _, pdf_nome, _ in ARQUIVOS:
        p = DOCS_DIR / pdf_nome
        if p.exists():
            print(f"  {p}  ({p.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
