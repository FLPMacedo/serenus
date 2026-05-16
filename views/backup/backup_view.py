"""
backup_view.py — Módulo 5: Backup e Restauração.
Cards de status local e Drive, configurações de frequência,
tabela de histórico e fluxo de restauração.
"""

from __future__ import annotations
import threading
import os
from pathlib import Path
import customtkinter as ctk
from config import get_tema
from database import obter_configuracao, salvar_configuracao
import backup_manager as bm
import google_drive as gd


class BackupView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="💾  Backup",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=self._cores["texto"]).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 0))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        self._scroll.grid_columnconfigure(0, weight=1)

        self._build_ui()

    # ------------------------------------------------------------------
    # Construção inicial
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._build_cards_status()
        self._build_config()
        self._build_acoes()
        self._build_historico()

    # ------------------------------------------------------------------
    # Cards de status
    # ------------------------------------------------------------------

    def _build_cards_status(self):
        cores = self._cores
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=(4, 0))
        frame.grid_columnconfigure((0, 1), weight=1)

        # --- Card Local ---
        card_local = ctk.CTkFrame(frame, fg_color=cores["card"], corner_radius=10)
        card_local.grid(row=0, column=0, padx=(0, 6), pady=4, sticky="ew")

        ctk.CTkLabel(card_local, text="💾  Backup Local",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkFrame(card_local, height=1, fg_color=cores["borda"]).pack(fill="x", padx=14)

        self._lbl_ultimo = ctk.CTkLabel(card_local,
                                        text=f"Último: {bm.ultimo_backup_str()}",
                                        text_color=cores["texto_mudo"],
                                        font=ctk.CTkFont(size=12), anchor="w")
        self._lbl_ultimo.pack(fill="x", padx=14, pady=(8, 2))

        self._lbl_proximo = ctk.CTkLabel(card_local,
                                         text=f"Próximo: {bm.proximo_backup_previsto()}",
                                         text_color=cores["texto_mudo"],
                                         font=ctk.CTkFont(size=12), anchor="w")
        self._lbl_proximo.pack(fill="x", padx=14, pady=(0, 12))

        # --- Card Drive ---
        card_drive = ctk.CTkFrame(frame, fg_color=cores["card"], corner_radius=10)
        card_drive.grid(row=0, column=1, padx=(6, 0), pady=4, sticky="ew")

        ctk.CTkLabel(card_drive, text="☁️  Google Drive",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkFrame(card_drive, height=1, fg_color=cores["borda"]).pack(fill="x", padx=14)

        conectado = gd.esta_conectado()
        email     = gd.obter_email()
        status_txt = f"✅  {email}" if conectado else "❌  Desconectado"
        status_cor = cores["positivo"] if conectado else cores["alerta"]

        self._lbl_drive_status = ctk.CTkLabel(card_drive, text=status_txt,
                                              text_color=status_cor,
                                              font=ctk.CTkFont(size=12, weight="bold"),
                                              anchor="w")
        self._lbl_drive_status.pack(fill="x", padx=14, pady=(8, 4))

        self._frame_drive_btns = ctk.CTkFrame(card_drive, fg_color="transparent")
        self._frame_drive_btns.pack(fill="x", padx=14, pady=(0, 12))
        self._build_drive_btns(conectado)

        # Aviso se client_secrets.json não existe
        if not gd.client_secrets_existe():
            aviso = ctk.CTkFrame(card_drive, fg_color=cores["atencao"], corner_radius=6)
            aviso.pack(fill="x", padx=14, pady=(0, 10))
            ctk.CTkLabel(aviso,
                         text="⚠️  client_secrets.json não encontrado.\n"
                              "Configure no Google Cloud Console e\n"
                              "copie para a pasta do Serenus.",
                         text_color="#FFFFFF",
                         font=ctk.CTkFont(size=10),
                         justify="left").pack(padx=8, pady=6)

    def _build_drive_btns(self, conectado: bool):
        for w in self._frame_drive_btns.winfo_children():
            w.destroy()
        cores = self._cores
        if conectado:
            ctk.CTkButton(self._frame_drive_btns, text="Desconectar", height=28,
                          width=120, fg_color=cores["alerta"],
                          command=self._desconectar_drive).pack(side="left")
        elif not gd.client_secrets_existe():
            # Sem client_secrets.json: mostra botão de configuração em vez de conectar
            ctk.CTkButton(self._frame_drive_btns,
                          text="ℹ️  Como configurar",
                          height=28, width=160,
                          fg_color=cores["secundario"],
                          command=self._mostrar_setup_drive).pack(side="left")
        else:
            ctk.CTkButton(self._frame_drive_btns, text="Conectar Google Drive",
                          height=28, width=160,
                          command=self._conectar_drive).pack(side="left")

    # ------------------------------------------------------------------
    # Configurações
    # ------------------------------------------------------------------

    def _build_config(self):
        cores = self._cores
        sec   = ctk.CTkFrame(self._scroll, fg_color=cores["card"], corner_radius=10)
        sec.pack(fill="x", padx=4, pady=(12, 0))

        ctk.CTkLabel(sec, text="⚙️  Configurações de Backup",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkFrame(sec, height=1, fg_color=cores["borda"]).pack(fill="x", padx=14)

        row1 = ctk.CTkFrame(sec, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(row1, text="Frequência automática:", width=180, anchor="w").pack(side="left")
        freq_atual = obter_configuracao("backup_frequencia", "desativado")
        self._combo_freq = ctk.CTkComboBox(
            row1,
            values=["diario", "semanal", "mensal", "desativado"],
            width=140, state="readonly",
            command=self._on_freq_change,
        )
        self._combo_freq.set(freq_atual)
        self._combo_freq.pack(side="left", padx=8)

        row2 = ctk.CTkFrame(sec, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkLabel(row2, text="Manter últimos N backups:", width=180, anchor="w").pack(side="left")
        max_n = obter_configuracao("backup_max_local", "30")
        self._entry_max = ctk.CTkEntry(row2, width=60, placeholder_text="30")
        self._entry_max.insert(0, max_n)
        self._entry_max.pack(side="left", padx=8)
        ctk.CTkButton(row2, text="Salvar", width=70, height=26,
                      command=self._salvar_max).pack(side="left", padx=4)

    def _on_freq_change(self, valor: str):
        salvar_configuracao("backup_frequencia", valor)
        self._lbl_proximo.configure(text=f"Próximo: {bm.proximo_backup_previsto()}")

    def _salvar_max(self):
        val = self._entry_max.get().strip()
        try:
            n = int(val)
            if n < 1:
                raise ValueError
            salvar_configuracao("backup_max_local", str(n))
            self._toast(f"Configuração salva: manter {n} backups.")
        except ValueError:
            self._entry_max.configure(border_color="#DC2626")

    # ------------------------------------------------------------------
    # Botões de ação
    # ------------------------------------------------------------------

    def _build_acoes(self):
        cores = self._cores
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=(12, 0))

        ctk.CTkButton(frame, text="💾  Fazer backup agora",
                      height=36, width=180,
                      command=self._backup_agora).pack(side="left", padx=(0, 8))

        ctk.CTkButton(frame, text="🔄  Restaurar backup",
                      height=36, width=160,
                      fg_color=cores["atencao"],
                      hover_color="#B45309",
                      command=self._abrir_restauracao).pack(side="left", padx=(0, 8))

        ctk.CTkButton(frame, text="📁  Abrir pasta de backups",
                      height=36, width=190,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"],
                      text_color=cores["texto"],
                      command=self._abrir_pasta).pack(side="left")

        # Label de progresso/status das operações
        self._lbl_status_op = ctk.CTkLabel(frame, text="",
                                           text_color=cores["texto_mudo"],
                                           font=ctk.CTkFont(size=11))
        self._lbl_status_op.pack(side="left", padx=12)

    # ------------------------------------------------------------------
    # Tabela de histórico
    # ------------------------------------------------------------------

    def _build_historico(self):
        cores = self._cores
        sec   = ctk.CTkFrame(self._scroll, fg_color="transparent")
        sec.pack(fill="x", padx=4, pady=(16, 16))

        ctk.CTkLabel(sec, text="Histórico de Backups",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 6))

        cols = [("Data/Hora", 160), ("Arquivo", 220), ("Tamanho", 80),
                ("Destino", 90), ("Status", 70)]

        cab = ctk.CTkFrame(sec, fg_color=cores["card"], corner_radius=8)
        cab.pack(fill="x")
        for i, (txt, w) in enumerate(cols):
            ctk.CTkLabel(cab, text=txt, width=w, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto_mudo"]).grid(
                row=0, column=i, padx=6, pady=6, sticky="w")

        self._scroll_hist = ctk.CTkScrollableFrame(sec, height=220,
                                                   fg_color="transparent")
        self._scroll_hist.pack(fill="x", pady=(2, 0))
        self._cols_hist = cols
        self._recarregar_historico()

    def _recarregar_historico(self):
        for w in self._scroll_hist.winfo_children():
            w.destroy()

        historico = bm.historico_backups()
        if not historico:
            ctk.CTkLabel(self._scroll_hist,
                         text="Nenhum backup registrado ainda.",
                         text_color=self._cores["texto_mudo"]).pack(pady=16)
            return

        for h in historico:
            self._linha_historico(h)

    def _linha_historico(self, h: dict):
        cores = self._cores
        ok    = h["status"] == "ok"
        bg    = cores["fundo"]

        row = ctk.CTkFrame(self._scroll_hist, fg_color=bg, corner_radius=0)
        row.pack(fill="x", pady=1)

        tamanho = f"{h['tamanho_kb']:.1f} KB" if h.get("tamanho_kb") else "—"
        vals = [
            (h.get("data_hora", "—")[:19],        self._cols_hist[0][1]),
            (h.get("arquivo", "—"),               self._cols_hist[1][1]),
            (tamanho,                              self._cols_hist[2][1]),
            ((h.get("destino") or "local").upper(), self._cols_hist[3][1]),
        ]
        for i, (txt, w) in enumerate(vals):
            ctk.CTkLabel(row, text=txt, width=w, anchor="w",
                         font=ctk.CTkFont(size=11),
                         text_color=cores["texto"]).grid(
                row=0, column=i, padx=6, pady=4, sticky="w")

        cor_status = cores["positivo"] if ok else cores["alerta"]
        ico        = "✅" if ok else "❌"
        ctk.CTkLabel(row, text=ico, width=self._cols_hist[4][1],
                     anchor="w", text_color=cor_status,
                     font=ctk.CTkFont(size=12)).grid(
            row=0, column=4, padx=6, pady=4, sticky="w")

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _backup_agora(self):
        self._lbl_status_op.configure(text="Realizando backup…")
        self.update_idletasks()

        def _run():
            ok, resultado = bm.fazer_backup()

            # Se Drive conectado, faz upload também
            drive_msg = ""
            if ok and gd.esta_conectado():
                caminho = Path(resultado)
                dok, dmsg = gd.upload_backup(caminho,
                                             progresso_cb=lambda m: None)
                from database import conectar
                with conectar() as conn:
                    conn.execute(
                        "INSERT INTO backups (data_hora, arquivo, tamanho_kb, destino, status)"
                        " VALUES (datetime('now'), ?, ?, 'google_drive', ?)",
                        (caminho.name, caminho.stat().st_size / 1024,
                         "ok" if dok else "erro")
                    )
                drive_msg = " + Drive ✅" if dok else " (Drive falhou)"

            def _ui():
                if ok:
                    self._lbl_status_op.configure(text="")
                    self._lbl_ultimo.configure(text=f"Último: {bm.ultimo_backup_str()}")
                    self._lbl_proximo.configure(text=f"Próximo: {bm.proximo_backup_previsto()}")
                    self._recarregar_historico()
                    self._toast(f"Backup realizado{drive_msg}.")
                else:
                    self._lbl_status_op.configure(text=f"Erro: {resultado[:60]}")

            self.after(0, _ui)

        threading.Thread(target=_run, daemon=True).start()

    def _abrir_pasta(self):
        pasta = bm._pasta_backups()
        try:
            os.startfile(str(pasta))   # Windows
        except AttributeError:
            import subprocess as sp
            sp.Popen(["xdg-open", str(pasta)])

    # ------------------------------------------------------------------
    # Google Drive
    # ------------------------------------------------------------------

    def _mostrar_setup_drive(self):
        """Abre modal com instruções de configuração do client_secrets.json."""
        _DriveSetupModal(self)

    def _conectar_drive(self):
        # Guarda de segurança: verifica client_secrets antes de entrar na thread
        if not gd.client_secrets_existe():
            self._mostrar_setup_drive()
            return

        self._lbl_status_op.configure(text="Aguardando autenticação no navegador…")

        def _sucesso(email: str):
            def _ui():
                self._lbl_drive_status.configure(
                    text=f"✅  {email}",
                    text_color=self._cores["positivo"]
                )
                self._build_drive_btns(True)
                self._lbl_status_op.configure(text="")
                self._toast(f"Google Drive conectado: {email}")
            self.after(0, _ui)

        def _erro(msg: str):
            def _ui():
                self._lbl_status_op.configure(text="")
                _DriveErroModal(self, msg)
            self.after(0, _ui)

        def _prog(msg: str):
            self.after(0, lambda: self._lbl_status_op.configure(text=msg))

        gd.conectar_drive_async(_sucesso, _erro, _prog)

    def _desconectar_drive(self):
        gd.desconectar()
        self._lbl_drive_status.configure(text="❌  Desconectado",
                                         text_color=self._cores["alerta"])
        self._build_drive_btns(False)
        self._toast("Google Drive desconectado.")

    # ------------------------------------------------------------------
    # Restauração
    # ------------------------------------------------------------------

    def _abrir_restauracao(self):
        RestauracaoModal(self, on_restaurado=self._pos_restauracao)

    def _pos_restauracao(self, msg: str):
        self._recarregar_historico()
        self._lbl_ultimo.configure(text=f"Último: {bm.ultimo_backup_str()}")
        self._toast(msg)

    # ------------------------------------------------------------------
    # Toast
    # ------------------------------------------------------------------

    def _toast(self, mensagem: str, tipo: str = "sucesso"):
        cores = self._cores
        cor = {"sucesso": cores["positivo"], "erro": cores["alerta"],
               "atencao": cores["atencao"]}.get(tipo, cores["positivo"])
        t = ctk.CTkFrame(self, fg_color=cor, corner_radius=8)
        ctk.CTkLabel(t, text=mensagem, text_color="#FFFFFF",
                     font=ctk.CTkFont(size=12),
                     wraplength=320).pack(padx=16, pady=8)
        t.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.after(3000, t.destroy)


# ============================================================================
# Modal de Setup do Google Drive
# ============================================================================

class _DriveSetupModal(ctk.CTkToplevel):
    """Explica passo a passo como criar o client_secrets.json."""

    def __init__(self, parent):
        super().__init__(parent)
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.title("Serenus — Configurar Google Drive")
        self.geometry("560x500")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self._build_ui()
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        cores = self._cores
        fr = ctk.CTkScrollableFrame(self, fg_color="transparent")
        fr.pack(fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(fr, text="☁️  Como conectar o Google Drive",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=cores["primario"]).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(fr,
                     text="O Serenus usa a API oficial do Google. É necessário criar\n"
                          "credenciais uma única vez no Google Cloud Console.",
                     text_color=cores["texto_mudo"],
                     font=ctk.CTkFont(size=12),
                     justify="left").pack(anchor="w", pady=(0, 14))

        passos = [
            ("1", "Acesse o Google Cloud Console",
             "console.cloud.google.com — faça login com sua conta Google."),
            ("2", "Crie ou selecione um projeto",
             "Clique em \"Novo projeto\", dê um nome (ex: Serenus) e crie."),
            ("3", "Ative a Google Drive API",
             "Menu → APIs e Serviços → Biblioteca → pesquise\n"
             "\"Google Drive API\" → clique em Ativar."),
            ("4", "Configure a tela de consentimento OAuth",
             "APIs e Serviços → Tela de consentimento OAuth\n"
             "→ Tipo: Externo → preencha nome do app → Salvar."),
            ("5", "Crie as credenciais OAuth",
             "APIs e Serviços → Credenciais → + Criar credenciais\n"
             "→ ID do cliente OAuth → Tipo: App para computador → Criar."),
            ("6", "Baixe o JSON e coloque na pasta do Serenus",
             "Clique no ícone ⬇️ ao lado da credencial criada.\n"
             "Renomeie o arquivo para:  client_secrets.json\n"
             f"Coloque em:  {gd.DIRETORIO_BASE}"),
            ("7", "Clique em \"Conectar Google Drive\"",
             "O Serenus abrirá o navegador para você autorizar o acesso."),
        ]

        for num, titulo, descricao in passos:
            row = ctk.CTkFrame(fr, fg_color=cores["card"], corner_radius=8)
            row.pack(fill="x", pady=4)
            row.grid_columnconfigure(1, weight=1)

            badge = ctk.CTkLabel(row, text=num, width=28, height=28,
                                 fg_color=cores["primario"],
                                 text_color="#FFFFFF",
                                 corner_radius=14,
                                 font=ctk.CTkFont(size=12, weight="bold"))
            badge.grid(row=0, column=0, padx=(10, 8), pady=10, sticky="n")

            txt_frame = ctk.CTkFrame(row, fg_color="transparent")
            txt_frame.grid(row=0, column=1, sticky="ew", pady=10, padx=(0, 10))

            ctk.CTkLabel(txt_frame, text=titulo, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cores["texto"]).pack(anchor="w")
            ctk.CTkLabel(txt_frame, text=descricao, anchor="w",
                         font=ctk.CTkFont(size=11),
                         text_color=cores["texto_mudo"],
                         justify="left").pack(anchor="w")

        btns = ctk.CTkFrame(fr, fg_color="transparent")
        btns.pack(fill="x", pady=(12, 0))

        ctk.CTkButton(btns, text="Abrir Google Cloud Console",
                      width=200,
                      command=lambda: __import__("webbrowser").open(
                          "https://console.cloud.google.com/apis/credentials"
                      )).pack(side="left")

        ctk.CTkButton(btns, text="Fechar", width=100,
                      fg_color="transparent", border_width=1,
                      border_color=cores["borda"],
                      text_color=cores["texto"],
                      command=self.destroy).pack(side="right")


class _DriveErroModal(ctk.CTkToplevel):
    """Mostra erro de conexão com o Drive de forma legível."""

    def __init__(self, parent, mensagem: str):
        super().__init__(parent)
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.title("Serenus — Erro ao conectar Drive")
        self.geometry("440x260")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        cores = self._cores

        ctk.CTkLabel(self, text="❌  Erro ao conectar Google Drive",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=cores["alerta"]).pack(pady=(20, 8), padx=20, anchor="w")

        box = ctk.CTkTextbox(self, height=120, font=ctk.CTkFont(size=11))
        box.pack(fill="x", padx=20)
        box.insert("0.0", mensagem)
        box.configure(state="disabled")

        ctk.CTkLabel(self,
                     text="Se a mensagem mencionar client_secrets.json,\n"
                          "clique em \"Como configurar\" no painel de Backup.",
                     text_color=cores["texto_mudo"],
                     font=ctk.CTkFont(size=11),
                     justify="left").pack(padx=20, pady=(8, 0), anchor="w")

        ctk.CTkButton(self, text="Fechar", width=100,
                      command=self.destroy).pack(pady=14)

        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")


# ============================================================================
# Modal de Restauração
# ============================================================================

class RestauracaoModal(ctk.CTkToplevel):
    def __init__(self, parent, on_restaurado):
        super().__init__(parent)
        self._on_restaurado = on_restaurado
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self._selecionado: Path | None = None

        self.title("Serenus — Restaurar Backup")
        self.geometry("560x480")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self._build_ui()
        self.after(100, self._centralizar)

    def _centralizar(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_rootx() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        cores = self._cores

        ctk.CTkLabel(self, text="🔄  Restaurar Backup",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 4), padx=20, anchor="w")

        aviso = ctk.CTkFrame(self, fg_color=cores["atencao"], corner_radius=8)
        aviso.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(aviso,
                     text="⚠️  Isso substituirá todos os dados atuais. Um backup de segurança\n"
                          "será feito automaticamente antes da restauração.",
                     text_color="#FFFFFF", font=ctk.CTkFont(size=11),
                     justify="left").pack(padx=12, pady=8)

        ctk.CTkLabel(self, text="Selecione um backup local:",
                     anchor="w").pack(fill="x", padx=20)

        # Lista de backups
        self._scroll_lista = ctk.CTkScrollableFrame(self, height=220, fg_color="transparent")
        self._scroll_lista.pack(fill="x", padx=20, pady=(4, 12))
        self._popular_lista()

        # Progresso
        self._barra = ctk.CTkProgressBar(self, height=10, corner_radius=4)
        self._barra.set(0)
        self._barra.pack(fill="x", padx=20, pady=(0, 4))
        self._lbl_prog = ctk.CTkLabel(self, text="",
                                      text_color=cores["texto_mudo"],
                                      font=ctk.CTkFont(size=11))
        self._lbl_prog.pack()

        # Botões
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text="Cancelar", width=120,
                      fg_color="transparent", border_width=1,
                      text_color=cores["texto"], border_color=cores["borda"],
                      command=self.destroy).pack(side="left", padx=8)
        self._btn_restaurar = ctk.CTkButton(
            btns, text="Restaurar selecionado", width=180,
            fg_color=cores["atencao"], hover_color="#B45309",
            state="disabled",
            command=self._confirmar,
        )
        self._btn_restaurar.pack(side="left", padx=8)

    def _popular_lista(self):
        for w in self._scroll_lista.winfo_children():
            w.destroy()

        backups = bm.listar_backups_locais()
        if not backups:
            ctk.CTkLabel(self._scroll_lista,
                         text="Nenhum backup local encontrado.",
                         text_color=self._cores["texto_mudo"]).pack(pady=16)
            return

        self._var_sel = ctk.StringVar(value="")
        for b in backups:
            linha = ctk.CTkFrame(self._scroll_lista,
                                 fg_color=self._cores["card"], corner_radius=6)
            linha.pack(fill="x", pady=2)
            ctk.CTkRadioButton(
                linha,
                text=f"{b['data']}   {b['nome']}   ({b['tamanho_kb']:.1f} KB)",
                variable=self._var_sel,
                value=str(b["caminho"]),
                command=lambda: self._btn_restaurar.configure(state="normal"),
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=10, pady=6)

    def _confirmar(self):
        sel = self._var_sel.get()
        if not sel:
            return

        self._selecionado = Path(sel)
        self._btn_restaurar.configure(state="disabled")

        def _progresso(msg: str, pct: float):
            def _ui():
                self._barra.set(pct)
                self._lbl_prog.configure(text=msg)
            self.after(0, _ui)

        def _run():
            ok, msg = bm.restaurar_backup(self._selecionado, progresso_cb=_progresso)

            def _ui():
                if ok:
                    self.destroy()
                    self._on_restaurado(msg)
                else:
                    self._lbl_prog.configure(text=f"Erro: {msg}")
                    self._btn_restaurar.configure(state="normal")
            self.after(0, _ui)

        threading.Thread(target=_run, daemon=True).start()
