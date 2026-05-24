"""
test_regras_categoria.py — Testes do CRUD de regras e casamento.
"""
import pytest


@pytest.fixture
def plano_super(banco):
    from database import conectar
    with conectar() as conn:
        r = conn.execute(
            "SELECT id FROM plano_contas WHERE nome='Supermercado'"
        ).fetchone()
    return r["id"]


@pytest.fixture
def plano_rest(banco):
    from database import conectar
    with conectar() as conn:
        r = conn.execute(
            "SELECT id FROM plano_contas WHERE nome='Restaurantes / Delivery'"
        ).fetchone()
    return r["id"]


@pytest.fixture
def fonte_clt(banco):
    from database import conectar
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO fontes_receita (nome, tipo, valor_mensal, ativa, criado_em)"
            " VALUES ('CLT Teste', 'clt', 5000.0, 1, '2026-01-01')"
        )
        return cur.lastrowid


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestSalvarRegra:
    def test_criar_regra_saida(self, banco, plano_super):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra, listar_regras
        rid = salvar_regra({
            "padrao": "MERCADO", "tipo": "saida",
            "plano_conta_id": plano_super, "prioridade": 5,
        })
        assert isinstance(rid, int) and rid > 0
        regras = listar_regras()
        assert len(regras) == 1
        assert regras[0].padrao == "MERCADO"

    def test_criar_regra_entrada(self, banco, fonte_clt):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra, listar_regras
        salvar_regra({
            "padrao": "REMUNERACAO", "tipo": "entrada",
            "fonte_receita_id": fonte_clt,
        })
        assert listar_regras()[0].nome_categoria == "CLT Teste"

    def test_padrao_vazio_falha(self, banco, plano_super):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra
        with pytest.raises(ValueError):
            salvar_regra({"padrao": "  ", "tipo": "saida",
                          "plano_conta_id": plano_super})

    def test_saida_sem_plano_falha(self, banco, fonte_clt):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra
        with pytest.raises(ValueError):
            salvar_regra({"padrao": "X", "tipo": "saida",
                          "fonte_receita_id": fonte_clt})

    def test_entrada_sem_fonte_falha(self, banco, plano_super):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra
        with pytest.raises(ValueError):
            salvar_regra({"padrao": "X", "tipo": "entrada",
                          "plano_conta_id": plano_super})


class TestListar:
    def test_ordena_prioridade_desc(self, banco, plano_super, plano_rest):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra, listar_regras
        salvar_regra({"padrao": "A", "tipo": "saida",
                      "plano_conta_id": plano_super, "prioridade": 1})
        salvar_regra({"padrao": "B", "tipo": "saida",
                      "plano_conta_id": plano_rest, "prioridade": 10})
        regras = listar_regras()
        assert [r.padrao for r in regras] == ["B", "A"]

    def test_filtra_apenas_ativas(self, banco, plano_super):
        from views.fluxo_caixa.regras_categoria_model import (
            salvar_regra, atualizar_regra, listar_regras,
        )
        rid = salvar_regra({"padrao": "A", "tipo": "saida",
                            "plano_conta_id": plano_super})
        atualizar_regra(rid, {"padrao": "A", "tipo": "saida",
                              "plano_conta_id": plano_super, "ativa": False})
        assert len(listar_regras()) == 1
        assert len(listar_regras(apenas_ativas=True)) == 0


class TestExcluir:
    def test_excluir(self, banco, plano_super):
        from views.fluxo_caixa.regras_categoria_model import (
            salvar_regra, excluir_regra, listar_regras,
        )
        rid = salvar_regra({"padrao": "X", "tipo": "saida",
                            "plano_conta_id": plano_super})
        excluir_regra(rid)
        assert listar_regras() == []


# ─────────────────────────────────────────────────────────────────────────────
# Casamento de regras
# ─────────────────────────────────────────────────────────────────────────────

class TestCasarRegras:
    def test_casa_substring_case_insensitive(self, banco, plano_super):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra, casar_regras
        salvar_regra({"padrao": "MERCADO", "tipo": "saida",
                      "plano_conta_id": plano_super})
        # 'MERCADO' (maiúsculo) deve casar com 'Mercado Bom' (minúsculo no meio)
        itens = [{"data": "2026-01-01", "descricao": "compra no Mercado Bom",
                  "valor": -30.0, "identificador_unico": "a"}]
        resultado = casar_regras(itens)
        assert resultado[0].get("plano_conta_id") == plano_super

    def test_separa_por_sinal_do_valor(self, banco, plano_super, fonte_clt):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra, casar_regras
        # Regra entrada
        salvar_regra({"padrao": "SALARIO", "tipo": "entrada",
                      "fonte_receita_id": fonte_clt})
        # Regra saida
        salvar_regra({"padrao": "SALARIO", "tipo": "saida",
                      "plano_conta_id": plano_super})
        itens = [
            {"data": "2026-01-01", "descricao": "SALARIO", "valor": 5000.0,
             "identificador_unico": "a"},
            {"data": "2026-01-02", "descricao": "SALARIO", "valor": -100.0,
             "identificador_unico": "b"},
        ]
        r = casar_regras(itens)
        # Entrada usa fonte
        assert r[0]["fonte_receita_id"] == fonte_clt
        assert "plano_conta_id" not in r[0] or r[0].get("plano_conta_id") is None
        # Saída usa plano
        assert r[1]["plano_conta_id"] == plano_super

    def test_prioridade_vence(self, banco, plano_super, plano_rest):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra, casar_regras
        salvar_regra({"padrao": "MERCADO", "tipo": "saida",
                      "plano_conta_id": plano_super, "prioridade": 1})
        salvar_regra({"padrao": "MERCADOLIVRE", "tipo": "saida",
                      "plano_conta_id": plano_rest, "prioridade": 10})
        itens = [{"data": "2026-01-01", "descricao": "MERCADOLIVRE STORE",
                  "valor": -50.0, "identificador_unico": "a"}]
        r = casar_regras(itens)
        # Maior prioridade vence
        assert r[0]["plano_conta_id"] == plano_rest

    def test_sem_match_nao_seta_categoria(self, banco, plano_super):
        from views.fluxo_caixa.regras_categoria_model import salvar_regra, casar_regras
        salvar_regra({"padrao": "MERCADO", "tipo": "saida",
                      "plano_conta_id": plano_super})
        itens = [{"data": "2026-01-01", "descricao": "POSTO X",
                  "valor": -50.0, "identificador_unico": "a"}]
        r = casar_regras(itens)
        assert r[0].get("plano_conta_id") is None

    def test_regras_inativas_nao_casam(self, banco, plano_super):
        from views.fluxo_caixa.regras_categoria_model import (
            salvar_regra, atualizar_regra, casar_regras,
        )
        rid = salvar_regra({"padrao": "MERCADO", "tipo": "saida",
                            "plano_conta_id": plano_super})
        atualizar_regra(rid, {"padrao": "MERCADO", "tipo": "saida",
                              "plano_conta_id": plano_super, "ativa": False})
        itens = [{"data": "2026-01-01", "descricao": "Compra Mercadinho",
                  "valor": -50.0, "identificador_unico": "a"}]
        r = casar_regras(itens)
        assert r[0].get("plano_conta_id") is None

    def test_lista_vazia_de_regras(self, banco):
        from views.fluxo_caixa.regras_categoria_model import casar_regras
        itens = [{"data": "2026-01-01", "descricao": "X",
                  "valor": -10.0, "identificador_unico": "a"}]
        r = casar_regras(itens)
        # Não casa nada, mas devolve a lista intacta
        assert len(r) == 1
        assert r[0]["descricao"] == "X"
