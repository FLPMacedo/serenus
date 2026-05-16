"""
config_view.py — Tela de Configurações do Serenus.
Seções: Perfil | Senha de acesso | Zerar sistema.
"""

from __future__ import annotations
import customtkinter as ctk
from config import get_tema
from database import (
    obter_configuracao, salvar_configuracao,
    tem_senha, verificar_senha, salvar_senha, remover_senha,
    zerar_dados,
)
import threading


class ConfiguracaoView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="⚙️  Configurações",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=self._cores["texto"]
                     ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 0))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=12)
        scroll.grid_columnconfigure(0, weight=1)

        self._scroll = scroll
        self._build_perfil()
        self._build_senha()
        self._build_modo_demo()
        self._build_zerar()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _secao(self, titulo: str) -> ctk.CTkFrame:
        cores = self._cores
        card = ctk.CTkFrame(self._scroll, fg_color=cores["card"], corner_radius=12)
        card.pack(fill="x", pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=titulo,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=cores["texto"]
                     ).pack(anchor="w", padx=20, pady=(14, 10))
        sep = ctk.CTkFrame(card, fg_color=cores["borda"], height=1)
        sep.pack(fill="x", padx=20, pady=(0, 12))
        return card

    def _lbl(self, parent, txt: str):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12),
                     text_color=self._cores["texto"]
                     ).pack(anchor="w", padx=20)

    def _toast(self, msg: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        toast = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(toast, text=msg, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, toast.destroy)

    # ------------------------------------------------------------------
    # Seção 1 — Perfil
    # ------------------------------------------------------------------

    def _build_perfil(self):
        card = self._secao("👤  Perfil")

        self._lbl(card, "Nome exibido no sistema")
        self._entry_nome = ctk.CTkEntry(card, placeholder_text="Seu nome")
        self._entry_nome.pack(fill="x", padx=20, pady=(4, 16))
        self._entry_nome.insert(0, obter_configuracao("usuario_nome", ""))

        ctk.CTkButton(card, text="Salvar nome", width=130, height=34,
                      command=self._salvar_nome
                      ).pack(anchor="w", padx=20, pady=(0, 16))

    def _salvar_nome(self):
        nome = self._entry_nome.get().strip()
        if not nome:
            self._toast("O nome não pode estar vazio.", tipo="erro")
            return
        salvar_configuracao("usuario_nome", nome)
        self._toast(f"Nome salvo: {nome}")

    # ------------------------------------------------------------------
    # Seção 2 — Senha de acesso
    # ------------------------------------------------------------------

    def _build_senha(self):
        self._card_senha = self._secao("🔒  Senha de acesso")
        self._render_senha()

    def _render_senha(self):
        """Reconstrói o conteúdo da seção senha conforme estado atual."""
        card = self._card_senha
        # Remove widgets de conteúdo (preserva título + sep)
        widgets = card.pack_slaves()
        for w in widgets[2:]:   # índices 0=título, 1=sep
            w.destroy()

        cores = self._cores
        ativa = tem_senha()

        status_txt = "✅  Senha ativa — exigida ao abrir o Serenus." \
                     if ativa else "⬜  Sem senha — acesso livre."
        status_cor = cores["positivo"] if ativa else cores["texto_mudo"]
        ctk.CTkLabel(card, text=status_txt, text_color=status_cor,
                     font=ctk.CTkFont(size=12)
                     ).pack(anchor="w", padx=20, pady=(0, 12))

        if ativa:
            self._build_form_alterar(card)
        else:
            self._build_form_criar(card)

    def _build_form_criar(self, card):
        self._lbl(card, "Nova senha")
        self._e_nova  = ctk.CTkEntry(card, show="•")
        self._e_nova.pack(fill="x", padx=20, pady=(4, 8))

        self._lbl(card, "Confirmar senha")
        self._e_conf  = ctk.CTkEntry(card, show="•")
        self._e_conf.pack(fill="x", padx=20, pady=(4, 4))

        self._lbl_err_senha = ctk.CTkLabel(card, text="",
                                            text_color=self._cores["alerta"],
                                            font=ctk.CTkFont(size=11))
        self._lbl_err_senha.pack(anchor="w", padx=20)

        ctk.CTkButton(card, text="Criar senha", width=130, height=34,
                      command=self._criar_senha
                      ).pack(anchor="w", padx=20, pady=(8, 16))

    def _build_form_alterar(self, card):
        cores = self._cores

        self._lbl(card, "Senha atual")
        self._e_atual = ctk.CTkEntry(card, show="•")
        self._e_atual.pack(fill="x", padx=20, pady=(4, 8))

        self._lbl(card, "Nova senha  (deixe em branco para remover a senha)")
        self._e_nova  = ctk.CTkEntry(card, show="•")
        self._e_nova.pack(fill="x", padx=20, pady=(4, 8))

        self._lbl(card, "Confirmar nova senha")
        self._e_conf  = ctk.CTkEntry(card, show="•")
        self._e_conf.pack(fill="x", padx=20, pady=(4, 4))

        self._lbl_err_senha = ctk.CTkLabel(card, text="",
                                            text_color=cores["alerta"],
                                            font=ctk.CTkFont(size=11))
        self._lbl_err_senha.pack(anchor="w", padx=20)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(anchor="w", padx=20, pady=(8, 16))

        ctk.CTkButton(btns, text="Salvar alteração", width=140, height=34,
                      command=self._alterar_senha
                      ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btns, text="Remover senha", width=130, height=34,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["alerta"],
                      text_color=self._cores["alerta"],
                      command=self._remover_senha
                      ).pack(side="left")

    def _criar_senha(self):
        nova = self._e_nova.get()
        conf = self._e_conf.get()
        if len(nova) < 4:
            self._lbl_err_senha.configure(text="A senha precisa ter ao menos 4 caracteres.")
            return
        if nova != conf:
            self._lbl_err_senha.configure(text="As senhas não conferem.")
            return
        salvar_senha(nova)
        self._toast("Senha criada com sucesso.")
        self._render_senha()

    def _alterar_senha(self):
        atual = self._e_atual.get()
        nova  = self._e_nova.get()
        conf  = self._e_conf.get()

        if not verificar_senha(atual):
            self._lbl_err_senha.configure(text="Senha atual incorreta.")
            return
        if not nova:
            # Campo em branco = remover senha (com confirmação implícita via senha atual)
            self._confirmar_remover()
            return
        if len(nova) < 4:
            self._lbl_err_senha.configure(text="A nova senha precisa ter ao menos 4 caracteres.")
            return
        if nova != conf:
            self._lbl_err_senha.configure(text="As senhas não conferem.")
            return
        salvar_senha(nova)
        self._toast("Senha alterada com sucesso.")
        self._render_senha()

    def _remover_senha(self):
        atual = self._e_atual.get()
        if not verificar_senha(atual):
            self._lbl_err_senha.configure(text="Senha atual incorreta.")
            return
        self._confirmar_remover()

    def _confirmar_remover(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Remover senha")
        dlg.geometry("340x160")
        dlg.resizable(False, False)
        dlg.grab_set()
        ctk.CTkLabel(dlg, text="Remover proteção por senha?",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 6))
        ctk.CTkLabel(dlg, text="O Serenus ficará acessível sem senha.",
                     text_color=self._cores["texto_mudo"]).pack()
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["borda"],
                      text_color=self._cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Remover", width=100,
                      fg_color=self._cores["alerta"],
                      command=lambda: (remover_senha(), dlg.destroy(),
                                       self._toast("Senha removida."),
                                       self._render_senha())
                      ).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    # Seção 3 — Modo Demonstrativo
    # ------------------------------------------------------------------

    def _build_modo_demo(self):
        from demo_manager import PERFIS_DEMO
        cores = self._cores
        card = self._secao("🎭  Modo Demonstrativo")

        ctk.CTkLabel(
            card,
            text="Preenche o sistema com dados realistas de exemplo:\n"
                 "• 10 anos de lançamentos (5 histórico + 5 projeção)\n"
                 "• Receitas, despesas fixas e variáveis mês a mês\n"
                 "• Cartões com compras parceladas e dívidas ativas\n\n"
                 "⚠️  O sistema será zerado antes de carregar os dados.",
            text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=12),
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        self._lbl(card, "Perfil financeiro")
        nomes_perfis = list(PERFIS_DEMO.values())
        chaves_perfis = list(PERFIS_DEMO.keys())
        self._combo_perfil = ctk.CTkComboBox(
            card, values=nomes_perfis, state="readonly",
        )
        self._combo_perfil.set(nomes_perfis[0])
        self._combo_perfil.pack(fill="x", padx=20, pady=(4, 14))
        self._chaves_perfis = chaves_perfis

        ctk.CTkButton(
            card, text="🎭  Ativar modo demonstrativo", height=36,
            fg_color=cores["primario"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._confirmar_modo_demo,
        ).pack(anchor="w", padx=20, pady=(0, 16))

    def _confirmar_modo_demo(self):
        from demo_manager import PERFIS_DEMO
        cores = self._cores
        perfil_nome = self._combo_perfil.get()
        nomes = list(PERFIS_DEMO.values())
        chaves = list(PERFIS_DEMO.keys())
        perfil_key = chaves[nomes.index(perfil_nome)] if perfil_nome in nomes else "padrao"

        dlg = ctk.CTkToplevel(self)
        dlg.title("Ativar modo demonstrativo")
        dlg.geometry("420x240")
        dlg.resizable(False, False)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="🎭  Carregar dados de demonstração?",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(dlg, text=f"Perfil: {perfil_nome}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=cores["primario"]).pack(pady=(0, 6))
        ctk.CTkLabel(
            dlg,
            text="Todos os dados atuais serão apagados e substituídos\n"
                 "por dados de exemplo com 5 anos de histórico e 5 de projeção.",
            text_color=cores["texto_mudo"],
            justify="center",
        ).pack(pady=(0, 16))

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack()
        ctk.CTkButton(btns, text="Cancelar", width=110,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Ativar demo", width=130,
                      fg_color=cores["primario"],
                      command=lambda: (dlg.destroy(),
                                       self._ativar_demo(perfil_key))
                      ).pack(side="left", padx=6)

    def _ativar_demo(self, perfil: str = "padrao"):
        self._toast("Carregando dados de demonstração…", tipo="atencao")

        def _executar():
            try:
                zerar_dados()
                from demo_manager import popular_modo_demo
                n = popular_modo_demo(perfil)
                self.after(0, lambda: self._toast(
                    f"Modo demo ativado: {n} lançamentos inseridos.", tipo="sucesso"
                ))
            except Exception as exc:
                self.after(0, lambda: self._toast(f"Erro: {exc}", tipo="erro"))

        threading.Thread(target=_executar, daemon=True).start()

    # ------------------------------------------------------------------
    # Seção 4 — Zerar sistema
    # ------------------------------------------------------------------

    def _build_zerar(self):
        cores = self._cores
        card = self._secao("🗑️  Zerar sistema")

        ctk.CTkLabel(
            card,
            text="Apaga todos os dados financeiros:\n"
                 "contas, receitas, cartões, dívidas, lançamentos e backups.\n"
                 "Configurações pessoais (nome, tema, senha) são mantidas.",
            text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=12),
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 14))

        ctk.CTkButton(
            card, text="🗑  Zerar todos os dados", height=36,
            fg_color=cores["alerta"],
            hover_color="#B91C1C",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._confirmar_zerar,
        ).pack(anchor="w", padx=20, pady=(0, 16))

    def _confirmar_zerar(self):
        cores = self._cores

        dlg = ctk.CTkToplevel(self)
        dlg.title("⚠️ Confirmar exclusão total")
        dlg.geometry("400x240")
        dlg.resizable(False, False)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="⚠️  Tem certeza absoluta?",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=cores["alerta"]).pack(pady=(20, 6))

        ctk.CTkLabel(
            dlg,
            text="Esta ação apagará TODOS os seus dados financeiros.\n"
                 "A operação não pode ser desfeita.",
            text_color=cores["texto_mudo"],
            justify="center",
        ).pack(pady=(0, 10))

        ctk.CTkLabel(dlg, text='Digite  CONFIRMAR  para prosseguir:',
                     font=ctk.CTkFont(size=12)).pack()

        entry = ctk.CTkEntry(dlg, width=200, justify="center")
        entry.pack(pady=(6, 14))

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack()

        def _executar():
            if entry.get().strip().upper() != "CONFIRMAR":
                entry.configure(border_color=cores["alerta"])
                return
            dlg.destroy()
            self._zerar()

        ctk.CTkButton(btns, text="Cancelar", width=110,
                      fg_color="transparent", border_width=1,
                      border_color=self._cores["borda"],
                      text_color=self._cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Zerar tudo", width=110,
                      fg_color=cores["alerta"],
                      command=_executar).pack(side="left", padx=6)

    def _zerar(self):
        try:
            zerar_dados()
            self._toast("Sistema zerado. Dados padrão restaurados.", tipo="atencao")
        except Exception as e:
            self._toast(f"Erro ao zerar: {e}", tipo="erro")
