"""
setup_view.py — Wizard de boas-vindas exibido na primeira execução.
Coleta: nome, tipo de perfil, moeda e tema. Salva em configuracoes.
"""

import customtkinter as ctk
from database import salvar_configuracao
from config import TEMAS, get_tema


class SetupView(ctk.CTkToplevel):
    def __init__(self, parent, on_concluido):
        super().__init__(parent)
        self.on_concluido = on_concluido
        self.title("Serenus — Configuração inicial")
        self.geometry("500x520")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # bloqueia fechar sem concluir

        self._tema_var = ctk.StringVar(value="claro")
        self._build_ui()
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        master = self.master
        x = master.winfo_x() + (master.winfo_width()  - self.winfo_width())  // 2
        y = master.winfo_y() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        pad = {"padx": 40, "pady": 0}

        # Cabeçalho
        ctk.CTkLabel(self, text="Serenus",
                     font=ctk.CTkFont(size=32, weight="bold"),
                     text_color="#1A56DB").pack(pady=(40, 4))
        ctk.CTkLabel(self, text="Suas finanças, com calma",
                     font=ctk.CTkFont(size=14),
                     text_color="#6B7280").pack(pady=(0, 30))

        # Nome
        ctk.CTkLabel(self, text="Seu nome ou nome da empresa",
                     anchor="w").pack(fill="x", **pad)
        self._nome_entry = ctk.CTkEntry(self, placeholder_text="Ex: João Silva")
        self._nome_entry.pack(fill="x", padx=40, pady=(4, 16))

        # Tipo de perfil
        ctk.CTkLabel(self, text="Tipo de perfil", anchor="w").pack(fill="x", **pad)
        self._perfil_var = ctk.StringVar(value="Pessoa Física")
        frame_perfil = ctk.CTkFrame(self, fg_color="transparent")
        frame_perfil.pack(fill="x", padx=40, pady=(4, 16))
        ctk.CTkRadioButton(frame_perfil, text="Pessoa Física",
                           variable=self._perfil_var, value="Pessoa Física").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(frame_perfil, text="Pequeno Negócio / Freelancer",
                           variable=self._perfil_var, value="Pequeno Negócio / Freelancer").pack(side="left")

        # Moeda (fixo BRL por enquanto)
        ctk.CTkLabel(self, text="Moeda padrão", anchor="w").pack(fill="x", **pad)
        ctk.CTkLabel(self, text="R$ — Real Brasileiro (BRL)",
                     anchor="w", text_color="#6B7280").pack(fill="x", padx=40, pady=(4, 16))

        # Tema
        ctk.CTkLabel(self, text="Tema padrão", anchor="w").pack(fill="x", **pad)
        frame_tema = ctk.CTkFrame(self, fg_color="transparent")
        frame_tema.pack(fill="x", padx=40, pady=(4, 0))
        ctk.CTkRadioButton(frame_tema, text="Claro",
                           variable=self._tema_var, value="claro").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(frame_tema, text="Escuro",
                           variable=self._tema_var, value="escuro").pack(side="left")

        # Botão concluir
        ctk.CTkButton(self, text="Começar →", height=44,
                      command=self._concluir).pack(fill="x", padx=40, pady=36)

    def _concluir(self):
        nome = self._nome_entry.get().strip()
        if not nome:
            self._nome_entry.configure(border_color="#DC2626")
            self._nome_entry.focus()
            return

        salvar_configuracao("usuario_nome",   nome)
        salvar_configuracao("usuario_perfil", self._perfil_var.get())
        salvar_configuracao("moeda",          "BRL")
        salvar_configuracao("tema",           self._tema_var.get())
        salvar_configuracao("setup_concluido", "true")

        self.destroy()
        self.on_concluido(self._tema_var.get())
