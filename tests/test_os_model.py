"""
test_os_model.py — Testes do módulo de Ordem de Serviço (OS) do Serenus.

Cobertura por etapa:
  Etapa 1 — Tabelas: criação das 3 tabelas (ordens_servico, itens_os, os_historico)
  Etapa 2 — Numeração: geração sequencial OS-NNNN
  Etapa 3 — CRUD de OS (criar, listar, obter, atualizar, cancelar)
  Etapa 4 — Itens de OS (produtos/serviços, reuso de tabela produtos)
  Etapa 5 — Cálculos (total_materiais, valor_mao_obra, valor_total)
  Etapa 6 — Histórico de alterações
  Etapa 7 — Filtros e busca
"""

import sys
from pathlib import Path
from datetime import date

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers de inserção / builders
# ---------------------------------------------------------------------------

def _dados_os(solicitante_nome: str = "João Silva",
              data: str | None = None) -> dict:
    """Builder de dados para cabeçalho de OS."""
    return {
        "solicitante_nome":  solicitante_nome,
        "solicitante_setor": "TI",
        "solicitante_ramal": "1234",
        "data_solicitacao":  data or date.today().isoformat(),
        "hora_solicitacao":  "09:00",
        "data_execucao":     None,
        "hora_execucao":     "",
        "descricao_servico": "Reparo geral",
        "observacoes":       "",
        "responsavel":       "",
        "status":            "aberta",
        "valor_hora":        0.0,
        "horas_trabalhadas": 0.0,
    }


def _item(descricao: str = "Item Teste",
          quantidade: float = 1.0,
          preco_unit: float = 100.0,
          produto_id: int | None = None,
          observacao: str = "") -> dict:
    return {
        "produto_id": produto_id,
        "descricao":  descricao,
        "quantidade": quantidade,
        "preco_unit": preco_unit,
        "observacao": observacao,
    }


# ---------------------------------------------------------------------------
# Etapa 1 — Database: verifica criação das 3 tabelas
# ---------------------------------------------------------------------------

class TestTabelasOS:
    def test_tabela_ordens_servico_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "ordens_servico" in tabelas

    def test_tabela_itens_os_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "itens_os" in tabelas

    def test_tabela_os_historico_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "os_historico" in tabelas

    def test_colunas_ordens_servico(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute(
                "PRAGMA table_info(ordens_servico)"
            ).fetchall()}
        esperadas = {
            "id", "numero",
            "solicitante_nome", "solicitante_setor", "solicitante_ramal",
            "data_solicitacao", "hora_solicitacao",
            "data_execucao",    "hora_execucao",
            "descricao_servico", "observacoes",
            "responsavel", "status",
            "valor_hora", "horas_trabalhadas",
            "criado_em",
        }
        assert esperadas <= colunas

    def test_colunas_itens_os(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute(
                "PRAGMA table_info(itens_os)"
            ).fetchall()}
        assert {"id", "os_id", "produto_id", "descricao",
                "quantidade", "preco_unit", "subtotal",
                "observacao", "criado_em"} <= colunas

    def test_colunas_os_historico(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute(
                "PRAGMA table_info(os_historico)"
            ).fetchall()}
        assert {"id", "os_id", "campo",
                "valor_anterior", "valor_novo", "alterado_em"} <= colunas

    def test_numero_os_unique(self, banco):
        """numero deve ter constraint UNIQUE para evitar duplicatas."""
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            conn.execute(
                "INSERT INTO ordens_servico (numero, data_solicitacao, criado_em)"
                " VALUES (?,?,?)",
                ("OS-0001", "2026-05-18", agora),
            )
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO ordens_servico (numero, data_solicitacao, criado_em)"
                    " VALUES (?,?,?)",
                    ("OS-0001", "2026-05-18", agora),
                )

    def test_status_check_constraint(self, banco):
        """status só aceita valores válidos."""
        from datetime import datetime
        import sqlite3
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO ordens_servico"
                    " (numero, data_solicitacao, status, criado_em)"
                    " VALUES (?,?,?,?)",
                    ("OS-9999", "2026-05-18", "status_invalido", agora),
                )
