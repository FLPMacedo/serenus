"""
form_venda.py — Modal para registrar nova venda (à vista ou a prazo).
"""
from __future__ import annotations
from datetime import date
import customtkinter as ctk
from config import get_tema, formatar_moeda, mascara_moeda, parsear_data
from database import obter_configuracao
from views.vendas.venda_model import listar_produtos, salvar_venda


class FormVendaModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo):
        super().__init__(parent)
        self._on_salvo  = on_salvo
        self._cores     = get_tema(obter_configuracao("tema", "claro"))
        self._produtos  = listar_produtos(apenas_ativos=True)
        self._itens: list[dict] = []

        self.title("Nova venda")
        self.geometry("560x640")
        self.resizable(False, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(80, self._centralizar)
        self._build()

    # ------------------------------------------------------------------
    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, txt):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    # ------------------------------------------------------------------
    def _build(self):
        cores = self._cores
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Descrição
        self._label(frame, "Descrição da venda")
        self._e_desc = ctk.CTkEntry(frame, width=510)
        self._e_desc.pack(fill="x", pady=(2, 10))

        # Data
        self._label(frame, "Data da venda *")
        self._e_data = ctk.CTkEntry(frame, width=510,
                                    placeholder_text="DD/MM/AAAA")
        self._e_data.insert(0, date.today().strftime("%d/%m/%Y"))
        self._e_data.pack(fill="x", pady=(2, 10))

        # Tipo de pagamento
        self._label(frame, "Forma de pagamento *")
        self._tipo_var = ctk.StringVar(value="avista")
        row_tp = ctk.CTkFrame(frame, fg_color="transparent")
        row_tp.pack(anchor="w", pady=(2, 10))
        ctk.CTkRadioButton(
            row_tp, text="À vista", variable=self._tipo_var, value="avista",
            command=self._on_tipo_toggle,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            row_tp, text="A prazo", variable=self._tipo_var, value="aprazo",
            command=self._on_tipo_toggle,
        ).pack(side="left")

        # Seção a prazo (oculta por padrão)
        self._frame_aprazo = ctk.CTkFrame(frame, fg_color=cores["fundo"],
                                          corner_radius=8)
        f = self._frame_aprazo
        self._label(f, "Número de parcelas")
        self._e_parcelas = ctk.CTkEntry(f, width=80, placeholder_text="1")
        self._e_parcelas.insert(0, "1")
        self._e_parcelas.pack(anchor="w", pady=(2, 6))
        self._label(f, "Data da 1ª parcela (DD/MM/AAAA)")
        self._e_data_p1 = ctk.CTkEntry(f, width=200,
                                       placeholder_text="DD/MM/AAAA")
        self._e_data_p1.insert(0, date.today().strftime("%d/%m/%Y"))
        self._e_data_p1.pack(anchor="w", pady=(2, 10))

        # Itens
        ctk.CTkFrame(frame, height=1, fg_color=cores["borda"]).pack(
            fill="x", pady=8
        )
        hdr_itens = ctk.CTkFrame(frame, fg_color="transparent")
        hdr_itens.pack(fill="x")
        ctk.CTkLabel(
            hdr_itens, text="Itens",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=cores["texto"],
        ).pack(side="left")
        ctk.CTkButton(
            hdr_itens, text="+ Adicionar item", height=28,
            command=self._add_item_row,
        ).pack(side="right")

        self._frame_itens = ctk.CTkFrame(frame, fg_color="transparent")
        self._frame_itens.pack(fill="x", pady=4)
        self._add_item_row()

        # Desconto
        ctk.CTkFrame(frame, height=1, fg_color=cores["borda"]).pack(
            fill="x", pady=8
        )
        row_desc = ctk.CTkFrame(frame, fg_color="transparent")
        row_desc.pack(fill="x")
        ctk.CTkLabel(row_desc, text="Desconto (R$)",
                     font=ctk.CTkFont(size=12)).pack(side="left")
        self._e_desconto = ctk.CTkEntry(row_desc, width=120,
                                        placeholder_text="0,00")
        self._e_desconto.insert(0, "0,00")
        self._e_desconto.pack(side="left", padx=8)
        self._e_desconto.bind("<KeyRelease>",
                              lambda e: (mascara_moeda(self._e_desconto),
                                         self._atualizar_total()))

        # Total
        self._lbl_total = ctk.CTkLabel(
            frame, text="Total: R$ 0,00",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=cores["primario"],
        )
        self._lbl_total.pack(anchor="e", pady=6)

        # Observação
        self._label(frame, "Observação")
        self._e_obs = ctk.CTkEntry(frame, width=510)
        self._e_obs.pack(fill="x", pady=(2, 10))

        self._lbl_erro = ctk.CTkLabel(frame, text="", text_color="#DC2626",
                                      font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w")

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(pady=8)
        ctk.CTkButton(btns, text="Cancelar", width=130,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Registrar venda", width=150,
                      command=self._salvar).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    def _on_tipo_toggle(self):
        if self._tipo_var.get() == "aprazo":
            self._frame_aprazo.pack(fill="x", pady=(0, 8))
        else:
            self._frame_aprazo.pack_forget()

    def _add_item_row(self):
        cores  = self._cores
        frame  = self._frame_itens
        idx    = len(self._itens)
        dados  = {"produto_id": None, "descricao": "", "quantidade": 1.0,
                  "preco_unit": 0.0}
        self._itens.append(dados)

        row = ctk.CTkFrame(frame, fg_color=cores["fundo"], corner_radius=6)
        row.pack(fill="x", pady=2)

        # Produto (combo)
        nomes_prods = ["(livre)"] + [p.nome for p in self._produtos]
        combo = ctk.CTkComboBox(
            row, values=nomes_prods, width=200,
            command=lambda v, d=dados, i=idx: self._on_produto_selecionado(v, d),
        )
        combo.set("(livre)")
        combo.pack(side="left", padx=(6, 4), pady=6)

        # Descrição
        e_desc = ctk.CTkEntry(row, width=130, placeholder_text="Descrição")
        e_desc.pack(side="left", padx=4)
        e_desc.bind("<KeyRelease>",
                    lambda e, d=dados, w=e_desc: d.update(descricao=w.get()))

        # Quantidade
        e_qtd = ctk.CTkEntry(row, width=50, placeholder_text="Qtd")
        e_qtd.insert(0, "1")
        e_qtd.pack(side="left", padx=4)

        # Preço unit
        e_preco = ctk.CTkEntry(row, width=90, placeholder_text="Preço")
        e_preco.insert(0, "0,00")
        e_preco.pack(side="left", padx=4)
        e_preco.bind("<KeyRelease>", lambda e: (
            mascara_moeda(e_preco), self._atualizar_total()
        ))
        e_qtd.bind("<KeyRelease>", lambda e: self._atualizar_total())

        # Remover
        ctk.CTkButton(
            row, text="✕", width=28, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["alerta"], text_color=cores["alerta"],
            font=ctk.CTkFont(size=11),
            command=lambda r=row, d=dados: self._remover_item(r, d),
        ).pack(side="left", padx=(4, 6))

        dados["_widgets"] = (combo, e_desc, e_qtd, e_preco)

    def _on_produto_selecionado(self, valor: str, dados: dict):
        prod = next((p for p in self._produtos if p.nome == valor), None)
        if prod:
            dados["produto_id"] = prod.id
            dados["descricao"]  = prod.nome
            combo, e_desc, e_qtd, e_preco = dados["_widgets"]
            e_desc.delete(0, "end")
            e_desc.insert(0, prod.nome)
            e_preco.delete(0, "end")
            e_preco.insert(0, f"{prod.preco:.2f}".replace(".", ","))
        else:
            dados["produto_id"] = None
        self._atualizar_total()

    def _remover_item(self, row: ctk.CTkFrame, dados: dict):
        if len(self._itens) <= 1:
            return
        self._itens.remove(dados)
        row.destroy()
        self._atualizar_total()

    def _atualizar_total(self):
        total = 0.0
        for d in self._itens:
            try:
                _, _, e_qtd, e_preco = d["_widgets"]
                qtd   = float(e_qtd.get().replace(",", ".") or 0)
                preco = float(e_preco.get().replace(".", "").replace(",", ".") or 0)
                total += qtd * preco
            except Exception:
                pass
        try:
            desc = float(
                self._e_desconto.get().replace(".", "").replace(",", ".") or 0
            )
        except Exception:
            desc = 0.0
        liquido = max(0.0, total - desc)
        self._lbl_total.configure(
            text=f"Total líquido: {formatar_moeda(liquido)}"
        )

    def _salvar(self):
        self._lbl_erro.configure(text="")

        # Data
        data_br = self._e_data.get().strip()
        data_iso = parsear_data(data_br)
        if not data_iso:
            self._lbl_erro.configure(text="Data inválida (use DD/MM/AAAA).")
            return

        # Itens
        itens_validos = []
        for d in self._itens:
            try:
                _, e_desc, e_qtd, e_preco = d["_widgets"]
                descricao = e_desc.get().strip() or d.get("descricao", "")
                qtd  = float(e_qtd.get().replace(",", ".") or 0)
                preco = float(e_preco.get().replace(".", "").replace(",", ".") or 0)
                if not descricao or qtd <= 0:
                    continue
                itens_validos.append({
                    "produto_id": d.get("produto_id"),
                    "descricao":  descricao,
                    "quantidade": qtd,
                    "preco_unit": preco,
                })
            except Exception:
                continue

        if not itens_validos:
            self._lbl_erro.configure(
                text="Adicione pelo menos um item com descrição e quantidade > 0."
            )
            return

        try:
            desconto = float(
                self._e_desconto.get().replace(".", "").replace(",", ".") or 0
            )
        except Exception:
            desconto = 0.0

        tipo = self._tipo_var.get()
        dados: dict = {
            "descricao":      self._e_desc.get().strip(),
            "data_venda":     data_iso,
            "desconto":       desconto,
            "tipo_pagamento": tipo,
            "observacao":     self._e_obs.get().strip(),
        }

        if tipo == "aprazo":
            try:
                parcelas = int(self._e_parcelas.get().strip() or 1)
                if parcelas < 1:
                    raise ValueError
            except ValueError:
                self._lbl_erro.configure(
                    text="Número de parcelas inválido."
                )
                return
            data_p1 = parsear_data(self._e_data_p1.get().strip())
            if not data_p1:
                self._lbl_erro.configure(
                    text="Data da 1ª parcela inválida."
                )
                return
            dados["parcelas"] = parcelas
            dados["data_primeira_parcela"] = data_p1

        salvar_venda(dados, itens_validos)
        self.destroy()
        self._on_salvo()
