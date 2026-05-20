"""
clientes_view.py — Tela de clientes vinculados ao módulo OS.

Layout em duas colunas:
  Esquerda  — lista de clientes em cards (busca por nome/doc/email)
  Direita   — detalhes do cliente selecionado + histórico de OS dele

Ações por card: editar, excluir (bloqueado se houver OS), ver histórico.
Botão "+ Novo Cliente" no header.
"""

from __future__ import annotations

import customtkinter as ctk

from config import formatar_data_exibicao, formatar_moeda, get_tema
from database import obter_configuracao
from views.os.cliente_model import (
    Cliente,
    buscar_clientes,
    excluir_cliente,
    listar_clientes,
)
from views.os.os_model import listar_os


_STATUS_LABEL = {
    "aberta":          "Aberta",
    "em_andamento":    "Em andamento",
    "aguardando_peca": "Aguard. peça",
    "concluida":       "Concluída",
    "cancelada":       "Cancelada",
}


def _status_cor(status: str, cores: dict) -> str:
    mapa = {
        "aberta":          cores["atencao"],
        "em_andamento":    cores["primario"],
        "aguardando_peca": "#EA580C",
        "concluida":       cores["positivo"],
        "cancelada":       cores["borda"],
    }
    return mapa.get(status, cores["borda"])


class ClientesView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores      = get_tema(obter_configuracao("tema", "claro"))
        self._busca      = ""
        self._cli_atual: Cliente | None = None

        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_corpo()
        self._carregar_lista()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_header(self):
        cores = self._cores
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew",
                 padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="👥  Clientes",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=0, sticky="w")

        # Busca
        filtros = ctk.CTkFrame(hdr, fg_color="transparent")
        filtros.grid(row=0, column=1, sticky="e", padx=8)
        self._entry_busca = ctk.CTkEntry(
            filtros, width=260, height=32,
            placeholder_text="Buscar por nome, documento, e-mail…",
        )
        self._entry_busca.pack(side="left", padx=(0, 8))
        self._entry_busca.bind("<KeyRelease>", lambda _e: self._on_busca())

        # Botão novo
        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=2, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            btns, text="+ Novo Cliente", height=34,
            command=self._abrir_form_novo,
        ).pack(side="left")

    def _build_corpo(self):
        cores = self._cores

        # Coluna esquerda — lista de clientes
        self._scroll_lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll_lista.grid(row=1, column=0, sticky="nsew",
                                 padx=(20, 8), pady=16)
        self._scroll_lista.grid_columnconfigure(0, weight=1)

        # Coluna direita — detalhes + histórico
        self._frame_det = ctk.CTkScrollableFrame(
            self, fg_color=cores["fundo"], corner_radius=10,
        )
        self._frame_det.grid(row=1, column=1, sticky="nsew",
                              padx=(8, 20), pady=16)
        self._frame_det.grid_columnconfigure(0, weight=1)
        self._mostrar_placeholder_det()

    # ------------------------------------------------------------------
    # Lista (esquerda)
    # ------------------------------------------------------------------

    def _on_busca(self):
        self._busca = self._entry_busca.get().strip()
        self._carregar_lista()

    def _carregar_lista(self):
        for w in self._scroll_lista.winfo_children():
            w.destroy()

        clientes = buscar_clientes(self._busca or None)
        if not clientes:
            ctk.CTkLabel(
                self._scroll_lista,
                text="Nenhum cliente encontrado.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=12),
            ).pack(pady=20)
            return

        ctk.CTkLabel(
            self._scroll_lista,
            text=f"{len(clientes)} cliente(s)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self._cores["texto_mudo"],
            anchor="w",
        ).pack(anchor="w", pady=(0, 6))

        for c in clientes:
            self._card_cliente(c)

    def _card_cliente(self, c: Cliente):
        cores = self._cores
        selecionado = (self._cli_atual is not None
                        and self._cli_atual.id == c.id)
        bg = cores["primario"] if selecionado else cores["card"]
        fg = "#FFFFFF" if selecionado else cores["texto"]

        card = ctk.CTkFrame(self._scroll_lista, fg_color=bg, corner_radius=8)
        card.pack(fill="x", pady=3)
        card.grid_columnconfigure(0, weight=1)

        nome = ctk.CTkLabel(
            card, text=c.nome,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=fg, anchor="w",
        )
        nome.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))

        partes = []
        if c.telefone:
            partes.append(f"📞 {c.telefone}")
        if c.email:
            partes.append(f"✉ {c.email}")
        sub = "   ".join(partes) if partes else "—"
        ctk.CTkLabel(
            card, text=sub,
            font=ctk.CTkFont(size=10),
            text_color=fg if selecionado else cores["texto_mudo"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))

        # Click no card abre detalhes
        for widget in (card, nome):
            widget.bind("<Button-1>", lambda _e, cli=c: self._selecionar(cli))

    def _selecionar(self, c: Cliente):
        self._cli_atual = c
        self._carregar_lista()
        self._mostrar_detalhes(c)

    # ------------------------------------------------------------------
    # Detalhes (direita)
    # ------------------------------------------------------------------

    def _mostrar_placeholder_det(self):
        for w in self._frame_det.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self._frame_det,
            text="Selecione um cliente à esquerda\npara ver detalhes e histórico.",
            text_color=self._cores["texto_mudo"],
            font=ctk.CTkFont(size=13),
            justify="center",
        ).pack(pady=80)

    def _mostrar_detalhes(self, c: Cliente):
        cores = self._cores
        for w in self._frame_det.winfo_children():
            w.destroy()

        # Cabeçalho com nome + ações
        topo = ctk.CTkFrame(self._frame_det, fg_color="transparent")
        topo.pack(fill="x", padx=16, pady=(16, 4))
        topo.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            topo, text=c.nome,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=cores["texto"], anchor="w",
        ).grid(row=0, column=0, sticky="w")
        acoes = ctk.CTkFrame(topo, fg_color="transparent")
        acoes.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            acoes, text="✏ Editar", width=80, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=lambda: self._abrir_form_edicao(c),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            acoes, text="🗑 Excluir", width=82, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["alerta"], text_color=cores["alerta"],
            command=lambda: self._confirmar_excluir(c),
        ).pack(side="left", padx=2)

        # Dados de contato
        def linha(label: str, valor: str):
            if not valor:
                return
            row = ctk.CTkFrame(self._frame_det, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=1)
            ctk.CTkLabel(
                row, text=f"{label}:",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=cores["texto_mudo"], width=120, anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=valor,
                font=ctk.CTkFont(size=12),
                text_color=cores["texto"], anchor="w",
            ).pack(side="left", padx=4)

        linha("CPF/CNPJ", c.documento)
        linha("Telefone", c.telefone)
        linha("WhatsApp", c.whatsapp)
        linha("E-mail",   c.email)
        linha("CEP",      c.cep)
        linha("Endereço", c.endereco)
        if c.observacao:
            ctk.CTkLabel(
                self._frame_det, text="Observações:",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=cores["texto_mudo"], anchor="w",
            ).pack(anchor="w", padx=16, pady=(8, 2))
            ctk.CTkLabel(
                self._frame_det, text=c.observacao,
                font=ctk.CTkFont(size=11),
                text_color=cores["texto"], wraplength=400, justify="left",
            ).pack(anchor="w", padx=16)

        # Histórico de OS
        ctk.CTkFrame(self._frame_det, height=1,
                     fg_color=cores["borda"]).pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(
            self._frame_det,
            text="📋 Histórico de Ordens de Serviço",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=cores["texto"], anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 6))

        oss = listar_os(cliente_id=c.id)
        if not oss:
            ctk.CTkLabel(
                self._frame_det,
                text="Nenhuma OS registrada para este cliente.",
                font=ctk.CTkFont(size=11),
                text_color=cores["texto_mudo"],
            ).pack(padx=16, pady=8)
            return

        total = sum(o.valor_total for o in oss if o.status != "cancelada")
        n_curso = sum(
            1 for o in oss
            if o.status in ("aberta", "em_andamento", "aguardando_peca")
        )
        ctk.CTkLabel(
            self._frame_det,
            text=f"{len(oss)} OS  ·  {n_curso} em curso  ·  Total {formatar_moeda(total)}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=cores["texto_mudo"], anchor="w",
        ).pack(anchor="w", padx=16, pady=(0, 4))

        for o in oss:
            self._linha_os(o)

    def _linha_os(self, o):
        cores = self._cores
        row = ctk.CTkFrame(self._frame_det, fg_color=cores["card"],
                            corner_radius=6)
        row.pack(fill="x", padx=16, pady=2)
        row.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            row, text=o.numero,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=cores["primario"], width=72,
        ).grid(row=0, column=0, padx=8, pady=6)

        ctk.CTkLabel(
            row, text=_STATUS_LABEL.get(o.status, o.status), width=100,
            fg_color=_status_cor(o.status, cores),
            text_color="#FFFFFF", corner_radius=4,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=1, padx=4, pady=6)

        descr = o.descricao_servico.strip()
        if len(descr) > 50:
            descr = descr[:47] + "…"
        ctk.CTkLabel(
            row,
            text=f"{formatar_data_exibicao(o.data_solicitacao)}  ·  {descr}",
            font=ctk.CTkFont(size=11),
            text_color=cores["texto_mudo"], anchor="w",
        ).grid(row=0, column=2, sticky="w", padx=4, pady=6)

        ctk.CTkLabel(
            row, text=formatar_moeda(o.valor_total),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=3, padx=8, pady=6)

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _abrir_form_novo(self):
        from views.os.form_cliente import FormClienteModal
        FormClienteModal(self, on_salvo=self._on_cliente_salvo)

    def _abrir_form_edicao(self, c: Cliente):
        from views.os.form_cliente import FormClienteModal
        FormClienteModal(self, on_salvo=self._on_cliente_salvo, cliente=c)

    def _on_cliente_salvo(self, cid: int):
        from views.os.cliente_model import obter_cliente
        c = obter_cliente(cid)
        self._cli_atual = c
        self._carregar_lista()
        if c:
            self._mostrar_detalhes(c)
        self._toast("Cliente salvo.")

    def _confirmar_excluir(self, c: Cliente):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Confirmar exclusão")
        dlg.geometry("420x150")
        dlg.grab_set()
        ctk.CTkLabel(
            dlg, text=f"Excluir cliente '{c.nome}'?",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(20, 4), padx=20)
        ctk.CTkLabel(
            dlg, text="Será bloqueado se houver OS vinculadas.",
            font=ctk.CTkFont(size=11),
            text_color=self._cores["texto_mudo"],
        ).pack(pady=(0, 12))
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=4)
        ctk.CTkButton(
            btns, text="Cancelar", width=90,
            fg_color="transparent", border_width=1,
            border_color=self._cores["borda"], text_color=self._cores["texto"],
            command=dlg.destroy,
        ).pack(side="left", padx=4)

        def _exc():
            ok, msg = excluir_cliente(c.id)
            dlg.destroy()
            if not ok:
                self._toast(msg, "erro")
                return
            self._cli_atual = None
            self._carregar_lista()
            self._mostrar_placeholder_det()
            self._toast("Cliente excluído.")

        ctk.CTkButton(
            btns, text="Excluir", width=100,
            fg_color=self._cores["alerta"], hover_color="#B91C1C",
            command=_exc,
        ).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # Toast
    # ------------------------------------------------------------------

    def _toast(self, mensagem: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        toast = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(
            toast, text=mensagem, text_color="#FFFFFF",
            font=ctk.CTkFont(size=12),
        ).pack(padx=16, pady=8)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, toast.destroy)
