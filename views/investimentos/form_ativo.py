"""
form_ativo.py — Formulário de cadastro de ativo financeiro.
"""
from __future__ import annotations
from typing import Callable, Optional

import customtkinter as ctk
from config import (get_tema, TIPOS_ATIVO, LABEL_TIPO_ATIVO,
                    INDEXADORES_RF, LABEL_INDEXADOR)
from database import obter_configuracao
from views.investimentos.investimento_model import (
    salvar_ativo, listar_contas_investimento, Ativo,
)


class FormAtivoModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo: Callable,
                 ativo: Optional[Ativo] = None):
        super().__init__(parent)
        self._cores    = get_tema(obter_configuracao("tema", "claro"))
        self._on_salvo = on_salvo
        self._ativo    = ativo

        self.title("Editar ativo" if ativo else "Novo ativo")
        self.geometry("460x520")
        self.resizable(False, False)
        self.grab_set()

        self._contas = listar_contas_investimento(apenas_ativas=True)
        self._build_ui()
        if ativo:
            self._preencher(ativo)

    def _label(self, parent, txt: str):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12),
                     text_color=self._cores["texto"]
                     ).pack(anchor="w", padx=20, pady=(8, 0))

    def _build_ui(self):
        cores = self._cores
        ctk.CTkLabel(self, text="📈  Ativo",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=cores["texto"]
                     ).pack(pady=(18, 4), padx=20, anchor="w")

        self._label(self, "Código / Ticker *")
        self._e_codigo = ctk.CTkEntry(self, placeholder_text="Ex: PETR4, HGLG11, CDB-NUBANK-130CDI")
        self._e_codigo.pack(fill="x", padx=20, pady=(2, 0))

        self._label(self, "Nome / Descrição *")
        self._e_nome = ctk.CTkEntry(self, placeholder_text="Ex: Petrobrás PN, CDB Nubank 130% CDI")
        self._e_nome.pack(fill="x", padx=20, pady=(2, 0))

        self._label(self, "Tipo *")
        tipos_labels = [LABEL_TIPO_ATIVO.get(t, t) for t in TIPOS_ATIVO]
        self._combo_tipo = ctk.CTkComboBox(
            self, values=tipos_labels, state="readonly",
            command=self._on_tipo_change,
        )
        self._combo_tipo.set(tipos_labels[0])
        self._combo_tipo.pack(fill="x", padx=20, pady=(2, 0))

        self._label(self, "Conta de investimento")
        nomes_contas = ["(sem conta)"] + [c.nome for c in self._contas]
        self._combo_conta = ctk.CTkComboBox(self, values=nomes_contas, state="readonly")
        self._combo_conta.set(nomes_contas[0])
        self._combo_conta.pack(fill="x", padx=20, pady=(2, 0))

        # Seção renda fixa (visível apenas para CDB, Tesouro, fundo)
        self._frame_rf = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_rf.pack(fill="x")

        ctk.CTkLabel(self._frame_rf, text="Indexador",
                     anchor="w", font=ctk.CTkFont(size=12),
                     text_color=cores["texto"]
                     ).pack(anchor="w", padx=20, pady=(8, 0))
        idx_labels = [LABEL_INDEXADOR.get(i, i) for i in INDEXADORES_RF]
        self._combo_idx = ctk.CTkComboBox(self._frame_rf, values=idx_labels, state="readonly")
        self._combo_idx.set(idx_labels[0])
        self._combo_idx.pack(fill="x", padx=20, pady=(2, 0))

        ctk.CTkLabel(self._frame_rf, text="Taxa contratada (% a.a.)",
                     anchor="w", font=ctk.CTkFont(size=12),
                     text_color=cores["texto"]
                     ).pack(anchor="w", padx=20, pady=(8, 0))
        self._e_taxa = ctk.CTkEntry(self._frame_rf, placeholder_text="Ex: 120  ou  13.5")
        self._e_taxa.pack(fill="x", padx=20, pady=(2, 0))

        ctk.CTkLabel(self._frame_rf, text="Vencimento (DD/MM/AAAA)",
                     anchor="w", font=ctk.CTkFont(size=12),
                     text_color=cores["texto"]
                     ).pack(anchor="w", padx=20, pady=(8, 0))
        self._e_venc = ctk.CTkEntry(self._frame_rf, placeholder_text="DD/MM/AAAA")
        self._e_venc.pack(fill="x", padx=20, pady=(2, 0))

        self._label(self, "Observação")
        self._e_obs = ctk.CTkEntry(self)
        self._e_obs.pack(fill="x", padx=20, pady=(2, 0))

        self._lbl_erro = ctk.CTkLabel(self, text="", text_color=cores["alerta"],
                                       font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w", padx=20, pady=(4, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text="Cancelar", width=110,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Salvar", width=110,
                      command=self._salvar).pack(side="left", padx=6)

        self._on_tipo_change(self._combo_tipo.get())

    def _on_tipo_change(self, _=None):
        tipo_label = self._combo_tipo.get()
        tipo = next((k for k, v in LABEL_TIPO_ATIVO.items() if v == tipo_label), "")
        if tipo in ("cdb", "tesouro", "fundo"):
            self._frame_rf.pack(fill="x", after=self._combo_conta)
        else:
            self._frame_rf.pack_forget()

    def _preencher(self, a: Ativo):
        self._e_codigo.insert(0, a.codigo)
        self._e_nome.insert(0, a.nome)
        tipos_labels = [LABEL_TIPO_ATIVO.get(t, t) for t in TIPOS_ATIVO]
        idx_t = TIPOS_ATIVO.index(a.tipo) if a.tipo in TIPOS_ATIVO else 0
        self._combo_tipo.set(tipos_labels[idx_t])
        self._on_tipo_change()

        nomes_contas = ["(sem conta)"] + [c.nome for c in self._contas]
        if a.conta_investimento_id:
            c = next((x for x in self._contas if x.id == a.conta_investimento_id), None)
            if c:
                self._combo_conta.set(c.nome)
        if a.indexador:
            idx_labels = [LABEL_INDEXADOR.get(i, i) for i in INDEXADORES_RF]
            idx_i = INDEXADORES_RF.index(a.indexador) if a.indexador in INDEXADORES_RF else 0
            self._combo_idx.set(idx_labels[idx_i])
        if a.taxa_contratada is not None:
            self._e_taxa.insert(0, str(a.taxa_contratada))
        if a.vencimento:
            from config import formatar_data_exibicao
            self._e_venc.insert(0, formatar_data_exibicao(a.vencimento))
        self._e_obs.insert(0, a.observacao)

    def _salvar(self):
        codigo = self._e_codigo.get().strip().upper()
        nome   = self._e_nome.get().strip()
        if not codigo:
            self._lbl_erro.configure(text="Código é obrigatório.")
            return
        if not nome:
            self._lbl_erro.configure(text="Nome é obrigatório.")
            return

        tipo_label = self._combo_tipo.get()
        tipo = next((k for k, v in LABEL_TIPO_ATIVO.items() if v == tipo_label), "outro")

        conta_nome = self._combo_conta.get()
        conta_id   = next((c.id for c in self._contas if c.nome == conta_nome), None)

        taxa = None
        venc = None
        indexador = None
        if tipo in ("cdb", "tesouro", "fundo"):
            try:
                taxa = float(self._e_taxa.get().replace(",", ".")) if self._e_taxa.get().strip() else None
            except ValueError:
                self._lbl_erro.configure(text="Taxa inválida.")
                return
            venc_br = self._e_venc.get().strip()
            if venc_br:
                from config import parsear_data
                venc = parsear_data(venc_br) or None
            idx_label = self._combo_idx.get()
            indexador = next((k for k, v in LABEL_INDEXADOR.items() if v == idx_label), None)

        dados = {
            "codigo": codigo, "nome": nome, "tipo": tipo,
            "conta_investimento_id": conta_id,
            "indexador": indexador, "taxa_contratada": taxa,
            "vencimento": venc,
            "observacao": self._e_obs.get().strip(),
        }
        salvar_ativo(dados, id=self._ativo.id if self._ativo else None)
        self.destroy()
        self._on_salvo()
