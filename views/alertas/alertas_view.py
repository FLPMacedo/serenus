"""
alertas_view.py — Painel de alertas/notificações (CTkToplevel).
"""
from __future__ import annotations
import customtkinter as ctk
from config import get_tema, formatar_moeda
from database import obter_configuracao


_COR_URGENCIA = {
    "alta":  "#DC2626",
    "media": "#D97706",
    "baixa": "#16A34A",
}


class PainelAlertasModal(ctk.CTkToplevel):
    def __init__(self, parent, alertas: list):
        super().__init__(parent)
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self._alertas = alertas

        self.title("Serenus — Alertas")
        self.geometry("480x520")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(80, self._centralizar)
        self._build()

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build(self):
        cores = self._cores

        header = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(
            header,
            text=f"🔔  {len(self._alertas)} alerta{'s' if len(self._alertas) != 1 else ''}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=cores["texto"],
        ).pack(padx=20, pady=12, anchor="w")

        scroll = ctk.CTkScrollableFrame(self, fg_color=cores["fundo"])
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        if not self._alertas:
            ctk.CTkLabel(
                scroll,
                text="Nenhum alerta no momento.",
                text_color=cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        for alerta in self._alertas:
            self._card_alerta(scroll, alerta, cores)

        ctk.CTkButton(
            self, text="Fechar", width=120,
            command=self.destroy,
        ).pack(pady=12)

    def _card_alerta(self, parent, alerta, cores):
        cor = _COR_URGENCIA.get(alerta.urgencia, cores["texto_mudo"])

        card = ctk.CTkFrame(parent, fg_color=cores["card"], corner_radius=8)
        card.pack(fill="x", padx=16, pady=4)

        barra = ctk.CTkFrame(card, width=4, fg_color=cor, corner_radius=2)
        barra.pack(side="left", fill="y", padx=(8, 0), pady=8)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        ctk.CTkLabel(
            info,
            text=alerta.descricao,
            font=ctk.CTkFont(size=12),
            text_color=cores["texto"],
            anchor="w",
            wraplength=370,
            justify="left",
        ).pack(anchor="w")

        rodape_parts = []
        if alerta.valor:
            rodape_parts.append(formatar_moeda(alerta.valor))
        rodape_parts.append(alerta.urgencia.upper())

        ctk.CTkLabel(
            info,
            text="  ·  ".join(rodape_parts),
            font=ctk.CTkFont(size=10),
            text_color=cor,
            anchor="w",
        ).pack(anchor="w")
