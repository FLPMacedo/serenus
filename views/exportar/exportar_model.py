"""
exportar_model.py — Exportação de dados para Excel (.xlsx) via openpyxl.

Funções públicas:
    exportar_extrato_xlsx(mes, ano, caminho)
    exportar_carteira_xlsx(caminho)
    exportar_fatura_xlsx(cartao_id, mes, ano, caminho)
"""
from __future__ import annotations
from datetime import date

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from database import conectar


# ─────────────────────────────────────────────────────────────────────────────
# Estilos
# ─────────────────────────────────────────────────────────────────────────────

_FILL_HEADER = PatternFill("solid", fgColor="1E3A5F")
_FONT_HEADER = Font(bold=True, color="FFFFFF", size=11)
_FONT_TOTAL  = Font(bold=True, size=11)
_FILL_TOTAL  = PatternFill("solid", fgColor="E8F0FE")
_ALIGN_CTR   = Alignment(horizontal="center", vertical="center")
_ALIGN_R     = Alignment(horizontal="right",  vertical="center")
_BORDER_THIN = Border(
    bottom=Side(style="thin", color="CCCCCC"),
)
_FILL_ALT    = PatternFill("solid", fgColor="F8FAFC")


def _estilo_header(ws, colunas: list[tuple[str, int]]):
    """Aplica estilo na linha 1 e ajusta larguras das colunas."""
    for col_idx, (titulo, largura) in enumerate(colunas, start=1):
        cell = ws.cell(row=1, column=col_idx, value=titulo)
        cell.font      = _FONT_HEADER
        cell.fill      = _FILL_HEADER
        cell.alignment = _ALIGN_CTR
        ws.column_dimensions[get_column_letter(col_idx)].width = largura
    ws.row_dimensions[1].height = 22


def _cel_moeda(ws, row, col, valor: float):
    cell = ws.cell(row=row, column=col, value=valor)
    cell.number_format = 'R#,##0.00'
    cell.alignment = _ALIGN_R
    return cell


def _linha_alternada(ws, row: int, n_cols: int):
    if row % 2 == 0:
        for c in range(1, n_cols + 1):
            ws.cell(row=row, column=c).fill = _FILL_ALT


# ─────────────────────────────────────────────────────────────────────────────
# Extrato mensal
# ─────────────────────────────────────────────────────────────────────────────

def exportar_extrato_xlsx(mes: int, ano: int, caminho: str) -> None:
    from views.fluxo_caixa.extrato_model import extrato_mes, resumo_extrato

    linhas = extrato_mes(mes, ano)

    COLS = [
        ("Data",       12),
        ("Descrição",  35),
        ("Categoria",  20),
        ("Débito",     14),
        ("Crédito",    14),
        ("Saldo",      14),
        ("Status",     12),
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Extrato {mes:02d}-{ano}"

    _estilo_header(ws, COLS)
    ws.freeze_panes = "A2"

    for i, linha in enumerate(linhas, start=2):
        data_fmt = _iso_para_br(linha.data)
        ws.cell(row=i, column=1, value=data_fmt).alignment = _ALIGN_CTR
        ws.cell(row=i, column=2, value=linha.descricao)
        ws.cell(row=i, column=3, value=linha.categoria)
        _cel_moeda(ws, i, 4, linha.debito  or None)
        _cel_moeda(ws, i, 5, linha.credito or None)
        _cel_moeda(ws, i, 6, linha.saldo)
        ws.cell(row=i, column=7, value=linha.status).alignment = _ALIGN_CTR
        _linha_alternada(ws, i, len(COLS))

    # Linha de totais
    if linhas:
        res = resumo_extrato(linhas)
        tot_row = len(linhas) + 2
        ws.cell(row=tot_row, column=2, value="TOTAL").font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 4, res["debito"]).font  = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 5, res["credito"]).font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 6, res["saldo"]).font   = _FONT_TOTAL
        for c in range(1, len(COLS) + 1):
            ws.cell(row=tot_row, column=c).fill = _FILL_TOTAL

    wb.save(caminho)


# ─────────────────────────────────────────────────────────────────────────────
# Carteira de investimentos
# ─────────────────────────────────────────────────────────────────────────────

def exportar_carteira_xlsx(caminho: str) -> None:
    from views.investimentos.investimento_model import listar_posicoes

    posicoes = listar_posicoes(apenas_com_saldo=False)

    COLS = [
        ("Código",          10),
        ("Nome",            28),
        ("Tipo",            10),
        ("Conta",           20),
        ("Qtd. Atual",      12),
        ("Custo Médio",     13),
        ("Valor Investido", 16),
        ("Valor Atual",     14),
        ("L/P Realizado",   15),
        ("L/P Não Real.",   15),
        ("Rent. %",         10),
        ("Rendimentos",     14),
        ("Vencimento",      13),
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Carteira"

    _estilo_header(ws, COLS)
    ws.freeze_panes = "A2"

    for i, p in enumerate(posicoes, start=2):
        ws.cell(row=i, column=1,  value=p.codigo).alignment = _ALIGN_CTR
        ws.cell(row=i, column=2,  value=p.nome)
        ws.cell(row=i, column=3,  value=p.tipo).alignment = _ALIGN_CTR
        ws.cell(row=i, column=4,  value=p.conta_nome)
        _cel_moeda(ws, i, 5,  p.quantidade_atual)
        _cel_moeda(ws, i, 6,  p.custo_medio)
        _cel_moeda(ws, i, 7,  p.valor_investido)
        _cel_moeda(ws, i, 8,  p.valor_atual)
        _cel_moeda(ws, i, 9,  p.lucro_realizado)
        _cel_moeda(ws, i, 10, p.lucro_nao_realizado)
        cell_rent = ws.cell(row=i, column=11, value=round(p.rentabilidade_pct, 2))
        cell_rent.number_format = '0.00"%"'
        cell_rent.alignment = _ALIGN_R
        _cel_moeda(ws, i, 12, p.rendimentos_recebidos)
        ws.cell(row=i, column=13, value=p.vencimento or "").alignment = _ALIGN_CTR
        _linha_alternada(ws, i, len(COLS))

    wb.save(caminho)


# ─────────────────────────────────────────────────────────────────────────────
# Fatura do cartão
# ─────────────────────────────────────────────────────────────────────────────

def exportar_fatura_xlsx(cartao_id: int, mes: int, ano: int, caminho: str) -> None:
    mes_ref = f"{ano:04d}-{mes:02d}"

    with conectar() as conn:
        rows = conn.execute("""
            SELECT p.numero_parcela, c.total_parcelas,
                   c.descricao, c.estabelecimento, c.categoria,
                   p.valor, p.status, p.mes_referencia
            FROM   parcelas_cartao p
            JOIN   compras_cartao  c ON c.id = p.compra_id
            WHERE  p.cartao_id = ? AND p.mes_referencia = ?
            ORDER  BY c.descricao, p.numero_parcela
        """, (cartao_id, mes_ref)).fetchall()

        cartao = conn.execute(
            "SELECT nome FROM cartoes WHERE id=?", (cartao_id,)
        ).fetchone()

    COLS = [
        ("Descrição",      30),
        ("Estabelecimento",22),
        ("Categoria",      16),
        ("Parcela",         9),
        ("Valor",          13),
        ("Status",         12),
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Fatura {mes:02d}-{ano}"

    # Título
    nome_cartao = cartao["nome"] if cartao else f"Cartão {cartao_id}"
    ws.merge_cells(f"A1:{get_column_letter(len(COLS))}1")
    titulo = ws.cell(row=1, column=1,
                     value=f"{nome_cartao} — Fatura {mes:02d}/{ano}")
    titulo.font      = Font(bold=True, size=13, color="1E3A5F")
    titulo.alignment = _ALIGN_CTR
    ws.row_dimensions[1].height = 24

    _estilo_header_row(ws, 2, COLS)
    ws.freeze_panes = "A3"

    total = 0.0
    for i, r in enumerate(rows, start=3):
        parc_str = f"{r['numero_parcela']}/{r['total_parcelas']}"
        ws.cell(row=i, column=1, value=r["descricao"])
        ws.cell(row=i, column=2, value=r["estabelecimento"] or "")
        ws.cell(row=i, column=3, value=r["categoria"] or "")
        ws.cell(row=i, column=4, value=parc_str).alignment = _ALIGN_CTR
        _cel_moeda(ws, i, 5, r["valor"])
        ws.cell(row=i, column=6, value=r["status"]).alignment = _ALIGN_CTR
        _linha_alternada(ws, i, len(COLS))
        total += r["valor"]

    if rows:
        tot_row = len(rows) + 3
        ws.cell(row=tot_row, column=1, value="TOTAL").font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 5, total).font = _FONT_TOTAL
        for c in range(1, len(COLS) + 1):
            ws.cell(row=tot_row, column=c).fill = _FILL_TOTAL

    wb.save(caminho)


def _estilo_header_row(ws, row: int, colunas: list[tuple[str, int]]):
    for col_idx, (titulo, largura) in enumerate(colunas, start=1):
        cell = ws.cell(row=row, column=col_idx, value=titulo)
        cell.font      = _FONT_HEADER
        cell.fill      = _FILL_HEADER
        cell.alignment = _ALIGN_CTR
        ws.column_dimensions[get_column_letter(col_idx)].width = largura
    ws.row_dimensions[row].height = 22


# ─────────────────────────────────────────────────────────────────────────────

def _iso_para_br(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
        return d.strftime("%d/%m/%Y")
    except Exception:
        return iso


# ─────────────────────────────────────────────────────────────────────────────
# Contas a Pagar
# ─────────────────────────────────────────────────────────────────────────────

def exportar_contas_pagar_xlsx(mes: int, ano: int, caminho: str) -> None:
    from views.contas_pagar.conta_model import listar_contas, totais_periodo
    from config import LABEL_TIPO_CUSTO

    contas = listar_contas(mes, ano)

    COLS = [
        ("Conta",        25),
        ("Descrição",    30),
        ("Tipo",         10),
        ("Valor",        13),
        ("Vencimento",   13),
        ("Pagamento",    13),
        ("Status",       12),
        ("Recorrente",   12),
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Despesas {mes:02d}-{ano}"

    _estilo_header(ws, COLS)
    ws.freeze_panes = "A2"

    for i, c in enumerate(contas, start=2):
        ws.cell(row=i, column=1, value=c.plano_nome or "—")
        ws.cell(row=i, column=2, value=c.descricao or "—")
        ws.cell(row=i, column=3, value=LABEL_TIPO_CUSTO.get(c.plano_tipo, "—")).alignment = _ALIGN_CTR
        _cel_moeda(ws, i, 4, c.valor)
        ws.cell(row=i, column=5, value=_iso_para_br(c.data_vencimento)).alignment = _ALIGN_CTR
        pag = getattr(c, "data_pagamento", None)
        ws.cell(row=i, column=6, value=_iso_para_br(pag) if pag else "").alignment = _ALIGN_CTR
        ws.cell(row=i, column=7, value=c.status.capitalize()).alignment = _ALIGN_CTR
        ws.cell(row=i, column=8, value="Sim" if c.recorrente else "Não").alignment = _ALIGN_CTR
        _linha_alternada(ws, i, len(COLS))

    if contas:
        tots = totais_periodo(mes, ano)
        tot_row = len(contas) + 2
        ws.cell(row=tot_row, column=1, value="TOTAL").font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 4, tots["total"]).font = _FONT_TOTAL
        for c in range(1, len(COLS) + 1):
            ws.cell(row=tot_row, column=c).fill = _FILL_TOTAL

    # Aba Resumo
    tots = totais_periodo(mes, ano)
    ws_res = wb.create_sheet("Resumo")
    _estilo_header(ws_res, [("Status", 20), ("Valor", 15)])
    linhas_resumo = [
        ("Pendente", tots["pendente"]),
        ("Pago",     tots["pago"]),
        ("Total",    tots["total"]),
    ]
    for i, (label, valor) in enumerate(linhas_resumo, start=2):
        ws_res.cell(row=i, column=1, value=label)
        _cel_moeda(ws_res, i, 2, valor)
        if label == "Total":
            ws_res.cell(row=i, column=1).font = _FONT_TOTAL
            _cel_moeda(ws_res, i, 2, valor).font = _FONT_TOTAL
            for col in range(1, 3):
                ws_res.cell(row=i, column=col).fill = _FILL_TOTAL

    wb.save(caminho)


# ─────────────────────────────────────────────────────────────────────────────
# Dívidas
# ─────────────────────────────────────────────────────────────────────────────

def exportar_dividas_xlsx(caminho: str) -> None:
    from views.visao_longo_prazo.divida_model import (
        listar_dividas, resumo_dividas, projetar_evolucao,
    )

    dividas = listar_dividas(apenas_ativas=True)

    COLS_DIV = [
        ("Nome",        25),
        ("Tipo",        14),
        ("Saldo Atual", 14),
        ("Parcela/Mês", 13),
        ("Pagas",       10),
        ("Restantes",   11),
        ("Taxa % a.m.", 13),
        ("Quitação",    13),
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dívidas Ativas"

    _estilo_header(ws, COLS_DIV)
    ws.freeze_panes = "A2"

    for i, d in enumerate(dividas, start=2):
        ws.cell(row=i, column=1, value=d.nome)
        ws.cell(row=i, column=2, value=d.tipo).alignment = _ALIGN_CTR
        _cel_moeda(ws, i, 3, d.saldo_atual)
        _cel_moeda(ws, i, 4, d.parcela_mensal)
        ws.cell(row=i, column=5, value=d.parcelas_pagas).alignment = _ALIGN_CTR
        ws.cell(row=i, column=6, value=d.parcelas_restantes).alignment = _ALIGN_CTR
        cell_taxa = ws.cell(row=i, column=7, value=round(d.taxa_juros, 4))
        cell_taxa.number_format = '0.00"%"'
        cell_taxa.alignment = _ALIGN_R
        ws.cell(row=i, column=8, value=d.fim_previsto_str).alignment = _ALIGN_CTR
        _linha_alternada(ws, i, len(COLS_DIV))

    if dividas:
        res = resumo_dividas(dividas)
        tot_row = len(dividas) + 2
        ws.cell(row=tot_row, column=1, value="TOTAL").font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 3, res["total_saldo"]).font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 4, res["total_parcelas"]).font = _FONT_TOTAL
        for c in range(1, len(COLS_DIV) + 1):
            ws.cell(row=tot_row, column=c).fill = _FILL_TOTAL

    # Aba Projeção
    ws_proj = wb.create_sheet("Projeção")
    COLS_PROJ = [("Mês", 12), ("Saldo Total", 15)]
    _estilo_header(ws_proj, COLS_PROJ)
    ws_proj.freeze_panes = "A2"

    if dividas:
        proj = projetar_evolucao(dividas, meses=36)
        for i, p in enumerate(proj, start=2):
            ws_proj.cell(row=i, column=1, value=p["label"]).alignment = _ALIGN_CTR
            _cel_moeda(ws_proj, i, 2, p["saldo"])
            _linha_alternada(ws_proj, i, 2)

    wb.save(caminho)


# ─────────────────────────────────────────────────────────────────────────────
# Receitas
# ─────────────────────────────────────────────────────────────────────────────

def exportar_receitas_xlsx(caminho: str) -> None:
    from views.receitas.receita_model import listar_fontes, listar_receitas_especiais
    from config import NOMES_MESES

    fontes   = listar_fontes()
    especiais = listar_receitas_especiais()

    COLS_F = [
        ("Nome",         25),
        ("Tipo",         12),
        ("Valor Mensal", 14),
        ("Periodicidade",14),
        ("Ativa",         8),
        ("Observação",   30),
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fontes de Receita"

    _estilo_header(ws, COLS_F)
    ws.freeze_panes = "A2"

    total_fontes = 0.0
    for i, f in enumerate(fontes, start=2):
        ws.cell(row=i, column=1, value=f.nome)
        ws.cell(row=i, column=2, value=f.tipo).alignment = _ALIGN_CTR
        _cel_moeda(ws, i, 3, f.valor_mensal)
        ws.cell(row=i, column=4, value=f.periodicidade).alignment = _ALIGN_CTR
        ws.cell(row=i, column=5, value="Sim" if f.ativa else "Não").alignment = _ALIGN_CTR
        ws.cell(row=i, column=6, value=f.observacao)
        _linha_alternada(ws, i, len(COLS_F))
        total_fontes += f.valor_mensal

    if fontes:
        tot_row = len(fontes) + 2
        ws.cell(row=tot_row, column=1, value="TOTAL").font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 3, total_fontes).font = _FONT_TOTAL
        for c in range(1, len(COLS_F) + 1):
            ws.cell(row=tot_row, column=c).fill = _FILL_TOTAL

    # Aba Receitas Especiais
    COLS_E = [
        ("Nome",        25),
        ("Mês",         12),
        ("Valor",       13),
        ("Tipo",        12),
        ("Recorrente",  12),
        ("Observação",  30),
    ]

    ws_esp = wb.create_sheet("Receitas Especiais")
    _estilo_header(ws_esp, COLS_E)
    ws_esp.freeze_panes = "A2"

    total_especiais = 0.0
    for i, e in enumerate(especiais, start=2):
        ws_esp.cell(row=i, column=1, value=e.nome)
        nome_mes = NOMES_MESES[e.mes] if 0 <= e.mes <= 11 else f"Mês {e.mes}"
        ws_esp.cell(row=i, column=2, value=nome_mes).alignment = _ALIGN_CTR
        _cel_moeda(ws_esp, i, 3, e.valor)
        ws_esp.cell(row=i, column=4, value=e.tipo).alignment = _ALIGN_CTR
        ws_esp.cell(row=i, column=5, value="Sim" if e.recorrente_anual else "Não").alignment = _ALIGN_CTR
        ws_esp.cell(row=i, column=6, value=e.observacao)
        _linha_alternada(ws_esp, i, len(COLS_E))
        total_especiais += e.valor

    if especiais:
        tot_row_e = len(especiais) + 2
        ws_esp.cell(row=tot_row_e, column=1, value="TOTAL").font = _FONT_TOTAL
        _cel_moeda(ws_esp, tot_row_e, 3, total_especiais).font = _FONT_TOTAL
        for c in range(1, len(COLS_E) + 1):
            ws_esp.cell(row=tot_row_e, column=c).fill = _FILL_TOTAL

    wb.save(caminho)


# ─────────────────────────────────────────────────────────────────────────────
# Projeção 5 anos
# ─────────────────────────────────────────────────────────────────────────────

def exportar_projecao_xlsx(caminho: str, meses: int = 60) -> None:
    from views.visao_futura.projecao_model import projetar

    projecao = projetar(meses=meses)

    COLS = [
        ("Mês",           12),
        ("Receitas",      14),
        ("Desp. Fixas",   14),
        ("Desp. Var.",    12),
        ("Parc. Cartão",  14),
        ("Dívidas",       12),
        ("Total Saídas",  14),
        ("Saldo",         13),
    ]

    _FILL_NEG = PatternFill("solid", fgColor="FEE2E2")
    _FILL_POS = PatternFill("solid", fgColor="DCFCE7")
    _FILL_ATU = PatternFill("solid", fgColor="DBEAFE")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Projeção {meses} Meses"

    _estilo_header(ws, COLS)
    ws.freeze_panes = "B2"

    for i, m in enumerate(projecao, start=2):
        ws.cell(row=i, column=1, value=m.label).alignment = _ALIGN_CTR
        _cel_moeda(ws, i, 2, m.receitas)
        _cel_moeda(ws, i, 3, m.desp_fixas)
        _cel_moeda(ws, i, 4, m.desp_variaveis)
        _cel_moeda(ws, i, 5, m.parcelas_cartao)
        _cel_moeda(ws, i, 6, m.dividas)
        _cel_moeda(ws, i, 7, m.total_saidas)
        _cel_moeda(ws, i, 8, m.saldo)

        if m.indice == 0:
            fill = _FILL_ATU
        elif m.saldo < 0:
            fill = _FILL_NEG
        elif m.saldo >= 500:
            fill = _FILL_POS
        else:
            fill = _FILL_ALT

        for c in range(1, len(COLS) + 1):
            ws.cell(row=i, column=c).fill = fill

    wb.save(caminho)


# ─────────────────────────────────────────────────────────────────────────────
# Metas financeiras
# ─────────────────────────────────────────────────────────────────────────────

def exportar_metas_xlsx(caminho: str) -> None:
    from views.metas.metas_model import listar_metas

    metas = listar_metas()

    COLS = [
        ("Nome",            25),
        ("Valor Alvo",      13),
        ("Valor Atual",     13),
        ("Progresso %",     13),
        ("Prazo",           13),
        ("Dias Restantes",  15),
        ("Economia/Mês",    14),
        ("Concluída",       11),
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Metas"

    _estilo_header(ws, COLS)
    ws.freeze_panes = "A2"

    total_alvo = total_atual = 0.0
    for i, m in enumerate(metas, start=2):
        ws.cell(row=i, column=1, value=m.nome)
        _cel_moeda(ws, i, 2, m.valor_alvo)
        _cel_moeda(ws, i, 3, m.valor_atual)
        cell_pct = ws.cell(row=i, column=4, value=round(m.progresso_pct, 1))
        cell_pct.number_format = '0.0"%"'
        cell_pct.alignment = _ALIGN_R
        ws.cell(row=i, column=5,
                value=_iso_para_br(m.prazo) if m.prazo else "—").alignment = _ALIGN_CTR
        dias = m.dias_restantes
        ws.cell(row=i, column=6,
                value=dias if dias is not None else "—").alignment = _ALIGN_CTR
        _cel_moeda(ws, i, 7, m.economia_mensal_necessaria or 0.0)
        ws.cell(row=i, column=8,
                value="Sim" if m.concluida else "Não").alignment = _ALIGN_CTR
        _linha_alternada(ws, i, len(COLS))
        total_alvo  += m.valor_alvo
        total_atual += m.valor_atual

    if metas:
        tot_row = len(metas) + 2
        ws.cell(row=tot_row, column=1, value="TOTAL").font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 2, total_alvo).font  = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 3, total_atual).font = _FONT_TOTAL
        for c in range(1, len(COLS) + 1):
            ws.cell(row=tot_row, column=c).fill = _FILL_TOTAL

    wb.save(caminho)


# ─────────────────────────────────────────────────────────────────────────────
# IR Estimado
# ─────────────────────────────────────────────────────────────────────────────

def exportar_ir_xlsx(caminho: str) -> None:
    from views.investimentos.ir_model import resumo_ir_carteira

    resumo   = resumo_ir_carteira()
    detalhes = resumo["detalhes"]

    COLS = [
        ("Código",          10),
        ("Nome",            28),
        ("Tipo",            10),
        ("Lucro Realizado", 16),
        ("Alíquota %",      12),
        ("IR Estimado",     14),
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "IR Estimado"

    _estilo_header(ws, COLS)
    ws.freeze_panes = "A2"

    for i, d in enumerate(detalhes, start=2):
        ws.cell(row=i, column=1, value=d["codigo"]).alignment = _ALIGN_CTR
        ws.cell(row=i, column=2, value=d["nome"])
        ws.cell(row=i, column=3, value=d["tipo"]).alignment = _ALIGN_CTR
        _cel_moeda(ws, i, 4, d["lucro"])
        cell_aliq = ws.cell(row=i, column=5, value=round(d["aliquota"] * 100, 1))
        cell_aliq.number_format = '0.0"%"'
        cell_aliq.alignment = _ALIGN_R
        _cel_moeda(ws, i, 6, d["ir"])
        _linha_alternada(ws, i, len(COLS))

    if detalhes:
        tot_row = len(detalhes) + 2
        ws.cell(row=tot_row, column=1, value="TOTAL").font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 4, resumo["total_lucro"]).font = _FONT_TOTAL
        _cel_moeda(ws, tot_row, 6, resumo["total_ir"]).font = _FONT_TOTAL
        for c in range(1, len(COLS) + 1):
            ws.cell(row=tot_row, column=c).fill = _FILL_TOTAL

    if detalhes:
        nota_row = len(detalhes) + 3
        ws.cell(row=nota_row, column=1,
                value="Estimativa educacional. Consulte um contador para declaração oficial."
                ).font = Font(italic=True, color="888888", size=9)

    wb.save(caminho)


# ─────────────────────────────────────────────────────────────────────────────
# Template de importação de fatura
# ─────────────────────────────────────────────────────────────────────────────

def gerar_template_importacao_xlsx(caminho: str) -> None:
    """Gera planilha-modelo para importação de fatura de cartão."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fatura"

    colunas = ["descricao", "estabelecimento", "categoria", "parcela", "valor"]
    for col, nome in enumerate(colunas, start=1):
        cell = ws.cell(row=1, column=col, value=nome)
        cell.font      = _FONT_HEADER
        cell.fill      = _FILL_HEADER
        cell.alignment = _ALIGN_CTR

    # Larguras sugeridas
    larguras = [30, 25, 20, 10, 12]
    for i, w in enumerate(larguras, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Linha de exemplo comentada
    ws.cell(row=2, column=1, value="Netflix")
    ws.cell(row=2, column=2, value="Netflix Inc")
    ws.cell(row=2, column=3, value="Streaming")
    ws.cell(row=2, column=4, value="3/12")
    ws.cell(row=2, column=5, value=55.90)
    for col in range(1, 6):
        ws.cell(row=2, column=col).font = Font(italic=True, color="888888")

    wb.save(caminho)
