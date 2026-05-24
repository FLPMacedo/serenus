"""
conciliacao_view.py — Aba 'Conciliação Bancária' dentro do Fluxo de Caixa.

Permite cadastrar contas bancárias, importar extratos (CSV/OFX/PDF), revisar
e categorizar cada lançamento, e marcar como conciliado quando confirmado.

Layout:
  - Toolbar: seletor de conta + botões (+ Conta, ⬆ Importar, ⚙ Regras)
  - Cards de resumo da conta selecionada (saldo atual, entradas, saídas, % conciliado)
  - Navegação de mês (◀ Mês ▶ Hoje)
  - Tabela de lançamentos filtrável (status conciliado, busca)
  - Cada linha: data, descrição, categoria, valor, checkbox conciliado
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk
import tkinter.messagebox as mb

from config import get_tema, formatar_moeda, NOMES_MESES
from database import obter_configuracao
from views.fluxo_caixa.conta_banco_model import (
    listar_contas, obter_conta, saldo_atual_conta,
)
from views.fluxo_caixa.extrato_banco_model import (
    listar_lancamentos_mes, marcar_conciliado, resumo_conta,
    categorizar, obter_lancamento, excluir_lancamento, reaplicar_regras,
    vincular_conta_pagar, candidatas_para_vincular,
)


_COLS = [
    ("Data",       80),
    ("Descrição",  340),
    ("Categoria",  170),
    ("Valor",      110),
    ("✓",          30),
]


class ConciliacaoView(ctk.CTkFrame):
    """Aba de conciliação bancária."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        hoje = date.today()
        self._mes = hoje.month
        self._ano = hoje.year
        self._conta_id: int | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_toolbar()
        self._build_cards()
        self._build_filtros()
        self._build_tabela()
        self._recarregar()

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self):
        cores = self._cores
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        bar.grid_columnconfigure(1, weight=1)

        # Seletor de conta
        ctk.CTkLabel(
            bar, text="Conta:", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=0, padx=(2, 6))

        self._combo_conta = ctk.CTkComboBox(
            bar, values=["(carregando…)"], state="readonly",
            width=240, command=lambda v: self._on_conta_mudou(),
        )
        self._combo_conta.grid(row=0, column=1, sticky="w")

        # Botões à direita
        botoes = ctk.CTkFrame(bar, fg_color="transparent")
        botoes.grid(row=0, column=2, sticky="e")

        ctk.CTkButton(
            botoes, text="+ Conta", width=90, height=30,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._nova_conta,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            botoes, text="✏ Editar", width=80, height=30,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._editar_conta,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            botoes, text="⬆ Importar", width=100, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._importar_extrato,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            botoes, text="⚙ Regras", width=90, height=30,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._gerenciar_regras,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            botoes, text="↻ Re-aplicar", width=110, height=30,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._reaplicar_regras,
        ).pack(side="left", padx=2)

    # ------------------------------------------------------------------
    # Cards de resumo
    # ------------------------------------------------------------------

    def _build_cards(self):
        self._cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._cards_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(10, 0))
        self._cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def _update_cards(self):
        for w in self._cards_frame.winfo_children():
            w.destroy()
        cores = self._cores

        if not self._conta_id:
            ctk.CTkLabel(
                self._cards_frame,
                text="Selecione ou cadastre uma conta bancária pra começar.",
                text_color=cores["texto_mudo"],
                font=ctk.CTkFont(size=12),
            ).pack(pady=16)
            return

        saldo = saldo_atual_conta(self._conta_id)
        r = resumo_conta(self._conta_id)
        pct_conc = (100 * r["conciliados"] / r["total"]) if r["total"] else 0
        cor_saldo = cores["positivo"] if saldo >= 0 else cores["alerta"]

        items = [
            ("💰  Saldo Atual",    formatar_moeda(saldo),               cor_saldo),
            ("⬆ Entradas",        formatar_moeda(r["entradas"]),       cores["positivo"]),
            ("⬇ Saídas",          formatar_moeda(r["saidas"]),         cores["alerta"]),
            ("✓ Conciliados",     f"{r['conciliados']}/{r['total']}  ({pct_conc:.0f}%)",
                                  cores["primario"]),
        ]
        for col, (titulo, valor, cor) in enumerate(items):
            card = ctk.CTkFrame(self._cards_frame, fg_color=cores["card"],
                                corner_radius=10)
            card.grid(row=0, column=col, padx=4, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=titulo, text_color=cores["texto_mudo"],
                         font=ctk.CTkFont(size=11)).pack(pady=(8, 2))
            ctk.CTkLabel(card, text=valor, text_color=cor,
                         font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(0, 8))

    # ------------------------------------------------------------------
    # Filtros e navegação de mês
    # ------------------------------------------------------------------

    def _build_filtros(self):
        cores = self._cores
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", padx=8, pady=(10, 0))
        bar.grid_columnconfigure(2, weight=1)

        # Navegação de mês
        ctk.CTkButton(
            bar, text="◀", width=30, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._mes_anterior,
        ).grid(row=0, column=0, padx=2)

        self._lbl_mes = ctk.CTkLabel(
            bar, text="", width=140,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"],
        )
        self._lbl_mes.grid(row=0, column=1)

        ctk.CTkButton(
            bar, text="▶", width=30, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._mes_proximo,
        ).grid(row=0, column=2, sticky="w", padx=2)

        # Filtros à direita
        filtros = ctk.CTkFrame(bar, fg_color="transparent")
        filtros.grid(row=0, column=3, sticky="e")

        self._entry_busca = ctk.CTkEntry(
            filtros, placeholder_text="🔍  Buscar…",
            width=180, height=28,
        )
        self._entry_busca.pack(side="left", padx=(0, 8))
        self._entry_busca.bind("<KeyRelease>", lambda e: self._aplicar_filtro())

        self._var_filtro = ctk.StringVar(value="todos")
        for label, val in [
            ("Todos", "todos"),
            ("Pendentes", "pendentes"),
            ("Conciliados", "conciliados"),
        ]:
            ctk.CTkRadioButton(
                filtros, text=label, variable=self._var_filtro, value=val,
                font=ctk.CTkFont(size=11),
                command=self._aplicar_filtro,
            ).pack(side="left", padx=2)

    # ------------------------------------------------------------------
    # Tabela
    # ------------------------------------------------------------------

    def _build_tabela(self):
        cores = self._cores

        # Cabeçalho
        cab = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        cab.grid(row=3, column=0, sticky="new", padx=8, pady=(8, 0))
        for i, (nome, larg) in enumerate(_COLS):
            if i < 3:
                anchor = "w"
                sticky = "w"
            elif i == 4:
                anchor = "center"
                sticky = ""
            else:
                anchor = "e"
                sticky = "e"
            ctk.CTkLabel(
                cab, text=nome, width=larg, anchor=anchor,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=cores["texto_mudo"],
            ).grid(row=0, column=i, padx=4, pady=6, sticky=sticky)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=4, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.grid_rowconfigure(4, weight=1)

    # ------------------------------------------------------------------
    # Carregamento de dados
    # ------------------------------------------------------------------

    def _recarregar(self):
        # Atualiza lista de contas
        contas = listar_contas(apenas_ativas=True)
        if contas:
            self._combo_conta.configure(values=[c.nome for c in contas])
            # Mantém seleção atual se ainda existe
            atual = self._combo_conta.get()
            existe = next((c for c in contas if c.nome == atual), None)
            if existe is None:
                self._combo_conta.set(contas[0].nome)
                self._conta_id = contas[0].id
            else:
                self._conta_id = existe.id
        else:
            self._combo_conta.configure(values=["(nenhuma conta cadastrada)"])
            self._combo_conta.set("(nenhuma conta cadastrada)")
            self._conta_id = None

        self._lbl_mes.configure(
            text=f"{NOMES_MESES[self._mes - 1]} {self._ano}"
        )

        self._update_cards()

        if self._conta_id:
            self._lancamentos = listar_lancamentos_mes(
                self._mes, self._ano, self._conta_id
            )
        else:
            self._lancamentos = []
        self._aplicar_filtro()

    def _aplicar_filtro(self):
        texto = (self._entry_busca.get() if hasattr(self, "_entry_busca") else "").lower()
        modo = self._var_filtro.get() if hasattr(self, "_var_filtro") else "todos"

        for w in self._scroll.winfo_children():
            w.destroy()

        if not self._conta_id:
            ctk.CTkLabel(
                self._scroll,
                text="Cadastre uma conta bancária pra começar a importar extratos.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
            ).pack(pady=32)
            return

        linhas = self._lancamentos
        if modo == "pendentes":
            linhas = [l for l in linhas if not l.conciliado]
        elif modo == "conciliados":
            linhas = [l for l in linhas if l.conciliado]
        if texto:
            linhas = [
                l for l in linhas
                if texto in l.descricao.lower()
                or texto in l.nome_categoria.lower()
            ]

        if not linhas:
            ctk.CTkLabel(
                self._scroll,
                text="Nenhum lançamento neste mês.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
            ).pack(pady=32)
            return

        for i, lanc in enumerate(linhas):
            self._linha(lanc, i)

    def _linha(self, lanc, idx: int):
        cores = self._cores

        # Cor de fundo
        if lanc.conciliado:
            bg = "#F0FDF4"      # verde muito claro
        elif lanc.valor > 0:
            bg = "#EFF6FF"      # azul muito claro (entrada)
        else:
            bg = cores["card"] if idx % 2 == 0 else cores["fundo"]

        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
        row.pack(fill="x", pady=1)

        # Duplo-clique abre modal de categorização
        row.bind("<Double-Button-1>",
                 lambda e, lid=lanc.id: self._categorizar_lancamento(lid))

        # Data DD/MM
        partes = lanc.data.split("-")
        data_fmt = f"{partes[2]}/{partes[1]}" if len(partes) == 3 else lanc.data

        # Categoria: nome ou "(sem categoria)"
        cat_txt = lanc.nome_categoria or "(sem categoria)"
        cor_cat = cores["texto"] if lanc.nome_categoria else cores["texto_mudo"]

        # Valor: colorido por sinal
        valor_txt = formatar_moeda(abs(lanc.valor))
        cor_val = cores["positivo"] if lanc.valor > 0 else cores["alerta"]
        sinal = "+" if lanc.valor > 0 else "-"

        # Prefixo 🔗 se vinculado com conta_pagar
        desc_prefix = "🔗 " if lanc.conta_pagar_id else ""

        cells = [
            (data_fmt, 0, "w", cores["texto_mudo"], False),
            (desc_prefix + lanc.descricao, 1, "w", cores["texto"], False),
            (cat_txt, 2, "w", cor_cat, False),
            (f"{sinal} {valor_txt}", 3, "e", cor_val, True),
        ]

        for texto, col_i, anchor, cor, bold in cells:
            _, larg = _COLS[col_i]
            cell = ctk.CTkLabel(
                row, text=texto, width=larg, anchor=anchor,
                font=ctk.CTkFont(size=11, weight="bold" if bold else "normal"),
                text_color=cor,
            )
            cell.grid(row=0, column=col_i, padx=4, pady=5, sticky=anchor)
            cell.bind("<Double-Button-1>",
                      lambda e, lid=lanc.id: self._categorizar_lancamento(lid))

        # Checkbox conciliado
        var = ctk.BooleanVar(value=lanc.conciliado)
        chk = ctk.CTkCheckBox(
            row, text="", variable=var, width=24,
            command=lambda lid=lanc.id, v=var: self._toggle_conciliado(lid, v.get()),
        )
        chk.grid(row=0, column=4, padx=4, pady=5)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _on_conta_mudou(self):
        nome = self._combo_conta.get()
        contas = listar_contas(apenas_ativas=True)
        cand = next((c for c in contas if c.nome == nome), None)
        self._conta_id = cand.id if cand else None
        self._recarregar()

    def _mes_anterior(self):
        if self._mes == 1:
            self._mes = 12; self._ano -= 1
        else:
            self._mes -= 1
        self._recarregar()

    def _mes_proximo(self):
        if self._mes == 12:
            self._mes = 1; self._ano += 1
        else:
            self._mes += 1
        self._recarregar()

    def _nova_conta(self):
        from views.fluxo_caixa.form_conta_banco import FormContaBancoModal
        FormContaBancoModal(self, on_salvo=lambda msg: self._recarregar())

    def _editar_conta(self):
        if not self._conta_id:
            mb.showinfo("Sem conta", "Selecione uma conta primeiro.")
            return
        c = obter_conta(self._conta_id)
        if not c:
            return
        from views.fluxo_caixa.form_conta_banco import FormContaBancoModal
        FormContaBancoModal(self, on_salvo=lambda msg: self._recarregar(), conta=c)

    def _importar_extrato(self):
        if not listar_contas(apenas_ativas=True):
            mb.showinfo("Sem conta", "Cadastre uma conta bancária primeiro.")
            return
        from views.fluxo_caixa.form_importar_extrato import FormImportarExtratoModal
        FormImportarExtratoModal(
            self, on_importado=self._on_extrato_importado,
            conta_inicial_id=self._conta_id,
        )

    def _on_extrato_importado(self, msg: str):
        self._recarregar()
        mb.showinfo("Importação concluída", msg)

    def _gerenciar_regras(self):
        from views.fluxo_caixa.form_regras_categoria import FormRegrasCategoriaModal
        FormRegrasCategoriaModal(self, on_fechado=lambda: self._recarregar())

    def _reaplicar_regras(self):
        """Aplica regras ativas aos lançamentos JÁ importados.

        Pergunta ao user se quer sobrescrever categorias manuais ou só
        preencher os sem categoria. Por padrão preserva manuais.
        """
        if not self._conta_id:
            mb.showinfo("Sem conta", "Selecione uma conta primeiro.")
            return

        sobrescrever = mb.askyesno(
            "Re-aplicar regras",
            "Re-aplicar regras de categorização nos lançamentos já importados?\n\n"
            "SIM = sobrescreve categorias manuais (CUIDADO).\n"
            "NÃO = preserva manuais, só preenche os sem categoria (recomendado).",
        )
        n = reaplicar_regras(
            self._conta_id, apenas_sem_categoria=not sobrescrever,
        )
        mb.showinfo("Concluído", f"{n} lançamento(s) categorizado(s).")
        self._recarregar()

    def _toggle_conciliado(self, lanc_id: int, conciliado: bool):
        marcar_conciliado(lanc_id, conciliado)
        # Atualiza apenas o resumo (não recarrega tudo pra preservar scroll)
        self._update_cards()
        # Atualiza o objeto na lista em memória
        for l in self._lancamentos:
            if l.id == lanc_id:
                l.conciliado = conciliado
                break

    def _categorizar_lancamento(self, lanc_id: int):
        """Modal simples pra escolher categoria do lançamento."""
        lanc = obter_lancamento(lanc_id)
        if not lanc:
            return

        from views.contas_pagar.conta_model import listar_plano_contas
        from views.receitas.receita_model import listar_fontes

        # Mini diálogo (CTkToplevel inline)
        dlg = ctk.CTkToplevel(self)
        dlg.title("Categorizar Lançamento")
        dlg.geometry("460x420")
        dlg.grab_set()
        dlg.bind("<Escape>", lambda e: dlg.destroy())

        cores = self._cores
        ctk.CTkLabel(
            dlg, text=lanc.descricao[:60], anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=cores["texto"],
        ).pack(pady=(12, 4), padx=16, anchor="w")

        sinal = "+" if lanc.valor > 0 else "-"
        ctk.CTkLabel(
            dlg, text=f"{sinal} {formatar_moeda(abs(lanc.valor))}   |   "
                      f"{lanc.data.replace('-','/')}",
            text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 12), padx=16, anchor="w")

        if lanc.valor > 0:
            tipo = "entrada"
            opcoes = listar_fontes(apenas_ativas=True)
        else:
            tipo = "saida"
            opcoes = listar_plano_contas(apenas_ativas=True)

        ctk.CTkLabel(
            dlg, text="Categoria:", anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=cores["texto_mudo"],
        ).pack(padx=16, anchor="w")
        nomes = [o.nome for o in opcoes] or ["(cadastre uma categoria primeiro)"]
        combo = ctk.CTkComboBox(dlg, values=nomes, state="readonly", width=420)
        atual = lanc.nome_categoria
        if atual and atual in nomes:
            combo.set(atual)
        else:
            combo.set(nomes[0])
        combo.pack(padx=16, pady=(2, 14))

        # Vínculo com conta_pagar (só pra saídas)
        combo_cp = None
        candidatas: list = []
        if lanc.valor < 0:
            ctk.CTkLabel(
                dlg, text="Vincular com conta a pagar:", anchor="w",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=cores["texto_mudo"],
            ).pack(padx=16, anchor="w")
            candidatas = candidatas_para_vincular(lanc.data, lanc.valor)
            opcoes_cp = ["(nenhum)"] + [
                f"#{c.id} - {c.data_vencimento} - {formatar_moeda(c.valor)}"
                f" - {c.descricao[:30] or c.nome_categoria}"
                for c in candidatas
            ]
            combo_cp = ctk.CTkComboBox(
                dlg, values=opcoes_cp, state="readonly", width=420,
            )
            # Pré-seleciona vínculo existente
            sel_inicial = "(nenhum)"
            for i, c in enumerate(candidatas):
                if c.id == lanc.conta_pagar_id:
                    sel_inicial = opcoes_cp[i + 1]
                    break
            combo_cp.set(sel_inicial)
            combo_cp.pack(padx=16, pady=(2, 4))
            ctk.CTkLabel(
                dlg, text=(
                    f"{len(candidatas)} candidato(s) com valor R$ "
                    f"{formatar_moeda(abs(lanc.valor))} em até ±5 dias"
                ),
                font=ctk.CTkFont(size=9),
                text_color=cores["texto_mudo"],
            ).pack(padx=16, anchor="w", pady=(0, 12))

        botoes = ctk.CTkFrame(dlg, fg_color="transparent")
        botoes.pack(fill="x", padx=16, pady=(16, 12))

        def aplicar():
            sel = combo.get()
            if sel.startswith("("):
                mb.showerror("Indisponível", sel)
                return
            cand = next((o for o in opcoes if o.nome == sel), None)
            if not cand:
                return
            if tipo == "entrada":
                categorizar(lanc_id, fonte_receita_id=cand.id)
            else:
                categorizar(lanc_id, plano_conta_id=cand.id)

            # Salva (ou remove) vínculo com conta_pagar
            if combo_cp is not None:
                sel_cp = combo_cp.get()
                if sel_cp == "(nenhum)":
                    vincular_conta_pagar(lanc_id, None)
                else:
                    # Formato "#42 - 2026-05-10 - ..."
                    try:
                        cp_id = int(sel_cp.split(" - ")[0].lstrip("#"))
                        vincular_conta_pagar(lanc_id, cp_id)
                    except (ValueError, IndexError):
                        pass

            dlg.destroy()
            self._recarregar()

        def remover():
            categorizar(lanc_id, plano_conta_id=None, fonte_receita_id=None)
            dlg.destroy()
            self._recarregar()

        def excluir():
            if not mb.askyesno(
                "Excluir lançamento",
                f"Excluir este lançamento?\n\n{lanc.descricao[:80]}\n"
                f"{sinal} {formatar_moeda(abs(lanc.valor))} em {lanc.data}\n\n"
                "Esta ação não pode ser desfeita. Para re-importar este "
                "lançamento, basta importar o extrato de novo — ele virá "
                "como novo (não é mais considerado duplicado).",
            ):
                return
            # Excluir do banco
            excluir_lancamento(lanc_id)
            dlg.destroy()
            self._recarregar()

        # Linha 1 de botões: ações destrutivas (esquerda)
        esq = ctk.CTkFrame(botoes, fg_color="transparent")
        esq.pack(side="left")
        ctk.CTkButton(
            esq, text="🗑 Excluir", width=100,
            fg_color="transparent", border_width=1,
            border_color=cores["alerta"], text_color=cores["alerta"],
            command=excluir,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            esq, text="Remover categoria", width=140,
            fg_color="transparent", border_width=1,
            border_color=cores["texto_mudo"], text_color=cores["texto_mudo"],
            command=remover,
        ).pack(side="left")

        ctk.CTkButton(
            botoes, text="Cancelar", width=90,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=dlg.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            botoes, text="💾 Salvar", width=100, command=aplicar,
        ).pack(side="right")
