"""
form_compra.py — Modal para lançar compra em cartão de crédito.
Melhorias: último cartão lembrado, mês calculado pelo fechamento,
preview rico em tempo real, lançamento em lote.
"""

from __future__ import annotations
import customtkinter as ctk
from datetime import date
from config import get_tema, formatar_moeda, mascara_moeda, CATEGORIAS_PLANO_CONTAS, NOMES_MESES
from database import obter_configuracao
from views.cartoes.cartao_model import (
    Cartao, listar_cartoes, salvar_compra_com_parcelas,
    BANDEIRAS, BANDEIRAS_LABEL,
)


def _avancar_mes(ano: int, mes: int, delta: int) -> tuple[int, int]:
    mes += delta
    ano += (mes - 1) // 12
    mes = ((mes - 1) % 12) + 1
    return ano, mes


def _calcular_mes_inicio(dia_compra: int, dia_fechamento: int | None) -> tuple[int, int, str]:
    """
    Retorna (ano, mes, motivo) da primeira parcela.
    Regra: dia_compra <= dia_fechamento → +1 mês; caso contrário → +2 meses.
    """
    hoje = date.today()
    if dia_fechamento is None:
        a, m = _avancar_mes(hoje.year, hoje.month, 1)
        return a, m, "fechamento nao cadastrado => +1 mes"
    if dia_compra <= dia_fechamento:
        a, m = _avancar_mes(hoje.year, hoje.month, 1)
        return a, m, f"dia {dia_compra} <= fechamento {dia_fechamento} => +1 mes"
    else:
        a, m = _avancar_mes(hoje.year, hoje.month, 2)
        return a, m, f"dia {dia_compra} > fechamento {dia_fechamento} => +2 meses"


class FormCompra(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, cartao: Cartao | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo          # on_salvo(msg: str)
        self._cartao_inicial = cartao
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        self.title("Serenus — Lançar Compra no Cartão")
        self.geometry("540x660")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._modo_var = ctk.StringVar(value="total")
        self._cartoes = listar_cartoes(apenas_ativos=True)
        self._build_ui()
        self._pre_selecionar_cartao(cartao)
        self.after(150, self._atualizar_preview)
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Seleção de cartão (MELHORIA 1)
    # ------------------------------------------------------------------

    def _pre_selecionar_cartao(self, cartao_explicito: Cartao | None):
        if not self._cartoes:
            return
        nomes = [f"{c.nome} ({c.banco})" for c in self._cartoes]

        # Cartão passado explicitamente tem prioridade
        if cartao_explicito:
            alvo = f"{cartao_explicito.nome} ({cartao_explicito.banco})"
            if alvo in nomes:
                self._combo_cartao.set(alvo)
                return

        # Último cartão usado
        ultimo_id_str = obter_configuracao("ultimo_cartao_id", "")
        if ultimo_id_str.isdigit():
            ultimo_id = int(ultimo_id_str)
            for c in self._cartoes:
                if c.id == ultimo_id:
                    self._combo_cartao.set(f"{c.nome} ({c.banco})")
                    return

        # Fallback: primeiro da lista
        self._combo_cartao.set(nomes[0])

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        cores = self._cores
        fr = ctk.CTkScrollableFrame(self, fg_color="transparent")
        fr.pack(fill="both", expand=True, padx=20, pady=16)
        self._fr = fr

        # Cartão
        self._lbl(fr, "Cartão *")
        nomes_cartoes = [f"{c.nome} ({c.banco})" for c in self._cartoes] or ["(Nenhum cartão ativo)"]
        self._combo_cartao = ctk.CTkComboBox(
            fr, values=nomes_cartoes, state="readonly",
            command=lambda v: self._atualizar_preview()
        )
        self._combo_cartao.set(nomes_cartoes[0])
        self._combo_cartao.pack(fill="x", pady=(2, 12))

        # Data da compra — MELHORIA 2
        self._lbl(fr, "Data da compra (DD/MM/AAAA)")
        hoje = date.today()
        self._entry_data = ctk.CTkEntry(fr, placeholder_text="DD/MM/AAAA", width=150)
        self._entry_data.insert(0, hoje.strftime("%d/%m/%Y"))
        self._entry_data.pack(anchor="w", pady=(2, 12))
        self._entry_data.bind("<KeyRelease>", lambda e: self._atualizar_preview())

        # Estabelecimento
        self._lbl(fr, "Estabelecimento / Loja")
        self._entry_estab = ctk.CTkEntry(fr, placeholder_text="Ex: Amazon, iFood…")
        self._entry_estab.pack(fill="x", pady=(2, 12))

        # Descrição
        self._lbl(fr, "Descrição *")
        self._entry_desc = ctk.CTkEntry(fr, placeholder_text="Ex: Tênis Nike, Curso Python…")
        self._entry_desc.pack(fill="x", pady=(2, 2))
        self._err_desc = ctk.CTkLabel(fr, text="", text_color="#DC2626",
                                      font=ctk.CTkFont(size=10), anchor="w")
        self._err_desc.pack(anchor="w", pady=(0, 8))

        # Categoria
        self._lbl(fr, "Categoria")
        self._combo_cat = ctk.CTkComboBox(fr, values=CATEGORIAS_PLANO_CONTAS, state="readonly")
        self._combo_cat.set(CATEGORIAS_PLANO_CONTAS[0])
        self._combo_cat.pack(fill="x", pady=(2, 12))

        # Modo de entrada
        modo_frame = ctk.CTkFrame(fr, fg_color=cores["card"], corner_radius=8)
        modo_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkRadioButton(modo_frame, text="Informar valor TOTAL",
                           variable=self._modo_var, value="total",
                           command=self._on_modo_mudou).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkRadioButton(modo_frame, text="Informar valor da PARCELA",
                           variable=self._modo_var, value="parcela",
                           command=self._on_modo_mudou).pack(anchor="w", padx=12, pady=(0, 10))

        # Valor + Parcelas
        valor_row = ctk.CTkFrame(fr, fg_color="transparent")
        valor_row.pack(fill="x", pady=(0, 4))
        valor_row.grid_columnconfigure((0, 1), weight=1)

        vf = ctk.CTkFrame(valor_row, fg_color="transparent")
        vf.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._lbl_valor = ctk.CTkLabel(vf, text="Valor total (R$) *", anchor="w",
                                        font=ctk.CTkFont(size=12))
        self._lbl_valor.pack(anchor="w")
        self._entry_valor = ctk.CTkEntry(vf)
        self._entry_valor.insert(0, "0,00")
        self._entry_valor.pack(fill="x", pady=(2, 0))
        self._entry_valor.bind("<KeyRelease>", lambda e: (
            mascara_moeda(self._entry_valor),
            self._atualizar_preview(),
        ))

        self._err_valor = ctk.CTkLabel(fr, text="", text_color="#DC2626",
                                       font=ctk.CTkFont(size=10), anchor="w")
        self._err_valor.pack(anchor="w", pady=(0, 4))

        pf = ctk.CTkFrame(valor_row, fg_color="transparent")
        pf.grid(row=0, column=1, sticky="ew")
        self._lbl(pf, "Nº de parcelas *")
        self._combo_parc = ctk.CTkComboBox(
            pf, values=[str(i) for i in range(1, 25)], state="readonly",
            command=lambda v: self._atualizar_preview()
        )
        self._combo_parc.set("1")
        self._combo_parc.pack(fill="x", pady=(2, 0))

        # Preview — MELHORIA 3
        self._frame_preview = ctk.CTkFrame(fr, fg_color=cores["card"], corner_radius=8)
        self._frame_preview.pack(fill="x", pady=(8, 0))
        self._lbl_preview = ctk.CTkLabel(
            self._frame_preview,
            text="Preencha os campos para ver o resumo.",
            font=ctk.CTkFont(size=11),
            text_color=cores["texto_mudo"],
            justify="left",
        )
        self._lbl_preview.pack(anchor="w", padx=12, pady=10)

        # Botões
        btns = ctk.CTkFrame(fr, fg_color="transparent")
        btns.pack(fill="x", pady=(16, 0))
        ctk.CTkButton(btns, text="Cancelar", width=120,
                      fg_color="transparent", border_width=1,
                      text_color=cores["texto"], border_color=cores["borda"],
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Lançar compra", width=140,
                      command=self._salvar).pack(side="right")

    def _lbl(self, parent, txt: str):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _on_modo_mudou(self):
        self._lbl_valor.configure(
            text="Valor total (R$) *" if self._modo_var.get() == "total"
            else "Valor da parcela (R$) *"
        )
        self._atualizar_preview()

    # ------------------------------------------------------------------
    # Preview em tempo real (MELHORIA 3)
    # ------------------------------------------------------------------

    def _cartao_selecionado(self) -> Cartao | None:
        sel = self._combo_cartao.get()
        return next((c for c in self._cartoes if f"{c.nome} ({c.banco})" == sel), None)

    def _dia_compra(self) -> int:
        raw = self._entry_data.get().strip()
        try:
            return int(raw.split("/")[0])
        except (ValueError, IndexError):
            return date.today().day

    def _atualizar_preview(self):
        cores = self._cores
        cartao = self._cartao_selecionado()
        dia_compra = self._dia_compra()

        # Calcula mês de início (MELHORIA 2)
        dia_fech = cartao.dia_fechamento if cartao else None
        ano_ini, mes_ini, motivo = _calcular_mes_inicio(dia_compra, dia_fech)

        # Monta cabeçalho do preview
        if cartao:
            band_idx = BANDEIRAS.index(cartao.bandeira) if cartao.bandeira in BANDEIRAS else 0
            band_label = BANDEIRAS_LABEL[band_idx]
            fech_txt = f"dia {cartao.dia_fechamento}" if cartao.dia_fechamento else "não informado"
            cab = (f"💳 {cartao.nome}  |  {band_label}  |  Fechamento: {fech_txt}\n"
                   f"→ {motivo}\n"
                   f"→ 1ª parcela: {NOMES_MESES[mes_ini - 1]}/{ano_ini}")
        else:
            cab = f"→ {motivo}\n→ 1ª parcela: {NOMES_MESES[mes_ini - 1]}/{ano_ini}"

        # Calcula valores
        val_str = self._entry_valor.get().replace(".", "").replace(",", ".").strip()
        try:
            val = float(val_str)
            if val <= 0:
                raise ValueError
        except ValueError:
            self._lbl_preview.configure(
                text=cab + "\n\nInforme o valor para ver as parcelas.",
                text_color=cores["texto_mudo"]
            )
            return

        n = int(self._combo_parc.get() or "1")
        if self._modo_var.get() == "total":
            total = round(val, 2)
            parcela_base = round(total / n, 2)
        else:
            parcela_base = round(val, 2)
            total = round(parcela_base * n, 2)
        ultima = round(total - parcela_base * (n - 1), 2)

        cab += f"\n{n}x de {formatar_moeda(parcela_base)} = {formatar_moeda(total)} total"

        # Lista de parcelas (MELHORIA 3 — máx 3 visíveis + resumo + última)
        linhas = []
        mostrar = list(range(n))
        if n > 6:
            mostrar = list(range(3))  # primeiros 3

        for i in mostrar:
            a, m = _avancar_mes(ano_ini, mes_ini, i)
            v = ultima if i == n - 1 else parcela_base
            linhas.append(f"  {i+1}/{n}  {NOMES_MESES[m-1][:3]}/{a}  {formatar_moeda(v)}")

        if n > 6:
            ocultas = n - 3 - 1  # -3 mostradas, -1 última
            if ocultas > 0:
                linhas.append(f"  … +{ocultas} parcelas")
            # sempre mostrar a última
            a_ult, m_ult = _avancar_mes(ano_ini, mes_ini, n - 1)
            linhas.append(f"  {n}/{n}  {NOMES_MESES[m_ult-1][:3]}/{a_ult}  {formatar_moeda(ultima)}")

        texto = cab + "\n" + "\n".join(linhas)
        self._lbl_preview.configure(text=texto, text_color=cores["texto"])

    # ------------------------------------------------------------------
    # Salvar
    # ------------------------------------------------------------------

    def _salvar(self):
        self._err_desc.configure(text="")
        self._err_valor.configure(text="")
        self._entry_desc.configure(border_color=self._cores["borda"])
        self._entry_valor.configure(border_color=self._cores["borda"])

        desc = self._entry_desc.get().strip()
        if not desc:
            self._entry_desc.configure(border_color="#DC2626")
            self._err_desc.configure(text="Descrição é obrigatória.")
            return

        val_str = self._entry_valor.get().replace(".", "").replace(",", ".").strip()
        try:
            val = float(val_str)
            if val <= 0:
                raise ValueError
        except ValueError:
            self._entry_valor.configure(border_color="#DC2626")
            self._err_valor.configure(text="Informe um valor maior que zero.")
            return

        cartao = self._cartao_selecionado()
        if not cartao:
            return

        n = int(self._combo_parc.get() or "1")
        if self._modo_var.get() == "total":
            total = round(val, 2)
            parcela_base = round(total / n, 2)
        else:
            parcela_base = round(val, 2)
            total = round(parcela_base * n, 2)

        # Mês de início calculado automaticamente (MELHORIA 2)
        dia_compra = self._dia_compra()
        ano_ini, mes_ini, _ = _calcular_mes_inicio(dia_compra, cartao.dia_fechamento)
        mes_inicio = f"{ano_ini:04d}-{mes_ini:02d}"

        dados = {
            "cartao_id":      cartao.id,
            "descricao":      desc,
            "estabelecimento": self._entry_estab.get().strip(),
            "categoria":      self._combo_cat.get(),
            "valor_total":    total,
            "valor_parcela":  parcela_base,
            "total_parcelas": n,
            "mes_inicio":     mes_inicio,
        }

        info = salvar_compra_com_parcelas(dados)

        # Toast com range de datas (MELHORIA 4)
        mes_fim_label = info.get("mes_fim", "")
        mes_ini_label = f"{NOMES_MESES[mes_ini - 1][:3]}/{ano_ini}"
        toast_msg = (
            f"Compra lançada! {n} parcela{'s' if n > 1 else ''} registrada{'s' if n > 1 else ''}"
            + (f" de {mes_ini_label} até {mes_fim_label}" if n > 1 else f" em {mes_ini_label}")
        )

        self.destroy()
        self._on_salvo(toast_msg)
