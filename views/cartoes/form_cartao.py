"""
form_cartao.py — Modal de cadastro e edição de cartão de crédito.
Inclui preview ao vivo do card visual.
"""

from __future__ import annotations
import customtkinter as ctk
from config import get_tema, mascara_moeda
from database import obter_configuracao
from views.cartoes.cartao_model import (
    Cartao, salvar_cartao,
    CORES_BANCO, NOMES_BANCOS, BANDEIRAS, BANDEIRAS_LABEL, CORES_BANDEIRA,
    carregar_logo_bandeira, bandeiras_disponiveis, salvar_bandeira_custom,
)


class FormCartao(ctk.CTkToplevel):
    def __init__(self, parent, on_salvo, cartao: Cartao | None = None):
        super().__init__(parent)
        self._on_salvo = on_salvo
        self._cartao = cartao
        self._cores = get_tema(obter_configuracao("tema", "claro"))

        titulo = "Editar Cartão" if cartao else "Novo Cartão"
        self.title(f"Serenus — {titulo}")
        self.geometry("740x560")
        self.resizable(True, True)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_ui()
        if cartao:
            self._preencher(cartao)
        self.after(100, self._centralizar)
        self.after(200, self._atualizar_preview)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------

    def _build_ui(self):
        cores = self._cores
        # Layout: formulário esq | preview dir
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=16)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)

        fr = ctk.CTkScrollableFrame(main, fg_color="transparent", width=380)
        fr.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._fr = fr

        # Preview
        prev_frame = ctk.CTkFrame(main, fg_color="transparent", width=260)
        prev_frame.grid(row=0, column=1, sticky="n", pady=8)
        prev_frame.grid_propagate(False)

        ctk.CTkLabel(prev_frame, text="Preview",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=cores["texto_mudo"]).pack(pady=(0, 8))

        self._preview_card = ctk.CTkFrame(prev_frame, fg_color="#6D28D9",
                                          corner_radius=16, width=240, height=151)
        self._preview_card.pack()
        self._preview_card.pack_propagate(False)

        topo_prev = ctk.CTkFrame(self._preview_card, fg_color="transparent")
        topo_prev.pack(fill="x", padx=14, pady=(12, 0))
        topo_prev.grid_columnconfigure(0, weight=1)

        self._prev_banco = ctk.CTkLabel(topo_prev, text="Banco",
                                         font=ctk.CTkFont(size=11, weight="bold"),
                                         text_color="#FFFFFF")
        self._prev_banco.grid(row=0, column=0, sticky="w")

        # Logo ou badge de bandeira (direita do topo)
        self._prev_band_img  = ctk.CTkLabel(topo_prev, text="", fg_color="transparent")
        self._prev_band_txt  = ctk.CTkLabel(topo_prev, text="VISA",
                                             fg_color="#FFFFFF", text_color="#1A1F71",
                                             corner_radius=4,
                                             font=ctk.CTkFont(size=10, weight="bold"))
        self._prev_band_img.grid(row=0, column=1, sticky="e")
        self._prev_band_txt.grid(row=0, column=1, sticky="e")

        self._prev_num  = ctk.CTkLabel(self._preview_card, text="•••• •••• •••• ----",
                                        font=ctk.CTkFont(size=13, weight="bold"),
                                        text_color="#FFFFFF")
        self._prev_nome = ctk.CTkLabel(self._preview_card, text="Meu Cartão",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        text_color="#FFFFFF")
        self._prev_num.pack(anchor="w", padx=14, pady=(10, 2))
        self._prev_nome.pack(anchor="w", padx=14)

        # Botões
        btns = ctk.CTkFrame(main, fg_color="transparent")
        btns.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ctk.CTkButton(btns, text="Cancelar", width=120,
                      fg_color="transparent", border_width=1,
                      text_color=cores["texto"], border_color=cores["borda"],
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Salvar", width=120,
                      command=self._salvar).pack(side="right")

        # Campos do formulário
        self._lbl(fr, "Nome do cartão *")
        self._entry_nome = ctk.CTkEntry(fr, placeholder_text="Ex: Nubank Roxo")
        self._entry_nome.pack(fill="x", pady=(2, 2))
        self._entry_nome.bind("<KeyRelease>", lambda e: self._atualizar_preview())
        self._err_nome = ctk.CTkLabel(fr, text="", text_color="#DC2626",
                                      font=ctk.CTkFont(size=10), anchor="w")
        self._err_nome.pack(anchor="w", pady=(0, 8))

        self._lbl(fr, "Banco *")
        bancos_chaves = list(NOMES_BANCOS.keys())
        bancos_labels = list(NOMES_BANCOS.values())
        self._combo_banco = ctk.CTkComboBox(
            fr, values=bancos_labels, state="readonly",
            command=self._on_banco_mudou
        )
        self._combo_banco.set(bancos_labels[0])
        self._combo_banco.pack(fill="x", pady=(2, 12))

        self._lbl(fr, "Bandeira *")
        self._band_chaves, self._band_labels = bandeiras_disponiveis()
        self._combo_bandeira = ctk.CTkComboBox(
            fr, values=self._band_labels, state="readonly",
            command=self._on_bandeira_mudou,
        )
        self._combo_bandeira.set(self._band_labels[0])
        self._combo_bandeira.pack(fill="x", pady=(2, 4))

        # Campo de nova bandeira (aparece só quando "✏ + Nova bandeira..." é selecionado)
        self._frame_nova_band = ctk.CTkFrame(fr, fg_color="transparent")
        self._lbl(self._frame_nova_band, "Nome da nova bandeira")
        self._entry_nova_band = ctk.CTkEntry(
            self._frame_nova_band, placeholder_text="Ex: Sodexo, VR, Ticket..."
        )
        self._entry_nova_band.pack(fill="x", pady=(2, 0))
        self._entry_nova_band.bind("<KeyRelease>", lambda e: self._atualizar_preview())
        ctk.CTkButton(
            self._frame_nova_band, text="Cadastrar bandeira", height=28,
            font=ctk.CTkFont(size=11),
            command=self._cadastrar_nova_bandeira,
        ).pack(anchor="w", pady=(6, 0))
        # frame oculto por padrão
        self._frame_nova_band.pack_forget()

        # espaço separador
        ctk.CTkFrame(fr, fg_color="transparent", height=8).pack()

        self._lbl(fr, "Últimos 4 dígitos")
        self._entry_digitos = ctk.CTkEntry(fr, placeholder_text="1234", width=100)
        self._entry_digitos.pack(anchor="w", pady=(2, 12))
        self._entry_digitos.bind("<KeyRelease>", lambda e: self._atualizar_preview())

        # Cores
        cores_row = ctk.CTkFrame(fr, fg_color="transparent")
        cores_row.pack(fill="x", pady=(0, 12))
        cores_row.grid_columnconfigure((0, 1), weight=1)

        cf = ctk.CTkFrame(cores_row, fg_color="transparent")
        cf.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._lbl(cf, "Cor do fundo (hex)")
        self._entry_cor_fundo = ctk.CTkEntry(cf, placeholder_text="#6D28D9")
        self._entry_cor_fundo.insert(0, "#6D28D9")
        self._entry_cor_fundo.pack(fill="x", pady=(2, 0))
        self._entry_cor_fundo.bind("<KeyRelease>", lambda e: self._atualizar_preview())

        ct = ctk.CTkFrame(cores_row, fg_color="transparent")
        ct.grid(row=0, column=1, sticky="ew")
        self._lbl(ct, "Cor do texto (hex)")
        self._entry_cor_texto = ctk.CTkEntry(ct, placeholder_text="#FFFFFF")
        self._entry_cor_texto.insert(0, "#FFFFFF")
        self._entry_cor_texto.pack(fill="x", pady=(2, 0))
        self._entry_cor_texto.bind("<KeyRelease>", lambda e: self._atualizar_preview())

        self._lbl(fr, "Limite total (R$)")
        self._entry_limite = ctk.CTkEntry(fr)
        self._entry_limite.insert(0, "0,00")
        self._entry_limite.pack(fill="x", pady=(2, 12))
        self._entry_limite.bind("<KeyRelease>", lambda e: mascara_moeda(self._entry_limite))

        dias_row = ctk.CTkFrame(fr, fg_color="transparent")
        dias_row.pack(fill="x", pady=(0, 12))
        dias_row.grid_columnconfigure((0, 1), weight=1)

        dv = ctk.CTkFrame(dias_row, fg_color="transparent")
        dv.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._lbl(dv, "Dia do vencimento")
        self._entry_vencimento = ctk.CTkEntry(dv, placeholder_text="10", width=80)
        self._entry_vencimento.pack(anchor="w", pady=(2, 0))

        df = ctk.CTkFrame(dias_row, fg_color="transparent")
        df.grid(row=0, column=1, sticky="ew")
        self._lbl(df, "Dia do fechamento")
        self._entry_fechamento = ctk.CTkEntry(df, placeholder_text="3", width=80)
        self._entry_fechamento.pack(anchor="w", pady=(2, 0))

    def _lbl(self, parent, txt: str):
        ctk.CTkLabel(parent, text=txt, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _on_bandeira_mudou(self, label: str):
        if label == self._band_labels[-1]:   # "✏ + Nova bandeira..."
            self._frame_nova_band.pack(fill="x", pady=(0, 8))
        else:
            self._frame_nova_band.pack_forget()
        self._atualizar_preview()

    def _cadastrar_nova_bandeira(self):
        nome = self._entry_nova_band.get().strip()
        if not nome:
            return
        chave = salvar_bandeira_custom(nome)
        # Recarrega dropdown com a nova bandeira
        self._band_chaves, self._band_labels = bandeiras_disponiveis()
        self._combo_bandeira.configure(values=self._band_labels)
        label = nome.strip().title()
        if label in self._band_labels:
            self._combo_bandeira.set(label)
        self._frame_nova_band.pack_forget()
        self._entry_nova_band.delete(0, "end")
        self._atualizar_preview()

    def _on_banco_mudou(self, label: str):
        inv = {v: k for k, v in NOMES_BANCOS.items()}
        chave = inv.get(label, "outro")
        cor = CORES_BANCO.get(chave, "#374151")
        self._entry_cor_fundo.delete(0, "end")
        self._entry_cor_fundo.insert(0, cor)
        self._atualizar_preview()

    def _atualizar_preview(self):
        cor_fundo = self._entry_cor_fundo.get().strip() or "#6D28D9"
        cor_texto = self._entry_cor_texto.get().strip() or "#FFFFFF"
        nome      = self._entry_nome.get().strip() or "Meu Cartão"
        digits    = self._entry_digitos.get().strip() or "----"
        banco_label = self._combo_banco.get()

        band_label = self._combo_bandeira.get()
        # Determina chave da bandeira selecionada
        if band_label in self._band_labels:
            idx = self._band_labels.index(band_label)
            band_chave = self._band_chaves[idx] if idx < len(self._band_chaves) else ""
        else:
            band_chave = ""

        # Bandeira customizada em edição livre
        if band_chave == "__nova__":
            band_chave = self._entry_nova_band.get().strip().lower().replace(" ", "_")

        try:
            self._preview_card.configure(fg_color=cor_fundo)
        except Exception:
            pass

        self._prev_banco.configure(text=banco_label, text_color=cor_texto)
        self._prev_num.configure(text=f"•••• •••• •••• {digits}", text_color=cor_texto)
        self._prev_nome.configure(text=nome, text_color=cor_texto)

        # Tenta exibir logo; senão mostra badge de texto
        logo = carregar_logo_bandeira(band_chave, size=(54, 34))
        if logo:
            self._prev_band_img.configure(image=logo, text="")
            self._prev_band_img.lift()
            self._prev_band_txt.lower()
        else:
            band_cor = CORES_BANDEIRA.get(band_chave, "#CCCCCC")
            lbl = band_label if band_label not in ("✏  + Nova bandeira...",) \
                  else (self._entry_nova_band.get().strip().upper() or "NOVA")
            self._prev_band_txt.configure(text=f" {lbl} ", text_color=band_cor)
            self._prev_band_txt.lift()
            self._prev_band_img.configure(image=None, text="")

    # ------------------------------------------------------------------

    def _preencher(self, c: Cartao):
        self._entry_nome.insert(0, c.nome)
        banco_label = NOMES_BANCOS.get(c.banco, c.banco)
        self._combo_banco.set(banco_label)
        # Encontra o label da bandeira entre padrão + customizadas
        if c.bandeira in self._band_chaves:
            idx = self._band_chaves.index(c.bandeira)
            self._combo_bandeira.set(self._band_labels[idx])
        else:
            self._combo_bandeira.set(self._band_labels[0])
        self._entry_digitos.insert(0, c.ultimos_digitos or "")
        self._entry_cor_fundo.delete(0, "end")
        self._entry_cor_fundo.insert(0, c.cor_fundo)
        self._entry_cor_texto.delete(0, "end")
        self._entry_cor_texto.insert(0, c.cor_texto)
        if c.limite:
            self._entry_limite.insert(0, f"{c.limite:.2f}".replace(".", ","))
        if c.dia_vencimento:
            self._entry_vencimento.insert(0, str(c.dia_vencimento))
        if c.dia_fechamento:
            self._entry_fechamento.insert(0, str(c.dia_fechamento))

    def _salvar(self):
        self._err_nome.configure(text="")
        self._entry_nome.configure(border_color=self._cores["borda"])

        nome = self._entry_nome.get().strip()
        if not nome:
            self._entry_nome.configure(border_color="#DC2626")
            self._err_nome.configure(text="Nome é obrigatório.")
            return

        banco_label = self._combo_banco.get()
        inv = {v: k for k, v in NOMES_BANCOS.items()}
        banco_chave = inv.get(banco_label, "outro")

        band_label = self._combo_bandeira.get()
        if band_label in self._band_labels:
            idx = self._band_labels.index(band_label)
            bandeira = self._band_chaves[idx]
        else:
            bandeira = "visa"
        # Se for "nova bandeira não salva ainda", salva agora
        if bandeira == "__nova__":
            nome_custom = self._entry_nova_band.get().strip()
            if nome_custom:
                bandeira = salvar_bandeira_custom(nome_custom)
            else:
                bandeira = "outro"

        limite_str = self._entry_limite.get().replace(".", "").replace(",", ".").strip()
        try:
            limite = float(limite_str) if limite_str else 0.0
            if limite < 0:
                self._err_nome.configure(text="Limite não pode ser negativo.")
                return
        except ValueError:
            self._err_nome.configure(text="Limite inválido. Digite só números.")
            return

        venc_str = self._entry_vencimento.get().strip()
        fech_str = self._entry_fechamento.get().strip()

        # Valida dias 1..31 (rejeita 99, 0 etc. antes de persistir lixo)
        def _dia_valido(s: str) -> int | None:
            if not s:
                return None
            if not s.isdigit():
                return False  # marcador de inválido
            n = int(s)
            return n if 1 <= n <= 31 else False

        dia_venc = _dia_valido(venc_str)
        dia_fech = _dia_valido(fech_str)
        if dia_venc is False or dia_fech is False:
            self._err_nome.configure(text="Dia de vencimento/fechamento deve estar entre 1 e 31.")
            return

        dados = {
            "nome":           nome,
            "banco":          banco_chave,
            "bandeira":       bandeira,
            "ultimos_digitos": self._entry_digitos.get().strip()[:4],
            "cor_fundo":      self._entry_cor_fundo.get().strip() or "#6D28D9",
            "cor_texto":      self._entry_cor_texto.get().strip() or "#FFFFFF",
            "limite":         limite,
            "dia_vencimento": dia_venc,
            "dia_fechamento": dia_fech,
        }

        salvar_cartao(dados, id=self._cartao.id if self._cartao else None)
        self.destroy()
        self._on_salvo()
