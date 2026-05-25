"""
date_picker.py — Mini calendário em popup, 100% stdlib + customtkinter.

Sem dependência externa (tkcalendar não é necessária). Uso:

    from views.widgets.date_picker import DatePickerEntry

    self._dp_exec = DatePickerEntry(parent, width=140)
    self._dp_exec.pack(...)
    self._dp_exec.set("25/05/2026")        # opcional — pré-preenche
    iso = self._dp_exec.get_iso()          # retorna "2026-05-25" ou ""
    br  = self._dp_exec.get()              # retorna "25/05/2026" ou ""

    # Acesso direto ao CTkEntry interno (validação, foco etc.):
    self._dp_exec.entry.configure(border_color="#DC2626")
"""
from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Optional

import customtkinter as ctk
import tkinter as tk


_MESES_PT = [
    "Janeiro", "Fevereiro", "Março",     "Abril",
    "Maio",    "Junho",     "Julho",     "Agosto",
    "Setembro","Outubro",   "Novembro",  "Dezembro",
]
_DIAS_SEM_PT = ["S", "T", "Q", "Q", "S", "S", "D"]   # Seg..Dom


class DatePickerEntry(ctk.CTkFrame):
    """Entry de data DD/MM/AAAA + botão 📅 que abre um mini-calendário."""

    def __init__(self, parent, width: int = 140, placeholder: str = "DD/MM/AAAA",
                 default: Optional[date] = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        # CTkEntry à esquerda
        self.entry = ctk.CTkEntry(self, width=width - 36,
                                  placeholder_text=placeholder)
        self.entry.pack(side="left")

        # Botão 📅 à direita
        ctk.CTkButton(self, text="📅", width=30, height=28,
                      command=self._abrir).pack(side="left", padx=(2, 0))

        if default is not None:
            self.entry.insert(0, default.strftime("%d/%m/%Y"))

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get(self) -> str:
        return self.entry.get().strip()

    def get_iso(self) -> str:
        """Retorna 'YYYY-MM-DD' ou string vazia se inválida/vazia."""
        s = self.get()
        if not s:
            return ""
        try:
            return datetime.strptime(s, "%d/%m/%Y").date().isoformat()
        except ValueError:
            return ""

    def set(self, valor: str | date | None):
        self.entry.delete(0, "end")
        if not valor:
            return
        if isinstance(valor, date):
            valor = valor.strftime("%d/%m/%Y")
        self.entry.insert(0, valor)

    # ------------------------------------------------------------------
    # Popup do calendário
    # ------------------------------------------------------------------

    def _abrir(self):
        # Data inicial: o que está digitado, senão hoje
        try:
            inicial = datetime.strptime(self.get(), "%d/%m/%Y").date()
        except ValueError:
            inicial = date.today()

        pop = ctk.CTkToplevel(self)
        pop.title("Selecionar data")
        pop.geometry("280x300")
        pop.resizable(False, False)
        pop.transient(self.winfo_toplevel())
        pop.grab_set()

        # Posiciona ao lado do botão
        try:
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height() + 4
            pop.geometry(f"+{x}+{y}")
        except Exception:
            pass

        state = {"ano": inicial.year, "mes": inicial.month}

        # Header — navegação ◀  Mês AAAA  ▶
        hdr = ctk.CTkFrame(pop, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(8, 4))

        btn_prev = ctk.CTkButton(hdr, text="◀", width=28, height=28)
        btn_prev.pack(side="left")

        lbl_titulo = ctk.CTkLabel(hdr, text="",
                                  font=ctk.CTkFont(size=13, weight="bold"))
        lbl_titulo.pack(side="left", expand=True)

        btn_next = ctk.CTkButton(hdr, text="▶", width=28, height=28)
        btn_next.pack(side="right")

        # Grid dos dias
        grid = ctk.CTkFrame(pop, fg_color="transparent")
        grid.pack(padx=8, pady=(0, 4))

        # Rodapé — Hoje + Limpar + Cancelar
        rod = ctk.CTkFrame(pop, fg_color="transparent")
        rod.pack(fill="x", padx=8, pady=(4, 8))

        ctk.CTkButton(rod, text="Hoje", width=70, height=26,
                      command=lambda: _escolher(date.today())).pack(side="left")
        ctk.CTkButton(rod, text="Limpar", width=70, height=26,
                      fg_color="transparent", border_width=1,
                      command=lambda: (_escolher(None))).pack(side="left", padx=4)
        ctk.CTkButton(rod, text="Cancelar", width=80, height=26,
                      fg_color="transparent", border_width=1,
                      command=pop.destroy).pack(side="right")

        def _escolher(d: Optional[date]):
            self.entry.delete(0, "end")
            if d is not None:
                self.entry.insert(0, d.strftime("%d/%m/%Y"))
            pop.destroy()

        def _redesenhar():
            for w in grid.winfo_children():
                w.destroy()
            ano, mes = state["ano"], state["mes"]
            lbl_titulo.configure(text=f"{_MESES_PT[mes - 1]} {ano}")

            # Cabeçalho dos dias da semana
            for col, d in enumerate(_DIAS_SEM_PT):
                ctk.CTkLabel(grid, text=d, width=32,
                             font=ctk.CTkFont(size=11, weight="bold")
                             ).grid(row=0, column=col, padx=1, pady=1)

            # Semana começa na Segunda (calendar.Calendar(0))
            cal = calendar.Calendar(firstweekday=0)
            semanas = cal.monthdayscalendar(ano, mes)
            hoje = date.today()
            for r, sem in enumerate(semanas, start=1):
                for c, dia in enumerate(sem):
                    if dia == 0:
                        continue
                    try:
                        d = date(ano, mes, dia)
                    except ValueError:
                        continue
                    eh_hoje = (d == hoje)
                    btn = ctk.CTkButton(
                        grid, text=str(dia), width=32, height=26,
                        fg_color=("#2563EB" if eh_hoje else "transparent"),
                        text_color=("#FFFFFF" if eh_hoje else None),
                        border_width=(0 if eh_hoje else 1),
                        command=lambda dd=d: _escolher(dd),
                    )
                    btn.grid(row=r, column=c, padx=1, pady=1)

        def _prev_mes():
            m, a = state["mes"], state["ano"]
            if m == 1:
                state["mes"], state["ano"] = 12, a - 1
            else:
                state["mes"] = m - 1
            _redesenhar()

        def _next_mes():
            m, a = state["mes"], state["ano"]
            if m == 12:
                state["mes"], state["ano"] = 1, a + 1
            else:
                state["mes"] = m + 1
            _redesenhar()

        btn_prev.configure(command=_prev_mes)
        btn_next.configure(command=_next_mes)
        _redesenhar()
        pop.bind("<Escape>", lambda e: pop.destroy())


def gerar_horarios(passo_min: int = 30) -> list[str]:
    """Lista de horários HH:MM de 00:00 a 23:30 (passo em minutos)."""
    out = []
    total = 24 * 60
    t = 0
    while t < total:
        out.append(f"{t // 60:02d}:{t % 60:02d}")
        t += passo_min
    return out


class TimePickerCombo(ctk.CTkComboBox):
    """ComboBox de horário HH:MM (passo de 30 min por padrão). Editável."""

    def __init__(self, parent, width: int = 90, passo_min: int = 30,
                 default: Optional[str] = None, **kwargs):
        super().__init__(parent, width=width,
                         values=gerar_horarios(passo_min), **kwargs)
        if default:
            self.set(default)
        else:
            self.set("")  # vazio até o usuário escolher
