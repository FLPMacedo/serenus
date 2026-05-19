"""
test_cliente_model.py — Testes do cadastro de clientes para o módulo OS.

Cobertura por etapa:
  A1 — Tabela `clientes` + migração `ordens_servico.cliente_id`
  A2 — CRUD de clientes + busca por nome (próxima etapa)
  A3 — Integração com OS (cliente_id em salvar/atualizar/listar)
  A5 — Histórico de OS por cliente
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# A1 — Schema: tabela clientes + coluna cliente_id em ordens_servico
# ---------------------------------------------------------------------------

class TestTabelaClientes:
    def test_tabela_clientes_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "clientes" in tabelas

    def test_colunas_clientes(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute(
                "PRAGMA table_info(clientes)"
            ).fetchall()}
        esperadas = {
            "id", "nome", "documento", "telefone", "whatsapp",
            "email", "cep", "endereco", "observacao", "criado_em",
        }
        assert esperadas <= colunas

    def test_nome_obrigatorio(self, banco):
        """clientes.nome deve ser NOT NULL."""
        import sqlite3
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO clientes (documento, criado_em) VALUES (?,?)",
                    ("123", agora),
                )

    def test_insere_cliente_minimo(self, banco):
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            cur = conn.execute(
                "INSERT INTO clientes (nome, criado_em) VALUES (?,?)",
                ("Cliente Teste", agora),
            )
            cid = cur.lastrowid
        assert cid > 0


class TestMigracaoOSClienteId:
    def test_coluna_cliente_id_existe(self, banco):
        """ordens_servico precisa ter a coluna cliente_id (adicionada via ALTER)."""
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute(
                "PRAGMA table_info(ordens_servico)"
            ).fetchall()}
        assert "cliente_id" in colunas

    def test_cliente_id_aceita_null(self, banco):
        """cliente_id é opcional (não obriga vincular a cliente cadastrado)."""
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            cur = conn.execute(
                "INSERT INTO ordens_servico (numero, data_solicitacao, criado_em)"
                " VALUES (?,?,?)",
                ("OS-X001", "2026-05-19", agora),
            )
            assert cur.lastrowid > 0
            row = conn.execute(
                "SELECT cliente_id FROM ordens_servico WHERE id=?",
                (cur.lastrowid,),
            ).fetchone()
            assert row["cliente_id"] is None

    def test_cliente_id_fk_valida(self, banco):
        """cliente_id deve referenciar clientes(id) — FK válida funciona."""
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            cur = conn.execute(
                "INSERT INTO clientes (nome, criado_em) VALUES (?,?)",
                ("Cliente FK", agora),
            )
            cid = cur.lastrowid
            cur = conn.execute(
                "INSERT INTO ordens_servico (numero, cliente_id,"
                " data_solicitacao, criado_em) VALUES (?,?,?,?)",
                ("OS-X002", cid, "2026-05-19", agora),
            )
            os_id = cur.lastrowid
        assert os_id > 0

    def test_cliente_id_fk_invalida_falha(self, banco):
        """cliente_id apontando para cliente inexistente deve violar FK."""
        import sqlite3
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO ordens_servico (numero, cliente_id,"
                    " data_solicitacao, criado_em) VALUES (?,?,?,?)",
                    ("OS-X003", 99999, "2026-05-19", agora),
                )


class TestZerarDadosInclueClientes:
    def test_zerar_dados_remove_clientes(self, banco):
        """zerar_dados deve apagar clientes também (respeitando FK das OS)."""
        from datetime import datetime
        from database import conectar, zerar_dados
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            cur = conn.execute(
                "INSERT INTO clientes (nome, criado_em) VALUES (?,?)",
                ("Para apagar", agora),
            )
            cid = cur.lastrowid
            conn.execute(
                "INSERT INTO ordens_servico (numero, cliente_id,"
                " data_solicitacao, criado_em) VALUES (?,?,?,?)",
                ("OS-X100", cid, "2026-05-19", agora),
            )
        zerar_dados()
        with conectar() as conn:
            n = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
        assert n == 0
