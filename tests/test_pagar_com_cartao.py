"""
test_pagar_com_cartao.py — Testes da função registrar_compra_parcelas
e do fluxo integrado "Pagar com Cartão" em contas_pagar.
"""
import pytest
from database import conectar


# ---------------------------------------------------------------------------
# Fixture: cartão de teste
# ---------------------------------------------------------------------------

@pytest.fixture
def cartao(banco):
    """Cartão de crédito simples para os testes."""
    from views.cartoes.cartao_model import salvar_cartao
    cid = salvar_cartao({
        "nome": "Nubank Teste",
        "banco": "nubank",
        "bandeira": "visa",
        "ultimos_digitos": "1234",
        "cor_fundo": "#6D28D9",
        "cor_texto": "#FFFFFF",
        "limite": 5_000.0,
        "limite_disponivel": 5_000.0,
        "dia_vencimento": 10,
        "dia_fechamento": 3,
    })
    return cid


@pytest.fixture
def plano(banco):
    """Plano de conta para contas_pagar."""
    from database import conectar
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)"
            " VALUES ('Compras','variavel','Outros',1,0,?)",
            (agora,)
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compras(banco_path, cartao_id):
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM compras_cartao WHERE cartao_id=?", (cartao_id,)
        ).fetchall()


def _parcelas(banco_path, cartao_id):
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM parcelas_cartao WHERE cartao_id=? ORDER BY numero_parcela",
            (cartao_id,)
        ).fetchall()


def _limite_disponivel(cartao_id):
    with conectar() as conn:
        return conn.execute(
            "SELECT limite_disponivel FROM cartoes WHERE id=?", (cartao_id,)
        ).fetchone()["limite_disponivel"]


# ---------------------------------------------------------------------------
# TestRegistrarCompraUmaParcela
# ---------------------------------------------------------------------------

class TestRegistrarCompraUmaParcela:
    def test_cria_compra_cartao(self, banco, cartao):
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Supermercado",
            "valor_total": 500.0,
            "total_parcelas": 1,
            "mes_inicio": "2025-06",
            "categoria": "",
            "estabelecimento": "",
        })
        compras = _compras(banco, cartao)
        assert len(compras) == 1
        assert compras[0]["valor_total"] == pytest.approx(500.0)
        assert compras[0]["total_parcelas"] == 1

    def test_cria_parcela_unica(self, banco, cartao):
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Supermercado",
            "valor_total": 500.0,
            "total_parcelas": 1,
            "mes_inicio": "2025-06",
            "categoria": "",
            "estabelecimento": "",
        })
        parcelas = _parcelas(banco, cartao)
        assert len(parcelas) == 1
        assert parcelas[0]["mes_referencia"] == "2025-06"
        assert parcelas[0]["valor"] == pytest.approx(500.0)
        assert parcelas[0]["status"] == "pendente"

    def test_debita_limite(self, banco, cartao):
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Notebook",
            "valor_total": 2_000.0,
            "total_parcelas": 1,
            "mes_inicio": "2025-07",
            "categoria": "",
            "estabelecimento": "",
        })
        assert _limite_disponivel(cartao) == pytest.approx(3_000.0)


# ---------------------------------------------------------------------------
# TestRegistrarCompraParcelada
# ---------------------------------------------------------------------------

class TestRegistrarCompraParcelada:
    def test_parcelas_corretas_quantidade(self, banco, cartao):
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "TV 4K",
            "valor_total": 1_200.0,
            "total_parcelas": 4,
            "mes_inicio": "2025-06",
            "categoria": "",
            "estabelecimento": "",
        })
        parcelas = _parcelas(banco, cartao)
        assert len(parcelas) == 4

    def test_parcelas_numeracao_sequencial(self, banco, cartao):
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Móveis",
            "valor_total": 900.0,
            "total_parcelas": 3,
            "mes_inicio": "2025-08",
            "categoria": "",
            "estabelecimento": "",
        })
        parcelas = _parcelas(banco, cartao)
        nums = [p["numero_parcela"] for p in parcelas]
        assert nums == [1, 2, 3]

    def test_parcelas_meses_sequenciais(self, banco, cartao):
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Geladeira",
            "valor_total": 600.0,
            "total_parcelas": 3,
            "mes_inicio": "2025-11",
            "categoria": "",
            "estabelecimento": "",
        })
        meses = [p["mes_referencia"] for p in _parcelas(banco, cartao)]
        assert meses == ["2025-11", "2025-12", "2026-01"]

    def test_valor_parcela_base(self, banco, cartao):
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Eletrônico",
            "valor_total": 300.0,
            "total_parcelas": 3,
            "mes_inicio": "2025-06",
            "categoria": "",
            "estabelecimento": "",
        })
        parcelas = _parcelas(banco, cartao)
        assert all(p["valor"] == pytest.approx(100.0) for p in parcelas)

    def test_ultima_parcela_absorve_arredondamento(self, banco, cartao):
        """R$100 / 3 = 33,33 + 33,33 + 33,34 → total exato."""
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Serviço",
            "valor_total": 100.0,
            "total_parcelas": 3,
            "mes_inicio": "2025-06",
            "categoria": "",
            "estabelecimento": "",
        })
        parcelas = _parcelas(banco, cartao)
        soma = sum(p["valor"] for p in parcelas)
        assert soma == pytest.approx(100.0, abs=0.01)
        # Primeira e segunda iguais; última diferente
        assert parcelas[0]["valor"] == parcelas[1]["valor"]
        assert parcelas[2]["valor"] != parcelas[0]["valor"]

    def test_limite_debitado_pelo_total(self, banco, cartao):
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "TV",
            "valor_total": 1_500.0,
            "total_parcelas": 10,
            "mes_inicio": "2025-06",
            "categoria": "",
            "estabelecimento": "",
        })
        assert _limite_disponivel(cartao) == pytest.approx(3_500.0)

    def test_retorna_compra_id(self, banco, cartao):
        from views.cartoes.cartao_model import registrar_compra_parcelas
        cid = registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "X",
            "valor_total": 100.0,
            "total_parcelas": 1,
            "mes_inicio": "2025-06",
            "categoria": "",
            "estabelecimento": "",
        })
        assert isinstance(cid, int) and cid > 0

    def test_virada_de_ano(self, banco, cartao):
        """12 parcelas a partir de dez/2025 devem ir até nov/2026."""
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Pacote",
            "valor_total": 1_200.0,
            "total_parcelas": 12,
            "mes_inicio": "2025-12",
            "categoria": "",
            "estabelecimento": "",
        })
        meses = [p["mes_referencia"] for p in _parcelas(banco, cartao)]
        assert meses[0]  == "2025-12"
        assert meses[-1] == "2026-11"


# ---------------------------------------------------------------------------
# TestFluxoIntegrado — salvar_conta + registrar_compra_parcelas
# ---------------------------------------------------------------------------

class TestFluxoIntegrado:
    """
    Simula o que form_view._salvar faz internamente:
    1. salvar_conta  → cria entrada em contas_pagar
    2. registrar_compra_parcelas → cria compras_cartao + parcelas_cartao
    Verifica que ambos os registros existem sem duplicação.
    """

    def test_contas_pagar_criada(self, banco, plano, cartao):
        from views.contas_pagar.conta_model import salvar_conta
        from views.cartoes.cartao_model import registrar_compra_parcelas
        dados = {
            "plano_conta_id": plano,
            "descricao": "Compra TV",
            "valor": 1_200.0,
            "data_vencimento": "2025-06-10",
            "data_pagamento": None,
            "status": "pendente",
            "recorrente": False,
            "observacao": "",
        }
        salvar_conta(dados, meses=1)
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Compra TV",
            "valor_total": 1_200.0,
            "total_parcelas": 3,
            "mes_inicio": "2025-06",
            "categoria": "",
            "estabelecimento": "",
        })

        with conectar() as conn:
            cp = conn.execute(
                "SELECT COUNT(*) AS n FROM contas_pagar WHERE plano_conta_id=?", (plano,)
            ).fetchone()["n"]
            cc = conn.execute(
                "SELECT COUNT(*) AS n FROM compras_cartao WHERE cartao_id=?", (cartao,)
            ).fetchone()["n"]
            pc = conn.execute(
                "SELECT COUNT(*) AS n FROM parcelas_cartao WHERE cartao_id=?", (cartao,)
            ).fetchone()["n"]

        assert cp == 1, "deve existir exatamente 1 entrada em contas_pagar"
        assert cc == 1, "deve existir exatamente 1 compra no cartão"
        assert pc == 3, "deve existir 3 parcelas no cartão"

    def test_nao_duplica_contas_pagar(self, banco, plano, cartao):
        """registrar_compra_parcelas não toca em contas_pagar."""
        from views.contas_pagar.conta_model import salvar_conta
        from views.cartoes.cartao_model import registrar_compra_parcelas
        dados = {
            "plano_conta_id": plano,
            "descricao": "Teste",
            "valor": 500.0,
            "data_vencimento": "2025-07-01",
            "data_pagamento": None,
            "status": "pendente",
            "recorrente": False,
            "observacao": "",
        }
        salvar_conta(dados, meses=1)
        registrar_compra_parcelas({
            "cartao_id": cartao,
            "descricao": "Teste",
            "valor_total": 500.0,
            "total_parcelas": 1,
            "mes_inicio": "2025-07",
            "categoria": "",
            "estabelecimento": "",
        })

        with conectar() as conn:
            n = conn.execute("SELECT COUNT(*) AS n FROM contas_pagar").fetchone()["n"]
        assert n == 1

    def test_multiplas_compras_cartao(self, banco, plano, cartao):
        """Duas compras distintas no mesmo cartão geram 2 compras e somam parcelas."""
        from views.cartoes.cartao_model import registrar_compra_parcelas
        registrar_compra_parcelas({
            "cartao_id": cartao, "descricao": "A",
            "valor_total": 300.0, "total_parcelas": 3,
            "mes_inicio": "2025-06", "categoria": "", "estabelecimento": "",
        })
        registrar_compra_parcelas({
            "cartao_id": cartao, "descricao": "B",
            "valor_total": 600.0, "total_parcelas": 6,
            "mes_inicio": "2025-07", "categoria": "", "estabelecimento": "",
        })
        compras = _compras(banco, cartao)
        assert len(compras) == 2
        total_parcelas = sum(c["total_parcelas"] for c in compras)
        assert total_parcelas == 9
        assert _limite_disponivel(cartao) == pytest.approx(4_100.0)
