"""
importar_fatura_pdf_modal.py — Modal de importação de fatura via PDF.

Fluxo:
    1. Usuário seleciona PDF
    2. Se protegido, exibe prompt de senha inline
    3. Extrai + identifica layout + parsea
    4. Mostra preview e metadata (layout, N itens, total)
    5. Usuário opta por:
        - Salvar XLSX para conferência (asksaveasfilename)
        - Continuar para importação → gera XLSX temporário e abre o
          ImportarFaturaModal existente, reaproveitando 100% do fluxo
          de import Excel já testado.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import customtkinter as ctk

from config import get_tema
from database import obter_configuracao
from views.cartoes.cartao_model import Cartao
from views.cartoes.importar_fatura_pdf_model import (
    PDFCorrompidoError,
    PDFLayoutDesconhecidoError,
    PDFSenhaIncorretaError,
    pdf_para_linhas,
    pdf_tem_senha,
    salvar_como_xlsx,
)

log = logging.getLogger(__name__)


_LAYOUT_LABEL = {
    "nubank":   "Nubank",
    "itau":     "Itaú",
    "generico": "Genérico (fallback)",
}


class ImportarFaturaPDFModal(ctk.CTkToplevel):
    def __init__(self, parent, cartao: Cartao | None = None, on_importado=None):
        super().__init__(parent)
        self._cartao       = cartao
        self._on_importado = on_importado
        self._cores        = get_tema(obter_configuracao("tema", "claro"))
        self._pdf_caminho  = ""
        self._senha        = ""
        self._linhas: list[dict] = []
        self._meta: dict = {}

        titulo = (f"Serenus — Importar Fatura PDF · {cartao.nome}"
                  if cartao else "Serenus — Importar Fatura via PDF")
        self.title(titulo)
        self.geometry("720x640")
        self.resizable(True, True)
        self.grab_set()

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        cores = self._cores
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color=cores["sidebar"], corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        titulo_hdr = (f"⬆ Importar Fatura PDF — {self._cartao.nome}"
                      if self._cartao else "⬆ Importar Fatura via PDF")
        ctk.CTkLabel(
            hdr, text=titulo_hdr,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=cores["primario"],
        ).pack(pady=14, padx=20, anchor="w")

        # Seleção do PDF
        sel = ctk.CTkFrame(self, fg_color="transparent")
        sel.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 4))
        sel.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            sel, text="📂 Abrir PDF", width=130, height=32,
            command=self._abrir_pdf,
        ).grid(row=0, column=0, sticky="w")
        self._lbl_arquivo = ctk.CTkLabel(
            sel, text="Nenhum PDF selecionado.",
            text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self._lbl_arquivo.grid(row=0, column=1, sticky="ew", padx=12)

        # Prompt de senha (escondido por padrão)
        self._frame_senha = ctk.CTkFrame(self, fg_color=cores["fundo"],
                                          corner_radius=8)
        ctk.CTkLabel(
            self._frame_senha, text="🔒 Este PDF está protegido. Digite a senha:",
            text_color=cores["texto"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(12, 8), pady=10)
        self._e_senha = ctk.CTkEntry(
            self._frame_senha, width=160, show="•",
        )
        self._e_senha.pack(side="left", padx=4, pady=10)
        self._e_senha.bind("<Return>", lambda _e: self._aplicar_senha())
        ctk.CTkButton(
            self._frame_senha, text="Aplicar", width=80, height=28,
            command=self._aplicar_senha,
        ).pack(side="left", padx=8, pady=10)
        # Não dou grid aqui — só apareço quando _abrir_pdf detectar senha

        # Metadata (layout, N itens, total)
        self._lbl_meta = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=cores["primario"],
            anchor="w",
        )
        self._lbl_meta.grid(row=3, column=0, sticky="ew", padx=16, pady=(8, 0))

        # Preview em tabela
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=cores["fundo"], corner_radius=8,
        )
        self._scroll.grid(row=4, column=0, sticky="nsew", padx=16, pady=8)

        # Mensagens (sucesso / erro)
        self._lbl_msg = ctk.CTkLabel(
            self, text="",
            text_color=cores["alerta"],
            font=ctk.CTkFont(size=11),
            wraplength=680, justify="left",
        )
        self._lbl_msg.grid(row=5, column=0, sticky="ew", padx=16, pady=2)

        # Rodapé com botões
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=6, column=0, sticky="ew", padx=16, pady=(4, 12))
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            footer, text="Cancelar", width=100, height=34,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self.destroy,
        ).grid(row=0, column=1, padx=4)

        self._btn_salvar = ctk.CTkButton(
            footer, text="💾 Salvar XLSX para conferência",
            width=240, height=34, state="disabled",
            fg_color="transparent", border_width=1,
            border_color=cores["primario"], text_color=cores["primario"],
            command=self._salvar_xlsx,
        )
        self._btn_salvar.grid(row=0, column=2, padx=4)

        self._btn_continuar = ctk.CTkButton(
            footer, text="📊 Continuar para importação",
            width=220, height=34, state="disabled",
            command=self._continuar_para_import,
        )
        self._btn_continuar.grid(row=0, column=3, padx=4)

    # ------------------------------------------------------------------
    # Fluxo
    # ------------------------------------------------------------------

    def _abrir_pdf(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Selecionar PDF da fatura",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")],
        )
        if not path:
            return
        self._pdf_caminho = path
        self._senha = ""
        self._lbl_arquivo.configure(text=Path(path).name)
        self._limpar_mensagem()
        self._limpar_preview()
        self._lbl_meta.configure(text="")
        self._btn_salvar.configure(state="disabled")
        self._btn_continuar.configure(state="disabled")

        # Detecta se precisa de senha
        try:
            precisa_senha = pdf_tem_senha(path)
        except PDFCorrompidoError as e:
            self._mostrar_erro(f"PDF corrompido: {e}")
            return
        except Exception as e:
            self._mostrar_erro(f"Falha ao abrir PDF: {e}")
            return

        if precisa_senha:
            # Mostra o frame de senha e foca no campo
            self._frame_senha.grid(row=2, column=0, sticky="ew",
                                    padx=16, pady=(4, 0))
            self._e_senha.delete(0, "end")
            self._e_senha.focus_set()
            self._mostrar_mensagem(
                "PDF protegido — digite a senha e clique Aplicar.",
                tipo="atencao",
            )
        else:
            self._frame_senha.grid_forget()
            self._processar_pdf()

    def _aplicar_senha(self):
        self._senha = self._e_senha.get()
        if not self._senha:
            self._mostrar_erro("Digite a senha antes de aplicar.")
            return
        self._processar_pdf()

    def _processar_pdf(self):
        try:
            linhas, meta = pdf_para_linhas(
                self._pdf_caminho, senha=self._senha or None,
            )
        except PDFSenhaIncorretaError as e:
            self._mostrar_erro(f"Senha incorreta: {e}")
            self._e_senha.delete(0, "end")
            self._e_senha.focus_set()
            return
        except PDFLayoutDesconhecidoError as e:
            self._mostrar_erro(f"Layout do PDF não reconhecido: {e}")
            return
        except PDFCorrompidoError as e:
            self._mostrar_erro(f"PDF corrompido: {e}")
            return
        except Exception as e:
            log.exception("Erro inesperado processando PDF")
            self._mostrar_erro(f"Erro inesperado: {e}")
            return

        self._linhas = linhas
        self._meta   = meta
        self._frame_senha.grid_forget()
        self._mostrar_preview()
        self._atualizar_meta()
        self._btn_salvar.configure(state="normal")
        self._btn_continuar.configure(state="normal")
        self._limpar_mensagem()

    # ------------------------------------------------------------------
    # Preview e meta
    # ------------------------------------------------------------------

    def _limpar_preview(self):
        for w in self._scroll.winfo_children():
            w.destroy()

    def _mostrar_preview(self):
        cores = self._cores
        self._limpar_preview()

        cabecalhos = ["Descrição", "Parcela", "Valor"]
        for col, txt in enumerate(cabecalhos):
            ctk.CTkLabel(
                self._scroll, text=txt,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=cores["texto_mudo"],
            ).grid(row=0, column=col, sticky="w", padx=8, pady=(0, 4))

        for i, l in enumerate(self._linhas, start=1):
            desc = (l.get("descricao") or "")[:50]
            ctk.CTkLabel(
                self._scroll, text=desc,
                font=ctk.CTkFont(size=11),
                text_color=cores["texto"],
            ).grid(row=i, column=0, sticky="w", padx=8, pady=1)
            ctk.CTkLabel(
                self._scroll, text=l.get("parcela") or "—",
                font=ctk.CTkFont(size=11),
                text_color=cores["texto"],
            ).grid(row=i, column=1, sticky="w", padx=8)
            ctk.CTkLabel(
                self._scroll, text=f"R$ {l.get('valor', 0):.2f}",
                font=ctk.CTkFont(size=11),
                text_color=cores["texto"],
            ).grid(row=i, column=2, sticky="w", padx=8)

    def _atualizar_meta(self):
        layout = _LAYOUT_LABEL.get(self._meta.get("layout", ""),
                                    self._meta.get("layout", ""))
        n      = self._meta.get("n_itens", 0)
        total  = self._meta.get("total", 0.0)
        marca  = "🔒 com senha" if self._meta.get("tinha_senha") else "🔓 sem senha"
        ocr    = " · 🔍 OCR" if self._meta.get("ocr_usado") else ""
        self._lbl_meta.configure(
            text=f"Layout: {layout} · {marca} · {n} item(ns) · "
                 f"Total R$ {total:.2f}{ocr}"
        )

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _salvar_xlsx(self):
        from tkinter import filedialog
        nome_inicial = (
            f"fatura_{Path(self._pdf_caminho).stem}.xlsx"
            if self._pdf_caminho else "fatura.xlsx"
        )
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=nome_inicial,
            title="Salvar XLSX para conferência",
        )
        if not path:
            return
        try:
            salvar_como_xlsx(self._linhas, path)
            self._mostrar_mensagem(
                f"XLSX salvo em: {Path(path).name}", tipo="sucesso",
            )
        except Exception as e:
            self._mostrar_erro(f"Erro ao salvar: {e}")

    def _continuar_para_import(self):
        """Gera XLSX temporário e abre o ImportarFaturaModal existente."""
        from views.cartoes.importar_fatura_modal import ImportarFaturaModal

        tmp_dir = Path(tempfile.gettempdir())
        xlsx_path = tmp_dir / f"fatura_pdf_{Path(self._pdf_caminho).stem}.xlsx"
        try:
            salvar_como_xlsx(self._linhas, str(xlsx_path))
        except Exception as e:
            self._mostrar_erro(f"Erro ao preparar XLSX temporário: {e}")
            return

        parent = self.master
        cartao = self._cartao
        on_imp = self._on_importado
        self.destroy()

        # Abre o modal Excel já carregado com o XLSX vindo do PDF
        ImportarFaturaModal(
            parent, cartao=cartao, on_importado=on_imp,
            arquivo_inicial=str(xlsx_path),
        )

    # ------------------------------------------------------------------
    # Mensagens
    # ------------------------------------------------------------------

    def _mostrar_mensagem(self, texto: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {
            "sucesso": cores["positivo"],
            "erro":    cores["alerta"],
            "atencao": cores["atencao"],
        }.get(tipo, cores["texto_mudo"])
        self._lbl_msg.configure(text=texto, text_color=cor)

    def _mostrar_erro(self, texto: str):
        self._mostrar_mensagem(texto, tipo="erro")

    def _limpar_mensagem(self):
        self._lbl_msg.configure(text="", text_color=self._cores["texto_mudo"])
