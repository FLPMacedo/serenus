"""
form_cliente.py — Modal de cadastro/edição de cliente para o módulo OS.

Espelha o padrão dos forms do projeto (CTkToplevel, _build, _salvar,
_label, _centralizar, _lbl_erro). Campos cobrem o pedido do usuário:
nome/empresa, documento, telefone, whatsapp, email, CEP, endereço,
observação.
"""

from __future__ import annotations

import customtkinter as ctk

from config import (
    get_tema,
    mascara_cep,
    mascara_cpf,
    mascara_telefone,
    validar_email,
)
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

        # Documento (CPF/CNPJ — opcional, com máscara de CPF)
        self._label(frame, "CPF (opcional)")
        self._e_documento = ctk.CTkEntry(frame, placeholder_text="000.000.000-00")
        self._e_documento.pack(fill="x", pady=(2, 10))
        self._e_documento.bind(
            "<KeyRelease>", lambda _e: mascara_cpf(self._e_documento),
        )

        # Telefone + WhatsApp lado a lado
        row_tel = ctk.CTkFrame(frame, fg_color="transparent")
        row_tel.pack(fill="x", pady=(0, 10))

        c1 = ctk.CTkFrame(row_tel, fg_color="transparent")
        c1.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._label(c1, "Telefone / Celular")
        self._e_telefone = ctk.CTkEntry(c1, placeholder_text="(31) 99999-0000")
        self._e_telefone.pack(fill="x", pady=(2, 0))
        self._e_telefone.bind("<KeyRelease>", self._on_telefone_keyrelease)

        c2 = ctk.CTkFrame(row_tel, fg_color="transparent")
        c2.pack(side="left", expand=True, fill="x", padx=(6, 0))
        self._label(c2, "WhatsApp")
        self._e_whatsapp = ctk.CTkEntry(c2, placeholder_text="(31) 99999-0000")
        self._e_whatsapp.pack(fill="x", pady=(2, 0))
        self._e_whatsapp.bind(
            "<KeyRelease>", lambda _e: mascara_telefone(self._e_whatsapp),
        )

        # Checkbox "WhatsApp = mesmo do telefone"
        self._var_wpp_igual_tel = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame, text="WhatsApp é o mesmo do telefone",
            variable=self._var_wpp_igual_tel,
            command=self._on_toggle_wpp_igual_tel,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", pady=(0, 8))

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
        self._e_cep.bind(
            "<KeyRelease>", lambda _e: mascara_cep(self._e_cep),
        )

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
    # Handlers de máscara / interação
    # ------------------------------------------------------------------

    def _on_telefone_keyrelease(self, _ev=None):
        """Aplica máscara no telefone; se 'WhatsApp = mesmo' está marcado,
        espelha o valor no campo de WhatsApp."""
        mascara_telefone(self._e_telefone)
        if self._var_wpp_igual_tel.get():
            self._e_whatsapp.delete(0, "end")
            self._e_whatsapp.insert(0, self._e_telefone.get())

    def _on_toggle_wpp_igual_tel(self):
        """Quando o checkbox é marcado, copia o telefone pro WhatsApp e
        desabilita o campo de WhatsApp. Quando desmarcado, reabilita."""
        if self._var_wpp_igual_tel.get():
            self._e_whatsapp.delete(0, "end")
            self._e_whatsapp.insert(0, self._e_telefone.get())
            self._e_whatsapp.configure(state="disabled")
        else:
            self._e_whatsapp.configure(state="normal")

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

        # Re-aplica máscaras pra normalizar valores vindos de cadastros antigos
        mascara_cpf(self._e_documento)
        mascara_telefone(self._e_telefone)
        mascara_telefone(self._e_whatsapp)
        mascara_cep(self._e_cep)

        # Se WhatsApp == telefone, marca o checkbox e desabilita o campo
        if (c.telefone and c.whatsapp
                and self._e_telefone.get() == self._e_whatsapp.get()):
            self._var_wpp_igual_tel.set(True)
            self._e_whatsapp.configure(state="disabled")

    # ------------------------------------------------------------------
    def _salvar(self):
        self._lbl_erro.configure(text="")
        nome = self._e_nome.get().strip()
        if not nome:
            self._lbl_erro.configure(text="Nome/empresa é obrigatório.")
            return

        # E-mail é opcional, mas se preenchido tem que ser válido
        email = self._e_email.get().strip()
        if email and not validar_email(email):
            self._lbl_erro.configure(
                text="E-mail inválido — use formato exemplo@dominio.com."
            )
            return

        dados = {
            "nome":       nome,
            "documento":  self._e_documento.get().strip(),
            "telefone":   self._e_telefone.get().strip(),
            "whatsapp":   self._e_whatsapp.get().strip(),
            "email":      email,
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
