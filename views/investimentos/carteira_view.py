"""
carteira_view.py — Tela principal de Investimentos.
Quatro abas: Carteira | Movimentações | Dashboard | Ativos / Contas
"""
from __future__ import annotations

import tkinter as tk
from datetime import date
from typing import Optional

import customtkinter as ctk

from config import (
    get_tema, formatar_moeda, LABEL_TIPO_ATIVO, LABEL_TIPO_MOV_INV,
    CORES_TIPO_ATIVO, NOMES_MESES,
)
from database import obter_configuracao
from views.investimentos.investimento_model import (
    listar_posicoes, resumo_carteira, listar_movimentacoes,
    listar_contas_investimento, listar_ativos,
    alocacao_por_tipo, rendimentos_por_mes, vencimentos_proximos,
    atualizar_valor_atual, excluir_movimentacao,
    excluir_ativo, excluir_conta_investimento,
    alternar_ativa_conta_inv, alternar_ativo_ativo,
)


class InvestimentosView(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Cabeçalho
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        ctk.CTkLabel(
            hdr, text="📈  Investimentos",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self._cores["texto"],
        ).pack(side="left")

        # Tab view
        self._tabs = ctk.CTkTabview(self, fg_color=self._cores["fundo"])
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        for nome in ("Carteira", "Movimentações", "Dashboard", "Ativos / Contas"):
            self._tabs.add(nome)

        self._build_carteira(self._tabs.tab("Carteira"))
        self._build_movimentacoes(self._tabs.tab("Movimentações"))
        self._build_dashboard(self._tabs.tab("Dashboard"))
        self._build_cadastros(self._tabs.tab("Ativos / Contas"))

    # ─────────────────────────────────────────────────────────────────────
    # Helpers visuais comuns
    # ─────────────────────────────────────────────────────────────────────

    def _card_kpi(self, parent, titulo: str, valor: str,
                  cor_valor: Optional[str] = None) -> ctk.CTkFrame:
        cores = self._cores
        card = ctk.CTkFrame(parent, fg_color=cores["card"],
                             corner_radius=10, border_width=1,
                             border_color=cores["borda"])
        ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=11),
                     text_color=cores["texto_mudo"]).pack(pady=(10, 0), padx=14)
        ctk.CTkLabel(card, text=valor,
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=cor_valor or cores["texto"]
                     ).pack(pady=(2, 10), padx=14)
        return card

    def _toast(self, msg: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        t = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(t, text=msg, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        t.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, t.destroy)

    # ─────────────────────────────────────────────────────────────────────
    # Aba 1 — Carteira
    # ─────────────────────────────────────────────────────────────────────

    def _build_carteira(self, parent: ctk.CTkFrame):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # KPIs
        self._kpi_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._kpi_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self._kpi_widgets: list[ctk.CTkFrame] = []

        # Barra de ações
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        ctk.CTkButton(bar, text="+ Nova movimentação", height=32,
                      command=self._abrir_form_mov
                      ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar, text="🔄 Atualizar", height=32, width=100,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["borda"],
                      text_color=self._cores["texto"],
                      command=self._refresh_carteira
                      ).pack(side="left")
        ctk.CTkButton(bar, text="⬇ Excel", height=32, width=80,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["borda"],
                      text_color=self._cores["texto_mudo"],
                      font=ctk.CTkFont(size=12),
                      command=self._exportar_carteira
                      ).pack(side="left", padx=(8, 0))

        # Tabela de posições
        self._frame_tabela_carteira = ctk.CTkFrame(parent, fg_color=self._cores["card"],
                                                    corner_radius=10)
        self._frame_tabela_carteira.grid(row=2, column=0, sticky="nsew",
                                          padx=8, pady=(0, 8))
        parent.grid_rowconfigure(2, weight=1)

        self._refresh_carteira()

    def _refresh_carteira(self):
        # KPIs
        for w in self._kpi_widgets:
            w.destroy()
        self._kpi_widgets.clear()

        r = resumo_carteira()
        kpis = [
            ("Patrimônio atual",   formatar_moeda(r["total_atual"]),   self._cores["primario"]),
            ("Valor investido",    formatar_moeda(r["total_investido"]), None),
            ("L/P não realizado",  formatar_moeda(r["lucro_nao_realizado"]),
             self._cores["positivo"] if r["lucro_nao_realizado"] >= 0 else self._cores["alerta"]),
            ("L/P realizado",      formatar_moeda(r["lucro_realizado"]),
             self._cores["positivo"] if r["lucro_realizado"] >= 0 else self._cores["alerta"]),
            ("Rendimentos recebidos", formatar_moeda(r["rendimentos"]), self._cores["positivo"]),
        ]
        for i, (titulo, valor, cor) in enumerate(kpis):
            card = self._card_kpi(self._kpi_frame, titulo, valor, cor)
            card.grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            self._kpi_frame.grid_columnconfigure(i, weight=1)
            self._kpi_widgets.append(card)

        # Tabela
        for w in self._frame_tabela_carteira.winfo_children():
            w.destroy()

        posicoes = listar_posicoes()
        cols = ["Código", "Nome", "Tipo", "Conta", "Qtd", "C.Médio", "V.Atual",
                "L/P", "Rent.%", ""]
        widths = [80, 150, 60, 110, 70, 90, 95, 90, 65, 90]
        cores = self._cores

        # Cabeçalho
        hdr = ctk.CTkFrame(self._frame_tabela_carteira,
                            fg_color=cores["sidebar"], corner_radius=8)
        hdr.pack(fill="x", padx=6, pady=(6, 2))
        for c, w in zip(cols, widths):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=cores["texto_mudo"]
                         ).pack(side="left", padx=4, pady=4)

        if not posicoes:
            ctk.CTkLabel(
                self._frame_tabela_carteira,
                text="Nenhum ativo com saldo. Lance sua primeira movimentação.",
                text_color=cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(
            self._frame_tabela_carteira, fg_color="transparent",
        )
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        for i, p in enumerate(posicoes):
            bg = cores["fundo"] if i % 2 == 0 else cores["card"]
            row = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=1)

            cor_lp = (cores["positivo"] if p.lucro_nao_realizado >= 0
                      else cores["alerta"])
            tipo_label = LABEL_TIPO_ATIVO.get(p.tipo, p.tipo)
            cor_tipo   = CORES_TIPO_ATIVO.get(p.tipo, cores["texto_mudo"])

            vals = [
                (p.codigo,                       80,  cores["texto"],   "bold"),
                (p.nome[:22],                    150, cores["texto"],   "normal"),
                (tipo_label,                      60,  cor_tipo,         "normal"),
                (p.conta_nome[:14],              110, cores["texto_mudo"], "normal"),
                (f"{p.quantidade_atual:,.2f}" if p.quantidade_atual else "—",
                                                  70,  cores["texto"],   "normal"),
                (formatar_moeda(p.custo_medio) if p.custo_medio else "—",
                                                  90,  cores["texto"],   "normal"),
                (formatar_moeda(p.valor_atual),   95,  cores["primario"], "bold"),
                (formatar_moeda(p.lucro_nao_realizado), 90, cor_lp,      "normal"),
                (f"{p.rentabilidade_pct:+.1f}%", 65,  cor_lp,           "normal"),
            ]
            for txt, w, cor, weight in vals:
                ctk.CTkLabel(row, text=str(txt), width=w, anchor="w",
                             font=ctk.CTkFont(size=11, weight=weight),
                             text_color=cor
                             ).pack(side="left", padx=4, pady=4)

            # Botão atualizar cotação
            ativo_id = p.ativo_id
            ctk.CTkButton(
                row, text="Cotação", width=80, height=24,
                fg_color="transparent", border_width=1,
                border_color=cores["borda"], text_color=cores["texto"],
                font=ctk.CTkFont(size=10),
                command=lambda aid=ativo_id, v=p.valor_atual: self._atualizar_cotacao(aid, v),
            ).pack(side="left", padx=4)

    def _atualizar_cotacao(self, ativo_id: int, valor_atual: float):
        """Diálogo para atualizar cotação manual ou via API."""
        from database import conectar
        from views.investimentos.cotacao_service import CotacaoAPIService

        with conectar() as conn:
            row = conn.execute(
                "SELECT codigo, tipo FROM ativos WHERE id=?", (ativo_id,)
            ).fetchone()
        codigo = row["codigo"] if row else ""
        tipo   = row["tipo"]   if row else "acao"

        cores = self._cores
        dlg = ctk.CTkToplevel(self)
        dlg.title("Atualizar cotação")
        dlg.geometry("360x220")
        dlg.resizable(False, False)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"Cotação — {codigo}",
                     font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(pady=(18, 4))
        ctk.CTkLabel(dlg, text="Valor atual (R$)",
                     font=ctk.CTkFont(size=11), text_color=cores["texto_mudo"]
                     ).pack()
        entry = ctk.CTkEntry(dlg, width=200, justify="center")
        entry.insert(0, f"{valor_atual:.2f}".replace(".", ","))
        entry.pack(pady=4)

        lbl_status = ctk.CTkLabel(dlg, text="", font=ctk.CTkFont(size=10),
                                  text_color=cores["texto_mudo"])
        lbl_status.pack()

        def _buscar_api():
            lbl_status.configure(text="Buscando…", text_color=cores["texto_mudo"])
            dlg.update()
            svc = CotacaoAPIService()
            preco = svc.obter_preco(codigo, tipo)
            if preco is not None:
                entry.delete(0, "end")
                entry.insert(0, f"{preco:.2f}".replace(".", ","))
                lbl_status.configure(text=f"✓ brapi.dev: R$ {preco:.2f}",
                                     text_color=cores["positivo"])
            else:
                lbl_status.configure(text="Cotação não encontrada.",
                                     text_color=cores["alerta"])

        def _ok():
            try:
                v = float(entry.get().replace(".", "").replace(",", "."))
                atualizar_valor_atual(ativo_id, v)
                dlg.destroy()
                self._refresh_carteira()
                self._toast("Cotação atualizada.")
            except ValueError:
                pass

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="🌐 Buscar API", width=110, height=30,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      font=ctk.CTkFont(size=11),
                      command=_buscar_api).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Cancelar", width=90, height=30,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Salvar", width=90, height=30,
                      command=_ok).pack(side="left", padx=4)

    def _exportar_carteira(self):
        import tkinter.filedialog as fd
        from views.exportar.exportar_model import exportar_carteira_xlsx
        from datetime import date
        nome = f"carteira_{date.today().isoformat()}.xlsx"
        caminho = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=nome,
            title="Exportar carteira",
        )
        if caminho:
            exportar_carteira_xlsx(caminho)
            import tkinter.messagebox as mb
            mb.showinfo("Exportado", f"Carteira salva em:\n{caminho}")

    def _exportar_ir_excel(self):
        import tkinter.filedialog as fd
        import tkinter.messagebox as mb
        from datetime import date
        caminho = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"ir_estimado_{date.today().isoformat()}.xlsx",
            title="Exportar IR Estimado",
        )
        if not caminho:
            return
        try:
            from views.exportar.exportar_model import exportar_ir_xlsx
            exportar_ir_xlsx(caminho)
            mb.showinfo("Exportado", f"Relatório de IR salvo em:\n{caminho}")
        except Exception as e:
            mb.showerror("Erro", f"Erro ao exportar: {e}")

    def _abrir_form_mov(self, ativo_id: Optional[int] = None):
        from views.investimentos.form_movimentacao import FormMovimentacaoModal
        FormMovimentacaoModal(self, on_salvo=self._on_mov_salva, ativo_id_default=ativo_id)

    def _on_mov_salva(self):
        self._refresh_carteira()
        self._refresh_movimentacoes()
        self._refresh_dashboard()
        self._toast("Movimentação registrada.")

    # ─────────────────────────────────────────────────────────────────────
    # Aba 2 — Movimentações
    # ─────────────────────────────────────────────────────────────────────

    def _build_movimentacoes(self, parent: ctk.CTkFrame):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Filtros
        filtros = ctk.CTkFrame(parent, fg_color="transparent")
        filtros.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        ctk.CTkLabel(filtros, text="Conta:", font=ctk.CTkFont(size=11),
                     text_color=self._cores["texto_mudo"]).pack(side="left", padx=(0, 4))
        contas = ["Todas"] + [c.nome for c in listar_contas_investimento(apenas_ativas=True)]
        self._filt_conta = ctk.CTkComboBox(filtros, values=contas, width=150,
                                            state="readonly",
                                            command=lambda _: self._refresh_movimentacoes())
        self._filt_conta.set("Todas")
        self._filt_conta.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(filtros, text="Tipo:", font=ctk.CTkFont(size=11),
                     text_color=self._cores["texto_mudo"]).pack(side="left", padx=(0, 4))
        tipos = ["Todos"] + [LABEL_TIPO_MOV_INV[t] for t in LABEL_TIPO_MOV_INV]
        self._filt_tipo = ctk.CTkComboBox(filtros, values=tipos, width=160,
                                           state="readonly",
                                           command=lambda _: self._refresh_movimentacoes())
        self._filt_tipo.set("Todos")
        self._filt_tipo.pack(side="left", padx=(0, 12))

        ctk.CTkButton(filtros, text="+ Lançar", height=30,
                      command=self._abrir_form_mov
                      ).pack(side="right", padx=4)

        # Tabela
        self._frame_tabela_mov = ctk.CTkFrame(parent, fg_color=self._cores["card"],
                                               corner_radius=10)
        self._frame_tabela_mov.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self._refresh_movimentacoes()

    def _refresh_movimentacoes(self):
        for w in self._frame_tabela_mov.winfo_children():
            w.destroy()

        conta_nome = self._filt_conta.get() if hasattr(self, "_filt_conta") else "Todas"
        tipo_label = self._filt_tipo.get()  if hasattr(self, "_filt_tipo")  else "Todos"

        contas = listar_contas_investimento(apenas_ativas=True)
        conta  = next((c for c in contas if c.nome == conta_nome), None)
        tipo   = next((k for k, v in LABEL_TIPO_MOV_INV.items() if v == tipo_label), None)

        movs = listar_movimentacoes(
            conta_id=conta.id if conta else None,
            tipo=tipo,
        )

        cores = self._cores
        cols   = ["Data", "Ativo", "Conta", "Tipo", "Qtd", "Preço", "Valor liq.", "Fin.", ""]
        widths = [88, 90, 110, 110, 70, 90, 100, 35, 65]

        hdr = ctk.CTkFrame(self._frame_tabela_mov,
                            fg_color=cores["sidebar"], corner_radius=8)
        hdr.pack(fill="x", padx=6, pady=(6, 2))
        for c, w in zip(cols, widths):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=cores["texto_mudo"]
                         ).pack(side="left", padx=4, pady=4)

        if not movs:
            ctk.CTkLabel(self._frame_tabela_mov,
                         text="Nenhuma movimentação encontrada.",
                         text_color=cores["texto_mudo"],
                         font=ctk.CTkFont(size=13)).pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(self._frame_tabela_mov, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        from config import formatar_data_exibicao
        for i, m in enumerate(movs):
            bg = cores["fundo"] if i % 2 == 0 else cores["card"]
            row = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=1)

            tipo_label_m = LABEL_TIPO_MOV_INV.get(m.tipo, m.tipo)
            fin_icon = "✓" if m.registrar_no_financeiro else "—"

            vals = [
                (formatar_data_exibicao(m.data), 88),
                (m.ativo_codigo,                 90),
                (m.conta_nome[:14],             110),
                (tipo_label_m,                  110),
                (f"{m.quantidade:.2f}" if m.quantidade else "—", 70),
                (formatar_moeda(m.preco_unitario) if m.preco_unitario else "—", 90),
                (formatar_moeda(m.valor_liquido), 100),
                (fin_icon,                        35),
            ]
            for txt, w in vals:
                ctk.CTkLabel(row, text=str(txt), width=w, anchor="w",
                             font=ctk.CTkFont(size=11),
                             text_color=cores["texto"]
                             ).pack(side="left", padx=4, pady=4)

            mov_id = m.id
            ctk.CTkButton(
                row, text="Excluir", width=60, height=24,
                fg_color="transparent", border_width=1,
                border_color=cores["alerta"], text_color=cores["alerta"],
                font=ctk.CTkFont(size=10),
                command=lambda mid=mov_id: self._excluir_mov(mid),
            ).pack(side="left", padx=4)

    def _excluir_mov(self, mov_id: int):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Confirmar exclusão")
        dlg.geometry("340x160")
        dlg.resizable(False, False)
        dlg.grab_set()
        cores = self._cores
        ctk.CTkLabel(dlg, text="Excluir esta movimentação?",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 6))
        ctk.CTkLabel(dlg, text="O lançamento financeiro vinculado também será removido.",
                     text_color=cores["texto_mudo"]).pack()
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=6)

        def _ok():
            excluir_movimentacao(mov_id)
            dlg.destroy()
            self._refresh_carteira()
            self._refresh_movimentacoes()
            self._refresh_dashboard()
            self._toast("Movimentação excluída.")

        ctk.CTkButton(btns, text="Excluir", width=100,
                      fg_color=cores["alerta"],
                      command=_ok).pack(side="left", padx=6)

    # ─────────────────────────────────────────────────────────────────────
    # Aba 3 — Dashboard
    # ─────────────────────────────────────────────────────────────────────

    def _build_dashboard(self, parent: ctk.CTkFrame):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        self._dash_parent = parent
        self._refresh_dashboard()

    def _refresh_dashboard(self):
        parent = self._dash_parent
        for w in parent.winfo_children():
            w.destroy()

        cores = self._cores
        r = resumo_carteira()

        # KPIs
        kpi_row = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_row.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        for i, (titulo, valor, cor) in enumerate([
            ("Patrimônio atual",  formatar_moeda(r["total_atual"]),   cores["primario"]),
            ("Rendimentos",       formatar_moeda(r["rendimentos"]),   cores["positivo"]),
            ("L/P realizado",     formatar_moeda(r["lucro_realizado"]),
             cores["positivo"] if r["lucro_realizado"] >= 0 else cores["alerta"]),
            ("Rentabilidade",     f"{r['rentabilidade_pct']:+.1f}%",
             cores["positivo"] if r["rentabilidade_pct"] >= 0 else cores["alerta"]),
        ]):
            c = self._card_kpi(kpi_row, titulo, valor, cor)
            c.grid(row=0, column=i, padx=4, sticky="ew")
            kpi_row.grid_columnconfigure(i, weight=1)

        # Corpo principal
        body = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        # Alocação por tipo
        card_aloc = ctk.CTkFrame(body, fg_color=cores["card"], corner_radius=10)
        card_aloc.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        ctk.CTkLabel(card_aloc, text="Alocação por classe",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]
                     ).pack(anchor="w", padx=14, pady=(12, 4))
        self._draw_alocacao(card_aloc)

        # Rendimentos mensais
        card_rend = ctk.CTkFrame(body, fg_color=cores["card"], corner_radius=10)
        card_rend.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        ctk.CTkLabel(card_rend, text=f"Rendimentos {date.today().year}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]
                     ).pack(anchor="w", padx=14, pady=(12, 4))
        self._draw_rendimentos(card_rend)

        # Vencimentos futuros
        card_venc = ctk.CTkFrame(body, fg_color=cores["card"], corner_radius=10)
        card_venc.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 4))
        ctk.CTkLabel(card_venc, text="Vencimentos nos próximos 12 meses",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]
                     ).pack(anchor="w", padx=14, pady=(12, 4))
        self._draw_vencimentos(card_venc)

        # IR estimado
        card_ir = ctk.CTkFrame(body, fg_color=cores["card"], corner_radius=10)
        card_ir.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 4))
        ir_hdr = ctk.CTkFrame(card_ir, fg_color="transparent")
        ir_hdr.pack(fill="x", padx=14, pady=(12, 4))
        ir_hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(ir_hdr, text="IR Estimado (lucros realizados)",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(ir_hdr, text="⬇ Excel", width=75, height=26,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      font=ctk.CTkFont(size=11),
                      command=self._exportar_ir_excel,
                      ).grid(row=0, column=1, sticky="e")
        self._draw_ir(card_ir)

    def _draw_alocacao(self, parent: ctk.CTkFrame):
        cores = self._cores
        aloc  = alocacao_por_tipo()

        if not aloc:
            ctk.CTkLabel(parent, text="Sem posições.",
                         text_color=cores["texto_mudo"]).pack(pady=20)
            return

        # ── Barra horizontal segmentada ───────────────────────────────
        canvas = tk.Canvas(parent, height=58, bg=cores["card"],
                           bd=0, highlightthickness=0)
        canvas.pack(fill="x", padx=14, pady=(0, 6))
        parent.update_idletasks()
        canvas.update_idletasks()
        w = canvas.winfo_width() or 340
        bar_h, bar_y = 28, 14
        x = 0
        for tipo, pct in aloc.items():
            seg_w = int(w * pct / 100)
            if seg_w < 1:
                continue
            cor = CORES_TIPO_ATIVO.get(tipo, "#6B7280")
            canvas.create_rectangle(x, bar_y, x + seg_w, bar_y + bar_h,
                                    fill=cor, outline="")
            if seg_w > 30:
                canvas.create_text(x + seg_w // 2, bar_y + bar_h // 2,
                                   text=f"{pct:.0f}%",
                                   fill="#FFFFFF", font=("Arial", 9, "bold"))
            x += seg_w

        # ── Legenda em grade de 2 colunas (widgets CTk) ───────────────
        leg = ctk.CTkFrame(parent, fg_color="transparent")
        leg.pack(fill="x", padx=14, pady=(0, 10))
        col = row = 0
        for tipo, pct in aloc.items():
            cor   = CORES_TIPO_ATIVO.get(tipo, "#6B7280")
            label = LABEL_TIPO_ATIVO.get(tipo, tipo)

            cell = ctk.CTkFrame(leg, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="w", padx=(0, 20), pady=2)

            sq = ctk.CTkFrame(cell, width=12, height=12,
                              fg_color=cor, corner_radius=2)
            sq.pack(side="left", padx=(0, 5))
            sq.pack_propagate(False)

            ctk.CTkLabel(cell, text=f"{label}  {pct:.1f}%",
                         font=ctk.CTkFont(size=11),
                         text_color=cores["texto"]).pack(side="left")

            col += 1
            if col >= 2:
                col = 0
                row += 1

    def _draw_rendimentos(self, parent: ctk.CTkFrame):
        cores = self._cores
        rend  = rendimentos_por_mes(date.today().year)
        h     = 180

        if not rend:
            ctk.CTkLabel(parent, text="Sem rendimentos neste ano.",
                         text_color=cores["texto_mudo"]).pack(pady=20)
            return

        canvas = tk.Canvas(parent, height=h, bg=cores["card"],
                           bd=0, highlightthickness=0)
        canvas.pack(fill="x", padx=14, pady=(0, 8))
        canvas.update_idletasks()
        w     = canvas.winfo_width() or 340
        max_v = max(rend.values()) if rend else 1
        n     = 12
        pad   = 10
        bar_w = max(4, (w - 2 * pad) // n - 4)
        bar_area_h = h - 36

        for mes in range(1, 13):
            val = rend.get(mes, 0.0)
            bh  = int(bar_area_h * val / max_v) if max_v > 0 else 0
            x0  = pad + (mes - 1) * ((w - 2 * pad) // n)
            x1  = x0 + bar_w
            y0  = h - 22 - bh
            y1  = h - 22
            cor = cores["positivo"] if val > 0 else cores["borda"]
            canvas.create_rectangle(x0, y0, x1, y1, fill=cor, outline="")
            canvas.create_text(x0 + bar_w // 2, h - 12,
                               text=NOMES_MESES[mes - 1][:3],
                               fill=cores["texto_mudo"], font=("Arial", 8))
            if val > 0:
                canvas.create_text(x0 + bar_w // 2, y0 - 8,
                                   text=f"{val:.0f}",
                                   fill=cores["texto"], font=("Arial", 8))

    def _draw_vencimentos(self, parent: ctk.CTkFrame):
        cores = self._cores
        items = vencimentos_proximos(12)
        if not items:
            ctk.CTkLabel(parent, text="Nenhum vencimento nos próximos 12 meses.",
                         text_color=cores["texto_mudo"]).pack(pady=10, padx=14, anchor="w")
            return

        from config import formatar_data_exibicao, LABEL_INDEXADOR, LABEL_TIPO_ATIVO
        cols   = ["Vencimento", "Código", "Nome", "Tipo", "Indexador", "Valor estimado"]
        widths = [100, 90, 160, 70, 80, 110]

        hdr = ctk.CTkFrame(parent, fg_color=cores["sidebar"], corner_radius=6)
        hdr.pack(fill="x", padx=14, pady=(0, 4))
        for c, w in zip(cols, widths):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="w",
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=cores["texto_mudo"]
                         ).pack(side="left", padx=4, pady=4)

        for i, item in enumerate(items):
            bg  = cores["fundo"] if i % 2 == 0 else cores["card"]
            row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=4)
            row.pack(fill="x", padx=14, pady=1)
            vals = [
                formatar_data_exibicao(item["vencimento"]),
                item["codigo"],
                item["nome"][:20],
                LABEL_TIPO_ATIVO.get(item["tipo"], item["tipo"]),
                LABEL_INDEXADOR.get(item["indexador"] or "", "—"),
                formatar_moeda(item["valor_estimado"]),
            ]
            for txt, w in zip(vals, widths):
                ctk.CTkLabel(row, text=str(txt), width=w, anchor="w",
                             font=ctk.CTkFont(size=11),
                             text_color=cores["texto"]
                             ).pack(side="left", padx=4, pady=3)

    def _draw_ir(self, parent: ctk.CTkFrame):
        from views.investimentos.ir_model import resumo_ir_carteira
        from config import formatar_moeda
        cores = self._cores
        res = resumo_ir_carteira()

        if not res["detalhes"]:
            ctk.CTkLabel(parent, text="Nenhum lucro realizado registrado.",
                         text_color=cores["texto_mudo"]).pack(pady=10, padx=14, anchor="w")
            return

        # Totais
        tot = ctk.CTkFrame(parent, fg_color="transparent")
        tot.pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkLabel(tot,
                     text=f"Lucro total: {formatar_moeda(res['total_lucro'])}   "
                          f"IR estimado: {formatar_moeda(res['total_ir'])}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=cores["alerta"] if res["total_ir"] > 0 else cores["texto"],
                     ).pack(side="left")

        # Detalhe por ativo
        cols = ["Código", "Tipo", "Lucro Real.", "Alíquota", "IR Est."]
        widths = [80, 70, 110, 80, 110]
        hdr = ctk.CTkFrame(parent, fg_color=cores["sidebar"], corner_radius=6)
        hdr.pack(fill="x", padx=14, pady=(0, 2))
        for c, w in zip(cols, widths):
            ctk.CTkLabel(hdr, text=c, width=w, anchor="w",
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=cores["texto_mudo"]
                         ).pack(side="left", padx=4, pady=3)

        for i, d in enumerate(res["detalhes"]):
            bg  = cores["fundo"] if i % 2 == 0 else cores["card"]
            row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=4)
            row.pack(fill="x", padx=14, pady=1)
            for txt, w in zip([
                d["codigo"], d["tipo"],
                formatar_moeda(d["lucro"]),
                f"{d['aliquota']*100:.1f}%",
                formatar_moeda(d["ir"]),
            ], widths):
                ctk.CTkLabel(row, text=str(txt), width=w, anchor="w",
                             font=ctk.CTkFont(size=11),
                             text_color=cores["texto"]
                             ).pack(side="left", padx=4, pady=3)

        ctk.CTkLabel(parent,
                     text="⚠ Estimativa simplificada. Consulte um contador para a declaração oficial.",
                     font=ctk.CTkFont(size=9), text_color=cores["texto_mudo"]
                     ).pack(anchor="w", padx=14, pady=(4, 8))

    # ─────────────────────────────────────────────────────────────────────
    # Aba 4 — Ativos / Contas
    # ─────────────────────────────────────────────────────────────────────

    def _build_cadastros(self, parent: ctk.CTkFrame):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self._frame_contas_cad = ctk.CTkFrame(parent, fg_color=self._cores["card"],
                                               corner_radius=10)
        self._frame_contas_cad.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)

        self._frame_ativos_cad = ctk.CTkFrame(parent, fg_color=self._cores["card"],
                                               corner_radius=10)
        self._frame_ativos_cad.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)

        self._refresh_cadastros()

    def _refresh_cadastros(self):
        self._render_lista_contas()
        self._render_lista_ativos()

    def _render_lista_contas(self):
        cores = self._cores
        frame = self._frame_contas_cad
        for w in frame.winfo_children():
            w.destroy()

        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(hdr, text="🏦  Contas de Investimento",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]).pack(side="left")
        ctk.CTkButton(hdr, text="+ Novo", width=60, height=26,
                      command=self._nova_conta_inv).pack(side="right")

        contas = listar_contas_investimento()
        if not contas:
            ctk.CTkLabel(frame, text="Nenhuma conta cadastrada.",
                         text_color=cores["texto_mudo"]).pack(pady=20)
            return

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        from config import LABEL_TIPO_CONTA_INV
        for i, c in enumerate(contas):
            bg  = cores["fundo"] if i % 2 == 0 else cores["card"]
            row = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, text=c.nome, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto"], width=130
                         ).pack(side="left", padx=8, pady=6)
            ctk.CTkLabel(row, text=c.instituicao, anchor="w",
                         font=ctk.CTkFont(size=11),
                         text_color=cores["texto_mudo"], width=110
                         ).pack(side="left")
            ctk.CTkLabel(row, text=LABEL_TIPO_CONTA_INV.get(c.tipo, c.tipo),
                         anchor="w", font=ctk.CTkFont(size=10),
                         text_color=cores["texto_mudo"], width=80
                         ).pack(side="left")

            cid = c.id
            ctk.CTkButton(
                row, text="Editar", width=55, height=24,
                fg_color="transparent", border_width=1,
                border_color=cores["borda"], text_color=cores["texto"],
                font=ctk.CTkFont(size=10),
                command=lambda cc=c: self._editar_conta_inv(cc),
            ).pack(side="right", padx=4)
            ctk.CTkButton(
                row, text="Excluir", width=55, height=24,
                fg_color="transparent", border_width=1,
                border_color=cores["alerta"], text_color=cores["alerta"],
                font=ctk.CTkFont(size=10),
                command=lambda cid=cid: self._excluir_conta_inv(cid),
            ).pack(side="right", padx=(0, 4))

    def _render_lista_ativos(self):
        cores = self._cores
        frame = self._frame_ativos_cad
        for w in frame.winfo_children():
            w.destroy()

        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(hdr, text="📊  Ativos",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]).pack(side="left")
        ctk.CTkButton(hdr, text="+ Novo", width=60, height=26,
                      command=self._novo_ativo).pack(side="right")

        ativos = listar_ativos()
        if not ativos:
            ctk.CTkLabel(frame, text="Nenhum ativo cadastrado.",
                         text_color=cores["texto_mudo"]).pack(pady=20)
            return

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        for i, a in enumerate(ativos):
            bg  = cores["fundo"] if i % 2 == 0 else cores["card"]
            row = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=1)

            cor_tipo = CORES_TIPO_ATIVO.get(a.tipo, cores["texto_mudo"])
            ctk.CTkLabel(row, text=a.codigo, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cor_tipo, width=80
                         ).pack(side="left", padx=8, pady=6)
            ctk.CTkLabel(row, text=a.nome[:20], anchor="w",
                         font=ctk.CTkFont(size=11),
                         text_color=cores["texto"], width=140
                         ).pack(side="left")
            tipo_lbl = LABEL_TIPO_ATIVO.get(a.tipo, a.tipo)
            ctk.CTkLabel(row, text=tipo_lbl, anchor="w",
                         font=ctk.CTkFont(size=10),
                         text_color=cores["texto_mudo"], width=70
                         ).pack(side="left")

            aid = a.id
            ctk.CTkButton(
                row, text="Editar", width=50, height=24,
                fg_color="transparent", border_width=1,
                border_color=cores["borda"], text_color=cores["texto"],
                font=ctk.CTkFont(size=10),
                command=lambda aa=a: self._editar_ativo(aa),
            ).pack(side="right", padx=4)
            ctk.CTkButton(
                row, text="Excluir", width=50, height=24,
                fg_color="transparent", border_width=1,
                border_color=cores["alerta"], text_color=cores["alerta"],
                font=ctk.CTkFont(size=10),
                command=lambda aid=aid: self._excluir_ativo_ui(aid),
            ).pack(side="right", padx=(0, 4))

    # ── Ações CRUD Contas ─────────────────────────────────────────────────

    def _nova_conta_inv(self):
        from views.investimentos.form_conta_inv import FormContaInvModal
        FormContaInvModal(self, on_salvo=self._on_cadastro_salvo)

    def _editar_conta_inv(self, conta):
        from views.investimentos.form_conta_inv import FormContaInvModal
        FormContaInvModal(self, on_salvo=self._on_cadastro_salvo, conta=conta)

    def _excluir_conta_inv(self, id: int):
        ok, msg = excluir_conta_investimento(id)
        if not ok:
            self._toast(msg, tipo="erro")
        else:
            self._render_lista_contas()
            self._toast("Conta excluída.")

    # ── Ações CRUD Ativos ─────────────────────────────────────────────────

    def _novo_ativo(self):
        from views.investimentos.form_ativo import FormAtivoModal
        FormAtivoModal(self, on_salvo=self._on_cadastro_salvo)

    def _editar_ativo(self, ativo):
        from views.investimentos.form_ativo import FormAtivoModal
        FormAtivoModal(self, on_salvo=self._on_cadastro_salvo, ativo=ativo)

    def _excluir_ativo_ui(self, id: int):
        ok, msg = excluir_ativo(id)
        if not ok:
            self._toast(msg, tipo="erro")
        else:
            self._render_lista_ativos()
            self._toast("Ativo excluído.")

    def _on_cadastro_salvo(self):
        self._refresh_cadastros()
        self._toast("Salvo com sucesso.")
