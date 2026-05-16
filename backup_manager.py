"""
backup_manager.py — Gerenciamento de backups locais do Serenus.
Cópia do banco, limpeza automática, agendamento e restauração.
"""

from __future__ import annotations
import shutil
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional

from database import CAMINHO_BANCO, conectar, obter_configuracao, salvar_configuracao

DIRETORIO_BASE   = Path(__file__).parent
PASTA_BACKUPS    = DIRETORIO_BASE / "backups"
MAX_BACKUPS_PADRAO = 30


# ---------------------------------------------------------------------------
# Estrutura de backup
# ---------------------------------------------------------------------------

def _pasta_backups() -> Path:
    PASTA_BACKUPS.mkdir(exist_ok=True)
    return PASTA_BACKUPS


# ---------------------------------------------------------------------------
# Backup local
# ---------------------------------------------------------------------------

def fazer_backup(destino_drive: bool = False) -> tuple[bool, str]:
    """
    Copia serenus.db para backups/serenus_backup_YYYYMMDD_HHMMSS.db.
    Registra no banco e limpa os mais antigos.
    Retorna (sucesso, caminho_ou_mensagem_erro).
    """
    try:
        pasta = _pasta_backups()
        agora = datetime.now()
        nome  = f"serenus_backup_{agora.strftime('%Y%m%d_%H%M%S')}.db"
        destino = pasta / nome

        shutil.copy2(CAMINHO_BANCO, destino)

        tamanho_kb = destino.stat().st_size / 1024
        _registrar(nome, tamanho_kb, "local", "ok")
        _limpar_antigos()

        salvar_configuracao("backup_ultimo_automatico", agora.isoformat())
        return True, str(destino)

    except Exception as exc:
        _registrar("—", 0, "local", "erro", observacao=str(exc))
        return False, str(exc)


def _registrar(arquivo: str, tamanho_kb: float, destino: str,
               status: str, observacao: str = ""):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        conn.execute("""
            INSERT INTO backups (data_hora, arquivo, tamanho_kb, destino, status, observacao)
            VALUES (?,?,?,?,?,?)
        """, (agora, arquivo, tamanho_kb, destino, status, observacao))


def _limpar_antigos():
    """Mantém apenas os N backups locais mais recentes."""
    max_n = int(obter_configuracao("backup_max_local", str(MAX_BACKUPS_PADRAO)))
    pasta = _pasta_backups()
    arquivos = sorted(pasta.glob("serenus_backup_*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in arquivos[max_n:]:
        try:
            f.unlink()
        except OSError:
            pass


def listar_backups_locais() -> list[dict]:
    """Retorna lista de backups locais ordenados do mais recente ao mais antigo."""
    pasta = _pasta_backups()
    arquivos = sorted(pasta.glob("serenus_backup_*.db"),
                      key=lambda f: f.stat().st_mtime, reverse=True)
    resultado = []
    for f in arquivos:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        resultado.append({
            "nome":       f.name,
            "caminho":    f,
            "tamanho_kb": f.stat().st_size / 1024,
            "data":       mtime.strftime("%d/%m/%Y %H:%M:%S"),
            "data_ord":   mtime,
        })
    return resultado


def historico_backups(limite: int = 50) -> list:
    """Lê o histórico da tabela backups no banco."""
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM backups ORDER BY data_hora DESC LIMIT ?", (limite,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Restauração
# ---------------------------------------------------------------------------

def restaurar_backup(caminho_backup: Path,
                     progresso_cb=None) -> tuple[bool, str]:
    """
    Restaura um backup:
    1. Faz backup de segurança do banco atual.
    2. Copia o arquivo selecionado sobre serenus.db.
    Retorna (sucesso, mensagem).
    """
    try:
        if progresso_cb:
            progresso_cb("Fazendo backup de segurança…", 0.2)
        ok, msg = fazer_backup()
        if not ok:
            return False, f"Erro no backup de segurança: {msg}"

        if progresso_cb:
            progresso_cb("Restaurando banco de dados…", 0.6)
        shutil.copy2(caminho_backup, CAMINHO_BANCO)

        if progresso_cb:
            progresso_cb("Concluído.", 1.0)
        return True, "Restauração concluída. Reinicie o Serenus para carregar os dados."

    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Agendamento automático
# ---------------------------------------------------------------------------

def backup_agendado_necessario() -> bool:
    """Verifica se é hora de executar o backup automático."""
    freq = obter_configuracao("backup_frequencia", "desativado")
    if freq == "desativado":
        return False

    ultimo_str = obter_configuracao("backup_ultimo_automatico", "")
    if not ultimo_str:
        return True

    try:
        ultimo = datetime.fromisoformat(ultimo_str)
    except ValueError:
        return True

    agora = datetime.now()
    delta = {
        "diario":  timedelta(days=1),
        "semanal": timedelta(weeks=1),
        "mensal":  timedelta(days=30),
    }.get(freq)

    return delta is not None and (agora - ultimo) >= delta


def proximo_backup_previsto() -> str:
    """Texto legível com o próximo backup agendado."""
    freq = obter_configuracao("backup_frequencia", "desativado")
    if freq == "desativado":
        return "Desativado"

    ultimo_str = obter_configuracao("backup_ultimo_automatico", "")
    if not ultimo_str:
        return "Em breve"

    try:
        ultimo = datetime.fromisoformat(ultimo_str)
    except ValueError:
        return "Em breve"

    delta = {
        "diario":  timedelta(days=1),
        "semanal": timedelta(weeks=1),
        "mensal":  timedelta(days=30),
    }.get(freq)

    if delta is None:
        return "—"

    proximo = ultimo + delta
    return proximo.strftime("%d/%m/%Y %H:%M")


def ultimo_backup_str() -> str:
    """Data/hora do último backup registrado."""
    ultimo_str = obter_configuracao("backup_ultimo_automatico", "")
    if not ultimo_str:
        return "Nenhum backup realizado"
    try:
        dt = datetime.fromisoformat(ultimo_str)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return ultimo_str
