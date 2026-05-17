"""
plano_view.py — CRUD de Plano de Contas (tipos de despesa).
"""

from __future__ import annotations
import customtkinter as ctk
from config import get_tema, CATEGORIAS_PLANO_CONTAS, LABEL_TIPO_CUSTO
from database import obter_configuracao, restaurar_plano_contas_padrao
from views.contas_pagar.conta_model import (
    PlanoContaItem, listar_plano_contas,
    salvar_plano_conta, alternar_ativa_plano, excluir_plano_conta,
    tem_lancamentos_plano,
)


class PlanoContasView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_banner()
        self._build_tabela()
        self._carregar()

    def _build_banner(self):
        from views.widgets.ajuda import banner_ajuda
        b = banner_ajuda(
            self, self._cores,
            "Aqui ficam as categorias usadas para classificar suas despesas. "
            "Use '↩ Restaurar padrões' para repor as categorias removidas e "
            "'+ Nova conta' para criar categorias personalizadas.",
        )
        if b:
            b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))

    # ------------------------------------------------------------------

    def _build_header(self):
        cores = self._cores
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="📋  Plano de Contas",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=cores["texto"]).grid(row=0, column=0, sticky="w")

        from views.widgets.ajuda import Tooltip
        btn_rest = ctk.CTkButton(
            header, text="↩ Restaurar padrões", height=32,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=12),
            command=self._restaurar_padroes,
        )
        btn_rest.grid(row=0, column=1, padx=(0, 8), sticky="e")
        Tooltip(btn_rest,
                "Recria as categorias padrão que foram excluídas.\n"
                "Suas categorias personalizadas e lançamentos existentes "
                "não são alterados.")

        ctk.CTkButton(header, text="+ Nova conta", height=32,
                      command=self._abrir_form_novo).grid(row=0, column=2, sticky="e")

        # Filtro ativas/inativas
        self._mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            header, text="Mostrar inativas",
            variable=self._mostrar_inativas,
            command=self._carregar,
        ).grid(row=0, column=2, padx=12, sticky="e")

    def _build_tabela(self):
        cores = self._cores
        colunas = [("Nome", 220), ("Tipo", 90), ("Categoria", 140), ("Status", 80), ("Ações", 170)]

        cab = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        cab.grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 0))
        for i, (nome, larg) in enumerate(colunas):
            ctk.CTkLabel(cab, text=nome, width=larg,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(
                row=0, column=i, padx=6, pady=6, sticky="w"
            )

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=3, column=0, sticky="nsew", padx=20, pady=(2, 16))
        self.grid_rowconfigure(3, weight=1)
        self._colunas = colunas

    # ------------------------------------------------------------------

    def _carregar(self):
        apenas_ativas = not self._mostrar_inativas.get()
        planos = listar_plano_contas(apenas_ativas=apenas_ativas)

        for w in self._scroll.winfo_children():
            w.destroy()

        if not planos:
            ctk.CTkLabel(self._scroll, text="Nenhuma conta cadastrada.",
                         text_color=self._cores["texto_mudo"]).pack(pady=24)
            return

        for p in planos:
            self._linha(p)

    def _linha(self, plano: PlanoContaItem):
        cores = self._cores
        bg = cores["card"] if plano.ativa else cores["fundo"]
        alpha = cores["texto"] if plano.ativa else cores["texto_mudo"]

        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=6)
        row.pack(fill="x", pady=2)

        dados = [
            (plano.nome,                                  self._colunas[0][1]),
            (LABEL_TIPO_CUSTO.get(plano.tipo_custo, "—"), self._colunas[1][1]),
            (plano.categoria or "—",                      self._colunas[2][1]),
        ]
        for i, (texto, larg) in enumerate(dados):
            ctk.CTkLabel(row, text=texto, width=larg, anchor="w",
                         text_color=alpha,
                         font=ctk.CTkFont(size=12)).grid(
                row=0, column=i, padx=6, pady=6, sticky="w"
            )

        # Badge de status
        badge_frame = ctk.CTkFrame(row, fg_color="transparent", width=self._colunas[3][1])
        badge_frame.grid(row=0, column=3, padx=6, pady=4, sticky="w")
        badge_frame.grid_propagate(False)
        if plano.ativa:
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

        ctk.CTkButton(
            acoes, text="✏", width=30, height=24,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"],
            text_color=cores["texto"],
            font=ctk.CTkFont(size=11),
            command=lambda p=plano: self._abrir_form_editar(p),
        ).pack(side="left", padx=2)

        toggle_txt = "Desativar" if plano.ativa else "Ativar"
        toggle_cor = cores["atencao"] if plano.ativa else cores["positivo"]
        ctk.CTkButton(
            acoes, text=toggle_txt, width=70, height=24,
            fg_color="transparent", border_width=1,
            border_color=toggle_cor,
            text_color=toggle_cor,
            font=ctk.CTkFont(size=11),
            command=lambda p=plano: self._toggle_ativa(p),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            acoes, text="🗑", width=30, height=24,
            fg_color="transparent", border_width=1,
            border_color=cores["alerta"],
            text_color=cores["alerta"],
            font=ctk.CTkFont(size=11),
            command=lambda p=plano: self._confirmar_excluir(p),
        ).pack(side="left", padx=2)

    # ------------------------------------------------------------------

    def _toggle_ativa(self, plano: PlanoContaItem):
        alternar_ativa_plano(plano.id, not plano.ativa)
        self._carregar()
        acao = "desativada" if plano.ativa else "ativada"
        self._toast(f"Conta \"{plano.nome}\" {acao}.")

    def _confirmar_excluir(self, plano: PlanoContaItem):
        if tem_lancamentos_plano(plano.id):
            dlg = ctk.CTkToplevel(self)
            dlg.title("Exclusão bloqueada")
            dlg.geometry("340x150")
            dlg.grab_set()
            dlg.resizable(False, False)
            ctk.CTkLabel(dlg, text=f'Não é possível excluir "{plano.nome}"',
                         font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 4))
            ctk.CTkLabel(dlg, text="Esta conta possui lançamentos vinculados.\nInative-a em vez de excluir.",
                         text_color=self._cores["texto_mudo"], justify="center").pack()
            ctk.CTkButton(dlg, text="OK", width=100,
                          command=dlg.destroy).pack(pady=12)
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Confirmar exclusão")
        dlg.geometry("320x140")
        dlg.grab_set()
        dlg.resizable(False, False)
        ctk.CTkLabel(dlg, text=f'Excluir "{plano.nome}"?',
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(dlg, text="Esta ação não pode ser desfeita.",
                     text_color=self._cores["texto_mudo"]).pack()
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["borda"],
                      text_color=self._cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Excluir", width=100,
                      fg_color=self._cores["alerta"],
                      command=lambda: self._excluir(plano.id, dlg)).pack(side="left", padx=6)

    def _excluir(self, id: int, dlg):
        dlg.destroy()
        ok, motivo = excluir_plano_conta(id)
        if ok:
            self._carregar()
            self._toast("Conta excluída.")
        else:
            self._toast(motivo, tipo="erro")

    def _restaurar_padroes(self):
        n = restaurar_plano_contas_padrao()
        self._carregar()
        if n == 0:
            self._toast("Todas as contas padrão já estão presentes.", tipo="atencao")
        else:
            self._toast(f"{n} conta{'s' if n != 1 else ''} padrão restaurada{'s' if n != 1 else ''}.")

    def _abrir_form_novo(self):
        _PlanoFormModal(self, on_salvo=lambda: (self._carregar(),
                                                self._toast("Conta salva.")))

    def _abrir_form_editar(self, plano: PlanoContaItem):
        _PlanoFormModal(self, plano=plano,
                        on_salvo=lambda: (self._carregar(),
                                          self._toast("Conta atualizada.")))

    def _toast(self, mensagem: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        toast = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(toast, text=mensagem, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, toast.destroy)


# ---------------------------------------------------------------------------
# Modal de formulário do Plano de Contas
# ---------------------------------------------------------------------------

class _PlanoFormModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, plano: PlanoContaItem | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._plano    = plano
        self._cores    = get_tema(obter_configuracao("tema", "claro"))

        titulo = "Editar Conta" if plano else "Nova Conta"
        self.title(f"Serenus — {titulo}")
        self.geometry("420x300")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self._build_ui()
        if plano:
            self._preencher(plano)
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        master = self.master
        x = master.winfo_rootx() + (master.winfo_width()  - self.winfo_width())  // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        pad = {"padx": 24, "pady": 0}
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=16)

        ctk.CTkLabel(frame, text="Nome *", anchor="w").pack(anchor="w")
        self._entry_nome = ctk.CTkEntry(frame, placeholder_text="Nome da conta")
        self._entry_nome.pack(fill="x", pady=(2, 2))
        self._lbl_err_nome = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                          font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_nome.pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(frame, text="Tipo de custo *", anchor="w").pack(anchor="w")
        self._combo_tipo = ctk.CTkComboBox(frame, values=["fixo", "variavel"], state="readonly")
        self._combo_tipo.set("fixo")
        self._combo_tipo.pack(fill="x", pady=(2, 12))

        ctk.CTkLabel(frame, text="Categoria *", anchor="w").pack(anchor="w")
        self._combo_cat = ctk.CTkComboBox(
            frame, values=CATEGORIAS_PLANO_CONTAS, state="readonly"
        )
        self._combo_cat.set(CATEGORIAS_PLANO_CONTAS[0])
        self._combo_cat.pack(fill="x", pady=(2, 16))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancelar", width=110,
                      fg_color="transparent", border_width=1,
                      text_color=self._cores["texto"],
                      border_color=self._cores["borda"],
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Salvar", width=110,
                      command=self._salvar).pack(side="right")

    def _preencher(self, plano: PlanoContaItem):
        self._entry_nome.insert(0, plano.nome)
        self._combo_tipo.set(plano.tipo_custo)
        self._combo_cat.set(plano.categoria or CATEGORIAS_PLANO_CONTAS[0])

    def _salvar(self):
        self._entry_nome.configure(border_color=self._cores["borda"])
        self._lbl_err_nome.configure(text="")

        nome = self._entry_nome.get().strip()
        if not nome:
            self._entry_nome.configure(border_color="#DC2626")
            self._lbl_err_nome.configure(text="Nome é obrigatório.")
            return
        salvar_plano_conta(
            nome=nome,
            tipo_custo=self._combo_tipo.get(),
            categoria=self._combo_cat.get(),
            id=self._plano.id if self._plano else None,
        )
        self.destroy()
        self._on_salvo()
