"""
form_importar_extrato.py — Modal para importar extrato bancário.

Fluxo:
  1. User seleciona conta bancária no combo.
  2. User escolhe arquivo (CSV/OFX/PDF) via filedialog.
  3. Sistema detecta o parser apropriado e mostra preview (N transações).
  4. User clica "Importar" — aplica regras automáticas e insere com dedup.
  5. Toast com resultado (novos, duplicados, categorizados auto).
"""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
import tkinter.filedialog as fd
import tkinter.messagebox as mb

from config import get_tema, formatar_moeda
from database import obter_configuracao
from views.fluxo_caixa.conta_banco_model import listar_contas
from views.fluxo_caixa.extrato_banco_model import importar
from views.fluxo_caixa.extrato_parsers import detectar_parser


class FormImportarExtratoModal(ctk.CTkToplevel):
    """Modal de importação. on_importado(msg) é chamado após sucesso."""

    def __init__(self, parent, on_importado, conta_inicial_id: int | None = None):
        super().__init__(parent)
        self._on_importado = on_importado
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self._contas = listar_contas(apenas_ativas=True)
        self._arquivo: Path | None = None
        self._preview: list[dict] = []

        self.title("Serenus — Importar Extrato Bancário")
        self.geometry("560x560")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_ui()

        if conta_inicial_id is not None:
            for c in self._contas:
                if c.id == conta_inicial_id:
                    self._combo_conta.set(c.nome)
                    break

        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        master = self.master
        x = master.winfo_rootx() + (master.winfo_width()  - self.winfo_width())  // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, texto: str):
        ctk.CTkLabel(parent, text=texto, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    # ------------------------------------------------------------------

    def _build_ui(self):
        cores = self._cores
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=24, pady=16)

        # Conta
        self._label(outer, "Conta bancária *")
        if self._contas:
            nomes = [c.nome for c in self._contas]
        else:
            nomes = ["(nenhuma conta cadastrada — cadastre primeiro)"]
        self._combo_conta = ctk.CTkComboBox(
            outer, values=nomes, state="readonly", width=500,
        )
        self._combo_conta.set(nomes[0])
        self._combo_conta.pack(fill="x", pady=(2, 12))

        # Arquivo
        self._label(outer, "Arquivo de extrato (CSV / OFX / PDF) *")
        linha_arq = ctk.CTkFrame(outer, fg_color="transparent")
        linha_arq.pack(fill="x", pady=(2, 12))

        self._entry_arq = ctk.CTkEntry(
            linha_arq, placeholder_text="Nenhum arquivo selecionado",
            state="readonly",
        )
        self._entry_arq.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            linha_arq, text="📂 Escolher", width=110,
            command=self._escolher_arquivo,
        ).pack(side="left")

        # Preview area
        self._frame_preview = ctk.CTkFrame(outer, fg_color=cores["card"], corner_radius=8)
        self._frame_preview.pack(fill="both", expand=True, pady=(8, 0))

        self._lbl_preview = ctk.CTkLabel(
            self._frame_preview,
            text="Selecione um arquivo pra ver o preview.",
            text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=12),
            justify="center",
        )
        self._lbl_preview.pack(pady=24, padx=16)

        # Botões
        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkButton(
            botoes, text="Cancelar", width=100,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        self._btn_importar = ctk.CTkButton(
            botoes, text="⬆ Importar", width=140,
            command=self._on_importar,
            state="disabled",  # habilita após preview OK
        )
        self._btn_importar.pack(side="right")

    # ------------------------------------------------------------------

    def _escolher_arquivo(self):
        caminho = fd.askopenfilename(
            title="Selecionar arquivo de extrato",
            filetypes=[
                ("Todos suportados",   "*.csv *.ofx *.pdf"),
                ("CSV",                "*.csv"),
                ("OFX",                "*.ofx"),
                ("PDF",                "*.pdf"),
                ("Todos arquivos",     "*.*"),
            ],
            parent=self,
        )
        if not caminho:
            return
        self._arquivo = Path(caminho)
        self._entry_arq.configure(state="normal")
        self._entry_arq.delete(0, "end")
        self._entry_arq.insert(0, self._arquivo.name)
        self._entry_arq.configure(state="readonly")
        self._gerar_preview()

    def _gerar_preview(self):
        if not self._arquivo:
            return

        # Tenta deduzir banco a partir do nome da conta selecionada
        nome_conta = self._combo_conta.get().lower()
        banco = None
        for chave in ("nubank", "itau", "itaú", "bradesco", "santander", "caixa"):
            if chave in nome_conta:
                banco = chave.replace("ú", "u")
                break

        parser = detectar_parser(self._arquivo, banco=banco)
        if parser is None:
            self._lbl_preview.configure(
                text=f"Não há parser para arquivo .{self._arquivo.suffix} "
                     f"(banco: {banco or 'desconhecido'}).",
                text_color=self._cores["alerta"],
            )
            self._btn_importar.configure(state="disabled")
            return

        try:
            itens = parser.parse(self._arquivo)
        except Exception as e:
            self._lbl_preview.configure(
                text=f"Erro ao ler arquivo:\n{type(e).__name__}: {e}",
                text_color=self._cores["alerta"],
            )
            self._btn_importar.configure(state="disabled")
            return

        self._preview = itens
        entradas = sum(i["valor"] for i in itens if i["valor"] > 0)
        saidas   = sum(i["valor"] for i in itens if i["valor"] < 0)
        primeira = min((i["data"] for i in itens), default="-")
        ultima   = max((i["data"] for i in itens), default="-")

        self._lbl_preview.configure(
            text=(
                f"Parser:  {parser.nome_formato}\n"
                f"Periodo: {primeira}  ate  {ultima}\n\n"
                f"Total:    {len(itens)} lancamentos\n"
                f"Entradas: {formatar_moeda(entradas)}\n"
                f"Saidas:   {formatar_moeda(abs(saidas))}\n"
                f"Saldo:    {formatar_moeda(entradas + saidas)}"
            ),
            text_color=self._cores["texto"],
            justify="left",
        )
        if itens and self._contas:
            self._btn_importar.configure(state="normal")

    def _on_importar(self):
        if not self._preview:
            return
        if not self._contas:
            mb.showerror("Sem conta", "Cadastre uma conta bancária primeiro.")
            return

        nome = self._combo_conta.get()
        conta = next((c for c in self._contas if c.nome == nome), None)
        if conta is None:
            mb.showerror("Conta inválida", "Selecione uma conta válida.")
            return

        try:
            r = importar(conta.id, self._preview)
        except Exception as e:
            mb.showerror("Erro ao importar", str(e))
            return

        msg = (
            f"{r.novos} novos | {r.duplicados} duplicados (ignorados) | "
            f"{r.com_regra} categorizados automaticamente"
        )
        self.destroy()
        if self._on_importado:
            self._on_importado(msg)
