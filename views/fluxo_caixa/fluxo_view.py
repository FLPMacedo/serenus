"""
fluxo_view.py — Módulo 4: Fluxo de Caixa (Receita vs Compromissos).
Dashboard com cards, seletor de horizonte, gráfico combinado,
alertas automáticos e tabela mensal detalhada.
"""

from __future__ import annotations
import customtkinter as ctk
from config import get_tema, formatar_moeda
from database import obter_configuracao
from views.fluxo_caixa.fluxo_model import (
    MesFluxo, projetar_fluxo, resumo_fluxo,
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class FluxoCaixaView(ctk.CTkFrame):
    def __init__(self, parent, modo_inicio: bool = False):
        super().__init__(parent, fg_color="transparent")
        self._cores      = get_tema(obter_configuracao("tema", "claro"))
        self._horizonte  = 12
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        if modo_inicio:
            from datetime import date
            from config import NOMES_MESES
            DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira",
                           "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
            hoje = date.today()
            dia_sem = DIAS_SEMANA[hoje.weekday()]
            titulo = f"{dia_sem}, {hoje.day} de {NOMES_MESES[hoje.month - 1]} de {hoje.year}"
        else:
            titulo = "🔄  Fluxo de Caixa"

        ctk.CTkLabel(self, text=titulo,
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=self._cores["texto"]).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 0))

        from views.widgets.ajuda import banner_ajuda
        _b = banner_ajuda(
            self, self._cores,
            "Visão geral das suas finanças. Os cards mostram receita base do "
            "mês, parcelas e saldo livre. Use a tabela abaixo para ver mês a "
            "mês — meses em vermelho indicam saldo negativo previsto.",
        )
        if _b:
            _b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        self._scroll.grid_columnconfigure(0, weight=1)

        self._recarregar()

    # ------------------------------------------------------------------
    # Recarga completa do dashboard
    # ------------------------------------------------------------------

    def _recarregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        projecao = projetar_fluxo(self._horizonte)
        resumo   = resumo_fluxo(projecao)

        self._build_cards(resumo)
        self._build_seletor()
        self._build_alertas(projecao)
        self._build_grafico(projecao)
        self._build_tabela(projecao)

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------

    def _build_cards(self, resumo: dict):
        cores = self._cores
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=(4, 0))
        frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        vm = resumo.get("meses_vermelho", 0)
        am = resumo.get("meses_amarelo", 0)
        total = resumo.get("total_meses", 1)

        saldo = resumo.get("saldo_livre_mes", 0)
        cor_saldo = cores["positivo"] if saldo >= 500 else (
            cores["atencao"] if saldo >= 0 else cores["alerta"]
        )

        if vm == 0 and am == 0:
            alerta_txt = "0 ✅"
            alerta_cor = cores["positivo"]
        elif vm > 0:
            alerta_txt = f"{vm} mês(es) 🔴"
            alerta_cor = cores["alerta"]
        else:
            alerta_txt = f"{am} mês(es) 🟡"
            alerta_cor = cores["atencao"]

        cards = [
            ("💰  Receita base/mês",     formatar_moeda(resumo.get("receita_base", 0)),    cores["primario"]),
            ("💳  Parcelas/mês",         formatar_moeda(resumo.get("total_parcelas", 0)),  cores["alerta"]),
            ("🟢  Saldo livre/mês",      formatar_moeda(saldo),                            cor_saldo),
            ("⚠️  Meses críticos",       alerta_txt,                                       alerta_cor),
        ]
        for i, (titulo, valor, cor) in enumerate(cards):
            card = ctk.CTkFrame(frame, fg_color=cores["card"], corner_radius=10)
            card.grid(row=0, column=i, padx=5, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=titulo, text_color=cores["texto_mudo"],
                         font=ctk.CTkFont(size=11)).pack(pady=(10, 2))
            ctk.CTkLabel(card, text=valor, text_color=cor,
                         font=ctk.CTkFont(size=17, weight="bold")).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # Seletor de horizonte
    # ------------------------------------------------------------------

    def _build_seletor(self):
        cores = self._cores
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=(10, 2))

        ctk.CTkLabel(frame, text="Horizonte:",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(4, 10))

        for meses, label in [(6,"6 meses"),(12,"1 ano"),(18,"1,5 anos"),(24,"2 anos"),(36,"3 anos")]:
            ativo = (meses == self._horizonte)
            ctk.CTkButton(
                frame, text=label, width=80, height=28,
                fg_color=cores["primario"] if ativo else "transparent",
                text_color="#FFFFFF" if ativo else cores["texto"],
                border_width=1,
                border_color=cores["primario"] if ativo else cores["borda"],
                corner_radius=6,
                font=ctk.CTkFont(size=12),
                command=lambda m=meses: self._set_horizonte(m),
            ).pack(side="left", padx=3)

    def _set_horizonte(self, meses: int):
        self._horizonte = meses
        self._recarregar()

    # ------------------------------------------------------------------
    # Alertas automáticos
    # ------------------------------------------------------------------

    def _build_alertas(self, projecao: list[MesFluxo]):
        cores = self._cores
        criticos = [m for m in projecao if m.status in ("vermelho", "amarelo")]

        sec = ctk.CTkFrame(self._scroll, fg_color="transparent")
        sec.pack(fill="x", padx=4, pady=(8, 0))

        if not criticos:
            banner = ctk.CTkFrame(sec, fg_color=cores["positivo"], corner_radius=8)
            banner.pack(fill="x")
            ctk.CTkLabel(banner,
                         text="✅  Nenhum mês no vermelho nesse período — suas finanças estão equilibradas!",
                         text_color="#FFFFFF",
                         font=ctk.CTkFont(size=13, weight="bold")).pack(pady=10, padx=16)
            return

        for m in criticos:
            if m.status == "vermelho":
                bg  = cores["alerta"]
                ico = "🔴"
                txt = f"{ico}  {m.label} — déficit de {formatar_moeda(abs(m.saldo_livre))}"
            else:
                bg  = cores["atencao"]
                ico = "🟡"
                txt = f"{ico}  {m.label} — saldo apertado: {formatar_moeda(m.saldo_livre)}"

            alerta = ctk.CTkFrame(sec, fg_color=bg, corner_radius=6)
            alerta.pack(fill="x", pady=2)
            ctk.CTkLabel(alerta, text=txt, text_color="#FFFFFF",
                         font=ctk.CTkFont(size=12)).pack(
                anchor="w", padx=14, pady=6)

    # ------------------------------------------------------------------
    # Gráfico combinado: barras agrupadas + linha saldo
    # ------------------------------------------------------------------

    def _build_grafico(self, projecao: list[MesFluxo]):
        cores  = self._cores
        escuro = obter_configuracao("tema", "claro") == "escuro"
        fundo  = "#2D3748" if escuro else "#F8FAFC"
        ctxt   = cores["texto"]

        n = len(projecao)
        labels      = [m.label      for m in projecao]
        receitas    = [m.receita    for m in projecao]
        parcelas    = [m.parcelas   for m in projecao]
        desp_fixas  = [m.despesas_fixas for m in projecao]
        saldos      = [m.saldo_livre for m in projecao]

        x     = np.arange(n)
        width = 0.28

        fig, ax = plt.subplots(figsize=(9, 3.6), dpi=96)
        fig.patch.set_facecolor(fundo)
        ax.set_facecolor(fundo)

        bars_r = ax.bar(x - width, receitas,   width, label="Receita",       color="#3B82F6", alpha=0.85)
        bars_p = ax.bar(x,         parcelas,   width, label="Parcelas",      color="#EF4444", alpha=0.85)
        bars_d = ax.bar(x + width, desp_fixas, width, label="Desp. Fixas",   color="#9CA3AF", alpha=0.85)

        # Linha do saldo livre (eixo secundário para escala)
        ax2 = ax.twinx()
        cor_linha = []
        for s in saldos:
            if s < 0:
                cor_linha.append("#EF4444")
            elif s < 500:
                cor_linha.append("#F59E0B")
            else:
                cor_linha.append("#10B981")

        ax2.plot(x, saldos, color="#10B981", linewidth=2.5,
                 marker="o", markersize=5, zorder=5, label="Saldo livre")
        # Preenche segmentos vermelhos/amarelos na linha
        for i in range(len(saldos) - 1):
            c = "#EF4444" if saldos[i] < 0 else ("#F59E0B" if saldos[i] < 500 else "#10B981")
            ax2.plot([x[i], x[i+1]], [saldos[i], saldos[i+1]], color=c,
                     linewidth=2.5, zorder=4)
        # Pontos com cor por status
        for xi, s, c in zip(x, saldos, cor_linha):
            ax2.plot(xi, s, "o", color=c, markersize=6, zorder=6)

        ax2.axhline(0, color=cores["alerta"], linestyle="--", linewidth=0.8, alpha=0.5)

        # Formatação dos eixos
        step = max(1, n // 10)
        ax.set_xticks(x[::step])
        ax.set_xticklabels(labels[::step], rotation=35, ha="right",
                           fontsize=8, color=ctxt)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"R${v/1000:.0f}k" if v >= 1000 else f"R${v:.0f}")
        )
        ax2.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"R${v/1000:.0f}k" if abs(v) >= 1000 else f"R${v:.0f}")
        )
        ax.tick_params(colors=ctxt)
        ax2.tick_params(colors="#10B981")
        ax.spines[["top"]].set_visible(False)
        ax2.spines[["top"]].set_visible(False)
        ax.spines[["left", "bottom", "right"]].set_color(cores["borda"])
        ax2.spines[["left", "bottom", "right"]].set_color(cores["borda"])

        ax.set_title("Receita vs Compromissos por Mês", color=ctxt,
                     fontsize=12, pad=8)
        ax.grid(axis="y", linestyle="--", alpha=0.25, color=cores["borda"])

        # Legenda unificada
        handles1, labels1 = ax.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(handles1 + handles2[:1], labels1 + labels2[:1],
                  fontsize=8, facecolor=fundo, labelcolor=ctxt,
                  framealpha=0.7, loc="upper right")

        fig.tight_layout(pad=1.5)

        container = ctk.CTkFrame(self._scroll, fg_color="transparent")
        container.pack(fill="x", padx=4, pady=(12, 4))
        canvas = FigureCanvasTkAgg(fig, master=container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x")
        plt.close(fig)

    # ------------------------------------------------------------------
    # Tabela mensal detalhada
    # ------------------------------------------------------------------

    def _build_tabela(self, projecao: list[MesFluxo]):
        cores = self._cores

        sec = ctk.CTkFrame(self._scroll, fg_color="transparent")
        sec.pack(fill="x", padx=4, pady=(12, 16))

        ctk.CTkLabel(sec, text="Detalhamento Mensal",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 6))

        # Cabeçalho
        cols = [
            ("Mês",          120),
            ("Receita",      110),
            ("Parcelas",     100),
            ("Desp. Fixas",  100),
            ("Saldo Livre",  110),
            ("Status",        80),
        ]
        cab = ctk.CTkFrame(sec, fg_color=cores["card"], corner_radius=8)
        cab.pack(fill="x")
        for i, (txt, w) in enumerate(cols):
            ctk.CTkLabel(cab, text=txt, width=w, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(
                row=0, column=i, padx=6, pady=6, sticky="w")

        for m in projecao:
            self._linha_tabela(sec, m, cols)

    def _linha_tabela(self, parent, m: MesFluxo, cols):
        cores  = self._cores
        escuro = obter_configuracao("tema", "claro") == "escuro"

        if m.status == "vermelho":
            bg = "#FEE2E2" if not escuro else "#7F1D1D"
        elif m.status == "amarelo":
            bg = "#FEF3C7" if not escuro else "#78350F"
        else:
            bg = cores["fundo"]

        row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=0)
        row.pack(fill="x", pady=1)

        # Coluna mês: nome + badge ESPECIAL se tiver receitas especiais
        frame_mes = ctk.CTkFrame(row, fg_color="transparent", width=cols[0][1])
        frame_mes.grid(row=0, column=0, padx=4, pady=5, sticky="w")
        frame_mes.grid_propagate(False)

        ctk.CTkLabel(frame_mes, text=m.label, anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=cores["texto"]).pack(side="left")

        if m.especiais:
            nomes = ", ".join(e.nome.split("—")[0].strip() for e in m.especiais)
            badge = ctk.CTkLabel(frame_mes,
                                 text=" ★ ",
                                 fg_color=cores["primario"],
                                 text_color="#FFFFFF",
                                 corner_radius=4,
                                 font=ctk.CTkFont(size=9, weight="bold"),
                                 width=20)
            badge.pack(side="left", padx=(4, 0))
            badge.bind("<Enter>", lambda e, n=nomes: self._tooltip(badge, n))

        # Receita
        ctk.CTkLabel(row, text=formatar_moeda(m.receita),
                     width=cols[1][1], anchor="w",
                     text_color=cores["positivo"],
                     font=ctk.CTkFont(size=12)).grid(row=0, column=1, padx=6, pady=5, sticky="w")

        # Parcelas
        ctk.CTkLabel(row, text=formatar_moeda(m.parcelas),
                     width=cols[2][1], anchor="w",
                     text_color=cores["alerta"],
                     font=ctk.CTkFont(size=12)).grid(row=0, column=2, padx=6, pady=5, sticky="w")

        # Despesas fixas
        desp_txt = formatar_moeda(m.despesas_fixas) if m.despesas_fixas > 0 else "R$ 0,00"
        ctk.CTkLabel(row, text=desp_txt,
                     width=cols[3][1], anchor="w",
                     text_color=cores["texto_mudo"],
                     font=ctk.CTkFont(size=12)).grid(row=0, column=3, padx=6, pady=5, sticky="w")

        # Saldo livre
        cor_saldo = (cores["positivo"] if m.saldo_livre >= 500
                     else cores["atencao"] if m.saldo_livre >= 0
                     else cores["alerta"])
        ctk.CTkLabel(row, text=formatar_moeda(m.saldo_livre),
                     width=cols[4][1], anchor="w",
                     text_color=cor_saldo,
                     font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=4, padx=6, pady=5, sticky="w")

        # Status (ícone)
        icone = {"verde": "✅", "amarelo": "⚠️", "vermelho": "🔴"}.get(m.status, "")
        ctk.CTkLabel(row, text=icone, width=cols[5][1], anchor="w",
                     font=ctk.CTkFont(size=14)).grid(
            row=0, column=5, padx=6, pady=5, sticky="w")

    def _tooltip(self, widget, texto: str):
        """Tooltip simples para o badge de receitas especiais."""
        tip = ctk.CTkToplevel(self)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{widget.winfo_rootx()+20}+{widget.winfo_rooty()-30}")
        ctk.CTkLabel(tip, text=texto, fg_color="#1F2937",
                     text_color="#F9FAFB",
                     corner_radius=4,
                     font=ctk.CTkFont(size=10)).pack(padx=8, pady=4)
        tip.after(2500, tip.destroy)
