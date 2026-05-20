"""
test_fluxo_dashboard.py — Testes do fluxo_model (página inicial / dashboard).

Bug reportado pelo usuário: ao importar uma fatura, as parcelas
do cartão NÃO apareciam no dashboard (parcelas e saldo livre não
atualizavam). Causa: `_parcelas_mes(dividas)` filtra por
`indice < d.parcelas_restantes`, mas dívidas de cartão são criadas
com `total_parcelas=0` (parcelas_restantes=0), então ficavam sempre
fora do somatório.

Fix: adicionar `_parcelas_cartao_mes(ano, mes)` que soma diretamente
da tabela parcelas_cartao, e incluir no fluxo.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestParcelasCartaoNoDashboard:
    def _setup_limpo(self, banco):
        """Remove as dívidas/fontes de exemplo populadas pelo init pra
        isolar o efeito do que o teste cria."""
        from database import conectar
        with conectar() as conn:
            conn.execute("DELETE FROM dividas")
            conn.execute("DELETE FROM fontes_receita")
            conn.execute("DELETE FROM receitas_especiais")
            conn.execute("DELETE FROM parcelas_cartao")
            conn.execute("DELETE FROM compras_cartao")
            conn.execute("DELETE FROM contas_pagar")
            conn.execute("DELETE FROM plano_contas")

    def _cartao_basico(self, banco):
        from views.cartoes.cartao_model import salvar_cartao
        return salvar_cartao({
            "nome": "Test", "banco": "outro", "bandeira": "visa",
            "limite": 5000, "limite_disponivel": 5000,
            "dia_vencimento": 10, "dia_fechamento": 5,
        })

    def test_dashboard_inclui_parcelas_cartao_apos_import(self, banco):
        """REGRESSÃO: ao importar fatura, as parcelas pendentes do mês
        devem aparecer no totais do fluxo da dashboard (campo `parcelas`)."""
        from datetime import date
        from views.cartoes.cartao_model import importar_compra_fatura
        from views.fluxo_caixa.fluxo_model import projetar_fluxo

        self._setup_limpo(banco)
        cartao_id = self._cartao_basico(banco)
        hoje = date.today()
        mes_ref = f"{hoje.year:04d}-{hoje.month:02d}"

        # Importa fatura: cria 3 parcelas, sendo a 1 do mês atual
        importar_compra_fatura({
            "cartao_id":      cartao_id,
            "descricao":      "TV 50pol",
            "numero_parcela": 1,
            "total_parcelas": 3,
            "valor_parcela":  300.0,
            "mes_referencia": mes_ref,
            "criar_historico": False,
        })

        projecao = projetar_fluxo(meses=3)
        # Mês atual (índice 0) deve incluir a parcela do cartão (R$ 300)
        assert projecao[0].parcelas >= 300.0, (
            f"parcelas do mês atual = {projecao[0].parcelas}, "
            "esperava ≥ 300 (parcela 1 do cartão importada)"
        )

    def test_dashboard_inclui_parcelas_meses_futuros(self, banco):
        """Parcelas em meses futuros também devem aparecer no fluxo."""
        from datetime import date
        from views.cartoes.cartao_model import importar_compra_fatura
        from views.fluxo_caixa.fluxo_model import projetar_fluxo

        self._setup_limpo(banco)
        cartao_id = self._cartao_basico(banco)
        hoje = date.today()
        mes_ref = f"{hoje.year:04d}-{hoje.month:02d}"

        importar_compra_fatura({
            "cartao_id":      cartao_id,
            "descricao":      "Geladeira",
            "numero_parcela": 1,
            "total_parcelas": 3,
            "valor_parcela":  500.0,
            "mes_referencia": mes_ref,
            "criar_historico": False,
        })

        projecao = projetar_fluxo(meses=3)
        # Soma das parcelas dos 3 meses deve ser pelo menos R$ 1500
        soma_parcelas = sum(p.parcelas for p in projecao)
        assert soma_parcelas >= 1500.0, (
            f"soma de parcelas em 3 meses = {soma_parcelas}, "
            "esperava ≥ 1500 (3 × R$ 500 da compra parcelada)"
        )

    def test_dashboard_saldo_livre_diminui_com_fatura(self, banco):
        """O saldo_livre do mês deve DIMINUIR após import de fatura."""
        from datetime import date, datetime
        from database import conectar
        from views.cartoes.cartao_model import importar_compra_fatura
        from views.fluxo_caixa.fluxo_model import projetar_fluxo

        self._setup_limpo(banco)
        # Cria uma receita base pra ter saldo positivo
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            conn.execute(
                "INSERT INTO fontes_receita (nome, tipo, valor_mensal,"
                " periodicidade, dia_pagamento, ativa, padrao, criado_em)"
                " VALUES (?,'clt',?,?,'mensal',1,0,?)",
                ("Salario", 5000.0, 5, agora),
            )

        cartao_id = self._cartao_basico(banco)

        antes = projetar_fluxo(meses=1)[0].saldo_livre

        hoje = date.today()
        importar_compra_fatura({
            "cartao_id":      cartao_id,
            "descricao":      "Notebook",
            "numero_parcela": 1,
            "total_parcelas": 1,
            "valor_parcela":  1000.0,
            "mes_referencia": f"{hoje.year:04d}-{hoje.month:02d}",
            "criar_historico": False,
        })

        depois = projetar_fluxo(meses=1)[0].saldo_livre

        assert depois < antes, (
            f"saldo NÃO diminuiu após import: antes={antes}, depois={depois}"
        )
        # Diferença deve ser aproximadamente R$ 1000 (valor da fatura)
        assert abs((antes - depois) - 1000.0) < 0.01

    def test_parcelas_cartao_nao_duplicam_com_dividas(self, banco):
        """Sanidade: parcelas de cartão (vindas de parcelas_cartao) não
        podem ser contadas em DOBRO via dividas.parcela_mensal."""
        from datetime import date
        from views.cartoes.cartao_model import importar_compra_fatura
        from views.fluxo_caixa.fluxo_model import projetar_fluxo

        self._setup_limpo(banco)
        cartao_id = self._cartao_basico(banco)
        hoje = date.today()
        importar_compra_fatura({
            "cartao_id":      cartao_id,
            "descricao":      "Item Único",
            "numero_parcela": 1,
            "total_parcelas": 1,
            "valor_parcela":  100.0,
            "mes_referencia": f"{hoje.year:04d}-{hoje.month:02d}",
            "criar_historico": False,
        })

        projecao = projetar_fluxo(meses=1)
        # Deve aparecer EXATAMENTE R$ 100 no mês atual, não R$ 200
        assert projecao[0].parcelas == pytest.approx(100.0), (
            f"parcelas duplicaram: {projecao[0].parcelas}"
        )
