"""
vendas_view.py — Tela principal do módulo de Vendas.
Abas: "Vendas do Mês" | "A Receber" | "Produtos/Serviços"
"""
from __future__ import annotations
from datetime import date
import customtkinter as ctk
from config import get_tema, formatar_moeda
from database import obter_configuracao
from views.vendas.venda_model import (
    Venda, ContaReceber,
    listar_vendas, listar_contas_receber, cancelar_venda,
)


class VendasView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self._mes   = date.today().month
        self._ano   = date.today().year
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_abas()
        self._carregar_vendas()

    # ------------------------------------------------------------------
    def _build_header(self):
        cores = self._cores
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="🛒  Vendas",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=0, sticky="w")

        # Navegação mês
        nav = ctk.CTkFrame(hdr, fg_color="transparent")
        nav.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(nav, text="◀", width=32, height=32,
                      command=self._mes_anterior).pack(side="left", padx=2)
        self._lbl_mes = ctk.CTkLabel(
            nav, text=self._mes_str(),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"], width=100,
        )
        self._lbl_mes.pack(side="left", padx=4)
        ctk.CTkButton(nav, text="▶", width=32, height=32,
                      command=self._proximo_mes).pack(side="left", padx=2)

        # Botões de ação
        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=2, sticky="e", padx=(16, 0))
        ctk.CTkButton(
            btns, text="📦 Produtos", height=34,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._abrir_produtos,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btns, text="+ Nova venda", height=34,
            command=self._abrir_form_venda,
        ).pack(side="left")

    def _build_abas(self):
        self._tab = ctk.CTkTabview(self)
        self._tab.grid(row=1, column=0, sticky="nsew", padx=20, pady=16)
        self._tab.add("Vendas do Mês")
        self._tab.add("A Receber")
        for aba in ("Vendas do Mês", "A Receber"):
            self._tab.tab(aba).grid_columnconfigure(0, weight=1)
            self._tab.tab(aba).grid_rowconfigure(0, weight=1)

        self._scroll_vendas = ctk.CTkScrollableFrame(
            self._tab.tab("Vendas do Mês"), fg_color="transparent"
        )
        self._scroll_vendas.grid(row=0, column=0, sticky="nsew")
        self._scroll_vendas.grid_columnconfigure(0, weight=1)

        self._scroll_receber = ctk.CTkScrollableFrame(
            self._tab.tab("A Receber"), fg_color="transparent"
        )
        self._scroll_receber.grid(row=0, column=0, sticky="nsew")
        self._scroll_receber.grid_columnconfigure(0, weight=1)

        self._tab.configure(command=self._on_aba_muda)

    # ------------------------------------------------------------------
    def _mes_str(self) -> str:
        meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                 "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        return f"{meses[self._mes - 1]}/{self._ano}"

    def _mes_anterior(self):
        if self._mes == 1:
            self._mes, self._ano = 12, self._ano - 1
        else:
            self._mes -= 1
        self._lbl_mes.configure(text=self._mes_str())
        self._carregar_vendas()

    def _proximo_mes(self):
        if self._mes == 12:
            self._mes, self._ano = 1, self._ano + 1
        else:
            self._mes += 1
        self._lbl_mes.configure(text=self._mes_str())
        self._carregar_vendas()

    def _on_aba_muda(self):
        aba = self._tab.get()
        if aba == "A Receber":
            self._carregar_receber()
        else:
            self._carregar_vendas()

    # ------------------------------------------------------------------
    def _carregar_vendas(self):
        for w in self._scroll_vendas.winfo_children():
            w.destroy()

        vendas = listar_vendas(self._mes, self._ano)
        if not vendas:
            ctk.CTkLabel(
                self._scroll_vendas,
                text="Nenhuma venda neste mês.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        total_mes = sum(v.valor_liquido for v in vendas
                        if v.status != "cancelada")
        ctk.CTkLabel(
            self._scroll_vendas,
            text=f"Total do mês: {formatar_moeda(total_mes)}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self._cores["positivo"],
            anchor="e",
        ).pack(anchor="e", pady=(0, 6))

        for v in vendas:
            self._card_venda(v)

    def _card_venda(self, v: Venda):
        cores   = self._cores
        status_cores = {
            "paga":      (cores["positivo"], "#FFFFFF"),
            "pendente":  (cores["atencao"],  "#000000"),
            "parcial":   (cores["primario"], "#FFFFFF"),
            "cancelada": (cores["borda"],    cores["texto_mudo"]),
        }
        badge_bg, badge_fg = status_cores.get(
            v.status, (cores["borda"], cores["texto"])
        )

        card = ctk.CTkFrame(self._scroll_vendas, fg_color=cores["card"],
                            corner_radius=10)
        card.pack(fill="x", pady=4)
        card.grid_columnconfigure(1, weight=1)

        # Badge status
        ctk.CTkLabel(
            card, text=v.status.upper(), width=72,
            fg_color=badge_bg, corner_radius=6,
            text_color=badge_fg,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=0, padx=(10, 8), pady=10, rowspan=2)

        # Info
        desc = v.descricao or f"Venda #{v.id}"
        ctk.CTkLabel(
            card, text=desc,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"], anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=4, pady=(10, 0))
        tipo_txt = "À vista" if v.tipo_pagamento == "avista" else (
            f"A prazo — {v.recebimentos_recebidos}/{v.recebimentos_recebidos + v.recebimentos_pendentes} parcelas"
        )
        ctk.CTkLabel(
            card,
            text=f"{v.data_venda}  ·  {tipo_txt}",
            font=ctk.CTkFont(size=11),
            text_color=cores["texto_mudo"], anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=4, pady=(0, 10))

        # Valor
        ctk.CTkLabel(
            card, text=formatar_moeda(v.valor_liquido),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=2, padx=16, rowspan=2)

        # Ações
        acoes = ctk.CTkFrame(card, fg_color="transparent")
        acoes.grid(row=0, column=3, padx=(0, 10), rowspan=2)
        if v.status not in ("cancelada",):
            ctk.CTkButton(
                acoes, text="Cancelar", width=72, height=28,
                fg_color="transparent", border_width=1,
                border_color=cores["alerta"], text_color=cores["alerta"],
                font=ctk.CTkFont(size=11),
                command=lambda vid=v.id: self._cancelar(vid),
            ).pack(pady=2)

    def _cancelar(self, venda_id: int):
        cancelar_venda(venda_id)
        self._carregar_vendas()
        self._toast("Venda cancelada.")

    # ------------------------------------------------------------------
    def _carregar_receber(self):
        for w in self._scroll_receber.winfo_children():
            w.destroy()

        receber = listar_contas_receber(status="pendente")
        if not receber:
            ctk.CTkLabel(
                self._scroll_receber,
                text="Nenhum recebível pendente.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        total = sum(r.valor for r in receber)
        ctk.CTkLabel(
            self._scroll_receber,
            text=f"Total pendente: {formatar_moeda(total)}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self._cores["atencao"],
            anchor="e",
        ).pack(anchor="e", pady=(0, 6))

        hoje = date.today().isoformat()
        for r in receber:
            self._card_receber(r, hoje)

    def _card_receber(self, r: ContaReceber, hoje: str):
        cores    = self._cores
        vencido  = r.data_vencimento < hoje
        bg_cor   = "#FEE2E2" if vencido else cores["card"]

        card = ctk.CTkFrame(self._scroll_receber, fg_color=bg_cor,
                            corner_radius=10)
        card.pack(fill="x", pady=4)
        card.grid_columnconfigure(1, weight=1)

        # Parcela badge
        parc_txt = (f"{r.numero_parcela}/{r.total_parcelas}"
                    if r.total_parcelas > 1 else "À vista")
        ctk.CTkLabel(
            card, text=parc_txt, width=60,
            fg_color=cores["primario"] if not vencido else cores["alerta"],
            corner_radius=6, text_color="#FFFFFF",
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=0, padx=(10, 8), pady=10, rowspan=2)

        ctk.CTkLabel(
            card, text=r.descricao,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"], anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=4, pady=(10, 0))
        venc_str = (f"Venceu em {r.data_vencimento}" if vencido
                    else f"Vence em {r.data_vencimento}")
        ctk.CTkLabel(
            card, text=venc_str,
            font=ctk.CTkFont(size=11),
            text_color=cores["alerta"] if vencido else cores["texto_mudo"],
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=4, pady=(0, 10))

        ctk.CTkLabel(
            card, text=formatar_moeda(r.valor),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=2, padx=16, rowspan=2)

        ctk.CTkButton(
            card, text="✓ Recebido", width=90, height=30,
            fg_color=cores["positivo"], hover_color="#15803D",
            text_color="#FFFFFF", font=ctk.CTkFont(size=11),
            command=lambda rec=r: self._abrir_recebimento(rec),
        ).grid(row=0, column=3, padx=(0, 10), rowspan=2)

    # ------------------------------------------------------------------
    def _abrir_form_venda(self):
        from views.vendas.form_venda import FormVendaModal
        FormVendaModal(self, on_salvo=self._on_venda_salva)

    def _on_venda_salva(self):
        self._carregar_vendas()
        self._toast("Venda registrada com sucesso.")

    def _abrir_produtos(self):
        from views.vendas.produtos_view import ProdutosView
        dlg = ctk.CTkToplevel(self)
        dlg.title("Produtos e Serviços")
        dlg.geometry("700x520")
        dlg.grab_set()
        view = ProdutosView(dlg)
        view.pack(fill="both", expand=True)

    def _abrir_recebimento(self, rec: ContaReceber):
        from views.vendas.form_recebimento import FormRecebimentoModal
        FormRecebimentoModal(self, on_salvo=self._on_recebimento_salvo,
                             conta=rec)

    def _on_recebimento_salvo(self):
        self._carregar_receber()
        self._carregar_vendas()
        self._toast("Recebimento registrado.")

    # ------------------------------------------------------------------
    def _toast(self, mensagem: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        toast = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(toast, text=mensagem, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, toast.destroy)
