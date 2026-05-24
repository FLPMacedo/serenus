"""
test_lancamentos_manuais.py — Testes do model de lançamentos manuais de caixa.

Lançamento manual é uma entrada ou saída pontual de dinheiro que não vem de
contas_pagar nem de fontes_receita automáticas (ex.: recebi R$ 50 em dinheiro,
paguei lanche em espécie). Tem categoria obrigatória — se entrada, vincula a
fontes_receita; se saída, vincula a plano_contas.
"""

import pytest
import sqlite3


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures locais
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def plano_supermercado(banco):
    """Categoria de saída — usa o padrão 'Supermercado'."""
    from database import conectar
    with conectar() as conn:
        row = conn.execute(
            "SELECT id FROM plano_contas WHERE nome = 'Supermercado'"
        ).fetchone()
    return row["id"]


@pytest.fixture
def fonte_clt(banco):
    """Categoria de entrada — cria uma fonte CLT de teste."""
    from database import conectar
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO fontes_receita (nome, tipo, valor_mensal, ativa, criado_em)"
            " VALUES ('Salário CLT Teste', 'clt', 5000.0, 1, '2026-01-01')"
        )
        return cur.lastrowid


# ─────────────────────────────────────────────────────────────────────────────
# CRUD básico
# ─────────────────────────────────────────────────────────────────────────────

class TestCriarLancamento:
    def test_criar_saida_retorna_id(self, banco, plano_supermercado):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        id_ = salvar_lancamento({
            "data":           "2026-05-23",
            "descricao":      "Compra em dinheiro no mercadinho",
            "tipo":           "saida",
            "plano_conta_id": plano_supermercado,
            "valor":          47.50,
            "observacao":     "",
        })
        assert isinstance(id_, int) and id_ > 0

    def test_criar_entrada_retorna_id(self, banco, fonte_clt):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        id_ = salvar_lancamento({
            "data":             "2026-05-23",
            "descricao":        "Recebi em espécie",
            "tipo":             "entrada",
            "fonte_receita_id": fonte_clt,
            "valor":            150.00,
            "observacao":       "Pagamento de freela",
        })
        assert isinstance(id_, int) and id_ > 0

    def test_saida_sem_plano_conta_falha(self, banco, fonte_clt):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            salvar_lancamento({
                "data":             "2026-05-23",
                "descricao":        "X",
                "tipo":             "saida",
                "fonte_receita_id": fonte_clt,  # errado — saída exige plano
                "valor":            10.0,
            })

    def test_entrada_sem_fonte_falha(self, banco, plano_supermercado):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            salvar_lancamento({
                "data":           "2026-05-23",
                "descricao":      "X",
                "tipo":           "entrada",
                "plano_conta_id": plano_supermercado,  # errado — entrada exige fonte
                "valor":            10.0,
            })

    def test_valor_zero_falha(self, banco, plano_supermercado):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            salvar_lancamento({
                "data":           "2026-05-23",
                "descricao":      "X",
                "tipo":           "saida",
                "plano_conta_id": plano_supermercado,
                "valor":          0.0,
            })

    def test_valor_negativo_falha(self, banco, plano_supermercado):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            salvar_lancamento({
                "data":           "2026-05-23",
                "descricao":      "X",
                "tipo":           "saida",
                "plano_conta_id": plano_supermercado,
                "valor":          -10.0,
            })

    def test_descricao_vazia_falha(self, banco, plano_supermercado):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        with pytest.raises(ValueError):
            salvar_lancamento({
                "data":           "2026-05-23",
                "descricao":      "   ",
                "tipo":           "saida",
                "plano_conta_id": plano_supermercado,
                "valor":          10.0,
            })

    def test_tipo_invalido_falha(self, banco, plano_supermercado):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            salvar_lancamento({
                "data":           "2026-05-23",
                "descricao":      "X",
                "tipo":           "transferencia",  # tipo inválido
                "plano_conta_id": plano_supermercado,
                "valor":          10.0,
            })


class TestListagem:
    def test_listar_vazio(self, banco):
        from views.fluxo_caixa.lancamento_manual_model import listar_lancamentos_mes
        assert listar_lancamentos_mes(5, 2026) == []

    def test_listar_filtra_por_mes(self, banco, plano_supermercado):
        from views.fluxo_caixa.lancamento_manual_model import (
            salvar_lancamento, listar_lancamentos_mes,
        )
        salvar_lancamento({"data": "2026-05-10", "descricao": "Maio A",
                           "tipo": "saida", "plano_conta_id": plano_supermercado,
                           "valor": 20.0})
        salvar_lancamento({"data": "2026-05-20", "descricao": "Maio B",
                           "tipo": "saida", "plano_conta_id": plano_supermercado,
                           "valor": 30.0})
        salvar_lancamento({"data": "2026-06-05", "descricao": "Junho",
                           "tipo": "saida", "plano_conta_id": plano_supermercado,
                           "valor": 40.0})

        maio = listar_lancamentos_mes(5, 2026)
        assert len(maio) == 2
        assert {l.descricao for l in maio} == {"Maio A", "Maio B"}

        junho = listar_lancamentos_mes(6, 2026)
        assert len(junho) == 1
        assert junho[0].descricao == "Junho"

    def test_listar_carrega_nome_categoria(
        self, banco, plano_supermercado, fonte_clt
    ):
        from views.fluxo_caixa.lancamento_manual_model import (
            salvar_lancamento, listar_lancamentos_mes,
        )
        salvar_lancamento({"data": "2026-05-10", "descricao": "Compra",
                           "tipo": "saida", "plano_conta_id": plano_supermercado,
                           "valor": 50.0})
        salvar_lancamento({"data": "2026-05-12", "descricao": "Pgto freela",
                           "tipo": "entrada", "fonte_receita_id": fonte_clt,
                           "valor": 200.0})

        linhas = listar_lancamentos_mes(5, 2026)
        por_desc = {l.descricao: l for l in linhas}
        assert por_desc["Compra"].nome_categoria == "Supermercado"
        assert por_desc["Pgto freela"].nome_categoria == "Salário CLT Teste"


class TestExcluir:
    def test_excluir_lancamento(self, banco, plano_supermercado):
        from views.fluxo_caixa.lancamento_manual_model import (
            salvar_lancamento, excluir_lancamento, listar_lancamentos_mes,
        )
        id_ = salvar_lancamento({"data": "2026-05-10", "descricao": "X",
                                  "tipo": "saida",
                                  "plano_conta_id": plano_supermercado,
                                  "valor": 10.0})
        excluir_lancamento(id_)
        assert listar_lancamentos_mes(5, 2026) == []

    def test_excluir_inexistente_silencioso(self, banco):
        from views.fluxo_caixa.lancamento_manual_model import excluir_lancamento
        excluir_lancamento(999)  # não levanta


class TestAtualizar:
    def test_atualizar_valor_e_descricao(self, banco, plano_supermercado):
        from views.fluxo_caixa.lancamento_manual_model import (
            salvar_lancamento, atualizar_lancamento, listar_lancamentos_mes,
        )
        id_ = salvar_lancamento({"data": "2026-05-10", "descricao": "Original",
                                  "tipo": "saida",
                                  "plano_conta_id": plano_supermercado,
                                  "valor": 10.0})
        atualizar_lancamento(id_, {
            "data":           "2026-05-15",
            "descricao":      "Atualizado",
            "tipo":           "saida",
            "plano_conta_id": plano_supermercado,
            "valor":          25.0,
            "observacao":     "obs nova",
        })
        l = listar_lancamentos_mes(5, 2026)[0]
        assert l.descricao == "Atualizado"
        assert l.valor == pytest.approx(25.0)
        assert l.data == "2026-05-15"
        assert l.observacao == "obs nova"


# ─────────────────────────────────────────────────────────────────────────────
# Integração com extrato
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegracaoExtrato:
    def test_lancamento_manual_aparece_no_extrato(
        self, banco, plano_supermercado, fonte_clt
    ):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        from views.fluxo_caixa.extrato_model import extrato_mes

        salvar_lancamento({"data": "2026-05-10", "descricao": "Saída em espécie",
                           "tipo": "saida", "plano_conta_id": plano_supermercado,
                           "valor": 75.50})
        salvar_lancamento({"data": "2026-05-15", "descricao": "Recebi em dinheiro",
                           "tipo": "entrada", "fonte_receita_id": fonte_clt,
                           "valor": 200.00})

        linhas = extrato_mes(5, 2026)
        descs = [l.descricao for l in linhas]
        assert "Saída em espécie" in descs
        assert "Recebi em dinheiro" in descs

    def test_lancamento_manual_tem_origem_marcada(
        self, banco, plano_supermercado
    ):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        from views.fluxo_caixa.extrato_model import extrato_mes

        id_ = salvar_lancamento({"data": "2026-05-10", "descricao": "Manual",
                                  "tipo": "saida",
                                  "plano_conta_id": plano_supermercado,
                                  "valor": 50.0})
        linhas = extrato_mes(5, 2026)
        manuais = [l for l in linhas if l.descricao == "Manual"]
        assert len(manuais) == 1
        assert manuais[0].origem == "manual"
        assert manuais[0].origem_id == id_

    def test_lancamento_manual_soma_corretamente_no_extrato(
        self, banco, plano_supermercado, fonte_clt
    ):
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        from views.fluxo_caixa.extrato_model import extrato_mes, resumo_extrato

        salvar_lancamento({"data": "2026-05-10", "descricao": "S",
                           "tipo": "saida", "plano_conta_id": plano_supermercado,
                           "valor": 30.0})
        salvar_lancamento({"data": "2026-05-15", "descricao": "E",
                           "tipo": "entrada", "fonte_receita_id": fonte_clt,
                           "valor": 100.0})

        linhas = extrato_mes(5, 2026)
        manuais = [l for l in linhas if l.origem == "manual"]
        soma_debito  = sum(l.debito  for l in manuais)
        soma_credito = sum(l.credito for l in manuais)
        assert soma_debito  == pytest.approx(30.0)
        assert soma_credito == pytest.approx(100.0)

    def test_lancamento_manual_nao_entra_na_projecao_futura(
        self, banco, plano_supermercado, fonte_clt
    ):
        """Decisão de produto: lançamento manual é avulso, não projeta."""
        from views.fluxo_caixa.lancamento_manual_model import salvar_lancamento
        from views.visao_futura.projecao_model import projetar

        salvar_lancamento({"data": "2026-05-10", "descricao": "Avulso",
                           "tipo": "saida", "plano_conta_id": plano_supermercado,
                           "valor": 1000.0})
        salvar_lancamento({"data": "2026-05-15", "descricao": "Avulso entrada",
                           "tipo": "entrada", "fonte_receita_id": fonte_clt,
                           "valor": 500.0})

        meses = projetar(meses=12)
        # Pega o mês de maio/2026 (campo é mes_num)
        mes_maio = [m for m in meses if m.mes_num == 5 and m.ano == 2026]
        if not mes_maio:
            pytest.skip("Projeção não cobriu maio/2026 — depende da data atual")
        m = mes_maio[0]
        # Soma não deve ter sido inflada pelos R$ 1000 / R$ 500 manuais
        # (validação fraca pra não acoplar demais ao formato da projeção)
        assert m.desp_variaveis < 900.0  # menos do que o avulso de R$ 1000
