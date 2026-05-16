"""
test_metas_model.py — Testes do módulo de metas financeiras.
"""
import pytest
from datetime import date, timedelta


# ─────────────────────────────────────────────────────────────────────────────
# CRUD básico
# ─────────────────────────────────────────────────────────────────────────────

class TestCRUDMetas:
    def test_criar_meta(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        salvar_meta({"nome": "Viagem Europa", "valor_alvo": 15000.0,
                     "valor_atual": 0.0, "prazo": "2026-12-01",
                     "descricao": "Férias em família"})
        metas = listar_metas()
        assert len(metas) == 1
        assert metas[0].nome == "Viagem Europa"

    def test_criar_meta_retorna_id(self, banco):
        from views.metas.metas_model import salvar_meta
        mid = salvar_meta({"nome": "Carro", "valor_alvo": 50000.0,
                           "valor_atual": 0.0, "prazo": None, "descricao": ""})
        assert isinstance(mid, int) and mid > 0

    def test_listar_metas_vazio(self, banco):
        from views.metas.metas_model import listar_metas
        assert listar_metas() == []

    def test_atualizar_valor_atual(self, banco):
        from views.metas.metas_model import salvar_meta, atualizar_valor_meta, listar_metas
        mid = salvar_meta({"nome": "Fundo Emergência", "valor_alvo": 10000.0,
                           "valor_atual": 0.0, "prazo": None, "descricao": ""})
        atualizar_valor_meta(mid, 3000.0)
        meta = listar_metas()[0]
        assert meta.valor_atual == pytest.approx(3000.0)

    def test_excluir_meta(self, banco):
        from views.metas.metas_model import salvar_meta, excluir_meta, listar_metas
        mid = salvar_meta({"nome": "X", "valor_alvo": 100.0,
                           "valor_atual": 0.0, "prazo": None, "descricao": ""})
        excluir_meta(mid)
        assert listar_metas() == []

    def test_editar_meta(self, banco):
        from views.metas.metas_model import salvar_meta, salvar_meta as editar, listar_metas
        mid = salvar_meta({"nome": "Notebook", "valor_alvo": 5000.0,
                           "valor_atual": 0.0, "prazo": None, "descricao": ""})
        editar({"nome": "Notebook Novo", "valor_alvo": 6000.0,
                "valor_atual": 500.0, "prazo": None, "descricao": "Atualizado"}, id=mid)
        meta = listar_metas()[0]
        assert meta.nome == "Notebook Novo"
        assert meta.valor_alvo == pytest.approx(6000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Progresso
# ─────────────────────────────────────────────────────────────────────────────

class TestProgressoMeta:
    def test_progresso_zero_quando_vazio(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        salvar_meta({"nome": "A", "valor_alvo": 1000.0,
                     "valor_atual": 0.0, "prazo": None, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.progresso_pct == pytest.approx(0.0)

    def test_progresso_50_porcento(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        salvar_meta({"nome": "B", "valor_alvo": 2000.0,
                     "valor_atual": 1000.0, "prazo": None, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.progresso_pct == pytest.approx(50.0)

    def test_progresso_100_quando_atingido(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        salvar_meta({"nome": "C", "valor_alvo": 500.0,
                     "valor_atual": 500.0, "prazo": None, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.progresso_pct == pytest.approx(100.0)

    def test_progresso_nao_ultrapassa_100(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        salvar_meta({"nome": "D", "valor_alvo": 500.0,
                     "valor_atual": 700.0, "prazo": None, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.progresso_pct <= 100.0

    def test_meta_concluida(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        salvar_meta({"nome": "E", "valor_alvo": 1000.0,
                     "valor_atual": 1000.0, "prazo": None, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.concluida is True

    def test_meta_nao_concluida(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        salvar_meta({"nome": "F", "valor_alvo": 1000.0,
                     "valor_atual": 500.0, "prazo": None, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.concluida is False


# ─────────────────────────────────────────────────────────────────────────────
# Prazo e dias restantes
# ─────────────────────────────────────────────────────────────────────────────

class TestPrazoMeta:
    def test_dias_restantes_futuro(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        prazo = (date.today() + timedelta(days=30)).isoformat()
        salvar_meta({"nome": "G", "valor_alvo": 1000.0,
                     "valor_atual": 0.0, "prazo": prazo, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.dias_restantes == pytest.approx(30, abs=1)

    def test_dias_restantes_none_sem_prazo(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        salvar_meta({"nome": "H", "valor_alvo": 1000.0,
                     "valor_atual": 0.0, "prazo": None, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.dias_restantes is None

    def test_meta_atrasada_dias_negativos(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        prazo = (date.today() - timedelta(days=5)).isoformat()
        salvar_meta({"nome": "I", "valor_alvo": 1000.0,
                     "valor_atual": 0.0, "prazo": prazo, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.dias_restantes < 0

    def test_economia_mensal_necessaria(self, banco):
        """Com 10 meses restantes e faltando R$1000, precisa de R$100/mês."""
        from views.metas.metas_model import salvar_meta, listar_metas
        prazo = (date.today() + timedelta(days=305)).isoformat()  # ~10 meses
        salvar_meta({"nome": "J", "valor_alvo": 1000.0,
                     "valor_atual": 0.0, "prazo": prazo, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.economia_mensal_necessaria is not None
        assert meta.economia_mensal_necessaria > 0

    def test_economia_mensal_none_sem_prazo(self, banco):
        from views.metas.metas_model import salvar_meta, listar_metas
        salvar_meta({"nome": "K", "valor_alvo": 500.0,
                     "valor_atual": 0.0, "prazo": None, "descricao": ""})
        meta = listar_metas()[0]
        assert meta.economia_mensal_necessaria is None
