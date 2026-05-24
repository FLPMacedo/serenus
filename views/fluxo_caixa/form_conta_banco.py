"""
form_conta_banco.py — Modal de cadastro/edição de conta bancária.

Conta bancária = onde o usuário tem dinheiro (Nubank, Itaú CC, Caixa Poupança).
Cada conta tem seu próprio extrato importável.
"""

from __future__ import annotations

import customtkinter as ctk
import tkinter.messagebox as mb

from config import get_tema, mascara_moeda
from database import obter_configuracao
from views.fluxo_caixa.conta_banco_model import (
    ContaBanco,
    salvar_conta,
    atualizar_conta,
    excluir_conta,
)


_TIPOS_LABELS = [
    ("Conta Corrente",   "corrente"),
    ("Conta Digital",    "digital"),
    ("Poupança",         "poupanca"),
    ("Conta Salário",    "salario"),
    ("Outra",            "outra"),
]


class FormContaBancoModal(ctk.CTkToplevel):
    """Modal de cadastro/edição. on_salvo(msg) é chamado após salvar/excluir."""

    def __init__(self, parent, on_salvo, conta: ContaBanco | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._conta = conta
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        titulo = "Editar Conta Bancária" if conta else "Nova Conta Bancária"
        self.title(f"Serenus — {titulo}")
        self.geometry("420x560")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_ui()
        if conta:
            self._preencher(conta)
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        master = self.master
        x = master.winfo_rootx() + (master.winfo_width()  - self.winfo_width())  // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, texto: str):
        ctk.CTkLabel(parent, text=texto, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    # ------------------------------------------------------------------

    def _build_ui(self):
        cores = self._cores
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=16)

        self._label(frame, "Nome da conta *")
        self._entry_nome = ctk.CTkEntry(
            frame, placeholder_text="Ex.: Nubank Principal", width=380
        )
        self._entry_nome.pack(fill="x", pady=(2, 12))

        self._label(frame, "Banco")
        self._entry_banco = ctk.CTkEntry(
            frame, placeholder_text="Ex.: Nubank, Itaú Unibanco", width=380
        )
        self._entry_banco.pack(fill="x", pady=(2, 12))

        self._label(frame, "Tipo de conta *")
        labels = [l for l, _ in _TIPOS_LABELS]
        self._combo_tipo = ctk.CTkComboBox(
            frame, values=labels, state="readonly", width=380
        )
        self._combo_tipo.set(labels[0])
        self._combo_tipo.pack(fill="x", pady=(2, 12))

        # Agência + Número lado a lado
        linha = ctk.CTkFrame(frame, fg_color="transparent")
        linha.pack(fill="x", pady=(2, 12))

        col_ag = ctk.CTkFrame(linha, fg_color="transparent")
        col_ag.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._label(col_ag, "Agência")
        self._entry_agencia = ctk.CTkEntry(col_ag, placeholder_text="0000")
        self._entry_agencia.pack(fill="x", pady=(2, 0))

        col_num = ctk.CTkFrame(linha, fg_color="transparent")
        col_num.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self._label(col_num, "Número da conta")
        self._entry_numero = ctk.CTkEntry(col_num, placeholder_text="00000-0")
        self._entry_numero.pack(fill="x", pady=(2, 0))

        self._label(frame, "Saldo inicial (R$)")
        self._entry_saldo = ctk.CTkEntry(frame, width=380)
        self._entry_saldo.insert(0, "0,00")
        self._entry_saldo.bind("<KeyRelease>",
                               lambda e: mascara_moeda(self._entry_saldo))
        self._entry_saldo.pack(fill="x", pady=(2, 4))
        ctk.CTkLabel(
            frame,
            text="Saldo no banco no momento do cadastro. Usado para calcular "
                 "saldo atual após importar extratos.",
            font=ctk.CTkFont(size=10),
            text_color=cores["texto_mudo"],
            wraplength=370, justify="left",
        ).pack(anchor="w", pady=(0, 12))

        # Ativa (checkbox)
        self._var_ativa = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame, text="Conta ativa", variable=self._var_ativa,
        ).pack(anchor="w", pady=(0, 8))

        # Botões
        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=24, pady=(0, 16))

        if self._conta:
            ctk.CTkButton(
                botoes, text="🗑 Excluir", width=100,
                fg_color="transparent", border_width=1,
                border_color=cores["alerta"], text_color=cores["alerta"],
                command=self._on_excluir,
            ).pack(side="left")

        ctk.CTkButton(
            botoes, text="Cancelar", width=100,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            botoes, text="💾 Salvar", width=120,
            command=self._on_salvar,
        ).pack(side="right")

    # ------------------------------------------------------------------

    def _preencher(self, c: ContaBanco):
        self._entry_nome.delete(0, "end"); self._entry_nome.insert(0, c.nome)
        self._entry_banco.delete(0, "end"); self._entry_banco.insert(0, c.banco)

        # Encontra label do tipo
        for label, valor in _TIPOS_LABELS:
            if valor == c.tipo:
                self._combo_tipo.set(label)
                break

        self._entry_agencia.delete(0, "end"); self._entry_agencia.insert(0, c.agencia)
        self._entry_numero.delete(0, "end");  self._entry_numero.insert(0, c.numero)

        saldo_str = f"{c.saldo_inicial:.2f}".replace(".", ",")
        self._entry_saldo.delete(0, "end"); self._entry_saldo.insert(0, saldo_str)

        self._var_ativa.set(c.ativa)

    def _coletar(self) -> dict | None:
        nome = self._entry_nome.get().strip()
        if not nome:
            mb.showerror("Nome obrigatório", "Informe o nome da conta.")
            return None

        # Tipo: converte label de volta pra valor
        label_tipo = self._combo_tipo.get()
        tipo = "corrente"
        for label, valor in _TIPOS_LABELS:
            if label == label_tipo:
                tipo = valor
                break

        raw = self._entry_saldo.get().strip().replace(".", "").replace(",", ".")
        try:
            saldo = float(raw)
        except ValueError:
            saldo = 0.0

        return {
            "nome":          nome,
            "banco":         self._entry_banco.get().strip(),
            "tipo":          tipo,
            "agencia":       self._entry_agencia.get().strip(),
            "numero":        self._entry_numero.get().strip(),
            "saldo_inicial": saldo,
            "ativa":         self._var_ativa.get(),
        }

    def _on_salvar(self):
        dados = self._coletar()
        if dados is None:
            return
        try:
            if self._conta:
                atualizar_conta(self._conta.id, dados)
                msg = "Conta atualizada."
            else:
                salvar_conta(dados)
                msg = "Conta criada."
        except Exception as e:
            mb.showerror("Erro ao salvar", str(e))
            return
        self.destroy()
        if self._on_salvo:
            self._on_salvo(msg)

    def _on_excluir(self):
        if not self._conta:
            return
        if not mb.askyesno(
            "Excluir conta bancária",
            f"Excluir a conta '{self._conta.nome}'?\n\n"
            "TODOS os lançamentos importados desta conta serão removidos "
            "(ON DELETE CASCADE). Essa ação não pode ser desfeita.",
        ):
            return
        ok, msg = excluir_conta(self._conta.id)
        if not ok:
            mb.showerror("Erro", msg)
            return
        self.destroy()
        if self._on_salvo:
            self._on_salvo("Conta excluída.")
