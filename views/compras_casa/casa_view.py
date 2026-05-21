"""
casa_view.py — Tela do módulo Compras de Casa.

Duas abas:
  Estoque         — cadastro de itens, edição, ajuste rápido (+/-)
  Lista de Compras — itens onde estoque_atual <= estoque_minimo
"""

from __future__ import annotations

import customtkinter as ctk

from config import get_tema
from database import obter_configuracao
from views.compras_casa.casa_model import (
    ItemEstoque,
    ajustar_estoque,
    excluir_item,
    listar_itens,
    listar_lista_compras,
)


class ComprasCasaView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self._busca = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_abas()
        self._carregar_estoque()
        self._carregar_lista()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_header(self):
        cores = self._cores
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="🏠  Compras de Casa",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=0, sticky="w")

        filtros = ctk.CTkFrame(hdr, fg_color="transparent")
        filtros.grid(row=0, column=1, sticky="e", padx=8)
        self._entry_busca = ctk.CTkEntry(
            filtros, width=240, height=32,
            placeholder_text="Buscar por nome…",
        )
        self._entry_busca.pack(side="left", padx=(0, 8))
        self._entry_busca.bind("<KeyRelease>", lambda _e: self._on_busca())

        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=2, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            btns, text="+ Novo Item", height=34,
            command=self._abrir_form_novo,
        ).pack(side="left")

    def _build_abas(self):
        self._tab = ctk.CTkTabview(self)
        self._tab.grid(row=2, column=0, sticky="nsew", padx=20, pady=16)
        self._tab.add("Estoque")
        self._tab.add("Lista de Compras")
        for aba in ("Estoque", "Lista de Compras"):
            self._tab.tab(aba).grid_columnconfigure(0, weight=1)
            self._tab.tab(aba).grid_rowconfigure(0, weight=1)

        self._scroll_est = ctk.CTkScrollableFrame(
            self._tab.tab("Estoque"), fg_color="transparent",
        )
        self._scroll_est.grid(row=0, column=0, sticky="nsew")
        self._scroll_est.grid_columnconfigure(0, weight=1)

        self._scroll_lista = ctk.CTkScrollableFrame(
            self._tab.tab("Lista de Compras"), fg_color="transparent",
        )
        self._scroll_lista.grid(row=0, column=0, sticky="nsew")
        self._scroll_lista.grid_columnconfigure(0, weight=1)

        self._tab.configure(command=self._on_aba)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _on_busca(self):
        self._busca = self._entry_busca.get().strip()
        self._carregar_estoque()

    def _on_aba(self):
        aba = self._tab.get()
        if aba == "Estoque":
            self._carregar_estoque()
        else:
            self._carregar_lista()

    # ------------------------------------------------------------------
    # Aba Estoque
    # ------------------------------------------------------------------

    def _carregar_estoque(self):
        for w in self._scroll_est.winfo_children():
            w.destroy()

        itens = listar_itens(busca=self._busca or None)
        if not itens:
            ctk.CTkLabel(
                self._scroll_est,
                text="Nenhum item cadastrado. Clique em + Novo Item para começar.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=12),
            ).pack(pady=40)
            return

        precisam = sum(1 for i in itens if i.precisa_repor)
        ctk.CTkLabel(
            self._scroll_est,
            text=f"{len(itens)} item(ns)  ·  {precisam} precisam repor",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self._cores["texto_mudo"],
            anchor="w",
        ).pack(anchor="w", pady=(0, 6))

        for it in itens:
            self._card_estoque(it)

    def _card_estoque(self, it: ItemEstoque):
        cores = self._cores
        bg = "#FEE2E2" if it.precisa_repor else cores["card"]
        card = ctk.CTkFrame(self._scroll_est, fg_color=bg, corner_radius=10)
        card.pack(fill="x", pady=3)
        card.grid_columnconfigure(1, weight=1)

        # Coluna info
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=10)
        info.grid_columnconfigure(0, weight=1)

        cat = f" · {it.categoria}" if it.categoria else ""
        ctk.CTkLabel(
            info, text=f"{it.nome}{cat}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        un = f" {it.unidade}" if it.unidade else ""
        cor_estoque = cores["alerta"] if it.precisa_repor else cores["texto"]
        ctk.CTkLabel(
            info,
            text=f"Atual: {it.estoque_atual:g}{un}  ·  Mínimo: {it.estoque_minimo:g}{un}",
            font=ctk.CTkFont(size=11),
            text_color=cor_estoque, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Ações (linha 2)
        acoes = ctk.CTkFrame(card, fg_color="transparent")
        acoes.grid(row=1, column=0, columnspan=2, sticky="ew",
                   padx=12, pady=(0, 10))

        ctk.CTkButton(
            acoes, text="−", width=36, height=28,
            command=lambda i=it: self._ajustar(i, -1),
        ).pack(side="left", padx=(0, 2))
        ctk.CTkButton(
            acoes, text="+", width=36, height=28,
            command=lambda i=it: self._ajustar(i, +1),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            acoes, text="↻ Definir", width=84, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=lambda i=it: self._definir_estoque(i),
        ).pack(side="left", padx=2)

        ctk.CTkLabel(acoes, text=" ", width=8).pack(side="left", expand=True)

        ctk.CTkButton(
            acoes, text="✏ Editar", width=80, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=lambda i=it: self._abrir_form_edicao(i),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            acoes, text="🗑", width=36, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["alerta"], text_color=cores["alerta"],
            command=lambda i=it: self._confirmar_excluir(i),
        ).pack(side="left", padx=2)

    def _ajustar(self, it: ItemEstoque, delta: int):
        ajustar_estoque(it.id, delta=float(delta))
        self._carregar_estoque()

    def _definir_estoque(self, it: ItemEstoque):
        """Diálogo simples pra setar valor exato do estoque."""
        cores = self._cores
        dlg = ctk.CTkToplevel(self)
        dlg.title("Definir estoque")
        dlg.geometry("320x180")
        dlg.grab_set()
        ctk.CTkLabel(
            dlg, text=f"Definir estoque de {it.nome}",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=(16, 8), padx=20)
        e = ctk.CTkEntry(dlg, width=140, placeholder_text=str(it.estoque_atual))
        e.insert(0, f"{it.estoque_atual:g}".replace(".", ","))
        e.pack(pady=4)
        lbl = ctk.CTkLabel(dlg, text="", text_color=cores["alerta"],
                            font=ctk.CTkFont(size=10))
        lbl.pack()

        def _ok():
            from views.compras_casa.form_item import _parse_num
            try:
                ajustar_estoque(it.id, novo_valor=_parse_num(e.get()))
                dlg.destroy()
                self._carregar_estoque()
            except ValueError as ex:
                lbl.configure(text=str(ex))

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=8)
        ctk.CTkButton(
            btns, text="Cancelar", width=90,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=dlg.destroy,
        ).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="OK", width=90, command=_ok).pack(side="left", padx=4)
        e.bind("<Return>", lambda _ev: _ok())
        e.focus_set()

    # ------------------------------------------------------------------
    # Aba Lista de Compras
    # ------------------------------------------------------------------

    def _carregar_lista(self):
        for w in self._scroll_lista.winfo_children():
            w.destroy()

        itens = listar_lista_compras()
        if not itens:
            ctk.CTkLabel(
                self._scroll_lista,
                text="✅ Nada precisa ser comprado.\n"
                     "Itens aparecem aqui quando estoque atual fica no/abaixo do mínimo.",
                text_color=self._cores["positivo"],
                font=ctk.CTkFont(size=13, weight="bold"),
                justify="center",
            ).pack(pady=40)
            return

        # Header com contador + botões de export
        topo = ctk.CTkFrame(self._scroll_lista, fg_color="transparent")
        topo.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            topo, text=f"🛒 {len(itens)} item(ns) para comprar",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self._cores["alerta"], anchor="w",
        ).pack(side="left")
        ctk.CTkButton(
            topo, text="📱 WhatsApp", height=28, width=110,
            command=self._exportar_whatsapp,
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            topo, text="📄 PDF", height=28, width=90,
            fg_color="transparent", border_width=1,
            border_color=self._cores["borda"],
            text_color=self._cores["texto"],
            command=self._exportar_pdf,
        ).pack(side="right", padx=2)

        # Agrupa por categoria
        grupos: dict[str, list] = {}
        for it in itens:
            grupos.setdefault(it.categoria or "Sem categoria", []).append(it)

        for cat in sorted(grupos):
            ctk.CTkLabel(
                self._scroll_lista, text=cat,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self._cores["texto_mudo"],
                anchor="w",
            ).pack(anchor="w", pady=(8, 2))
            for it in grupos[cat]:
                self._linha_compra(it)

    def _linha_compra(self, it: ItemEstoque):
        cores = self._cores
        row = ctk.CTkFrame(self._scroll_lista, fg_color=cores["card"],
                            corner_radius=6)
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(1, weight=1)

        un = f" {it.unidade}" if it.unidade else ""
        ctk.CTkLabel(
            row, text=it.nome,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=cores["texto"], anchor="w",
        ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(
            row,
            text=f"Comprar: {it.quantidade_a_comprar:g}{un}"
                 f"  (atual {it.estoque_atual:g} · mín {it.estoque_minimo:g})",
            font=ctk.CTkFont(size=11),
            text_color=cores["texto_mudo"], anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=8)

        ctk.CTkButton(
            row, text="✓ Comprado",
            width=104, height=28,
            command=lambda i=it: self._marcar_comprado(i),
        ).grid(row=0, column=2, padx=8, pady=4)

    def _marcar_comprado(self, it: ItemEstoque):
        """Repõe estoque ao mínimo (atalho do botão 'Comprado')."""
        ajustar_estoque(it.id, novo_valor=it.estoque_minimo)
        self._carregar_lista()
        self._carregar_estoque()
        self._toast(f"{it.nome} reposto ao mínimo.")

    # ------------------------------------------------------------------
    # Form (novo/editar) e excluir
    # ------------------------------------------------------------------

    def _abrir_form_novo(self):
        from views.compras_casa.form_item import FormItemModal
        FormItemModal(self, on_salvo=self._on_item_salvo)

    def _abrir_form_edicao(self, it: ItemEstoque):
        from views.compras_casa.form_item import FormItemModal
        FormItemModal(self, on_salvo=self._on_item_salvo, item=it)

    def _on_item_salvo(self, _id: int):
        self._carregar_estoque()
        self._carregar_lista()
        self._toast("Item salvo.")

    def _confirmar_excluir(self, it: ItemEstoque):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Excluir item")
        dlg.geometry("360x140")
        dlg.grab_set()
        ctk.CTkLabel(
            dlg, text=f"Excluir '{it.nome}'?",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=20, padx=20)
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=4)
        ctk.CTkButton(
            btns, text="Cancelar", width=90,
            fg_color="transparent", border_width=1,
            border_color=self._cores["borda"], text_color=self._cores["texto"],
            command=dlg.destroy,
        ).pack(side="left", padx=4)

        def _exc():
            excluir_item(it.id)
            dlg.destroy()
            self._carregar_estoque()
            self._carregar_lista()
            self._toast("Item excluído.")

        ctk.CTkButton(
            btns, text="Excluir", width=100,
            fg_color=self._cores["alerta"], hover_color="#B91C1C",
            command=_exc,
        ).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # Exportações (PDF + WhatsApp)
    # ------------------------------------------------------------------

    def _exportar_pdf(self):
        from tkinter import filedialog
        from datetime import date as _date
        from views.compras_casa.imprimir_lista import imprimir_lista_pdf

        itens = listar_lista_compras()
        if not itens:
            self._toast("Lista vazia — nada a exportar.", "atencao")
            return
        nome_inicial = f"lista_compras_{_date.today().isoformat()}.pdf"
        destino = filedialog.asksaveasfilename(
            title="Salvar lista como PDF",
            defaultextension=".pdf",
            initialfile=nome_inicial,
            filetypes=[("PDF", "*.pdf")],
        )
        if not destino:
            return
        try:
            imprimir_lista_pdf(itens, destino)
            self._toast(f"PDF salvo: {destino}")
        except Exception as e:
            self._toast(f"Erro ao gerar PDF: {e}", "erro")

    def _exportar_whatsapp(self):
        """Abre diálogo pra confirmar/inserir número, copia texto pro
        clipboard, abre wa.me no navegador."""
        import webbrowser
        from database import obter_configuracao, salvar_configuracao
        from views.compras_casa.imprimir_lista import (
            formatar_texto_lista, gerar_link_whatsapp,
        )

        itens = listar_lista_compras()
        if not itens:
            self._toast("Lista vazia — nada a enviar.", "atencao")
            return

        texto = formatar_texto_lista(itens)
        numero_salvo = obter_configuracao("whatsapp_numero_padrao", "")

        cores = self._cores
        dlg = ctk.CTkToplevel(self)
        dlg.title("Enviar lista pelo WhatsApp")
        dlg.geometry("440x260")
        dlg.grab_set()
        ctk.CTkLabel(
            dlg, text="📱 Enviar lista pelo WhatsApp",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=cores["texto"],
        ).pack(pady=(16, 4), padx=20)
        ctk.CTkLabel(
            dlg, text="Vou abrir o WhatsApp Web/Desktop com a lista já\n"
                       "formatada. Você só clica em enviar.",
            font=ctk.CTkFont(size=11),
            text_color=cores["texto_mudo"], justify="center",
        ).pack(pady=(0, 12), padx=20)
        ctk.CTkLabel(
            dlg, text="Número do destinatário (com DDD)",
            font=ctk.CTkFont(size=11),
            text_color=cores["texto"], anchor="w",
        ).pack(anchor="w", padx=20)
        e_num = ctk.CTkEntry(dlg, placeholder_text="Ex.: 31999990000")
        e_num.insert(0, numero_salvo)
        e_num.pack(fill="x", padx=20, pady=(2, 4))
        var_lembrar = ctk.BooleanVar(value=bool(numero_salvo))
        ctk.CTkCheckBox(
            dlg, text="Lembrar este número como padrão",
            variable=var_lembrar,
        ).pack(anchor="w", padx=20, pady=4)

        def _enviar():
            numero = e_num.get().strip()
            if var_lembrar.get() and numero:
                salvar_configuracao("whatsapp_numero_padrao", numero)
            elif not var_lembrar.get():
                salvar_configuracao("whatsapp_numero_padrao", "")
            # Copia texto pro clipboard como fallback
            try:
                self.clipboard_clear()
                self.clipboard_append(texto)
            except Exception:
                pass
            url = gerar_link_whatsapp(texto, numero=numero)
            webbrowser.open(url, new=2)
            dlg.destroy()
            self._toast("WhatsApp aberto. Texto também copiado.")

        def _so_copiar():
            try:
                self.clipboard_clear()
                self.clipboard_append(texto)
                self._toast("Texto copiado.")
            except Exception as e:
                self._toast(f"Falha ao copiar: {e}", "erro")
            dlg.destroy()

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=8)
        ctk.CTkButton(
            btns, text="Cancelar", width=90,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=dlg.destroy,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btns, text="Só copiar texto", width=130,
            fg_color="transparent", border_width=1,
            border_color=cores["primario"], text_color=cores["primario"],
            command=_so_copiar,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btns, text="Abrir WhatsApp", width=130, command=_enviar,
        ).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # Toast
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
