"""
produtos_view.py — Tela de cadastro de produtos e serviços.
"""
from __future__ import annotations
import customtkinter as ctk
from config import get_tema, formatar_moeda
from database import obter_configuracao
from views.vendas.venda_model import Produto, listar_produtos, excluir_produto


class ProdutosView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores      = get_tema(obter_configuracao("tema", "claro"))
        self._so_ativos  = True
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_tabela()
        self._carregar()

    # ------------------------------------------------------------------
    def _build_header(self):
        cores = self._cores
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="📦  Produtos e Serviços",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=0, sticky="w")

        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")
        self._chk_ativos = ctk.CTkCheckBox(
            btns, text="Apenas ativos",
            command=self._toggle_ativos,
        )
        self._chk_ativos.select()
        self._chk_ativos.pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btns, text="+ Novo", height=34,
            command=self._abrir_form_novo,
        ).pack(side="left")

    def _build_tabela(self):
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=16)
        self._scroll.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    def _toggle_ativos(self):
        self._so_ativos = bool(self._chk_ativos.get())
        self._carregar()

    def _carregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        produtos = listar_produtos(apenas_ativos=self._so_ativos)
        if not produtos:
            ctk.CTkLabel(
                self._scroll,
                text="Nenhum produto/serviço cadastrado.\nClique em '+ Novo' para começar.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
                justify="center",
            ).pack(pady=60)
            return

        for p in produtos:
            self._linha(p)

    def _linha(self, p: Produto):
        cores = self._cores
        bg    = cores["card"] if p.ativo else cores["fundo"]

        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=8)
        row.pack(fill="x", pady=3)
        row.grid_columnconfigure(1, weight=1)

        # Tipo badge
        badge_cor = cores["primario"] if p.tipo == "servico" else cores["positivo"]
        badge_txt = "Serviço" if p.tipo == "servico" else "Produto"
        ctk.CTkLabel(
            row, text=badge_txt, width=64,
            fg_color=badge_cor, corner_radius=6,
            text_color="#FFFFFF", font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=0, padx=(10, 8), pady=10)

        # Nome + descrição
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.grid(row=0, column=1, sticky="w")
        nome_txt = p.nome if p.ativo else f"{p.nome}  (inativo)"
        ctk.CTkLabel(
            info, text=nome_txt,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"] if p.ativo else cores["texto_mudo"],
            anchor="w",
        ).pack(anchor="w")
        if p.descricao:
            ctk.CTkLabel(
                info, text=p.descricao,
                font=ctk.CTkFont(size=11),
                text_color=cores["texto_mudo"], anchor="w",
            ).pack(anchor="w")

        # Preço
        ctk.CTkLabel(
            row, text=formatar_moeda(p.preco),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=2, padx=16)

        # Ações
        acoes = ctk.CTkFrame(row, fg_color="transparent")
        acoes.grid(row=0, column=3, padx=(0, 10))
        ctk.CTkButton(
            acoes, text="✏", width=32, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            font=ctk.CTkFont(size=11),
            command=lambda prod=p: self._abrir_form_editar(prod),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            acoes, text="🗑", width=32, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["alerta"], text_color=cores["alerta"],
            font=ctk.CTkFont(size=11),
            command=lambda prod=p: self._confirmar_excluir(prod),
        ).pack(side="left", padx=2)

    # ------------------------------------------------------------------
    def _abrir_form_novo(self):
        from views.vendas.form_produto import FormProdutoModal
        FormProdutoModal(self, on_salvo=self._on_salvo)

    def _abrir_form_editar(self, produto: Produto):
        from views.vendas.form_produto import FormProdutoModal
        FormProdutoModal(self, on_salvo=self._on_salvo, produto=produto)

    def _on_salvo(self):
        self._carregar()
        self._toast("Produto salvo com sucesso.")

    def _confirmar_excluir(self, produto: Produto):
        cores = self._cores
        dlg = ctk.CTkToplevel(self)
        dlg.title("Excluir produto")
        dlg.geometry("360x160")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.bind("<Escape>", lambda e: dlg.destroy())

        ctk.CTkLabel(
            dlg, text=f'Excluir "{produto.nome}"?',
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=(24, 6))
        ctk.CTkLabel(
            dlg, text="Produtos com vendas não podem ser excluídos.",
            text_color=cores["texto_mudo"], font=ctk.CTkFont(size=11),
        ).pack()

        def _ok():
            ok, msg = excluir_produto(produto.id)
            dlg.destroy()
            if ok:
                self._carregar()
                self._toast("Produto excluído.")
            else:
                self._toast(msg, tipo="erro")

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Excluir", width=100,
                      fg_color=cores["alerta"], hover_color="#B91C1C",
                      command=_ok).pack(side="left", padx=6)

    def _toast(self, mensagem: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        toast = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(toast, text=mensagem, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, toast.destroy)
