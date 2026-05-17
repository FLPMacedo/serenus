"""
importar_fatura_model.py — Leitura e validação de arquivos de fatura de cartão.
Suporta CSV (.csv) e Excel (.xlsx).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# parsear_parcela
# ---------------------------------------------------------------------------

def parsear_parcela(valor: str | None) -> tuple[int, int]:
    """
    Converte uma string de parcela para (numero, total).
    Formatos suportados: "7/12", "7 de 12", "  3 / 12  ", "1/1".
    Retorna (1, 1) se vazio ou None.
    Levanta ValueError se numero > total ou numero < 1.
    """
    if not valor:
        return (1, 1)
    s = str(valor).strip()
    if not s:
        return (1, 1)

    # Tenta "N/M" ou "N de M"
    m = re.match(r"^\s*(\d+)\s*(?:/|de)\s*(\d+)\s*$", s, re.IGNORECASE)
    if not m:
        raise ValueError(f"Formato de parcela inválido: {valor!r}")

    num   = int(m.group(1))
    total = int(m.group(2))
    if num < 1 or total < 1:
        raise ValueError(f"Parcela inválida (valores devem ser >= 1): {valor!r}")
    if num > total:
        raise ValueError(f"Número da parcela ({num}) maior que total ({total}): {valor!r}")
    return (num, total)


# ---------------------------------------------------------------------------
# validar_linhas_fatura
# ---------------------------------------------------------------------------

def validar_linhas_fatura(linhas: list[dict]) -> list[str]:
    """
    Valida uma lista de dicts lidos de um arquivo de fatura.
    Retorna lista de strings de erro (vazia = tudo ok).
    Cada erro menciona o número da linha (1-based).
    """
    erros: list[str] = []
    for i, linha in enumerate(linhas, start=1):
        desc  = str(linha.get("descricao") or "").strip()
        valor = linha.get("valor")
        parc  = linha.get("parcela")

        if not desc:
            erros.append(f"Linha {i}: descrição é obrigatória.")
        try:
            v = float(valor) if valor is not None else 0.0
        except (ValueError, TypeError):
            erros.append(f"Linha {i}: valor inválido ({valor!r}).")
            continue
        if v <= 0:
            erros.append(f"Linha {i}: valor deve ser positivo (recebido: {v}).")
        if parc:
            try:
                parsear_parcela(str(parc))
            except ValueError as exc:
                erros.append(f"Linha {i}: {exc}")
    return erros


# ---------------------------------------------------------------------------
# ler_arquivo_fatura
# ---------------------------------------------------------------------------

def _parse_valor(raw) -> float:
    """
    Converte string/número para float.
    Suporta formato brasileiro ("1.234,56") e padrão ("1234.56").
    Heurística: se há vírgula E ponto, a vírgula é decimal (BR).
    Se só vírgula, é decimal BR. Se só ponto (ou nenhum), é padrão.
    """
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw or "").strip().strip('"')
    if "," in s and "." in s:
        # Formato BR: "1.234,56" — remove ponto milhar, troca vírgula por ponto
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # Só vírgula: decimal BR — troca por ponto
        s = s.replace(",", ".")
    # Caso contrário: padrão ("199.90") — usa diretamente
    return float(s)


def ler_arquivo_fatura(caminho: str) -> list[dict]:
    """
    Lê um arquivo CSV ou XLSX de fatura e retorna lista de dicts com chaves:
        descricao, estabelecimento, categoria, parcela, valor
    Linhas sem descricao E sem valor são ignoradas (linhas vazias).
    Levanta ValueError para extensões não suportadas.
    """
    p = Path(caminho)
    ext = p.suffix.lower()

    if ext == ".csv":
        return _ler_csv(caminho)
    elif ext in (".xlsx", ".xls"):
        return _ler_xlsx(caminho)
    else:
        raise ValueError(f"Extensão não suportada: {ext!r}. Use .csv ou .xlsx.")


def _ler_csv(caminho: str) -> list[dict]:
    linhas: list[dict] = []
    with open(caminho, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            desc  = str(row.get("descricao") or "").strip()
            valor_raw = row.get("valor")
            if not desc and not valor_raw:
                continue
            try:
                valor = _parse_valor(valor_raw)
            except (ValueError, TypeError):
                valor = 0.0
            linhas.append({
                "descricao":       desc,
                "estabelecimento": str(row.get("estabelecimento") or "").strip(),
                "categoria":       str(row.get("categoria") or "").strip(),
                "parcela":         str(row.get("parcela") or "").strip(),
                "valor":           valor,
            })
    return linhas


def _ler_xlsx(caminho: str) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb.active

    # Detecta linha de cabeçalho (primeira linha não-vazia)
    header_row = None
    col_map: dict[str, int] = {}
    campos = ["descricao", "estabelecimento", "categoria", "parcela", "valor"]
    for row in ws.iter_rows():
        vals = [str(c.value or "").strip().lower() for c in row]
        if any(v in campos for v in vals):
            header_row = row[0].row
            for cell in row:
                key = str(cell.value or "").strip().lower()
                if key in campos:
                    col_map[key] = cell.column
            break

    if header_row is None:
        return []

    linhas: list[dict] = []
    for row in ws.iter_rows(min_row=header_row + 1):
        def _get(campo: str):
            col = col_map.get(campo)
            if col is None:
                return None
            return row[col - 1].value

        desc      = str(_get("descricao") or "").strip()
        valor_raw = _get("valor")
        if not desc and valor_raw is None:
            continue
        try:
            valor = _parse_valor(valor_raw)
        except (ValueError, TypeError):
            valor = 0.0
        linhas.append({
            "descricao":       desc,
            "estabelecimento": str(_get("estabelecimento") or "").strip(),
            "categoria":       str(_get("categoria") or "").strip(),
            "parcela":         str(_get("parcela") or "").strip(),
            "valor":           valor,
        })
    return linhas
