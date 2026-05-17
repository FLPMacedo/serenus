"""
form_produto.py — Modal de cadastro e edição de produto/serviço.
"""
from __future__ import annotations
import customtkinter as ctk
from config import get_tema, mascara_moeda
from database import obter_configuracao
from views.vendas.venda_model import Produto, salvar_produto


class FormProdutoModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, produto: Produto | None = None):
        super().__init__(parent)
        self._on_salvo  = on_salvo
        self._produto   = produto
        self._cores     = get_tema(obter_configuracao("tema", "claro"))

        self.title("Editar produto/serviço" if produto else "Novo produto/serviço")
        self.geometry("440x420")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(80, self._centralizar)
        self._build()
        if produto:
            self._preencher()

    # ------------------------------------------------------------------
    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, txt):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    # ------------------------------------------------------------------
    def _build(self):
        cores = self._cores
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        self._label(frame, "Nome *")
        self._e_nome = ctk.CTkEntry(frame, width=390)
        self._e_nome.pack(fill="x", pady=(2, 10))

        self._label(frame, "Tipo *")
        self._tipo_var = ctk.StringVar(value="produto")
        row_tipo = ctk.CTkFrame(frame, fg_color="transparent")
        row_tipo.pack(anchor="w", pady=(2, 10))
        ctk.CTkRadioButton(row_tipo, text="Produto",  variable=self._tipo_var,
                           value="produto").pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(row_tipo, text="Serviço",  variable=self._tipo_var,
                           value="servico").pack(side="left")

        self._label(frame, "Preço (R$) *")
        self._e_preco = ctk.CTkEntry(frame, width=390, placeholder_text="0,00")
        self._e_preco.insert(0, "0,00")
        self._e_preco.pack(fill="x", pady=(2, 2))
        self._e_preco.bind("<KeyRelease>", lambda e: mascara_moeda(self._e_preco))
        self._lbl_err_preco = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                           font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_preco.pack(anchor="w", pady=(0, 8))

        self._label(frame, "Descrição")
        self._e_desc = ctk.CTkEntry(frame, width=390)
        self._e_desc.pack(fill="x", pady=(2, 10))

        self._label(frame, "Status")
        self._ativo_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame, text="Ativo", variable=self._ativo_var).pack(
            anchor="w", pady=(2, 10)
        )

        self._lbl_erro = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                      font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w")

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(pady=8)
        ctk.CTkButton(btns, text="Cancelar", width=120,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Salvar", width=120,
                      command=self._salvar).pack(side="left", padx=6)

    def _preencher(self):
        p = self._produto
        self._e_nome.insert(0, p.nome)
        self._tipo_var.set(p.tipo)
        self._e_preco.delete(0, "end")
        self._e_preco.insert(0, f"{p.preco:.2f}".replace(".", ","))
        self._e_desc.insert(0, p.descricao)
        self._ativo_var.set(p.ativo)

    def _salvar(self):
        borda = self._cores["borda"]
        self._e_preco.configure(border_color=borda)
        self._lbl_err_preco.configure(text="")
        self._lbl_erro.configure(text="")

        nome = self._e_nome.get().strip()
        if not nome:
            self._lbl_erro.configure(text="Informe o nome do produto/serviço.")
            return

        try:
            preco = float(
                self._e_preco.get().replace(".", "").replace(",", ".").strip()
            )
            if preco < 0:
                raise ValueError
        except ValueError:
            self._e_preco.configure(border_color="#DC2626")
            self._lbl_err_preco.configure(text="Informe um preço válido (≥ 0).")
            return

        dados = {
            "nome":     nome,
            "tipo":     self._tipo_var.get(),
            "preco":    preco,
            "descricao": self._e_desc.get().strip(),
            "ativo":    self._ativo_var.get(),
        }
        salvar_produto(dados, id=self._produto.id if self._produto else None)
        self.destroy()
        self._on_salvo()
