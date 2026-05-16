"""
test_vendas_model.py — Testes do módulo de Vendas do Serenus.

Cobertura por etapa:
  Etapa 1 — Tabelas: verifica criação das 4 tabelas no banco
  Etapa 2 — Produtos: CRUD completo
  Etapa 3 — Venda à vista: salvar, listar, cancelar
  Etapa 4 — Venda a prazo: contas a receber, quitação
  Etapa 5 — Integração extrato de caixa
  Etapa 6 — Alertas: recebíveis vencidos/vencendo
"""

import sys
from pathlib import Path
from datetime import date, timedelta

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers de inserção direta (padrão _inserir_*)
# ---------------------------------------------------------------------------

def _produto(nome: str = "Produto Teste", tipo: str = "produto",
             preco: float = 100.0) -> dict:
    """Builder de dados para produto."""
    return {"nome": nome, "tipo": tipo, "preco": preco,
            "descricao": "", "ativo": True}


def _dados_venda(tipo_pagamento: str = "avista",
                 data: str | None = None) -> dict:
    """Builder de dados para cabeçalho de venda."""
    return {
        "descricao": "Venda teste",
        "data_venda": data or date.today().isoformat(),
        "desconto": 0.0,
        "tipo_pagamento": tipo_pagamento,
        "observacao": "",
    }


def _item(descricao: str = "Item Teste", quantidade: float = 1.0,
          preco_unit: float = 100.0, produto_id: int | None = None) -> dict:
    return {
        "produto_id": produto_id,
        "descricao": descricao,
        "quantidade": quantidade,
        "preco_unit": preco_unit,
    }


def _inserir_conta_receber(venda_id: int | None, descricao: str, valor: float,
                           data_vencimento: str, status: str = "pendente",
                           numero_parcela: int = 1,
                           total_parcelas: int = 1) -> int:
    """Insere uma conta a receber diretamente no banco (helper de teste)."""
    from datetime import datetime
    from database import conectar
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute(
            """INSERT INTO contas_a_receber
               (venda_id, descricao, valor, data_vencimento, status,
                numero_parcela, total_parcelas, observacao, criado_em)
               VALUES (?,?,?,?,?,?,?,'',?)""",
            (venda_id, descricao, valor, data_vencimento, status,
             numero_parcela, total_parcelas, agora),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Etapa 1 — Database: verifica criação das 4 tabelas
# ---------------------------------------------------------------------------

class TestTabelasVendas:
    def test_tabela_produtos_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "produtos" in tabelas

    def test_tabela_vendas_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "vendas" in tabelas

    def test_tabela_itens_venda_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "itens_venda" in tabelas

    def test_tabela_contas_a_receber_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "contas_a_receber" in tabelas

    def test_colunas_produtos(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute("PRAGMA table_info(produtos)").fetchall()}
        assert {"id", "nome", "tipo", "preco", "descricao", "ativo", "criado_em"} <= colunas

    def test_colunas_vendas(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute("PRAGMA table_info(vendas)").fetchall()}
        assert {"id", "descricao", "data_venda", "valor_total", "desconto",
                "valor_liquido", "tipo_pagamento", "status", "criado_em"} <= colunas

    def test_colunas_itens_venda(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute("PRAGMA table_info(itens_venda)").fetchall()}
        assert {"id", "venda_id", "produto_id", "descricao",
                "quantidade", "preco_unit", "subtotal", "criado_em"} <= colunas

    def test_colunas_contas_a_receber(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute(
                "PRAGMA table_info(contas_a_receber)"
            ).fetchall()}
        assert {"id", "venda_id", "descricao", "valor", "data_vencimento",
                "data_recebimento", "status", "numero_parcela",
                "total_parcelas", "criado_em"} <= colunas


# ---------------------------------------------------------------------------
# Etapa 2 — Produtos: CRUD
# ---------------------------------------------------------------------------

class TestCRUDProdutos:
    def test_criar_produto_retorna_id(self, banco):
        from views.vendas.venda_model import salvar_produto
        pid = salvar_produto(_produto())
        assert isinstance(pid, int) and pid > 0

    def test_listar_produtos_vazio(self, banco):
        from views.vendas.venda_model import listar_produtos
        assert listar_produtos() == []

    def test_listar_produtos_retorna_criado(self, banco):
        from views.vendas.venda_model import salvar_produto, listar_produtos
        salvar_produto(_produto("Caneca", "produto", 25.0))
        prods = listar_produtos()
        assert len(prods) == 1
        assert prods[0].nome == "Caneca"
        assert prods[0].preco == pytest.approx(25.0)

    def test_listar_apenas_ativos(self, banco):
        from views.vendas.venda_model import salvar_produto, listar_produtos
        salvar_produto(_produto("Ativo"))
        salvar_produto({**_produto("Inativo"), "ativo": False})
        assert len(listar_produtos(apenas_ativos=True)) == 1
        assert len(listar_produtos(apenas_ativos=False)) == 2

    def test_editar_produto(self, banco):
        from views.vendas.venda_model import salvar_produto, listar_produtos
        pid = salvar_produto(_produto("Original", preco=50.0))
        salvar_produto({"nome": "Atualizado", "tipo": "servico",
                        "preco": 80.0, "descricao": "", "ativo": True}, id=pid)
        prods = listar_produtos()
        assert prods[0].nome == "Atualizado"
        assert prods[0].preco == pytest.approx(80.0)
        assert prods[0].tipo == "servico"

    def test_excluir_produto_sem_vendas(self, banco):
        from views.vendas.venda_model import salvar_produto, excluir_produto, listar_produtos
        pid = salvar_produto(_produto())
        ok, _ = excluir_produto(pid)
        assert ok is True
        assert listar_produtos() == []

    def test_excluir_produto_com_vendas_bloqueado(self, banco):
        from views.vendas.venda_model import salvar_produto, excluir_produto, salvar_venda
        pid = salvar_produto(_produto("Prod Usado", preco=100.0))
        salvar_venda(_dados_venda(), [_item(produto_id=pid)])
        ok, msg = excluir_produto(pid)
        assert ok is False
        assert msg != ""

    def test_tipo_produto_e_servico_aceitos(self, banco):
        from views.vendas.venda_model import salvar_produto, listar_produtos
        salvar_produto(_produto("P", "produto"))
        salvar_produto(_produto("S", "servico"))
        tipos = {p.tipo for p in listar_produtos()}
        assert tipos == {"produto", "servico"}


# ---------------------------------------------------------------------------
# Etapa 3 — Venda à vista
# ---------------------------------------------------------------------------

class TestVendaAvista:
    def test_salvar_venda_avista_cria_registro(self, banco):
        from views.vendas.venda_model import salvar_venda, listar_vendas
        salvar_venda(_dados_venda(), [_item()])
        vendas = listar_vendas(date.today().month, date.today().year)
        assert len(vendas) == 1

    def test_salvar_venda_avista_retorna_id(self, banco):
        from views.vendas.venda_model import salvar_venda
        vid = salvar_venda(_dados_venda(), [_item()])
        assert isinstance(vid, int) and vid > 0

    def test_salvar_venda_avista_status_paga(self, banco):
        from views.vendas.venda_model import salvar_venda, listar_vendas
        salvar_venda(_dados_venda("avista"), [_item()])
        v = listar_vendas(date.today().month, date.today().year)[0]
        assert v.status == "paga"

    def test_salvar_venda_avista_nao_cria_contas_receber(self, banco):
        from views.vendas.venda_model import salvar_venda
        from database import conectar
        salvar_venda(_dados_venda("avista"), [_item()])
        with conectar() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM contas_a_receber"
            ).fetchone()[0]
        assert total == 0

    def test_salvar_venda_avista_cria_itens(self, banco):
        from views.vendas.venda_model import salvar_venda, obter_venda
        vid = salvar_venda(_dados_venda(), [
            _item("Item A", 2.0, 50.0),
            _item("Item B", 1.0, 30.0),
        ])
        v = obter_venda(vid)
        assert len(v.itens) == 2

    def test_valor_liquido_com_desconto(self, banco):
        from views.vendas.venda_model import salvar_venda, obter_venda
        dados = {**_dados_venda(), "desconto": 20.0}
        vid = salvar_venda(dados, [_item("X", 1.0, 100.0)])
        v = obter_venda(vid)
        assert v.valor_total == pytest.approx(100.0)
        assert v.desconto == pytest.approx(20.0)
        assert v.valor_liquido == pytest.approx(80.0)

    def test_valor_total_soma_subtotais(self, banco):
        from views.vendas.venda_model import salvar_venda, obter_venda
        vid = salvar_venda(_dados_venda(), [
            _item("A", 2.0, 50.0),
            _item("B", 3.0, 10.0),
        ])
        v = obter_venda(vid)
        assert v.valor_total == pytest.approx(130.0)

    def test_listar_vendas_filtra_por_mes(self, banco):
        from views.vendas.venda_model import salvar_venda, listar_vendas
        salvar_venda({**_dados_venda(), "data_venda": "2025-06-15"}, [_item()])
        salvar_venda({**_dados_venda(), "data_venda": "2025-07-01"}, [_item()])
        assert len(listar_vendas(6, 2025)) == 1
        assert len(listar_vendas(7, 2025)) == 1

    def test_cancelar_venda(self, banco):
        from views.vendas.venda_model import salvar_venda, cancelar_venda, obter_venda
        vid = salvar_venda(_dados_venda(), [_item()])
        cancelar_venda(vid)
        assert obter_venda(vid).status == "cancelada"

    def test_obter_venda_inexistente_retorna_none(self, banco):
        from views.vendas.venda_model import obter_venda
        assert obter_venda(9999) is None


# ---------------------------------------------------------------------------
# Etapa 4 — Venda a prazo + contas a receber
# ---------------------------------------------------------------------------

class TestVendaAPrazo:
    def test_venda_aprazo_status_pendente(self, banco):
        from views.vendas.venda_model import salvar_venda, obter_venda
        vid = salvar_venda(
            {**_dados_venda("aprazo"), "parcelas": 3,
             "data_primeira_parcela": "2025-08-01"},
            [_item("P", 1.0, 300.0)],
        )
        assert obter_venda(vid).status == "pendente"

    def test_venda_aprazo_cria_contas_receber(self, banco):
        from views.vendas.venda_model import salvar_venda, listar_contas_receber
        salvar_venda(
            {**_dados_venda("aprazo"), "parcelas": 3,
             "data_primeira_parcela": "2025-08-01"},
            [_item("P", 1.0, 300.0)],
        )
        receber = listar_contas_receber()
        assert len(receber) == 3

    def test_venda_aprazo_parcelas_corretas(self, banco):
        from views.vendas.venda_model import salvar_venda, listar_contas_receber
        salvar_venda(
            {**_dados_venda("aprazo"), "parcelas": 2,
             "data_primeira_parcela": "2025-09-01"},
            [_item("P", 1.0, 200.0)],
        )
        receber = listar_contas_receber()
        valores = [r.valor for r in receber]
        assert all(v == pytest.approx(100.0) for v in valores)
        nums = sorted(r.numero_parcela for r in receber)
        assert nums == [1, 2]

    def test_venda_aprazo_nao_entra_no_caixa_imediatamente(self, banco):
        from views.vendas.venda_model import salvar_venda
        mes = date.today().month
        ano = date.today().year
        salvar_venda(
            {**_dados_venda("aprazo"), "parcelas": 2,
             "data_primeira_parcela": date.today().isoformat()},
            [_item("P", 1.0, 200.0)],
        )
        from views.fluxo_caixa.extrato_model import extrato_mes
        linhas = extrato_mes(mes, ano)
        creditos_vendas = [l for l in linhas if l.categoria == "Vendas"]
        assert creditos_vendas == []

    def test_venda_aprazo_parcelas_vinculadas_venda(self, banco):
        from views.vendas.venda_model import salvar_venda, listar_contas_receber
        vid = salvar_venda(
            {**_dados_venda("aprazo"), "parcelas": 2,
             "data_primeira_parcela": "2025-10-01"},
            [_item("P", 1.0, 200.0)],
        )
        receber = listar_contas_receber()
        assert all(r.venda_id == vid for r in receber)


class TestQuitacaoRecebivel:
    def test_marcar_recebido_atualiza_status(self, banco):
        from views.vendas.venda_model import marcar_recebido, listar_contas_receber
        rid = _inserir_conta_receber(None, "Parcela 1", 100.0, "2025-08-01")
        marcar_recebido(rid, "2025-08-05")
        rec = listar_contas_receber()
        assert rec[0].status == "recebido"
        assert rec[0].data_recebimento == "2025-08-05"

    def test_marcar_recebido_ultima_parcela_fecha_venda(self, banco):
        from views.vendas.venda_model import (
            salvar_venda, marcar_recebido, obter_venda, listar_contas_receber
        )
        vid = salvar_venda(
            {**_dados_venda("aprazo"), "parcelas": 2,
             "data_primeira_parcela": "2025-08-01"},
            [_item("P", 1.0, 200.0)],
        )
        receber = listar_contas_receber()
        for r in receber:
            marcar_recebido(r.id, "2025-08-10")
        assert obter_venda(vid).status == "paga"

    def test_marcar_recebido_parcial_status_parcial(self, banco):
        from views.vendas.venda_model import (
            salvar_venda, marcar_recebido, obter_venda, listar_contas_receber
        )
        vid = salvar_venda(
            {**_dados_venda("aprazo"), "parcelas": 3,
             "data_primeira_parcela": "2025-08-01"},
            [_item("P", 1.0, 300.0)],
        )
        receber = listar_contas_receber()
        marcar_recebido(receber[0].id, "2025-08-10")
        assert obter_venda(vid).status == "parcial"

    def test_quitacao_mantem_vinculo_venda(self, banco):
        from views.vendas.venda_model import (
            salvar_venda, marcar_recebido, listar_contas_receber
        )
        vid = salvar_venda(
            {**_dados_venda("aprazo"), "parcelas": 1,
             "data_primeira_parcela": "2025-08-01"},
            [_item("P", 1.0, 100.0)],
        )
        receber = listar_contas_receber()
        marcar_recebido(receber[0].id, "2025-08-05")
        receber_pos = listar_contas_receber()
        assert receber_pos[0].venda_id == vid

    def test_listar_contas_receber_filtra_status(self, banco):
        from views.vendas.venda_model import marcar_recebido, listar_contas_receber
        rid1 = _inserir_conta_receber(None, "P1", 50.0, "2025-08-01")
        _inserir_conta_receber(None, "P2", 50.0, "2025-08-01")
        marcar_recebido(rid1, "2025-08-02")
        assert len(listar_contas_receber(status="recebido")) == 1
        assert len(listar_contas_receber(status="pendente")) == 1
        assert len(listar_contas_receber()) == 2


# ---------------------------------------------------------------------------
# Etapa 5 — Integração com extrato de caixa
# ---------------------------------------------------------------------------

class TestIntegracaoVendasExtrato:
    def test_venda_avista_aparece_no_extrato(self, banco):
        from views.vendas.venda_model import salvar_venda
        from views.fluxo_caixa.extrato_model import extrato_mes
        salvar_venda(
            {**_dados_venda("avista"), "data_venda": "2025-06-10"},
            [_item("Produto", 1.0, 150.0)],
        )
        linhas = extrato_mes(6, 2025)
        creditos = [l for l in linhas if l.categoria == "Vendas" and l.credito > 0]
        assert len(creditos) == 1
        assert creditos[0].credito == pytest.approx(150.0)

    def test_venda_aprazo_nao_aparece_no_extrato_antes_de_receber(self, banco):
        from views.vendas.venda_model import salvar_venda
        from views.fluxo_caixa.extrato_model import extrato_mes
        salvar_venda(
            {**_dados_venda("aprazo"), "data_venda": "2025-06-10",
             "parcelas": 2, "data_primeira_parcela": "2025-06-15"},
            [_item("P", 1.0, 200.0)],
        )
        linhas = extrato_mes(6, 2025)
        creditos_vendas = [l for l in linhas if l.categoria == "Vendas"]
        assert creditos_vendas == []

    def test_venda_aprazo_aparece_no_extrato_apos_receber(self, banco):
        from views.vendas.venda_model import (
            salvar_venda, listar_contas_receber, marcar_recebido
        )
        from views.fluxo_caixa.extrato_model import extrato_mes
        salvar_venda(
            {**_dados_venda("aprazo"), "data_venda": "2025-06-10",
             "parcelas": 1, "data_primeira_parcela": "2025-06-20"},
            [_item("P", 1.0, 200.0)],
        )
        receber = listar_contas_receber()
        marcar_recebido(receber[0].id, "2025-06-20")
        linhas = extrato_mes(6, 2025)
        creditos = [l for l in linhas if l.categoria == "Vendas" and l.credito > 0]
        assert len(creditos) == 1
        assert creditos[0].credito == pytest.approx(200.0)

    def test_extrato_nao_duplica_receita_avista(self, banco):
        from views.vendas.venda_model import salvar_venda
        from views.fluxo_caixa.extrato_model import extrato_mes
        salvar_venda(
            {**_dados_venda("avista"), "data_venda": "2025-06-10"},
            [_item("P", 1.0, 100.0)],
        )
        linhas = extrato_mes(6, 2025)
        creditos_vendas = [l for l in linhas if l.categoria == "Vendas"]
        assert len(creditos_vendas) == 1


# ---------------------------------------------------------------------------
# Etapa 6 — Alertas: recebíveis vencidos/vencendo
# ---------------------------------------------------------------------------

class TestAlertasReceber:
    def test_recebivel_vencido_gera_alerta_alta(self, banco):
        from views.alertas.alertas_model import alertas_pendentes
        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_conta_receber(None, "Fatura vencida", 200.0, ontem)
        alertas = alertas_pendentes()
        tipos = [a.tipo for a in alertas]
        assert "recebivel_vencido" in tipos
        urgencias = {a.urgencia for a in alertas if a.tipo == "recebivel_vencido"}
        assert "alta" in urgencias

    def test_recebivel_vencendo_gera_alerta_media(self, banco):
        from views.alertas.alertas_model import alertas_pendentes
        em_3_dias = (date.today() + timedelta(days=3)).isoformat()
        _inserir_conta_receber(None, "Parcela próxima", 100.0, em_3_dias)
        alertas = alertas_pendentes()
        tipos = [a.tipo for a in alertas]
        assert "recebivel_vencendo" in tipos
        urgencias = {a.urgencia for a in alertas if a.tipo == "recebivel_vencendo"}
        assert "media" in urgencias

    def test_recebivel_recebido_nao_gera_alerta(self, banco):
        from views.vendas.venda_model import marcar_recebido
        from views.alertas.alertas_model import alertas_pendentes
        ontem = (date.today() - timedelta(days=1)).isoformat()
        rid = _inserir_conta_receber(None, "Já recebido", 100.0, ontem)
        marcar_recebido(rid, date.today().isoformat())
        alertas = alertas_pendentes()
        tipos = [a.tipo for a in alertas]
        assert "recebivel_vencido" not in tipos

    def test_recebivel_longe_nao_gera_alerta(self, banco):
        from views.alertas.alertas_model import alertas_pendentes
        em_30_dias = (date.today() + timedelta(days=30)).isoformat()
        _inserir_conta_receber(None, "Parcela futura", 100.0, em_30_dias)
        alertas = alertas_pendentes()
        tipos_receber = [a.tipo for a in alertas
                         if a.tipo in ("recebivel_vencido", "recebivel_vencendo")]
        assert tipos_receber == []
