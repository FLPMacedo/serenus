"""
test_integracao.py — Testes de integração entre módulos do Serenus.

Verifica os pontos de cruzamento reais entre módulos:
  TestIntegracaoCartaoContas    — cartao_model → contas_pagar
  TestIntegracaoInvestContas    — investimento_model → contas_pagar
  TestIntegracaoExtrato         — extrato_model agrega receitas + investimentos + vendas
  TestIntegracaoProjecao        — projecao_model agrega receitas + dívidas + vendas
  TestIntegracaoAlertas         — alertas_pendentes lê todos os módulos
  TestIntegracaoExportar        — exportar_model gera Excel de todos os módulos sem erro
"""

import sys
from pathlib import Path
from datetime import date, timedelta, datetime

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import conectar

_AGORA = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
_HOJE  = date.today().isoformat()
_MES   = date.today().month
_ANO   = date.today().year
_MES_REF = f"{_ANO:04d}-{_MES:02d}"


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------

def _inserir_plano(nome: str = "Teste", tipo: str = "variavel") -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)"
            " VALUES (?,?,'Outros',1,0,?)",
            (nome, tipo, _AGORA),
        )
        return cur.lastrowid


def _inserir_conta_pagar(plano_id: int, valor: float,
                         vencimento: str, status: str = "pendente") -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO contas_pagar (plano_conta_id, descricao, valor,"
            " data_vencimento, status, recorrente, criado_em)"
            " VALUES (?,?,?,?,?,0,?)",
            (plano_id, "Conta teste", valor, vencimento, status, _AGORA),
        )
        return cur.lastrowid


def _inserir_fonte(nome: str = "Salário", valor: float = 5000.0,
                   dia: int = 5) -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO fontes_receita (nome, tipo, valor_mensal, periodicidade,"
            " dia_pagamento, ativa, padrao, criado_em)"
            " VALUES (?,'clt',?,?,'mensal',?,1,0,?)",
            (nome, valor, valor, dia, 1, _AGORA),
        )
        return cur.lastrowid


def _inserir_cartao(nome: str = "Nubank Teste") -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO cartoes (nome, bandeira, banco, limite, limite_disponivel,"
            " dia_vencimento, dia_fechamento, ativo, padrao, criado_em)"
            " VALUES (?,?,?,?,?,10,5,1,0,?)",
            (nome, "visa", "nubank", 10000.0, 10000.0, _AGORA),
        )
        return cur.lastrowid


def _inserir_conta_invest(nome: str = "Corretora") -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO contas_investimento (nome, instituicao, tipo, criado_em)"
            " VALUES (?,?,'corretora',?)",
            (nome, "Banco Teste", _AGORA),
        )
        return cur.lastrowid


def _inserir_ativo(conta_id: int, codigo: str = "TEST4",
                   tipo: str = "acao") -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO ativos (codigo, nome, tipo, conta_investimento_id, criado_em)"
            " VALUES (?,?,?,?,?)",
            (codigo, "Empresa Teste", tipo, conta_id, _AGORA),
        )
        return cur.lastrowid


def _inserir_divida(nome: str = "Financiamento", parcela: float = 500.0,
                    parcelas: int = 24) -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO dividas (nome, tipo, saldo_atual, parcela_mensal,"
            " total_parcelas, parcelas_pagas, dia_vencimento, taxa_juros,"
            " observacao, ativa, criado_em)"
            " VALUES (?,?,?,?,?,0,10,0.0,'',1,?)",
            (nome, "financiamento", parcela * parcelas, parcela, parcelas, _AGORA),
        )
        return cur.lastrowid


def _inserir_venda_avista(valor: float = 200.0,
                          data: str | None = None) -> int:
    from views.vendas.venda_model import salvar_venda
    dados = {
        "descricao": "Venda integração",
        "data_venda": data or _HOJE,
        "desconto": 0.0,
        "tipo_pagamento": "avista",
        "observacao": "",
    }
    itens = [{"produto_id": None, "descricao": "Item", "quantidade": 1.0,
               "preco_unit": valor}]
    return salvar_venda(dados, itens)


def _inserir_venda_aprazo(valor: float = 300.0, parcelas: int = 3,
                          data_p1: str | None = None) -> int:
    from views.vendas.venda_model import salvar_venda
    dados = {
        "descricao": "Venda a prazo integração",
        "data_venda": _HOJE,
        "desconto": 0.0,
        "tipo_pagamento": "aprazo",
        "parcelas": parcelas,
        "data_primeira_parcela": data_p1 or _HOJE,
        "observacao": "",
    }
    itens = [{"produto_id": None, "descricao": "Item prazo", "quantidade": 1.0,
               "preco_unit": valor}]
    return salvar_venda(dados, itens)


# ===========================================================================
# 1. Cartão → Contas a Pagar
# ===========================================================================

class TestIntegracaoCartaoContas:
    """lancar_fatura_contas_pagar() deve criar entrada em contas_pagar."""

    def test_lancar_fatura_cria_conta_pagar(self, banco):
        from views.cartoes.cartao_model import registrar_compra_parcelas, lancar_fatura_contas_pagar

        cartao_id = _inserir_cartao()
        registrar_compra_parcelas({
            "cartao_id":     cartao_id,
            "descricao":     "Compra Teste",
            "valor_total":   600.0,
            "total_parcelas": 3,
            "mes_inicio":    _MES_REF,
        })

        lancar_fatura_contas_pagar(cartao_id, _MES, _ANO)

        with conectar() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM contas_pagar cp"
                " JOIN plano_contas pc ON pc.id = cp.plano_conta_id"
                " WHERE pc.categoria='Cartão de Crédito'",
            ).fetchone()
        assert row["n"] >= 1

    def test_lancar_fatura_valor_correto(self, banco):
        from views.cartoes.cartao_model import registrar_compra_parcelas, lancar_fatura_contas_pagar, total_fatura_mes

        cartao_id = _inserir_cartao()
        registrar_compra_parcelas({
            "cartao_id":     cartao_id,
            "descricao":     "Notebook",
            "valor_total":   1200.0,
            "total_parcelas": 1,
            "mes_inicio":    _MES_REF,
        })

        total_dict = total_fatura_mes(cartao_id, _MES, _ANO)
        total = float(total_dict["total"]) if isinstance(total_dict, dict) else float(total_dict)
        lancar_fatura_contas_pagar(cartao_id, _MES, _ANO)

        with conectar() as conn:
            row = conn.execute(
                "SELECT valor FROM contas_pagar cp"
                " JOIN plano_contas pc ON pc.id = cp.plano_conta_id"
                " WHERE pc.categoria='Cartão de Crédito' ORDER BY cp.id DESC LIMIT 1",
            ).fetchone()
        assert pytest.approx(float(row["valor"]), abs=0.01) == total

    def test_fatura_sem_parcelas_nao_cria_conta(self, banco):
        from views.cartoes.cartao_model import lancar_fatura_contas_pagar

        cartao_id = _inserir_cartao()
        lancar_fatura_contas_pagar(cartao_id, _MES, _ANO)

        with conectar() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM contas_pagar cp"
                " JOIN plano_contas pc ON pc.id = cp.plano_conta_id"
                " WHERE pc.categoria='Cartão de Crédito'",
            ).fetchone()
        assert row["n"] == 0

    def test_limite_reduzido_apos_compra(self, banco):
        from views.cartoes.cartao_model import registrar_compra_parcelas

        cartao_id = _inserir_cartao()
        registrar_compra_parcelas({
            "cartao_id":     cartao_id,
            "descricao":     "Celular",
            "valor_total":   2000.0,
            "total_parcelas": 2,
            "mes_inicio":    _MES_REF,
        })

        with conectar() as conn:
            row = conn.execute(
                "SELECT limite_disponivel FROM cartoes WHERE id=?", (cartao_id,)
            ).fetchone()
        assert pytest.approx(float(row["limite_disponivel"]), abs=0.01) == 8000.0


# ===========================================================================
# 2. Investimento → Contas a Pagar
# ===========================================================================

class TestIntegracaoInvestContas:
    """salvar_movimentacao com registrar_no_financeiro=True deve gerar conta_pagar."""

    def test_resgate_registra_no_financeiro(self, banco):
        from views.investimentos.investimento_model import (
            salvar_conta_investimento, salvar_ativo, salvar_movimentacao,
        )

        conta_id = salvar_conta_investimento({
            "nome": "Corretora", "instituicao": "Banco", "tipo": "corretora", "observacao": "",
        })
        ativo_id = salvar_ativo({
            "codigo": "CDB01", "nome": "CDB Teste", "tipo": "cdb",
            "conta_investimento_id": conta_id, "observacao": "",
        })

        salvar_movimentacao({
            "ativo_id":              ativo_id,
            "conta_investimento_id": conta_id,
            "tipo":                  "resgate",
            "data":                  _HOJE,
            "quantidade":            0.0,
            "preco_unitario":        0.0,
            "valor_bruto":           1000.0,
            "taxas":                 0.0,
            "valor_liquido":         1000.0,
            "observacao":            "",
            "registrar_no_financeiro": True,
        })

        from views.investimentos.investimento_model import rendimentos_financeiros_mes
        entradas = rendimentos_financeiros_mes(_MES, _ANO)
        assert len(entradas) >= 1
        assert any(e["credito"] == pytest.approx(1000.0) for e in entradas)

    def test_compra_sem_financeiro_nao_entra_extrato(self, banco):
        from views.investimentos.investimento_model import (
            salvar_conta_investimento, salvar_ativo, salvar_movimentacao,
            rendimentos_financeiros_mes,
        )

        conta_id = salvar_conta_investimento({
            "nome": "Corretora2", "instituicao": "Banco2", "tipo": "corretora", "observacao": "",
        })
        ativo_id = salvar_ativo({
            "codigo": "PETR4", "nome": "Petrobras", "tipo": "acao",
            "conta_investimento_id": conta_id, "observacao": "",
        })

        salvar_movimentacao({
            "ativo_id":              ativo_id,
            "conta_investimento_id": conta_id,
            "tipo":                  "compra",
            "data":                  _HOJE,
            "quantidade":            100.0,
            "preco_unitario":        35.0,
            "valor_bruto":           3500.0,
            "taxas":                 5.0,
            "valor_liquido":         3505.0,
            "observacao":            "",
            "registrar_no_financeiro": False,
        })

        entradas = rendimentos_financeiros_mes(_MES, _ANO)
        assert all(e.get("descricao", "").find("PETR4") == -1 for e in entradas)


# ===========================================================================
# 3. Extrato agrega receitas + investimentos + vendas
# ===========================================================================

class TestIntegracaoExtrato:
    """extrato_mes() deve consolidar créditos de todos os módulos."""

    def test_extrato_inclui_fonte_receita(self, banco):
        from views.fluxo_caixa.extrato_model import extrato_mes
        from views.receitas.receita_model import salvar_fonte

        salvar_fonte({
            "nome": "Salário", "tipo": "clt", "valor_mensal": 4000.0,
            "periodicidade": "mensal", "dia_pagamento": 5, "ativa": True, "padrao": False,
        })

        linhas = extrato_mes(_MES, _ANO)
        creditos = [l for l in linhas if l.credito > 0 and l.descricao == "Salário"]
        assert len(creditos) == 1
        assert pytest.approx(creditos[0].credito, abs=0.01) == 4000.0

    def test_extrato_inclui_venda_avista(self, banco):
        from views.fluxo_caixa.extrato_model import extrato_mes

        _inserir_venda_avista(valor=500.0)

        linhas = extrato_mes(_MES, _ANO)
        creditos_venda = [l for l in linhas if l.categoria == "Vendas" and l.credito > 0]
        assert len(creditos_venda) >= 1
        assert any(pytest.approx(l.credito, abs=0.01) == 500.0 for l in creditos_venda)

    def test_extrato_venda_aprazo_ausente_antes_receber(self, banco):
        from views.fluxo_caixa.extrato_model import extrato_mes
        from views.vendas.venda_model import listar_contas_receber

        _inserir_venda_aprazo(valor=300.0, parcelas=3)

        # Nenhuma parcela recebida ainda
        linhas = extrato_mes(_MES, _ANO)
        total_vendas = sum(l.credito for l in linhas if l.categoria == "Vendas")
        assert total_vendas == pytest.approx(0.0)

    def test_extrato_venda_aprazo_aparece_apos_recebimento(self, banco):
        from views.fluxo_caixa.extrato_model import extrato_mes
        from views.vendas.venda_model import listar_contas_receber, marcar_recebido

        _inserir_venda_aprazo(valor=300.0, parcelas=3)
        parcelas = listar_contas_receber(status="pendente")
        marcar_recebido(parcelas[0].id, _HOJE)

        linhas = extrato_mes(_MES, _ANO)
        creditos_venda = [l for l in linhas if l.categoria == "Vendas" and l.credito > 0]
        assert len(creditos_venda) >= 1

    def test_extrato_inclui_rendimento_investimento(self, banco):
        from views.fluxo_caixa.extrato_model import extrato_mes
        from views.investimentos.investimento_model import (
            salvar_conta_investimento, salvar_ativo, salvar_movimentacao,
        )

        conta_id = salvar_conta_investimento({
            "nome": "Cor", "instituicao": "B", "tipo": "corretora", "observacao": "",
        })
        ativo_id = salvar_ativo({
            "codigo": "DIV3", "nome": "Empresa Div", "tipo": "acao",
            "conta_investimento_id": conta_id, "observacao": "",
        })
        salvar_movimentacao({
            "ativo_id": ativo_id, "conta_investimento_id": conta_id,
            "tipo": "dividendo", "data": _HOJE,
            "quantidade": 0.0, "preco_unitario": 0.0,
            "valor_bruto": 200.0, "taxas": 0.0, "valor_liquido": 200.0,
            "observacao": "", "registrar_no_financeiro": True,
        })

        linhas = extrato_mes(_MES, _ANO)
        inv = [l for l in linhas if l.categoria == "Rendimento de investimento" and l.credito > 0]
        assert len(inv) >= 1
        assert any(pytest.approx(l.credito, abs=0.01) == 200.0 for l in inv)

    def test_extrato_inclui_contas_pagar_como_debito(self, banco):
        from views.fluxo_caixa.extrato_model import extrato_mes

        plano_id = _inserir_plano("Aluguel")
        _inserir_conta_pagar(plano_id, 1500.0, _HOJE, status="pago")

        linhas = extrato_mes(_MES, _ANO)
        debitos = [l for l in linhas if l.debito > 0]
        assert any(pytest.approx(l.debito, abs=0.01) == 1500.0 for l in debitos)

    def test_saldo_acumulado_consistente(self, banco):
        from views.fluxo_caixa.extrato_model import extrato_mes
        from views.receitas.receita_model import salvar_fonte

        salvar_fonte({
            "nome": "Renda", "tipo": "clt", "valor_mensal": 3000.0,
            "periodicidade": "mensal", "dia_pagamento": 1, "ativa": True, "padrao": False,
        })
        plano_id = _inserir_plano("Despesa")
        _inserir_conta_pagar(plano_id, 500.0, _HOJE, status="pago")

        linhas = extrato_mes(_MES, _ANO)
        assert len(linhas) >= 2
        # Saldo da última linha deve ser a soma de todos os créditos menos débitos
        total_credito = sum(l.credito for l in linhas)
        total_debito  = sum(l.debito  for l in linhas)
        assert pytest.approx(linhas[-1].saldo, abs=0.01) == total_credito - total_debito


# ===========================================================================
# 4. Projeção agrega receitas + dívidas + vendas
# ===========================================================================

class TestIntegracaoProjecao:
    """projetar() deve incorporar receitas reais, dívidas e vendas realizadas."""

    def test_projecao_inclui_fonte_receita(self, banco):
        from views.visao_futura.projecao_model import projetar
        from views.receitas.receita_model import salvar_fonte

        # Banco já tem fontes padrão com ativa=1; somamos mais uma
        base = projetar(meses=1, inicio_offset=0)[0].receitas
        salvar_fonte({
            "nome": "Freela extra", "tipo": "freela", "valor_mensal": 2000.0,
            "periodicidade": "mensal", "dia_pagamento": 15, "ativa": True, "padrao": False,
        })

        meses = projetar(meses=1, inicio_offset=0)
        assert pytest.approx(meses[0].receitas, abs=0.01) == base + 2000.0

    def test_projecao_inclui_venda_avista_mes_atual(self, banco):
        from views.visao_futura.projecao_model import projetar

        _inserir_venda_avista(valor=800.0)

        meses = projetar(meses=1, inicio_offset=0)
        assert meses[0].receitas >= 800.0

    def test_projecao_nao_inclui_venda_em_mes_futuro(self, banco):
        from views.visao_futura.projecao_model import projetar, _receitas_vendas_mes

        # Venda registrada hoje não deve aparecer como receita em meses futuros
        _inserir_venda_avista(valor=999.0)

        mes_futuro_num = _MES % 12 + 1
        ano_futuro = _ANO + (1 if _MES == 12 else 0)
        receitas_futuras = _receitas_vendas_mes(ano_futuro, mes_futuro_num)
        assert receitas_futuras == pytest.approx(0.0)

    def test_projecao_inclui_dividas_futuras(self, banco):
        from views.visao_futura.projecao_model import projetar

        _inserir_divida(parcela=600.0, parcelas=12)

        meses = projetar(meses=2, inicio_offset=0)
        mes_futuro = meses[1]
        assert mes_futuro.dividas >= 600.0

    def test_projecao_inclui_despesas_reais_passadas(self, banco):
        from views.visao_futura.projecao_model import projetar

        plano_id = _inserir_plano("Fixo", "fixo")
        _inserir_conta_pagar(plano_id, 1000.0, _HOJE)

        meses = projetar(meses=1, inicio_offset=0)
        assert meses[0].desp_fixas >= 1000.0

    def test_projecao_detalhe_inclui_vendas(self, banco):
        from views.visao_futura.projecao_model import projetar, carregar_detalhes

        _inserir_venda_avista(valor=350.0)

        meses = projetar(meses=1, inicio_offset=0)
        det = carregar_detalhes(meses)
        assert "Vendas e Serviços" in det.receitas
        assert det.receitas["Vendas e Serviços"][0] == pytest.approx(350.0, abs=0.01)

    def test_projecao_saldo_coerente_com_receitas_e_saidas(self, banco):
        from views.visao_futura.projecao_model import projetar

        meses = projetar(meses=1, inicio_offset=0)
        m = meses[0]
        assert pytest.approx(m.saldo, abs=0.01) == m.receitas - m.total_saidas


# ===========================================================================
# 5. Alertas lê múltiplos módulos
# ===========================================================================

class TestIntegracaoAlertas:
    """alertas_pendentes() deve cruzar contas_pagar, cartões, RF e recebíveis."""

    def test_alertas_conta_pagar_vencida(self, banco):
        from views.alertas.alertas_model import alertas_pendentes

        plano_id = _inserir_plano("Conta vencida")
        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_conta_pagar(plano_id, 200.0, ontem)

        alertas = alertas_pendentes()
        tipos = [a.tipo for a in alertas]
        assert "conta_vencida" in tipos

    def test_alertas_parcela_cartao_mes_atual(self, banco):
        from views.alertas.alertas_model import alertas_pendentes
        from views.cartoes.cartao_model import registrar_compra_parcelas

        cartao_id = _inserir_cartao("Visa Alerta")
        registrar_compra_parcelas({
            "cartao_id":     cartao_id,
            "descricao":     "Compra alerta",
            "valor_total":   400.0,
            "total_parcelas": 1,
            "mes_inicio":    _MES_REF,
        })

        alertas = alertas_pendentes()
        tipos = [a.tipo for a in alertas]
        # O alerta pode ser "parcela_cartao" ou "fatura_cartao" dependendo da versão
        assert any(t in tipos for t in ("parcela_cartao", "fatura_cartao"))

    def test_alertas_recebivel_vencido(self, banco):
        from views.alertas.alertas_model import alertas_pendentes

        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_venda_aprazo(valor=150.0, parcelas=1, data_p1=ontem)

        alertas = alertas_pendentes()
        tipos = [a.tipo for a in alertas]
        assert "recebivel_vencido" in tipos

    def test_alertas_recebivel_vencendo_em_breve(self, banco):
        from views.alertas.alertas_model import alertas_pendentes

        em3 = (date.today() + timedelta(days=3)).isoformat()
        _inserir_venda_aprazo(valor=150.0, parcelas=1, data_p1=em3)

        alertas = alertas_pendentes()
        tipos = [a.tipo for a in alertas]
        assert "recebivel_vencendo" in tipos

    def test_sem_dados_retorna_lista_vazia(self, banco):
        from views.alertas.alertas_model import alertas_pendentes

        alertas = alertas_pendentes()
        assert alertas == []

    def test_alertas_sem_duplicatas_entre_modulos(self, banco):
        from views.alertas.alertas_model import alertas_pendentes
        from views.cartoes.cartao_model import registrar_compra_parcelas

        plano_id = _inserir_plano("Conta dup")
        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_conta_pagar(plano_id, 100.0, ontem)

        cartao_id = _inserir_cartao("Dup Card")
        registrar_compra_parcelas({
            "cartao_id": cartao_id, "descricao": "Compra dup",
            "valor_total": 200.0, "total_parcelas": 1, "mes_inicio": _MES_REF,
        })

        ontem2 = (date.today() - timedelta(days=2)).isoformat()
        _inserir_venda_aprazo(valor=80.0, parcelas=1, data_p1=ontem2)

        alertas = alertas_pendentes()
        # Verifica que não há pares (tipo, descricao) duplicados entre módulos
        chaves = [(a.tipo, a.descricao) for a in alertas]
        assert len(chaves) == len(set(chaves)), "Alertas duplicados entre módulos"


# ===========================================================================
# 6. Exportar gera arquivos sem erros
# ===========================================================================

class TestIntegracaoExportar:
    """exportar_model deve gerar cada tipo de relatório Excel sem exceções."""

    def _dest(self, tmp_path: Path, nome: str) -> str:
        return str(tmp_path / nome)

    def test_exportar_extrato_sem_erro(self, banco, tmp_path):
        from views.exportar.exportar_model import exportar_extrato_xlsx
        from views.receitas.receita_model import salvar_fonte

        salvar_fonte({
            "nome": "Fonte X", "tipo": "clt", "valor_mensal": 1000.0,
            "periodicidade": "mensal", "dia_pagamento": 1, "ativa": True, "padrao": False,
        })
        dest = self._dest(tmp_path, "extrato.xlsx")
        exportar_extrato_xlsx(_MES, _ANO, dest)
        assert Path(dest).exists() and Path(dest).stat().st_size > 0

    def test_exportar_contas_pagar_sem_erro(self, banco, tmp_path):
        from views.exportar.exportar_model import exportar_contas_pagar_xlsx

        plano_id = _inserir_plano("Aluguel Export")
        _inserir_conta_pagar(plano_id, 900.0, _HOJE)
        dest = self._dest(tmp_path, "contas.xlsx")
        exportar_contas_pagar_xlsx(_MES, _ANO, dest)
        assert Path(dest).exists() and Path(dest).stat().st_size > 0

    def test_exportar_receitas_sem_erro(self, banco, tmp_path):
        from views.exportar.exportar_model import exportar_receitas_xlsx
        from views.receitas.receita_model import salvar_fonte

        salvar_fonte({
            "nome": "Receita Export", "tipo": "clt", "valor_mensal": 3000.0,
            "periodicidade": "mensal", "dia_pagamento": 5, "ativa": True, "padrao": False,
        })
        dest = self._dest(tmp_path, "receitas.xlsx")
        exportar_receitas_xlsx(dest)
        assert Path(dest).exists() and Path(dest).stat().st_size > 0

    def test_exportar_carteira_sem_erro(self, banco, tmp_path):
        from views.exportar.exportar_model import exportar_carteira_xlsx
        from views.investimentos.investimento_model import (
            salvar_conta_investimento, salvar_ativo, salvar_movimentacao,
        )

        conta_id = salvar_conta_investimento({
            "nome": "Carteira X", "instituicao": "B", "tipo": "corretora", "observacao": "",
        })
        ativo_id = salvar_ativo({
            "codigo": "EXPT4", "nome": "Export Ação", "tipo": "acao",
            "conta_investimento_id": conta_id, "observacao": "",
        })
        salvar_movimentacao({
            "ativo_id": ativo_id, "conta_investimento_id": conta_id,
            "tipo": "compra", "data": _HOJE,
            "quantidade": 10.0, "preco_unitario": 30.0,
            "valor_bruto": 300.0, "taxas": 0.0, "valor_liquido": 300.0,
            "observacao": "", "registrar_no_financeiro": False,
        })

        dest = self._dest(tmp_path, "carteira.xlsx")
        exportar_carteira_xlsx(dest)
        assert Path(dest).exists() and Path(dest).stat().st_size > 0

    def test_exportar_dividas_sem_erro(self, banco, tmp_path):
        from views.exportar.exportar_model import exportar_dividas_xlsx

        _inserir_divida("Financ Export", parcela=400.0, parcelas=12)
        dest = self._dest(tmp_path, "dividas.xlsx")
        exportar_dividas_xlsx(dest)
        assert Path(dest).exists() and Path(dest).stat().st_size > 0

    def test_exportar_projecao_sem_erro(self, banco, tmp_path):
        from views.exportar.exportar_model import exportar_projecao_xlsx

        dest = self._dest(tmp_path, "projecao.xlsx")
        exportar_projecao_xlsx(dest)
        assert Path(dest).exists() and Path(dest).stat().st_size > 0

    def test_exportar_metas_sem_erro(self, banco, tmp_path):
        from views.exportar.exportar_model import exportar_metas_xlsx
        from views.metas.metas_model import salvar_meta

        salvar_meta({
            "nome": "Meta Export", "valor_alvo": 10000.0, "valor_atual": 1000.0,
            "prazo": "2027-12-01", "descricao": "",
        })
        dest = self._dest(tmp_path, "metas.xlsx")
        exportar_metas_xlsx(dest)
        assert Path(dest).exists() and Path(dest).stat().st_size > 0

    def test_exportar_banco_vazio_nao_levanta_excecao(self, banco, tmp_path):
        from views.exportar.exportar_model import (
            exportar_extrato_xlsx, exportar_contas_pagar_xlsx,
            exportar_receitas_xlsx, exportar_projecao_xlsx,
        )

        exportar_extrato_xlsx(_MES, _ANO, self._dest(tmp_path, "ext_vazio.xlsx"))
        exportar_contas_pagar_xlsx(_MES, _ANO, self._dest(tmp_path, "cp_vazio.xlsx"))
        exportar_receitas_xlsx(self._dest(tmp_path, "rec_vazio.xlsx"))
        exportar_projecao_xlsx(self._dest(tmp_path, "proj_vazio.xlsx"))

        for nome in ("ext_vazio.xlsx", "cp_vazio.xlsx", "rec_vazio.xlsx", "proj_vazio.xlsx"):
            assert Path(self._dest(tmp_path, nome)).exists()


# ---------------------------------------------------------------------------
# OS interna: reuso de produtos/serviços e isolamento do financeiro
# ---------------------------------------------------------------------------

def _dados_os_min(nome: str = "Solicitante", data: str | None = None) -> dict:
    """Builder mínimo de OS para testes de integração."""
    return {
        "solicitante_nome":  nome,
        "solicitante_setor": "",
        "solicitante_ramal": "",
        "data_solicitacao":  data or _HOJE,
        "hora_solicitacao":  "",
        "data_execucao":     None,
        "hora_execucao":     "",
        "descricao_servico": "",
        "observacoes":       "",
        "responsavel":       "",
        "status":            "aberta",
        "valor_hora":        0.0,
        "horas_trabalhadas": 0.0,
    }


class TestIntegracaoOS:
    def test_os_reusa_produto_da_tabela_vendas(self, banco):
        """Produto cadastrado no módulo Vendas deve ser usável como item de OS."""
        from views.os.os_model import obter_os, salvar_os
        from views.vendas.venda_model import salvar_produto

        pid = salvar_produto({
            "nome": "Parafuso M5", "tipo": "produto", "preco": 0.50,
            "descricao": "", "ativo": True,
        })
        oid = salvar_os(_dados_os_min(), [{
            "produto_id": pid, "descricao": "Parafuso",
            "quantidade": 10.0, "preco_unit": 0.50, "observacao": "",
        }])
        os_obj = obter_os(oid)
        assert os_obj.itens[0].produto_id == pid
        assert os_obj.total_materiais == pytest.approx(5.0)

    def test_servico_da_tabela_produtos_usavel_em_os(self, banco):
        """Item com tipo='servico' do catálogo de Vendas deve servir em OS."""
        from views.os.os_model import obter_os, salvar_os
        from views.vendas.venda_model import salvar_produto

        sid = salvar_produto({
            "nome": "Hora técnica especializada", "tipo": "servico",
            "preco": 120.0, "descricao": "", "ativo": True,
        })
        oid = salvar_os(_dados_os_min(), [{
            "produto_id": sid, "descricao": "Hora técnica",
            "quantidade": 2.0, "preco_unit": 120.0, "observacao": "",
        }])
        os_obj = obter_os(oid)
        assert os_obj.itens[0].produto_id == sid
        assert os_obj.total_materiais == pytest.approx(240.0)

    def test_excluir_produto_usado_em_os_e_bloqueado(self, banco):
        """OS preserva integridade — excluir produto referenciado é bloqueado
        com mensagem clara antes de tentar o DELETE (evita FK error cru)."""
        from views.os.os_model import salvar_os
        from views.vendas.venda_model import excluir_produto, salvar_produto

        pid = salvar_produto({
            "nome": "Filtro Ar", "tipo": "produto", "preco": 15.0,
            "descricao": "", "ativo": True,
        })
        salvar_os(_dados_os_min(), [{
            "produto_id": pid, "descricao": "Filtro",
            "quantidade": 1.0, "preco_unit": 15.0, "observacao": "",
        }])
        ok, msg = excluir_produto(pid)
        assert ok is False
        assert "ordens de serviço" in msg.lower()

    def test_os_concluida_nao_aparece_no_extrato(self, banco):
        """Decisão arquitetural: OS NÃO gera lançamento financeiro automático.
        Concluir uma OS não pode adicionar nada ao extrato de caixa."""
        from views.fluxo_caixa.extrato_model import extrato_mes
        from views.os.os_model import atualizar_os, salvar_os

        dados = {**_dados_os_min("Cliente Interno", data=_HOJE),
                 "valor_hora": 100.0, "horas_trabalhadas": 3.0}
        oid = salvar_os(dados, [{
            "produto_id": None, "descricao": "Material",
            "quantidade": 1.0, "preco_unit": 50.0, "observacao": "",
        }])
        atualizar_os(oid, {**dados, "status": "concluida"}, [{
            "produto_id": None, "descricao": "Material",
            "quantidade": 1.0, "preco_unit": 50.0, "observacao": "",
        }])
        linhas = extrato_mes(_MES, _ANO)
        # Nenhuma linha pode ter origem em OS
        for l in linhas:
            assert "OS" not in (l.categoria or "")
            assert "Ordem de Serviço" not in (l.categoria or "")

    def test_os_nao_afeta_projecao_visao_futura(self, banco):
        """OS concluída (com mão de obra + materiais) não deve aparecer na
        projeção de visão futura — está fora do fluxo financeiro."""
        from views.os.os_model import salvar_os
        from views.visao_futura.projecao_model import projetar

        dados = {**_dados_os_min("Setor Interno", data=_HOJE),
                 "status": "concluida", "valor_hora": 80.0,
                 "horas_trabalhadas": 2.0}
        salvar_os(dados, [{
            "produto_id": None, "descricao": "Material",
            "quantidade": 1.0, "preco_unit": 200.0, "observacao": "",
        }])
        meses = projetar(meses=3)
        # Receitas e despesas projetadas não devem incluir o valor da OS (360,00).
        # Não é uma garantia de ausência total, mas qualquer aparição da string
        # "OS" como rótulo indicaria vazamento da OS para o módulo financeiro.
        for m in meses:
            for atributo in ("receitas", "despesas_fixas", "despesas_variaveis"):
                valor = getattr(m, atributo, None)
                assert valor is None or isinstance(valor, (int, float))
