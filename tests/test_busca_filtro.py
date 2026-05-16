"""
test_busca_filtro.py — Testes das funções de busca/filtro no extrato e contas a pagar.
"""
import pytest
from datetime import datetime, date


def _inserir_plano(nome):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    from database import conectar
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO plano_contas (nome,tipo_custo,categoria,ativa,padrao,criado_em)"
            " VALUES (?,'variavel','Outros',1,0,?)", (nome, agora))
        return cur.lastrowid


def _inserir_conta(plano_id, descricao, valor, venc, status="pendente"):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    from database import conectar
    with conectar() as conn:
        conn.execute(
            "INSERT INTO contas_pagar (plano_conta_id,descricao,valor,"
            "data_vencimento,status,recorrente,criado_em) VALUES (?,?,?,?,?,0,?)",
            (plano_id, descricao, valor, venc, status, agora))


# ─────────────────────────────────────────────────────────────────────────────
# buscar_contas_pagar
# ─────────────────────────────────────────────────────────────────────────────

class TestBuscarContasPagar:
    def test_busca_por_descricao(self, banco):
        plano1 = _inserir_plano("Moradia")
        plano2 = _inserir_plano("Utilidades")
        _inserir_conta(plano1, "Aluguel Apartamento", 1500.0, "2025-06-10")
        _inserir_conta(plano2, "Água e Luz",          200.0,  "2025-06-15")

        from views.contas_pagar.conta_model import buscar_contas_pagar
        resultado = buscar_contas_pagar("Aluguel")
        assert len(resultado) == 1
        assert resultado[0].descricao == "Aluguel Apartamento"

    def test_busca_por_nome_plano(self, banco):
        plano = _inserir_plano("Internet")
        _inserir_conta(plano, "", 100.0, "2025-06-20")

        from views.contas_pagar.conta_model import buscar_contas_pagar
        resultado = buscar_contas_pagar("Internet")
        assert len(resultado) == 1

    def test_busca_case_insensitive(self, banco):
        plano = _inserir_plano("Outros")
        _inserir_conta(plano, "Netflix Premium", 45.0, "2025-06-05")

        from views.contas_pagar.conta_model import buscar_contas_pagar
        assert len(buscar_contas_pagar("netflix")) == 1
        assert len(buscar_contas_pagar("NETFLIX")) == 1
        assert len(buscar_contas_pagar("Net"))      == 1

    def test_busca_sem_resultado(self, banco):
        plano = _inserir_plano("Outros")
        _inserir_conta(plano, "Academia", 80.0, "2025-06-01")

        from views.contas_pagar.conta_model import buscar_contas_pagar
        assert buscar_contas_pagar("XYZZY") == []

    def test_busca_vazia_retorna_tudo(self, banco):
        plano = _inserir_plano("Outros")
        _inserir_conta(plano, "A", 10.0, "2025-06-01")
        _inserir_conta(plano, "B", 20.0, "2025-06-02")
        _inserir_conta(plano, "C", 30.0, "2025-06-03")

        from views.contas_pagar.conta_model import buscar_contas_pagar
        assert len(buscar_contas_pagar("")) == 3

    def test_filtro_por_status(self, banco):
        plano = _inserir_plano("X")
        _inserir_conta(plano, "Paga",    100.0, "2025-05-01", status="pago")
        _inserir_conta(plano, "Aberta",  200.0, "2025-06-01", status="pendente")

        from views.contas_pagar.conta_model import buscar_contas_pagar
        pago     = buscar_contas_pagar("", status="pago")
        pendente = buscar_contas_pagar("", status="pendente")
        assert len(pago)     == 1
        assert len(pendente) == 1
        assert pago[0].descricao     == "Paga"
        assert pendente[0].descricao == "Aberta"

    def test_filtro_por_mes_ano(self, banco):
        plano = _inserir_plano("Y")
        _inserir_conta(plano, "Junho",   50.0, "2025-06-10")
        _inserir_conta(plano, "Julho",   60.0, "2025-07-10")

        from views.contas_pagar.conta_model import buscar_contas_pagar
        junho = buscar_contas_pagar("", mes=6, ano=2025)
        julho = buscar_contas_pagar("", mes=7, ano=2025)
        assert len(junho) == 1 and junho[0].descricao == "Junho"
        assert len(julho) == 1 and julho[0].descricao == "Julho"


# ─────────────────────────────────────────────────────────────────────────────
# filtrar_extrato (filtro em memória sobre LinhaExtrato)
# ─────────────────────────────────────────────────────────────────────────────

class TestFiltrarExtrato:
    def _linhas_exemplo(self):
        from views.fluxo_caixa.extrato_model import LinhaExtrato
        return [
            LinhaExtrato("2025-06-01", "Salário", "Receita", 0.0, 5000.0, 5000.0, "receita", ""),
            LinhaExtrato("2025-06-05", "Aluguel",   "Moradia", 1500.0, 0.0, 3500.0, "despesa", "pago"),
            LinhaExtrato("2025-06-10", "Supermercado", "Alimentação", 300.0, 0.0, 3200.0, "despesa", "pendente"),
            LinhaExtrato("2025-06-15", "Netflix",   "Lazer", 45.0, 0.0, 3155.0, "despesa", "pago"),
        ]

    def test_busca_por_descricao(self):
        from views.fluxo_caixa.extrato_model import filtrar_extrato
        linhas = self._linhas_exemplo()
        resultado = filtrar_extrato(linhas, "Aluguel")
        assert len(resultado) == 1
        assert resultado[0].descricao == "Aluguel"

    def test_busca_case_insensitive(self):
        from views.fluxo_caixa.extrato_model import filtrar_extrato
        linhas = self._linhas_exemplo()
        assert len(filtrar_extrato(linhas, "netflix")) == 1
        assert len(filtrar_extrato(linhas, "SUPER"))   == 1

    def test_busca_por_categoria(self):
        from views.fluxo_caixa.extrato_model import filtrar_extrato
        linhas = self._linhas_exemplo()
        resultado = filtrar_extrato(linhas, "Moradia")
        assert len(resultado) == 1

    def test_busca_vazia_retorna_tudo(self):
        from views.fluxo_caixa.extrato_model import filtrar_extrato
        linhas = self._linhas_exemplo()
        assert len(filtrar_extrato(linhas, "")) == 4

    def test_filtra_apenas_receitas(self):
        from views.fluxo_caixa.extrato_model import filtrar_extrato
        linhas = self._linhas_exemplo()
        resultado = filtrar_extrato(linhas, "", tipo="receita")
        assert all(l.tipo == "receita" for l in resultado)
        assert len(resultado) == 1

    def test_filtra_apenas_despesas(self):
        from views.fluxo_caixa.extrato_model import filtrar_extrato
        linhas = self._linhas_exemplo()
        resultado = filtrar_extrato(linhas, "", tipo="despesa")
        assert all(l.tipo == "despesa" for l in resultado)
        assert len(resultado) == 3

    def test_sem_resultado(self):
        from views.fluxo_caixa.extrato_model import filtrar_extrato
        linhas = self._linhas_exemplo()
        assert filtrar_extrato(linhas, "XYZZY123") == []
