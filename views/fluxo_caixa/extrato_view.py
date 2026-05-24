"""
extrato_view.py — Fluxo de Caixa: extrato de transações com Débito, Crédito e Saldo.
"""

from __future__ import annotations
from datetime import date
import customtkinter as ctk
from config import get_tema, formatar_moeda, NOMES_MESES
from database import obter_configuracao
from views.fluxo_caixa.extrato_model import LinhaExtrato, extrato_mes, resumo_extrato, filtrar_extrato


_COLS = [
    ("Data",       90),
    ("Descrição",  230),
    ("Categoria",  140),
    ("Débito",     105),
    ("Crédito",    105),
    ("Saldo",      105),
]


class ExtratoCaixaView(ctk.CTkFrame):
    """Container do Fluxo de Caixa com 2 abas:
       - Movimentações (extrato consolidado de todas as origens)
       - Conciliação Bancária (extratos importados de bancos)
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._tabview = ctk.CTkTabview(self, fg_color="transparent")
        self._tabview.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._tabview.add("📋  Movimentações")
        self._tabview.add("🏦  Conciliação Bancária")

        # Aba 1: extrato consolidado (lógica atual)
        aba_mov = self._tabview.tab("📋  Movimentações")
        aba_mov.grid_columnconfigure(0, weight=1)
        aba_mov.grid_rowconfigure(0, weight=1)
        _AbaMovimentacoes(aba_mov).grid(row=0, column=0, sticky="nsew")

        # Aba 2: conciliação bancária (nova)
        aba_conc = self._tabview.tab("🏦  Conciliação Bancária")
        aba_conc.grid_columnconfigure(0, weight=1)
        aba_conc.grid_rowconfigure(0, weight=1)
        from views.fluxo_caixa.conciliacao_view import ConciliacaoView
        ConciliacaoView(aba_conc).grid(row=0, column=0, sticky="nsew")


class _AbaMovimentacoes(ctk.CTkFrame):
    """Aba 'Movimentações' — extrato consolidado de todas as origens
    (contas_pagar, fontes_receita, vendas, investimentos, lançamentos manuais).

    Conteúdo idêntico à versão original do ExtratoCaixaView.
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        hoje = date.today()
        self._mes = hoje.month
        self._ano = hoje.year

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_cards_area()
        self._build_tabela()
        self._carregar()

    # ------------------------------------------------------------------
    # Header: título + navegação de mês
    # ------------------------------------------------------------------

    def _build_header(self):
        cores = self._cores
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="🔄  Fluxo de Caixa",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=0, sticky="w")

        nav = ctk.CTkFrame(hdr, fg_color="transparent")
        nav.grid(row=0, column=2, sticky="e")

        ctk.CTkButton(
            nav, text="◀", width=32, height=32,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._mes_anterior,
        ).pack(side="left", padx=2)

        self._lbl_mes = ctk.CTkLabel(
            nav, text="", width=160,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=cores["texto"],
        )
        self._lbl_mes.pack(side="left", padx=4)

        ctk.CTkButton(
            nav, text="▶", width=32, height=32,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._mes_proximo,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            nav, text="Hoje", width=60, height=32,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=12),
            command=self._ir_hoje,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            nav, text="⬇ Excel", width=72, height=32,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=12),
            command=self._exportar_excel,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            nav, text="+  Lançar", width=86, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._novo_lancamento,
        ).pack(side="left", padx=(8, 0))

    # ------------------------------------------------------------------
    # Cards de resumo
    # ------------------------------------------------------------------

    def _build_cards_area(self):
        self._cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._cards_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 0))
        self._cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

    def _update_cards(self, resumo: dict):
        for w in self._cards_frame.winfo_children():
            w.destroy()

        cores = self._cores
        saldo = resumo["saldo"]
        cor_saldo = cores["positivo"] if saldo >= 0 else cores["alerta"]

        items = [
            ("💚  Total Entradas", formatar_moeda(resumo["credito"]), cores["positivo"]),
            ("🔴  Total Saídas",   formatar_moeda(resumo["debito"]),  cores["alerta"]),
            ("📊  Saldo do Mês",   formatar_moeda(saldo),             cor_saldo),
        ]
        for col, (titulo, valor, cor) in enumerate(items):
            card = ctk.CTkFrame(self._cards_frame, fg_color=cores["card"],
                                corner_radius=10)
            card.grid(row=0, column=col, padx=5, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=titulo, text_color=cores["texto_mudo"],
                         font=ctk.CTkFont(size=11)).pack(pady=(10, 2))
            ctk.CTkLabel(card, text=valor, text_color=cor,
                         font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # Tabela
    # ------------------------------------------------------------------

    def _build_tabela(self):
        cores = self._cores

        # Barra de busca + filtro tipo
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 0))
        self._entry_busca = ctk.CTkEntry(
            barra, placeholder_text="🔍  Buscar por descrição ou categoria…",
            width=300, height=30, font=ctk.CTkFont(size=12),
        )
        self._entry_busca.pack(side="left", padx=(0, 8))
        self._entry_busca.bind("<KeyRelease>", lambda e: self._aplicar_filtro())

        self._filtro_tipo = ctk.StringVar(value="todos")
        for label, val in [("Todos", "todos"), ("Receitas", "receita"), ("Despesas", "despesa")]:
            ctk.CTkRadioButton(
                barra, text=label, variable=self._filtro_tipo, value=val,
                font=ctk.CTkFont(size=11),
                command=self._aplicar_filtro,
            ).pack(side="left", padx=4)

        cab = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        cab.grid(row=3, column=0, sticky="ew", padx=20, pady=(6, 0))
        for i, (nome, larg) in enumerate(_COLS):
            ctk.CTkLabel(
                cab, text=nome, width=larg,
                anchor="w" if i < 3 else "e",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=cores["texto_mudo"],
            ).grid(row=0, column=i, padx=6, pady=6,
                   sticky="w" if i < 3 else "e")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=4, column=0, sticky="nsew", padx=20, pady=(2, 16))
        self.grid_rowconfigure(4, weight=1)

    # ------------------------------------------------------------------
    # Carga de dados
    # ------------------------------------------------------------------

    def _carregar(self):
        self._lbl_mes.configure(
            text=f"{NOMES_MESES[self._mes - 1]}  {self._ano}"
        )
        self._linhas_mes = extrato_mes(self._mes, self._ano)
        resumo = resumo_extrato(self._linhas_mes)
        self._update_cards(resumo)
        self._aplicar_filtro()

    def _aplicar_filtro(self):
        texto = self._entry_busca.get() if hasattr(self, "_entry_busca") else ""
        tipo  = self._filtro_tipo.get() if hasattr(self, "_filtro_tipo") else "todos"
        tipo_filtro = "" if tipo == "todos" else tipo

        linhas = filtrar_extrato(getattr(self, "_linhas_mes", []), texto, tipo_filtro)

        for w in self._scroll.winfo_children():
            w.destroy()

        if not linhas:
            ctk.CTkLabel(
                self._scroll,
                text="Nenhuma transação encontrada.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
            ).pack(pady=32)
            return

        for i, linha in enumerate(linhas):
            self._linha(linha, i)

    def _linha(self, l: LinhaExtrato, idx: int):
        cores = self._cores

        if l.tipo == "receita":
            bg = "#F0FDF4"      # verde muito claro
        elif l.status == "pendente":
            bg = "#FFFBEB"      # amarelo muito claro
        else:
            bg = cores["card"] if idx % 2 == 0 else cores["fundo"]

        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=5)
        row.pack(fill="x", pady=1)

        # Duplo-clique abre o modal de edição se origem='manual'
        if l.origem == "manual" and l.origem_id is not None:
            row.bind("<Double-Button-1>",
                     lambda e, lid=l.origem_id: self._editar_lancamento(lid))

        # Data formatada DD/MM
        partes = l.data.split("-")
        data_fmt = f"{partes[2]}/{partes[1]}" if len(partes) == 3 else l.data

        # Badge de status para despesas pendentes
        desc_txt = l.descricao
        if l.status == "pendente":
            desc_txt = f"⏳ {l.descricao}"

        cells = [
            (data_fmt,                    0, "w"),
            (desc_txt,                    1, "w"),
            (l.categoria,                 2, "w"),
            (formatar_moeda(l.debito)  if l.debito  > 0 else "—",   3, "e"),
            (formatar_moeda(l.credito) if l.credito > 0 else "—",   4, "e"),
            (formatar_moeda(l.saldo),     5, "e"),
        ]

        for texto, col_i, anchor in cells:
            _, larg = _COLS[col_i]

            if col_i == 3 and l.debito > 0:
                cor_txt = cores["alerta"]
            elif col_i == 4 and l.credito > 0:
                cor_txt = cores["positivo"]
            elif col_i == 5:
                cor_txt = cores["positivo"] if l.saldo >= 0 else cores["alerta"]
            else:
                cor_txt = cores["texto_mudo"] if texto == "—" else cores["texto"]

            bold = col_i == 5
            cell = ctk.CTkLabel(
                row, text=texto, width=larg, anchor=anchor,
                font=ctk.CTkFont(size=11, weight="bold" if bold else "normal"),
                text_color=cor_txt,
            )
            cell.grid(row=0, column=col_i, padx=6, pady=5, sticky=anchor)
            # Propaga o duplo-clique das células para o row inteiro
            if l.origem == "manual" and l.origem_id is not None:
                cell.bind("<Double-Button-1>",
                          lambda e, lid=l.origem_id: self._editar_lancamento(lid))

    # ------------------------------------------------------------------
    # Navegação de mês
    # ------------------------------------------------------------------

    def _mes_anterior(self):
        if self._mes == 1:
            self._mes = 12
            self._ano -= 1
        else:
            self._mes -= 1
        self._carregar()

    def _mes_proximo(self):
        if self._mes == 12:
            self._mes = 1
            self._ano += 1
        else:
            self._mes += 1
        self._carregar()

    def _ir_hoje(self):
        hoje = date.today()
        self._mes = hoje.month
        self._ano = hoje.year
        self._carregar()

    def _exportar_excel(self):
        import tkinter.filedialog as fd
        from views.exportar.exportar_model import exportar_extrato_xlsx
        from config import NOMES_MESES
        nome_sugerido = f"extrato_{NOMES_MESES[self._mes-1].lower()}_{self._ano}.xlsx"
        caminho = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=nome_sugerido,
            title="Exportar extrato",
        )
        if caminho:
            exportar_extrato_xlsx(self._mes, self._ano, caminho)
            import tkinter.messagebox as mb
            mb.showinfo("Exportado", f"Extrato salvo em:\n{caminho}")

    # ------------------------------------------------------------------
    # Lançamentos manuais
    # ------------------------------------------------------------------

    def _novo_lancamento(self):
        from views.fluxo_caixa.form_lancamento_manual import FormLancamentoManualModal
        FormLancamentoManualModal(self, on_salvo=self._on_lancamento_salvo)

    def _editar_lancamento(self, lanc_id: int):
        from views.fluxo_caixa.form_lancamento_manual import FormLancamentoManualModal
        from views.fluxo_caixa.lancamento_manual_model import obter_lancamento
        lanc = obter_lancamento(lanc_id)
        if not lanc:
            return
        FormLancamentoManualModal(
            self, on_salvo=self._on_lancamento_salvo, lancamento=lanc,
        )

    def _on_lancamento_salvo(self, msg: str):
        self._carregar()
