"""
form_movimentacao.py — Formulário de lançamento de movimentação de investimento.
"""
from __future__ import annotations
from typing import Callable, Optional

import customtkinter as ctk
from config import (get_tema, TIPOS_MOVIMENTACAO_INV, LABEL_TIPO_MOV_INV,
                    MOV_INV_SAIDA, MOV_INV_ENTRADA, formatar_moeda, parsear_data)
from database import obter_configuracao
from views.investimentos.investimento_model import (
    salvar_movimentacao, listar_contas_investimento, listar_ativos,
)

# Tipos que exigem campos de quantidade + preço unitário
_TIPOS_COM_QTD = {"compra", "venda"}


class FormMovimentacaoModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo: Callable,
                 ativo_id_default: Optional[int] = None):
        super().__init__(parent)
        self._cores         = get_tema(obter_configuracao("tema", "claro"))
        self._on_salvo      = on_salvo
        self._ativo_id_def  = ativo_id_default

        self.title("Nova movimentação")
        self.geometry("480x620")
        self.resizable(True, True)
        self.grab_set()

        self._contas = listar_contas_investimento(apenas_ativas=True)
        self._ativos_todos = listar_ativos(apenas_ativos=True)
        self._ativos_filtrados: list = list(self._ativos_todos)

        self._build_ui()
        self._on_tipo_change()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _label(self, parent, txt: str):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12),
                     text_color=self._cores["texto"]
                     ).pack(anchor="w", padx=20, pady=(8, 0))

    def _toast_erro(self, msg: str):
        self._lbl_erro.configure(text=msg)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        cores = self._cores

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll

        ctk.CTkLabel(scroll, text="📋  Nova Movimentação",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=cores["texto"]
                     ).pack(pady=(16, 4), padx=20, anchor="w")

        # Conta
        self._label(scroll, "Conta de investimento *")
        nomes_contas = [c.nome for c in self._contas] or ["(nenhuma conta ativa)"]
        self._combo_conta = ctk.CTkComboBox(
            scroll, values=nomes_contas, state="readonly",
            command=self._on_conta_change,
        )
        self._combo_conta.set(nomes_contas[0])
        self._combo_conta.pack(fill="x", padx=20, pady=(2, 0))

        # Ativo
        self._label(scroll, "Ativo *")
        frame_ativo = ctk.CTkFrame(scroll, fg_color="transparent")
        frame_ativo.pack(fill="x", padx=20, pady=(2, 0))
        self._combo_ativo = ctk.CTkComboBox(
            frame_ativo, values=self._nomes_ativos(), state="readonly",
        )
        self._combo_ativo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            frame_ativo, text="+ Novo", width=60, height=28,
            command=self._novo_ativo,
        ).pack(side="left", padx=(6, 0))
        if self._ativos_filtrados:
            self._combo_ativo.set(self._nomes_ativos()[0])

        # Tipo
        self._label(scroll, "Tipo *")
        tipos_labels = [LABEL_TIPO_MOV_INV.get(t, t) for t in TIPOS_MOVIMENTACAO_INV]
        self._combo_tipo = ctk.CTkComboBox(
            scroll, values=tipos_labels, state="readonly",
            command=self._on_tipo_change,
        )
        self._combo_tipo.set(tipos_labels[0])
        self._combo_tipo.pack(fill="x", padx=20, pady=(2, 0))

        # Data
        self._label(scroll, "Data *")
        from datetime import date
        self._e_data = ctk.CTkEntry(scroll, placeholder_text="DD/MM/AAAA")
        self._e_data.pack(fill="x", padx=20, pady=(2, 0))
        self._e_data.insert(0, date.today().strftime("%d/%m/%Y"))

        # Quantidade + preço (renda variável)
        self._frame_qtd = ctk.CTkFrame(scroll, fg_color="transparent")
        row_qtd = ctk.CTkFrame(self._frame_qtd, fg_color="transparent")
        row_qtd.pack(fill="x")
        ctk.CTkLabel(row_qtd, text="Quantidade",
                     anchor="w", font=ctk.CTkFont(size=12),
                     text_color=cores["texto"]
                     ).pack(side="left", padx=(0, 8))
        self._e_qtd = ctk.CTkEntry(row_qtd, width=110, placeholder_text="0")
        self._e_qtd.pack(side="left")
        ctk.CTkLabel(row_qtd, text="  Preço unit. (R$)",
                     anchor="w", font=ctk.CTkFont(size=12),
                     text_color=cores["texto"]
                     ).pack(side="left", padx=(16, 8))
        self._e_preco = ctk.CTkEntry(row_qtd, width=110, placeholder_text="0,00")
        self._e_preco.pack(side="left")
        self._e_qtd.bind("<KeyRelease>",   lambda _: self._calc_bruto())
        self._e_preco.bind("<KeyRelease>", lambda _: self._calc_bruto())
        self._frame_qtd.pack(fill="x", padx=20, pady=(8, 0))

        # Valor bruto
        self._label(scroll, "Valor bruto (R$) *")
        self._e_bruto = ctk.CTkEntry(scroll, placeholder_text="0,00")
        self._e_bruto.pack(fill="x", padx=20, pady=(2, 0))
        self._e_bruto.bind("<KeyRelease>", lambda _: self._calc_liquido())

        # Taxas
        self._label(scroll, "Taxas / Corretagem (R$)")
        self._e_taxas = ctk.CTkEntry(scroll, placeholder_text="0,00")
        self._e_taxas.pack(fill="x", padx=20, pady=(2, 0))
        self._e_taxas.bind("<KeyRelease>", lambda _: self._calc_liquido())

        # Valor líquido (read-only calculado)
        self._label(scroll, "Valor líquido (R$)")
        self._e_liq = ctk.CTkEntry(scroll, state="disabled",
                                    placeholder_text="calculado automaticamente")
        self._e_liq.pack(fill="x", padx=20, pady=(2, 0))

        # Registrar no financeiro
        self._fin_var = ctk.BooleanVar(value=True)
        self._chk_fin = ctk.CTkCheckBox(
            scroll, text="Registrar no módulo financeiro",
            variable=self._fin_var,
            font=ctk.CTkFont(size=12),
        )
        self._chk_fin.pack(anchor="w", padx=20, pady=(12, 0))
        self._lbl_fin_hint = ctk.CTkLabel(
            scroll, text="", font=ctk.CTkFont(size=10),
            text_color=cores["texto_mudo"], anchor="w",
        )
        self._lbl_fin_hint.pack(anchor="w", padx=20)

        # Observação
        self._label(scroll, "Observação")
        self._e_obs = ctk.CTkEntry(scroll)
        self._e_obs.pack(fill="x", padx=20, pady=(2, 0))

        # Erro
        self._lbl_erro = ctk.CTkLabel(scroll, text="",
                                       text_color=cores["alerta"],
                                       font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w", padx=20, pady=(6, 0))

        # Botões
        btns = ctk.CTkFrame(scroll, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="Cancelar", width=120,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["borda"],
                      text_color=self._cores["texto"],
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Salvar", width=120,
                      command=self._salvar).pack(side="left", padx=6)

    # ── lógica dinâmica ──────────────────────────────────────────────────────

    def _nomes_ativos(self) -> list[str]:
        return [f"{a.codigo} — {a.nome}" for a in self._ativos_filtrados] or ["(nenhum ativo)"]

    def _on_conta_change(self, _=None):
        conta_nome = self._combo_conta.get()
        conta = next((c for c in self._contas if c.nome == conta_nome), None)
        if conta:
            self._ativos_filtrados = [
                a for a in self._ativos_todos
                if a.conta_investimento_id == conta.id
            ]
            if not self._ativos_filtrados:
                self._ativos_filtrados = list(self._ativos_todos)
        else:
            self._ativos_filtrados = list(self._ativos_todos)
        nomes = self._nomes_ativos()
        self._combo_ativo.configure(values=nomes)
        self._combo_ativo.set(nomes[0])

    def _on_tipo_change(self, _=None):
        tipo_label = self._combo_tipo.get()
        tipo = next((k for k, v in LABEL_TIPO_MOV_INV.items() if v == tipo_label), "")

        if tipo in _TIPOS_COM_QTD:
            self._frame_qtd.pack(fill="x", padx=20, pady=(8, 0))
        else:
            self._frame_qtd.pack_forget()

        if tipo in MOV_INV_SAIDA:
            hint = "⬇ Gera saída no extrato financeiro"
        elif tipo in MOV_INV_ENTRADA:
            hint = "⬆ Gera entrada no extrato financeiro"
        else:
            hint = ""
        self._lbl_fin_hint.configure(text=hint)

    def _calc_bruto(self):
        try:
            qtd   = float(self._e_qtd.get().replace(",", ".") or 0)
            preco = float(self._e_preco.get().replace(",", ".") or 0)
            bruto = round(qtd * preco, 2)
            self._e_bruto.delete(0, "end")
            self._e_bruto.insert(0, f"{bruto:.2f}".replace(".", ","))
        except ValueError:
            pass
        self._calc_liquido()

    def _calc_liquido(self):
        try:
            bruto = float(self._e_bruto.get().replace(",", ".") or 0)
            taxas = float(self._e_taxas.get().replace(",", ".") or 0)
            tipo_label = self._combo_tipo.get()
            tipo = next((k for k, v in LABEL_TIPO_MOV_INV.items() if v == tipo_label), "")
            # Saídas: líquido = bruto + taxas; Entradas: líquido = bruto - taxas
            liq = bruto + taxas if tipo in MOV_INV_SAIDA else bruto - taxas
            liq = max(0.0, round(liq, 2))
            self._e_liq.configure(state="normal")
            self._e_liq.delete(0, "end")
            self._e_liq.insert(0, f"{liq:.2f}".replace(".", ","))
            self._e_liq.configure(state="disabled")
        except ValueError:
            pass

    def _novo_ativo(self):
        from views.investimentos.form_ativo import FormAtivoModal
        FormAtivoModal(self, on_salvo=self._recarregar_ativos)

    def _recarregar_ativos(self):
        self._ativos_todos = listar_ativos(apenas_ativos=True)
        self._on_conta_change()

    # ── salvar ───────────────────────────────────────────────────────────────

    def _salvar(self):
        self._lbl_erro.configure(text="")

        # Conta
        conta_nome = self._combo_conta.get()
        conta = next((c for c in self._contas if c.nome == conta_nome), None)
        if not conta:
            self._toast_erro("Selecione uma conta.")
            return

        # Ativo
        ativo_str  = self._combo_ativo.get()
        ativo_code = ativo_str.split(" — ")[0].strip()
        ativo = next((a for a in self._ativos_filtrados if a.codigo == ativo_code), None)
        if not ativo:
            self._toast_erro("Selecione um ativo.")
            return

        # Tipo
        tipo_label = self._combo_tipo.get()
        tipo = next((k for k, v in LABEL_TIPO_MOV_INV.items() if v == tipo_label), "")

        # Data
        data_br = self._e_data.get().strip()
        data_iso = parsear_data(data_br)
        if not data_iso:
            self._toast_erro("Data inválida.")
            return

        # Qtd / preço — devem ser positivos para movimentações que mexem na posição
        qtd, preco = 0.0, 0.0
        if tipo in _TIPOS_COM_QTD:
            try:
                qtd   = float(self._e_qtd.get().replace(",", ".") or 0)
                preco = float(self._e_preco.get().replace(",", ".") or 0)
            except ValueError:
                self._toast_erro("Quantidade ou preço inválido.")
                return
            if qtd <= 0:
                self._toast_erro("Quantidade deve ser maior que zero.")
                return
            if preco < 0:
                self._toast_erro("Preço unitário não pode ser negativo.")
                return

        # Bruto / taxas / líquido
        try:
            bruto = float(self._e_bruto.get().replace(",", ".") or 0)
            taxas = float(self._e_taxas.get().replace(",", ".") or 0)
        except ValueError:
            self._toast_erro("Valor inválido.")
            return

        if bruto <= 0:
            self._toast_erro("Informe o valor bruto.")
            return

        liq = bruto + taxas if tipo in MOV_INV_SAIDA else max(0.0, bruto - taxas)

        dados = {
            "ativo_id":               ativo.id,
            "conta_investimento_id":  conta.id,
            "tipo":                   tipo,
            "data":                   data_iso,
            "quantidade":             qtd,
            "preco_unitario":         preco,
            "valor_bruto":            round(bruto, 2),
            "taxas":                  round(taxas, 2),
            "valor_liquido":          round(liq, 2),
            "observacao":             self._e_obs.get().strip(),
            "registrar_no_financeiro": self._fin_var.get(),
        }
        salvar_movimentacao(dados)
        self.destroy()
        self._on_salvo()
