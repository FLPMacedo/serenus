"""
test_investimento_model.py — Testes do módulo de investimentos.

Cobre:
- Compra de ativos (ação e renda fixa)
- Venda parcial e total
- Custo médio ponderado
- Posição atual (listar_posicoes)
- Rendimentos (dividendo, JCP, juros)
- Taxas e impostos manuais
- Integração opcional com financeiro (contas_pagar / extrato)
- Atualização manual de cotação
- Exclusão de movimentação (com e sem vínculo financeiro)
- Cenários de borda
"""

import pytest
from tests.conftest import mov
from views.investimentos.investimento_model import (
    salvar_movimentacao,
    excluir_movimentacao,
    listar_movimentacoes,
    listar_posicoes,
    resumo_carteira,
    alocacao_por_tipo,
    rendimentos_por_mes,
    rendimentos_financeiros_mes,
    atualizar_valor_atual,
    vencimentos_proximos,
    estimar_valor_atual_rf,
)
from database import conectar


# ─────────────────────────────────────────────────────────────────────────────
# Helpers locais
# ─────────────────────────────────────────────────────────────────────────────

def _posicao(ativo_id: int):
    """Busca posicao_cache direto no banco para o ativo."""
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM posicao_cache WHERE ativo_id=?", (ativo_id,)
        ).fetchone()


def _count_contas_pagar(plano_substr: str = "") -> int:
    """Conta entradas em contas_pagar, opcionalmente filtradas por plano."""
    with conectar() as conn:
        if plano_substr:
            return conn.execute(
                "SELECT COUNT(*) FROM contas_pagar cp"
                " JOIN plano_contas pc ON pc.id = cp.plano_conta_id"
                " WHERE pc.nome LIKE ?", (f"%{plano_substr}%",)
            ).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM contas_pagar").fetchone()[0]


# ─────────────────────────────────────────────────────────────────────────────
# 1 — Compra
# ─────────────────────────────────────────────────────────────────────────────

class TestCompra:

    def test_compra_simples_cria_movimentacao(self, banco, conta_inv, ativo_acao):
        """Compra cria 1 registro em movimentacoes_investimento."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3250.0,
                                qtd=100, preco=32.50))
        movs = listar_movimentacoes(ativo_id=ativo_acao)
        assert len(movs) == 1
        assert movs[0].tipo == "compra"
        assert movs[0].valor_bruto == 3250.0

    def test_compra_atualiza_posicao(self, banco, conta_inv, ativo_acao):
        """Após compra, posicao_cache reflete quantidade e valor_investido."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3250.0,
                                qtd=100, preco=32.50))
        p = _posicao(ativo_acao)
        assert p is not None
        assert p["quantidade_atual"] == pytest.approx(100.0)
        assert p["valor_investido"]  == pytest.approx(3250.0)

    def test_compra_calcula_custo_medio(self, banco, conta_inv, ativo_acao):
        """Custo médio = valor_investido / qtd após compra única."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3250.0,
                                qtd=100, preco=32.50))
        p = _posicao(ativo_acao)
        assert p["custo_medio"] == pytest.approx(32.50)

    def test_compra_com_taxas_valor_liquido(self, banco, conta_inv, ativo_acao):
        """Para compra: valor_liquido = valor_bruto + taxas."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3250.0,
                                qtd=100, preco=32.50, taxas=5.0))
        movs = listar_movimentacoes(ativo_id=ativo_acao)
        assert movs[0].valor_liquido == pytest.approx(3255.0)

    def test_compra_com_taxas_inclui_no_custo(self, banco, conta_inv, ativo_acao):
        """Taxas de compra são somadas ao custo total (valor_liquido)."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3250.0,
                                qtd=100, preco=32.50, taxas=10.0))
        p = _posicao(ativo_acao)
        # valor_investido = valor_liquido (bruto + taxas)
        assert p["valor_investido"] == pytest.approx(3260.0)

    def test_duas_compras_acumulam_quantidade(self, banco, conta_inv, ativo_acao):
        """Duas compras somam quantidades na posição."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3250.0,
                                qtd=100, preco=32.50))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 2000.0,
                                qtd=50, preco=40.00))
        p = _posicao(ativo_acao)
        assert p["quantidade_atual"] == pytest.approx(150.0)

    def test_aplicacao_renda_fixa_sem_quantidade(self, banco, conta_inv, ativo_cdb):
        """Aplicação de CDB sem quantidade → valor_investido correto."""
        salvar_movimentacao(mov(ativo_cdb, conta_inv, "aplicacao", 10_000.0))
        p = _posicao(ativo_cdb)
        assert p["valor_investido"] == pytest.approx(10_000.0)
        assert p["quantidade_atual"] == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2 — Custo médio ponderado
# ─────────────────────────────────────────────────────────────────────────────

class TestCustoMedio:

    def test_custo_medio_ponderado_duas_compras(self, banco, conta_inv, ativo_acao):
        """
        Compra 1: 100 ações a R$30 → custo total = 3.000
        Compra 2:  50 ações a R$40 → custo total = 2.000
        Total: 150 ações, custo = 5.000 → custo médio = 33,33
        """
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 2_000.0,
                                qtd=50, preco=40.0))
        p = _posicao(ativo_acao)
        assert p["custo_medio"]    == pytest.approx(5_000.0 / 150, rel=1e-4)
        assert p["valor_investido"] == pytest.approx(5_000.0)

    def test_custo_medio_ponderado_tres_compras(self, banco, conta_inv, ativo_acao):
        """Custo médio com três compras a preços distintos."""
        compras = [(200, 10.0), (100, 12.0), (50, 8.0)]
        for qtd, preco in compras:
            salvar_movimentacao(mov(ativo_acao, conta_inv, "compra",
                                    qtd * preco, qtd=qtd, preco=preco))
        p = _posicao(ativo_acao)
        total_qtd  = 350
        total_custo = 200*10 + 100*12 + 50*8  # 2000 + 1200 + 400 = 3600
        assert p["quantidade_atual"] == pytest.approx(total_qtd)
        assert p["custo_medio"]      == pytest.approx(total_custo / total_qtd, rel=1e-4)

    def test_custo_medio_nao_muda_apos_venda(self, banco, conta_inv, ativo_acao):
        """Venda parcial não altera o custo médio dos lotes restantes."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 2_000.0,
                                qtd=50, preco=40.0))
        custo_medio_antes = _posicao(ativo_acao)["custo_medio"]

        # Vende 50 ações — custo médio dos restantes não muda
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 50 * 38.0,
                                qtd=50, preco=38.0))
        custo_medio_depois = _posicao(ativo_acao)["custo_medio"]
        assert custo_medio_depois == pytest.approx(custo_medio_antes, rel=1e-4)


# ─────────────────────────────────────────────────────────────────────────────
# 3 — Venda
# ─────────────────────────────────────────────────────────────────────────────

class TestVenda:

    def test_venda_parcial_reduz_quantidade(self, banco, conta_inv, ativo_acao):
        """Venda de 30% das ações → quantidade restante = 70%."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 900.0,
                                qtd=30, preco=30.0))
        p = _posicao(ativo_acao)
        assert p["quantidade_atual"] == pytest.approx(70.0)

    def test_venda_parcial_reduz_valor_investido(self, banco, conta_inv, ativo_acao):
        """Venda proporcional reduz valor_investido proporcionalmente."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 900.0,
                                qtd=30, preco=30.0))
        p = _posicao(ativo_acao)
        # 70% do custo original = 2.100
        assert p["valor_investido"] == pytest.approx(2_100.0, rel=1e-4)

    def test_venda_com_lucro_registra_lucro_realizado(self, banco, conta_inv, ativo_acao):
        """Lucro realizado = (preco venda - custo médio) × qtd vendida."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        # Vende 50 ações a R$40 → lucro = 50 × (40-30) = 500
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 2_000.0,
                                qtd=50, preco=40.0))
        p = _posicao(ativo_acao)
        assert p["lucro_realizado"] == pytest.approx(500.0, rel=1e-4)

    def test_venda_com_prejuizo_registra_negativo(self, banco, conta_inv, ativo_acao):
        """Venda abaixo do custo médio gera lucro_realizado negativo."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        # Vende 50 a R$20 → prejuízo = 50 × (20-30) = -500
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 1_000.0,
                                qtd=50, preco=20.0))
        p = _posicao(ativo_acao)
        assert p["lucro_realizado"] == pytest.approx(-500.0, rel=1e-4)

    def test_venda_total_zera_posicao(self, banco, conta_inv, ativo_acao):
        """Após venda total, quantidade e valor_investido são zero."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 3_500.0,
                                qtd=100, preco=35.0))
        p = _posicao(ativo_acao)
        assert p["quantidade_atual"] == pytest.approx(0.0, abs=1e-6)
        assert p["valor_investido"]  == pytest.approx(0.0, abs=1e-6)

    def test_venda_lucro_correto_com_custo_medio_ponderado(self, banco, conta_inv, ativo_acao):
        """
        Compra 1: 100 ações a 30 → custo médio = 30
        Compra 2:  50 ações a 40 → custo médio = 33,33
        Venda: 50 ações a 50 → lucro = 50 × (50 - 33,33) = 833,33
        """
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 2_000.0,
                                qtd=50, preco=40.0))
        cm = _posicao(ativo_acao)["custo_medio"]  # ~33.33

        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 2_500.0,
                                qtd=50, preco=50.0))
        p = _posicao(ativo_acao)
        lucro_esperado = 50 * (50.0 - cm)
        assert p["lucro_realizado"] == pytest.approx(lucro_esperado, rel=1e-3)

    def test_resgate_renda_fixa(self, banco, conta_inv, ativo_cdb):
        """Resgate de CDB sem quantidade → valor_investido reduz proporcionalmente."""
        salvar_movimentacao(mov(ativo_cdb, conta_inv, "aplicacao", 10_000.0))
        # Resgate de 5.000 (50% do total)
        salvar_movimentacao(mov(ativo_cdb, conta_inv, "resgate", 5_000.0))
        p = _posicao(ativo_cdb)
        assert p["valor_investido"] == pytest.approx(5_000.0, rel=1e-3)


# ─────────────────────────────────────────────────────────────────────────────
# 4 — Posição
# ─────────────────────────────────────────────────────────────────────────────

class TestPosicao:

    def test_listar_posicoes_retorna_ativo_com_saldo(self, banco, conta_inv, ativo_acao):
        """Após compra, ativo aparece em listar_posicoes."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        posicoes = listar_posicoes()
        assert any(p.ativo_id == ativo_acao for p in posicoes)

    def test_listar_posicoes_sem_saldo_nao_aparece(self, banco, conta_inv, ativo_acao):
        """Ativo zerado é excluído por padrão (apenas_com_saldo=True)."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 3_500.0,
                                qtd=100, preco=35.0))
        posicoes = listar_posicoes(apenas_com_saldo=True)
        assert not any(p.ativo_id == ativo_acao for p in posicoes)

    def test_listar_posicoes_campos_corretos(self, banco, conta_inv, ativo_acao):
        """Campos da Posicao são calculados corretamente."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        atualizar_valor_atual(ativo_acao, 3_500.0)
        p = next(x for x in listar_posicoes() if x.ativo_id == ativo_acao)

        assert p.quantidade_atual   == pytest.approx(100.0)
        assert p.custo_medio        == pytest.approx(30.0)
        assert p.valor_investido    == pytest.approx(3_000.0)
        assert p.valor_atual        == pytest.approx(3_500.0)
        assert p.lucro_nao_realizado == pytest.approx(500.0)
        assert p.rentabilidade_pct  == pytest.approx(16.667, rel=1e-3)

    def test_resumo_carteira_soma_todos_ativos(self, banco, conta_inv,
                                                ativo_acao, ativo_cdb):
        """resumo_carteira soma posições de todos os ativos."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_cdb, conta_inv, "aplicacao", 10_000.0))
        r = resumo_carteira()
        assert r["total_investido"] == pytest.approx(13_000.0, rel=1e-3)

    def test_atualizar_valor_atual(self, banco, conta_inv, ativo_acao):
        """atualizar_valor_atual persiste no posicao_cache."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        atualizar_valor_atual(ativo_acao, 4_000.0)
        p = _posicao(ativo_acao)
        assert p["valor_atual"] == pytest.approx(4_000.0)

    def test_alocacao_por_tipo(self, banco, conta_inv, ativo_acao, ativo_fii):
        """alocacao_por_tipo retorna percentuais somando 100%."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 6_000.0,
                                qtd=100, preco=60.0))
        salvar_movimentacao(mov(ativo_fii, conta_inv, "compra", 4_000.0,
                                qtd=100, preco=40.0))
        atualizar_valor_atual(ativo_acao, 6_000.0)
        atualizar_valor_atual(ativo_fii,  4_000.0)
        aloc = alocacao_por_tipo()
        total = sum(aloc.values())
        assert total == pytest.approx(100.0, rel=1e-3)


# ─────────────────────────────────────────────────────────────────────────────
# 5 — Rendimentos
# ─────────────────────────────────────────────────────────────────────────────

class TestRendimentos:

    def test_dividendo_nao_altera_posicao(self, banco, conta_inv, ativo_acao):
        """Dividendo não muda quantidade nem valor_investido."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        qtd_antes = _posicao(ativo_acao)["quantidade_atual"]
        inv_antes  = _posicao(ativo_acao)["valor_investido"]

        salvar_movimentacao(mov(ativo_acao, conta_inv, "dividendo", 450.0,
                                data="2025-07-10"))
        p = _posicao(ativo_acao)
        assert p["quantidade_atual"] == pytest.approx(qtd_antes)
        assert p["valor_investido"]  == pytest.approx(inv_antes)

    def test_rendimentos_acumulam_em_posicao(self, banco, conta_inv, ativo_acao):
        """rendimentos_recebidos somam todos os dividendos/JCP do ativo."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "dividendo", 300.0,
                                data="2025-04-10"))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "jcp", 150.0,
                                data="2025-07-10"))
        pos = next(p for p in listar_posicoes() if p.ativo_id == ativo_acao)
        assert pos.rendimentos_recebidos == pytest.approx(450.0)

    def test_rendimentos_por_mes(self, banco, conta_inv, ativo_acao):
        """rendimentos_por_mes agrupa por mês do ano corretamente."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "dividendo", 200.0,
                                data="2025-03-15"))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "dividendo", 300.0,
                                data="2025-06-15"))
        rend = rendimentos_por_mes(2025)
        assert rend.get(3, 0) == pytest.approx(200.0)
        assert rend.get(6, 0) == pytest.approx(300.0)
        assert rend.get(1, 0) == pytest.approx(0.0)

    def test_juros_renda_fixa_nao_altera_posicao(self, banco, conta_inv, ativo_cdb):
        """Juros de CDB não alteram valor_investido."""
        salvar_movimentacao(mov(ativo_cdb, conta_inv, "aplicacao", 10_000.0))
        inv_antes = _posicao(ativo_cdb)["valor_investido"]

        salvar_movimentacao(mov(ativo_cdb, conta_inv, "juros", 800.0,
                                data="2025-12-01"))
        p = _posicao(ativo_cdb)
        assert p["valor_investido"] == pytest.approx(inv_antes)

    def test_amortizacao_reduz_valor_investido(self, banco, conta_inv, ativo_cdb):
        """Amortização (devolução de principal) reduz valor_investido."""
        salvar_movimentacao(mov(ativo_cdb, conta_inv, "aplicacao", 10_000.0))
        salvar_movimentacao(mov(ativo_cdb, conta_inv, "amortizacao", 2_000.0))
        p = _posicao(ativo_cdb)
        assert p["valor_investido"] == pytest.approx(8_000.0, rel=1e-4)


# ─────────────────────────────────────────────────────────────────────────────
# 6 — Taxas e Impostos manuais
# ─────────────────────────────────────────────────────────────────────────────

class TestTaxasEImpostos:

    def test_taxa_nao_altera_posicao(self, banco, conta_inv, ativo_acao):
        """Taxa de corretagem não altera quantidade nem custo médio."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        qtd_antes = _posicao(ativo_acao)["quantidade_atual"]
        salvar_movimentacao(mov(ativo_acao, conta_inv, "taxa", 8.50))
        p = _posicao(ativo_acao)
        assert p["quantidade_atual"] == pytest.approx(qtd_antes)

    def test_imposto_nao_altera_posicao(self, banco, conta_inv, ativo_acao):
        """Imposto (IR manual) não altera posição do ativo."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        qtd_antes = _posicao(ativo_acao)["quantidade_atual"]
        salvar_movimentacao(mov(ativo_acao, conta_inv, "imposto", 45.0))
        p = _posicao(ativo_acao)
        assert p["quantidade_atual"] == pytest.approx(qtd_antes)

    def test_taxa_registra_movimentacao(self, banco, conta_inv, ativo_acao):
        """Taxa registrada em movimentacoes_investimento com tipo correto."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "taxa", 8.50))
        movs = listar_movimentacoes(ativo_id=ativo_acao, tipo="taxa")
        assert len(movs) == 1
        assert movs[0].valor_bruto == pytest.approx(8.50)

    def test_imposto_registra_movimentacao(self, banco, conta_inv, ativo_acao):
        """Imposto registrado com tipo correto."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "imposto", 150.0))
        movs = listar_movimentacoes(ativo_id=ativo_acao, tipo="imposto")
        assert len(movs) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 7 — Integração com módulo financeiro
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegracaoFinanceira:

    def test_compra_com_flag_gera_contas_pagar(self, banco, conta_inv, ativo_acao):
        """Compra com registrar_no_financeiro=True cria 1 entrada em contas_pagar."""
        n_antes = _count_contas_pagar()
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0, financeiro=True))
        assert _count_contas_pagar() == n_antes + 1

    def test_compra_sem_flag_nao_gera_contas_pagar(self, banco, conta_inv, ativo_acao):
        """Compra com registrar_no_financeiro=False não cria contas_pagar."""
        n_antes = _count_contas_pagar()
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0, financeiro=False))
        assert _count_contas_pagar() == n_antes

    def test_aplicacao_com_flag_gera_contas_pagar(self, banco, conta_inv, ativo_cdb):
        """Aplicação de renda fixa com flag gera contas_pagar de saída."""
        n_antes = _count_contas_pagar()
        salvar_movimentacao(mov(ativo_cdb, conta_inv, "aplicacao", 10_000.0,
                                financeiro=True))
        assert _count_contas_pagar() == n_antes + 1

    def test_taxa_com_flag_gera_contas_pagar_plano_taxas(self, banco, conta_inv, ativo_acao):
        """Taxa com flag usa plano 'Investimentos — Taxas e Impostos'."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "taxa", 8.50,
                                financeiro=True))
        n = _count_contas_pagar("Taxas e Impostos")
        assert n >= 1

    def test_imposto_com_flag_gera_contas_pagar_plano_taxas(self, banco, conta_inv, ativo_acao):
        """Imposto com flag usa plano de taxas (não de aplicação)."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "imposto", 150.0,
                                financeiro=True))
        n = _count_contas_pagar("Taxas e Impostos")
        assert n >= 1

    def test_compra_com_flag_vincula_contas_pagar_id(self, banco, conta_inv, ativo_acao):
        """contas_pagar_id da movimentação aponta para o lançamento criado."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0, financeiro=True))
        m = listar_movimentacoes(ativo_id=ativo_acao)[0]
        assert m.contas_pagar_id is not None
        assert m.contas_pagar_id > 0

    def test_dividendo_com_flag_nao_gera_contas_pagar(self, banco, conta_inv, ativo_acao):
        """Dividendo (entrada) com flag NÃO gera contas_pagar (aparece no extrato)."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        n_antes = _count_contas_pagar()
        salvar_movimentacao(mov(ativo_acao, conta_inv, "dividendo", 450.0,
                                data="2025-07-10", financeiro=True))
        assert _count_contas_pagar() == n_antes  # não aumentou

    def test_dividendo_com_flag_aparece_no_extrato(self, banco, conta_inv, ativo_acao):
        """Dividendo com flag aparece em rendimentos_financeiros_mes."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "dividendo", 450.0,
                                data="2025-07-10", financeiro=True))
        rend = rendimentos_financeiros_mes(mes=7, ano=2025)
        assert len(rend) == 1
        assert rend[0]["credito"] == pytest.approx(450.0)
        assert rend[0]["tipo"] == "receita"

    def test_dividendo_sem_flag_nao_aparece_no_extrato(self, banco, conta_inv, ativo_acao):
        """Dividendo sem flag NÃO aparece em rendimentos_financeiros_mes."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "dividendo", 450.0,
                                data="2025-07-10", financeiro=False))
        rend = rendimentos_financeiros_mes(mes=7, ano=2025)
        assert len(rend) == 0

    def test_venda_com_flag_aparece_no_extrato(self, banco, conta_inv, ativo_acao):
        """Venda com flag aparece como entrada em rendimentos_financeiros_mes."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 3_500.0,
                                qtd=100, preco=35.0,
                                data="2025-08-20", financeiro=True))
        rend = rendimentos_financeiros_mes(mes=8, ano=2025)
        assert any(r["credito"] == pytest.approx(3_500.0) for r in rend)

    def test_mes_errado_nao_aparece_no_extrato(self, banco, conta_inv, ativo_acao):
        """Dividendo de julho não aparece no extrato de agosto."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "dividendo", 450.0,
                                data="2025-07-10", financeiro=True))
        rend_ago = rendimentos_financeiros_mes(mes=8, ano=2025)
        assert len(rend_ago) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 8 — Exclusão de movimentação
# ─────────────────────────────────────────────────────────────────────────────

class TestExclusao:

    def test_excluir_movimentacao_remove_registro(self, banco, conta_inv, ativo_acao):
        """Após excluir, movimentação não aparece mais na listagem."""
        mid = salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                      qtd=100, preco=30.0))
        excluir_movimentacao(mid)
        movs = listar_movimentacoes(ativo_id=ativo_acao)
        assert len(movs) == 0

    def test_excluir_movimentacao_recalcula_posicao(self, banco, conta_inv, ativo_acao):
        """Excluir compra zera posição."""
        mid = salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                      qtd=100, preco=30.0))
        excluir_movimentacao(mid)
        p = _posicao(ativo_acao)
        # Posição pode não existir ou estar zerada
        if p:
            assert p["quantidade_atual"] == pytest.approx(0.0, abs=1e-6)
            assert p["valor_investido"]  == pytest.approx(0.0, abs=1e-6)

    def test_excluir_com_flag_remove_contas_pagar(self, banco, conta_inv, ativo_acao):
        """Excluir movimentação com integração remove a contas_pagar vinculada."""
        mid = salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                      qtd=100, preco=30.0, financeiro=True))
        n_antes = _count_contas_pagar()
        excluir_movimentacao(mid)
        assert _count_contas_pagar() < n_antes

    def test_excluir_sem_flag_nao_afeta_contas_pagar(self, banco, conta_inv, ativo_acao):
        """Excluir movimentação sem integração não remove nada de contas_pagar."""
        # Cria uma compra COM integração para ter algo a contar
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0, financeiro=True))
        n_antes = _count_contas_pagar()
        # Cria e exclui outra SEM integração
        mid2 = salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 1_000.0,
                                        qtd=30, preco=33.0, financeiro=False))
        excluir_movimentacao(mid2)
        assert _count_contas_pagar() == n_antes


# ─────────────────────────────────────────────────────────────────────────────
# 9 — Renda Fixa
# ─────────────────────────────────────────────────────────────────────────────

class TestRendaFixa:

    def test_estimar_valor_rf_sem_tempo(self):
        """Valor atual = valor investido quando dias = 0."""
        v = estimar_valor_atual_rf(10_000.0, 13.5, "2025-06-15", "2025-06-15")
        assert v == pytest.approx(10_000.0)

    def test_estimar_valor_rf_um_ano(self):
        """Após 1 ano com 10% a.a., valor = 11.000."""
        v = estimar_valor_atual_rf(10_000.0, 10.0, "2024-06-15", "2025-06-15")
        assert v == pytest.approx(11_000.0, rel=1e-3)

    def test_estimar_valor_rf_zero_taxa(self):
        """Taxa zero retorna valor original sem correção."""
        v = estimar_valor_atual_rf(10_000.0, 0.0, "2024-01-01", "2025-01-01")
        assert v == pytest.approx(10_000.0)

    def test_estimar_valor_rf_valor_zero(self):
        """Valor investido zero retorna zero."""
        v = estimar_valor_atual_rf(0.0, 13.5, "2024-01-01", "2025-01-01")
        assert v == pytest.approx(0.0)

    def test_vencimentos_proximos_inclui_cdb(self, banco, conta_inv, ativo_cdb):
        """vencimentos_proximos inclui CDB dentro do prazo."""
        # ativo_cdb tem vencimento "2027-12-01" — dentro de 24 meses
        salvar_movimentacao(mov(ativo_cdb, conta_inv, "aplicacao", 10_000.0))
        venc = vencimentos_proximos(meses=24)
        codigos = [v["codigo"] for v in venc]
        assert "CDB-TESTE-120CDI" in codigos

    def test_vencimentos_proximos_exclui_vencido(self, banco, conta_inv):
        """Ativo com vencimento passado não aparece em vencimentos_proximos."""
        from views.investimentos.investimento_model import salvar_ativo
        aid = salvar_ativo({
            "codigo": "CDB-PASSADO",
            "nome": "CDB vencido",
            "tipo": "cdb",
            "conta_investimento_id": conta_inv,
            "vencimento": "2020-01-01",
        })
        salvar_movimentacao(mov(aid, conta_inv, "aplicacao", 5_000.0))
        venc = vencimentos_proximos(meses=12)
        assert not any(v["codigo"] == "CDB-PASSADO" for v in venc)


# ─────────────────────────────────────────────────────────────────────────────
# 10 — Cenários de borda
# ─────────────────────────────────────────────────────────────────────────────

class TestCenariosBorda:

    def test_venda_sem_compra_nao_causa_erro(self, banco, conta_inv, ativo_acao):
        """Vender ativo sem compra prévia não levanta exceção."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 1_000.0,
                                qtd=50, preco=20.0))
        # Apenas verifica que não houve exceção e posição é coerente
        p = _posicao(ativo_acao)
        assert p is not None

    def test_multiplos_ativos_posicoes_independentes(self, banco, conta_inv,
                                                      ativo_acao, ativo_fii):
        """Movimentações em ativos distintos não interferem entre si."""
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_fii, conta_inv, "compra", 5_000.0,
                                qtd=50, preco=100.0))
        p_acao = _posicao(ativo_acao)
        p_fii  = _posicao(ativo_fii)
        assert p_acao["quantidade_atual"] == pytest.approx(100.0)
        assert p_fii["quantidade_atual"]  == pytest.approx(50.0)

    def test_excluir_movimentacao_inexistente_nao_causa_erro(self, banco):
        """Excluir movimentação que não existe não levanta exceção."""
        excluir_movimentacao(99999)  # ID inexistente

    def test_custo_medio_apos_venda_e_nova_compra(self, banco, conta_inv, ativo_acao):
        """
        Ciclo: compra → venda total → nova compra.
        Após a segunda compra, custo médio deve refletir apenas a nova compra.
        """
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "venda", 3_500.0,
                                qtd=100, preco=35.0))
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 4_000.0,
                                qtd=100, preco=40.0))
        p = _posicao(ativo_acao)
        assert p["quantidade_atual"] == pytest.approx(100.0)
        assert p["custo_medio"]      == pytest.approx(40.0)

    def test_rendimentos_financeiros_mes_sem_dados(self, banco, conta_inv, ativo_acao):
        """rendimentos_financeiros_mes retorna lista vazia quando não há dados."""
        rend = rendimentos_financeiros_mes(mes=1, ano=2025)
        assert rend == []

    def test_resumo_carteira_sem_posicoes(self, banco):
        """resumo_carteira retorna zeros quando não há ativos."""
        r = resumo_carteira()
        assert r["total_investido"]    == pytest.approx(0.0)
        assert r["total_atual"]        == pytest.approx(0.0)
        assert r["lucro_realizado"]    == pytest.approx(0.0)
        assert r["rendimentos"]        == pytest.approx(0.0)

    def test_listar_posicoes_ativo_apenas_rendimentos(self, banco, conta_inv, ativo_acao):
        """
        Ativo com apenas dividendos (sem compra): posição zero, mas rendimentos
        registrados. Com apenas_com_saldo=False deve aparecer.
        """
        salvar_movimentacao(mov(ativo_acao, conta_inv, "dividendo", 200.0,
                                data="2025-06-01"))
        posicoes = listar_posicoes(apenas_com_saldo=False)
        p = next((x for x in posicoes if x.ativo_id == ativo_acao), None)
        assert p is not None
        assert p.rendimentos_recebidos == pytest.approx(200.0)

    def test_integracao_plano_criado_automaticamente(self, banco, conta_inv, ativo_acao):
        """
        Plano 'Investimentos — Aplicação' é criado automaticamente na primeira
        compra com integração financeira, sem precisar existir previamente.
        """
        salvar_movimentacao(mov(ativo_acao, conta_inv, "compra", 3_000.0,
                                qtd=100, preco=30.0, financeiro=True))
        with conectar() as conn:
            plano = conn.execute(
                "SELECT id FROM plano_contas WHERE nome='Investimentos — Aplicação'"
            ).fetchone()
        assert plano is not None
