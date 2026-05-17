"""
form_recebimento.py — Modal para confirmar recebimento de parcela.
"""
from __future__ import annotations
from datetime import date
import customtkinter as ctk
from config import get_tema, formatar_moeda, parsear_data
from database import obter_configuracao
from views.vendas.venda_model import ContaReceber, marcar_recebido


class FormRecebimentoModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, conta: ContaReceber):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._conta    = conta
        self._cores    = get_tema(obter_configuracao("tema", "claro"))

        self.title("Confirmar recebimento")
        self.geometry("400x280")
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
        r     = self._conta
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            frame, text="Confirmar recebimento",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=cores["texto"],
        ).pack(anchor="w", pady=(0, 4))

        parc_txt = (f"Parcela {r.numero_parcela} de {r.total_parcelas}"
                    if r.total_parcelas > 1 else "Pagamento único")
        ctk.CTkLabel(
            frame,
            text=f"{r.descricao}\n{parc_txt}  ·  Vencimento: {r.data_vencimento}",
            font=ctk.CTkFont(size=12),
            text_color=cores["texto_mudo"],
            justify="left",
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            frame, text=formatar_moeda(r.valor),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=cores["positivo"],
        ).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(frame, text="Data do recebimento *",
                     anchor="w", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self._e_data = ctk.CTkEntry(frame, width=200,
                                    placeholder_text="DD/MM/AAAA")
        self._e_data.insert(0, date.today().strftime("%d/%m/%Y"))
        self._e_data.pack(anchor="w", pady=(2, 4))

        self._lbl_erro = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                      font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w", pady=(0, 8))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(anchor="w")
        ctk.CTkButton(
            btns, text="Cancelar", width=110,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btns, text="✓ Confirmar", width=130,
            fg_color=cores["positivo"], hover_color="#15803D",
            command=self._confirmar,
        ).pack(side="left")

    def _confirmar(self):
        data_br  = self._e_data.get().strip()
        data_iso = parsear_data(data_br)
        if not data_iso:
            self._lbl_erro.configure(text="Data inválida (use DD/MM/AAAA).")
            return
        marcar_recebido(self._conta.id, data_iso)
        self.destroy()
        self._on_salvo()
