"""
form_regras_categoria.py — Modal de CRUD de regras de categorização.

Cada regra mapeia uma substring (case-insensitive) na descrição do extrato
para uma categoria fixa, separado por tipo (entrada/saída).

Exemplos:
  'LANCHONETE' (saida)    -> Alimentação
  'REMUNERACAO' (entrada) -> Salário CLT

Aplicação automática: quando um extrato é importado, casar_regras() é
chamado e preenche o campo de categoria.
"""

from __future__ import annotations

import customtkinter as ctk
import tkinter.messagebox as mb

from config import get_tema
from database import obter_configuracao
from views.contas_pagar.conta_model import listar_plano_contas
from views.receitas.receita_model import listar_fontes
from views.fluxo_caixa.regras_categoria_model import (
    RegraCategoria,
    listar_regras,
    salvar_regra,
    atualizar_regra,
    excluir_regra,
)


class FormRegrasCategoriaModal(ctk.CTkToplevel):
    """Modal de gestão de regras. Lista + form embutido."""

    def __init__(self, parent, on_fechado=None):
        super().__init__(parent)
        self._on_fechado = on_fechado
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self._planos = listar_plano_contas(apenas_ativas=True)
        self._fontes = listar_fontes(apenas_ativas=True)
        self._editando: RegraCategoria | None = None

        self.title("Serenus — Regras de Categorização Automática")
        self.geometry("760x560")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self._fechar())
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        self._build_ui()
        self._recarregar()
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        master = self.master
        x = master.winfo_rootx() + (master.winfo_width()  - self.winfo_width())  // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _fechar(self):
        self.destroy()
        if self._on_fechado:
            self._on_fechado()

    def _label(self, parent, texto: str):
        ctk.CTkLabel(parent, text=texto, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    # ------------------------------------------------------------------

    def _build_ui(self):
        cores = self._cores
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=16, pady=12)
        outer.grid_columnconfigure(0, weight=2)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        # Esquerda: lista de regras
        esq = ctk.CTkFrame(outer, fg_color=cores["card"], corner_radius=8)
        esq.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(
            esq, text="Regras cadastradas",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(10, 4), padx=12, anchor="w")

        ctk.CTkLabel(
            esq, text="Clique numa regra pra editar. Duplo-clique exclui.",
            font=ctk.CTkFont(size=10),
            text_color=cores["texto_mudo"],
        ).pack(anchor="w", padx=12, pady=(0, 6))

        self._scroll = ctk.CTkScrollableFrame(esq, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        # Direita: form de criação/edição
        dir_ = ctk.CTkFrame(outer, fg_color=cores["card"], corner_radius=8)
        dir_.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            dir_, text="Nova regra",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(10, 8), padx=12, anchor="w")
        self._lbl_form_titulo = dir_.winfo_children()[-1]

        form = ctk.CTkFrame(dir_, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # Tipo
        self._label(form, "Tipo *")
        self._var_tipo = ctk.StringVar(value="saida")
        tipo_frame = ctk.CTkFrame(form, fg_color="transparent")
        tipo_frame.pack(fill="x", pady=(2, 10))
        ctk.CTkRadioButton(
            tipo_frame, text="🔴  Saída", variable=self._var_tipo,
            value="saida", command=self._on_tipo_mudou,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(
            tipo_frame, text="🟢  Entrada", variable=self._var_tipo,
            value="entrada", command=self._on_tipo_mudou,
        ).pack(side="left")

        # Padrão
        self._label(form, "Texto a buscar (case-insensitive) *")
        self._entry_padrao = ctk.CTkEntry(
            form, placeholder_text="Ex.: LANCHONETE, SPOTIFY, SALARIO",
        )
        self._entry_padrao.pack(fill="x", pady=(2, 4))
        ctk.CTkLabel(
            form, text="A regra casa se a descrição CONTÉM esse texto.",
            font=ctk.CTkFont(size=10), text_color=cores["texto_mudo"],
        ).pack(anchor="w", pady=(0, 10))

        # Categoria
        self._label(form, "Categoria *")
        self._combo_cat = ctk.CTkComboBox(form, values=[""], state="readonly")
        self._combo_cat.pack(fill="x", pady=(2, 10))

        # Prioridade
        self._label(form, "Prioridade (maior = aplicada primeiro)")
        self._entry_prio = ctk.CTkEntry(form, placeholder_text="0")
        self._entry_prio.insert(0, "0")
        self._entry_prio.pack(fill="x", pady=(2, 10))

        # Botões
        botoes = ctk.CTkFrame(form, fg_color="transparent")
        botoes.pack(fill="x", pady=(8, 0))

        ctk.CTkButton(
            botoes, text="Limpar", width=80,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._limpar_form,
        ).pack(side="left")

        self._btn_salvar = ctk.CTkButton(
            botoes, text="💾 Adicionar", command=self._on_salvar,
        )
        self._btn_salvar.pack(side="right")

        # Fechar
        ctk.CTkButton(
            self, text="Fechar", width=100,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._fechar,
        ).pack(pady=(0, 12))

        self._on_tipo_mudou()

    # ------------------------------------------------------------------

    def _on_tipo_mudou(self):
        if self._var_tipo.get() == "saida":
            valores = [p.nome for p in self._planos] or \
                      ["(cadastre uma categoria em Plano de Contas)"]
        else:
            valores = [f.nome for f in self._fontes] or \
                      ["(cadastre uma fonte em Receitas)"]
        self._combo_cat.configure(values=valores)
        self._combo_cat.set(valores[0])

    def _recarregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        regras = listar_regras()
        if not regras:
            ctk.CTkLabel(
                self._scroll,
                text="Nenhuma regra cadastrada ainda.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=12),
            ).pack(pady=24)
            return

        for r in regras:
            self._linha_regra(r)

    def _linha_regra(self, r: RegraCategoria):
        cores = self._cores
        bg = cores["fundo"]
        if self._editando and self._editando.id == r.id:
            bg = "#DBEAFE"

        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
        row.pack(fill="x", pady=2)

        tipo_ico = "🔴" if r.tipo == "saida" else "🟢"
        txt = (f"{tipo_ico}  {r.padrao!r}  →  {r.nome_categoria}"
               f"   [prioridade: {r.prioridade}]")
        lbl = ctk.CTkLabel(row, text=txt, anchor="w",
                           font=ctk.CTkFont(size=12),
                           text_color=cores["texto"])
        lbl.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        for w in (row, lbl):
            w.bind("<Button-1>", lambda e, reg=r: self._editar(reg))
            w.bind("<Double-Button-1>", lambda e, reg=r: self._on_excluir(reg))

    def _editar(self, r: RegraCategoria):
        self._editando = r
        self._lbl_form_titulo.configure(text=f"Editando regra #{r.id}")
        self._btn_salvar.configure(text="💾 Atualizar")

        self._var_tipo.set(r.tipo)
        self._on_tipo_mudou()
        self._entry_padrao.delete(0, "end")
        self._entry_padrao.insert(0, r.padrao)
        if r.nome_categoria:
            self._combo_cat.set(r.nome_categoria)
        self._entry_prio.delete(0, "end")
        self._entry_prio.insert(0, str(r.prioridade))

        self._recarregar()  # destaca a regra selecionada

    def _limpar_form(self):
        self._editando = None
        self._lbl_form_titulo.configure(text="Nova regra")
        self._btn_salvar.configure(text="💾 Adicionar")
        self._var_tipo.set("saida")
        self._on_tipo_mudou()
        self._entry_padrao.delete(0, "end")
        self._entry_prio.delete(0, "end"); self._entry_prio.insert(0, "0")
        self._recarregar()

    def _coletar(self) -> dict | None:
        tipo = self._var_tipo.get()
        padrao = self._entry_padrao.get().strip()
        if not padrao:
            mb.showerror("Padrão obrigatório", "Informe o texto a ser buscado.")
            return None

        nome_cat = self._combo_cat.get()
        if nome_cat.startswith("("):
            mb.showerror("Categoria indisponível", nome_cat)
            return None

        plano_id = fonte_id = None
        if tipo == "saida":
            cand = [p for p in self._planos if p.nome == nome_cat]
            if not cand:
                mb.showerror("Categoria inválida", "Categoria não encontrada.")
                return None
            plano_id = cand[0].id
        else:
            cand = [f for f in self._fontes if f.nome == nome_cat]
            if not cand:
                mb.showerror("Categoria inválida", "Fonte não encontrada.")
                return None
            fonte_id = cand[0].id

        try:
            prio = int(self._entry_prio.get().strip() or "0")
        except ValueError:
            prio = 0

        return {
            "padrao":           padrao,
            "tipo":             tipo,
            "plano_conta_id":   plano_id,
            "fonte_receita_id": fonte_id,
            "prioridade":       prio,
            "ativa":            True,
        }

    def _on_salvar(self):
        dados = self._coletar()
        if dados is None:
            return
        try:
            if self._editando:
                atualizar_regra(self._editando.id, dados)
            else:
                salvar_regra(dados)
        except Exception as e:
            mb.showerror("Erro", str(e))
            return
        self._limpar_form()

    def _on_excluir(self, r: RegraCategoria):
        if not mb.askyesno(
            "Excluir regra",
            f"Excluir a regra {r.padrao!r} → {r.nome_categoria}?",
        ):
            return
        excluir_regra(r.id)
        if self._editando and self._editando.id == r.id:
            self._limpar_form()
        else:
            self._recarregar()
