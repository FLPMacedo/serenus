"""
lista_view.py — Listagem mensal de Contas a Pagar com filtros e ações.
"""

from __future__ import annotations
import customtkinter as ctk
from datetime import date
from config import get_tema, formatar_moeda, formatar_data_exibicao, LABEL_TIPO_CUSTO
from database import obter_configuracao
from views.contas_pagar.conta_model import (
    ContaPagar, listar_contas, buscar_contas_pagar,
    marcar_pago, excluir_conta, totais_periodo,
)


COLUNAS = [
    ("Conta",       180),
    ("Descrição",   160),
    ("Tipo",         70),
    ("Valor",        90),
    ("Vencimento",   95),
    ("Status",       80),
    ("Ações",       130),
]


class ContasPagarView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        hoje = date.today()
        self._mes = hoje.month
        self._ano = hoje.year
        self._filtro_status    = None
        self._filtro_tipo      = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._build_header()
        self._build_banner()
        self._build_tabela()
        self._build_rodape()
        self._carregar()

    def _build_banner(self):
        from views.widgets.ajuda import banner_ajuda
        b = banner_ajuda(
            self, self._cores,
            "Liste e gerencie suas despesas do mês. Use '+ Nova despesa' para "
            "lançar uma conta (com opção de pagar no cartão de crédito ou "
            "criar despesa recorrente).",
        )
        if b:
            b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))

    # ------------------------------------------------------------------
    # Header: título + filtros + botão novo
    # ------------------------------------------------------------------

    def _build_header(self):
        cores = self._cores
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="💸  Contas a Pagar",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=cores["texto"]).grid(row=0, column=0, sticky="w")

        # Navegação mês/ano
        nav = ctk.CTkFrame(header, fg_color="transparent")
        nav.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(nav, text="◀", width=30, height=28,
                      command=self._mes_anterior).pack(side="left", padx=2)
        self._lbl_mes = ctk.CTkLabel(nav, text="", width=120,
                                     font=ctk.CTkFont(size=14, weight="bold"))
        self._lbl_mes.pack(side="left", padx=4)
        ctk.CTkButton(nav, text="▶", width=30, height=28,
                      command=self._mes_proximo).pack(side="left", padx=2)

        # Filtros
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 0))

        ctk.CTkLabel(filtros, text="Status:").pack(side="left", padx=(0, 4))
        self._combo_status = ctk.CTkComboBox(
            filtros, width=120,
            values=["Todos", "Pendente", "Pago", "Cancelado"],
            command=self._on_filtro_status,
        )
        self._combo_status.set("Todos")
        self._combo_status.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(filtros, text="Tipo:").pack(side="left", padx=(0, 4))
        self._combo_tipo = ctk.CTkComboBox(
            filtros, width=120,
            values=["Todos", "Fixo", "Variável"],
            command=self._on_filtro_tipo,
        )
        self._combo_tipo.set("Todos")
        self._combo_tipo.pack(side="left", padx=(0, 16))

        self._entry_busca_cp = ctk.CTkEntry(
            filtros, placeholder_text="🔍  Buscar…", width=200, height=30,
            font=ctk.CTkFont(size=12),
        )
        self._entry_busca_cp.pack(side="left", padx=(0, 8))
        self._entry_busca_cp.bind("<KeyRelease>", lambda e: self._carregar())

        ctk.CTkButton(filtros, text="⬇ Excel", height=32, width=80,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["borda"],
                      text_color=self._cores["texto"],
                      command=self._exportar_excel).pack(side="right", padx=(0, 6))
        ctk.CTkButton(filtros, text="+ Nova despesa", height=32,
                      command=self._abrir_form_novo).pack(side="right")

    # ------------------------------------------------------------------
    # Tabela
    # ------------------------------------------------------------------

    def _build_tabela(self):
        cores = self._cores

        # Cabeçalho fixo
        cab = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        cab.grid(row=3, column=0, sticky="ew", padx=20, pady=(8, 0))
        for i, (nome, larg) in enumerate(COLUNAS):
            ctk.CTkLabel(cab, text=nome, width=larg,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(
                row=0, column=i, padx=6, pady=6, sticky="w"
            )

        # Área scrollável para as linhas
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.grid(row=4, column=0, sticky="nsew", padx=20, pady=(2, 0))
        self.grid_rowconfigure(4, weight=1)

    def _build_rodape(self):
        cores = self._cores
        rod = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        rod.grid(row=5, column=0, sticky="ew", padx=20, pady=(8, 16))

        self._lbl_pendente = ctk.CTkLabel(rod, text="Pendente: —",
                                          text_color=cores["atencao"],
                                          font=ctk.CTkFont(weight="bold"))
        self._lbl_pendente.pack(side="left", padx=20, pady=8)

        self._lbl_pago = ctk.CTkLabel(rod, text="Pago: —",
                                      text_color=cores["positivo"],
                                      font=ctk.CTkFont(weight="bold"))
        self._lbl_pago.pack(side="left", padx=20)

        self._lbl_total = ctk.CTkLabel(rod, text="Total: —",
                                       font=ctk.CTkFont(weight="bold"))
        self._lbl_total.pack(side="right", padx=20)

    # ------------------------------------------------------------------
    # Carga de dados
    # ------------------------------------------------------------------

    def _carregar(self):
        from config import NOMES_MESES
        self._lbl_mes.configure(
            text=f"{NOMES_MESES[self._mes-1]} / {self._ano}"
        )

        texto_busca = self._entry_busca_cp.get().strip() if hasattr(self, "_entry_busca_cp") else ""
        if texto_busca:
            contas = buscar_contas_pagar(
                texto_busca,
                status=self._filtro_status,
                mes=self._mes, ano=self._ano,
            )
        else:
            contas = listar_contas(
                self._mes, self._ano,
                status=self._filtro_status,
                tipo_custo=self._filtro_tipo,
            )

        # Limpa linhas antigas
        for w in self._scroll.winfo_children():
            w.destroy()

        if not contas:
            ctk.CTkLabel(self._scroll, text="Nenhuma despesa neste período.",
                         text_color=self._cores["texto_mudo"]).pack(pady=24)
        else:
            for c in contas:
                self._linha(c)

        # Rodapé
        tots = totais_periodo(self._mes, self._ano)
        self._lbl_pendente.configure(
            text=f"Pendente: {formatar_moeda(tots['pendente'])}")
        self._lbl_pago.configure(
            text=f"Pago: {formatar_moeda(tots['pago'])}")
        self._lbl_total.configure(
            text=f"Total período: {formatar_moeda(tots['total'])}")

    def _linha(self, conta: ContaPagar):
        cores = self._cores
        hoje_iso = date.today().isoformat()

        # Cor de fundo da linha
        if conta.status == "pago":
            bg = "#D1FAE5" if obter_configuracao("tema", "claro") == "claro" else "#064E3B"
        elif conta.status == "pendente" and conta.data_vencimento < hoje_iso:
            bg = "#FEE2E2" if obter_configuracao("tema", "claro") == "claro" else "#7F1D1D"
        else:
            bg = cores["card"]

        row_frame = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=6)
        row_frame.pack(fill="x", pady=2)

        valores = [
            (conta.plano_nome or "—",            COLUNAS[0][1]),
            (conta.descricao or "—",             COLUNAS[1][1]),
            (LABEL_TIPO_CUSTO.get(conta.plano_tipo, "—"), COLUNAS[2][1]),
            (formatar_moeda(conta.valor),         COLUNAS[3][1]),
            (formatar_data_exibicao(conta.data_vencimento), COLUNAS[4][1]),
            (conta.status.capitalize(),           COLUNAS[5][1]),
        ]

        for i, (texto, larg) in enumerate(valores):
            ctk.CTkLabel(row_frame, text=texto, width=larg,
                         anchor="w", font=ctk.CTkFont(size=12)).grid(
                row=0, column=i, padx=6, pady=6, sticky="w"
            )

        # Ações
        acoes = ctk.CTkFrame(row_frame, fg_color="transparent")
        acoes.grid(row=0, column=6, padx=4)

        if conta.status == "pendente":
            ctk.CTkButton(
                acoes, text="✓ Pago", width=60, height=24,
                fg_color=cores["positivo"], hover_color="#15803D",
                font=ctk.CTkFont(size=11),
                command=lambda cid=conta.id: self._marcar_pago(cid),
            ).pack(side="left", padx=2)

        ctk.CTkButton(
            acoes, text="✏", width=30, height=24,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"],
            text_color=cores["texto"],
            font=ctk.CTkFont(size=11),
            command=lambda c=conta: self._abrir_form_editar(c),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            acoes, text="🗑", width=30, height=24,
            fg_color="transparent", border_width=1,
            border_color=cores["alerta"],
            text_color=cores["alerta"],
            font=ctk.CTkFont(size=11),
            command=lambda cid=conta.id: self._confirmar_excluir(cid),
        ).pack(side="left", padx=2)

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _exportar_excel(self):
        from tkinter import filedialog as fd
        from config import NOMES_MESES
        mes_nome = NOMES_MESES[self._mes - 1]
        dest = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"contas_pagar_{mes_nome}_{self._ano}.xlsx",
        )
        if not dest:
            return
        try:
            from views.exportar.exportar_model import exportar_contas_pagar_xlsx
            exportar_contas_pagar_xlsx(self._mes, self._ano, dest)
            self._toast("Relatório Excel exportado com sucesso.")
        except Exception as e:
            self._toast(f"Erro ao exportar: {e}", tipo="erro")

    def _marcar_pago(self, id: int):
        marcar_pago(id)
        self._carregar()
        self._toast("Despesa marcada como paga.")

    def _confirmar_excluir(self, id: int):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Confirmar exclusão")
        dlg.geometry("320x140")
        dlg.grab_set()
        dlg.resizable(False, False)
        ctk.CTkLabel(dlg, text="Excluir esta despesa?",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(dlg, text="Esta ação não pode ser desfeita.",
                     text_color=self._cores["texto_mudo"]).pack()
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=16)
        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"],
                      text_color=cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Excluir", width=100,
                      fg_color=self._cores["alerta"],
                      command=lambda: self._excluir(id, dlg)).pack(side="left", padx=8)

    def _excluir(self, id: int, dlg):
        dlg.destroy()
        ok, msg = excluir_conta(id)
        if not ok:
            self._toast(msg, "erro")
            return
        self._carregar()
        self._toast("Despesa excluída.")

    def _abrir_form_novo(self):
        from views.contas_pagar.form_view import ContaPagarFormModal
        ContaPagarFormModal(self, on_salvo=self._on_form_salvo)

    def _abrir_form_editar(self, conta: ContaPagar):
        from views.contas_pagar.form_view import ContaPagarFormModal
        ContaPagarFormModal(self, on_salvo=self._on_form_salvo, conta=conta)

    def _on_form_salvo(self, msg: str = "Despesa salva com sucesso."):
        self._carregar()
        self._toast(msg)

    # ------------------------------------------------------------------
    # Filtros e navegação
    # ------------------------------------------------------------------

    def _on_filtro_status(self, valor: str):
        mapa = {"Todos": None, "Pendente": "pendente", "Pago": "pago", "Cancelado": "cancelado"}
        self._filtro_status = mapa.get(valor)
        self._carregar()

    def _on_filtro_tipo(self, valor: str):
        mapa = {"Todos": None, "Fixo": "fixo", "Variável": "variavel"}
        self._filtro_tipo = mapa.get(valor)
        self._carregar()

    def _mes_anterior(self):
        if self._mes == 1:
            self._mes, self._ano = 12, self._ano - 1
        else:
            self._mes -= 1
        self._carregar()

    def _mes_proximo(self):
        if self._mes == 12:
            self._mes, self._ano = 1, self._ano + 1
        else:
            self._mes += 1
        self._carregar()

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
