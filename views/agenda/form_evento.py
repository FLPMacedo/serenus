"""
form_evento.py — Modal pra cadastrar/editar compromisso avulso da Agenda.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional

import customtkinter as ctk

from config import formatar_data_exibicao, get_tema
from database import obter_configuracao
from views.agenda.agenda_model import (
    CATEGORIAS_EVENTO,
    EventoAgenda,
    excluir_evento,
    salvar_evento,
)
from views.widgets.date_picker import DatePickerEntry, TimePickerCombo


_CATEGORIA_LABELS = {
    "pessoal":  "Pessoal",
    "trabalho": "Trabalho",
    "saude":    "Saúde",
    "outro":    "Outro",
}
_LABEL_TO_CAT = {v: k for k, v in _CATEGORIA_LABELS.items()}


class EventoFormModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo: Callable[[], None],
                 evento: Optional[EventoAgenda] = None,
                 data_inicial: Optional[date] = None):
        super().__init__(parent)
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self._on_salvo = on_salvo
        self._evento = evento

        titulo = "Editar compromisso" if evento else "Novo compromisso"
        self.title(f"Serenus — {titulo}")
        self.geometry("440x500")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_ui(data_inicial or date.today())
        if evento:
            self._preencher_edicao()

    # ------------------------------------------------------------------

    def _build_ui(self, data_inicial: date):
        cores = self._cores
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(f, text="Título *",
                     text_color=cores["texto"]).pack(anchor="w")
        self._e_titulo = ctk.CTkEntry(f, placeholder_text="Ex: Renovar CNH")
        self._e_titulo.pack(fill="x", pady=(2, 8))

        # Data + Hora
        linha = ctk.CTkFrame(f, fg_color="transparent")
        linha.pack(fill="x", pady=(0, 8))

        c1 = ctk.CTkFrame(linha, fg_color="transparent")
        c1.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(c1, text="Data *", text_color=cores["texto"]).pack(anchor="w")
        self._dp_data = DatePickerEntry(c1, width=160, default=data_inicial)
        self._dp_data.pack(pady=(2, 0))

        c2 = ctk.CTkFrame(linha, fg_color="transparent")
        c2.pack(side="left")
        ctk.CTkLabel(c2, text="Hora (opcional)", text_color=cores["texto"]).pack(anchor="w")
        self._tp_hora = TimePickerCombo(c2, width=110)
        self._tp_hora.pack(pady=(2, 0))

        # Categoria
        ctk.CTkLabel(f, text="Categoria",
                     text_color=cores["texto"]).pack(anchor="w")
        self._cb_categoria = ctk.CTkComboBox(
            f, values=[_CATEGORIA_LABELS[c] for c in CATEGORIAS_EVENTO],
            state="readonly", width=200,
        )
        self._cb_categoria.set(_CATEGORIA_LABELS["pessoal"])
        self._cb_categoria.pack(anchor="w", pady=(2, 8))

        # Descrição
        ctk.CTkLabel(f, text="Descrição (opcional)",
                     text_color=cores["texto"]).pack(anchor="w")
        self._t_descricao = ctk.CTkTextbox(f, height=80)
        self._t_descricao.pack(fill="x", pady=(2, 8))

        # Concluído (só em edição faz sentido)
        self._var_concluido = ctk.BooleanVar(value=False)
        self._chk_concluido = ctk.CTkCheckBox(
            f, text="Marcar como concluído",
            variable=self._var_concluido,
        )
        self._chk_concluido.pack(anchor="w", pady=(0, 8))

        # Erro
        self._lbl_err = ctk.CTkLabel(f, text="", text_color="#DC2626")
        self._lbl_err.pack(anchor="w", pady=(0, 4))

        # Botões
        btns = ctk.CTkFrame(f, fg_color="transparent")
        btns.pack(fill="x", pady=(8, 0))

        if self._evento is not None:
            ctk.CTkButton(btns, text="Excluir", width=100,
                          fg_color=cores["alerta"],
                          command=self._excluir).pack(side="left")

        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="transparent", border_width=1,
                      text_color=cores["texto"],
                      border_color=cores["borda"],
                      command=self.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btns, text="Salvar", width=100,
                      command=self._salvar).pack(side="right")

    def _preencher_edicao(self):
        e = self._evento
        self._e_titulo.insert(0, e.titulo)
        self._dp_data.set(formatar_data_exibicao(e.data))
        if e.hora:
            self._tp_hora.set(e.hora)
        self._cb_categoria.set(_CATEGORIA_LABELS.get(e.categoria, "Pessoal"))
        if e.descricao:
            self._t_descricao.insert("1.0", e.descricao)
        self._var_concluido.set(e.concluido)

    # ------------------------------------------------------------------

    def _excluir(self):
        if not self._evento:
            return
        excluir_evento(self._evento.id)
        self.destroy()
        self._on_salvo()

    def _salvar(self):
        titulo = self._e_titulo.get().strip()
        if not titulo:
            self._lbl_err.configure(text="Informe um título.")
            return

        data_iso = self._dp_data.get_iso()
        if not data_iso:
            self._lbl_err.configure(text="Informe uma data válida (DD/MM/AAAA).")
            return

        hora = self._tp_hora.get().strip()
        if hora:
            # validação leve — aceita HH:MM
            try:
                datetime.strptime(hora, "%H:%M")
            except ValueError:
                self._lbl_err.configure(text="Hora inválida (use HH:MM).")
                return

        categoria_label = self._cb_categoria.get()
        categoria = _LABEL_TO_CAT.get(categoria_label, "pessoal")

        dados = {
            "titulo":    titulo,
            "descricao": self._t_descricao.get("1.0", "end").strip(),
            "data":      data_iso,
            "hora":      hora,
            "categoria": categoria,
            "concluido": self._var_concluido.get(),
        }

        try:
            salvar_evento(dados, id=self._evento.id if self._evento else None)
        except ValueError as ex:
            self._lbl_err.configure(text=str(ex))
            return

        self.destroy()
        self._on_salvo()
