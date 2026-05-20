"""
form_cliente.py — Modal de cadastro/edição de cliente para o módulo OS.

Espelha o padrão dos forms do projeto (CTkToplevel, _build, _salvar,
_label, _centralizar, _lbl_erro). Campos cobrem o pedido do usuário:
nome/empresa, documento, telefone, whatsapp, email, CEP, endereço,
observação.
"""

from __future__ import annotations

import customtkinter as ctk

from config import get_tema
from database import obter_configuracao
from views.os.cliente_model import Cliente, salvar_cliente


class FormClienteModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, cliente: Cliente | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._cliente  = cliente
        self._cores    = get_tema(obter_configuracao("tema", "claro"))

        self.title("Editar cliente" if cliente else "Novo cliente")
        self.geometry("520x600")
        self.resizable(False, True)
        self.grab_set()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(80, self._centralizar)

        self._build()
        if cliente:
            self._preencher(cliente)

    # ------------------------------------------------------------------
    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, texto: str):
        ctk.CTkLabel(parent, text=texto, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    # ------------------------------------------------------------------
    def _build(self):
        cores = self._cores
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Nome
        self._label(frame, "Nome / Empresa *")
        self._e_nome = ctk.CTkEntry(frame, placeholder_text="Ex.: João Silva")
        self._e_nome.pack(fill="x", pady=(2, 10))

        # Documento
        self._label(frame, "CPF / CNPJ")
        self._e_documento = ctk.CTkEntry(frame, placeholder_text="000.000.000-00")
        self._e_documento.pack(fill="x", pady=(2, 10))

        # Telefone + WhatsApp lado a lado
        row_tel = ctk.CTkFrame(frame, fg_color="transparent")
        row_tel.pack(fill="x", pady=(0, 10))

        c1 = ctk.CTkFrame(row_tel, fg_color="transparent")
        c1.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._label(c1, "Telefone / Celular")
        self._e_telefone = ctk.CTkEntry(c1, placeholder_text="(31) 99999-0000")
        self._e_telefone.pack(fill="x", pady=(2, 0))

        c2 = ctk.CTkFrame(row_tel, fg_color="transparent")
        c2.pack(side="left", expand=True, fill="x", padx=(6, 0))
        self._label(c2, "WhatsApp")
        self._e_whatsapp = ctk.CTkEntry(c2, placeholder_text="(31) 99999-0000")
        self._e_whatsapp.pack(fill="x", pady=(2, 0))

        # E-mail
        self._label(frame, "E-mail")
        self._e_email = ctk.CTkEntry(frame, placeholder_text="exemplo@dominio.com")
        self._e_email.pack(fill="x", pady=(2, 10))

        # CEP + Endereço
        row_end = ctk.CTkFrame(frame, fg_color="transparent")
        row_end.pack(fill="x", pady=(0, 10))

        c_cep = ctk.CTkFrame(row_end, fg_color="transparent")
        c_cep.pack(side="left", padx=(0, 6))
        self._label(c_cep, "CEP")
        self._e_cep = ctk.CTkEntry(c_cep, width=120, placeholder_text="00000-000")
        self._e_cep.pack(pady=(2, 0))

        c_end = ctk.CTkFrame(row_end, fg_color="transparent")
        c_end.pack(side="left", expand=True, fill="x", padx=(6, 0))
        self._label(c_end, "Endereço")
        self._e_endereco = ctk.CTkEntry(
            c_end, placeholder_text="Rua / Av., número, bairro, cidade/UF",
        )
        self._e_endereco.pack(fill="x", pady=(2, 0))

        # Observação
        self._label(frame, "Observações")
        self._t_observacao = ctk.CTkTextbox(frame, height=80)
        self._t_observacao.pack(fill="x", pady=(2, 10))

        # Erro
        self._lbl_erro = ctk.CTkLabel(
            frame, text="", text_color=cores["alerta"],
            font=ctk.CTkFont(size=11),
        )
        self._lbl_erro.pack(anchor="w")

        # Botões
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(
            btns, text="Cancelar", width=130,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self.destroy,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btns,
            text="Atualizar" if self._cliente else "Salvar",
            width=140,
            command=self._salvar,
        ).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    def _preencher(self, c: Cliente):
        self._e_nome.insert(0, c.nome)
        self._e_documento.insert(0, c.documento)
        self._e_telefone.insert(0, c.telefone)
        self._e_whatsapp.insert(0, c.whatsapp)
        self._e_email.insert(0, c.email)
        self._e_cep.insert(0, c.cep)
        self._e_endereco.insert(0, c.endereco)
        self._t_observacao.insert("1.0", c.observacao)

    # ------------------------------------------------------------------
    def _salvar(self):
        self._lbl_erro.configure(text="")
        nome = self._e_nome.get().strip()
        if not nome:
            self._lbl_erro.configure(text="Nome/empresa é obrigatório.")
            return

        dados = {
            "nome":       nome,
            "documento":  self._e_documento.get().strip(),
            "telefone":   self._e_telefone.get().strip(),
            "whatsapp":   self._e_whatsapp.get().strip(),
            "email":      self._e_email.get().strip(),
            "cep":        self._e_cep.get().strip(),
            "endereco":   self._e_endereco.get().strip(),
            "observacao": self._t_observacao.get("1.0", "end").strip(),
        }

        try:
            cid = salvar_cliente(
                dados, id=self._cliente.id if self._cliente else None,
            )
        except ValueError as e:
            self._lbl_erro.configure(text=str(e))
            return

        self.destroy()
        self._on_salvo(cid)
