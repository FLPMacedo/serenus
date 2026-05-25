"""
Testes do agenda_model — eventos avulsos (CRUD) + agregador
(compromissos_periodo, compromissos_mes, proximos_dias).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from database import conectar
from views.agenda.agenda_model import (
    CATEGORIAS_EVENTO,
    agrupar_por_dia,
    alternar_concluido_evento,
    compromissos_mes,
    compromissos_periodo,
    excluir_evento,
    listar_eventos_periodo,
    obter_evento,
    proximos_dias,
    salvar_evento,
)


@pytest.fixture
def banco_limpo(banco):
    """
    Banco com as tabelas que o agregador consome ZERADAS — útil pra testes
    que verificam contagem exata. A fixture `banco` padrão popula dados
    de exemplo (Salário CLT, Freela, Aluguel recebido).
    """
    with conectar() as conn:
        conn.execute("DELETE FROM agenda_eventos")
        conn.execute("DELETE FROM receitas_especiais")
        conn.execute("DELETE FROM fontes_receita")
        conn.execute("DELETE FROM contas_pagar")
        try:
            conn.execute("DELETE FROM ordens_servico")
        except Exception:
            pass
    return banco


# ---------------------------------------------------------------------------
# Eventos avulsos — CRUD
# ---------------------------------------------------------------------------

class TestEventoAvulsoCRUD:
    def test_salvar_evento_minimo(self, banco):
        eid = salvar_evento({
            "titulo": "Renovar CNH",
            "data":   "2026-06-15",
        })
        assert isinstance(eid, int) and eid > 0

        ev = obter_evento(eid)
        assert ev is not None
        assert ev.titulo == "Renovar CNH"
        assert ev.data == "2026-06-15"
        assert ev.hora == ""
        assert ev.categoria == "pessoal"
        assert ev.concluido is False
        assert ev.descricao == ""

    def test_salvar_evento_completo(self, banco):
        eid = salvar_evento({
            "titulo":    "Reunião com fornecedor",
            "descricao": "Discutir contrato 2027",
            "data":      "2026-07-10",
            "hora":      "14:30",
            "categoria": "trabalho",
        })
        ev = obter_evento(eid)
        assert ev.titulo == "Reunião com fornecedor"
        assert ev.descricao == "Discutir contrato 2027"
        assert ev.hora == "14:30"
        assert ev.categoria == "trabalho"

    def test_titulo_obrigatorio(self, banco):
        with pytest.raises(ValueError, match="Título"):
            salvar_evento({"titulo": "", "data": "2026-01-01"})
        with pytest.raises(ValueError, match="Título"):
            salvar_evento({"data": "2026-01-01"})

    def test_data_obrigatoria(self, banco):
        with pytest.raises(ValueError, match="Data"):
            salvar_evento({"titulo": "Algo", "data": ""})

    def test_categoria_invalida(self, banco):
        with pytest.raises(ValueError, match="Categoria"):
            salvar_evento({
                "titulo": "X", "data": "2026-01-01",
                "categoria": "inexistente",
            })

    def test_atualizar_evento(self, banco):
        eid = salvar_evento({"titulo": "Original", "data": "2026-01-01"})
        salvar_evento({
            "titulo": "Editado",
            "data":   "2026-02-01",
            "hora":   "10:00",
            "categoria": "saude",
        }, id=eid)
        ev = obter_evento(eid)
        assert ev.titulo == "Editado"
        assert ev.data == "2026-02-01"
        assert ev.hora == "10:00"
        assert ev.categoria == "saude"

    def test_alternar_concluido(self, banco):
        eid = salvar_evento({"titulo": "X", "data": "2026-01-01"})
        assert obter_evento(eid).concluido is False
        alternar_concluido_evento(eid, True)
        assert obter_evento(eid).concluido is True
        alternar_concluido_evento(eid, False)
        assert obter_evento(eid).concluido is False

    def test_excluir(self, banco):
        eid = salvar_evento({"titulo": "X", "data": "2026-01-01"})
        assert obter_evento(eid) is not None
        excluir_evento(eid)
        assert obter_evento(eid) is None

    def test_listar_periodo(self, banco):
        salvar_evento({"titulo": "Fora", "data": "2026-01-01"})
        salvar_evento({"titulo": "Dentro 1", "data": "2026-06-15"})
        salvar_evento({"titulo": "Dentro 2", "data": "2026-06-20"})
        salvar_evento({"titulo": "Fora 2", "data": "2026-12-31"})

        evts = listar_eventos_periodo("2026-06-01", "2026-06-30")
        titulos = [e.titulo for e in evts]
        assert "Dentro 1" in titulos
        assert "Dentro 2" in titulos
        assert "Fora" not in titulos
        assert "Fora 2" not in titulos

    def test_categorias_disponíveis(self, banco):
        # Sanity: garante o tuplo público
        assert set(CATEGORIAS_EVENTO) == {"pessoal", "trabalho", "saude", "outro"}


# ---------------------------------------------------------------------------
# Agregador — junta tabelas existentes + eventos
# ---------------------------------------------------------------------------

class TestAgregador:
    def test_compromissos_vazios(self, banco_limpo):
        # Banco recém criado pelo fixture deve estar VAZIO (sem dados-exemplo)
        # ou ter dados-exemplo previsíveis. Testamos só a forma.
        itens = compromissos_periodo("2099-01-01", "2099-01-31")
        assert isinstance(itens, list)
        # Nada cadastrado em 2099 — esperado vazio
        assert itens == []

    def test_apenas_evento_avulso(self, banco_limpo):
        salvar_evento({
            "titulo": "Único compromisso",
            "data": "2099-06-15",
            "hora": "09:00",
        })
        itens = compromissos_periodo("2099-06-01", "2099-06-30")
        assert len(itens) == 1
        it = itens[0]
        assert it["tipo"] == "evento"
        assert it["data"] == "2099-06-15"
        assert it["hora"] == "09:00"
        assert it["titulo"] == "Único compromisso"
        assert it["valor"] is None
        assert it["concluido"] is False

    def test_agregador_despesa_aparece(self, banco_limpo):
        # Insere uma conta a pagar com vencimento no período
        with conectar() as conn:
            cur = conn.execute("""
                INSERT INTO contas_pagar
                (descricao, valor, data_vencimento, status, criado_em)
                VALUES (?, ?, ?, ?, ?)
            """, ("Aluguel", 1500.0, "2099-06-10", "pendente",
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            cid = cur.lastrowid

        itens = compromissos_periodo("2099-06-01", "2099-06-30",
                                     tipos={"despesa"})
        assert len(itens) == 1
        it = itens[0]
        assert it["tipo"] == "despesa"
        assert it["ref_id"] == cid
        assert it["valor"] == -1500.0   # negativo (saída)
        assert it["data"] == "2099-06-10"

    def test_agregador_receita_especial(self, banco_limpo):
        # mes=5 = Junho (0-indexed)
        with conectar() as conn:
            conn.execute("""
                INSERT INTO receitas_especiais
                (nome, mes, valor, tipo, recorrente_anual)
                VALUES (?, ?, ?, ?, ?)
            """, ("Bônus", 5, 5000.0, "outro", 1))

        # No mês de Junho/2099 deve aparecer
        itens = compromissos_periodo("2099-06-01", "2099-06-30",
                                     tipos={"receita"})
        nomes = [i["titulo"] for i in itens]
        assert "Bônus" in nomes
        # Valor positivo
        bonus = next(i for i in itens if i["titulo"] == "Bônus")
        assert bonus["valor"] == 5000.0

    def test_agregador_filtro_tipos(self, banco_limpo):
        salvar_evento({"titulo": "Evento X", "data": "2099-06-10"})
        with conectar() as conn:
            conn.execute("""
                INSERT INTO contas_pagar
                (descricao, valor, data_vencimento, status, criado_em)
                VALUES (?, ?, ?, ?, ?)
            """, ("Conta", 100.0, "2099-06-10", "pendente",
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        # Só eventos
        itens = compromissos_periodo("2099-06-01", "2099-06-30",
                                     tipos={"evento"})
        assert len(itens) == 1
        assert itens[0]["tipo"] == "evento"

        # Só despesas
        itens = compromissos_periodo("2099-06-01", "2099-06-30",
                                     tipos={"despesa"})
        assert len(itens) == 1
        assert itens[0]["tipo"] == "despesa"

        # Ambos
        itens = compromissos_periodo("2099-06-01", "2099-06-30",
                                     tipos={"despesa", "evento"})
        assert len(itens) == 2

    def test_agregador_ordenado_por_data_e_hora(self, banco_limpo):
        salvar_evento({"titulo": "B", "data": "2099-06-10", "hora": "14:00"})
        salvar_evento({"titulo": "A", "data": "2099-06-10", "hora": "08:00"})
        salvar_evento({"titulo": "C", "data": "2099-06-11"})

        itens = compromissos_periodo("2099-06-01", "2099-06-30",
                                     tipos={"evento"})
        titulos = [i["titulo"] for i in itens]
        assert titulos == ["A", "B", "C"]

    def test_compromissos_mes_atalho(self, banco_limpo):
        salvar_evento({"titulo": "X", "data": "2099-06-15"})
        salvar_evento({"titulo": "Y", "data": "2099-07-01"})

        itens = compromissos_mes(2099, 6)
        assert len(itens) == 1
        assert itens[0]["titulo"] == "X"

    def test_proximos_dias_a_partir_de_base(self, banco_limpo):
        base = date(2099, 1, 1)
        salvar_evento({"titulo": "Hoje", "data": "2099-01-01"})
        salvar_evento({"titulo": "Daqui 5d", "data": "2099-01-06"})
        salvar_evento({"titulo": "Daqui 60d", "data": "2099-03-02"})

        itens = proximos_dias(num_dias=30, base=base)
        titulos = [i["titulo"] for i in itens]
        assert "Hoje" in titulos
        assert "Daqui 5d" in titulos
        assert "Daqui 60d" not in titulos

    def test_fonte_sem_dia_pagamento_usa_padrao(self, banco_limpo):
        """
        Regressão: fonte ativa com `dia_pagamento=NULL` precisa aparecer
        na agenda. Versão anterior filtrava `IS NOT NULL` e a fonte sumia.
        Comportamento esperado: usar dia 5 como padrão e marcar como
        "dia previsto" no subtítulo.
        """
        from datetime import datetime as _dt
        with conectar() as conn:
            conn.execute("""
                INSERT INTO fontes_receita
                (nome, tipo, valor_mensal, ativa, periodicidade, dia_pagamento, criado_em)
                VALUES (?, ?, ?, 1, 'mensal', NULL, ?)
            """, ("Freela X", "freela", 2000.0,
                  _dt.now().strftime("%Y-%m-%d %H:%M:%S")))

        itens = compromissos_periodo("2099-06-01", "2099-06-30",
                                     tipos={"receita"})
        assert len(itens) == 1
        it = itens[0]
        assert it["titulo"] == "Freela X"
        assert it["data"] == "2099-06-05"   # padrão = dia 5
        assert "previsto" in it["subtitulo"].lower()
        assert it["valor"] == 2000.0

    def test_fonte_dia_invalido_usa_ultimo_dia_do_mes(self, banco_limpo):
        """
        Fonte com dia_pagamento=31 cadastrado deve aparecer em Fevereiro
        no dia 28/29 (último dia do mês), não sumir.
        """
        from datetime import datetime as _dt
        with conectar() as conn:
            conn.execute("""
                INSERT INTO fontes_receita
                (nome, tipo, valor_mensal, ativa, periodicidade, dia_pagamento, criado_em)
                VALUES (?, ?, ?, 1, 'mensal', 31, ?)
            """, ("Salário", "clt", 5000.0,
                  _dt.now().strftime("%Y-%m-%d %H:%M:%S")))

        # 2099 não-bissexto — fevereiro tem 28 dias
        itens = compromissos_periodo("2099-02-01", "2099-02-28",
                                     tipos={"receita"})
        assert len(itens) == 1
        assert itens[0]["data"] == "2099-02-28"

    def test_os_aparece_com_numero_formatado(self, banco_limpo):
        """
        Regressão: o campo `numero` de ordens_servico é TEXT já formatado
        ("OS-0003"), não int. Versão anterior fazia int(d['numero']) e
        explodia com 'invalid literal for int() with base 10: OS-0003'.
        """
        from datetime import datetime as _dt
        with conectar() as conn:
            conn.execute("""
                INSERT INTO ordens_servico
                (numero, solicitante_nome, data_solicitacao,
                 data_execucao, status, criado_em)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("OS-0003", "João da Silva", "2099-06-01",
                  "2099-06-10", "aberta",
                  _dt.now().strftime("%Y-%m-%d %H:%M:%S")))

        itens = compromissos_periodo("2099-06-01", "2099-06-30",
                                     tipos={"os"})
        assert len(itens) == 1
        assert itens[0]["tipo"] == "os"
        assert itens[0]["titulo"] == "OS-0003"
        assert itens[0]["data"] == "2099-06-10"
        assert itens[0]["concluido"] is False

    def test_agrupar_por_dia(self, banco):
        items = [
            {"data": "2099-06-10", "titulo": "A"},
            {"data": "2099-06-10", "titulo": "B"},
            {"data": "2099-06-11", "titulo": "C"},
        ]
        agrupado = agrupar_por_dia(items)
        assert set(agrupado.keys()) == {"2099-06-10", "2099-06-11"}
        assert len(agrupado["2099-06-10"]) == 2
        assert agrupado["2099-06-11"][0]["titulo"] == "C"
