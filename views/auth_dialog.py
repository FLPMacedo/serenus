"""
auth_dialog.py — Diálogo de senha exibido na abertura do Serenus.
"""

from __future__ import annotations
from typing import Callable
import customtkinter as ctk
from config import get_tema
from database import obter_configuracao, verificar_senha


class SenhaLoginDialog(ctk.CTkToplevel):
    """
    Diálogo de login. Chama `on_resultado(True/False)` quando o usuário
    autentica ou fecha a janela. Não usa wait_window — compatível com
    qualquer ponto do ciclo de vida do mainloop.
    """

    def __init__(self, parent, on_resultado: Callable[[bool], None]):
        super().__init__(parent)
        self._on_resultado = on_resultado
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self._tentativas = 0

        self.title("Serenus — Identificação")
        self.geometry("360x280")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self.bind("<Return>", lambda e: self._verificar())

        self._build_ui()
        self.after(80, self._centralizar)
        self.after(150, lambda: self._entry_senha.focus_set())

    def _centralizar(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - self.winfo_width())  // 2
        y = (sh - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        cores = self._cores
        nome = obter_configuracao("usuario_nome", "Usuário")

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=32, pady=24)

        ctk.CTkLabel(frame, text="🔒  Serenus",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=cores["primario"]).pack(pady=(0, 4))

        ctk.CTkLabel(frame, text=f"Bem-vindo, {nome}",
                     font=ctk.CTkFont(size=13),
                     text_color=cores["texto_mudo"]).pack(pady=(0, 20))

        ctk.CTkLabel(frame, text="Senha", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

        self._entry_senha = ctk.CTkEntry(frame, show="•", height=38)
        self._entry_senha.pack(fill="x", pady=(4, 4))

        self._lbl_erro = ctk.CTkLabel(frame, text="",
                                       text_color=cores["alerta"],
                                       font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w", pady=(0, 12))

        ctk.CTkButton(frame, text="Entrar", height=38,
                      command=self._verificar).pack(fill="x")

    def _verificar(self):
        senha = self._entry_senha.get()
        if verificar_senha(senha):
            self.grab_release()
            self.destroy()
            self._on_resultado(True)
        else:
            self._tentativas += 1
            self._entry_senha.delete(0, "end")
            self._lbl_erro.configure(
                text=f"Senha incorreta. (tentativa {self._tentativas})"
            )

    def _fechar(self):
        self.grab_release()
        self.destroy()
        self._on_resultado(False)
