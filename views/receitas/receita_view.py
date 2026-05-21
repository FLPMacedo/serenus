"""
receita_view.py — Módulo 2: Minhas Receitas.
Três abas: Fontes de Renda | Receitas Especiais | Visão Mensal.
"""

from __future__ import annotations
import customtkinter as ctk
from datetime import date
from config import (
    get_tema, formatar_moeda, mascara_moeda, LABEL_TIPO_RECEITA, NOMES_MESES,
)
from database import obter_configuracao
from views.receitas.receita_model import (
    FonteReceita, ReceitaEspecial,
    listar_fontes, salvar_fonte, alternar_ativa_fonte,
    listar_receitas_especiais, salvar_receita_especial, excluir_receita_especial,
    total_previsto_mes, _gerar_especiais_clt,
)


# ============================================================================
# View principal (ponto de entrada da sidebar)
# ============================================================================

class ReceitasView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="💰  Minhas Receitas",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=self._cores["texto"]).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="⬇ Excel", width=80, height=30,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["borda"],
                      text_color=self._cores["texto"],
                      command=self._exportar_excel).grid(row=0, column=1, sticky="e")

        from views.widgets.ajuda import banner_ajuda
        _b = banner_ajuda(
            self, self._cores,
            "Cadastre suas fontes de renda recorrentes (salário, aluguel, etc.) "
            "e receitas pontuais como 13º e férias. A aba 'Visão Mensal' soma "
            "tudo do mês, incluindo vendas já realizadas.",
        )
        if _b:
            _b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=2, column=0, sticky="nsew", padx=16, pady=8)
        tabs.add("Fontes de Renda")
        tabs.add("Receitas Especiais")
        tabs.add("Visão Mensal")

        self._tab_fontes   = _FontesTab(tabs.tab("Fontes de Renda"),   self._cores)
        self._tab_especiais = _EspeciaisTab(tabs.tab("Receitas Especiais"), self._cores)
        self._tab_mensal   = _MensalTab(tabs.tab("Visão Mensal"),       self._cores)

    def _exportar_excel(self):
        from tkinter import filedialog as fd
        import tkinter.messagebox as mb
        dest = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="receitas.xlsx",
        )
        if not dest:
            return
        try:
            from views.exportar.exportar_model import exportar_receitas_xlsx
            exportar_receitas_xlsx(dest)
            mb.showinfo("Exportação", "Relatório de receitas exportado com sucesso.")
        except Exception as e:
            mb.showerror("Erro", f"Erro ao exportar: {e}")


# ============================================================================
# Aba 1 — Fontes de Renda
# ============================================================================

class _FontesTab(ctk.CTkFrame):
    def __init__(self, parent, cores):
        super().__init__(parent, fg_color="transparent")
        self._cores = cores
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Barra superior
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        bar.grid_columnconfigure(0, weight=1)

        self._mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(bar, text="Mostrar inativas",
                        variable=self._mostrar_inativas,
                        command=self._carregar).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(bar, text="+ Nova fonte", height=30,
                      command=self._novo).grid(row=0, column=1, sticky="e")

        # Cabeçalho da tabela
        cab = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        cab.grid(row=1, column=0, sticky="ew", padx=8, pady=(6, 0))
        for i, (txt, w) in enumerate([("Nome",200),("Tipo",130),("Valor/mês",100),("Status",70),("Ações",130)]):
            ctk.CTkLabel(cab, text=txt, width=w, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(row=0, column=i, padx=6, pady=6, sticky="w")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(2, 8))
        self.grid_rowconfigure(2, weight=1)

        self._carregar()

    def _carregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        fontes = listar_fontes(apenas_ativas=not self._mostrar_inativas.get())
        if not fontes:
            ctk.CTkLabel(self._scroll, text="Nenhuma fonte cadastrada.",
                         text_color=self._cores["texto_mudo"]).pack(pady=20)
            return
        for f in fontes:
            self._linha(f)

    def _linha(self, f: FonteReceita):
        cores = self._cores
        bg    = cores["card"] if f.ativa else cores["fundo"]
        alfa  = cores["texto"] if f.ativa else cores["texto_mudo"]

        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=6)
        row.pack(fill="x", pady=2)

        # Valor efetivo por mês considerando periodicidade
        val_mes = f.valor_mensal
        if f.periodicidade == "bimestral":
            val_mes /= 2
        elif f.periodicidade == "anual":
            val_mes /= 12

        dados = [
            (f.nome,                              200),
            (LABEL_TIPO_RECEITA.get(f.tipo, "—"), 130),
            (formatar_moeda(val_mes),             100),
        ]
        for i, (txt, w) in enumerate(dados):
            ctk.CTkLabel(row, text=txt, width=w, anchor="w",
                         text_color=alfa,
                         font=ctk.CTkFont(size=12)).grid(row=0, column=i, padx=6, pady=6, sticky="w")

        # Badge de status
        badge_frame = ctk.CTkFrame(row, fg_color="transparent", width=70)
        badge_frame.grid(row=0, column=3, padx=6, pady=4, sticky="w")
        badge_frame.grid_propagate(False)
        if f.ativa:
            badge = ctk.CTkLabel(badge_frame, text="Ativa",
                                 fg_color=cores["positivo"], text_color="#FFFFFF",
                                 corner_radius=4, font=ctk.CTkFont(size=10, weight="bold"),
                                 width=50, height=20)
        else:
            badge = ctk.CTkLabel(badge_frame, text="Inativa",
                                 fg_color=cores["texto_mudo"], text_color="#FFFFFF",
                                 corner_radius=4, font=ctk.CTkFont(size=10, weight="bold"),
                                 width=50, height=20)
        badge.pack(pady=2)

        acoes = ctk.CTkFrame(row, fg_color="transparent")
        acoes.grid(row=0, column=4, padx=4)

        if not f.padrao:
            ctk.CTkButton(acoes, text="✏", width=30, height=24,
                          fg_color="transparent", border_width=1,
                          border_color=cores["borda"], text_color=cores["texto"],
                          command=lambda ff=f: self._editar(ff)).pack(side="left", padx=2)

        lbl = "Desativar" if f.ativa else "Ativar"
        cor = cores["atencao"] if f.ativa else cores["positivo"]
        ctk.CTkButton(acoes, text=lbl, width=70, height=24,
                      fg_color="transparent", border_width=1,
                      border_color=cor, text_color=cor,
                      command=lambda ff=f: self._toggle(ff)).pack(side="left", padx=2)

    def _toggle(self, f: FonteReceita):
        alternar_ativa_fonte(f.id, not f.ativa)
        self._carregar()
        self._toast(f"Fonte \"{'Desativada' if f.ativa else 'Ativada'}\".")

    def _novo(self):
        FonteFormModal(self, on_salvo=lambda: (self._carregar(), self._toast("Fonte salva.")))

    def _editar(self, f: FonteReceita):
        FonteFormModal(self, fonte=f,
                       on_salvo=lambda: (self._carregar(), self._toast("Fonte atualizada.")))

    def _toast(self, msg: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        t = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(t, text=msg, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        t.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, t.destroy)


# ============================================================================
# Aba 2 — Receitas Especiais
# ============================================================================

class _EspeciaisTab(ctk.CTkFrame):
    def __init__(self, parent, cores):
        super().__init__(parent, fg_color="transparent")
        self._cores = cores
        self._mes_filtro: int | None = None
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Barra superior
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        bar.grid_columnconfigure(0, weight=1)

        # Filtro por mês
        frame_filtro = ctk.CTkFrame(bar, fg_color="transparent")
        frame_filtro.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(frame_filtro, text="Filtrar mês:").pack(side="left", padx=(0, 6))
        meses_opcoes = ["Todos"] + NOMES_MESES
        self._combo_mes = ctk.CTkComboBox(frame_filtro, values=meses_opcoes,
                                          width=130, state="readonly",
                                          command=self._on_filtro_mes)
        self._combo_mes.set("Todos")
        self._combo_mes.pack(side="left")

        ctk.CTkButton(bar, text="+ Nova receita especial", height=30,
                      command=self._nova).grid(row=0, column=1, sticky="e")

        # Cabeçalho
        cab = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        cab.grid(row=1, column=0, sticky="ew", padx=8, pady=(6, 0))
        for i, (txt, w) in enumerate([("Nome",200),("Mês",110),("Valor",100),("Tipo",120),("Recorrente",90),("Ações",80)]):
            ctk.CTkLabel(cab, text=txt, width=w, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(row=0, column=i, padx=6, pady=6, sticky="w")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(2, 8))
        self.grid_rowconfigure(2, weight=1)

        self._carregar()

    def _on_filtro_mes(self, valor: str):
        if valor == "Todos":
            self._mes_filtro = None
        else:
            self._mes_filtro = NOMES_MESES.index(valor)
        self._carregar()

    def _carregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        especiais = listar_receitas_especiais(mes=self._mes_filtro)
        if not especiais:
            ctk.CTkLabel(self._scroll, text="Nenhuma receita especial cadastrada.",
                         text_color=self._cores["texto_mudo"]).pack(pady=20)
            return
        for e in especiais:
            self._linha(e)

    def _linha(self, e: ReceitaEspecial):
        cores = self._cores
        row = ctk.CTkFrame(self._scroll, fg_color=cores["card"], corner_radius=6)
        row.pack(fill="x", pady=2)

        dados = [
            (e.nome,                     200),
            (NOMES_MESES[e.mes] if 0 <= e.mes <= 11 else "—", 110),
            (formatar_moeda(e.valor),    100),
            (e.tipo.upper(),             120),
            ("Sim" if e.recorrente_anual else "Não", 90),
        ]
        for i, (txt, w) in enumerate(dados):
            ctk.CTkLabel(row, text=txt, width=w, anchor="w",
                         font=ctk.CTkFont(size=12)).grid(row=0, column=i, padx=6, pady=6, sticky="w")

        acoes = ctk.CTkFrame(row, fg_color="transparent")
        acoes.grid(row=0, column=5, padx=4)

        ctk.CTkButton(acoes, text="✏", width=30, height=24,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=lambda ee=e: self._editar(ee)).pack(side="left", padx=2)
        ctk.CTkButton(acoes, text="🗑", width=30, height=24,
                      fg_color="transparent", border_width=1,
                      border_color=cores["alerta"], text_color=cores["alerta"],
                      command=lambda ee=e: self._excluir(ee)).pack(side="left", padx=2)

    def _nova(self):
        EspecialFormModal(self, on_salvo=lambda: (self._carregar(),
                                                   self._toast("Receita especial salva.")))

    def _editar(self, e: ReceitaEspecial):
        EspecialFormModal(self, especial=e,
                          on_salvo=lambda: (self._carregar(),
                                            self._toast("Receita especial atualizada.")))

    def _excluir(self, e: ReceitaEspecial):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Confirmar exclusão")
        dlg.geometry("300x130")
        dlg.grab_set()
        dlg.resizable(False, False)
        ctk.CTkLabel(dlg, text=f"Excluir \"{e.nome}\"?",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(dlg, text="Esta ação não pode ser desfeita.",
                     text_color=self._cores["texto_mudo"]).pack()
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"],
                      text_color=cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Excluir", width=100,
                      fg_color=self._cores["alerta"],
                      command=lambda: self._conf_excluir(e.id, dlg)).pack(side="left", padx=6)

    def _conf_excluir(self, id: int, dlg):
        dlg.destroy()
        excluir_receita_especial(id)
        self._carregar()
        self._toast("Receita especial excluída.")

    def _toast(self, msg: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        t = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(t, text=msg, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        t.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, t.destroy)


# ============================================================================
# Aba 3 — Visão Mensal
# ============================================================================

class _MensalTab(ctk.CTkFrame):
    def __init__(self, parent, cores):
        super().__init__(parent, fg_color="transparent")
        self._cores = cores
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hoje = date.today()
        self._mes_0 = hoje.month - 1   # 0–11
        self._ano   = hoje.year

        self._build_nav()
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))
        self._carregar()

    def _build_nav(self):
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        nav.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(nav, text="◀", width=30, height=28,
                      command=self._mes_ant).grid(row=0, column=0, padx=2)
        self._lbl_mes = ctk.CTkLabel(nav, text="",
                                     font=ctk.CTkFont(size=14, weight="bold"))
        self._lbl_mes.grid(row=0, column=1)
        ctk.CTkButton(nav, text="▶", width=30, height=28,
                      command=self._mes_prox).grid(row=0, column=2, padx=2)

    def _mes_ant(self):
        if self._mes_0 == 0:
            self._mes_0, self._ano = 11, self._ano - 1
        else:
            self._mes_0 -= 1
        self._carregar()

    def _mes_prox(self):
        if self._mes_0 == 11:
            self._mes_0, self._ano = 0, self._ano + 1
        else:
            self._mes_0 += 1
        self._carregar()

    def _carregar(self):
        cores = self._cores
        self._lbl_mes.configure(
            text=f"{NOMES_MESES[self._mes_0]} / {self._ano}"
        )
        for w in self._scroll.winfo_children():
            w.destroy()

        dados = total_previsto_mes(self._mes_0, self._ano)

        # --- Vendas e Serviços realizados no mês ---
        total_vendas, vendas_itens = self._carregar_vendas_mes()

        # --- Card total ---
        card_total = ctk.CTkFrame(self._scroll, fg_color=cores["primario"], corner_radius=10)
        card_total.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(card_total, text="Total do mês",
                     text_color="#FFFFFF", font=ctk.CTkFont(size=12)).pack(pady=(10, 2))
        ctk.CTkLabel(card_total,
                     text=formatar_moeda(dados["total"] + total_vendas),
                     text_color="#FFFFFF",
                     font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(0, 10))

        # Sub-cards
        sub = ctk.CTkFrame(self._scroll, fg_color="transparent")
        sub.pack(fill="x", pady=(0, 16))
        n_cols = 3 if total_vendas > 0 else 2
        sub.grid_columnconfigure(tuple(range(n_cols)), weight=1)

        self._mini_card(sub, "Fontes recorrentes",
                        formatar_moeda(dados["total_fontes"]), 0)
        self._mini_card(sub, f"Receitas especiais ({len(dados['especiais'])})",
                        formatar_moeda(dados["total_especiais"]), 1)
        if total_vendas > 0:
            self._mini_card(sub, "Vendas e Serviços",
                            formatar_moeda(total_vendas), 2)

        # --- Fontes ---
        if dados["fontes"]:
            ctk.CTkLabel(self._scroll, text="Fontes de renda",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         anchor="w").pack(fill="x", pady=(0, 4))
            for item in dados["fontes"]:
                f: FonteReceita = item["fonte"]
                self._linha_receita(
                    nome=f.nome,
                    subtipo=LABEL_TIPO_RECEITA.get(f.tipo, ""),
                    valor=item["valor_mes"],
                    destaque=False,
                )

        # --- Especiais ---
        if dados["especiais"]:
            ctk.CTkLabel(self._scroll, text="Receitas especiais do mês",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=cores["primario"],
                         anchor="w").pack(fill="x", pady=(12, 4))
            for e in dados["especiais"]:
                self._linha_receita(
                    nome=e.nome,
                    subtipo="Especial — " + NOMES_MESES[e.mes],
                    valor=e.valor,
                    destaque=True,
                )

        # --- Vendas e Serviços ---
        if total_vendas > 0:
            ctk.CTkLabel(self._scroll, text="Vendas e Serviços realizados",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=cores["positivo"],
                         anchor="w").pack(fill="x", pady=(12, 4))
            for item in vendas_itens:
                self._linha_receita(
                    nome=item["descricao"],
                    subtipo=item["subtipo"],
                    valor=item["valor"],
                    destaque=False,
                )

        if not dados["fontes"] and not dados["especiais"] and total_vendas == 0:
            ctk.CTkLabel(self._scroll,
                         text="Nenhuma receita cadastrada para este mês.",
                         text_color=cores["texto_mudo"]).pack(pady=24)

    def _carregar_vendas_mes(self) -> tuple[float, list[dict]]:
        """Retorna (total, lista de itens) de vendas realizadas no mês selecionado."""
        mes_num = self._mes_0 + 1
        inicio  = f"{self._ano:04d}-{mes_num:02d}-01"
        fim     = (f"{self._ano:04d}-{mes_num+1:02d}-01"
                   if mes_num < 12 else f"{self._ano+1:04d}-01-01")
        try:
            from database import conectar
            with conectar() as conn:
                avista_rows = conn.execute("""
                    SELECT COALESCE(descricao, 'Venda') AS desc, valor_liquido AS valor
                    FROM vendas
                    WHERE tipo_pagamento='avista' AND status='paga'
                      AND data_venda >= ? AND data_venda < ?
                    ORDER BY data_venda
                """, (inicio, fim)).fetchall()
                aprazo_rows = conn.execute("""
                    SELECT descricao,
                           numero_parcela, total_parcelas,
                           data_recebimento, valor
                    FROM contas_a_receber
                    WHERE status='recebido'
                      AND data_recebimento >= ? AND data_recebimento < ?
                    ORDER BY data_recebimento
                """, (inicio, fim)).fetchall()
        except Exception:
            return 0.0, []

        itens: list[dict] = []
        total = 0.0

        for r in avista_rows:
            itens.append({
                "descricao": r["desc"],
                "subtipo":   "À vista",
                "valor":     float(r["valor"]),
            })
            total += float(r["valor"])

        for r in aprazo_rows:
            parc = (f"Parcela {r['numero_parcela']}/{r['total_parcelas']}"
                    if r["total_parcelas"] > 1 else "À vista")
            itens.append({
                "descricao": r["descricao"],
                "subtipo":   f"{parc} · Recebido em {r['data_recebimento']}",
                "valor":     float(r["valor"]),
            })
            total += float(r["valor"])

        return total, itens

    def _mini_card(self, parent, titulo: str, valor: str, col: int):
        cores = self._cores
        card = ctk.CTkFrame(parent, fg_color=cores["card"], corner_radius=8)
        card.grid(row=0, column=col, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(card, text=titulo, text_color=cores["texto_mudo"],
                     font=ctk.CTkFont(size=11)).pack(pady=(8, 2))
        ctk.CTkLabel(card, text=valor,
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 8))

    def _linha_receita(self, nome: str, subtipo: str, valor: float, destaque: bool):
        cores = self._cores
        bg = cores["card"]
        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=6)
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(0, weight=1)

        frame_txt = ctk.CTkFrame(row, fg_color="transparent")
        frame_txt.grid(row=0, column=0, sticky="w", padx=10, pady=6)

        cor_nome = cores["primario"] if destaque else cores["texto"]
        ctk.CTkLabel(frame_txt, text=nome, anchor="w",
                     text_color=cor_nome,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        if subtipo:
            ctk.CTkLabel(frame_txt, text=subtipo, anchor="w",
                         text_color=cores["texto_mudo"],
                         font=ctk.CTkFont(size=11)).pack(anchor="w")

        if destaque:
            badge = ctk.CTkLabel(row, text="ESPECIAL",
                                 fg_color=cores["primario"],
                                 text_color="#FFFFFF",
                                 corner_radius=4,
                                 font=ctk.CTkFont(size=10, weight="bold"),
                                 width=60)
            badge.grid(row=0, column=1, padx=8)

        ctk.CTkLabel(row, text=formatar_moeda(valor),
                     text_color=cores["positivo"],
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=2, padx=12)


# ============================================================================
# Modal — Formulário de Fonte de Receita
# ============================================================================

class FonteFormModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, fonte: FonteReceita | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._fonte    = fonte
        self._cores    = get_tema(obter_configuracao("tema", "claro"))

        titulo = "Editar Fonte" if fonte else "Nova Fonte de Renda"
        self.title(f"Serenus — {titulo}")
        self.geometry("500x620")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._tipo_var = ctk.StringVar(
            value=fonte.tipo if fonte else "clt"
        )
        self._build_ui()
        if fonte:
            self._preencher(fonte)
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll_frame.pack(fill="both", expand=True, padx=20, pady=16)
        fr = self._scroll_frame

        self._lbl(fr, "Nome *")
        self._entry_nome = ctk.CTkEntry(fr, placeholder_text="Ex: Salário CLT")
        self._entry_nome.pack(fill="x", pady=(2, 2))
        self._lbl_err_nome = ctk.CTkLabel(fr, text="", text_color="#DC2626",
                                          font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_nome.pack(anchor="w", pady=(0, 8))

        self._lbl(fr, "Tipo de renda *")
        tipos = list(LABEL_TIPO_RECEITA.keys())
        labels_tipo = list(LABEL_TIPO_RECEITA.values())
        self._combo_tipo = ctk.CTkComboBox(
            fr, values=labels_tipo, state="readonly",
            command=self._on_tipo_mudou,
        )
        self._combo_tipo.set(LABEL_TIPO_RECEITA.get(self._tipo_var.get(), labels_tipo[0]))
        self._combo_tipo.pack(fill="x", pady=(2, 12))

        self._lbl(fr, "Valor *")
        self._entry_valor = ctk.CTkEntry(fr)
        self._entry_valor.insert(0, "0,00")
        self._entry_valor.pack(fill="x", pady=(2, 2))
        self._entry_valor.bind("<KeyRelease>", lambda e: mascara_moeda(self._entry_valor))
        self._lbl_err_valor = ctk.CTkLabel(fr, text="", text_color="#DC2626",
                                           font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_valor.pack(anchor="w", pady=(0, 8))

        # Campos dinâmicos por tipo (criados/destruídos conforme seleção)
        self._frame_dinamico = ctk.CTkFrame(fr, fg_color="transparent")
        self._frame_dinamico.pack(fill="x")

        self._lbl(fr, "Observação")
        self._entry_obs = ctk.CTkEntry(fr, placeholder_text="Opcional")
        self._entry_obs.pack(fill="x", pady=(2, 16))

        # Botões
        btns = ctk.CTkFrame(fr, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancelar", width=110,
                      fg_color="transparent", border_width=1,
                      text_color=self._cores["texto"],
                      border_color=self._cores["borda"],
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Salvar", width=110,
                      command=self._salvar).pack(side="right")

        self._on_tipo_mudou(self._combo_tipo.get())

    def _lbl(self, parent, txt: str):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _on_tipo_mudou(self, label: str):
        # Descobre o valor interno (chave) do tipo selecionado
        inv = {v: k for k, v in LABEL_TIPO_RECEITA.items()}
        tipo = inv.get(label, "outro")
        self._tipo_var.set(tipo)

        for w in self._frame_dinamico.winfo_children():
            w.destroy()

        fd = self._frame_dinamico

        if tipo == "clt":
            self._lbl(fd, "Dia do pagamento")
            self._entry_dia = ctk.CTkEntry(fd, placeholder_text="Ex: 5", width=100)
            self._entry_dia.pack(anchor="w", pady=(2, 10))

            self._fgts_var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(fd, text="Recebe FGTS aniversário?",
                            variable=self._fgts_var,
                            command=self._toggle_fgts).pack(anchor="w", pady=(0, 6))

            self._frame_fgts = ctk.CTkFrame(fd, fg_color="transparent")
            self._lbl(self._frame_fgts, "Mês do FGTS")
            self._combo_fgts_mes = ctk.CTkComboBox(
                self._frame_fgts, values=NOMES_MESES, state="readonly", width=160
            )
            self._combo_fgts_mes.set(NOMES_MESES[0])
            self._combo_fgts_mes.pack(anchor="w", pady=(2, 8))
            self._lbl(self._frame_fgts, "Valor estimado FGTS (R$)")
            self._entry_fgts_val = ctk.CTkEntry(self._frame_fgts, width=160)
            self._entry_fgts_val.insert(0, "0,00")
            self._entry_fgts_val.pack(anchor="w", pady=(2, 8))
            self._entry_fgts_val.bind("<KeyRelease>", lambda e: mascara_moeda(self._entry_fgts_val))

        elif tipo in ("aluguel",):
            self._lbl(fd, "Dia do recebimento")
            self._entry_dia = ctk.CTkEntry(fd, placeholder_text="Ex: 10", width=100)
            self._entry_dia.pack(anchor="w", pady=(2, 10))

        elif tipo == "dividendos":
            self._lbl(fd, "Origem (FIIs, ações, CDB, etc.)")
            self._entry_origem = ctk.CTkEntry(fd, placeholder_text="Ex: FIIs + CDB")
            self._entry_origem.pack(fill="x", pady=(2, 10))

        elif tipo == "outro":
            self._lbl(fd, "Periodicidade")
            self._combo_periodo = ctk.CTkComboBox(
                fd, values=["mensal", "bimestral", "anual"],
                state="readonly", width=160
            )
            self._combo_periodo.set("mensal")
            self._combo_periodo.pack(anchor="w", pady=(2, 10))

    def _toggle_fgts(self):
        if self._fgts_var.get():
            self._frame_fgts.pack(fill="x", pady=(0, 8))
        else:
            self._frame_fgts.pack_forget()

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _preencher(self, f: FonteReceita):
        self._entry_nome.insert(0, f.nome)
        self._combo_tipo.set(LABEL_TIPO_RECEITA.get(f.tipo, f.tipo))
        self._on_tipo_mudou(self._combo_tipo.get())
        self._entry_valor.insert(0, f"{f.valor_mensal:.2f}".replace(".", ","))
        self._entry_obs.insert(0, f.observacao or "")

        if f.tipo == "clt":
            if f.dia_pagamento:
                self._entry_dia.insert(0, str(f.dia_pagamento))
            if f.fgts_aniversario:
                self._fgts_var.set(True)
                self._toggle_fgts()
                if f.fgts_mes is not None:
                    self._combo_fgts_mes.set(NOMES_MESES[f.fgts_mes])
                if f.fgts_valor:
                    self._entry_fgts_val.insert(0, f"{f.fgts_valor:.2f}".replace(".", ","))
        elif f.tipo == "aluguel":
            if f.dia_pagamento:
                self._entry_dia.insert(0, str(f.dia_pagamento))
        elif f.tipo == "dividendos":
            if hasattr(self, "_entry_origem"):
                self._entry_origem.insert(0, f.origem or "")
        elif f.tipo == "outro":
            if hasattr(self, "_combo_periodo"):
                self._combo_periodo.set(f.periodicidade or "mensal")

    def _salvar(self):
        borda = self._cores["borda"]
        self._entry_nome.configure(border_color=borda)
        self._entry_valor.configure(border_color=borda)
        self._lbl_err_nome.configure(text="")
        self._lbl_err_valor.configure(text="")

        nome = self._entry_nome.get().strip()
        if not nome:
            self._entry_nome.configure(border_color="#DC2626")
            self._lbl_err_nome.configure(text="Nome é obrigatório.")
            return

        val_str = self._entry_valor.get().replace(".", "").replace(",", ".").strip()
        try:
            valor = float(val_str)
            if valor <= 0:
                raise ValueError
        except ValueError:
            self._entry_valor.configure(border_color="#DC2626")
            self._lbl_err_valor.configure(text="Informe um valor maior que zero.")
            return

        tipo = self._tipo_var.get()
        dados: dict = {
            "nome":        nome,
            "tipo":        tipo,
            "valor_mensal": valor,
            "observacao":  self._entry_obs.get().strip(),
        }

        if tipo == "clt":
            dia_str = getattr(self, "_entry_dia", None)
            dados["dia_pagamento"] = int(dia_str.get()) if dia_str and dia_str.get().isdigit() else None
            dados["fgts_aniversario"] = getattr(self, "_fgts_var", ctk.BooleanVar()).get()
            if dados["fgts_aniversario"]:
                mes_nome = self._combo_fgts_mes.get()
                dados["fgts_mes"]   = NOMES_MESES.index(mes_nome)
                fgts_val = self._entry_fgts_val.get().replace(".", "").replace(",", ".")
                try:
                    dados["fgts_valor"] = float(fgts_val)
                except ValueError:
                    dados["fgts_valor"] = None

        elif tipo == "aluguel":
            dia_str = getattr(self, "_entry_dia", None)
            dados["dia_pagamento"] = int(dia_str.get()) if dia_str and dia_str.get().isdigit() else None

        elif tipo == "dividendos":
            if hasattr(self, "_entry_origem"):
                dados["origem"] = self._entry_origem.get().strip()

        elif tipo == "outro":
            if hasattr(self, "_combo_periodo"):
                dados["periodicidade"] = self._combo_periodo.get()

        fonte_id = self._fonte.id if self._fonte else None
        novo_id = salvar_fonte(dados, id=fonte_id)

        # Gera receitas especiais automaticamente para CLT novo
        if tipo == "clt" and not self._fonte:
            _gerar_especiais_clt(
                fonte_id      = novo_id,
                nome_fonte    = nome,
                salario       = valor,
                fgts          = dados.get("fgts_aniversario", False),
                fgts_mes      = dados.get("fgts_mes"),
                fgts_valor    = dados.get("fgts_valor"),
            )

        self.destroy()
        self._on_salvo()


# ============================================================================
# Modal — Receita Especial
# ============================================================================

class EspecialFormModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, especial: ReceitaEspecial | None = None):
        super().__init__(parent)
        self._on_salvo  = on_salvo
        self._especial  = especial
        self._cores     = get_tema(obter_configuracao("tema", "claro"))

        titulo = "Editar Receita Especial" if especial else "Nova Receita Especial"
        self.title(f"Serenus — {titulo}")
        self.geometry("420x360")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self._build_ui()
        if especial:
            self._preencher(especial)
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _lbl(self, txt):
        ctk.CTkLabel(self._fr, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _build_ui(self):
        self._fr = ctk.CTkFrame(self, fg_color="transparent")
        self._fr.pack(fill="both", expand=True, padx=24, pady=16)

        self._lbl("Nome *")
        self._entry_nome = ctk.CTkEntry(self._fr, placeholder_text="Ex: 13º Salário")
        self._entry_nome.pack(fill="x", pady=(2, 2))
        self._lbl_err_nome = ctk.CTkLabel(self._fr, text="", text_color="#DC2626",
                                          font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_nome.pack(anchor="w", pady=(0, 8))

        self._lbl("Mês *")
        self._combo_mes = ctk.CTkComboBox(self._fr, values=NOMES_MESES,
                                          state="readonly")
        self._combo_mes.set(NOMES_MESES[0])
        self._combo_mes.pack(fill="x", pady=(2, 12))

        self._lbl("Valor (R$) *")
        self._entry_valor = ctk.CTkEntry(self._fr)
        self._entry_valor.insert(0, "0,00")
        self._entry_valor.pack(fill="x", pady=(2, 2))
        self._entry_valor.bind("<KeyRelease>", lambda e: mascara_moeda(self._entry_valor))
        self._lbl_err_valor = ctk.CTkLabel(self._fr, text="", text_color="#DC2626",
                                           font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_valor.pack(anchor="w", pady=(0, 8))

        self._lbl("Tipo")
        self._combo_tipo = ctk.CTkComboBox(
            self._fr, values=["clt", "bonus", "extra", "outro"], state="readonly"
        )
        self._combo_tipo.set("clt")
        self._combo_tipo.pack(fill="x", pady=(2, 12))

        self._recorrente_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self._fr, text="Recorrente anualmente",
                        variable=self._recorrente_var).pack(anchor="w", pady=(0, 16))

        btns = ctk.CTkFrame(self._fr, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancelar", width=110,
                      fg_color="transparent", border_width=1,
                      text_color=self._cores["texto"],
                      border_color=self._cores["borda"],
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Salvar", width=110,
                      command=self._salvar).pack(side="right")

    def _preencher(self, e: ReceitaEspecial):
        self._entry_nome.insert(0, e.nome)
        self._combo_mes.set(NOMES_MESES[e.mes])
        self._entry_valor.insert(0, f"{e.valor:.2f}".replace(".", ","))
        self._combo_tipo.set(e.tipo)
        self._recorrente_var.set(e.recorrente_anual)

    def _salvar(self):
        borda = self._cores["borda"]
        self._entry_nome.configure(border_color=borda)
        self._entry_valor.configure(border_color=borda)
        self._lbl_err_nome.configure(text="")
        self._lbl_err_valor.configure(text="")

        nome = self._entry_nome.get().strip()
        if not nome:
            self._entry_nome.configure(border_color="#DC2626")
            self._lbl_err_nome.configure(text="Nome é obrigatório.")
            return

        val_str = self._entry_valor.get().replace(".", "").replace(",", ".").strip()
        try:
            valor = float(val_str)
            if valor <= 0:
                raise ValueError
        except ValueError:
            self._entry_valor.configure(border_color="#DC2626")
            self._lbl_err_valor.configure(text="Informe um valor maior que zero.")
            return

        dados = {
            "nome":             nome,
            "mes":              NOMES_MESES.index(self._combo_mes.get()),
            "valor":            valor,
            "tipo":             self._combo_tipo.get(),
            "recorrente_anual": self._recorrente_var.get(),
        }

        salvar_receita_especial(dados, id=self._especial.id if self._especial else None)
        self.destroy()
        self._on_salvo()
