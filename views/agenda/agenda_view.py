"""
agenda_view.py — Agenda do Serenus em duas abas:

  • Mês       — calendário grid 7x6 com pílulas coloridas por tipo
  • Próximos  — lista cronológica dos próximos 30 dias

Itens agregados de: contas a pagar, receitas previstas, OS, eventos avulsos.
Botão "+ Compromisso" abre EventoFormModal pra cadastrar lembrete avulso.
"""
from __future__ import annotations

import calendar as _cal
from datetime import date, datetime, timedelta

import customtkinter as ctk

from config import (
    formatar_data_exibicao,
    formatar_moeda,
    get_tema,
)
from database import obter_configuracao
from views.agenda.agenda_model import (
    COR_DESPESA, COR_EVENTO, COR_OS, COR_RECEITA,
    compromissos_mes,
    obter_evento,
    proximos_dias,
)
from views.agenda.form_evento import EventoFormModal


_MESES_PT = [
    "Janeiro", "Fevereiro", "Março",     "Abril",
    "Maio",    "Junho",     "Julho",     "Agosto",
    "Setembro","Outubro",   "Novembro",  "Dezembro",
]
_DIAS_SEM_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
_TIPOS_LABEL = {
    "despesa": "💸 Despesa",
    "receita": "💰 Receita",
    "os":      "🔧 OS",
    "evento":  "📌 Compromisso",
}


class AgendaView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        hoje = date.today()
        self._mes = hoje.month
        self._ano = hoje.year

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_banner()
        self._build_tabs()

    # ------------------------------------------------------------------

    def _build_header(self):
        cores = self._cores
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        h.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(h, text="📅  Agenda",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=cores["texto"]).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(h, text="+ Compromisso", height=32,
                      command=self._novo_evento).grid(row=0, column=1, sticky="e")

    def _build_banner(self):
        from views.widgets.ajuda import banner_ajuda
        b = banner_ajuda(
            self, self._cores,
            "Veja em um só lugar tudo o que está chegando: vencimentos de "
            "contas, receitas previstas, ordens de serviço agendadas e "
            "seus próprios lembretes. Use '+ Compromisso' pra cadastrar "
            "algo avulso (CNH, reunião, exame...).",
        )
        if b:
            b.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))

    def _build_tabs(self):
        tabs = ctk.CTkTabview(self, fg_color=self._cores["fundo"])
        tabs.grid(row=2, column=0, sticky="nsew", padx=20, pady=(8, 16))

        tabs.add("Mês")
        tabs.add("Próximos")

        self._tab_mes = _AbaMes(tabs.tab("Mês"), cores=self._cores,
                                on_dia_click=self._abrir_dia,
                                on_item_click=self._abrir_item,
                                ano=self._ano, mes=self._mes)
        self._tab_mes.pack(fill="both", expand=True)

        self._tab_prox = _AbaProximos(tabs.tab("Próximos"), cores=self._cores,
                                      on_item_click=self._abrir_item)
        self._tab_prox.pack(fill="both", expand=True)

    # ------------------------------------------------------------------

    def _novo_evento(self, data_inicial=None):
        EventoFormModal(self, on_salvo=self._on_salvo,
                        data_inicial=data_inicial)

    def _on_salvo(self):
        self._tab_mes.recarregar()
        self._tab_prox.recarregar()

    def _abrir_dia(self, d: date):
        # Clicou num dia do grid → abre form novo já com a data preenchida
        self._novo_evento(data_inicial=d)

    def _abrir_item(self, item: dict):
        # Só itens do tipo 'evento' são editáveis aqui — os outros têm
        # módulos próprios. Pra evento, abre o modal de edição.
        if item.get("tipo") != "evento":
            return
        ev = obter_evento(item["ref_id"])
        if ev:
            EventoFormModal(self, on_salvo=self._on_salvo, evento=ev)


# ----------------------------------------------------------------------
# Aba MÊS — grid de calendário
# ----------------------------------------------------------------------

class _AbaMes(ctk.CTkFrame):
    def __init__(self, parent, cores: dict, on_dia_click, on_item_click,
                 ano: int, mes: int):
        super().__init__(parent, fg_color="transparent")
        self._cores = cores
        self._on_dia_click = on_dia_click
        self._on_item_click = on_item_click
        self._ano = ano
        self._mes = mes

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_nav()
        self._grid_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._grid_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        self.recarregar()

    def _build_nav(self):
        cores = self._cores
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        ctk.CTkButton(nav, text="◀", width=32, height=28,
                      command=self._mes_anterior).pack(side="left", padx=(8, 4))
        self._lbl_mes = ctk.CTkLabel(
            nav, text="", width=180,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self._lbl_mes.pack(side="left", padx=8)
        ctk.CTkButton(nav, text="▶", width=32, height=28,
                      command=self._mes_proximo).pack(side="left", padx=4)

        ctk.CTkButton(nav, text="Hoje", width=70, height=28,
                      fg_color="transparent", border_width=1,
                      text_color=cores["texto"],
                      border_color=cores["borda"],
                      command=self._ir_hoje).pack(side="left", padx=(16, 0))

        # Legenda de cores
        leg = ctk.CTkFrame(nav, fg_color="transparent")
        leg.pack(side="right", padx=8)
        for cor, lbl in [(COR_DESPESA, "Despesa"),
                          (COR_RECEITA, "Receita"),
                          (COR_OS,      "OS"),
                          (COR_EVENTO,  "Compromisso")]:
            c = ctk.CTkFrame(leg, fg_color="transparent")
            c.pack(side="left", padx=4)
            ctk.CTkFrame(c, fg_color=cor, width=10, height=10,
                         corner_radius=3).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(c, text=lbl, font=ctk.CTkFont(size=10),
                         text_color=cores["texto_mudo"]).pack(side="left")

    def _mes_anterior(self):
        if self._mes == 1:
            self._mes, self._ano = 12, self._ano - 1
        else:
            self._mes -= 1
        self.recarregar()

    def _mes_proximo(self):
        if self._mes == 12:
            self._mes, self._ano = 1, self._ano + 1
        else:
            self._mes += 1
        self.recarregar()

    def _ir_hoje(self):
        hoje = date.today()
        self._mes, self._ano = hoje.month, hoje.year
        self.recarregar()

    def recarregar(self):
        cores = self._cores
        self._lbl_mes.configure(text=f"{_MESES_PT[self._mes - 1]} {self._ano}")

        for w in self._grid_frame.winfo_children():
            w.destroy()

        itens = compromissos_mes(self._ano, self._mes)
        por_dia: dict[int, list[dict]] = {}
        for it in itens:
            try:
                d = datetime.strptime(it["data"], "%Y-%m-%d").date()
            except ValueError:
                continue
            por_dia.setdefault(d.day, []).append(it)

        # Cabeçalho dos dias da semana
        for c, dia_sem in enumerate(_DIAS_SEM_PT):
            ctk.CTkLabel(self._grid_frame, text=dia_sem,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=cores["texto_mudo"]
                         ).grid(row=0, column=c, padx=2, pady=2, sticky="ew")
            self._grid_frame.grid_columnconfigure(c, weight=1, uniform="dia")

        cal = _cal.Calendar(firstweekday=0)  # 0 = Segunda
        semanas = cal.monthdayscalendar(self._ano, self._mes)
        hoje = date.today()
        for r, sem in enumerate(semanas, start=1):
            for c, dia in enumerate(sem):
                cell = ctk.CTkFrame(self._grid_frame,
                                    fg_color=cores["card"],
                                    corner_radius=6, border_width=1,
                                    border_color=cores["borda"])
                cell.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

                if dia == 0:
                    # Célula vazia (dias do mês anterior/próximo)
                    cell.configure(fg_color="transparent", border_width=0)
                    continue

                try:
                    d_atual = date(self._ano, self._mes, dia)
                except ValueError:
                    continue

                # Header da célula — número do dia (clicável → novo evento)
                eh_hoje = (d_atual == hoje)
                lbl = ctk.CTkLabel(
                    cell, text=str(dia),
                    font=ctk.CTkFont(size=12,
                                     weight="bold" if eh_hoje else "normal"),
                    text_color="#FFFFFF" if eh_hoje else cores["texto"],
                    fg_color="#2563EB" if eh_hoje else "transparent",
                    corner_radius=10, width=22, height=22,
                )
                lbl.pack(anchor="ne", padx=4, pady=2)
                lbl.bind("<Button-1>",
                         lambda e, dd=d_atual: self._on_dia_click(dd))

                # Pílulas dos compromissos (máx 3, depois "+N")
                itens_dia = por_dia.get(dia, [])
                for it in itens_dia[:3]:
                    self._pilula(cell, it)
                if len(itens_dia) > 3:
                    ctk.CTkLabel(
                        cell, text=f"+{len(itens_dia) - 3} mais",
                        font=ctk.CTkFont(size=10, slant="italic"),
                        text_color=cores["texto_mudo"],
                    ).pack(anchor="w", padx=4, pady=(0, 2))

    def _pilula(self, parent, item: dict):
        """Pílula colorida com título curto. Click abre o item (se evento)."""
        cor = item.get("cor", "#888")
        riscar = item.get("concluido")
        titulo = item["titulo"]
        if len(titulo) > 16:
            titulo = titulo[:14] + "…"
        if item.get("hora"):
            titulo = f"{item['hora']} {titulo}"

        pill = ctk.CTkFrame(parent, fg_color=cor, corner_radius=4, height=18)
        pill.pack(fill="x", padx=4, pady=1)
        pill.pack_propagate(False)
        lbl = ctk.CTkLabel(
            pill, text=titulo,
            font=ctk.CTkFont(size=10,
                             overstrike=bool(riscar)),
            text_color="#FFFFFF", anchor="w",
        )
        lbl.pack(fill="x", padx=4)
        # Bind tanto no frame quanto no label (área toda clicável)
        for w in (pill, lbl):
            w.bind("<Button-1>", lambda e, it=item: self._on_item_click(it))


# ----------------------------------------------------------------------
# Aba PRÓXIMOS — lista cronológica
# ----------------------------------------------------------------------

class _AbaProximos(ctk.CTkFrame):
    def __init__(self, parent, cores: dict, on_item_click,
                 num_dias: int = 30):
        super().__init__(parent, fg_color="transparent")
        self._cores = cores
        self._on_item_click = on_item_click
        self._num_dias = num_dias

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_nav()
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        self.recarregar()

    def _build_nav(self):
        cores = self._cores
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(nav, text="Janela:",
                     text_color=cores["texto_mudo"]).pack(side="left", padx=(8, 4))
        self._cb_janela = ctk.CTkComboBox(
            nav, width=140,
            values=["Próximos 7 dias", "Próximos 15 dias",
                    "Próximos 30 dias", "Próximos 60 dias"],
            command=self._on_janela_change,
        )
        self._cb_janela.set("Próximos 30 dias")
        self._cb_janela.pack(side="left", padx=(0, 16))

    def _on_janela_change(self, valor: str):
        mapa = {"Próximos 7 dias": 7, "Próximos 15 dias": 15,
                "Próximos 30 dias": 30, "Próximos 60 dias": 60}
        self._num_dias = mapa.get(valor, 30)
        self.recarregar()

    def recarregar(self):
        cores = self._cores
        for w in self._scroll.winfo_children():
            w.destroy()

        itens = proximos_dias(self._num_dias)
        if not itens:
            ctk.CTkLabel(self._scroll,
                         text="Nada agendado nessa janela. 🎉",
                         text_color=cores["texto_mudo"],
                         font=ctk.CTkFont(size=14)).pack(pady=40)
            return

        # Agrupa por dia preservando ordem
        por_dia: dict[str, list[dict]] = {}
        for it in itens:
            por_dia.setdefault(it["data"], []).append(it)

        hoje_iso = date.today().isoformat()
        amanha_iso = (date.today() + timedelta(days=1)).isoformat()

        for data_iso, lst in por_dia.items():
            # Label do dia
            if data_iso == hoje_iso:
                label = "Hoje"
            elif data_iso == amanha_iso:
                label = "Amanhã"
            else:
                try:
                    d = datetime.strptime(data_iso, "%Y-%m-%d").date()
                    dia_sem = _DIAS_SEM_PT[d.weekday()]
                    label = f"{dia_sem} {d.strftime('%d/%m')}"
                except ValueError:
                    label = data_iso

            cab = ctk.CTkFrame(self._scroll, fg_color="transparent")
            cab.pack(fill="x", pady=(12, 4))
            ctk.CTkLabel(
                cab, text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=cores["texto"],
            ).pack(side="left")
            ctk.CTkFrame(cab, height=1, fg_color=cores["borda"]
                         ).pack(side="left", fill="x", expand=True,
                                padx=(8, 0), pady=8)

            for it in lst:
                self._linha_item(it)

    def _linha_item(self, item: dict):
        cores = self._cores
        riscar = item.get("concluido")
        row = ctk.CTkFrame(self._scroll, fg_color=cores["card"],
                           corner_radius=6)
        row.pack(fill="x", pady=2)

        # Barra colorida lateral
        ctk.CTkFrame(row, fg_color=item.get("cor", "#888"),
                     width=4, corner_radius=2
                     ).pack(side="left", fill="y", padx=(4, 8), pady=4)

        # Hora (se tiver)
        if item.get("hora"):
            ctk.CTkLabel(
                row, text=item["hora"], width=50,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=cores["texto"],
            ).pack(side="left", padx=(0, 8), pady=8)

        # Bloco central — título + subtítulo
        bloco = ctk.CTkFrame(row, fg_color="transparent")
        bloco.pack(side="left", fill="both", expand=True, pady=4)

        ctk.CTkLabel(
            bloco, text=_TIPOS_LABEL.get(item["tipo"], "") + "  " + item["titulo"],
            font=ctk.CTkFont(size=12, weight="bold",
                             overstrike=bool(riscar)),
            text_color=cores["texto"], anchor="w",
        ).pack(fill="x")
        if item.get("subtitulo"):
            ctk.CTkLabel(
                bloco, text=item["subtitulo"],
                font=ctk.CTkFont(size=11),
                text_color=cores["texto_mudo"], anchor="w",
            ).pack(fill="x")

        # Valor à direita (se houver)
        if item.get("valor") is not None:
            cor_v = COR_RECEITA if item["valor"] > 0 else COR_DESPESA
            ctk.CTkLabel(
                row, text=formatar_moeda(item["valor"]),
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=cor_v,
            ).pack(side="right", padx=12, pady=8)

        # Click — chama callback
        for w in (row, bloco):
            w.bind("<Button-1>", lambda e, it=item: self._on_item_click(it))
