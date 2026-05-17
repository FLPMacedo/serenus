"""
metas_view.py — Tela de Metas Financeiras.
"""
from __future__ import annotations
import customtkinter as ctk
from config import get_tema, formatar_moeda
from database import obter_configuracao
from views.metas.metas_model import Meta, listar_metas, excluir_meta, atualizar_valor_meta


class MetasView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_banner()
        self._build_corpo()
        self._carregar()

    def _build_banner(self):
        from views.widgets.ajuda import banner_ajuda
        b = banner_ajuda(
            self, self._cores,
            "Defina objetivos financeiros (viagem, reserva, etc.). O sistema "
            "calcula quanto poupar por mês para chegar no prazo e mostra "
            "barra de progresso a cada depósito.",
        )
        if b:
            b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))

    # ─────────────────────────────────────────────────────────────────────
    # Layout
    # ─────────────────────────────────────────────────────────────────────

    def _build_header(self):
        cores = self._cores
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="🎯  Metas Financeiras",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=cores["texto"],
        ).grid(row=0, column=0, sticky="w")

        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            btns, text="⬇ Excel", width=80, height=34,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._exportar_excel,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btns, text="+ Nova meta", height=34,
            command=self._abrir_form_novo,
        ).pack(side="left")

    def _build_corpo(self):
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=16)
        self._scroll.grid_columnconfigure(0, weight=1)

    def _exportar_excel(self):
        from tkinter import filedialog as fd
        import tkinter.messagebox as mb
        dest = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="metas_financeiras.xlsx",
        )
        if not dest:
            return
        try:
            from views.exportar.exportar_model import exportar_metas_xlsx
            exportar_metas_xlsx(dest)
            mb.showinfo("Exportação", "Metas exportadas com sucesso.")
        except Exception as e:
            mb.showerror("Erro", f"Erro ao exportar: {e}")

    # ─────────────────────────────────────────────────────────────────────
    # Dados
    # ─────────────────────────────────────────────────────────────────────

    def _carregar(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        metas = listar_metas()
        if not metas:
            ctk.CTkLabel(
                self._scroll,
                text="Nenhuma meta cadastrada.\nClique em '+ Nova meta' para começar.",
                text_color=self._cores["texto_mudo"],
                font=ctk.CTkFont(size=13),
                justify="center",
            ).pack(pady=60)
            return

        for meta in metas:
            self._card_meta(meta)

    def _card_meta(self, meta: Meta):
        cores = self._cores
        concluida = meta.concluida

        card = ctk.CTkFrame(
            self._scroll,
            fg_color=cores["card"],
            corner_radius=12,
            border_width=2 if concluida else 0,
            border_color=cores["positivo"] if concluida else cores["borda"],
        )
        card.pack(fill="x", pady=6)
        card.grid_columnconfigure(0, weight=1)

        # Linha título
        topo = ctk.CTkFrame(card, fg_color="transparent")
        topo.pack(fill="x", padx=16, pady=(12, 4))
        topo.grid_columnconfigure(0, weight=1)

        emoji = "✅" if concluida else "🎯"
        ctk.CTkLabel(
            topo,
            text=f"{emoji}  {meta.nome}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=cores["positivo"] if concluida else cores["texto"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        # Botões ação
        btns = ctk.CTkFrame(topo, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            btns, text="✏ Editar", width=70, height=26,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            font=ctk.CTkFont(size=11),
            command=lambda m=meta: self._abrir_form_editar(m),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btns, text="💰 Depositar", width=90, height=26,
            fg_color="transparent", border_width=1,
            border_color=cores["primario"], text_color=cores["primario"],
            font=ctk.CTkFont(size=11),
            command=lambda m=meta: self._depositar(m),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btns, text="🗑", width=32, height=26,
            fg_color="transparent", border_width=1,
            border_color=cores["alerta"], text_color=cores["alerta"],
            font=ctk.CTkFont(size=11),
            command=lambda m=meta: self._confirmar_excluir(m),
        ).pack(side="left", padx=2)

        # Valores
        vals = ctk.CTkFrame(card, fg_color="transparent")
        vals.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(
            vals,
            text=f"Acumulado: {formatar_moeda(meta.valor_atual)}  /  "
                 f"Meta: {formatar_moeda(meta.valor_alvo)}",
            font=ctk.CTkFont(size=12),
            text_color=cores["texto_mudo"],
        ).pack(side="left")

        # Prazo + economia
        if meta.prazo:
            dias = meta.dias_restantes
            if dias is not None:
                sufixo = f"{dias}d" if dias >= 0 else f"{abs(dias)}d atrasada"
                econ   = (f"  ·  Economizar {formatar_moeda(meta.economia_mensal_necessaria)}/mês"
                          if meta.economia_mensal_necessaria else "")
                ctk.CTkLabel(
                    vals,
                    text=f"  ·  Prazo: {meta.prazo}  ({sufixo}){econ}",
                    font=ctk.CTkFont(size=11),
                    text_color=cores["alerta"] if dias < 0 else cores["texto_mudo"],
                ).pack(side="left")

        # Barra de progresso
        bar_frame = ctk.CTkFrame(card, fg_color="transparent")
        bar_frame.pack(fill="x", padx=16, pady=(2, 12))

        bar_bg = ctk.CTkFrame(bar_frame, height=14,
                              fg_color=cores["borda"], corner_radius=7)
        bar_bg.pack(fill="x")
        bar_bg.update_idletasks()
        w = bar_bg.winfo_width() or 400
        pct = meta.progresso_pct / 100
        bar_w = max(14, int(w * pct))
        cor_barra = cores["positivo"] if concluida else cores["primario"]
        ctk.CTkFrame(bar_bg, width=bar_w, height=14,
                     fg_color=cor_barra, corner_radius=7
                     ).place(x=0, y=0)
        ctk.CTkLabel(
            bar_frame,
            text=f"{meta.progresso_pct:.0f}%",
            font=ctk.CTkFont(size=10),
            text_color=cores["texto_mudo"],
        ).pack(anchor="e")

    # ─────────────────────────────────────────────────────────────────────
    # Formulário (modal inline)
    # ─────────────────────────────────────────────────────────────────────

    def _abrir_form_novo(self):
        _FormMetaModal(self, on_salvo=self._carregar)

    def _abrir_form_editar(self, meta: Meta):
        _FormMetaModal(self, on_salvo=self._carregar, meta=meta)

    def _depositar(self, meta: Meta):
        """Diálogo rápido para adicionar valor à meta."""
        cores = self._cores
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Depositar em: {meta.nome}")
        dlg.geometry("320x200")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.bind("<Escape>", lambda e: dlg.destroy())

        ctk.CTkLabel(dlg, text="Valor a adicionar (R$)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 8))
        entry = ctk.CTkEntry(dlg, width=200, justify="center",
                             placeholder_text="0,00")
        entry.pack()
        ctk.CTkLabel(dlg, text=f"Acumulado atual: {formatar_moeda(meta.valor_atual)}",
                     font=ctk.CTkFont(size=10), text_color=cores["texto_mudo"]).pack(pady=4)

        def _ok():
            try:
                adicionar = float(entry.get().replace(".", "").replace(",", "."))
                if adicionar > 0:
                    novo = round(meta.valor_atual + adicionar, 2)
                    atualizar_valor_meta(meta.id, novo)
                    dlg.destroy()
                    self._carregar()
            except ValueError:
                pass

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Cancelar", width=90, height=30,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Confirmar", width=100, height=30,
                      command=_ok).pack(side="left", padx=4)

    def _confirmar_excluir(self, meta: Meta):
        cores = self._cores
        dlg = ctk.CTkToplevel(self)
        dlg.title("Excluir meta")
        dlg.geometry("340x160")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.bind("<Escape>", lambda e: dlg.destroy())

        ctk.CTkLabel(dlg, text=f'Excluir a meta "{meta.nome}"?',
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(24, 8))
        ctk.CTkLabel(dlg, text="Esta ação não pode ser desfeita.",
                     text_color=cores["texto_mudo"]).pack()

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=16)

        def _ok():
            excluir_meta(meta.id)
            dlg.destroy()
            self._carregar()

        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Excluir", width=100,
                      fg_color=cores["alerta"], hover_color="#B91C1C",
                      command=_ok).pack(side="left", padx=6)


# ─────────────────────────────────────────────────────────────────────────────
# Modal de formulário
# ─────────────────────────────────────────────────────────────────────────────

class _FormMetaModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, meta: Meta | None = None):
        super().__init__(parent)
        from views.metas.metas_model import salvar_meta
        self._salvar_meta = salvar_meta
        self._on_salvo = on_salvo
        self._meta = meta
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        self.title("Editar meta" if meta else "Nova meta")
        self.geometry("420x380")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(80, self._centralizar)
        self._build()
        if meta:
            self._preencher()

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, txt):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _build(self):
        cores = self._cores
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        self._label(frame, "Nome da meta *")
        self._e_nome = ctk.CTkEntry(frame, width=370)
        self._e_nome.pack(fill="x", pady=(2, 10))

        self._label(frame, "Valor alvo (R$) *")
        self._e_alvo = ctk.CTkEntry(frame, width=370, placeholder_text="0,00")
        self._e_alvo.pack(fill="x", pady=(2, 10))

        self._label(frame, "Valor já acumulado (R$)")
        self._e_atual = ctk.CTkEntry(frame, width=370, placeholder_text="0,00")
        self._e_atual.pack(fill="x", pady=(2, 10))

        self._label(frame, "Prazo (DD/MM/AAAA) — opcional")
        self._e_prazo = ctk.CTkEntry(frame, width=370, placeholder_text="DD/MM/AAAA")
        self._e_prazo.pack(fill="x", pady=(2, 10))

        self._label(frame, "Descrição")
        self._e_desc = ctk.CTkEntry(frame, width=370)
        self._e_desc.pack(fill="x", pady=(2, 10))

        self._lbl_erro = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                      font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w")

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(pady=8)
        ctk.CTkButton(btns, text="Cancelar", width=120,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Salvar", width=120,
                      command=self._salvar).pack(side="left", padx=6)

    def _preencher(self):
        m = self._meta
        self._e_nome.insert(0, m.nome)
        self._e_alvo.insert(0, f"{m.valor_alvo:.2f}".replace(".", ","))
        self._e_atual.insert(0, f"{m.valor_atual:.2f}".replace(".", ","))
        if m.prazo:
            from datetime import date
            try:
                d = date.fromisoformat(m.prazo)
                self._e_prazo.insert(0, d.strftime("%d/%m/%Y"))
            except Exception:
                self._e_prazo.insert(0, m.prazo)
        self._e_desc.insert(0, m.descricao)

    def _salvar(self):
        from config import parsear_data
        nome = self._e_nome.get().strip()
        if not nome:
            self._lbl_erro.configure(text="Informe o nome da meta.")
            return
        try:
            alvo = float(self._e_alvo.get().replace(".", "").replace(",", ".") or 0)
            if alvo <= 0:
                raise ValueError
        except ValueError:
            self._lbl_erro.configure(text="Informe um valor alvo maior que zero.")
            return
        try:
            atual = float(self._e_atual.get().replace(".", "").replace(",", ".") or 0)
        except ValueError:
            atual = 0.0

        prazo_br  = self._e_prazo.get().strip()
        prazo_iso = parsear_data(prazo_br) if prazo_br else None

        dados = {
            "nome": nome, "valor_alvo": alvo, "valor_atual": atual,
            "prazo": prazo_iso, "descricao": self._e_desc.get().strip(),
        }
        self._salvar_meta(dados, id=self._meta.id if self._meta else None)
        self.destroy()
        self._on_salvo()
