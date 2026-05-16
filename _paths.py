"""
_paths.py — Serenus
Resolve caminhos de recursos e dados do usuário de forma compatível
com execução normal (Python) e empacotada (PyInstaller --onefile).

Recursos estáticos (imagens):
  Em desenvolvimento → pasta raiz do projeto
  Empacotado        → sys._MEIPASS (extração temporária do bundle)

Dados do usuário (banco, backups, tokens):
  Windows -> %APPDATA%/Serenus
  macOS / Linux -> ~/.serenus
  Sempre persistente entre execuções — nunca dentro do bundle.
"""

import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Resolvedores internos
# ---------------------------------------------------------------------------

def _base_recursos() -> Path:
    """Raiz onde ficam os recursos estáticos (imagens, ícones)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def _base_dados() -> Path:
    """Pasta persistente para dados do usuário (banco, backups, tokens)."""
    import os
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        base = Path.home()
    pasta = base / "Serenus"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


# ---------------------------------------------------------------------------
# Caminhos exportados
# ---------------------------------------------------------------------------

RECURSOS        = _base_recursos()
DADOS           = _base_dados()

DATABASE_PATH   = DADOS / "serenus.db"
BACKUPS_DIR     = DADOS / "backups"
TOKEN_PATH      = DADOS / "google_token.json"
SECRETS_PATH    = DADOS / "client_secrets.json"
IMAGENS_DIR     = RECURSOS / "imagens"
