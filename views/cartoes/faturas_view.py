"""
faturas_view.py — Tela de faturas mensais de um cartão de crédito.
Seletor de mês, lista de parcelas, rodapé com totais, ações.
"""

from __future__ import annotations
import customtkinter as ctk
from datetime import date
from config import get_tema, formatar_moeda, NOMES_MESES
from database import obter_configuracao
from views.cartoes.cartao_model import (
    Cartao, ParcelaCartao,
    listar_parcelas_mes, marcar_parcela_paga, marcar_todas_pagas,
    total_fatura_mes, lancar_fatura_contas_pagar,
)


class FaturasView(ctk.CTkToplevel):
    def __init__(self, parent, cartao: Cartao, on_atualizado=None):
        super().__init__(parent)
        self._cartao = cartao
        self._on_atualizado = on_atualizado
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        hoje = date.today()
        self._mes = hoje.month
        self._ano = hoje.year

        self.title(f"Serenus — Faturas: {cartao.nome}")
        self.geometry("700x560")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_tabela()
        self._build_rodape()
        self._carregar()
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------

    def _build_header(self):
        cores = self._cores
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 0))
        header.grid_columnconfigure(1, weight=1)

        # Info do cartão
        info = ctk.CTkFrame(header, fg_color=self._cartao.cor_fundo, corner_radius=8)
        info.grid(row=0, column=0, padx=(0, 20), pady=4)
        ctk.CTkLabel(info, text=f"💳 {self._cartao.nome}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=self._cartao.cor_texto).pack(padx=16, pady=8)

        # Navegação de mês
        nav = ctk.CTkFrame(header, fg_color="transparent")
        nav.grid(row=0, column=1)
        nav.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(nav, text="◀", width=30, height=28,
                      command=self._mes_anterior).grid(row=0, column=0, padx=4)
        self._lbl_mes = ctk.CTkLabel(nav, text="",
                                     font=ctk.CTkFont(size=14, weight="bold"),
                                     text_color=cores["texto"])
        self._lbl_mes.grid(row=0, column=1, padx=8)
        ctk.CTkButton(nav, text="▶", width=30, height=28,
                      command=self._mes_proximo).grid(row=0, column=2, padx=4)

        # Ações
        acoes = ctk.CTkFrame(header, fg_color="transparent")
        acoes.grid(row=0, column=2, padx=(20, 0))

        ctk.CTkButton(acoes, text="Marcar todas pagas", height=30,
                      fg_color=cores["positivo"],
                      command=self._marcar_todas_pagas).pack(side="left", padx=4)
        ctk.CTkButton(acoes, text="Lançar em Contas a Pagar", height=30,
                      fg_color="transparent", border_width=1,
                      border_color=cores["primario"], text_color=cores["primario"],
                      font=ctk.CTkFont(size=11),
                      command=self._lancar_contas_pagar).pack(side="left", padx=4)

    def _build_tabela(self):
        cores = self._cores
        colunas = [
            ("Estabelecimento / Descrição", 220),
            ("Parcela", 75),
            ("Valor", 100),
            ("Status", 80),
            ("Ações", 80),
        ]

        cab = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        cab.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 0))
        for i, (nome, larg) in enumerate(colunas):
            ctk.CTkLabel(cab, text=nome, width=larg, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(
                row=0, column=i, padx=6, pady=6, sticky="w"
            )

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(2, 0))
        self._colunas = colunas

    def _build_rodape(self):
        cores = self._cores
        rodape = ctk.CTkFrame(self, fg_color=cores["card"], corner_radius=8)
        rodape.grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 16))
        rodape.grid_columnconfigure((0, 1, 2), weight=1)

        self._lbl_pendente = ctk.CTkLabel(rodape, text="Pendente: R$ 0,00",
                                           text_color=cores["atencao"],
                                           font=ctk.CTkFont(size=13, weight="bold"))
        self._lbl_pendente.grid(row=0, column=0, padx=12, pady=10)

        self._lbl_pago = ctk.CTkLabel(rodape, text="Pago: R$ 0,00",
                                       text_color=cores["positivo"],
                                       font=ctk.CTkFont(size=13, weight="bold"))
        self._lbl_pago.grid(row=0, column=1, padx=12, pady=10)

        self._lbl_total = ctk.CTkLabel(rodape, text="Total: R$ 0,00",
                                        text_color=cores["texto"],
                                        font=ctk.CTkFont(size=14, weight="bold"))
        self._lbl_total.grid(row=0, column=2, padx=12, pady=10)

        ctk.CTkButton(
            rodape, text="⬇ Excel", width=80, height=28,
            fg_color="transparent", border_width=1,
            border_color=cores["borda"], text_color=cores["texto_mudo"],
            font=ctk.CTkFont(size=11),
            command=self._exportar_excel,
        ).grid(row=0, column=3, padx=12, pady=10)

    # ------------------------------------------------------------------

    def _exportar_excel(self):
        import tkinter.filedialog as fd
        from views.exportar.exportar_model import exportar_fatura_xlsx
        from config import NOMES_MESES
        nome = f"fatura_{self._cartao.nome.lower().replace(' ','_')}_{self._mes:02d}_{self._ano}.xlsx"
        caminho = fd.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=nome,
            title="Exportar fatura",
        )
        if caminho:
            exportar_fatura_xlsx(self._cartao.id, self._mes, self._ano, caminho)
            import tkinter.messagebox as mb
            mb.showinfo("Exportado", f"Fatura salva em:\n{caminho}")

    def _carregar(self):
        self._lbl_mes.configure(text=f"{NOMES_MESES[self._mes - 1]} / {self._ano}")

        for w in self._scroll.winfo_children():
            w.destroy()

        parcelas = listar_parcelas_mes(self._cartao.id, self._mes, self._ano)

        if not parcelas:
            ctk.CTkLabel(self._scroll,
                         text="Nenhuma parcela neste mês.",
                         text_color=self._cores["texto_mudo"]).pack(pady=24)
        else:
            for p in parcelas:
                self._linha(p)

        totais = total_fatura_mes(self._cartao.id, self._mes, self._ano)
        self._lbl_pendente.configure(text=f"Pendente: {formatar_moeda(totais['pendente'])}")
        self._lbl_pago.configure(text=f"Pago: {formatar_moeda(totais['pago'])}")
        self._lbl_total.configure(text=f"Total: {formatar_moeda(totais['total'])}")

    def _linha(self, p: ParcelaCartao):
        cores = self._cores
        pago = p.status == "pago"
        bg = "#D1FAE5" if pago else cores["card"]

        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=6)
        row.pack(fill="x", pady=2)

        titulo = p.estabelecimento or p.descricao
        if p.estabelecimento and p.descricao and p.estabelecimento != p.descricao:
            titulo = f"{p.estabelecimento} — {p.descricao}"

        ctk.CTkLabel(row, text=titulo, width=self._colunas[0][1], anchor="w",
                     font=ctk.CTkFont(size=12),
                     text_color=cores["texto"]).grid(row=0, column=0, padx=6, pady=6, sticky="w")

        parc_txt = f"{p.numero_parcela}/{p.total_parcelas}"
        ctk.CTkLabel(row, text=parc_txt, width=self._colunas[1][1], anchor="w",
                     font=ctk.CTkFont(size=12),
                     text_color=cores["texto_mudo"]).grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ctk.CTkLabel(row, text=formatar_moeda(p.valor), width=self._colunas[2][1], anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=cores["texto"]).grid(row=0, column=2, padx=6, pady=6, sticky="w")

        # Badge status
        badge_txt = "Pago" if pago else "Pendente"
        badge_cor = cores["positivo"] if pago else cores["atencao"]
        ctk.CTkLabel(row, text=badge_txt,
                     fg_color=badge_cor, text_color="#FFFFFF",
                     corner_radius=4, font=ctk.CTkFont(size=10, weight="bold"),
                     width=65, height=20).grid(row=0, column=3, padx=6, pady=6)

        acoes = ctk.CTkFrame(row, fg_color="transparent")
        acoes.grid(row=0, column=4, padx=4)

        if not pago:
            ctk.CTkButton(acoes, text="Pagar", width=60, height=24,
                          fg_color=cores["positivo"],
                          font=ctk.CTkFont(size=11),
                          command=lambda pid=p.id: self._pagar(pid)).pack()

    # ------------------------------------------------------------------

    def _pagar(self, parcela_id: int):
        marcar_parcela_paga(parcela_id)
        self._carregar()
        if self._on_atualizado:
            self._on_atualizado()

    def _marcar_todas_pagas(self):
        marcar_todas_pagas(self._cartao.id, self._mes, self._ano)
        self._carregar()
        if self._on_atualizado:
            self._on_atualizado()

    def _lancar_contas_pagar(self):
        lancar_fatura_contas_pagar(self._cartao.id, self._mes, self._ano)
        self._toast("Fatura lançada em Contas a Pagar.")

    def _mes_anterior(self):
        if self._mes == 1:
            self._mes, self._ano = 12, self._ano - 1
        else:
            self._mes -= 1
        self._carregar()

    def _mes_proximo(self):
        if self._mes == 12:
            self._mes, self._ano = 1, self._ano + 1
        else:
            self._mes += 1
        self._carregar()

    def _toast(self, mensagem: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"]}.get(tipo, cores["positivo"])
        toast = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(toast, text=mensagem, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12)).pack(padx=16, pady=8)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)
        self.after(3000, toast.destroy)
