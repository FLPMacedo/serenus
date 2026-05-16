"""
test_cotacao_ir.py — Testes de cotação via API (adapter) e cálculo de IR estimado.
"""
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# CotacaoService — adapter pattern
# ─────────────────────────────────────────────────────────────────────────────

class TestCotacaoService:
    def test_servico_manual_retorna_none(self):
        from views.investimentos.cotacao_service import CotacaoService
        svc = CotacaoService()
        assert svc.obter_preco("PETR4", "acao") is None

    def test_servico_manual_nao_disponivel(self):
        from views.investimentos.cotacao_service import CotacaoService
        svc = CotacaoService()
        assert svc.disponivel() is False

    def test_servico_api_disponivel(self):
        from views.investimentos.cotacao_service import CotacaoAPIService
        svc = CotacaoAPIService()
        assert svc.disponivel() is True

    def test_servico_api_codigo_invalido_retorna_none(self):
        """Código inexistente não deve lançar exceção — retorna None."""
        from views.investimentos.cotacao_service import CotacaoAPIService
        svc = CotacaoAPIService()
        resultado = svc.obter_preco("XXXXINVALIDO999", "acao")
        assert resultado is None

    def test_servico_api_crypto_retorna_none_sem_sufixo(self):
        """Cripto sem sufixo adequado retorna None sem exceção."""
        from views.investimentos.cotacao_service import CotacaoAPIService
        svc = CotacaoAPIService()
        resultado = svc.obter_preco("BTC", "cripto")
        # pode ser None ou float — não deve lançar exceção
        assert resultado is None or isinstance(resultado, float)


# ─────────────────────────────────────────────────────────────────────────────
# IR Estimado — cálculo simplificado
# ─────────────────────────────────────────────────────────────────────────────

class TestIREstimado:
    def test_sem_lucro_sem_ir(self):
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=0.0, tipo="acao")
        assert r["ir_devido"] == pytest.approx(0.0)

    def test_prejuizo_sem_ir(self):
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=-500.0, tipo="acao")
        assert r["ir_devido"] == pytest.approx(0.0)

    def test_acao_aliquota_15(self):
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=1000.0, tipo="acao")
        assert r["aliquota"] == pytest.approx(0.15)
        assert r["ir_devido"] == pytest.approx(150.0)

    def test_fii_aliquota_20(self):
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=500.0, tipo="fii")
        assert r["aliquota"] == pytest.approx(0.20)
        assert r["ir_devido"] == pytest.approx(100.0)

    def test_cdb_aliquota_regressiva_ate_180_dias(self):
        """Até 180 dias: 22,5%."""
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=1000.0, tipo="cdb", dias_aplicacao=100)
        assert r["aliquota"] == pytest.approx(0.225)
        assert r["ir_devido"] == pytest.approx(225.0)

    def test_cdb_aliquota_regressiva_181_a_360(self):
        """181–360 dias: 20%."""
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=1000.0, tipo="cdb", dias_aplicacao=270)
        assert r["aliquota"] == pytest.approx(0.20)

    def test_cdb_aliquota_regressiva_361_a_720(self):
        """361–720 dias: 17,5%."""
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=1000.0, tipo="cdb", dias_aplicacao=500)
        assert r["aliquota"] == pytest.approx(0.175)

    def test_cdb_aliquota_regressiva_acima_720(self):
        """Acima de 720 dias: 15%."""
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=1000.0, tipo="cdb", dias_aplicacao=800)
        assert r["aliquota"] == pytest.approx(0.15)

    def test_etf_aliquota_15(self):
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=2000.0, tipo="etf")
        assert r["aliquota"] == pytest.approx(0.15)

    def test_resultado_tem_campos_esperados(self):
        from views.investimentos.ir_model import calcular_ir_estimado
        r = calcular_ir_estimado(lucro_realizado=1000.0, tipo="acao")
        assert "ir_devido"      in r
        assert "aliquota"       in r
        assert "base_calculo"   in r
        assert "nota"           in r

    def test_resumo_carteira_ir(self, banco):
        """resumo_ir_carteira agrega IR de todas as posições com lucro realizado."""
        from views.investimentos.ir_model import resumo_ir_carteira
        from views.investimentos.investimento_model import salvar_conta_investimento, salvar_ativo, salvar_movimentacao
        from tests.conftest import mov

        ci = salvar_conta_investimento({"nome": "B", "instituicao": "X", "tipo": "corretora", "observacao": ""})
        a1 = salvar_ativo({"codigo": "A1", "nome": "Acao1", "tipo": "acao", "conta_investimento_id": ci, "observacao": ""})
        a2 = salvar_ativo({"codigo": "F1", "nome": "FII1",  "tipo": "fii",  "conta_investimento_id": ci, "observacao": ""})

        salvar_movimentacao(mov(a1, ci, "compra", 1000.0, qtd=10, preco=100.0))
        salvar_movimentacao(mov(a1, ci, "venda",  1500.0, qtd=10, preco=150.0))  # +500
        salvar_movimentacao(mov(a2, ci, "compra", 2000.0, qtd=20, preco=100.0))
        salvar_movimentacao(mov(a2, ci, "venda",  2200.0, qtd=20, preco=110.0))  # +200

        resultado = resumo_ir_carteira()
        assert resultado["total_lucro"] == pytest.approx(700.0)
        assert resultado["total_ir"]    > 0
