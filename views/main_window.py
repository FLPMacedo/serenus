"""
main_window.py — Janela principal do Serenus.
Sidebar fixa (220 px) + área de conteúdo à direita.
Cada item da sidebar carrega a view correspondente no frame de conteúdo.
"""

import customtkinter as ctk
from config import get_tema, SIDEBAR_WIDTH, MIN_WIDTH, MIN_HEIGHT
from database import obter_configuracao, salvar_configuracao
from _paths import IMAGENS_DIR

_LOGO_PATH = IMAGENS_DIR / "logo.png"


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._tema_nome = obter_configuracao("tema", "claro")
        self._cores = get_tema(self._tema_nome)

        ctk.set_appearance_mode(
            "dark" if self._tema_nome == "escuro" else "light"
        )
        ctk.set_default_color_theme("blue")

        self.title("Serenus")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.geometry(f"{MIN_WIDTH}x{MIN_HEIGHT}")

        self.after(200, self._aplicar_icone)

        self._view_atual = None
        self._botoes_nav: dict[str, ctk.CTkButton] = {}

        self._build_layout()
        self._navegar("dashboard")

    # ------------------------------------------------------------------
    # Ícone da janela
    # ------------------------------------------------------------------

    def _aplicar_icone(self):
        if not _LOGO_PATH.exists():
            return
        try:
            from PIL import Image
            ico_path = _LOGO_PATH.with_suffix(".ico")
            if not ico_path.exists():
                img = Image.open(_LOGO_PATH)
                img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
            self.iconbitmap(str(ico_path))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Layout principal
    # ------------------------------------------------------------------

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._sidebar = ctk.CTkFrame(
            self, width=SIDEBAR_WIDTH, corner_radius=0,
            fg_color=self._cores["sidebar"]
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)
        self._build_sidebar()

        self._content = ctk.CTkFrame(self, corner_radius=0,
                                     fg_color=self._cores["fundo"])
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

    def _build_sidebar(self):
        usuario = obter_configuracao("usuario_nome", "Usuário")
        cores = self._cores

        # Logo + nome
        if _LOGO_PATH.exists():
            try:
                from PIL import Image
                from customtkinter import CTkImage
                _img = Image.open(_LOGO_PATH)
                _w, _h = _img.size
                _logo_w = SIDEBAR_WIDTH - 32   # 16px padding de cada lado
                _logo_h = int(_h * _logo_w / _w)
                _ctk_logo = CTkImage(light_image=_img, dark_image=_img,
                                     size=(_logo_w, _logo_h))
                ctk.CTkLabel(
                    self._sidebar, image=_ctk_logo, text="",
                ).pack(pady=(20, 4), padx=16)
            except Exception:
                ctk.CTkLabel(
                    self._sidebar, text="Serenus",
                    font=ctk.CTkFont(size=20, weight="bold"),
                    text_color=cores["primario"]
                ).pack(pady=(24, 2), padx=16)
        else:
            ctk.CTkLabel(
                self._sidebar, text="Serenus",
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=cores["primario"]
            ).pack(pady=(24, 2), padx=16)
        ctk.CTkLabel(
            self._sidebar, text=usuario,
            font=ctk.CTkFont(size=11),
            text_color=cores["texto_mudo"]
        ).pack(pady=(0, 20), padx=16)

        ctk.CTkFrame(self._sidebar, height=1,
                     fg_color=cores["borda"]).pack(fill="x", padx=12)

        # Itens de navegação
        itens = [
            ("🏠",  "Início",          "dashboard"),
            ("💰",  "Minhas Receitas", "receitas"),
            ("💸",  "Contas a Pagar",  "contas_pagar"),
            ("🛒",  "Vendas",          "vendas"),
            ("🔧",  "Ordens de Serviço", "os"),
            ("💳",  "Cartões",         "cartoes"),
            ("📉",  "Gerenc. Dívidas",  "dividas"),
            ("📋",  "Plano de Contas", "plano_contas"),
            ("📊",  "Visão Financeira", "visao_futura"),
            ("🔄",  "Fluxo de Caixa",  "fluxo_caixa"),
            ("📈",  "Investimentos",   "investimentos"),
            ("🎯",  "Metas",           "metas"),
            ("💾",  "Backup",          "backup"),
            ("⚙️",  "Configurações",   "configuracoes"),
        ]

        frame_nav = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        frame_nav.pack(fill="both", expand=True, pady=8)

        for emoji, label, chave in itens:
            btn = ctk.CTkButton(
                frame_nav,
                text=f"  {emoji}  {label}",
                anchor="w",
                height=38,
                corner_radius=8,
                fg_color="transparent",
                text_color=cores["texto"],
                hover_color=cores["borda"],
                font=ctk.CTkFont(size=13),
                command=lambda c=chave: self._navegar(c),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._botoes_nav[chave] = btn

        # Toggle de tema no rodapé
        ctk.CTkFrame(self._sidebar, height=1,
                     fg_color=cores["borda"]).pack(fill="x", padx=12, side="bottom", pady=(0, 4))
        ctk.CTkButton(
            self._sidebar,
            text="☀️ / 🌙  Alternar tema",
            height=32,
            corner_radius=8,
            fg_color="transparent",
            text_color=cores["texto_mudo"],
            hover_color=cores["borda"],
            font=ctk.CTkFont(size=11),
            command=self._alternar_tema,
        ).pack(side="bottom", fill="x", padx=8, pady=2)

        # Botão de alertas (rodapé, acima do tema)
        self._btn_alertas = ctk.CTkButton(
            self._sidebar,
            text="🔔  Alertas",
            height=32,
            corner_radius=8,
            fg_color="transparent",
            text_color=cores["texto_mudo"],
            hover_color=cores["borda"],
            font=ctk.CTkFont(size=11),
            command=self._abrir_alertas,
        )
        self._btn_alertas.pack(side="bottom", fill="x", padx=8, pady=2)
        self.after(500, self._atualizar_badge_alertas)

    def _marcar_ativo(self, chave: str):
        cores = self._cores
        for k, btn in self._botoes_nav.items():
            if k == chave:
                btn.configure(
                    fg_color=cores["primario"],
                    text_color="#FFFFFF",
                    hover_color=cores["primario"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=cores["texto"],
                    hover_color=cores["borda"],
                )

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def _navegar(self, chave: str):
        if self._view_atual:
            self._view_atual.destroy()
            self._view_atual = None

        self._marcar_ativo(chave)

        view = self._criar_view(chave)
        view.grid(row=0, column=0, sticky="nsew")
        self._view_atual = view

    def _criar_view(self, chave: str) -> ctk.CTkFrame:
        from views.contas_pagar.lista_view import ContasPagarView
        from views.contas_pagar.plano_view import PlanoContasView
        from views.receitas.receita_view import ReceitasView
        from views.visao_futura.visao_futura_view import VisaoFuturaView
        from views.visao_longo_prazo.dividas_view import VisaoLongoPrazoView
        from views.fluxo_caixa.fluxo_view import FluxoCaixaView
        from views.fluxo_caixa.extrato_view import ExtratoCaixaView
        from views.backup.backup_view import BackupView
        from views.cartoes.cartoes_view import CartoesView
        from views.configuracoes.config_view import ConfiguracaoView
        from views.investimentos.carteira_view import InvestimentosView
        from views.metas.metas_view import MetasView
        from views.vendas.vendas_view import VendasView
        from views.os.os_view import OrdensServicoView

        mapa = {
            "dashboard":      lambda p: FluxoCaixaView(p, modo_inicio=True),
            "contas_pagar":   lambda p: ContasPagarView(p),
            "plano_contas":   lambda p: PlanoContasView(p),
            "receitas":       lambda p: ReceitasView(p),
            "visao_futura":   lambda p: VisaoFuturaView(p),
            "dividas":        lambda p: VisaoLongoPrazoView(p),
            "fluxo_caixa":    lambda p: ExtratoCaixaView(p),
            "backup":         lambda p: BackupView(p),
            "cartoes":        lambda p: CartoesView(p),
            "configuracoes":  lambda p: ConfiguracaoView(p),
            "investimentos":  lambda p: InvestimentosView(p),
            "metas":          lambda p: MetasView(p),
            "vendas":         lambda p: VendasView(p),
            "os":             lambda p: OrdensServicoView(p),
        }

        if chave in mapa:
            return mapa[chave](self._content)

        # Placeholder para módulos ainda não implementados
        return self._placeholder(chave)

    def _placeholder(self, chave: str) -> ctk.CTkFrame:
        cores = self._cores
        frame = ctk.CTkFrame(self._content, fg_color=cores["fundo"])
        nomes = {
            "dashboard":     "🏠  Início",
            "receitas":      "💰  Minhas Receitas",
            "visao_futura":  "📊  Visão Futura",
            "fluxo_caixa":   "🔄  Fluxo de Caixa",
            "backup":        "💾  Backup",
            "configuracoes": "⚙️  Configurações",
        }
        ctk.CTkLabel(
            frame,
            text=nomes.get(chave, chave),
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=cores["texto_mudo"],
        ).place(relx=0.5, rely=0.5, anchor="center")
        return frame

    # ------------------------------------------------------------------
    # Alertas
    # ------------------------------------------------------------------

    def _atualizar_badge_alertas(self):
        try:
            from views.alertas.alertas_model import alertas_pendentes
            n = len(alertas_pendentes())
        except Exception:
            n = 0
        cores = self._cores
        if n > 0:
            self._btn_alertas.configure(
                text=f"🔔  Alertas  ({n})",
                text_color="#DC2626",
            )
        else:
            self._btn_alertas.configure(
                text="🔔  Alertas",
                text_color=cores["texto_mudo"],
            )

    def _abrir_alertas(self):
        from views.alertas.alertas_model import alertas_pendentes
        from views.alertas.alertas_view import PainelAlertasModal
        PainelAlertasModal(self, alertas_pendentes())

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------

    def _alternar_tema(self):
        novo = "escuro" if self._tema_nome == "claro" else "claro"
        salvar_configuracao("tema", novo)
        self._tema_nome = novo
        self._cores = get_tema(novo)
        ctk.set_appearance_mode("dark" if novo == "escuro" else "light")
        self._reload_layout()

    def _reload_layout(self):
        for widget in self.winfo_children():
            widget.destroy()
        self._botoes_nav = {}
        self._view_atual = None
        self._build_layout()
        self._navegar("contas_pagar")
