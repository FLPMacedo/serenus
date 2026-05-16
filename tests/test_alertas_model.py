"""
test_alertas_model.py — Testes do módulo de alertas/notificações.
Cobre: contas vencidas, contas a vencer, parcelas de cartão, vencimentos de RF.
"""
import pytest
from datetime import date, timedelta
from database import conectar


# ---------------------------------------------------------------------------
# Helpers de inserção direta
# ---------------------------------------------------------------------------

def _inserir_conta_pagar(banco, plano_id, descricao, valor, vencimento, status="pendente"):
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        conn.execute(
            "INSERT INTO contas_pagar (plano_conta_id, descricao, valor, "
            "data_vencimento, status, recorrente, criado_em) VALUES (?,?,?,?,?,0,?)",
            (plano_id, descricao, valor, vencimento, status, agora),
        )


def _inserir_plano(nome="Despesa Teste"):
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)"
            " VALUES (?,'variavel','Outros',1,0,?)",
            (nome, agora),
        )
        return cur.lastrowid


def _inserir_cartao():
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO cartoes (nome, banco, bandeira, limite, limite_disponivel,"
            " ativo, criado_em) VALUES ('C Teste','nubank','visa',2000,2000,1,?)",
            (agora,),
        )
        return cur.lastrowid


def _inserir_parcela(cartao_id, mes_ref, status="pendente"):
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO compras_cartao (cartao_id, descricao, valor_total,"
            " valor_parcela, total_parcelas, parcelas_pagas, mes_inicio,"
            " categoria, estabelecimento, criado_em)"
            " VALUES (?,?,100,100,1,0,?,?,?,?)",
            (cartao_id, "Compra Teste", mes_ref, "", "", agora),
        )
        compra_id = cur.lastrowid
        conn.execute(
            "INSERT INTO parcelas_cartao (compra_id, cartao_id, numero_parcela,"
            " mes_referencia, valor, status) VALUES (?,?,1,?,100,?)",
            (compra_id, cartao_id, mes_ref, status),
        )


def _inserir_ativo_rf(conta_inv_id, vencimento):
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO ativos (codigo, nome, tipo, conta_investimento_id,"
            " indexador, taxa_contratada, vencimento, ativo, criado_em)"
            " VALUES ('CDB-T','CDB Teste','cdb',?,?,?,?,1,?)",
            (conta_inv_id, "cdi", 120.0, vencimento, agora),
        )
        return cur.lastrowid


def _inserir_conta_investimento():
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO contas_investimento (nome, instituicao, tipo, ativa, criado_em)"
            " VALUES ('Corretora','Banco','corretora',1,?)",
            (agora,),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Etapa 1 — Contas a pagar vencidas
# ---------------------------------------------------------------------------

class TestAlertasContasPagar:
    def test_conta_vencida_gera_alerta(self, banco):
        plano = _inserir_plano()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_conta_pagar(banco, plano, "Conta vencida", 150.0, ontem)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        tipos = [a.tipo for a in alertas]
        assert "conta_vencida" in tipos

    def test_conta_hoje_gera_alerta(self, banco):
        plano = _inserir_plano()
        hoje = date.today().isoformat()
        _inserir_conta_pagar(banco, plano, "Vence hoje", 100.0, hoje)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert any(a.tipo in ("conta_vencida", "conta_proxima") for a in alertas)

    def test_conta_em_5_dias_gera_alerta(self, banco):
        plano = _inserir_plano()
        em5 = (date.today() + timedelta(days=5)).isoformat()
        _inserir_conta_pagar(banco, plano, "Próxima", 200.0, em5)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert any(a.tipo == "conta_proxima" for a in alertas)

    def test_conta_em_8_dias_nao_gera_alerta(self, banco):
        plano = _inserir_plano()
        em8 = (date.today() + timedelta(days=8)).isoformat()
        _inserir_conta_pagar(banco, plano, "Longe", 200.0, em8)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert not any(a.tipo in ("conta_vencida", "conta_proxima") for a in alertas)

    def test_conta_paga_nao_gera_alerta(self, banco):
        plano = _inserir_plano()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_conta_pagar(banco, plano, "Já paga", 100.0, ontem, status="pago")

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert not any(a.tipo == "conta_vencida" for a in alertas)

    def test_urgencia_vencida_e_alta(self, banco):
        plano = _inserir_plano()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_conta_pagar(banco, plano, "Urgente", 100.0, ontem)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = [a for a in alertas_pendentes() if a.tipo == "conta_vencida"]
        assert all(a.urgencia == "alta" for a in alertas)

    def test_urgencia_proxima_e_media(self, banco):
        plano = _inserir_plano()
        em3 = (date.today() + timedelta(days=3)).isoformat()
        _inserir_conta_pagar(banco, plano, "Em breve", 100.0, em3)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = [a for a in alertas_pendentes() if a.tipo == "conta_proxima"]
        assert all(a.urgencia == "media" for a in alertas)


# ---------------------------------------------------------------------------
# Etapa 2 — Parcelas de cartão no mês corrente
# ---------------------------------------------------------------------------

class TestAlertasCartao:
    def test_parcela_mes_atual_gera_alerta(self, banco):
        cartao = _inserir_cartao()
        mes_atual = date.today().strftime("%Y-%m")
        _inserir_parcela(cartao, mes_atual)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert any(a.tipo == "fatura_cartao" for a in alertas)

    def test_parcela_mes_passado_nao_gera_alerta(self, banco):
        cartao = _inserir_cartao()
        d = date.today()
        mes_ant = (d.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        _inserir_parcela(cartao, mes_ant)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert not any(a.tipo == "fatura_cartao" for a in alertas)

    def test_parcela_paga_nao_gera_alerta(self, banco):
        cartao = _inserir_cartao()
        mes_atual = date.today().strftime("%Y-%m")
        _inserir_parcela(cartao, mes_atual, status="pago")

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert not any(a.tipo == "fatura_cartao" for a in alertas)


# ---------------------------------------------------------------------------
# Etapa 3 — Vencimentos de renda fixa
# ---------------------------------------------------------------------------

class TestAlertasRendaFixa:
    def test_rf_vencendo_em_20_dias_gera_alerta(self, banco):
        ci = _inserir_conta_investimento()
        em20 = (date.today() + timedelta(days=20)).isoformat()
        _inserir_ativo_rf(ci, em20)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert any(a.tipo == "vencimento_rf" for a in alertas)

    def test_rf_vencendo_em_40_dias_nao_gera_alerta(self, banco):
        ci = _inserir_conta_investimento()
        em40 = (date.today() + timedelta(days=40)).isoformat()
        _inserir_ativo_rf(ci, em40)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert not any(a.tipo == "vencimento_rf" for a in alertas)

    def test_rf_ja_vencido_gera_alerta(self, banco):
        ci = _inserir_conta_investimento()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_ativo_rf(ci, ontem)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert any(a.tipo == "vencimento_rf" for a in alertas)

    def test_rf_sem_vencimento_nao_gera_alerta(self, banco):
        ci = _inserir_conta_investimento()
        # ativo sem vencimento (None)
        from datetime import datetime
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            conn.execute(
                "INSERT INTO ativos (codigo, nome, tipo, conta_investimento_id,"
                " ativo, criado_em) VALUES ('ACAO-T','Ação Teste','acao',?,1,?)",
                (ci, agora),
            )

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert not any(a.tipo == "vencimento_rf" for a in alertas)


# ---------------------------------------------------------------------------
# Etapa 4 — Estado vazio e interface pública
# ---------------------------------------------------------------------------

class TestAlertasGeral:
    def test_sem_dados_retorna_lista_vazia(self, banco):
        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert alertas == []

    def test_retorna_lista_de_alerta(self, banco):
        plano = _inserir_plano()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_conta_pagar(banco, plano, "Teste", 100.0, ontem)

        from views.alertas.alertas_model import alertas_pendentes, Alerta
        alertas = alertas_pendentes()
        assert all(isinstance(a, Alerta) for a in alertas)

    def test_alerta_tem_campos_obrigatorios(self, banco):
        plano = _inserir_plano()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        _inserir_conta_pagar(banco, plano, "X", 50.0, ontem)

        from views.alertas.alertas_model import alertas_pendentes
        a = alertas_pendentes()[0]
        assert a.tipo
        assert a.descricao
        assert a.urgencia in ("alta", "media", "baixa")

    def test_ordenacao_alta_antes_de_media(self, banco):
        plano = _inserir_plano()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        em3   = (date.today() + timedelta(days=3)).isoformat()
        _inserir_conta_pagar(banco, plano, "Vencida", 100.0, ontem)
        _inserir_conta_pagar(banco, plano, "Em breve", 100.0, em3)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        urgencias = [a.urgencia for a in alertas]
        # alta deve vir antes de media
        idx_alta  = next(i for i, u in enumerate(urgencias) if u == "alta")
        idx_media = next(i for i, u in enumerate(urgencias) if u == "media")
        assert idx_alta < idx_media

    def test_contagem_total(self, banco):
        plano   = _inserir_plano()
        cartao  = _inserir_cartao()
        ci      = _inserir_conta_investimento()
        ontem   = (date.today() - timedelta(days=1)).isoformat()
        mes_at  = date.today().strftime("%Y-%m")
        em10    = (date.today() + timedelta(days=10)).isoformat()

        _inserir_conta_pagar(banco, plano, "Vencida", 100.0, ontem)
        _inserir_parcela(cartao, mes_at)
        _inserir_ativo_rf(ci, em10)

        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        tipos = {a.tipo for a in alertas}
        assert "conta_vencida"  in tipos
        assert "fatura_cartao"  in tipos
        assert "vencimento_rf"  in tipos
