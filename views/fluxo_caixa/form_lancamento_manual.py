"""
form_lancamento_manual.py — Modal de criação/edição de lançamento manual de caixa.

Lançamento manual = entrada ou saída pontual que NÃO vem de contas_pagar nem
das automações (fontes_receita fixas, vendas, investimentos). Útil pra "recebi
R$ 50 em dinheiro" ou "paguei lanche em espécie".

UI:
  - Radio Tipo: ⬇ Saída | ⬆ Entrada
  - Data (DD/MM/AAAA) com máscara
  - Descrição (livre)
  - Categoria (combo) — muda conforme tipo:
       saída   → itens de plano_contas
       entrada → itens de fontes_receita
  - Valor (R$) com máscara monetária
  - Observação (opcional)
  - Botões: [Excluir] (só em edição) [Cancelar] [Salvar]
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk
import tkinter.messagebox as mb

from config import (
    get_tema,
    formatar_data_exibicao,
    parsear_data,
    mascara_moeda,
)
from database import obter_configuracao
from views.contas_pagar.conta_model import listar_plano_contas
from views.receitas.receita_model import listar_fontes
from views.fluxo_caixa.lancamento_manual_model import (
    LancamentoManual,
    salvar_lancamento,
    atualizar_lancamento,
    excluir_lancamento,
)


class FormLancamentoManualModal(ctk.CTkToplevel):
    """Modal de cadastro/edição de lançamento manual.

    on_salvo(msg) é chamado após salvar/excluir com sucesso.
    """

    def __init__(
        self,
        parent,
        on_salvo,
        lancamento: LancamentoManual | None = None,
    ):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._lanc = lancamento
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        self._planos  = listar_plano_contas(apenas_ativas=True)
        self._fontes  = listar_fontes(apenas_ativas=True)

        titulo = "Editar Lançamento" if lancamento else "Novo Lançamento"
        self.title(f"Serenus — {titulo}")
        self.geometry("440x560")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_ui()
        if lancamento:
            self._preencher(lancamento)
        else:
            self._on_tipo_mudou()  # popula combo inicial
        self.after(100, self._centralizar)

    # ------------------------------------------------------------------

    def _centralizar(self):
        self.update_idletasks()
        master = self.master
        x = master.winfo_rootx() + (master.winfo_width()  - self.winfo_width())  // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, texto: str):
        ctk.CTkLabel(parent, text=texto, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _mascara_data(self, entry: ctk.CTkEntry):
        raw = entry.get()
        digits = "".join(c for c in raw if c.isdigit())[:8]
        if len(digits) > 4:
            masked = digits[:2] + "/" + digits[2:4] + "/" + digits[4:]
        elif len(digits) > 2:
            masked = digits[:2] + "/" + digits[2:]
        else:
            masked = digits
        if masked != raw:
            entry.delete(0, "end")
            entry.insert(0, masked)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        cores = self._cores
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=16)
        self._frame = frame

        # Tipo (radio)
        self._label(frame, "Tipo *")
        tipo_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tipo_frame.pack(fill="x", pady=(2, 12))

        self._var_tipo = ctk.StringVar(value="saida")
        ctk.CTkRadioButton(
            tipo_frame, text="🔴  Saída", variable=self._var_tipo,
            value="saida", command=self._on_tipo_mudou,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            tipo_frame, text="🟢  Entrada", variable=self._var_tipo,
            value="entrada", command=self._on_tipo_mudou,
        ).pack(side="left")

        # Data
        self._label(frame, "Data *")
        self._entry_data = ctk.CTkEntry(frame, placeholder_text="DD/MM/AAAA", width=400)
        self._entry_data.insert(0, formatar_data_exibicao(date.today().isoformat()))
        self._entry_data.bind("<KeyRelease>",
                              lambda e: self._mascara_data(self._entry_data))
        self._entry_data.pack(fill="x", pady=(2, 12))

        # Descrição
        self._label(frame, "Descrição *")
        self._entry_desc = ctk.CTkEntry(
            frame, placeholder_text="Ex.: Comprei lanche em dinheiro", width=400
        )
        self._entry_desc.pack(fill="x", pady=(2, 12))

        # Categoria
        self._label(frame, "Categoria *")
        self._combo_cat = ctk.CTkComboBox(
            frame, values=[""], state="readonly", width=400
        )
        self._combo_cat.pack(fill="x", pady=(2, 12))

        # Valor
        self._label(frame, "Valor (R$) *")
        self._entry_valor = ctk.CTkEntry(frame, width=400)
        self._entry_valor.insert(0, "0,00")
        self._entry_valor.bind("<KeyRelease>",
                               lambda e: mascara_moeda(self._entry_valor))
        self._entry_valor.pack(fill="x", pady=(2, 12))

        # Observação
        self._label(frame, "Observação (opcional)")
        self._txt_obs = ctk.CTkTextbox(frame, height=70, width=400)
        self._txt_obs.pack(fill="x", pady=(2, 12))

        # Botões
        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=24, pady=(0, 16))

        if self._lanc:
            ctk.CTkButton(
                botoes, text="🗑 Excluir", width=100,
                fg_color="transparent", border_width=1,
                border_color=cores["alerta"], text_color=cores["alerta"],
                command=self._on_excluir,
            ).pack(side="left")

        ctk.CTkButton(
            botoes, text="Cancelar", width=100,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            botoes, text="💾 Salvar", width=120,
            command=self._on_salvar,
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _on_tipo_mudou(self):
        """Atualiza valores do combo de categoria conforme tipo escolhido."""
        if self._var_tipo.get() == "saida":
            valores = [p.nome for p in self._planos]
            if not valores:
                valores = ["(nenhuma categoria de despesa cadastrada)"]
        else:
            valores = [f.nome for f in self._fontes]
            if not valores:
                valores = ["(nenhuma fonte de receita cadastrada)"]
        self._combo_cat.configure(values=valores)
        self._combo_cat.set(valores[0])

    def _preencher(self, lanc: LancamentoManual):
        self._var_tipo.set(lanc.tipo)
        self._on_tipo_mudou()

        self._entry_data.delete(0, "end")
        self._entry_data.insert(0, formatar_data_exibicao(lanc.data))

        self._entry_desc.delete(0, "end")
        self._entry_desc.insert(0, lanc.descricao)

        if lanc.nome_categoria:
            self._combo_cat.set(lanc.nome_categoria)

        valor_str = f"{lanc.valor:.2f}".replace(".", ",")
        self._entry_valor.delete(0, "end")
        self._entry_valor.insert(0, valor_str)

        if lanc.observacao:
            self._txt_obs.delete("1.0", "end")
            self._txt_obs.insert("1.0", lanc.observacao)

    def _coletar(self) -> dict | None:
        tipo = self._var_tipo.get()

        data_iso = parsear_data(self._entry_data.get().strip())
        if not data_iso:
            mb.showerror("Data inválida", "Informe a data no formato DD/MM/AAAA.")
            return None

        descricao = self._entry_desc.get().strip()
        if not descricao:
            mb.showerror("Descrição obrigatória", "Informe uma descrição.")
            return None

        nome_cat = self._combo_cat.get().strip()
        if not nome_cat or nome_cat.startswith("("):
            mb.showerror(
                "Categoria obrigatória",
                "Selecione uma categoria. Se a lista estiver vazia, cadastre "
                "primeiro na tela de Plano de Contas (saídas) ou Receitas (entradas).",
            )
            return None

        # Resolve nome → id conforme tipo
        plano_id = fonte_id = None
        if tipo == "saida":
            cand = [p for p in self._planos if p.nome == nome_cat]
            if not cand:
                mb.showerror("Categoria inválida", "Categoria não encontrada.")
                return None
            plano_id = cand[0].id
        else:
            cand = [f for f in self._fontes if f.nome == nome_cat]
            if not cand:
                mb.showerror("Categoria inválida", "Fonte de receita não encontrada.")
                return None
            fonte_id = cand[0].id

        raw_valor = self._entry_valor.get().strip().replace(".", "").replace(",", ".")
        try:
            valor = float(raw_valor)
        except ValueError:
            valor = 0.0
        if valor <= 0:
            mb.showerror("Valor inválido", "Informe um valor maior que zero.")
            return None

        observacao = self._txt_obs.get("1.0", "end").strip()

        return {
            "data":             data_iso,
            "descricao":        descricao,
            "tipo":             tipo,
            "plano_conta_id":   plano_id,
            "fonte_receita_id": fonte_id,
            "valor":            valor,
            "observacao":       observacao,
        }

    def _on_salvar(self):
        dados = self._coletar()
        if dados is None:
            return
        try:
            if self._lanc:
                atualizar_lancamento(self._lanc.id, dados)
                msg = "Lançamento atualizado."
            else:
                salvar_lancamento(dados)
                msg = "Lançamento criado."
        except Exception as e:
            mb.showerror("Erro ao salvar", str(e))
            return

        self.destroy()
        if self._on_salvo:
            self._on_salvo(msg)

    def _on_excluir(self):
        if not self._lanc:
            return
        if not mb.askyesno(
            "Excluir lançamento",
            f"Excluir o lançamento '{self._lanc.descricao}'?\n\n"
            "Essa ação não pode ser desfeita.",
        ):
            return
        excluir_lancamento(self._lanc.id)
        self.destroy()
        if self._on_salvo:
            self._on_salvo("Lançamento excluído.")
