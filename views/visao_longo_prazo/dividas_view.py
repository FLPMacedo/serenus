"""
dividas_view.py — Módulo 3: Visão de Longo Prazo.
Duas abas: Dashboard | Minhas Dívidas.
"""

from __future__ import annotations
import customtkinter as ctk
from config import get_tema, formatar_moeda, mascara_moeda, LABEL_TIPO_DIVIDA
from database import obter_configuracao
from views.visao_longo_prazo.divida_model import (
    Divida, listar_dividas, salvar_divida, alternar_ativa_divida,
    projetar_evolucao, status_horizonte, dados_barras_empilhadas, resumo_dividas,
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Paleta de cores para as barras/linhas por dívida
CORES_DIVIDAS = [
    "#3B82F6", "#EF4444", "#10B981", "#F59E0B",
    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
]


# ============================================================================
# View principal
# ============================================================================

class VisaoLongoPrazoView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores   = get_tema(obter_configuracao("tema", "claro"))
        self._horizonte = 12  # meses padrão
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="📉  Gerenciamento de Dívidas",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=self._cores["texto"]).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="⬇ Excel", width=80, height=30,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["borda"],
                      text_color=self._cores["texto"],
                      command=self._exportar_excel).grid(row=0, column=1, sticky="e")

        from views.widgets.ajuda import banner_ajuda
        _b = banner_ajuda(
            self, self._cores,
            "Centralize empréstimos, financiamentos e parcelados. O Dashboard "
            "mostra a evolução do saldo total mês a mês; em 'Minhas Dívidas' "
            "você cadastra cada dívida com saldo e parcela mensal.",
        )
        if _b:
            _b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=2, column=0, sticky="nsew", padx=16, pady=8)
        tabs.add("Dashboard")
        tabs.add("Minhas Dívidas")
        tabs._segmented_button.configure(font=ctk.CTkFont(size=13))

        self._dash_tab   = _DashboardTab(tabs.tab("Dashboard"),   self._cores,
                                         get_horizonte=lambda: self._horizonte,
                                         set_horizonte=self._set_horizonte)
        self._crud_tab   = _DividasCrudTab(tabs.tab("Minhas Dívidas"), self._cores,
                                           on_change=self._dash_tab.recarregar)

    def _set_horizonte(self, meses: int):
        self._horizonte = meses
        self._dash_tab.recarregar()

    def _exportar_excel(self):
        from tkinter import filedialog as fd
        import tkinter.messagebox as mb
        dest = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="dividas.xlsx",
        )
        if not dest:
            return
        try:
            from views.exportar.exportar_model import exportar_dividas_xlsx
            exportar_dividas_xlsx(dest)
            mb.showinfo("Exportação", "Relatório de dívidas exportado com sucesso.")
        except Exception as e:
            mb.showerror("Erro", f"Erro ao exportar: {e}")


# ============================================================================
# Aba 1 — Dashboard
# ============================================================================

class _DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, cores, get_horizonte, set_horizonte):
        super().__init__(parent, fg_color="transparent")
        self._cores          = cores
        self._get_horizonte  = get_horizonte
        self._set_horizonte  = set_horizonte
        self.pack(fill="both", expand=True)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)
        self._scroll.grid_columnconfigure(0, weight=1)

        self.recarregar()

    def recarregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        dividas_ativas = listar_dividas(apenas_ativas=True)
        resumo = resumo_dividas(dividas_ativas)
        meses  = self._get_horizonte()

        self._build_cards(resumo)
        self._build_seletor_horizonte(meses)

        if not dividas_ativas:
            ctk.CTkLabel(self._scroll,
                         text="Nenhuma dívida ativa cadastrada.",
                         text_color=self._cores["texto_mudo"],
                         font=ctk.CTkFont(size=14)).pack(pady=40)
            return

        self._build_progresso(dividas_ativas, meses)
        self._build_grafico_linha(dividas_ativas, meses)
        self._build_grafico_barras(dividas_ativas, meses)
        self._build_tabela(dividas_ativas)

    # ------------------------------------------------------------------
    # Cards de resumo
    # ------------------------------------------------------------------

    def _build_cards(self, resumo: dict):
        cores = self._cores
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=(8, 4))
        frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        cards = [
            ("💰  Total em dívidas",    formatar_moeda(resumo["total_saldo"]),    cores["alerta"]),
            ("📅  Parcelas/mês",        formatar_moeda(resumo["total_parcelas"]), cores["atencao"]),
            ("📋  Dívidas ativas",      str(resumo["qtd_ativas"]),               cores["primario"]),
            ("🏁  Quitação total",      resumo["quitacao_total"],                cores["positivo"]),
        ]
        for i, (titulo, valor, cor) in enumerate(cards):
            card = ctk.CTkFrame(frame, fg_color=cores["card"], corner_radius=10)
            card.grid(row=0, column=i, padx=6, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=titulo, text_color=cores["texto_mudo"],
                         font=ctk.CTkFont(size=11)).pack(pady=(10, 2))
            ctk.CTkLabel(card, text=valor, text_color=cor,
                         font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # Seletor de horizonte
    # ------------------------------------------------------------------

    def _build_seletor_horizonte(self, meses_atual: int):
        cores = self._cores
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=(4, 0))

        ctk.CTkLabel(frame, text="Horizonte:",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(4, 10))

        opcoes = [(6, "6 meses"), (12, "1 ano"), (18, "1,5 anos"), (24, "2 anos"), (36, "3 anos")]
        for meses, label in opcoes:
            ativo = (meses == meses_atual)
            btn = ctk.CTkButton(
                frame, text=label, width=80, height=28,
                fg_color=cores["primario"] if ativo else "transparent",
                text_color="#FFFFFF" if ativo else cores["texto"],
                border_width=1,
                border_color=cores["primario"] if ativo else cores["borda"],
                corner_radius=6,
                font=ctk.CTkFont(size=12),
                command=lambda m=meses: self._set_horizonte(m),
            )
            btn.pack(side="left", padx=3)

    # ------------------------------------------------------------------
    # Barras de progresso por dívida
    # ------------------------------------------------------------------

    def _build_progresso(self, dividas: list[Divida], meses: int):
        cores   = self._cores
        dados   = status_horizonte(dividas, meses)
        todas_zeradas = all(d["zerado"] for d in dados)

        sec = ctk.CTkFrame(self._scroll, fg_color="transparent")
        sec.pack(fill="x", padx=8, pady=(12, 0))

        ctk.CTkLabel(sec, text="Progresso no horizonte selecionado",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=cores["texto"]).pack(anchor="w", pady=(0, 8))

        if todas_zeradas:
            banner = ctk.CTkFrame(sec, fg_color=cores["positivo"], corner_radius=8)
            banner.pack(fill="x", pady=(0, 8))
            ctk.CTkLabel(banner,
                         text="✅  Todas as dívidas são quitadas nesse período!",
                         text_color="#FFFFFF",
                         font=ctk.CTkFont(size=13, weight="bold")).pack(pady=10)

        for item in dados:
            d:   Divida = item["divida"]
            pct: float  = item["pct"]
            self._linha_progresso(sec, d, item, pct)

    def _linha_progresso(self, parent, d: Divida, item: dict, pct: float):
        cores = self._cores
        row   = ctk.CTkFrame(parent, fg_color=cores["card"], corner_radius=8)
        row.pack(fill="x", pady=3)
        row.grid_columnconfigure(1, weight=1)

        # Nome + tipo
        info = ctk.CTkFrame(row, fg_color="transparent", width=190)
        info.grid(row=0, column=0, padx=10, pady=8, sticky="w")
        info.grid_propagate(False)
        ctk.CTkLabel(info, text=d.nome, anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]).pack(anchor="w")
        ctk.CTkLabel(info, text=LABEL_TIPO_DIVIDA.get(d.tipo, d.tipo),
                     anchor="w", text_color=cores["texto_mudo"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w")

        # Barra de progresso
        barra_frame = ctk.CTkFrame(row, fg_color="transparent")
        barra_frame.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        barra = ctk.CTkProgressBar(barra_frame, height=14, corner_radius=6)
        barra.set(pct / 100)
        barra.configure(progress_color=cores["positivo"] if item["zerado"] else cores["primario"])
        barra.pack(fill="x")
        ctk.CTkLabel(barra_frame, text=f"{pct:.0f}% quitado",
                     text_color=cores["texto_mudo"],
                     font=ctk.CTkFont(size=10)).pack(anchor="e")

        # Saldo restante + badge
        right = ctk.CTkFrame(row, fg_color="transparent", width=150)
        right.grid(row=0, column=2, padx=10, pady=8, sticky="e")
        right.grid_propagate(False)

        if item["zerado"]:
            badge = ctk.CTkLabel(right, text="  ✓ ZERADO  ",
                                 fg_color=cores["positivo"],
                                 text_color="#FFFFFF",
                                 corner_radius=6,
                                 font=ctk.CTkFont(size=11, weight="bold"))
            badge.pack(anchor="e")
        else:
            ctk.CTkLabel(right,
                         text=f"Restante: {formatar_moeda(item['saldo_restante'])}",
                         anchor="e", text_color=cores["atencao"],
                         font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="e")
            ctk.CTkLabel(right,
                         text=f"Fim: {d.fim_previsto_str}",
                         anchor="e", text_color=cores["texto_mudo"],
                         font=ctk.CTkFont(size=10)).pack(anchor="e")

    # ------------------------------------------------------------------
    # Gráfico de linha — evolução do saldo
    # ------------------------------------------------------------------

    def _build_grafico_linha(self, dividas: list[Divida], meses: int):
        cores     = self._cores
        escuro    = obter_configuracao("tema", "claro") == "escuro"
        fundo_fig = "#2D3748" if escuro else "#F8FAFC"
        cor_texto = cores["texto"]

        evolucao = projetar_evolucao(dividas, meses)
        labels   = [e["label"] for e in evolucao]
        saldos   = [e["saldo"] for e in evolucao]
        # Marca o horizonte selecionado
        x_horizonte = min(meses, len(labels) - 1)

        fig, ax = plt.subplots(figsize=(8, 3), dpi=96)
        fig.patch.set_facecolor(fundo_fig)
        ax.set_facecolor(fundo_fig)

        xs = list(range(len(labels)))
        ax.plot(xs, saldos, color=cores["primario"], linewidth=2.5,
                marker="o", markersize=4, zorder=3)
        ax.fill_between(xs, saldos, alpha=0.15, color=cores["primario"])

        # Linha vertical no horizonte
        if x_horizonte < len(xs):
            ax.axvline(x=x_horizonte, color=cores["atencao"],
                       linestyle="--", linewidth=1.2, alpha=0.8,
                       label=f"Horizonte {meses}m")
            ax.legend(fontsize=9, facecolor=fundo_fig,
                      labelcolor=cor_texto, framealpha=0.6)

        # Ticks e rótulos
        step = max(1, len(labels) // 8)
        ax.set_xticks(xs[::step])
        ax.set_xticklabels(labels[::step], rotation=35, ha="right",
                           fontsize=8, color=cor_texto)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"R$ {v/1000:.0f}k" if v >= 1000 else f"R$ {v:.0f}")
        )
        ax.tick_params(colors=cor_texto)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(cores["borda"])
        ax.set_title("Evolução do Saldo Devedor Total", color=cor_texto,
                     fontsize=12, pad=8)
        ax.grid(axis="y", linestyle="--", alpha=0.3, color=cores["borda"])
        fig.tight_layout(pad=1.5)

        container = ctk.CTkFrame(self._scroll, fg_color="transparent")
        container.pack(fill="x", padx=8, pady=(16, 4))
        canvas = FigureCanvasTkAgg(fig, master=container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x")
        plt.close(fig)

    # ------------------------------------------------------------------
    # Gráfico de barras empilhadas — parcelas por mês
    # ------------------------------------------------------------------

    def _build_grafico_barras(self, dividas: list[Divida], meses: int):
        cores  = self._cores
        escuro = obter_configuracao("tema", "claro") == "escuro"
        fundo_fig = "#2D3748" if escuro else "#F8FAFC"
        cor_texto = cores["texto"]

        dados = dados_barras_empilhadas(dividas, meses)
        labels = dados["labels"]
        series = dados["series"]

        # Limita a 24 rótulos no eixo X para não poluir
        step   = max(1, len(labels) // 12)

        fig, ax = plt.subplots(figsize=(8, 3.2), dpi=96)
        fig.patch.set_facecolor(fundo_fig)
        ax.set_facecolor(fundo_fig)

        xs      = list(range(len(labels)))
        bottom  = [0.0] * len(labels)

        for i, serie in enumerate(series):
            cor = CORES_DIVIDAS[i % len(CORES_DIVIDAS)]
            valores = serie["valores"]
            ax.bar(xs, valores, bottom=bottom, label=serie["nome"],
                   color=cor, alpha=0.85, width=0.6)
            bottom = [b + v for b, v in zip(bottom, valores)]

        ax.set_xticks(xs[::step])
        ax.set_xticklabels(labels[::step], rotation=35, ha="right",
                           fontsize=8, color=cor_texto)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"R$ {v:,.0f}".replace(",", "."))
        )
        ax.tick_params(colors=cor_texto)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(cores["borda"])
        ax.set_title("Parcelas por Mês (por Dívida)", color=cor_texto,
                     fontsize=12, pad=8)
        ax.grid(axis="y", linestyle="--", alpha=0.3, color=cores["borda"])
        ax.legend(fontsize=8, facecolor=fundo_fig, labelcolor=cor_texto,
                  framealpha=0.6, loc="upper right")
        fig.tight_layout(pad=1.5)

        container = ctk.CTkFrame(self._scroll, fg_color="transparent")
        container.pack(fill="x", padx=8, pady=(8, 4))
        canvas = FigureCanvasTkAgg(fig, master=container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x")
        plt.close(fig)

    # ------------------------------------------------------------------
    # Tabela resumida
    # ------------------------------------------------------------------

    def _build_tabela(self, dividas: list[Divida]):
        cores = self._cores
        sec   = ctk.CTkFrame(self._scroll, fg_color="transparent")
        sec.pack(fill="x", padx=8, pady=(12, 16))

        ctk.CTkLabel(sec, text="Detalhamento das Dívidas",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 6))

        cols = [("Nome", 180), ("Tipo", 110), ("Saldo", 110),
                ("Parcela/mês", 110), ("Parcelas rest.", 110), ("Fim previsto", 100)]

        cab = ctk.CTkFrame(sec, fg_color=cores["card"], corner_radius=8)
        cab.pack(fill="x")
        for i, (txt, w) in enumerate(cols):
            ctk.CTkLabel(cab, text=txt, width=w, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(
                row=0, column=i, padx=6, pady=6, sticky="w")

        for d in dividas:
            row = ctk.CTkFrame(sec, fg_color=cores["fundo"], corner_radius=6)
            row.pack(fill="x", pady=1)
            valores = [
                (d.nome,                              180),
                (LABEL_TIPO_DIVIDA.get(d.tipo, d.tipo), 110),
                (formatar_moeda(d.saldo_atual),       110),
                (formatar_moeda(d.parcela_mensal),    110),
                (str(d.parcelas_restantes),           110),
                (d.fim_previsto_str,                  100),
            ]
            for i, (txt, w) in enumerate(valores):
                cor = cores["positivo"] if txt == "Quitado" else cores["texto"]
                ctk.CTkLabel(row, text=txt, width=w, anchor="w",
                             text_color=cor,
                             font=ctk.CTkFont(size=12)).grid(
                    row=0, column=i, padx=6, pady=6, sticky="w")


# ============================================================================
# Aba 2 — Minhas Dívidas (CRUD)
# ============================================================================

class _DividasCrudTab(ctk.CTkFrame):
    def __init__(self, parent, cores, on_change):
        super().__init__(parent, fg_color="transparent")
        self._cores     = cores
        self._on_change = on_change
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Barra superior
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        bar.grid_columnconfigure(0, weight=1)

        self._mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(bar, text="Mostrar inativas",
                        variable=self._mostrar_inativas,
                        command=self._carregar).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(bar, text="+ Nova dívida", height=30,
                      command=self._nova).grid(row=0, column=1, sticky="e")

        # Cabeçalho
        cols = [("Nome",170),("Tipo",100),("Saldo",100),("Parcela",100),
                ("Pagas/Total",100),("Status",70),("Ações",130)]
        cab  = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        cab.grid(row=1, column=0, sticky="ew", padx=8, pady=(6, 0))
        for i, (txt, w) in enumerate(cols):
            ctk.CTkLabel(cab, text=txt, width=w, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(
                row=0, column=i, padx=6, pady=6, sticky="w")
        self._cols = cols

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(2, 8))
        self.grid_rowconfigure(2, weight=1)

        self._carregar()

    def _carregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        dividas = listar_dividas(apenas_ativas=not self._mostrar_inativas.get())
        if not dividas:
            ctk.CTkLabel(self._scroll, text="Nenhuma dívida cadastrada.",
                         text_color=self._cores["texto_mudo"]).pack(pady=20)
            return
        for d in dividas:
            self._linha(d)

    def _linha(self, d: Divida):
        cores = self._cores
        bg    = cores["card"] if d.ativa else cores["fundo"]
        alfa  = cores["texto"] if d.ativa else cores["texto_mudo"]

        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=6)
        row.pack(fill="x", pady=2)

        dados = [
            (d.nome,                                  170),
            (LABEL_TIPO_DIVIDA.get(d.tipo, d.tipo),   100),
            (formatar_moeda(d.saldo_atual),            100),
            (formatar_moeda(d.parcela_mensal),         100),
            (f"{d.parcelas_pagas}/{d.total_parcelas}", 100),
            ("Ativa" if d.ativa else "Inativa",         70),
        ]
        for i, (txt, w) in enumerate(dados):
            ctk.CTkLabel(row, text=txt, width=w, anchor="w",
                         text_color=alfa,
                         font=ctk.CTkFont(size=12)).grid(
                row=0, column=i, padx=6, pady=6, sticky="w")

        acoes = ctk.CTkFrame(row, fg_color="transparent")
        acoes.grid(row=0, column=6, padx=4)

        ctk.CTkButton(acoes, text="✏", width=30, height=24,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=lambda dd=d: self._editar(dd)).pack(side="left", padx=2)

        lbl = "Desativar" if d.ativa else "Ativar"
        cor = cores["atencao"] if d.ativa else cores["positivo"]
        ctk.CTkButton(acoes, text=lbl, width=70, height=24,
                      fg_color="transparent", border_width=1,
                      border_color=cor, text_color=cor,
                      command=lambda dd=d: self._toggle(dd)).pack(side="left", padx=2)

    def _toggle(self, d: Divida):
        alternar_ativa_divida(d.id, not d.ativa)
        self._carregar()
        self._on_change()
        self._toast(f"Dívida \"{'Desativada' if d.ativa else 'Ativada'}\".")

    def _nova(self):
        DividaFormModal(self, on_salvo=self._on_salvo)

    def _editar(self, d: Divida):
        DividaFormModal(self, divida=d, on_salvo=self._on_salvo)

    def _on_salvo(self):
        self._carregar()
        self._on_change()
        self._toast("Dívida salva.")

    def _toast(self, msg: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        t = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(t, text=msg, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        t.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, t.destroy)


# ============================================================================
# Modal de formulário de dívida
# ============================================================================

class DividaFormModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, divida: Divida | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._divida   = divida
        self._cores    = get_tema(obter_configuracao("tema", "claro"))

        titulo = "Editar Dívida" if divida else "Nova Dívida"
        self.title(f"Serenus — {titulo}")
        self.geometry("460x580")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self._build_ui()
        if divida:
            self._preencher(divida)
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _lbl(self, txt: str):
        ctk.CTkLabel(self._fr, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _entry(self, placeholder: str) -> ctk.CTkEntry:
        e = ctk.CTkEntry(self._fr, placeholder_text=placeholder)
        e.pack(fill="x", pady=(2, 2))
        return e

    def _err_label(self) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(self._fr, text="", text_color="#DC2626",
                           font=ctk.CTkFont(size=10), anchor="w")
        lbl.pack(anchor="w", pady=(0, 6))
        return lbl

    def _build_ui(self):
        self._fr = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._fr.pack(fill="both", expand=True, padx=20, pady=16)

        self._lbl("Nome *")
        self._entry_nome = self._entry("Ex: Nubank, Financiamento Carro")
        self._lbl_err_nome = self._err_label()

        self._lbl("Tipo *")
        tipos_label = list(LABEL_TIPO_DIVIDA.values())
        self._combo_tipo = ctk.CTkComboBox(self._fr, values=tipos_label, state="readonly")
        self._combo_tipo.set(tipos_label[0])
        self._combo_tipo.pack(fill="x", pady=(2, 10))

        self._lbl("Saldo atual devedor (R$) *")
        self._entry_saldo = self._entry("0,00")
        self._entry_saldo.bind("<KeyRelease>", lambda e: mascara_moeda(self._entry_saldo))
        self._lbl_err_saldo = self._err_label()

        self._lbl("Parcela mensal (R$) *")
        self._entry_parcela = self._entry("0,00")
        self._entry_parcela.bind("<KeyRelease>", lambda e: mascara_moeda(self._entry_parcela))
        self._lbl_err_parcela = self._err_label()

        # Total e pagas — na mesma linha
        frame_parc = ctk.CTkFrame(self._fr, fg_color="transparent")
        frame_parc.pack(fill="x", pady=(0, 10))
        frame_parc.grid_columnconfigure((0, 1), weight=1)

        sub_tot = ctk.CTkFrame(frame_parc, fg_color="transparent")
        sub_tot.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(sub_tot, text="Total de parcelas *", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")
        self._entry_total = ctk.CTkEntry(sub_tot, placeholder_text="Ex: 24")
        self._entry_total.pack(fill="x", pady=(2, 2))
        self._lbl_err_total = ctk.CTkLabel(sub_tot, text="", text_color="#DC2626",
                                           font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_total.pack(anchor="w")

        sub_pag = ctk.CTkFrame(frame_parc, fg_color="transparent")
        sub_pag.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(sub_pag, text="Parcelas já pagas", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")
        self._entry_pagas = ctk.CTkEntry(sub_pag, placeholder_text="Ex: 3")
        self._entry_pagas.pack(fill="x", pady=(2, 0))

        self._lbl("Dia de vencimento")
        self._entry_dia = self._entry("Ex: 10")

        self._lbl("Taxa de juros % a.m. (opcional)")
        self._entry_juros = self._entry("Ex: 1,99")

        self._lbl("Observação")
        self._entry_obs = self._entry("Opcional")

        btns = ctk.CTkFrame(self._fr, fg_color="transparent")
        btns.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(btns, text="Cancelar", width=110,
                      fg_color="transparent", border_width=1,
                      text_color=self._cores["texto"],
                      border_color=self._cores["borda"],
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Salvar", width=110,
                      command=self._salvar).pack(side="right")

    def _preencher(self, d: Divida):
        inv = {v: k for k, v in LABEL_TIPO_DIVIDA.items()}
        self._entry_nome.insert(0, d.nome)
        self._combo_tipo.set(LABEL_TIPO_DIVIDA.get(d.tipo, d.tipo))
        self._entry_saldo.insert(0, f"{d.saldo_atual:.2f}".replace(".", ","))
        self._entry_parcela.insert(0, f"{d.parcela_mensal:.2f}".replace(".", ","))
        self._entry_total.insert(0, str(d.total_parcelas))
        self._entry_pagas.insert(0, str(d.parcelas_pagas))
        if d.dia_vencimento:
            self._entry_dia.insert(0, str(d.dia_vencimento))
        if d.taxa_juros:
            self._entry_juros.insert(0, f"{d.taxa_juros:.2f}".replace(".", ","))
        self._entry_obs.insert(0, d.observacao or "")

    def _float(self, widget: ctk.CTkEntry, obrigatorio: bool = True) -> float | None:
        txt = widget.get().replace(".", "").replace(",", ".").strip()
        try:
            v = float(txt)
            if obrigatorio and v <= 0:
                raise ValueError
            widget.configure(border_color="transparent")
            return v
        except ValueError:
            widget.configure(border_color="#DC2626")
            return None

    def _int(self, widget: ctk.CTkEntry, obrigatorio: bool = True) -> int | None:
        txt = widget.get().strip()
        try:
            v = int(txt)
            if obrigatorio and v <= 0:
                raise ValueError
            widget.configure(border_color="transparent")
            return v
        except ValueError:
            widget.configure(border_color="#DC2626" if obrigatorio else "transparent")
            return 0 if not obrigatorio else None

    def _salvar(self):
        # Reset erros
        borda = self._cores["borda"]
        for entry in [self._entry_nome, self._entry_saldo, self._entry_parcela, self._entry_total]:
            entry.configure(border_color=borda)
        self._lbl_err_nome.configure(text="")
        self._lbl_err_saldo.configure(text="")
        self._lbl_err_parcela.configure(text="")
        self._lbl_err_total.configure(text="")

        nome = self._entry_nome.get().strip()
        if not nome:
            self._entry_nome.configure(border_color="#DC2626")
            self._lbl_err_nome.configure(text="Nome é obrigatório.")
            return

        saldo   = self._float(self._entry_saldo)
        if saldo is None:
            self._lbl_err_saldo.configure(text="Informe um valor maior que zero.")
        parcela = self._float(self._entry_parcela)
        if parcela is None:
            self._lbl_err_parcela.configure(text="Informe um valor maior que zero.")
        total   = self._int(self._entry_total)
        if total is None:
            self._lbl_err_total.configure(text="Informe um número maior que zero.")
        pagas   = self._int(self._entry_pagas, obrigatorio=False)
        dia     = self._int(self._entry_dia, obrigatorio=False) or None
        juros   = self._float(self._entry_juros, obrigatorio=False) or 0.0

        if any(v is None for v in [saldo, parcela, total]):
            return

        inv = {v: k for k, v in LABEL_TIPO_DIVIDA.items()}
        tipo = inv.get(self._combo_tipo.get(), "outro")

        dados = {
            "nome":          nome,
            "tipo":          tipo,
            "saldo_atual":   saldo,
            "parcela_mensal": parcela,
            "total_parcelas": total,
            "parcelas_pagas": pagas or 0,
            "dia_vencimento": dia,
            "taxa_juros":    juros,
            "observacao":    self._entry_obs.get().strip(),
        }
        salvar_divida(dados, id=self._divida.id if self._divida else None)
        self.destroy()
        self._on_salvo()
