"""
form_conta_inv.py — Formulário de cadastro de conta de investimento.
"""
from __future__ import annotations
from typing import Callable, Optional

import customtkinter as ctk
from config import get_tema, TIPOS_CONTA_INV, LABEL_TIPO_CONTA_INV
from database import obter_configuracao
from views.investimentos.investimento_model import (
    salvar_conta_investimento, ContaInvestimento,
)


class FormContaInvModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo: Callable,
                 conta: Optional[ContaInvestimento] = None):
        super().__init__(parent)
        self._cores   = get_tema(obter_configuracao("tema", "claro"))
        self._on_salvo = on_salvo
        self._conta    = conta

        titulo = "Editar conta" if conta else "Nova conta de investimento"
        self.title(titulo)
        self.geometry("420x340")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()
        if conta:
            self._preencher(conta)

    def _label(self, parent, txt: str):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12),
                     text_color=self._cores["texto"]
                     ).pack(anchor="w", padx=20, pady=(8, 0))

    def _build_ui(self):
        cores = self._cores
        ctk.CTkLabel(self, text="🏦  Conta de Investimento",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=cores["texto"]
                     ).pack(pady=(18, 4), padx=20, anchor="w")

        self._label(self, "Nome da conta *")
        self._e_nome = ctk.CTkEntry(self, placeholder_text="Ex: Rico XP, Tesouro Direto")
        self._e_nome.pack(fill="x", padx=20, pady=(2, 0))

        self._label(self, "Instituição *")
        self._e_inst = ctk.CTkEntry(self, placeholder_text="Ex: XP Investimentos, BTG, Nubank")
        self._e_inst.pack(fill="x", padx=20, pady=(2, 0))

        self._label(self, "Tipo")
        valores = [LABEL_TIPO_CONTA_INV.get(t, t) for t in TIPOS_CONTA_INV]
        self._combo_tipo = ctk.CTkComboBox(self, values=valores, state="readonly")
        self._combo_tipo.set(valores[0])
        self._combo_tipo.pack(fill="x", padx=20, pady=(2, 0))
        self._tipos_keys = TIPOS_CONTA_INV

        self._label(self, "Observação")
        self._e_obs = ctk.CTkEntry(self)
        self._e_obs.pack(fill="x", padx=20, pady=(2, 0))

        self._lbl_erro = ctk.CTkLabel(self, text="", text_color=cores["alerta"],
                                       font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w", padx=20, pady=(4, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="Cancelar", width=110,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Salvar", width=110,
                      command=self._salvar).pack(side="left", padx=6)

    def _preencher(self, c: ContaInvestimento):
        self._e_nome.insert(0, c.nome)
        self._e_inst.insert(0, c.instituicao)
        idx = TIPOS_CONTA_INV.index(c.tipo) if c.tipo in TIPOS_CONTA_INV else 0
        valores = [LABEL_TIPO_CONTA_INV.get(t, t) for t in TIPOS_CONTA_INV]
        self._combo_tipo.set(valores[idx])
        self._e_obs.insert(0, c.observacao)

    def _salvar(self):
        nome = self._e_nome.get().strip()
        inst = self._e_inst.get().strip()
        if not nome:
            self._lbl_erro.configure(text="Nome é obrigatório.")
            return
        if not inst:
            self._lbl_erro.configure(text="Instituição é obrigatória.")
            return

        tipo_label = self._combo_tipo.get()
        tipo = next(
            (k for k, v in LABEL_TIPO_CONTA_INV.items() if v == tipo_label),
            "outro",
        )

        dados = {"nome": nome, "instituicao": inst, "tipo": tipo,
                 "observacao": self._e_obs.get().strip()}
        salvar_conta_investimento(dados, id=self._conta.id if self._conta else None)
        self.destroy()
        self._on_salvo()
