"""
google_drive.py — Integração com Google Drive para backup do Serenus.
Instala as bibliotecas automaticamente na primeira conexão.
Requer client_secrets.json configurado pelo desenvolvedor.
"""

from __future__ import annotations
import sys
import json
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

from _paths import TOKEN_PATH, SECRETS_PATH
SCOPES          = ["https://www.googleapis.com/auth/drive.file"]
PASTA_DRIVE     = "Serenus/Backups"


# ---------------------------------------------------------------------------
# Verificação / instalação de bibliotecas
# ---------------------------------------------------------------------------

def _bibliotecas_disponiveis() -> bool:
    try:
        import google.oauth2.credentials          # noqa: F401
        import google_auth_oauthlib.flow          # noqa: F401
        import googleapiclient.discovery          # noqa: F401
        return True
    except ImportError:
        return False


def instalar_bibliotecas(progresso_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Instala google-auth-oauthlib e google-api-python-client via pip.
    progresso_cb(mensagem) é chamado com atualizações de status.
    Retorna True se instalação bem-sucedida.
    """
    if _bibliotecas_disponiveis():
        return True

    if progresso_cb:
        progresso_cb("Instalando bibliotecas Google…")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "google-auth-oauthlib", "google-api-python-client",
             "--quiet", "--disable-pip-version-check"],
            capture_output=True, text=True, timeout=120
        )
        ok = result.returncode == 0
        if progresso_cb:
            progresso_cb("Bibliotecas instaladas." if ok else f"Erro: {result.stderr[:200]}")
        return ok
    except Exception as exc:
        if progresso_cb:
            progresso_cb(f"Erro na instalação: {exc}")
        return False


# ---------------------------------------------------------------------------
# Estado de conexão
# ---------------------------------------------------------------------------

def esta_conectado() -> bool:
    """Verifica se o token existe e é válido sem fazer requisição de rede."""
    if not TOKEN_PATH.exists():
        return False
    try:
        with open(TOKEN_PATH) as f:
            data = json.load(f)
        return bool(data.get("token") or data.get("access_token"))
    except (json.JSONDecodeError, OSError):
        return False


def obter_email() -> str:
    """Lê o e-mail salvo no token. Retorna '' se não disponível."""
    if not TOKEN_PATH.exists():
        return ""
    try:
        with open(TOKEN_PATH) as f:
            data = json.load(f)
        return data.get("_email", "")
    except (json.JSONDecodeError, OSError):
        return ""


def client_secrets_existe() -> bool:
    return SECRETS_PATH.exists()


# ---------------------------------------------------------------------------
# OAuth — conexão
# ---------------------------------------------------------------------------

def conectar_drive_async(
    sucesso_cb:  Callable[[str], None],
    erro_cb:     Callable[[str], None],
    progresso_cb: Optional[Callable[[str], None]] = None,
):
    """
    Inicia o fluxo OAuth em uma thread separada para não bloquear a UI.
    Chama sucesso_cb(email) ou erro_cb(mensagem) ao finalizar.
    """
    def _run():
        if not instalar_bibliotecas(progresso_cb):
            erro_cb("Não foi possível instalar as bibliotecas Google.")
            return

        if not SECRETS_PATH.exists():
            erro_cb(
                "client_secrets.json não encontrado.\n"
                "Configure um projeto no Google Cloud Console e baixe\n"
                "o arquivo de credenciais OAuth para a pasta do Serenus."
            )
            return

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            if progresso_cb:
                progresso_cb("Abrindo navegador para autenticação…")

            flow = InstalledAppFlow.from_client_secrets_file(
                str(SECRETS_PATH), scopes=SCOPES
            )
            # run_local_server abre o navegador e aguarda callback
            creds = flow.run_local_server(port=0, open_browser=True)

            # Busca e-mail do usuário
            email = ""
            try:
                service = build("oauth2", "v2", credentials=creds)
                info = service.userinfo().get().execute()
                email = info.get("email", "")
            except Exception:
                pass

            # Persiste token + e-mail
            token_data = json.loads(creds.to_json())
            token_data["_email"] = email
            with open(TOKEN_PATH, "w") as f:
                json.dump(token_data, f, indent=2)

            sucesso_cb(email)

        except Exception as exc:
            erro_cb(f"Erro na autenticação: {exc}")

    threading.Thread(target=_run, daemon=True).start()


def desconectar():
    """Remove o token local."""
    try:
        TOKEN_PATH.unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Upload para o Drive
# ---------------------------------------------------------------------------

def _obter_credenciais():
    """Carrega e atualiza credenciais do token salvo."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    with open(TOKEN_PATH) as f:
        data = json.load(f)

    # Remove campo interno antes de construir Credentials
    data_limpo = {k: v for k, v in data.items() if not k.startswith("_")}
    creds = Credentials.from_authorized_user_info(data_limpo, SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Re-salva token atualizado
        token_data = json.loads(creds.to_json())
        token_data["_email"] = data.get("_email", "")
        with open(TOKEN_PATH, "w") as f:
            json.dump(token_data, f, indent=2)

    return creds


def _obter_ou_criar_pasta(service) -> str:
    """Localiza ou cria a pasta Serenus/Backups/ no Drive. Retorna o folder_id."""
    # Pasta raiz Serenus
    query = "name='Serenus' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    res = service.files().list(q=query, fields="files(id)").execute()
    files = res.get("files", [])
    if files:
        serenus_id = files[0]["id"]
    else:
        meta = {"name": "Serenus", "mimeType": "application/vnd.google-apps.folder"}
        serenus_id = service.files().create(body=meta, fields="id").execute()["id"]

    # Sub-pasta Backups dentro de Serenus
    query = (f"name='Backups' and mimeType='application/vnd.google-apps.folder'"
             f" and '{serenus_id}' in parents and trashed=false")
    res = service.files().list(q=query, fields="files(id)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    else:
        meta = {"name": "Backups",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [serenus_id]}
        return service.files().create(body=meta, fields="id").execute()["id"]


def upload_backup(caminho_arquivo: Path,
                  progresso_cb: Optional[Callable[[str], None]] = None) -> tuple[bool, str]:
    """
    Faz upload do arquivo de backup para Google Drive.
    Retorna (sucesso, mensagem).
    """
    if not esta_conectado():
        return False, "Drive não conectado."
    if not _bibliotecas_disponiveis():
        return False, "Bibliotecas não instaladas."

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        if progresso_cb:
            progresso_cb("Conectando ao Google Drive…")

        creds   = _obter_credenciais()
        service = build("drive", "v3", credentials=creds)
        pasta_id = _obter_ou_criar_pasta(service)

        if progresso_cb:
            progresso_cb(f"Enviando {caminho_arquivo.name}…")

        media = MediaFileUpload(str(caminho_arquivo), mimetype="application/octet-stream")
        meta  = {"name": caminho_arquivo.name, "parents": [pasta_id]}
        service.files().create(body=meta, media_body=media, fields="id").execute()

        if progresso_cb:
            progresso_cb("Upload concluído.")
        return True, "Upload para Google Drive concluído."

    except Exception as exc:
        return False, str(exc)


def fazer_backup_drive(caminho_arquivo: Path,
                       progresso_cb: Optional[Callable[[str], None]] = None) -> tuple[bool, str]:
    """Upload assíncrono — executa em thread para não bloquear a UI."""
    resultado: list = []

    def _run():
        ok, msg = upload_backup(caminho_arquivo, progresso_cb)
        resultado.extend([ok, msg])

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=60)

    if not resultado:
        return False, "Timeout no upload."
    return resultado[0], resultado[1]
