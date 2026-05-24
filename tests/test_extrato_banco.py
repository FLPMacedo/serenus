"""
test_extrato_banco.py — Testes do model de lançamentos bancários.
"""
import pytest


@pytest.fixture
def conta(banco):
    from views.fluxo_caixa.conta_banco_model import salvar_conta
    return salvar_conta({"nome": "Nu", "banco": "Nubank", "tipo": "digital"})


@pytest.fixture
def conta_b(banco):
    from views.fluxo_caixa.conta_banco_model import salvar_conta
    return salvar_conta({"nome": "Itau", "banco": "Itau", "tipo": "corrente"})


def _item(data, desc, valor, fitid):
    return {
        "data": data, "descricao": desc, "valor": valor,
        "identificador_unico": fitid,
    }


class TestImportar:
    def test_importar_lista_vazia(self, conta):
        from views.fluxo_caixa.extrato_banco_model import importar
        r = importar(conta, [])
        assert r.novos == 0 and r.duplicados == 0 and r.total == 0

    def test_importar_basico(self, conta):
        from views.fluxo_caixa.extrato_banco_model import importar
        r = importar(conta, [
            _item("2026-05-10", "Compra", -50.0, "a"),
            _item("2026-05-11", "Pix",     30.0, "b"),
        ])
        assert r.novos == 2
        assert r.duplicados == 0

    def test_dedup_por_identificador(self, conta):
        from views.fluxo_caixa.extrato_banco_model import importar
        importar(conta, [_item("2026-05-10", "X", -10.0, "abc")])
        r = importar(conta, [_item("2026-05-10", "X", -10.0, "abc")])
        assert r.novos == 0
        assert r.duplicados == 1

    def test_dedup_e_por_conta(self, conta, conta_b):
        """Mesmo identificador em contas diferentes NÃO duplica."""
        from views.fluxo_caixa.extrato_banco_model import importar, listar_lancamentos_mes
        importar(conta,   [_item("2026-05-10", "X", -10.0, "fitid")])
        importar(conta_b, [_item("2026-05-10", "X", -10.0, "fitid")])
        assert len(listar_lancamentos_mes(5, 2026, conta))   == 1
        assert len(listar_lancamentos_mes(5, 2026, conta_b)) == 1


class TestListar:
    def test_listar_filtra_mes(self, conta):
        from views.fluxo_caixa.extrato_banco_model import importar, listar_lancamentos_mes
        importar(conta, [
            _item("2026-05-10", "Maio A", 10.0, "a"),
            _item("2026-05-20", "Maio B", 20.0, "b"),
            _item("2026-06-05", "Junho",  30.0, "c"),
        ])
        maio = listar_lancamentos_mes(5, 2026, conta)
        assert len(maio) == 2

    def test_listar_filtra_conta(self, conta, conta_b):
        from views.fluxo_caixa.extrato_banco_model import importar, listar_lancamentos_mes
        importar(conta,   [_item("2026-05-10", "A", 10.0, "a")])
        importar(conta_b, [_item("2026-05-10", "B", 20.0, "b")])
        assert len(listar_lancamentos_mes(5, 2026, conta))   == 1
        assert len(listar_lancamentos_mes(5, 2026, conta_b)) == 1
        # Sem filtro de conta = todos
        assert len(listar_lancamentos_mes(5, 2026)) == 2

    def test_listar_ordena_data_desc(self, conta):
        from views.fluxo_caixa.extrato_banco_model import importar, listar_lancamentos_mes
        importar(conta, [
            _item("2026-05-01", "A", 10.0, "a"),
            _item("2026-05-15", "B", 20.0, "b"),
            _item("2026-05-30", "C", 30.0, "c"),
        ])
        lst = listar_lancamentos_mes(5, 2026, conta)
        assert [l.descricao for l in lst] == ["C", "B", "A"]


class TestCategorizar:
    def test_categorizar_saida(self, banco, conta):
        from views.fluxo_caixa.extrato_banco_model import (
            importar, listar_lancamentos_mes, categorizar,
        )
        from database import conectar
        with conectar() as conn:
            pid = conn.execute(
                "SELECT id FROM plano_contas WHERE nome='Supermercado'"
            ).fetchone()["id"]
        importar(conta, [_item("2026-05-10", "X", -50.0, "a")])
        lid = listar_lancamentos_mes(5, 2026, conta)[0].id
        categorizar(lid, plano_conta_id=pid)
        l = listar_lancamentos_mes(5, 2026, conta)[0]
        assert l.plano_conta_id == pid
        assert l.nome_categoria == "Supermercado"

    def test_remover_categoria(self, banco, conta):
        from views.fluxo_caixa.extrato_banco_model import (
            importar, listar_lancamentos_mes, categorizar,
        )
        from database import conectar
        with conectar() as conn:
            pid = conn.execute(
                "SELECT id FROM plano_contas WHERE nome='Supermercado'"
            ).fetchone()["id"]
        importar(conta, [_item("2026-05-10", "X", -50.0, "a")])
        lid = listar_lancamentos_mes(5, 2026, conta)[0].id
        categorizar(lid, plano_conta_id=pid)
        categorizar(lid, plano_conta_id=None, fonte_receita_id=None)
        l = listar_lancamentos_mes(5, 2026, conta)[0]
        assert l.plano_conta_id is None


class TestConciliacao:
    def test_marcar_conciliado(self, conta):
        from views.fluxo_caixa.extrato_banco_model import (
            importar, listar_lancamentos_mes, marcar_conciliado,
        )
        importar(conta, [_item("2026-05-10", "X", -50.0, "a")])
        lid = listar_lancamentos_mes(5, 2026, conta)[0].id
        marcar_conciliado(lid, True)
        assert listar_lancamentos_mes(5, 2026, conta)[0].conciliado is True
        marcar_conciliado(lid, False)
        assert listar_lancamentos_mes(5, 2026, conta)[0].conciliado is False

    def test_listar_nao_conciliados(self, conta):
        from views.fluxo_caixa.extrato_banco_model import (
            importar, marcar_conciliado, listar_lancamentos_mes,
            listar_nao_conciliados,
        )
        importar(conta, [
            _item("2026-05-10", "A", 10.0, "a"),
            _item("2026-05-11", "B", 20.0, "b"),
        ])
        ids = [l.id for l in listar_lancamentos_mes(5, 2026, conta)]
        marcar_conciliado(ids[0], True)
        pendentes = listar_nao_conciliados(conta)
        assert len(pendentes) == 1


class TestResumo:
    def test_resumo_conta(self, conta):
        from views.fluxo_caixa.extrato_banco_model import importar, resumo_conta
        importar(conta, [
            _item("2026-05-01", "+", 100.0, "a"),
            _item("2026-05-02", "+",  50.0, "b"),
            _item("2026-05-03", "-", -30.0, "c"),
        ])
        r = resumo_conta(conta)
        assert r["total"] == 3
        assert r["entradas"] == pytest.approx(150.0)
        assert r["saidas"] == pytest.approx(30.0)
        assert r["saldo_mov"] == pytest.approx(120.0)
        assert r["conciliados"] == 0
        assert r["sem_categoria"] == 3


class TestExcluir:
    def test_excluir_individual(self, conta):
        from views.fluxo_caixa.extrato_banco_model import (
            importar, listar_lancamentos_mes, excluir_lancamento,
        )
        importar(conta, [_item("2026-05-10", "X", -50.0, "a")])
        lid = listar_lancamentos_mes(5, 2026, conta)[0].id
        excluir_lancamento(lid)
        assert listar_lancamentos_mes(5, 2026, conta) == []

    def test_excluir_todos_da_conta(self, conta):
        from views.fluxo_caixa.extrato_banco_model import (
            importar, excluir_lancamentos_conta, listar_lancamentos_mes,
        )
        importar(conta, [
            _item("2026-05-10", "A", 10.0, "a"),
            _item("2026-05-11", "B", 20.0, "b"),
        ])
        n = excluir_lancamentos_conta(conta)
        assert n == 2
        assert listar_lancamentos_mes(5, 2026, conta) == []
