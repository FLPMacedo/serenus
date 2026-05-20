"""
form_os.py — Modal de cadastro/edição de Ordem de Serviço.

Layout em seções dentro de um CTkScrollableFrame:
  Cabeçalho (número + status) → Solicitante (nome/setor/ramal) →
  Datas/horas (solicitação + execução) → Descrição do serviço →
  Responsável → Materiais (lista com add/remover) →
  Mão de obra (valor_hora × horas) → Observações → Resumo + botões
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from config import (
    formatar_data_exibicao,
    formatar_moeda,
    get_tema,
    mascara_moeda,
    parsear_data,
)
from database import obter_configuracao
from views.os.os_model import (
    atualizar_os,
    obter_os,
    proximo_numero_os,
    salvar_os,
)
from views.vendas.venda_model import listar_produtos


_STATUS_OPCOES: list[tuple[str, str]] = [
    ("Aberta",         "aberta"),
    ("Em andamento",   "em_andamento"),
    ("Aguard. peça",   "aguardando_peca"),
    ("Concluída",      "concluida"),
    ("Cancelada",      "cancelada"),
]
_STATUS_LABEL_TO_KEY = {lbl: k for lbl, k in _STATUS_OPCOES}
_STATUS_KEY_TO_LABEL = {k: lbl for lbl, k in _STATUS_OPCOES}


def _parse_valor(texto: str) -> float:
    """Converte string monetária BR ('1.234,56') ou simples ('1234.56') em float."""
    s = (texto or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def _parse_horas(texto: str) -> float:
    """Aceita '2', '2.5' ou '2,5'."""
    s = (texto or "").strip().replace(",", ".")
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


class FormOSModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, os_id: int | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._cores    = get_tema(obter_configuracao("tema", "claro"))
        self._os_id    = os_id
        self._produtos = listar_produtos(apenas_ativos=True)
        # Cliente atual selecionado no dropdown (None = sem cliente cadastrado)
        from views.os.cliente_model import listar_clientes
        self._clientes = listar_clientes()
        self._cliente_id_atual: int | None = None
        self._itens: list[dict] = []  # cada dict: produto_id, descricao, quantidade, preco_unit, observacao, _widgets

        self._os_existente = obter_os(os_id) if os_id else None
        titulo = (f"Editar {self._os_existente.numero}"
                  if self._os_existente else "Nova Ordem de Serviço")
        self.title(titulo)
        self.geometry("640x720")
        self.resizable(False, True)
        self.grab_set()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(80, self._centralizar)

        self._build()
        self._preencher_se_edicao()
        self._atualizar_totais()

    # ------------------------------------------------------------------
    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, texto: str):
        ctk.CTkLabel(parent, text=texto, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _divisor(self, parent):
        ctk.CTkFrame(parent, height=1,
                     fg_color=self._cores["borda"]).pack(fill="x", pady=10)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        cores = self._cores
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)
        self._frame = frame

        # --- Cabeçalho: número + status ---
        cab = ctk.CTkFrame(frame, fg_color="transparent")
        cab.pack(fill="x")
        col_num = ctk.CTkFrame(cab, fg_color="transparent")
        col_num.pack(side="left")
        ctk.CTkLabel(col_num, text="Nº da OS",
                     font=ctk.CTkFont(size=11),
                     text_color=cores["texto_mudo"]).pack(anchor="w")
        numero_inicial = (self._os_existente.numero
                          if self._os_existente else proximo_numero_os())
        ctk.CTkLabel(col_num, text=numero_inicial,
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=cores["primario"]).pack(anchor="w")

        col_status = ctk.CTkFrame(cab, fg_color="transparent")
        col_status.pack(side="right")
        ctk.CTkLabel(col_status, text="Status",
                     font=ctk.CTkFont(size=11),
                     text_color=cores["texto_mudo"]).pack(anchor="e")
        self._cb_status = ctk.CTkComboBox(
            col_status, width=170, state="readonly",
            values=[lbl for lbl, _ in _STATUS_OPCOES],
        )
        self._cb_status.set("Aberta")
        self._cb_status.pack(anchor="e", pady=(2, 0))

        self._divisor(frame)

        # --- Cliente cadastrado (opcional) ---
        ctk.CTkLabel(frame, text="Cliente cadastrado",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]).pack(anchor="w")
        row_cli = ctk.CTkFrame(frame, fg_color="transparent")
        row_cli.pack(fill="x", pady=(4, 8))

        opcoes_cli = ["(sem cliente cadastrado)"] + [c.nome for c in self._clientes]
        self._cb_cliente = ctk.CTkComboBox(
            row_cli, values=opcoes_cli, width=320, state="readonly",
            command=lambda _v: self._on_cliente_combo_change(),
        )
        self._cb_cliente.set("(sem cliente cadastrado)")
        self._cb_cliente.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            row_cli, text="+ Novo cliente", width=130, height=28,
            command=self._abrir_form_cliente_novo,
        ).pack(side="left", padx=(0, 6))

        self._btn_editar_cli = ctk.CTkButton(
            row_cli, text="✏ Editar", width=80, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto"],
            command=self._abrir_form_cliente_edicao, state="disabled",
        )
        self._btn_editar_cli.pack(side="left")

        self._divisor(frame)

        # --- Solicitante (texto livre — opcional, retrocompat) ---
        ctk.CTkLabel(frame, text="Solicitante (texto livre, opcional)",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]).pack(anchor="w")
        ctk.CTkLabel(
            frame,
            text="Use se a OS é avulsa ou se ainda não cadastrou o cliente.",
            font=ctk.CTkFont(size=10),
            text_color=cores["texto_mudo"],
        ).pack(anchor="w", pady=(0, 4))
        row_solic = ctk.CTkFrame(frame, fg_color="transparent")
        row_solic.pack(fill="x", pady=(0, 8))

        col1 = ctk.CTkFrame(row_solic, fg_color="transparent")
        col1.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._label(col1, "Nome do contato")
        self._e_solic_nome = ctk.CTkEntry(col1, placeholder_text="Ex.: João da Silva")
        self._e_solic_nome.pack(fill="x", pady=(2, 0))

        col2 = ctk.CTkFrame(row_solic, fg_color="transparent")
        col2.pack(side="left", padx=6)
        self._label(col2, "Setor")
        self._e_solic_setor = ctk.CTkEntry(col2, width=180,
                                            placeholder_text="Ex.: TI")
        self._e_solic_setor.pack(pady=(2, 0))

        col3 = ctk.CTkFrame(row_solic, fg_color="transparent")
        col3.pack(side="left", padx=(6, 0))
        self._label(col3, "Ramal")
        self._e_solic_ramal = ctk.CTkEntry(col3, width=100,
                                            placeholder_text="1234")
        self._e_solic_ramal.pack(pady=(2, 0))

        # --- Datas e horas ---
        ctk.CTkLabel(frame, text="Datas e horários",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]).pack(anchor="w", pady=(4, 0))
        row_data = ctk.CTkFrame(frame, fg_color="transparent")
        row_data.pack(fill="x", pady=(4, 8))

        c_ds = ctk.CTkFrame(row_data, fg_color="transparent")
        c_ds.pack(side="left", padx=(0, 6))
        self._label(c_ds, "Data de solicitação *")
        self._e_data_solic = ctk.CTkEntry(c_ds, width=140,
                                           placeholder_text="DD/MM/AAAA")
        self._e_data_solic.insert(0, date.today().strftime("%d/%m/%Y"))
        self._e_data_solic.pack(pady=(2, 0))

        c_hs = ctk.CTkFrame(row_data, fg_color="transparent")
        c_hs.pack(side="left", padx=6)
        self._label(c_hs, "Hora")
        self._e_hora_solic = ctk.CTkEntry(c_hs, width=80,
                                           placeholder_text="HH:MM")
        self._e_hora_solic.pack(pady=(2, 0))

        c_de = ctk.CTkFrame(row_data, fg_color="transparent")
        c_de.pack(side="left", padx=6)
        self._label(c_de, "Data de execução")
        self._e_data_exec = ctk.CTkEntry(c_de, width=140,
                                          placeholder_text="DD/MM/AAAA")
        self._e_data_exec.pack(pady=(2, 0))

        c_he = ctk.CTkFrame(row_data, fg_color="transparent")
        c_he.pack(side="left", padx=(6, 0))
        self._label(c_he, "Hora")
        self._e_hora_exec = ctk.CTkEntry(c_he, width=80,
                                          placeholder_text="HH:MM")
        self._e_hora_exec.pack(pady=(2, 0))

        # --- Descrição do serviço + Responsável ---
        self._label(frame, "Descrição do serviço")
        self._t_descricao = ctk.CTkTextbox(frame, height=80)
        self._t_descricao.pack(fill="x", pady=(2, 8))

        self._label(frame, "Responsável pela execução")
        self._e_responsavel = ctk.CTkEntry(frame,
                                            placeholder_text="Quem executou")
        self._e_responsavel.pack(fill="x", pady=(2, 8))

        self._divisor(frame)

        # --- Materiais utilizados ---
        hdr_mat = ctk.CTkFrame(frame, fg_color="transparent")
        hdr_mat.pack(fill="x")
        ctk.CTkLabel(
            hdr_mat, text="Materiais utilizados",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"],
        ).pack(side="left")
        ctk.CTkButton(hdr_mat, text="+ Adicionar item", height=28,
                      command=self._add_item_row).pack(side="right")

        self._frame_itens = ctk.CTkFrame(frame, fg_color="transparent")
        self._frame_itens.pack(fill="x", pady=4)

        self._divisor(frame)

        # --- Mão de obra ---
        ctk.CTkLabel(frame, text="Mão de obra",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=cores["texto"]).pack(anchor="w")
        row_mo = ctk.CTkFrame(frame, fg_color="transparent")
        row_mo.pack(fill="x", pady=(4, 6))

        c_vh = ctk.CTkFrame(row_mo, fg_color="transparent")
        c_vh.pack(side="left", padx=(0, 8))
        self._label(c_vh, "Valor por hora (R$)")
        self._e_valor_hora = ctk.CTkEntry(c_vh, width=130,
                                           placeholder_text="0,00")
        self._e_valor_hora.insert(0, "0,00")
        self._e_valor_hora.pack(pady=(2, 0))
        self._e_valor_hora.bind("<KeyRelease>", lambda _e: (
            mascara_moeda(self._e_valor_hora), self._atualizar_totais(),
        ))

        c_hh = ctk.CTkFrame(row_mo, fg_color="transparent")
        c_hh.pack(side="left", padx=8)
        self._label(c_hh, "Horas trabalhadas")
        self._e_horas = ctk.CTkEntry(c_hh, width=100,
                                      placeholder_text="0 (aceita 2,5)")
        self._e_horas.pack(pady=(2, 0))
        self._e_horas.bind("<KeyRelease>", lambda _e: self._atualizar_totais())

        # --- Observações gerais ---
        self._label(frame, "Observações gerais")
        self._t_observacoes = ctk.CTkTextbox(frame, height=70)
        self._t_observacoes.pack(fill="x", pady=(2, 8))

        # --- Resumo de totais ---
        self._divisor(frame)
        resumo = ctk.CTkFrame(frame, fg_color=cores["fundo"], corner_radius=8)
        resumo.pack(fill="x", pady=4)
        self._lbl_total_mat = ctk.CTkLabel(
            resumo, text="Materiais: R$ 0,00",
            font=ctk.CTkFont(size=12), text_color=cores["texto"], anchor="w",
        )
        self._lbl_total_mat.pack(anchor="w", padx=12, pady=(8, 2))
        self._lbl_total_mo = ctk.CTkLabel(
            resumo, text="Mão de obra: R$ 0,00",
            font=ctk.CTkFont(size=12), text_color=cores["texto"], anchor="w",
        )
        self._lbl_total_mo.pack(anchor="w", padx=12, pady=2)
        self._lbl_total_final = ctk.CTkLabel(
            resumo, text="Total: R$ 0,00",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=cores["primario"], anchor="e",
        )
        self._lbl_total_final.pack(anchor="e", padx=12, pady=(2, 8))

        # --- Erro + Botões ---
        self._lbl_erro = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                       font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w", pady=(4, 0))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Cancelar", width=130,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=self.destroy).pack(side="left", padx=6)
        texto_salvar = "Atualizar" if self._os_existente else "Registrar OS"
        ctk.CTkButton(btns, text=texto_salvar, width=160,
                      command=self._salvar).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    # Itens (materiais)
    # ------------------------------------------------------------------

    def _add_item_row(self, prefill: dict | None = None):
        cores = self._cores
        dados = {
            "produto_id": prefill.get("produto_id") if prefill else None,
            "descricao":  prefill.get("descricao", "") if prefill else "",
            "quantidade": prefill.get("quantidade", 1.0) if prefill else 1.0,
            "preco_unit": prefill.get("preco_unit", 0.0) if prefill else 0.0,
            "observacao": prefill.get("observacao", "") if prefill else "",
        }
        self._itens.append(dados)

        row = ctk.CTkFrame(self._frame_itens, fg_color=cores["fundo"],
                            corner_radius=6)
        row.pack(fill="x", pady=2)

        nomes = ["(livre)"] + [f"{p.nome} [{p.tipo}]" for p in self._produtos]
        combo = ctk.CTkComboBox(
            row, values=nomes, width=200, state="readonly",
            command=lambda v, d=dados: self._on_produto_selecionado(v, d),
        )
        combo.set("(livre)")
        combo.pack(side="left", padx=(6, 4), pady=6)

        e_desc = ctk.CTkEntry(row, width=140, placeholder_text="Descrição")
        e_desc.insert(0, dados["descricao"])
        e_desc.pack(side="left", padx=4)
        e_desc.bind("<KeyRelease>",
                    lambda _e, d=dados, w=e_desc: d.update(descricao=w.get()))

        e_qtd = ctk.CTkEntry(row, width=50, placeholder_text="Qtd")
        e_qtd.insert(0, f"{dados['quantidade']:g}".replace(".", ","))
        e_qtd.pack(side="left", padx=4)

        e_preco = ctk.CTkEntry(row, width=90, placeholder_text="Preço")
        e_preco.insert(0, f"{dados['preco_unit']:.2f}".replace(".", ","))
        e_preco.pack(side="left", padx=4)
        e_preco.bind("<KeyRelease>", lambda _e: (
            mascara_moeda(e_preco), self._atualizar_totais(),
        ))
        e_qtd.bind("<KeyRelease>", lambda _e: self._atualizar_totais())

        e_obs = ctk.CTkEntry(row, width=120, placeholder_text="Observação")
        e_obs.insert(0, dados["observacao"])
        e_obs.pack(side="left", padx=4)
        e_obs.bind("<KeyRelease>",
                    lambda _e, d=dados, w=e_obs: d.update(observacao=w.get()))

        ctk.CTkButton(
            row, text="✕", width=28, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["alerta"], text_color=cores["alerta"],
            font=ctk.CTkFont(size=11),
            command=lambda r=row, d=dados: self._remover_item(r, d),
        ).pack(side="left", padx=(4, 6))

        dados["_widgets"] = (combo, e_desc, e_qtd, e_preco, e_obs)

        # Se prefill veio com produto_id, marca o combo
        if prefill and prefill.get("produto_id"):
            for p in self._produtos:
                if p.id == prefill["produto_id"]:
                    combo.set(f"{p.nome} [{p.tipo}]")
                    break

    def _on_produto_selecionado(self, valor: str, dados: dict):
        prod = next(
            (p for p in self._produtos if f"{p.nome} [{p.tipo}]" == valor),
            None,
        )
        combo, e_desc, e_qtd, e_preco, e_obs = dados["_widgets"]
        if prod:
            dados["produto_id"] = prod.id
            dados["descricao"]  = prod.nome
            e_desc.delete(0, "end")
            e_desc.insert(0, prod.nome)
            e_preco.delete(0, "end")
            e_preco.insert(0, f"{prod.preco:.2f}".replace(".", ","))
        else:
            dados["produto_id"] = None
        self._atualizar_totais()

    def _remover_item(self, row, dados):
        if dados in self._itens:
            self._itens.remove(dados)
        row.destroy()
        self._atualizar_totais()

    # ------------------------------------------------------------------
    # Cálculo de totais em tempo real
    # ------------------------------------------------------------------

    def _atualizar_totais(self):
        total_mat = 0.0
        for d in self._itens:
            try:
                _, _, e_qtd, e_preco, _ = d["_widgets"]
                qtd   = _parse_horas(e_qtd.get())
                preco = _parse_valor(e_preco.get())
                total_mat += qtd * preco
            except Exception:
                pass

        valor_hora = _parse_valor(self._e_valor_hora.get())
        horas      = _parse_horas(self._e_horas.get())
        valor_mo   = round(valor_hora * horas, 2)
        total      = round(total_mat + valor_mo, 2)

        self._lbl_total_mat.configure(
            text=f"Materiais: {formatar_moeda(round(total_mat, 2))}")
        self._lbl_total_mo.configure(
            text=f"Mão de obra: {formatar_moeda(valor_mo)}  "
                 f"({horas:g}h × {formatar_moeda(valor_hora)})")
        self._lbl_total_final.configure(
            text=f"Total: {formatar_moeda(total)}")

    # ------------------------------------------------------------------
    # Cliente — handlers do combo + botões "Novo" / "Editar"
    # ------------------------------------------------------------------

    def _on_cliente_combo_change(self):
        nome = self._cb_cliente.get()
        if nome == "(sem cliente cadastrado)":
            self._cliente_id_atual = None
            self._btn_editar_cli.configure(state="disabled")
            return
        c = next((cl for cl in self._clientes if cl.nome == nome), None)
        self._cliente_id_atual = c.id if c else None
        self._btn_editar_cli.configure(
            state="normal" if c else "disabled"
        )

    def _abrir_form_cliente_novo(self):
        from views.os.form_cliente import FormClienteModal
        FormClienteModal(self, on_salvo=self._on_cliente_salvo)

    def _abrir_form_cliente_edicao(self):
        from views.os.cliente_model import obter_cliente
        from views.os.form_cliente import FormClienteModal
        if self._cliente_id_atual is None:
            return
        c = obter_cliente(self._cliente_id_atual)
        if c is None:
            return
        FormClienteModal(self, on_salvo=self._on_cliente_salvo, cliente=c)

    def _on_cliente_salvo(self, cid: int):
        """Callback: recarrega lista de clientes e seleciona o que acabou de
        ser criado/editado."""
        from views.os.cliente_model import listar_clientes
        self._clientes = listar_clientes()
        novos = ["(sem cliente cadastrado)"] + [c.nome for c in self._clientes]
        self._cb_cliente.configure(values=novos)
        c = next((cl for cl in self._clientes if cl.id == cid), None)
        if c:
            self._cb_cliente.set(c.nome)
            self._cliente_id_atual = cid
            self._btn_editar_cli.configure(state="normal")

    # ------------------------------------------------------------------
    # Pré-preenchimento na edição
    # ------------------------------------------------------------------

    def _preencher_se_edicao(self):
        o = self._os_existente
        if o is None:
            return

        self._cb_status.set(_STATUS_KEY_TO_LABEL.get(o.status, "Aberta"))

        # Cliente (se vinculado)
        if o.cliente_id is not None:
            c = next((cl for cl in self._clientes if cl.id == o.cliente_id), None)
            if c:
                self._cb_cliente.set(c.nome)
                self._cliente_id_atual = c.id
                self._btn_editar_cli.configure(state="normal")

        self._e_solic_nome.insert(0,  o.solicitante_nome)
        self._e_solic_setor.insert(0, o.solicitante_setor)
        self._e_solic_ramal.insert(0, o.solicitante_ramal)

        self._e_data_solic.delete(0, "end")
        self._e_data_solic.insert(0, formatar_data_exibicao(o.data_solicitacao))
        self._e_hora_solic.insert(0, o.hora_solicitacao)
        if o.data_execucao:
            self._e_data_exec.insert(0, formatar_data_exibicao(o.data_execucao))
        self._e_hora_exec.insert(0, o.hora_execucao)

        self._t_descricao.insert("1.0", o.descricao_servico)
        self._e_responsavel.insert(0, o.responsavel)
        self._t_observacoes.insert("1.0", o.observacoes)

        self._e_valor_hora.delete(0, "end")
        self._e_valor_hora.insert(0, f"{o.valor_hora:.2f}".replace(".", ","))
        self._e_horas.insert(0, f"{o.horas_trabalhadas:g}".replace(".", ","))

        for it in o.itens:
            self._add_item_row({
                "produto_id": it.produto_id,
                "descricao":  it.descricao,
                "quantidade": it.quantidade,
                "preco_unit": it.preco_unit,
                "observacao": it.observacao,
            })

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def _salvar(self):
        self._lbl_erro.configure(text="")

        nome_solic = self._e_solic_nome.get().strip()
        # Aceita cliente cadastrado OU solicitante texto-livre. Tem que ter algo.
        if not self._cliente_id_atual and not nome_solic:
            self._lbl_erro.configure(
                text="Selecione um cliente cadastrado ou informe o nome do solicitante."
            )
            return

        # Valida valor_hora / horas trabalhadas (defesa em profundidade — model
        # também rejeita, mas mostrar no form é melhor UX que crash em runtime)
        vh = _parse_valor(self._e_valor_hora.get())
        if vh < 0:
            self._lbl_erro.configure(text="Valor por hora não pode ser negativo.")
            return
        ht = _parse_horas(self._e_horas.get())
        if ht < 0:
            self._lbl_erro.configure(text="Horas trabalhadas não pode ser negativo.")
            return

        data_iso = parsear_data(self._e_data_solic.get().strip())
        if not data_iso:
            self._lbl_erro.configure(
                text="Data de solicitação inválida (use DD/MM/AAAA).")
            return

        data_exec_iso = None
        if self._e_data_exec.get().strip():
            data_exec_iso = parsear_data(self._e_data_exec.get().strip())
            if not data_exec_iso:
                self._lbl_erro.configure(
                    text="Data de execução inválida (use DD/MM/AAAA).")
                return

        # Coleta itens válidos (descrição e qtd > 0)
        itens_validos: list[dict] = []
        for d in self._itens:
            try:
                _, e_desc, e_qtd, e_preco, e_obs = d["_widgets"]
                descricao = e_desc.get().strip() or d.get("descricao", "")
                qtd   = _parse_horas(e_qtd.get())
                preco = _parse_valor(e_preco.get())
                if not descricao or qtd <= 0:
                    continue
                itens_validos.append({
                    "produto_id": d.get("produto_id"),
                    "descricao":  descricao,
                    "quantidade": qtd,
                    "preco_unit": preco,
                    "observacao": e_obs.get().strip(),
                })
            except Exception:
                continue

        status_label = self._cb_status.get()
        status_key   = _STATUS_LABEL_TO_KEY.get(status_label, "aberta")

        dados = {
            "cliente_id":        self._cliente_id_atual,
            "solicitante_nome":  nome_solic,
            "solicitante_setor": self._e_solic_setor.get().strip(),
            "solicitante_ramal": self._e_solic_ramal.get().strip(),
            "data_solicitacao":  data_iso,
            "hora_solicitacao":  self._e_hora_solic.get().strip(),
            "data_execucao":     data_exec_iso,
            "hora_execucao":     self._e_hora_exec.get().strip(),
            "descricao_servico": self._t_descricao.get("1.0", "end").strip(),
            "observacoes":       self._t_observacoes.get("1.0", "end").strip(),
            "responsavel":       self._e_responsavel.get().strip(),
            "status":            status_key,
            "valor_hora":        _parse_valor(self._e_valor_hora.get()),
            "horas_trabalhadas": _parse_horas(self._e_horas.get()),
        }

        if self._os_existente:
            atualizar_os(self._os_existente.id, dados, itens_validos)
        else:
            salvar_os(dados, itens_validos)

        self.destroy()
        self._on_salvo()
