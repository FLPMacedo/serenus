"""
form_item.py — Modal de cadastro/edição de item do estoque doméstico.

Layout:
    [Item sugerido]    Combo com autocompletar do catálogo (500 itens)
                       Ao escolher, preenche Nome/Categoria automaticamente
                       e popula as marcas sugeridas pra esse item
    [Nome *]           Editável — pode digitar livremente um item não-catalogado
    [Categoria] [Unidade]
    [Marca]            Combo:
                         · marcas sugeridas pro item (em destaque)
                         · todas as marcas cadastradas (catálogo global)
                         · "(outra)" libera input livre — salva no catálogo
    [Estoque atual] [Estoque mínimo]
    [Observações]
    [Ativo]
"""

from __future__ import annotations

import customtkinter as ctk

from config import get_tema
from database import obter_configuracao
from views.compras_casa.casa_model import ItemEstoque, listar_marcas, salvar_item
from views.compras_casa.catalogo import (
    listar_itens_sugeridos,
    listar_marcas_sugeridas,
)


_OPCAO_OUTRA = "(outra — digitar)"
_OPCAO_SEM_SUGESTAO = "(digitar manualmente)"


def _parse_num(s: str) -> float:
    s = (s or "0").strip().replace(",", ".")
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


class FormItemModal(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, item: ItemEstoque | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._item     = item
        self._cores    = get_tema(obter_configuracao("tema", "claro"))
        # Lookup do catálogo (uma vez)
        self._cat = listar_itens_sugeridos()
        self._cat_por_nome = {i["nome"].lower(): i for i in self._cat}

        self.title("Editar item" if item else "Novo item")
        self.geometry("520x620")
        self.resizable(False, True)
        self.grab_set()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(80, self._centralizar)

        self._build()
        if item:
            self._preencher(item)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, t: str):
        ctk.CTkLabel(parent, text=t, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _build(self):
        cores = self._cores
        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Item sugerido (catálogo) — só aparece em modo NOVO
        if self._item is None:
            self._label(frame, "Item sugerido (catálogo)")
            opcoes = ["— digitar item novo —"] + sorted(i["nome"] for i in self._cat)
            self._cb_sugestao = ctk.CTkComboBox(
                frame, values=opcoes, width=460, state="readonly",
                command=lambda v: self._on_sugestao_selecionada(v),
            )
            self._cb_sugestao.set("— digitar item novo —")
            self._cb_sugestao.pack(fill="x", pady=(2, 8))
            ctk.CTkLabel(
                frame,
                text="Escolha um item do catálogo pra preencher nome, categoria e marcas; ou digite tudo manualmente abaixo.",
                font=ctk.CTkFont(size=10),
                text_color=cores["texto_mudo"], wraplength=460, justify="left",
            ).pack(anchor="w", pady=(0, 8))

        self._label(frame, "Nome *")
        self._e_nome = ctk.CTkEntry(frame, placeholder_text="Ex.: Arroz, Sabão líquido")
        self._e_nome.pack(fill="x", pady=(2, 10))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(0, 10))
        c1 = ctk.CTkFrame(row, fg_color="transparent")
        c1.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._label(c1, "Categoria")
        self._e_categoria = ctk.CTkEntry(c1, placeholder_text="Mercearia / Limpeza / ...")
        self._e_categoria.pack(fill="x", pady=(2, 0))

        c2 = ctk.CTkFrame(row, fg_color="transparent")
        c2.pack(side="left", padx=6)
        self._label(c2, "Unidade")
        self._e_unidade = ctk.CTkEntry(c2, width=120, placeholder_text="kg, un, L...")
        self._e_unidade.pack(pady=(2, 0))

        # Marca — combo + opção "outra"
        self._label(frame, "Marca")
        marcas_opcoes = self._construir_opcoes_marca([])
        self._cb_marca = ctk.CTkComboBox(
            frame, values=marcas_opcoes, width=460,
            command=lambda v: self._on_marca_selecionada(v),
        )
        self._cb_marca.set(marcas_opcoes[0])
        self._cb_marca.pack(fill="x", pady=(2, 2))
        # Input pra "nova marca" — só aparece quando seleciona "(outra)"
        self._e_marca_nova = ctk.CTkEntry(
            frame, placeholder_text="Digite a marca nova (será adicionada ao catálogo)",
        )

        row2 = ctk.CTkFrame(frame, fg_color="transparent")
        row2.pack(fill="x", pady=(8, 10))
        ca = ctk.CTkFrame(row2, fg_color="transparent")
        ca.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._label(ca, "Estoque atual")
        self._e_atual = ctk.CTkEntry(ca, placeholder_text="0")
        self._e_atual.insert(0, "0")
        self._e_atual.pack(fill="x", pady=(2, 0))

        cm = ctk.CTkFrame(row2, fg_color="transparent")
        cm.pack(side="left", expand=True, fill="x", padx=(6, 0))
        self._label(cm, "Estoque mínimo (gera lista quando atual <= mínimo)")
        self._e_minimo = ctk.CTkEntry(cm, placeholder_text="0")
        self._e_minimo.insert(0, "0")
        self._e_minimo.pack(fill="x", pady=(2, 0))

        self._label(frame, "Observações")
        self._t_obs = ctk.CTkTextbox(frame, height=70)
        self._t_obs.pack(fill="x", pady=(2, 8))

        self._var_ativo = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame, text="Ativo (aparece na lista de estoque)",
                        variable=self._var_ativo).pack(anchor="w", pady=4)

        self._lbl_erro = ctk.CTkLabel(frame, text="", text_color=cores["alerta"],
                                       font=ctk.CTkFont(size=11))
        self._lbl_erro.pack(anchor="w", pady=(4, 0))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Cancelar", width=130,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"], text_color=cores["texto"],
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Atualizar" if self._item else "Salvar",
                      width=140, command=self._salvar).pack(side="left", padx=6)

        # Recarrega marcas iniciais (pode incluir catalogo cheio)
        self._refresh_combo_marcas(sugeridas=[])

    # ------------------------------------------------------------------
    # Marcas: opções e mudanças
    # ------------------------------------------------------------------

    def _construir_opcoes_marca(self, sugeridas: list[str]) -> list[str]:
        """Monta a lista de opções do combo:
        '(sem marca)' + sugeridas (★) + todas as marcas cadastradas + '(outra)'."""
        opcoes = ["(sem marca)"]
        # Sugeridas vem com prefixo ★ pra destacar
        for m in sugeridas:
            opcoes.append(f"★ {m}")
        # Marcas globais (sem duplicar as sugeridas)
        ja = {m.lower() for m in sugeridas}
        for m in listar_marcas():
            if m.nome.lower() in ja:
                continue
            opcoes.append(m.nome)
        opcoes.append(_OPCAO_OUTRA)
        return opcoes

    def _refresh_combo_marcas(self, sugeridas: list[str]):
        opcoes = self._construir_opcoes_marca(sugeridas)
        self._cb_marca.configure(values=opcoes)
        # mantém seleção atual se ainda for válida
        atual = self._cb_marca.get()
        if atual not in opcoes:
            self._cb_marca.set(opcoes[0])
        self._e_marca_nova.pack_forget()

    def _on_marca_selecionada(self, valor: str):
        if valor == _OPCAO_OUTRA:
            self._e_marca_nova.pack(fill="x", pady=(0, 8))
            self._e_marca_nova.focus_set()
        else:
            self._e_marca_nova.pack_forget()

    # ------------------------------------------------------------------
    # Item sugerido: preencher nome/categoria/marcas ao selecionar
    # ------------------------------------------------------------------

    def _on_sugestao_selecionada(self, nome: str):
        if nome == "— digitar item novo —":
            self._refresh_combo_marcas([])
            return
        it = self._cat_por_nome.get(nome.lower())
        if not it:
            return
        # Preenche nome e categoria (overwrite se já tinha algo)
        self._e_nome.delete(0, "end")
        self._e_nome.insert(0, it["nome"])
        self._e_categoria.delete(0, "end")
        self._e_categoria.insert(0, it["categoria"])
        # Marcas sugeridas pra esse item
        self._refresh_combo_marcas(it["marcas"])

    # ------------------------------------------------------------------
    # Preencher modo edição
    # ------------------------------------------------------------------

    def _preencher(self, it: ItemEstoque):
        self._e_nome.insert(0, it.nome)
        self._e_categoria.insert(0, it.categoria)
        self._e_unidade.insert(0, it.unidade)
        self._e_atual.delete(0, "end")
        self._e_atual.insert(0, f"{it.estoque_atual:g}".replace(".", ","))
        self._e_minimo.delete(0, "end")
        self._e_minimo.insert(0, f"{it.estoque_minimo:g}".replace(".", ","))
        self._t_obs.insert("1.0", it.observacao)
        self._var_ativo.set(it.ativo)
        # Marca: tenta selecionar do combo; se não estiver, vira "(outra)"
        sugeridas = listar_marcas_sugeridas(it.nome)
        self._refresh_combo_marcas(sugeridas)
        if it.marca:
            opcoes = self._cb_marca.cget("values")
            # tenta achar com prefixo ★
            star = f"★ {it.marca}"
            if star in opcoes:
                self._cb_marca.set(star)
            elif it.marca in opcoes:
                self._cb_marca.set(it.marca)
            else:
                self._cb_marca.set(_OPCAO_OUTRA)
                self._e_marca_nova.pack(fill="x", pady=(0, 8))
                self._e_marca_nova.insert(0, it.marca)

    # ------------------------------------------------------------------
    # Coleta da marca final
    # ------------------------------------------------------------------

    def _marca_final(self) -> str:
        sel = self._cb_marca.get()
        if sel == "(sem marca)":
            return ""
        if sel == _OPCAO_OUTRA:
            return self._e_marca_nova.get().strip()
        # Remove prefixo ★
        if sel.startswith("★ "):
            return sel[2:].strip()
        return sel.strip()

    # ------------------------------------------------------------------
    # Salvar
    # ------------------------------------------------------------------

    def _salvar(self):
        self._lbl_erro.configure(text="")
        nome = self._e_nome.get().strip()
        if not nome:
            self._lbl_erro.configure(text="Nome é obrigatório.")
            return
        dados = {
            "nome":           nome,
            "categoria":      self._e_categoria.get().strip(),
            "unidade":        self._e_unidade.get().strip(),
            "marca":          self._marca_final(),
            "estoque_atual":  _parse_num(self._e_atual.get()),
            "estoque_minimo": _parse_num(self._e_minimo.get()),
            "observacao":     self._t_obs.get("1.0", "end").strip(),
            "ativo":          self._var_ativo.get(),
        }
        try:
            iid = salvar_item(dados, id=self._item.id if self._item else None)
        except ValueError as e:
            self._lbl_erro.configure(text=str(e))
            return
        self.destroy()
        self._on_salvo(iid)
