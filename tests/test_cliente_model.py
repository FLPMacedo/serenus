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


# ---------------------------------------------------------------------------
# A2 — CRUD do model (cliente_model.py)
# ---------------------------------------------------------------------------

def _dados_cli(nome: str = "Cliente Teste") -> dict:
    return {
        "nome":       nome,
        "documento":  "111.222.333-44",
        "telefone":   "(31) 3333-4444",
        "whatsapp":   "(31) 99999-0000",
        "email":      "teste@exemplo.com",
        "cep":        "35430-000",
        "endereco":   "Rua Teste, 123",
        "observacao": "",
    }


class TestCRUDClientes:
    def test_salvar_retorna_id(self, banco):
        from views.os.cliente_model import salvar_cliente
        cid = salvar_cliente(_dados_cli())
        assert isinstance(cid, int) and cid > 0

    def test_obter_cliente_devolve_todos_campos(self, banco):
        from views.os.cliente_model import obter_cliente, salvar_cliente
        cid = salvar_cliente(_dados_cli("Maria"))
        c = obter_cliente(cid)
        assert c is not None
        assert c.nome == "Maria"
        assert c.telefone == "(31) 3333-4444"
        assert c.whatsapp == "(31) 99999-0000"
        assert c.email == "teste@exemplo.com"
        assert c.cep == "35430-000"
        assert c.endereco == "Rua Teste, 123"

    def test_obter_inexistente_retorna_none(self, banco):
        from views.os.cliente_model import obter_cliente
        assert obter_cliente(9999) is None

    def test_listar_vazio(self, banco):
        from views.os.cliente_model import listar_clientes
        assert listar_clientes() == []

    def test_listar_ordena_alfabeticamente(self, banco):
        from views.os.cliente_model import listar_clientes, salvar_cliente
        salvar_cliente(_dados_cli("Zelda"))
        salvar_cliente(_dados_cli("Ana"))
        salvar_cliente(_dados_cli("Marco"))
        nomes = [c.nome for c in listar_clientes()]
        assert nomes == ["Ana", "Marco", "Zelda"]

    def test_atualizar_cliente(self, banco):
        from views.os.cliente_model import (
            obter_cliente, salvar_cliente,
        )
        cid = salvar_cliente(_dados_cli("Antes"))
        novo = {**_dados_cli("Depois"), "telefone": "(11) 4444-5555"}
        salvar_cliente(novo, id=cid)
        c = obter_cliente(cid)
        assert c.nome == "Depois"
        assert c.telefone == "(11) 4444-5555"

    def test_excluir_cliente_sem_os(self, banco):
        from views.os.cliente_model import (
            excluir_cliente, listar_clientes, salvar_cliente,
        )
        cid = salvar_cliente(_dados_cli())
        ok, _ = excluir_cliente(cid)
        assert ok is True
        assert listar_clientes() == []

    def test_excluir_cliente_com_os_bloqueado(self, banco):
        """Cliente vinculado a OS não pode ser excluído (mesma sistemática
        de excluir_produto e excluir_conta)."""
        from datetime import datetime
        from database import conectar
        from views.os.cliente_model import excluir_cliente, salvar_cliente
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cid = salvar_cliente(_dados_cli("Vinc"))
        with conectar() as conn:
            conn.execute(
                "INSERT INTO ordens_servico (numero, cliente_id,"
                " data_solicitacao, criado_em) VALUES (?,?,?,?)",
                ("OS-V001", cid, "2026-05-19", agora),
            )
        ok, msg = excluir_cliente(cid)
        assert ok is False
        assert msg != ""
        assert "ordem" in msg.lower() or "servi" in msg.lower()


class TestBuscaCliente:
    def test_buscar_por_nome_parcial(self, banco):
        from views.os.cliente_model import buscar_clientes, salvar_cliente
        salvar_cliente(_dados_cli("Ana Silva"))
        salvar_cliente(_dados_cli("Marco Santos"))
        salvar_cliente(_dados_cli("Carla Silva"))
        resultados = buscar_clientes("silva")
        nomes = sorted(c.nome for c in resultados)
        assert nomes == ["Ana Silva", "Carla Silva"]

    def test_busca_case_insensitive(self, banco):
        from views.os.cliente_model import buscar_clientes, salvar_cliente
        salvar_cliente(_dados_cli("José da Silva"))
        for q in ["josé", "JOSÉ", "José", "jose"]:
            r = buscar_clientes(q)
            # Aceita match com ou sem acento (depende da implementação)
            if q.lower() == "jose":
                # tolera não match (sem normalização de acento)
                continue
            assert len(r) >= 1, f"falhou pra '{q}'"

    def test_busca_vazia_retorna_todos(self, banco):
        from views.os.cliente_model import buscar_clientes, salvar_cliente
        for n in ("A", "B", "C"):
            salvar_cliente(_dados_cli(n))
        assert len(buscar_clientes("")) == 3
        assert len(buscar_clientes(None)) == 3

    def test_busca_documento_e_email_tambem(self, banco):
        """Busca deve cobrir nome E documento E email (mais útil pra usuário)."""
        from views.os.cliente_model import buscar_clientes, salvar_cliente
        salvar_cliente({**_dados_cli("Joao"), "documento": "999.888.777-66",
                        "email": "joao@empresa.com"})
        # busca por trecho do documento
        assert len(buscar_clientes("999.888")) == 1
        # busca por domínio do email
        assert len(buscar_clientes("empresa.com")) == 1
