"""
ajuda.py — Modo ajuda: banner de dica no topo das telas + tooltips em botões.

Quem usa o app pela primeira vez vê dicas explicando o que cada tela faz e
balõezinhos ao passar o mouse em botões-chave. Quando o usuário já conhece o
sistema, basta desligar em Configurações → Aparência → "Mostrar dicas de uso".

Uso típico:
    from views.widgets.ajuda import banner_ajuda, Tooltip

    banner = banner_ajuda(self, cores,
        "Aqui você acompanha o saldo do mês. Use a busca para filtrar lançamentos.")
    if banner:
        banner.grid(row=1, column=0, sticky="ew", padx=20, pady=(6, 0))

    Tooltip(botao_importar,
        "Importe a fatura do banco em CSV ou XLSX — o sistema detecta as parcelas.")
"""
from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from database import obter_configuracao


_CHAVE = "modo_ajuda"
_PADRAO = "1"   # ligado por padrão


def modo_ajuda_ativo() -> bool:
    """Retorna True se o modo ajuda está habilitado nas configurações."""
    return obter_configuracao(_CHAVE, _PADRAO) == "1"


# ---------------------------------------------------------------------------
# Banner — frase curta exibida no topo de uma tela
# ---------------------------------------------------------------------------

def banner_ajuda(parent,
                 cores: dict,
                 texto: str,
                 *,
                 icone: str = "💡") -> ctk.CTkFrame | None:
    """
    Cria um banner de dica para colocar no topo de uma tela.

    Retorna `None` se o modo ajuda estiver desligado — o caller deve fazer
    `if banner: banner.grid(...)` para evitar reservar espaço quando off.

    Não usa `cores["primario"]` porque queremos que o banner seja
    visualmente distinto do tema (cor informativa fixa em ambos os temas).
    """
    if not modo_ajuda_ativo():
        return None

    bg = "#DBEAFE"   # azul-claro (info)
    fg = "#075985"   # azul escuro (legível em ambos os temas)

    frame = ctk.CTkFrame(parent, fg_color=bg, corner_radius=8)
    ctk.CTkLabel(
        frame, text=f"{icone}  {texto}",
        text_color=fg,
        font=ctk.CTkFont(size=11),
        wraplength=900,
        justify="left",
        anchor="w",
    ).pack(fill="x", padx=12, pady=6)
    return frame


# ---------------------------------------------------------------------------
# Tooltip — balão de ajuda ao passar o mouse
# ---------------------------------------------------------------------------

class Tooltip:
    """
    Tooltip simples para widgets do CustomTkinter / Tkinter.

    Aparece após `delay_ms` ao passar o mouse e some ao sair ou clicar.
    Em modo ajuda desligado, não exibe nada — apenas registra os binds.
    """

    def __init__(self, widget, texto: str, *, delay_ms: int = 500):
        self._widget = widget
        self._texto  = texto
        self._delay  = delay_ms
        self._tip:      tk.Toplevel | None = None
        self._after_id: str | None         = None

        widget.bind("<Enter>",      self._on_enter, add="+")
        widget.bind("<Leave>",      self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _on_enter(self, _evt=None) -> None:
        if not modo_ajuda_ativo():
            return
        self._cancelar_pendente()
        self._after_id = self._widget.after(self._delay, self._mostrar)

    def _on_leave(self, _evt=None) -> None:
        self._cancelar_pendente()
        self._fechar()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _cancelar_pendente(self) -> None:
        if self._after_id is None:
            return
        try:
            self._widget.after_cancel(self._after_id)
        except Exception:
            pass
        self._after_id = None

    def _fechar(self) -> None:
        if self._tip is None:
            return
        try:
            self._tip.destroy()
        except Exception:
            pass
        self._tip = None

    def _mostrar(self) -> None:
        if self._tip is not None:
            return
        if not self._widget.winfo_exists():
            return

        x = self._widget.winfo_rootx() + 14
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4

        tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        try:
            tw.attributes("-topmost", True)
        except Exception:
            pass
        tk.Label(
            tw, text=self._texto,
            bg="#1F2937", fg="#F9FAFB",
            font=("Segoe UI", 9),
            padx=10, pady=5, bd=0,
            justify="left", wraplength=320,
        ).pack()
        self._tip = tw
