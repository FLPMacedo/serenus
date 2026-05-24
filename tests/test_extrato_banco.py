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


class TestReaplicarRegras:
    def test_reaplicar_em_lancamentos_existentes(self, banco, conta):
        """Cenário típico: user importa primeiro, cadastra regra depois."""
        from views.fluxo_caixa.extrato_banco_model import (
            importar, listar_lancamentos_mes, reaplicar_regras,
        )
        from views.fluxo_caixa.regras_categoria_model import salvar_regra
        from database import conectar
        with conectar() as conn:
            pid = conn.execute(
                "SELECT id FROM plano_contas WHERE nome='Restaurantes / Delivery'"
            ).fetchone()["id"]

        # 1. Importa sem regra (todos ficam sem categoria)
        importar(conta, [
            _item("2026-05-10", "LANCHONETE X", -10.0, "a"),
            _item("2026-05-11", "POSTO Y",      -50.0, "b"),
        ])
        lst = listar_lancamentos_mes(5, 2026, conta)
        assert all(l.plano_conta_id is None for l in lst)

        # 2. Cadastra regra
        salvar_regra({"padrao": "LANCHONETE", "tipo": "saida",
                      "plano_conta_id": pid})

        # 3. Re-aplica
        n = reaplicar_regras(conta)
        assert n == 1, f"esperava 1 categorizado, veio {n}"

        # 4. Verifica DB
        lst = listar_lancamentos_mes(5, 2026, conta)
        cat = next(l for l in lst if "LANCHONETE" in l.descricao)
        nao_cat = next(l for l in lst if "POSTO" in l.descricao)
        assert cat.plano_conta_id == pid
        assert nao_cat.plano_conta_id is None

    def test_apenas_sem_categoria_preserva_manuais(self, banco, conta):
        """User categorizou X manualmente; regra que casaria com X NÃO deve
        sobrescrever quando apenas_sem_categoria=True (padrão)."""
        from views.fluxo_caixa.extrato_banco_model import (
            importar, listar_lancamentos_mes, reaplicar_regras, categorizar,
        )
        from views.fluxo_caixa.regras_categoria_model import salvar_regra
        from database import conectar
        with conectar() as conn:
            p_super = conn.execute(
                "SELECT id FROM plano_contas WHERE nome='Supermercado'"
            ).fetchone()["id"]
            p_rest = conn.execute(
                "SELECT id FROM plano_contas WHERE nome='Restaurantes / Delivery'"
            ).fetchone()["id"]

        importar(conta, [_item("2026-05-10", "LANCHONETE X", -10.0, "a")])
        lid = listar_lancamentos_mes(5, 2026, conta)[0].id
        # User categoriza manualmente
        categorizar(lid, plano_conta_id=p_super)

        # Cadastra regra que casaria
        salvar_regra({"padrao": "LANCHONETE", "tipo": "saida",
                      "plano_conta_id": p_rest})

        # Re-aplica com apenas_sem_categoria=True (padrão) — NÃO sobrescreve
        n = reaplicar_regras(conta)
        assert n == 0
        assert listar_lancamentos_mes(5, 2026, conta)[0].plano_conta_id == p_super

        # Com apenas_sem_categoria=False — sobrescreve
        n = reaplicar_regras(conta, apenas_sem_categoria=False)
        assert n == 1
        assert listar_lancamentos_mes(5, 2026, conta)[0].plano_conta_id == p_rest

    def test_filtra_por_conta(self, banco, conta, conta_b):
        from views.fluxo_caixa.extrato_banco_model import (
            importar, listar_lancamentos_mes, reaplicar_regras,
        )
        from views.fluxo_caixa.regras_categoria_model import salvar_regra
        from database import conectar
        with conectar() as conn:
            pid = conn.execute(
                "SELECT id FROM plano_contas WHERE nome='Supermercado'"
            ).fetchone()["id"]

        importar(conta,   [_item("2026-05-10", "MERCADO X", -10.0, "a")])
        importar(conta_b, [_item("2026-05-11", "MERCADO Y", -20.0, "b")])
        salvar_regra({"padrao": "MERCADO", "tipo": "saida",
                      "plano_conta_id": pid})

        # Reaplica só na conta A
        n = reaplicar_regras(conta)
        assert n == 1
        # Conta A categorizada, conta B não
        assert listar_lancamentos_mes(5, 2026, conta)[0].plano_conta_id == pid
        assert listar_lancamentos_mes(5, 2026, conta_b)[0].plano_conta_id is None


class TestVincularContaPagar:
    @pytest.fixture
    def conta_pagar_factory(self, banco):
        from database import conectar
        from datetime import datetime
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def _criar(valor, data_venc, descricao="X", status="pendente"):
            with conectar() as conn:
                cur = conn.execute(
                    "INSERT INTO contas_pagar (descricao, valor, data_vencimento,"
                    " status, criado_em) VALUES (?, ?, ?, ?, ?)",
                    (descricao, valor, data_venc, status, agora),
                )
                return cur.lastrowid
        return _criar

    def test_candidatas_match_exato(self, banco, conta_pagar_factory):
        from views.fluxo_caixa.extrato_banco_model import candidatas_para_vincular
        cp_id = conta_pagar_factory(100.0, "2026-05-10", "Energia")
        # Lançamento de saída de R$ 100 no mesmo dia
        cands = candidatas_para_vincular("2026-05-10", -100.0)
        assert len(cands) == 1
        assert cands[0].id == cp_id
        assert cands[0].valor == pytest.approx(100.0)

    def test_candidatas_tolera_diferenca_de_dias(self, banco, conta_pagar_factory):
        from views.fluxo_caixa.extrato_banco_model import candidatas_para_vincular
        # Conta vence dia 10, pagamento real cai no dia 12
        conta_pagar_factory(50.0, "2026-05-10")
        cands = candidatas_para_vincular("2026-05-12", -50.0, dias_tolerancia=5)
        assert len(cands) == 1

    def test_candidatas_filtra_canceladas(self, banco, conta_pagar_factory):
        from views.fluxo_caixa.extrato_banco_model import candidatas_para_vincular
        conta_pagar_factory(100.0, "2026-05-10", status="cancelado")
        assert candidatas_para_vincular("2026-05-10", -100.0) == []

    def test_candidatas_filtra_por_valor(self, banco, conta_pagar_factory):
        from views.fluxo_caixa.extrato_banco_model import candidatas_para_vincular
        conta_pagar_factory(100.0, "2026-05-10")
        # Valor diferente — não casa
        assert candidatas_para_vincular("2026-05-10", -200.0) == []

    def test_vincular_persiste_no_lancamento(self, banco, conta, conta_pagar_factory):
        from views.fluxo_caixa.extrato_banco_model import (
            importar, listar_lancamentos_mes, vincular_conta_pagar,
        )
        cp_id = conta_pagar_factory(50.0, "2026-05-10")
        importar(conta, [_item("2026-05-10", "Energia", -50.0, "a")])
        lid = listar_lancamentos_mes(5, 2026, conta)[0].id
        vincular_conta_pagar(lid, cp_id)
        l = listar_lancamentos_mes(5, 2026, conta)[0]
        assert l.conta_pagar_id == cp_id

    def test_desvincular(self, banco, conta, conta_pagar_factory):
        from views.fluxo_caixa.extrato_banco_model import (
            importar, listar_lancamentos_mes, vincular_conta_pagar,
        )
        cp_id = conta_pagar_factory(50.0, "2026-05-10")
        importar(conta, [_item("2026-05-10", "X", -50.0, "a")])
        lid = listar_lancamentos_mes(5, 2026, conta)[0].id
        vincular_conta_pagar(lid, cp_id)
        vincular_conta_pagar(lid, None)
        assert listar_lancamentos_mes(5, 2026, conta)[0].conta_pagar_id is None


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
