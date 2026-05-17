"""
config.py — Serenus
Centraliza cores, constantes de layout, tema e listas de domínio.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Paletas de cores
# ---------------------------------------------------------------------------

TEMAS: dict[str, dict[str, str]] = {
    "claro": {
        "fundo":      "#F5F7FA",
        "primario":   "#1A56DB",
        "secundario": "#374151",
        "texto":      "#111827",
        "positivo":   "#16A34A",
        "alerta":     "#DC2626",
        "atencao":    "#D97706",
        # superfícies secundárias
        "sidebar":    "#E8ECF2",
        "card":       "#FFFFFF",
        "borda":      "#D1D5DB",
        "texto_mudo": "#6B7280",
    },
    "escuro": {
        "fundo":      "#1F2937",
        "primario":   "#3B82F6",
        "secundario": "#9CA3AF",
        "texto":      "#F9FAFB",
        "positivo":   "#16A34A",
        "alerta":     "#DC2626",
        "atencao":    "#D97706",
        "sidebar":    "#111827",
        "card":       "#374151",
        "borda":      "#4B5563",
        "texto_mudo": "#9CA3AF",
    },
}

TEMA_PADRAO = "claro"


def get_tema(nome: str = TEMA_PADRAO) -> dict[str, str]:
    """Retorna o dicionário de cores do tema solicitado."""
    return TEMAS.get(nome, TEMAS[TEMA_PADRAO])


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

SIDEBAR_WIDTH = 220
MIN_WIDTH     = 1100
MIN_HEIGHT    = 720

# ---------------------------------------------------------------------------
# UX / comportamento
# ---------------------------------------------------------------------------

TOAST_DURATION = 3000          # milissegundos
TOAST_POSICAO  = "bottom-right"
MESES_RECORRENTE_MAX = 12      # máximo de meses ao lançar despesa recorrente

# ---------------------------------------------------------------------------
# Domínio — listas fixas
# ---------------------------------------------------------------------------

CATEGORIAS_PLANO_CONTAS = [
    "Moradia",
    "Transporte",
    "Alimentação",
    "Saúde",
    "Educação",
    "Serviços",
    "Lazer",
    "Impostos",
    "Pessoal",
    "Cartão de Crédito",
    "Outros",
]

TIPOS_CUSTO = ["fixo", "variavel"]

TIPOS_RECEITA = ["clt", "freela", "aluguel", "dividendos", "outro"]

TIPOS_DIVIDA = ["cartao", "emprestimo", "financiamento", "outro"]

STATUS_CONTA = ["pendente", "pago", "cancelado"]

HORIZONTES_MESES = [6, 12, 18, 24, 36]   # seletores de horizonte nos dashboards

NOMES_MESES = [
    "Janeiro", "Fevereiro", "Março",    "Abril",
    "Maio",    "Junho",     "Julho",    "Agosto",
    "Setembro","Outubro",   "Novembro", "Dezembro",
]

# Labels legíveis para exibição
LABEL_TIPO_CUSTO: dict[str, str] = {
    "fixo":    "Fixo",
    "variavel": "Variável",
}

LABEL_TIPO_RECEITA: dict[str, str] = {
    "clt":        "CLT",
    "freela":     "Freela / Serviço",
    "aluguel":    "Aluguel recebido",
    "dividendos": "Dividendos / Investimentos",
    "outro":      "Outro",
}

LABEL_TIPO_DIVIDA: dict[str, str] = {
    "cartao":        "Cartão de Crédito",
    "emprestimo":    "Empréstimo",
    "financiamento": "Financiamento",
    "outro":         "Outro",
}

LABEL_STATUS_CONTA: dict[str, str] = {
    "pendente":  "Pendente",
    "pago":      "Pago",
    "cancelado": "Cancelado",
}

# ---------------------------------------------------------------------------
# Investimentos — domínio
# ---------------------------------------------------------------------------

TIPOS_ATIVO = ["acao", "etf", "fii", "cdb", "tesouro", "fundo", "cripto", "outro"]

LABEL_TIPO_ATIVO: dict[str, str] = {
    "acao":    "Ação",
    "etf":     "ETF",
    "fii":     "FII",
    "cdb":     "CDB",
    "tesouro": "Tesouro Direto",
    "fundo":   "Fundo",
    "cripto":  "Cripto",
    "outro":   "Outro",
}

TIPOS_CONTA_INV = ["corretora", "banco", "tesouro", "outro"]

LABEL_TIPO_CONTA_INV: dict[str, str] = {
    "corretora": "Corretora",
    "banco":     "Banco / Financeira",
    "tesouro":   "Tesouro Direto",
    "outro":     "Outro",
}

TIPOS_MOVIMENTACAO_INV = [
    "compra", "venda", "aplicacao", "resgate",
    "dividendo", "jcp", "juros", "amortizacao", "taxa", "imposto",
]

LABEL_TIPO_MOV_INV: dict[str, str] = {
    "compra":       "Compra",
    "venda":        "Venda",
    "aplicacao":    "Aplicação",
    "resgate":      "Resgate",
    "dividendo":    "Dividendo",
    "jcp":          "JCP",
    "juros":        "Juros / Rendimento",
    "amortizacao":  "Amortização",
    "taxa":         "Taxa",
    "imposto":      "Imposto (IR/DARF)",
}

INDEXADORES_RF = ["cdi", "selic", "ipca", "prefixado", "igpm", "dolar", "outro"]

LABEL_INDEXADOR: dict[str, str] = {
    "cdi":       "CDI",
    "selic":     "SELIC",
    "ipca":      "IPCA",
    "prefixado": "Prefixado",
    "igpm":      "IGPM",
    "dolar":     "Dólar",
    "outro":     "Outro",
}

# Tipos de movimentação que geram saída financeira
MOV_INV_SAIDA  = {"compra", "aplicacao", "taxa", "imposto"}
# Tipos de movimentação que geram entrada financeira
MOV_INV_ENTRADA = {"venda", "resgate", "dividendo", "jcp", "juros", "amortizacao"}

CORES_TIPO_ATIVO: dict[str, str] = {
    "acao":    "#1A56DB",
    "etf":     "#16A34A",
    "fii":     "#D97706",
    "cdb":     "#6D28D9",
    "tesouro": "#DC2626",
    "fundo":   "#0891B2",
    "cripto":  "#F59E0B",
    "outro":   "#6B7280",
}

# ---------------------------------------------------------------------------
# Formatação monetária
# ---------------------------------------------------------------------------

def formatar_moeda(valor: float) -> str:
    """Formata um float como moeda brasileira: R$ 1.234,56"""
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def mascara_moeda(entry) -> None:
    """
    Aplica máscara monetária a um CTkEntry em tempo real.
    Vincular ao evento <KeyRelease>. Digitar '1','0','0' → '1,00'.
    O valor é interpretado em centavos conforme os dígitos digitados.
    """
    raw = entry.get()
    digits = "".join(c for c in raw if c.isdigit())
    if not digits:
        novo = "0,00"
    else:
        cents = int(digits)
        reais = cents // 100
        centavos = cents % 100
        reais_fmt = f"{reais:,}".replace(",", ".")
        novo = f"{reais_fmt},{centavos:02d}"
    if novo != raw:
        entry.delete(0, "end")
        entry.insert(0, novo)


def formatar_data_exibicao(data_iso: str) -> str:
    """Converte YYYY-MM-DD para DD/MM/AAAA."""
    if not data_iso:
        return ""
    try:
        parts = data_iso.split("-")
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except (IndexError, AttributeError):
        return data_iso


def parsear_data(data_br: str) -> str:
    """Converte DD/MM/AAAA para YYYY-MM-DD para gravação no banco.

    Retorna string vazia se a entrada for vazia OU representar uma data inválida
    (ex.: "31/02/2025"). Callers usam `if not data_iso:` para detectar erro.
    """
    if not data_br:
        return ""
    try:
        from datetime import date as _date
        parts = data_br.split("/")
        if len(parts) != 3:
            return ""
        dia, mes, ano = int(parts[0]), int(parts[1]), int(parts[2])
        return _date(ano, mes, dia).isoformat()
    except (IndexError, AttributeError, ValueError, TypeError):
        return ""


if __name__ == "__main__":
    t = get_tema("claro")
    print("Tema claro:")
    for chave, valor in t.items():
        print(f"  {chave}: {valor}")

    print("\nTema escuro:")
    for chave, valor in get_tema("escuro").items():
        print(f"  {chave}: {valor}")

    print(f"\nExemplo formatar_moeda: {formatar_moeda(1234.56)}")
    print(f"Exemplo formatar_data:  {formatar_data_exibicao('2025-12-25')}")
