"""
visao_futura_view.py — Módulo Visão Financeira.
Planilha mês a mês com navegação temporal e expansão de sub-itens.
"""

from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from config import get_tema, formatar_moeda
from database import obter_configuracao
from views.visao_futura.projecao_model import (
    MesProjecao, DetalheProjecao, projetar, carregar_detalhes,
)


class VisaoFuturaView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="📊  Visão Financeira",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self._cores["texto"],
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 0))

        from views.widgets.ajuda import banner_ajuda
        _b = banner_ajuda(
            self, self._cores,
            "Projeção mês a mês dos próximos 5 anos. Cores indicam o saldo "
            "previsto: verde sobra, amarelo apertado, vermelho déficit. "
            "Clique em uma categoria para ver os sub-itens que a compõem.",
        )
        if _b:
            _b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))
            grid_row = 2
        else:
            grid_row = 1

        _ProjecaoTab(self, self._cores, grid_row=grid_row)


# ---------------------------------------------------------------------------
# Planilha de projeção
# ---------------------------------------------------------------------------

class _ProjecaoTab(ctk.CTkFrame):
    _HDR_H     = 34   # altura cabeçalho de meses
    _ROW_H     = 30   # altura de linha de categoria
    _SUB_ROW_H = 24   # altura de linha de sub-item
    _COL_W     = 95   # largura de cada coluna de mês
    _LBL_W     = 175  # largura da coluna fixa (um pouco maior para nomes)

    # (label, attr_MesProjecao, kind, detalhe_key)  — None = não expansível
    _LINHAS = [
        ("Receitas",     "receitas",        "receita",  "receitas"),
        ("Desp. Fixas",  "desp_fixas",      "despesa",  "desp_fixas"),
        ("Desp. Var.",   "desp_variaveis",  "variavel", "desp_variaveis"),
        ("Parc. Cartão", "parcelas_cartao", "despesa",  "parcelas_cartao"),
        ("Dívidas",      "dividas",         "despesa",  "dividas_items"),
        ("Total Saídas", "total_saidas",    "total",    None),
        ("Saldo",        "saldo",           "saldo",    None),
    ]

    _OFFSET_MIN = -60
    _OFFSET_MAX =  0

    def __init__(self, parent, cores: dict, grid_row: int = 0):
        super().__init__(parent, fg_color="transparent")
        self._cores            = cores
        self._offset           = 0
        self._expandido: set[str] = set()
        self._detalhes: DetalheProjecao | None = None
        self._ultima_projecao: list[MesProjecao] = []

        self.grid(row=grid_row, column=0, sticky="nsew", padx=16, pady=(4, 8))
        parent.grid_rowconfigure(grid_row, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_table_area()
        self._carregar()

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self):
        cores = self._cores
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 2))
        bar.grid_columnconfigure(0, weight=1)

        # Legenda de cores
        leg = ctk.CTkFrame(bar, fg_color="transparent")
        leg.grid(row=0, column=0, sticky="w")
        for cor, txt in [
            ("#DBEAFE", "Mês atual"),
            ("#DCFCE7", "Saldo positivo"),
            ("#FEF9C3", "Saldo baixo (< R$500)"),
            ("#FEE2E2", "Saldo negativo"),
        ]:
            ctk.CTkFrame(leg, width=11, height=11, fg_color=cor,
                         corner_radius=2).pack(side="left", padx=(8, 2))
            ctk.CTkLabel(leg, text=txt, font=ctk.CTkFont(size=11),
                         text_color=cores["texto_mudo"]).pack(side="left", padx=(0, 10))

        btns_dir = ctk.CTkFrame(bar, fg_color="transparent")
        btns_dir.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            btns_dir, text="⬇ Excel", width=80, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=12),
            command=self._exportar_excel,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            btns_dir, text="↺ Atualizar", width=95, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=12),
            command=self._carregar,
        ).pack(side="left")

        # Navegação temporal
        nav = ctk.CTkFrame(bar, fg_color="transparent")
        nav.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        btn_kw = dict(height=26, fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto_mudo"],
                      font=ctk.CTkFont(size=11))

        ctk.CTkButton(nav, text="◀◀ 5 anos", width=80, **btn_kw,
                      command=lambda: self._navegar(-60)).pack(side="left", padx=(0, 2))
        ctk.CTkButton(nav, text="◀ 1 ano", width=70, **btn_kw,
                      command=lambda: self._navegar(-12)).pack(side="left", padx=2)

        self._lbl_periodo = ctk.CTkLabel(
            nav, text="", width=200,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=cores["texto"],
        )
        self._lbl_periodo.pack(side="left", padx=10)

        ctk.CTkButton(nav, text="1 ano ▶", width=70, **btn_kw,
                      command=lambda: self._navegar(12)).pack(side="left", padx=2)
        ctk.CTkButton(nav, text="Hoje ↑", width=65, height=26,
                      font=ctk.CTkFont(size=11),
                      command=self._ir_hoje).pack(side="left", padx=(2, 0))

    # ------------------------------------------------------------------
    # Área da tabela
    # ------------------------------------------------------------------

    def _build_table_area(self):
        cores = self._cores

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        self._lbl_col = tk.Frame(outer, width=self._LBL_W, bg=cores["card"],
                                  bd=0, highlightthickness=0)
        self._lbl_col.grid(row=0, column=0, sticky="ns")
        self._lbl_col.grid_propagate(False)

        right = tk.Frame(outer, bg=cores["fundo"], bd=0, highlightthickness=0)
        right.grid(row=0, column=1, sticky="nsew")
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(right, bg=cores["fundo"], highlightthickness=0, bd=0)
        self._canvas.pack(side="top", fill="both", expand=True)

        hbar = tk.Scrollbar(right, orient="horizontal", command=self._canvas.xview)
        hbar.pack(side="bottom", fill="x")
        self._canvas.configure(xscrollcommand=hbar.set)

        self._inner = tk.Frame(self._canvas, bg=cores["fundo"], bd=0, highlightthickness=0)
        self._canvas_win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(self._canvas_win, height=e.height))
        self._canvas.bind("<MouseWheel>", self._on_mousewheel_h)
        self._inner.bind("<MouseWheel>", self._on_mousewheel_h)

    def _on_mousewheel_h(self, event):
        self._canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    # ------------------------------------------------------------------
    # Navegação temporal
    # ------------------------------------------------------------------

    def _navegar(self, delta: int):
        self._offset = max(self._OFFSET_MIN, min(self._OFFSET_MAX, self._offset + delta))
        self._detalhes = None   # invalida cache ao mudar período
        self._carregar()

    def _exportar_excel(self):
        from tkinter import filedialog as fd
        import tkinter.messagebox as mb
        dest = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="projecao_financeira.xlsx",
        )
        if not dest:
            return
        try:
            from views.exportar.exportar_model import exportar_projecao_xlsx
            exportar_projecao_xlsx(dest, meses=60)
            mb.showinfo("Exportação", "Projeção exportada com sucesso.")
        except Exception as e:
            mb.showerror("Erro", f"Erro ao exportar: {e}")

    def _ir_hoje(self):
        self._offset = 0
        self._detalhes = None
        self._carregar()

    # ------------------------------------------------------------------
    # Toggle de expansão
    # ------------------------------------------------------------------

    def _toggle_expand(self, detalhe_key: str):
        if detalhe_key in self._expandido:
            self._expandido.discard(detalhe_key)
        else:
            self._expandido.add(detalhe_key)
            if self._detalhes is None and self._ultima_projecao:
                self._detalhes = carregar_detalhes(self._ultima_projecao)
        self._rebuild_table()

    # ------------------------------------------------------------------
    # Render list: lista plana de linhas a renderizar
    # ------------------------------------------------------------------

    def _compute_render_rows(self) -> list[dict]:
        """Retorna lista ordenada de linhas (cabeçalho + sub-itens expandidos)."""
        rows = []
        for li, (label, attr, kind, detalhe_key) in enumerate(self._LINHAS):
            expandavel = detalhe_key is not None
            expandido  = expandavel and detalhe_key in self._expandido
            rows.append({
                "tipo": "header", "li": li,
                "label": label, "attr": attr, "kind": kind,
                "detalhe_key": detalhe_key,
                "expandavel": expandavel, "expandido": expandido,
            })
            if expandido and self._detalhes:
                sub_dict = getattr(self._detalhes, detalhe_key, {})
                for si, (sub_nome, vals) in enumerate(sub_dict.items()):
                    if any(v != 0 for v in vals):   # omite linhas totalmente zeradas
                        rows.append({
                            "tipo": "sub", "li": li, "si": si,
                            "label": sub_nome, "kind": kind, "valores": vals,
                        })
        return rows

    # ------------------------------------------------------------------
    # Carga principal
    # ------------------------------------------------------------------

    def _carregar(self):
        projecao = projetar(60, inicio_offset=self._offset)
        self._ultima_projecao = projecao

        # Invalida cache de detalhes ao atualizar
        self._detalhes = None

        if projecao:
            self._lbl_periodo.configure(
                text=f"{projecao[0].label}  →  {projecao[-1].label}"
            )

        self._rebuild_table(projecao)

        if self._offset < 0 and projecao:
            col_atual = -self._offset
            frac = col_atual / len(projecao)
            self.after(80, lambda: self._canvas.xview_moveto(max(0.0, frac - 0.15)))

    def _rebuild_table(self, projecao: list[MesProjecao] | None = None):
        """Reconstrói a tabela preservando a projeção atual."""
        if projecao is None:
            projecao = self._ultima_projecao

        for w in self._lbl_col.winfo_children():
            w.destroy()
        for w in self._inner.winfo_children():
            w.destroy()

        render_rows = self._compute_render_rows()

        self._build_label_column(render_rows)
        self._build_month_columns(projecao, render_rows)

        n_hdr = sum(1 for r in render_rows if r["tipo"] == "header")
        n_sub = sum(1 for r in render_rows if r["tipo"] == "sub")
        table_h = self._HDR_H + n_hdr * self._ROW_H + n_sub * self._SUB_ROW_H
        self._canvas.configure(height=table_h)
        self._lbl_col.configure(height=table_h)

    # ------------------------------------------------------------------
    # Coluna fixa de categorias
    # ------------------------------------------------------------------

    def _build_label_column(self, render_rows: list[dict]):
        cores = self._cores
        W = self._LBL_W

        def _frame(parent, h, bg):
            f = tk.Frame(parent, width=W, height=h, bg=bg,
                         bd=0, highlightthickness=0)
            f.pack(fill="x")
            f.pack_propagate(False)
            return f

        # Cabeçalho
        hdr = _frame(self._lbl_col, self._HDR_H, cores["card"])
        tk.Label(hdr, text="Categoria", bg=cores["card"],
                 fg=cores["texto_mudo"], font=("Helvetica", 9, "bold"),
                 anchor="w", bd=0, highlightthickness=0,
                 ).pack(fill="both", expand=True, padx=10)

        for row in render_rows:
            kind = row["kind"]

            if row["tipo"] == "header":
                li   = row["li"]
                bg   = self._row_bg(li, kind, is_atual=False)
                bold = kind in ("total", "saldo")

                cell = _frame(self._lbl_col, self._ROW_H, bg)

                if row["expandavel"]:
                    tri = "▼" if row["expandido"] else "▶"
                    key = row["detalhe_key"]

                    # Usa Label (não Button) para evitar padding do OS
                    tri_lbl = tk.Label(
                        cell, text=tri, bg=bg, fg=cores["primario"],
                        font=("Helvetica", 9), cursor="hand2",
                        bd=0, highlightthickness=0,
                    )
                    tri_lbl.pack(side="left", padx=(6, 1))

                    txt_lbl = tk.Label(
                        cell, text=row["label"], bg=bg, fg=cores["texto"],
                        font=("Helvetica", 10, "bold" if bold else "normal"),
                        anchor="w", cursor="hand2",
                        bd=0, highlightthickness=0,
                    )
                    txt_lbl.pack(side="left", fill="both", expand=True)

                    # Bind em toda a célula e nos dois labels
                    for w in (cell, tri_lbl, txt_lbl):
                        w.bind("<Button-1>", lambda e, k=key: self._toggle_expand(k))
                else:
                    tk.Label(
                        cell, text=row["label"], bg=bg, fg=cores["texto"],
                        font=("Helvetica", 10, "bold" if bold else "normal"),
                        anchor="w", bd=0, highlightthickness=0,
                    ).pack(fill="both", expand=True, padx=10)

            else:  # sub-item
                li  = row["li"]
                bg  = self._sub_bg(li)

                cell = _frame(self._lbl_col, self._SUB_ROW_H, bg)
                nome = row["label"]
                if len(nome) > 28:
                    nome = nome[:26] + "…"
                tk.Label(
                    cell, text=f"  · {nome}", bg=bg,
                    fg=cores["texto_mudo"], font=("Helvetica", 9),
                    anchor="w", bd=0, highlightthickness=0,
                ).pack(fill="both", expand=True, padx=4)

    # ------------------------------------------------------------------
    # Colunas de meses
    # ------------------------------------------------------------------

    def _build_month_columns(self, projecao: list[MesProjecao], render_rows: list[dict]):
        cores = self._cores
        W = self._COL_W

        # ── Força alturas exatas de cada linha do grid ────────────────────
        # Sem isso o grid manager varia 1-2px e desalinha com a coluna esquerda
        self._inner.grid_rowconfigure(0, minsize=self._HDR_H, pad=0)
        for gi, row in enumerate(render_rows, start=1):
            h = self._ROW_H if row["tipo"] == "header" else self._SUB_ROW_H
            self._inner.grid_rowconfigure(gi, minsize=h, pad=0)

        for col_i, m in enumerate(projecao):
            is_atual = (m.indice == 0)

            # Cabeçalho do mês
            hdr_bg  = "#DBEAFE" if is_atual else cores["card"]
            hdr_fg  = cores["primario"] if is_atual else cores["texto_mudo"]
            hdr_txt = f"★ {m.label}" if is_atual else m.label

            hdr = tk.Frame(self._inner, width=W, height=self._HDR_H, bg=hdr_bg,
                           bd=0, highlightthickness=0)
            hdr.grid(row=0, column=col_i, padx=1, pady=0, sticky="nsew")
            hdr.grid_propagate(False)
            tk.Label(hdr, text=hdr_txt, bg=hdr_bg, fg=hdr_fg,
                     font=("Helvetica", 9, "bold" if is_atual else "normal"),
                     anchor="center", bd=0, highlightthickness=0,
                     ).pack(fill="both", expand=True, padx=2)

            for grid_row, row in enumerate(render_rows, start=1):
                kind = row["kind"]

                if row["tipo"] == "header":
                    li   = row["li"]
                    attr = row["attr"]
                    val  = getattr(m, attr)
                    bg   = self._row_bg(li, kind, is_atual=is_atual)
                    bold = kind in ("total", "saldo")
                    h    = self._ROW_H

                    if attr == "saldo":
                        fg = cores["positivo"] if val >= 0 else cores["alerta"]
                    elif kind in ("total", "saldo"):
                        fg = cores["texto"]
                    elif attr == "desp_variaveis" and m.is_futuro:
                        fg = cores["texto_mudo"]
                    else:
                        fg = cores["texto"]

                    txt  = formatar_moeda(val)
                    font = ("Helvetica", 10, "bold" if bold else "normal")

                else:  # sub-item
                    li   = row["li"]
                    vals = row["valores"]
                    val  = vals[col_i] if col_i < len(vals) else 0.0
                    bg   = self._sub_bg(li, is_atual=is_atual)
                    bold = False
                    h    = self._SUB_ROW_H
                    fg   = cores["texto_mudo"] if val == 0 else cores["texto"]
                    txt  = "—" if val == 0 else formatar_moeda(val)
                    font = ("Helvetica", 9)

                cell = tk.Frame(self._inner, width=W, height=h, bg=bg,
                                bd=0, highlightthickness=0)
                cell.grid(row=grid_row, column=col_i, padx=1, pady=0, sticky="nsew")
                cell.grid_propagate(False)
                tk.Label(cell, text=txt, bg=bg, fg=fg, font=font,
                         anchor="e", bd=0, highlightthickness=0,
                         ).pack(fill="both", expand=True, padx=6)
                cell.bind("<MouseWheel>",
                          lambda e: self._canvas.xview_scroll(
                              int(-1 * (e.delta / 120)), "units"))

    # ------------------------------------------------------------------
    # Cores de fundo
    # ------------------------------------------------------------------

    def _row_bg(self, row_i: int, kind: str, is_atual: bool) -> str:
        cores = self._cores
        if is_atual:
            return "#DBEAFE" if kind not in ("total", "saldo") else "#BFDBFE"
        if kind in ("total", "saldo"):
            return cores["sidebar"] if "sidebar" in cores else cores["borda"]
        return cores["card"] if row_i % 2 == 0 else cores["fundo"]

    def _sub_bg(self, parent_li: int, is_atual: bool = False) -> str:
        cores = self._cores
        if is_atual:
            return "#E0EDFF"
        # Slightly distinct from parent row
        return "#F5F7FA" if parent_li % 2 == 0 else "#EEEFF2"
