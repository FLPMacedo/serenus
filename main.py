"""
main.py — Ponto de entrada do Serenus.
"""

import threading
import customtkinter as ctk
from database import inicializar_banco, setup_completo
from views.setup_view import SetupView
from views.main_window import MainWindow


def _verificar_backup_automatico():
    """Executa backup agendado em background se estiver na hora."""
    try:
        import backup_manager as bm
        if bm.backup_agendado_necessario():
            ok, resultado = bm.fazer_backup()
            import google_drive as gd
            from pathlib import Path
            if ok and gd.esta_conectado():
                gd.upload_backup(Path(resultado))
    except Exception:
        pass  # Não interrompe a inicialização por falha de backup


def _pos_autenticacao(app):
    """Chamado após login bem-sucedido (ou direto se não há senha)."""
    if not setup_completo():
        def on_setup_concluido(tema: str):
            ctk.set_appearance_mode("dark" if tema == "escuro" else "light")
            app._reload_layout()
        app.after(200, lambda: SetupView(app, on_setup_concluido))


def main():
    inicializar_banco()

    # Verifica backup automático em thread separada (não bloqueia a UI)
    threading.Thread(target=_verificar_backup_automatico, daemon=True).start()

    app = MainWindow()

    from database import tem_senha
    if tem_senha():
        # Oculta a janela principal e exibe o login via after
        # (garante que o mainloop já está rodando quando o diálogo aparecer)
        app.withdraw()

        def _abrir_login():
            from views.auth_dialog import SenhaLoginDialog

            def _resultado(autenticado: bool):
                if autenticado:
                    app.deiconify()
                    _pos_autenticacao(app)
                else:
                    app.destroy()

            SenhaLoginDialog(app, on_resultado=_resultado)

        app.after(50, _abrir_login)
    else:
        _pos_autenticacao(app)

    app.mainloop()


if __name__ == "__main__":
    main()
