"""
conftest.py — Fixtures compartilhadas para os testes do Serenus.

Estratégia de isolamento de banco de dados:
- Cada teste recebe um banco SQLite temporário (tmp_path).
- CAMINHO_BANCO em database.py é monkeypatched para o banco temporário.
- O banco é inicializado com o schema completo antes de cada teste.
- Após o teste, o tmp_path é descartado automaticamente pelo pytest.
"""

import sys
from pathlib import Path

# Garante que a raiz do projeto está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import database as db_module


@pytest.fixture(autouse=False)
def banco(tmp_path, monkeypatch):
    """
    Fixture principal: banco SQLite isolado por teste.
    Uso: adicione `banco` como parâmetro da função de teste.
    """
    db_path = tmp_path / "test_serenus.db"
    monkeypatch.setattr(db_module, "CAMINHO_BANCO", db_path)
    db_module.inicializar_banco()
    return db_path


@pytest.fixture
def conta_inv(banco):
    """Conta de investimento padrão para testes."""
    from views.investimentos.investimento_model import salvar_conta_investimento
    id_ = salvar_conta_investimento({
        "nome": "Corretora Teste",
        "instituicao": "Banco Teste S.A.",
        "tipo": "corretora",
        "observacao": "",
    })
    return id_


@pytest.fixture
def ativo_acao(conta_inv, banco):
    """Ativo do tipo ação para testes."""
    from views.investimentos.investimento_model import salvar_ativo
    id_ = salvar_ativo({
        "codigo": "TEST4",
        "nome": "Empresa Teste PN",
        "tipo": "acao",
        "conta_investimento_id": conta_inv,
        "observacao": "",
    })
    return id_


@pytest.fixture
def ativo_fii(conta_inv, banco):
    """Ativo do tipo FII para testes."""
    from views.investimentos.investimento_model import salvar_ativo
    id_ = salvar_ativo({
        "codigo": "TFII11",
        "nome": "FII Teste",
        "tipo": "fii",
        "conta_investimento_id": conta_inv,
        "observacao": "",
    })
    return id_


@pytest.fixture
def ativo_cdb(conta_inv, banco):
    """Ativo do tipo CDB (renda fixa) para testes."""
    from views.investimentos.investimento_model import salvar_ativo
    id_ = salvar_ativo({
        "codigo": "CDB-TESTE-120CDI",
        "nome": "CDB Teste 120% CDI",
        "tipo": "cdb",
        "conta_investimento_id": conta_inv,
        "indexador": "cdi",
        "taxa_contratada": 120.0,
        "vencimento": "2027-12-01",
        "observacao": "",
    })
    return id_


def mov(ativo_id: int, conta_id: int, tipo: str, valor: float,
        qtd: float = 0.0, preco: float = 0.0,
        taxas: float = 0.0, data: str = "2025-06-15",
        financeiro: bool = False) -> dict:
    """Helper para construir dados de movimentação nos testes."""
    from config import MOV_INV_SAIDA
    liq = valor + taxas if tipo in MOV_INV_SAIDA else max(0.0, valor - taxas)
    return {
        "ativo_id": ativo_id,
        "conta_investimento_id": conta_id,
        "tipo": tipo,
        "data": data,
        "quantidade": qtd,
        "preco_unitario": preco,
        "valor_bruto": valor,
        "taxas": taxas,
        "valor_liquido": liq,
        "observacao": "",
        "registrar_no_financeiro": financeiro,
    }
