"""
importar_fatura_modal.py — Modal de importação de fatura de cartão.
Fluxo: selecionar arquivo → pré-visualizar → validar → importar.
"""

from __future__ import annotations
import customtkinter as ctk
from datetime import date
from pathlib import Path

from config import get_tema, NOMES_MESES
from database import obter_configuracao
from views.cartoes.cartao_model import Cartao


class ImportarFaturaModal(ctk.CTkToplevel):
    def __init__(self, parent, cartao: Cartao | None = None, on_importado=None,
                 arquivo_inicial: str | None = None):
        """
        arquivo_inicial: se passado, pula o filedialog e carrega esse XLSX/CSV
        diretamente. Usado pelo modal de PDF para entregar o XLSX intermediário
        no mesmo fluxo de import existente.
        """
        super().__init__(parent)
        self._cartao       = cartao
        self._on_importado = on_importado
        self._cores        = get_tema(obter_configuracao("tema", "claro"))
        self._linhas: list = []
        self._arquivo      = arquivo_inicial or ""
        self._cartoes_map: dict[str, int] = {}  # "Nome" → id

        titulo = f"Serenus — Importar Fatura · {cartao.nome}" if cartao else "Serenus — Importar Fatura de Cartão"
        self.title(titulo)
        self.geometry("700x660")
        self.resizable(True, True)
        self.grab_set()

        self._build()

        # Se veio arquivo inicial (vindo do fluxo PDF), carrega já
        if arquivo_inicial:
            self._lbl_arquivo.configure(text=Path(arquivo_inicial).name)
            self._processar_arquivo()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        cores = self._cores
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Cabeçalho ──────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=cores["sidebar"], corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        titulo_hdr = (f"⬆  Importar Fatura — {self._cartao.nome}"
                      if self._cartao else "⬆  Importar Fatura de Cartão")
        ctk.CTkLabel(hdr,
                     text=titulo_hdr,
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=cores["primario"]).pack(pady=14, padx=20, anchor="w")

        # ── Controles superiores ───────────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 0))
        ctrl.grid_columnconfigure(1, weight=1)

        # Seletor de cartão (visível apenas quando não foi passado cartão)
        if self._cartao is None:
            from views.cartoes.cartao_model import listar_cartoes
            todos = listar_cartoes(apenas_ativos=True)
            self._cartoes_map = {c.nome: c.id for c in todos}
            nomes = list(self._cartoes_map.keys())
            if not nomes:
                nomes = ["(nenhum cartão cadastrado)"]
            ctk.CTkLabel(ctrl, text="Cartão:",
                         text_color=cores["texto"]).grid(row=0, column=0, sticky="w", padx=(0, 8))
            self._var_cartao = ctk.StringVar(value=nomes[0])
            ctk.CTkComboBox(ctrl, values=nomes, variable=self._var_cartao,
                            width=200).grid(row=0, column=1, sticky="w")
            row_offset = 1
        else:
            row_offset = 0

        # Mês de referência da fatura
        ctk.CTkLabel(ctrl, text="Mês da fatura:",
                     text_color=cores["texto"]).grid(row=row_offset, column=0, sticky="w", padx=(0, 8))

        hoje = date.today()
        anos = [hoje.year - 1, hoje.year, hoje.year + 1]
        meses = [f"{NOMES_MESES[m]} {a}" for a in anos for m in range(12)]
        mes_atual = f"{NOMES_MESES[hoje.month - 1]} {hoje.year}"
        self._var_mes = ctk.StringVar(value=mes_atual)
        combo_mes = ctk.CTkComboBox(ctrl, values=meses, variable=self._var_mes, width=180)
        combo_mes.grid(row=row_offset, column=1, sticky="w")

        # Data de vencimento da fatura (opcional — cabeçalho do extrato)
        row_venc = row_offset + 1
        ctk.CTkLabel(ctrl, text="Vencimento (opcional):",
                     text_color=cores["texto"]).grid(
            row=row_venc, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        self._e_vencimento = ctk.CTkEntry(
            ctrl, width=120, placeholder_text="DD/MM/AAAA",
        )
        self._e_vencimento.grid(row=row_venc, column=1, sticky="w", pady=(8, 0))
        ctk.CTkLabel(
            ctrl,
            text="Se vazio, usa o dia de vencimento do cartão.",
            text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=10),
        ).grid(row=row_venc, column=2, sticky="w", padx=8, pady=(8, 0))

        # Checkbox criar histórico
        self._var_historico = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(ctrl,
                        text="Criar histórico das parcelas já pagas",
                        variable=self._var_historico,
                        font=ctk.CTkFont(size=12),
                        text_color=cores["texto"]).grid(row=row_offset, column=2, padx=16)

        # Botões de arquivo
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="e", padx=16, pady=(10, 0))

        ctk.CTkButton(btns, text="⬇  Template XLSX", width=140, height=30,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      font=ctk.CTkFont(size=11),
                      command=self._baixar_template).pack(side="left", padx=4)

        ctk.CTkButton(btns, text="📂  Abrir arquivo", width=130, height=30,
                      font=ctk.CTkFont(size=11),
                      command=self._abrir_arquivo).pack(side="left", padx=4)

        # ── Label do arquivo selecionado ───────────────────────────────
        self._lbl_arquivo = ctk.CTkLabel(self, text="Nenhum arquivo selecionado.",
                                          text_color=cores["texto_mudo"],
                                          font=ctk.CTkFont(size=11))
        self._lbl_arquivo.grid(row=1, column=0, sticky="w", padx=16, pady=(44, 0))

        # ── Tabela de pré-visualização ─────────────────────────────────
        scroll = ctk.CTkScrollableFrame(self, fg_color=cores["fundo"], corner_radius=8)
        scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(8, 0))
        scroll.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self._scroll_tabela = scroll

        # ── Erros ──────────────────────────────────────────────────────
        self._lbl_erros = ctk.CTkLabel(self, text="",
                                        text_color=cores["alerta"],
                                        font=ctk.CTkFont(size=11),
                                        wraplength=660, justify="left")
        self._lbl_erros.grid(row=3, column=0, sticky="ew", padx=16, pady=4)

        # ── Rodapé ─────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)

        self._lbl_resumo = ctk.CTkLabel(footer, text="",
                                         text_color=cores["texto_mudo"],
                                         font=ctk.CTkFont(size=11))
        self._lbl_resumo.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(footer, text="Cancelar", width=100, height=34,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=self.destroy).grid(row=0, column=1, padx=4)

        self._btn_importar = ctk.CTkButton(footer, text="⬆  Importar", width=120, height=34,
                                            state="disabled",
                                            command=self._importar)
        self._btn_importar.grid(row=0, column=2, padx=4)

    # ------------------------------------------------------------------
    # Arquivo
    # ------------------------------------------------------------------

    def _abrir_arquivo(self):
        from tkinter import filedialog
        caminho = filedialog.askopenfilename(
            title="Selecionar fatura",
            filetypes=[("Planilhas / CSV", "*.xlsx *.csv"), ("Todos", "*.*")],
        )
        if not caminho:
            return
        self._arquivo = caminho
        self._lbl_arquivo.configure(text=Path(caminho).name)
        self._processar_arquivo()

    def _processar_arquivo(self):
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura, validar_linhas_fatura
        cores = self._cores
        try:
            linhas = ler_arquivo_fatura(self._arquivo)
        except Exception as exc:
            self._lbl_erros.configure(text=f"Erro ao ler arquivo: {exc}")
            self._btn_importar.configure(state="disabled")
            return

        erros = validar_linhas_fatura(linhas)
        self._linhas = linhas

        # Atualiza tabela
        for w in self._scroll_tabela.winfo_children():
            w.destroy()

        # Cabeçalho tabela
        for col, txt in enumerate(["Descrição", "Parcela", "Valor", "Categoria"]):
            ctk.CTkLabel(self._scroll_tabela, text=txt,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(
                row=0, column=col, sticky="w", padx=8, pady=(0, 4))

        for i, l in enumerate(linhas, start=1):
            ctk.CTkLabel(self._scroll_tabela,
                         text=l.get("descricao", "")[:40],
                         font=ctk.CTkFont(size=11),
                         text_color=cores["texto"]).grid(row=i, column=0, sticky="w", padx=8, pady=1)
            ctk.CTkLabel(self._scroll_tabela,
                         text=l.get("parcela", "") or "1/1",
                         font=ctk.CTkFont(size=11),
                         text_color=cores["texto"]).grid(row=i, column=1, sticky="w", padx=8)
            ctk.CTkLabel(self._scroll_tabela,
                         text=f"R$ {l.get('valor', 0):.2f}",
                         font=ctk.CTkFont(size=11),
                         text_color=cores["texto"]).grid(row=i, column=2, sticky="w", padx=8)
            ctk.CTkLabel(self._scroll_tabela,
                         text=l.get("categoria", "")[:20],
                         font=ctk.CTkFont(size=11),
                         text_color=cores["texto_mudo"]).grid(row=i, column=3, sticky="w", padx=8)

        if erros:
            self._lbl_erros.configure(text="\n".join(erros[:5]))
            self._btn_importar.configure(state="disabled")
        else:
            self._lbl_erros.configure(text="")
            self._btn_importar.configure(state="normal")

        total = sum(l.get("valor", 0) for l in linhas)
        self._lbl_resumo.configure(
            text=f"{len(linhas)} item(ns)  •  Total: R$ {total:.2f}"
        )

    # ------------------------------------------------------------------
    # Template
    # ------------------------------------------------------------------

    def _baixar_template(self):
        from tkinter import filedialog
        from views.exportar.exportar_model import gerar_template_importacao_xlsx
        destino = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="template_fatura.xlsx",
            title="Salvar template",
        )
        if not destino:
            return
        try:
            gerar_template_importacao_xlsx(destino)
            self._lbl_erros.configure(
                text=f"Template salvo: {Path(destino).name}",
            )
            self._lbl_erros.configure(text_color=self._cores["positivo"])
        except Exception as exc:
            self._lbl_erros.configure(text=f"Erro ao salvar template: {exc}")

    # ------------------------------------------------------------------
    # Importar
    # ------------------------------------------------------------------

    def _mes_referencia_selecionado(self) -> str:
        """Converte o label do combo (ex: 'Maio 2025') para 'YYYY-MM'."""
        val = self._var_mes.get()
        hoje = date.today()
        partes = val.strip().split()
        if len(partes) == 2:
            nome_mes, ano_str = partes
            try:
                mes_idx = next(
                    i + 1 for i, m in enumerate(NOMES_MESES)
                    if m.lower() == nome_mes.lower()
                )
                return f"{int(ano_str):04d}-{mes_idx:02d}"
            except (StopIteration, ValueError):
                pass
        return f"{hoje.year:04d}-{hoje.month:02d}"

    def _cartao_id_selecionado(self) -> int | None:
        if self._cartao:
            return self._cartao.id
        nome = self._var_cartao.get()
        return self._cartoes_map.get(nome)

    def _importar(self):
        from config import parsear_data
        from views.cartoes.importar_fatura_model import parsear_parcela
        from views.cartoes.cartao_model import importar_compra_fatura

        if not self._linhas:
            return

        cartao_id = self._cartao_id_selecionado()
        if not cartao_id:
            self._lbl_erros.configure(text="Selecione um cartão antes de importar.")
            return

        mes_ref     = self._mes_referencia_selecionado()
        criar_hist  = self._var_historico.get()

        # Vencimento opcional: se preenchido, valida e usa pra forçar a data
        # da parcela do mes_referencia em contas_pagar
        venc_iso = None
        venc_str = self._e_vencimento.get().strip()
        if venc_str:
            venc_iso = parsear_data(venc_str)
            if not venc_iso:
                self._lbl_erros.configure(
                    text="Data de vencimento inválida (use DD/MM/AAAA)."
                )
                return

        importados  = 0
        duplicados  = 0
        erros_imp: list[str] = []

        for linha in self._linhas:
            try:
                parcela_str = linha.get("parcela", "")
                num_parc, total_parc = parsear_parcela(parcela_str)
                dados = {
                    "cartao_id":        cartao_id,
                    "descricao":        linha["descricao"],
                    "estabelecimento":  linha.get("estabelecimento", ""),
                    "categoria":        linha.get("categoria", ""),
                    "numero_parcela":   num_parc,
                    "total_parcelas":   total_parc,
                    "valor_parcela":    linha["valor"],
                    "mes_referencia":   mes_ref,
                    "data_vencimento":  venc_iso,
                    "criar_historico":  criar_hist,
                }
                resultado = importar_compra_fatura(dados)
                if resultado is None:
                    duplicados += 1
                else:
                    importados += 1
            except Exception as exc:
                erros_imp.append(f"{linha.get('descricao', '?')}: {exc}")

        msg_partes = [f"{importados} item(ns) importado(s)"]
        if duplicados:
            msg_partes.append(f"{duplicados} duplicata(s) ignorada(s)")
        if erros_imp:
            msg_partes.append(f"{len(erros_imp)} erro(s)")

        self._lbl_resumo.configure(text=" · ".join(msg_partes))

        if erros_imp:
            self._lbl_erros.configure(
                text="\n".join(erros_imp[:3]),
                text_color=self._cores["alerta"],
            )

        if importados > 0 and self._on_importado:
            self._on_importado(f"Fatura importada: {importados} item(ns).")

        if not erros_imp:
            self.after(1200, self.destroy)
