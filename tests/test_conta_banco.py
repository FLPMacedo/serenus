"""
test_conta_banco.py — Testes do CRUD de contas bancárias.
"""
import pytest


class TestSalvarConta:
    def test_criar_conta_basica(self, banco):
        from views.fluxo_caixa.conta_banco_model import salvar_conta, listar_contas
        cid = salvar_conta({
            "nome": "Nubank Principal",
            "banco": "Nubank",
            "tipo": "digital",
            "agencia": "0001",
            "numero": "56380208-2",
            "saldo_inicial": 100.0,
        })
        assert isinstance(cid, int) and cid > 0
        contas = listar_contas()
        assert len(contas) == 1
        assert contas[0].nome == "Nubank Principal"
        assert contas[0].banco == "Nubank"
        assert contas[0].tipo == "digital"
        assert contas[0].saldo_inicial == pytest.approx(100.0)

    def test_nome_vazio_falha(self, banco):
        from views.fluxo_caixa.conta_banco_model import salvar_conta
        with pytest.raises(ValueError):
            salvar_conta({"nome": "   "})

    def test_tipo_invalido_falha(self, banco):
        from views.fluxo_caixa.conta_banco_model import salvar_conta
        with pytest.raises(ValueError):
            salvar_conta({"nome": "X", "tipo": "investimento"})

    def test_saldo_inicial_default_zero(self, banco):
        from views.fluxo_caixa.conta_banco_model import salvar_conta, listar_contas
        salvar_conta({"nome": "X"})
        assert listar_contas()[0].saldo_inicial == 0.0

    def test_ativa_default_true(self, banco):
        from views.fluxo_caixa.conta_banco_model import salvar_conta, listar_contas
        salvar_conta({"nome": "X"})
        assert listar_contas()[0].ativa is True


class TestListar:
    def test_listar_vazio(self, banco):
        from views.fluxo_caixa.conta_banco_model import listar_contas
        assert listar_contas() == []

    def test_listar_filtra_inativas(self, banco):
        from views.fluxo_caixa.conta_banco_model import (
            salvar_conta, atualizar_conta, listar_contas,
        )
        c1 = salvar_conta({"nome": "Ativa"})
        c2 = salvar_conta({"nome": "Inativa"})
        atualizar_conta(c2, {"nome": "Inativa", "ativa": False})
        assert len(listar_contas()) == 2
        assert len(listar_contas(apenas_ativas=True)) == 1

    def test_listar_ordena_por_nome(self, banco):
        from views.fluxo_caixa.conta_banco_model import salvar_conta, listar_contas
        salvar_conta({"nome": "Zeta"})
        salvar_conta({"nome": "Alfa"})
        salvar_conta({"nome": "Beta"})
        nomes = [c.nome for c in listar_contas()]
        assert nomes == ["Alfa", "Beta", "Zeta"]


class TestObter:
    def test_obter_existente(self, banco):
        from views.fluxo_caixa.conta_banco_model import salvar_conta, obter_conta
        cid = salvar_conta({"nome": "X"})
        c = obter_conta(cid)
        assert c is not None
        assert c.id == cid

    def test_obter_inexistente_retorna_none(self, banco):
        from views.fluxo_caixa.conta_banco_model import obter_conta
        assert obter_conta(999) is None


class TestAtualizar:
    def test_atualizar_campos(self, banco):
        from views.fluxo_caixa.conta_banco_model import (
            salvar_conta, atualizar_conta, obter_conta,
        )
        cid = salvar_conta({"nome": "Original"})
        atualizar_conta(cid, {
            "nome": "Renomeada", "banco": "Itaú",
            "tipo": "corrente", "saldo_inicial": 500.0,
        })
        c = obter_conta(cid)
        assert c.nome == "Renomeada"
        assert c.banco == "Itaú"
        assert c.tipo == "corrente"
        assert c.saldo_inicial == 500.0


class TestExcluir:
    def test_excluir_conta(self, banco):
        from views.fluxo_caixa.conta_banco_model import (
            salvar_conta, excluir_conta, listar_contas,
        )
        cid = salvar_conta({"nome": "X"})
        ok, msg = excluir_conta(cid)
        assert ok is True
        assert listar_contas() == []

    def test_excluir_inexistente_retorna_false(self, banco):
        from views.fluxo_caixa.conta_banco_model import excluir_conta
        ok, msg = excluir_conta(999)
        assert ok is False

    def test_excluir_cascateia_lancamentos(self, banco):
        """Conforme ON DELETE CASCADE: apagar conta apaga seus lançamentos."""
        from views.fluxo_caixa.conta_banco_model import salvar_conta, excluir_conta
        from views.fluxo_caixa.extrato_banco_model import importar, listar_lancamentos_mes
        cid = salvar_conta({"nome": "X"})
        importar(cid, [{
            "data": "2026-05-10", "descricao": "T",
            "valor": 10.0, "identificador_unico": "abc",
        }])
        assert len(listar_lancamentos_mes(5, 2026, cid)) == 1
        excluir_conta(cid)
        assert listar_lancamentos_mes(5, 2026) == []


class TestSaldoAtual:
    def test_saldo_inicial_sem_lancamentos(self, banco):
        from views.fluxo_caixa.conta_banco_model import salvar_conta, saldo_atual_conta
        cid = salvar_conta({"nome": "X", "saldo_inicial": 100.0})
        assert saldo_atual_conta(cid) == pytest.approx(100.0)

    def test_saldo_com_lancamentos(self, banco):
        from views.fluxo_caixa.conta_banco_model import salvar_conta, saldo_atual_conta
        from views.fluxo_caixa.extrato_banco_model import importar
        cid = salvar_conta({"nome": "X", "saldo_inicial": 50.0})
        importar(cid, [
            {"data": "2026-05-10", "descricao": "+ T", "valor":  30.0, "identificador_unico": "a"},
            {"data": "2026-05-15", "descricao": "- T", "valor": -10.0, "identificador_unico": "b"},
        ])
        # 50 + 30 - 10 = 70
        assert saldo_atual_conta(cid) == pytest.approx(70.0)
