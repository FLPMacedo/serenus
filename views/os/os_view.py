"""
os_view.py — Tela principal do módulo de Ordem de Serviço (OS Interna).
Listagem em cards com filtros (status + busca) e ações por card.
"""
from __future__ import annotations

import customtkinter as ctk

from config import get_tema, formatar_moeda
from database import obter_configuracao
from views.os.os_model import (
    OrdemServico,
    cancelar_os,
    listar_historico,
    listar_os,
    obter_os,
)


# Labels e ordem dos filtros (None = "Todos")
_STATUS_LABEL: dict[str, str] = {
    "aberta":          "Aberta",
    "em_andamento":    "Em andamento",
    "aguardando_peca": "Aguard. peça",
    "concluida":       "Concluída",
    "cancelada":       "Cancelada",
}
_STATUS_FILTROS: list[tuple[str, str | None]] = (
    [("Todos", None)] + [(rotulo, chave) for chave, rotulo in _STATUS_LABEL.items()]
)


def _status_cores(status: str, cores: dict) -> tuple[str, str]:
    """Retorna (bg, fg) para o badge de status."""
    mapa = {
        "aberta":          (cores["atencao"],  "#FFFFFF"),
        "em_andamento":    (cores["primario"], "#FFFFFF"),
        "aguardando_peca": ("#EA580C",         "#FFFFFF"),
        "concluida":       (cores["positivo"], "#FFFFFF"),
        "cancelada":       (cores["borda"],    cores["texto_mudo"]),
    }
    return mapa.get(status, (cores["borda"], cores["texto"]))


class OrdensServicoView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores         = get_tema(obter_configuracao("tema", "claro"))
        self._busca         = ""
        self._status_filtro: str | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_banner()
        self._build_lista()
        self._carregar()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_banner(self):
        try:
            from views.widgets.ajuda import banner_ajuda
            b = banner_ajuda(
                self, self._cores,
                "Registre ordens de serviço internas: solicitante, materiais "
                "consumidos (da sua lista de Produtos) e mão de obra. Os valores "
                "ficam só na OS — não geram lançamento financeiro automático.",
            )
            if b:
                b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))
        except Exception:
            pass

    def _build_header(self):
        cores = self._cores
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="🔧  Ordens de Serviço",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=0, sticky="w")

        # Filtros (busca + status)
        filtros = ctk.CTkFrame(hdr, fg_color="transparent")
        filtros.grid(row=0, column=1, sticky="e", padx=8)

        self._entry_busca = ctk.CTkEntry(
            filtros, width=220, height=32,
            placeholder_text="Buscar nº, solicitante, descrição…",
        )
        self._entry_busca.pack(side="left", padx=(0, 8))
        self._entry_busca.bind("<KeyRelease>", lambda _e: self._on_busca_muda())

        self._combo_status = ctk.CTkComboBox(
            filtros, width=150, height=32, state="readonly",
            values=[opt[0] for opt in _STATUS_FILTROS],
            command=self._on_status_muda,
        )
        self._combo_status.set("Todos")
        self._combo_status.pack(side="left", padx=(0, 8))

        # Botões de ação
        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=2, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            btns, text="📦 Produtos", height=34,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._abrir_produtos,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btns, text="+ Nova OS", height=34,
            command=self._abrir_form_nova,
        ).pack(side="left")

    def _build_lista(self):
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=16)
        self._scroll.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Filtros
    # ------------------------------------------------------------------

    def _on_busca_muda(self):
        self._busca = self._entry_busca.get().strip()
        self._carregar()

    def _on_status_muda(self, _value):
        label = self._combo_status.get()
        for lbl, val in _STATUS_FILTROS:
            if lbl == label:
                self._status_filtro = val
                break
        self._carregar()

    # ------------------------------------------------------------------
    # Carregamento + cards
    # ------------------------------------------------------------------

    def _carregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        oss = listar_os(status=self._status_filtro,
                        busca=self._busca or None)
        if not oss:
            ctk.CTkLabel(
                self._scroll,
                text="Nenhuma ordem de serviço encontrada.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        n_curso = sum(
            1 for o in oss
            if o.status in ("aberta", "em_andamento", "aguardando_peca")
        )
        total = sum(o.valor_total for o in oss if o.status != "cancelada")
        ctk.CTkLabel(
            self._scroll,
            text=f"{len(oss)} OS  ·  {n_curso} em curso  ·  Total {formatar_moeda(total)}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self._cores["texto_mudo"],
            anchor="e",
        ).pack(anchor="e", pady=(0, 6))

        for o in oss:
            self._card_os(o)

    def _card_os(self, o: OrdemServico):
        cores              = self._cores
        badge_bg, badge_fg = _status_cores(o.status, cores)

        card = ctk.CTkFrame(self._scroll, fg_color=cores["card"],
                            corner_radius=10)
        card.pack(fill="x", pady=4)
        card.grid_columnconfigure(2, weight=1)

        # Número da OS
        ctk.CTkLabel(
            card, text=o.numero,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=cores["primario"], width=80,
        ).grid(row=0, column=0, padx=(12, 8), pady=10, rowspan=2)

        # Badge status
        ctk.CTkLabel(
            card,
            text=_STATUS_LABEL.get(o.status, o.status), width=110,
            fg_color=badge_bg, corner_radius=6,
            text_color=badge_fg,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=1, padx=4, pady=10, rowspan=2)

        # Linha 1: solicitante + setor + ramal
        partes_solic = [o.solicitante_nome or "(sem solicitante)"]
        if o.solicitante_setor:
            partes_solic.append(o.solicitante_setor)
        if o.solicitante_ramal:
            partes_solic.append(f"ramal {o.solicitante_ramal}")
        ctk.CTkLabel(
            card, text="  ·  ".join(partes_solic),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"], anchor="w",
        ).grid(row=0, column=2, sticky="w", padx=4, pady=(10, 0))

        # Linha 2: data + (truncada) descrição
        descr = o.descricao_servico.strip()
        if len(descr) > 90:
            descr = descr[:87] + "…"
        linha2 = f"Solicitada em {o.data_solicitacao}"
        if descr:
            linha2 += f"  ·  {descr}"
        ctk.CTkLabel(
            card, text=linha2,
            font=ctk.CTkFont(size=11),
            text_color=cores["texto_mudo"], anchor="w",
        ).grid(row=1, column=2, sticky="w", padx=4, pady=(0, 10))

        # Valor total da OS
        ctk.CTkLabel(
            card, text=formatar_moeda(o.valor_total),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=3, padx=16, rowspan=2)

        # Ações
        acoes = ctk.CTkFrame(card, fg_color="transparent")
        acoes.grid(row=0, column=4, padx=(0, 10), rowspan=2)

        ctk.CTkButton(
            acoes, text="✏ Editar", width=80, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            font=ctk.CTkFont(size=11),
            command=lambda oid=o.id: self._abrir_form_edicao(oid),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            acoes, text="🖨 Imprimir", width=88, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            font=ctk.CTkFont(size=11),
            command=lambda oid=o.id: self._imprimir(oid),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            acoes, text="📋 Histórico", width=92, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            font=ctk.CTkFont(size=11),
            command=lambda oid=o.id: self._abrir_historico(oid),
        ).pack(side="left", padx=2)

        if o.status != "cancelada":
            ctk.CTkButton(
                acoes, text="Cancelar", width=80, height=28,
                fg_color="transparent", border_width=1,
                border_color=cores["alerta"], text_color=cores["alerta"],
                font=ctk.CTkFont(size=11),
                command=lambda oid=o.id: self._confirmar_cancelar(oid),
            ).pack(side="left", padx=2)

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _abrir_form_nova(self):
        try:
            from views.os.form_os import FormOSModal
            FormOSModal(self, on_salvo=self._on_salvo)
        except ImportError:
            self._toast("Formulário de OS ainda não implementado.", "atencao")

    def _abrir_form_edicao(self, os_id: int):
        try:
            from views.os.form_os import FormOSModal
            FormOSModal(self, on_salvo=self._on_salvo, os_id=os_id)
        except ImportError:
            self._toast("Formulário de OS ainda não implementado.", "atencao")

    def _on_salvo(self):
        self._carregar()
        self._toast("Ordem de serviço salva.")

    def _imprimir(self, os_id: int):
        try:
            from tkinter.filedialog import asksaveasfilename
            from views.os.imprimir_os import imprimir_os_pdf
        except ImportError:
            self._toast("Impressão de OS ainda não implementada.", "atencao")
            return

        os_obj = obter_os(os_id)
        if not os_obj:
            self._toast("OS não encontrada.", "erro")
            return
        arquivo = asksaveasfilename(
            title="Salvar OS como PDF",
            defaultextension=".pdf",
            initialfile=f"{os_obj.numero}.pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not arquivo:
            return
        try:
            imprimir_os_pdf(os_obj, arquivo)
            self._toast(f"Salvo em {arquivo}.")
        except Exception as exc:
            self._toast(f"Falha ao gerar PDF: {exc}", "erro")

    def _confirmar_cancelar(self, os_id: int):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Confirmar cancelamento")
        dlg.geometry("380x150")
        dlg.grab_set()
        ctk.CTkLabel(
            dlg, text="Cancelar esta OS?",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(20, 4), padx=20)
        ctk.CTkLabel(
            dlg, text="Esta ação é registrada no histórico e não pode ser desfeita.",
            font=ctk.CTkFont(size=11),
            text_color=self._cores["texto_mudo"], wraplength=320,
        ).pack(pady=(0, 12), padx=20)
        botoes = ctk.CTkFrame(dlg, fg_color="transparent")
        botoes.pack(pady=4)
        ctk.CTkButton(
            botoes, text="Voltar", width=90,
            fg_color="transparent", border_width=1,
            border_color=self._cores["borda"], text_color=self._cores["texto"],
            command=dlg.destroy,
        ).pack(side="left", padx=4)

        def _confirma():
            cancelar_os(os_id)
            dlg.destroy()
            self._carregar()
            self._toast("Ordem cancelada.")

        ctk.CTkButton(
            botoes, text="Cancelar OS", width=110,
            fg_color=self._cores["alerta"], hover_color="#B91C1C",
            command=_confirma,
        ).pack(side="left", padx=4)

    def _abrir_historico(self, os_id: int):
        cores = self._cores
        os_obj = obter_os(os_id)
        hist   = listar_historico(os_id)
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Histórico — {os_obj.numero if os_obj else 'OS'}")
        dlg.geometry("520x420")
        dlg.grab_set()

        ctk.CTkLabel(
            dlg,
            text=f"📋 Histórico de alterações  ·  {os_obj.numero if os_obj else ''}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=cores["texto"],
        ).pack(pady=(16, 8), padx=16, anchor="w")

        scroll = ctk.CTkScrollableFrame(dlg, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        if not hist:
            ctk.CTkLabel(scroll, text="Sem alterações registradas.",
                         text_color=cores["texto_mudo"]).pack(pady=20)
            return

        for h in hist:
            linha = ctk.CTkFrame(scroll, fg_color=cores["card"],
                                  corner_radius=6)
            linha.pack(fill="x", pady=2)
            linha.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                linha, text=h.alterado_em,
                font=ctk.CTkFont(size=10),
                text_color=cores["texto_mudo"], width=140,
            ).grid(row=0, column=0, padx=8, pady=6, sticky="w")

            if h.campo == "criacao":
                detalhe = f"OS criada ({h.valor_novo or ''})"
            else:
                ant = h.valor_anterior if h.valor_anterior not in (None, "") else "—"
                nov = h.valor_novo     if h.valor_novo     not in (None, "") else "—"
                detalhe = f"{h.campo}: {ant} → {nov}"

            ctk.CTkLabel(
                linha, text=detalhe,
                font=ctk.CTkFont(size=12),
                text_color=cores["texto"], anchor="w",
            ).grid(row=0, column=1, padx=8, pady=6, sticky="w")

    def _abrir_produtos(self):
        # Reusa o modal de cadastro de produtos do módulo Vendas (compartilhado).
        from views.vendas.produtos_view import ProdutosView
        dlg = ctk.CTkToplevel(self)
        dlg.title("Produtos e Serviços")
        dlg.geometry("700x520")
        dlg.grab_set()
        view = ProdutosView(dlg)
        view.pack(fill="both", expand=True)

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
