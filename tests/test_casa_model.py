"""
test_casa_model.py — Testes do módulo Compras de Casa.

Cobertura por etapa:
  C1 — Schema itens_estoque
  C2 — CRUD + listar_lista_compras (estoque <= mínimo)
  C3/C4 — UI (smoke import)
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# C1 — Schema: itens_estoque
# ---------------------------------------------------------------------------

class TestTabelaItensEstoque:
    def test_tabela_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "itens_estoque" in tabelas

    def test_colunas(self, banco):
        from database import conectar
        with conectar() as conn:
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(itens_estoque)"
            ).fetchall()}
        esperadas = {
            "id", "nome", "categoria", "unidade",
            "estoque_atual", "estoque_minimo",
            "observacao", "ativo", "criado_em",
        }
        assert esperadas <= cols

    def test_nome_obrigatorio(self, banco):
        import sqlite3
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO itens_estoque (categoria, criado_em)"
                    " VALUES (?, ?)",
                    ("Mercearia", agora),
                )

    def test_insere_item_minimo(self, banco):
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            cur = conn.execute(
                "INSERT INTO itens_estoque (nome, criado_em) VALUES (?, ?)",
                ("Arroz", agora),
            )
            iid = cur.lastrowid
            row = conn.execute(
                "SELECT estoque_atual, estoque_minimo, ativo"
                " FROM itens_estoque WHERE id=?", (iid,),
            ).fetchone()
        # Defaults razoáveis
        assert iid > 0
        assert row["estoque_atual"] == 0
        assert row["estoque_minimo"] == 0
        assert row["ativo"] == 1


class TestZerarDadosInclueItensEstoque:
    def test_zerar_dados_remove_itens_estoque(self, banco):
        from datetime import datetime
        from database import conectar, zerar_dados
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            conn.execute(
                "INSERT INTO itens_estoque (nome, criado_em) VALUES (?,?)",
                ("Apagar", agora),
            )
        zerar_dados()
        with conectar() as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM itens_estoque"
            ).fetchone()[0]
        assert n == 0
