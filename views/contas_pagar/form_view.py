"""
form_view.py — Modal de criação e edição de Conta a Pagar.
Suporta lançamento opcional com cartão de crédito (compras_cartao + parcelas_cartao).
"""

from __future__ import annotations
import customtkinter as ctk
from datetime import date
from config import get_tema, formatar_data_exibicao, parsear_data, formatar_moeda, mascara_moeda, NOMES_MESES
from database import obter_configuracao
from views.contas_pagar.conta_model import (
    ContaPagar, PlanoContaItem,
    listar_plano_contas, salvar_conta, atualizar_conta, atualizar_recorrentes_futuros,
)


class ContaPagarFormModal(ctk.CTkToplevel):
    """
    Modal para criar ou editar uma Conta a Pagar.
    on_salvo(msg) é chamado após salvar com sucesso.
    """

    def __init__(self, parent, on_salvo, conta: ContaPagar | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._conta = conta
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self._planos: list[PlanoContaItem] = listar_plano_contas(apenas_ativas=True)
        self._cartoes_lista = []

        titulo = "Editar Despesa" if conta else "Nova Despesa"
        self.title(f"Serenus — {titulo}")
        self.geometry("480x680")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_ui()
        if conta:
            self._preencher(conta)
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        master = self.master
        x = master.winfo_rootx() + (master.winfo_width()  - self.winfo_width())  // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        cores = self._cores
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=16)
        self._frame = frame

        # Conta (plano_contas)
        self._label(frame, "Conta *")
        nomes = [p.nome for p in self._planos]
        self._combo_conta = ctk.CTkComboBox(
            frame, values=nomes, state="readonly",
            command=self._on_conta_selecionada, width=430
        )
        self._combo_conta.set(nomes[0] if nomes else "")
        self._combo_conta.pack(fill="x", pady=(2, 12))

        # Descrição
        self._label(frame, "Descrição")
        self._entry_desc = ctk.CTkEntry(frame, placeholder_text="Descrição opcional", width=430)
        self._entry_desc.pack(fill="x", pady=(2, 12))

        # Valor
        self._label(frame, "Valor (R$) *")
        self._entry_valor = ctk.CTkEntry(frame, width=430)
        self._entry_valor.insert(0, "0,00")
        self._entry_valor.pack(fill="x", pady=(2, 2))
        self._entry_valor.bind("<KeyRelease>", lambda e: (
            mascara_moeda(self._entry_valor),
            self._atualizar_preview_cartao(),
        ))
        self._lbl_err_valor = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                           font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_valor.pack(anchor="w", pady=(0, 8))

        # Data de vencimento
        self._label(frame, "Data de Vencimento * (DD/MM/AAAA)")
        self._entry_venc = ctk.CTkEntry(frame, placeholder_text="DD/MM/AAAA", width=430)
        self._entry_venc.insert(0, date.today().strftime("%d/%m/%Y"))
        self._entry_venc.pack(fill="x", pady=(2, 2))
        self._entry_venc.bind("<KeyRelease>", lambda e: (
            self._mascara_data(self._entry_venc),
            self._atualizar_preview_cartao(),
        ))
        self._lbl_err_venc = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                          font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_venc.pack(anchor="w", pady=(0, 8))

        # Data de pagamento
        self._label(frame, "Data de Pagamento (DD/MM/AAAA) — opcional")
        self._entry_pag = ctk.CTkEntry(frame, placeholder_text="Deixe vazio se ainda não pago", width=430)
        self._entry_pag.pack(fill="x", pady=(2, 2))
        self._entry_pag.bind("<KeyRelease>", lambda e: self._mascara_data(self._entry_pag))
        self._lbl_err_pag = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                         font=ctk.CTkFont(size=10), anchor="w")
        self._lbl_err_pag.pack(anchor="w", pady=(0, 8))

        # Recorrente — num frame próprio para poder ser ocultado
        self._frame_recorrente_check = ctk.CTkFrame(frame, fg_color="transparent")
        self._frame_recorrente_check.pack(anchor="w", pady=(0, 4))

        self._recorrente_var = ctk.BooleanVar(value=False)
        self._check_recorrente = ctk.CTkCheckBox(
            self._frame_recorrente_check, text="Despesa recorrente",
            variable=self._recorrente_var,
            command=self._on_recorrente_toggle,
        )
        self._check_recorrente.pack(anchor="w")

        # Quantos meses (aparece só se recorrente)
        self._frame_meses = ctk.CTkFrame(frame, fg_color="transparent")
        self._label(self._frame_meses, "Lançar para quantos meses?")
        self._spin_meses = ctk.CTkOptionMenu(
            self._frame_meses,
            values=[str(i) for i in range(1, 13)],
        )
        self._spin_meses.set("1")
        self._spin_meses.pack(anchor="w", pady=(2, 0))

        # ── Pagar com cartão ──────────────────────────────────────────
        self._cartao_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame, text="Pagar com cartão de crédito",
            variable=self._cartao_var,
            command=self._on_cartao_toggle,
        ).pack(anchor="w", pady=(0, 4))

        # Seção de cartão (oculta por padrão)
        self._frame_cartao = ctk.CTkFrame(frame, fg_color=cores["card"], corner_radius=8)

        self._label(self._frame_cartao, "Cartão *")
        self._combo_cartao = ctk.CTkComboBox(
            self._frame_cartao, values=["(carregando…)"], state="readonly",
            command=lambda v: self._atualizar_preview_cartao(),
        )
        self._combo_cartao.pack(fill="x", pady=(2, 10), padx=12)

        modo_fr = ctk.CTkFrame(self._frame_cartao, fg_color="transparent")
        modo_fr.pack(fill="x", padx=12, pady=(0, 10))
        self._modo_cartao = ctk.StringVar(value="total")
        ctk.CTkRadioButton(modo_fr, text="Valor total",
                           variable=self._modo_cartao, value="total",
                           command=self._atualizar_preview_cartao).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(modo_fr, text="Valor da parcela",
                           variable=self._modo_cartao, value="parcela",
                           command=self._atualizar_preview_cartao).pack(side="left")

        parc_fr = ctk.CTkFrame(self._frame_cartao, fg_color="transparent")
        parc_fr.pack(fill="x", padx=12, pady=(0, 10))
        self._label(parc_fr, "Nº de parcelas")
        self._combo_parc = ctk.CTkComboBox(
            parc_fr, values=[str(i) for i in range(1, 25)], state="readonly",
            width=100, command=lambda v: self._atualizar_preview_cartao(),
        )
        self._combo_parc.set("1")
        self._combo_parc.pack(anchor="w", pady=(2, 0))

        self._lbl_prev_cartao = ctk.CTkLabel(
            self._frame_cartao, text="", justify="left",
            font=ctk.CTkFont(size=11), text_color=cores["texto_mudo"],
            anchor="w", wraplength=400,
        )
        self._lbl_prev_cartao.pack(fill="x", padx=12, pady=(0, 10))

        # Observação
        self._label(frame, "Observação")
        self._entry_obs = ctk.CTkEntry(frame, placeholder_text="Observação opcional", width=430)
        self._entry_obs.pack(fill="x", pady=(2, 16))

        # Botões
        frame_btns = ctk.CTkFrame(frame, fg_color="transparent")
        frame_btns.pack(fill="x")
        ctk.CTkButton(frame_btns, text="Cancelar", width=120,
                      fg_color="transparent", border_width=1,
                      text_color=cores["texto"],
                      border_color=cores["borda"],
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(frame_btns, text="Salvar", width=120,
                      command=self._salvar).pack(side="right")

        self._on_conta_selecionada(self._combo_conta.get())

    def _label(self, parent, texto: str):
        ctk.CTkLabel(parent, text=texto, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _mascara_data(self, entry: ctk.CTkEntry):
        """Insere barras automaticamente enquanto o usuário digita: DD/MM/AAAA."""
        raw = entry.get()
        digits = "".join(c for c in raw if c.isdigit())[:8]
        if len(digits) > 4:
            masked = digits[:2] + "/" + digits[2:4] + "/" + digits[4:]
        elif len(digits) > 2:
            masked = digits[:2] + "/" + digits[2:]
        else:
            masked = digits
        if masked != raw:
            entry.delete(0, "end")
            entry.insert(0, masked)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _on_conta_selecionada(self, nome: str):
        plano = next((p for p in self._planos if p.nome == nome), None)
        if plano and plano.tipo_custo == "fixo":
            self._recorrente_var.set(True)
            self._on_recorrente_toggle()

    def _on_recorrente_toggle(self):
        if self._recorrente_var.get():
            self._frame_meses.pack(fill="x", pady=(0, 12))
        else:
            self._frame_meses.pack_forget()

    def _on_cartao_toggle(self):
        if self._cartao_var.get():
            from views.cartoes.cartao_model import listar_cartoes, NOMES_BANCOS
            self._cartoes_lista = listar_cartoes(apenas_ativos=True)
            nomes = [f"{c.nome} ({NOMES_BANCOS.get(c.banco, c.banco)})"
                     for c in self._cartoes_lista]
            self._combo_cartao.configure(values=nomes if nomes else ["(nenhum cartão ativo)"])
            if nomes:
                self._combo_cartao.set(nomes[0])
            # Recorrente e cartão são incompatíveis
            self._recorrente_var.set(False)
            self._on_recorrente_toggle()
            self._frame_recorrente_check.pack_forget()
            self._frame_cartao.pack(fill="x", pady=(0, 12),
                                    before=self._entry_obs)
            self._atualizar_preview_cartao()
        else:
            self._frame_cartao.pack_forget()
            self._frame_recorrente_check.pack(anchor="w", pady=(0, 4),
                                              before=self._entry_obs)

    def _atualizar_preview_cartao(self):
        if not self._cartao_var.get():
            return

        val_str = self._entry_valor.get().replace(".", "").replace(",", ".").strip()
        try:
            val = float(val_str)
            if val <= 0:
                raise ValueError
        except ValueError:
            self._lbl_prev_cartao.configure(
                text="Informe o valor para ver o resumo.",
                text_color=self._cores["texto_mudo"],
            )
            return

        n = int(self._combo_parc.get() or "1")
        if self._modo_cartao.get() == "total":
            total = round(val, 2)
            base  = round(total / n, 2)
        else:
            base  = round(val, 2)
            total = round(base * n, 2)
        ultima = round(total - base * (n - 1), 2)

        venc_iso = parsear_data(self._entry_venc.get().strip())
        try:
            d = date.fromisoformat(venc_iso)
            ano_ini, mes_ini = d.year, d.month
        except Exception:
            hoje = date.today()
            ano_ini, mes_ini = hoje.year, hoje.month

        linhas = [f"{n}x de {formatar_moeda(base)} = {formatar_moeda(total)} total"]
        mostrar = min(n, 4)
        for i in range(mostrar):
            mes_r = mes_ini + i
            ano_r = ano_ini + (mes_r - 1) // 12
            mes_r = ((mes_r - 1) % 12) + 1
            v = ultima if i == n - 1 else base
            linhas.append(f"  {i+1}/{n}  {NOMES_MESES[mes_r-1][:3]}/{ano_r}  {formatar_moeda(v)}")
        if n > 4:
            mes_ult = mes_ini + n - 1
            ano_ult = ano_ini + (mes_ult - 1) // 12
            mes_ult = ((mes_ult - 1) % 12) + 1
            linhas.append(f"  … até {NOMES_MESES[mes_ult-1][:3]}/{ano_ult}  {formatar_moeda(ultima)}")

        self._lbl_prev_cartao.configure(
            text="\n".join(linhas),
            text_color=self._cores["texto"],
        )

        # No modo "parcela", o campo Valor (R$) exibe o total calculado
        if self._modo_cartao.get() == "parcela":
            total_fmt = f"{total:.2f}".replace(".", ",")
            self._entry_valor.delete(0, "end")
            self._entry_valor.insert(0, total_fmt)

    def _dialogo_reajuste(self, dados: dict):
        """Pergunta se o reajuste aplica só a esta parcela ou a todas as futuras pendentes."""
        cores = self._cores
        dlg = ctk.CTkToplevel(self)
        dlg.title("Atualizar despesa recorrente")
        dlg.geometry("380x190")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.bind("<Escape>", lambda e: dlg.destroy())

        ctk.CTkLabel(dlg, text="Esta é uma despesa recorrente.",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(dlg, text="Deseja aplicar a alteração em:",
                     text_color=cores["texto_mudo"]).pack()

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=16)

        def _so_esta():
            dlg.destroy()
            atualizar_conta(self._conta.id, dados)
            self.destroy()
            self._on_salvo("Despesa atualizada.")

        def _todas_futuras():
            dlg.destroy()
            n = atualizar_recorrentes_futuros(self._conta.id, dados)
            self.destroy()
            self._on_salvo(f"Reajuste aplicado em {n} despesa{'s' if n != 1 else ''} pendente{'s' if n != 1 else ''}.")

        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=dlg.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Apenas esta", width=110,
                      fg_color="transparent", border_width=1,
                      border_color=cores["primario"], text_color=cores["primario"],
                      command=_so_esta).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Esta e as próximas", width=150,
                      command=_todas_futuras).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _preencher(self, conta: ContaPagar):
        if conta.plano_nome:
            self._combo_conta.set(conta.plano_nome)
        self._entry_desc.insert(0, conta.descricao or "")
        self._entry_valor.insert(0, f"{conta.valor:.2f}".replace(".", ","))
        self._entry_venc.delete(0, "end")
        self._entry_venc.insert(0, formatar_data_exibicao(conta.data_vencimento))
        if conta.data_pagamento:
            self._entry_pag.insert(0, formatar_data_exibicao(conta.data_pagamento))
        self._recorrente_var.set(bool(conta.recorrente))
        self._on_recorrente_toggle()
        self._entry_obs.insert(0, conta.observacao or "")

    def _salvar(self):
        borda = self._cores["borda"]
        self._entry_valor.configure(border_color=borda)
        self._entry_venc.configure(border_color=borda)
        self._entry_pag.configure(border_color=borda)
        self._lbl_err_valor.configure(text="")
        self._lbl_err_venc.configure(text="")
        self._lbl_err_pag.configure(text="")

        erros = []

        nome_plano = self._combo_conta.get().strip()
        plano = next((p for p in self._planos if p.nome == nome_plano), None)
        if not plano:
            erros.append("plano")

        valor_str = self._entry_valor.get().replace(".", "").replace(",", ".").strip()
        try:
            valor = float(valor_str)
            if valor <= 0:
                raise ValueError
        except ValueError:
            self._entry_valor.configure(border_color="#DC2626")
            self._lbl_err_valor.configure(text="Informe um valor maior que zero.")
            erros.append("valor")
            valor = None

        venc_br = self._entry_venc.get().strip()
        venc_iso = parsear_data(venc_br)
        try:
            date.fromisoformat(venc_iso)
        except ValueError:
            self._entry_venc.configure(border_color="#DC2626")
            self._lbl_err_venc.configure(text="Use o formato DD/MM/AAAA.")
            erros.append("venc")
            venc_iso = None

        pag_br  = self._entry_pag.get().strip()
        pag_iso = parsear_data(pag_br) if pag_br else None
        if pag_br and pag_iso:
            try:
                date.fromisoformat(pag_iso)
            except ValueError:
                self._entry_pag.configure(border_color="#DC2626")
                self._lbl_err_pag.configure(text="Use o formato DD/MM/AAAA.")
                erros.append("pag")
                pag_iso = None

        if erros:
            return

        status = "pago" if pag_iso else "pendente"
        dados = {
            "plano_conta_id":  plano.id if plano else None,
            "descricao":       self._entry_desc.get().strip(),
            "valor":           valor,
            "data_vencimento": venc_iso,
            "data_pagamento":  pag_iso,
            "status":          status,
            "recorrente":      self._recorrente_var.get(),
            "observacao":      self._entry_obs.get().strip(),
        }

        if self._conta:
            if self._conta.recorrente:
                self._dialogo_reajuste(dados)
            else:
                atualizar_conta(self._conta.id, dados)
                self.destroy()
                self._on_salvo()
            return

        meses = int(self._spin_meses.get()) if self._recorrente_var.get() else 1
        salvar_conta(dados, meses=meses)

        # Lançamento adicional em cartão
        if self._cartao_var.get() and self._cartoes_lista:
            from views.cartoes.cartao_model import registrar_compra_parcelas, NOMES_BANCOS
            sel = self._combo_cartao.get()
            cartao_obj = next(
                (c for c in self._cartoes_lista
                 if f"{c.nome} ({NOMES_BANCOS.get(c.banco, c.banco)})" == sel),
                None,
            )
            if cartao_obj:
                n = int(self._combo_parc.get() or "1")
                if self._modo_cartao.get() == "total":
                    total_v = valor
                    base_v  = round(total_v / n, 2)
                else:
                    base_v  = valor
                    total_v = round(base_v * n, 2)

                mes_inicio = venc_iso[:7]  # "YYYY-MM"
                registrar_compra_parcelas({
                    "cartao_id":      cartao_obj.id,
                    "descricao":      self._entry_desc.get().strip() or nome_plano,
                    "valor_total":    total_v,
                    "total_parcelas": n,
                    "mes_inicio":     mes_inicio,
                    "categoria":      "",
                    "estabelecimento": "",
                })
                msg = (
                    f"Despesa salva + {n} parcela{'s' if n > 1 else ''} "
                    f"registrada{'s' if n > 1 else ''} no cartão {cartao_obj.nome}."
                )
                self.destroy()
                self._on_salvo(msg)
                return

        self.destroy()
        self._on_salvo()
