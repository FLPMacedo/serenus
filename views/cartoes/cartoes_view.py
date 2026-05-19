"""
cartoes_view.py — Tela principal do Módulo 7: Meus Cartões.
Grid de cards visuais 2 colunas + botões de ação por cartão.
"""

from __future__ import annotations
import customtkinter as ctk
from config import get_tema, formatar_moeda
from database import obter_configuracao
from views.cartoes.cartao_model import (
    Cartao, listar_cartoes, alternar_ativo_cartao,
    CORES_BANDEIRA, BANDEIRAS, BANDEIRAS_LABEL, carregar_logo_bandeira,
)


class CartoesView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_banner()
        self._build_conteudo()
        self._carregar()

    def _build_banner(self):
        from views.widgets.ajuda import banner_ajuda
        b = banner_ajuda(
            self, self._cores,
            "Cadastre seus cartões e lance compras parceladas. Use '⬆ Importar "
            "Fatura' para importar o extrato do banco em CSV ou XLSX — o sistema "
            "detecta as parcelas e o histórico automaticamente.",
        )
        if b:
            b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))

    # ------------------------------------------------------------------

    def _build_header(self):
        cores = self._cores
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="💳  Cartões de Crédito",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=cores["texto"]).grid(row=0, column=0, sticky="w")

        self._var_inativos = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(header, text="Mostrar inativos",
                        variable=self._var_inativos,
                        command=self._carregar).grid(row=0, column=1, padx=12, sticky="e")

        from views.widgets.ajuda import Tooltip
        btn_importar = ctk.CTkButton(
            header, text="⬆ Importar Fatura ▾", height=32,
            fg_color="transparent", border_width=1,
            border_color=cores["primario"], text_color=cores["primario"],
        )
        btn_importar.configure(
            command=lambda b=btn_importar: self._abrir_menu_import(None, b)
        )
        btn_importar.grid(row=0, column=2, padx=8, sticky="e")
        Tooltip(btn_importar,
                "Importe a fatura do cartão em CSV ou XLSX.\n"
                "O sistema detecta parcelas (ex.: 7/12) e cria as compras "
                "automaticamente, com histórico das já pagas.")

        btn_novo = ctk.CTkButton(header, text="+ Novo Cartão", height=32,
                                 command=self._novo_cartao)
        btn_novo.grid(row=0, column=3, sticky="e")
        Tooltip(btn_novo,
                "Cadastre um novo cartão de crédito.\n"
                "Informe banco, bandeira, limite e dia de vencimento — "
                "o cartão aparecerá na grade com cor da bandeira.")

    def _build_conteudo(self):
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=12)
        self._scroll.grid_columnconfigure((0, 1), weight=1)

    # ------------------------------------------------------------------

    def _carregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        apenas_ativos = not self._var_inativos.get()
        cartoes = listar_cartoes(apenas_ativos=apenas_ativos)

        if not cartoes:
            ctk.CTkLabel(self._scroll,
                         text="Nenhum cartão cadastrado.\nClique em '+ Novo Cartão' para começar.",
                         text_color=self._cores["texto_mudo"],
                         font=ctk.CTkFont(size=14),
                         justify="center").grid(row=0, column=0, columnspan=2, pady=60)
            return

        for i, cartao in enumerate(cartoes):
            row, col = divmod(i, 2)
            self._card_cartao(cartao, row, col)

    # Proporção ISO 7810 ID-1: 85,6 × 53,98 mm — largura máxima ≈ tamanho real a ~96 DPI
    _CARD_RATIO   = 85.6 / 53.98   # ≈ 1.586
    _CARD_MAX_W   = 323             # px — 85,6 mm a 96 DPI

    def _card_cartao(self, cartao: Cartao, row: int, col: int):
        cores = self._cores

        # Container externo (ocupa a coluna inteira, mas o card fica centralizado)
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        # Card com tamanho fixo inicial; será recalculado pelo bind abaixo
        card_w = self._CARD_MAX_W
        card_h = int(card_w / self._CARD_RATIO)
        card = ctk.CTkFrame(outer, fg_color=cartao.cor_fundo, corner_radius=16,
                            width=card_w, height=card_h)
        card.pack(anchor="center", pady=2)   # centralizado, sem fill="x"
        card.pack_propagate(False)

        def _manter_proporcao(event, c=card):
            # Limita ao máximo do cartão real; nunca estica além disso
            w = min(event.width - 8, self._CARD_MAX_W)
            w = max(w, 120)
            c.configure(width=w, height=int(w / self._CARD_RATIO))

        outer.bind("<Configure>", _manter_proporcao)

        txt_cor = cartao.cor_texto

        # Linha topo: banco (esq) + logo/badge bandeira (dir)
        topo = ctk.CTkFrame(card, fg_color="transparent")
        topo.pack(fill="x", padx=16, pady=(14, 0))
        topo.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(topo, text=cartao.banco,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=txt_cor).grid(row=0, column=0, sticky="w")

        # Tenta carregar logo; se não existir usa badge de texto
        logo = carregar_logo_bandeira(cartao.bandeira, size=(58, 36))
        if logo:
            ctk.CTkLabel(topo, text="", image=logo,
                         fg_color="transparent").grid(row=0, column=1, sticky="e")
        else:
            band_cor = CORES_BANDEIRA.get(cartao.bandeira, "#FFFFFF")
            band_idx = BANDEIRAS.index(cartao.bandeira) if cartao.bandeira in BANDEIRAS else -1
            band_label = BANDEIRAS_LABEL[band_idx] if 0 <= band_idx < len(BANDEIRAS_LABEL) \
                         else cartao.bandeira.replace("_", " ").upper()
            ctk.CTkLabel(topo, text=f" {band_label} ",
                         fg_color="#FFFFFF", text_color=band_cor,
                         corner_radius=4,
                         font=ctk.CTkFont(size=10, weight="bold")
                         ).grid(row=0, column=1, sticky="e")

        # Número mascarado
        digits = cartao.ultimos_digitos or "----"
        ctk.CTkLabel(card, text=f"•••• •••• •••• {digits}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=txt_cor).pack(anchor="w", padx=16, pady=(10, 2))

        # Nome e dados
        ctk.CTkLabel(card, text=cartao.nome,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=txt_cor).pack(anchor="w", padx=16)

        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=16, pady=(4, 0))

        lim_txt = f"Limite: {formatar_moeda(cartao.limite)}"
        disp_txt = f"Disponível: {formatar_moeda(cartao.limite_disponivel)}"
        ctk.CTkLabel(info_frame, text=lim_txt,
                     font=ctk.CTkFont(size=10),
                     text_color=txt_cor).pack(side="left")
        venc_txt = f"Vence dia {cartao.dia_vencimento}" if cartao.dia_vencimento else ""
        ctk.CTkLabel(info_frame, text=venc_txt,
                     font=ctk.CTkFont(size=10),
                     text_color=txt_cor).pack(side="right")

        # Badge inativo
        if not cartao.ativo:
            ctk.CTkLabel(card, text="INATIVO",
                         fg_color="#000000", text_color="#FFFFFF",
                         corner_radius=4,
                         font=ctk.CTkFont(size=9, weight="bold"),
                         width=55, height=18).pack(anchor="e", padx=16, pady=(2, 0))

        # Botões de ação abaixo do card
        btns = ctk.CTkFrame(outer, fg_color="transparent")
        btns.pack(fill="x", pady=(4, 0))

        ctk.CTkButton(btns, text="+ Lançar", height=28, width=80,
                      font=ctk.CTkFont(size=11),
                      command=lambda c=cartao: self._lancar_compra(c)
                      ).pack(side="left", padx=2)

        btn_imp = ctk.CTkButton(btns, text="⬆ Importar ▾", height=28, width=100,
                                 font=ctk.CTkFont(size=11))
        btn_imp.configure(
            command=lambda c=cartao, b=btn_imp: self._abrir_menu_import(c, b)
        )
        btn_imp.pack(side="left", padx=2)

        ctk.CTkButton(btns, text="Ver faturas", height=28, width=90,
                      font=ctk.CTkFont(size=11),
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=lambda c=cartao: self._ver_faturas(c)
                      ).pack(side="left", padx=2)

        ctk.CTkButton(btns, text="✏ Editar", height=28, width=80,
                      font=ctk.CTkFont(size=11),
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=lambda c=cartao: self._editar_cartao(c)
                      ).pack(side="left", padx=2)

        tog_txt = "Desativar" if cartao.ativo else "Ativar"
        tog_cor = cores["atencao"] if cartao.ativo else cores["positivo"]
        ctk.CTkButton(btns, text=tog_txt, height=28, width=72,
                      font=ctk.CTkFont(size=11),
                      fg_color="transparent", border_width=1,
                      border_color=tog_cor, text_color=tog_cor,
                      command=lambda c=cartao: self._toggle_ativo(c)
                      ).pack(side="left", padx=2)

    # ------------------------------------------------------------------

    def _novo_cartao(self):
        from views.cartoes.form_cartao import FormCartao
        FormCartao(self, on_salvo=lambda: (self._carregar(),
                                           self._toast("Cartão salvo.")))

    def _editar_cartao(self, cartao: Cartao):
        from views.cartoes.form_cartao import FormCartao
        FormCartao(self, cartao=cartao,
                   on_salvo=lambda: (self._carregar(),
                                     self._toast("Cartão atualizado.")))

    def _lancar_compra(self, cartao: Cartao):
        from views.cartoes.form_compra import FormCompra
        FormCompra(self, cartao=cartao,
                   on_salvo=lambda msg: (self._carregar(),
                                         self._toast(msg)))

    def _abrir_menu_import(self, cartao, widget):
        """Mostra menu popup com opções Excel/CSV e PDF logo abaixo do botão."""
        from tkinter import Menu
        menu = Menu(self, tearoff=0)
        menu.add_command(
            label="📊  Excel / CSV (XLSX)",
            command=lambda c=cartao: self._importar_excel(c),
        )
        menu.add_command(
            label="📄  PDF da fatura",
            command=lambda c=cartao: self._importar_pdf(c),
        )
        try:
            x = widget.winfo_rootx()
            y = widget.winfo_rooty() + widget.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _importar_excel(self, cartao):
        from views.cartoes.importar_fatura_modal import ImportarFaturaModal
        ImportarFaturaModal(
            self, cartao=cartao,
            on_importado=lambda msg: (self._carregar(), self._toast(msg)),
        )

    def _importar_pdf(self, cartao):
        from views.cartoes.importar_fatura_pdf_modal import ImportarFaturaPDFModal
        ImportarFaturaPDFModal(
            self, cartao=cartao,
            on_importado=lambda msg: (self._carregar(), self._toast(msg)),
        )

    def _ver_faturas(self, cartao: Cartao):
        from views.cartoes.faturas_view import FaturasView
        FaturasView(self, cartao=cartao,
                    on_atualizado=self._carregar)

    def _toggle_ativo(self, cartao: Cartao):
        alternar_ativo_cartao(cartao.id, not cartao.ativo)
        self._carregar()
        acao = "desativado" if cartao.ativo else "ativado"
        self._toast(f"Cartão \"{cartao.nome}\" {acao}.")

    def _toast(self, mensagem: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        toast = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(toast, text=mensagem, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, toast.destroy)
