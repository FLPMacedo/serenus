"""
test_os_model.py — Testes do módulo de Ordem de Serviço (OS) do Serenus.

Cobertura por etapa:
  Etapa 1 — Tabelas: criação das 3 tabelas (ordens_servico, itens_os, os_historico)
  Etapa 2 — Numeração: geração sequencial OS-NNNN
  Etapa 3 — CRUD de OS (criar, listar, obter, atualizar, cancelar)
  Etapa 4 — Itens de OS (produtos/serviços, reuso de tabela produtos)
  Etapa 5 — Cálculos (total_materiais, valor_mao_obra, valor_total)
  Etapa 6 — Histórico de alterações
  Etapa 7 — Filtros e busca
"""

import sys
from pathlib import Path
from datetime import date

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers de inserção / builders
# ---------------------------------------------------------------------------

def _dados_os(solicitante_nome: str = "João Silva",
              data: str | None = None) -> dict:
    """Builder de dados para cabeçalho de OS."""
    return {
        "solicitante_nome":  solicitante_nome,
        "solicitante_setor": "TI",
        "solicitante_ramal": "1234",
        "data_solicitacao":  data or date.today().isoformat(),
        "hora_solicitacao":  "09:00",
        "data_execucao":     None,
        "hora_execucao":     "",
        "descricao_servico": "Reparo geral",
        "observacoes":       "",
        "responsavel":       "",
        "status":            "aberta",
        "valor_hora":        0.0,
        "horas_trabalhadas": 0.0,
    }


def _item(descricao: str = "Item Teste",
          quantidade: float = 1.0,
          preco_unit: float = 100.0,
          produto_id: int | None = None,
          observacao: str = "") -> dict:
    return {
        "produto_id": produto_id,
        "descricao":  descricao,
        "quantidade": quantidade,
        "preco_unit": preco_unit,
        "observacao": observacao,
    }


# ---------------------------------------------------------------------------
# Etapa 1 — Database: verifica criação das 3 tabelas
# ---------------------------------------------------------------------------

class TestTabelasOS:
    def test_tabela_ordens_servico_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "ordens_servico" in tabelas

    def test_tabela_itens_os_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "itens_os" in tabelas

    def test_tabela_os_historico_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "os_historico" in tabelas

    def test_colunas_ordens_servico(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute(
                "PRAGMA table_info(ordens_servico)"
            ).fetchall()}
        esperadas = {
            "id", "numero",
            "solicitante_nome", "solicitante_setor", "solicitante_ramal",
            "data_solicitacao", "hora_solicitacao",
            "data_execucao",    "hora_execucao",
            "descricao_servico", "observacoes",
            "responsavel", "status",
            "valor_hora", "horas_trabalhadas",
            "criado_em",
        }
        assert esperadas <= colunas

    def test_colunas_itens_os(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute(
                "PRAGMA table_info(itens_os)"
            ).fetchall()}
        assert {"id", "os_id", "produto_id", "descricao",
                "quantidade", "preco_unit", "subtotal",
                "observacao", "criado_em"} <= colunas

    def test_colunas_os_historico(self, banco):
        from database import conectar
        with conectar() as conn:
            colunas = {r[1] for r in conn.execute(
                "PRAGMA table_info(os_historico)"
            ).fetchall()}
        assert {"id", "os_id", "campo",
                "valor_anterior", "valor_novo", "alterado_em"} <= colunas

    def test_numero_os_unique(self, banco):
        """numero deve ter constraint UNIQUE para evitar duplicatas."""
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            conn.execute(
                "INSERT INTO ordens_servico (numero, data_solicitacao, criado_em)"
                " VALUES (?,?,?)",
                ("OS-0001", "2026-05-18", agora),
            )
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO ordens_servico (numero, data_solicitacao, criado_em)"
                    " VALUES (?,?,?)",
                    ("OS-0001", "2026-05-18", agora),
                )

    def test_status_check_constraint(self, banco):
        """status só aceita valores válidos."""
        from datetime import datetime
        import sqlite3
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO ordens_servico"
                    " (numero, data_solicitacao, status, criado_em)"
                    " VALUES (?,?,?,?)",
                    ("OS-9999", "2026-05-18", "status_invalido", agora),
                )


# ---------------------------------------------------------------------------
# Etapa 2 — Numeração sequencial
# ---------------------------------------------------------------------------

class TestNumeracao:
    def test_proximo_numero_inicia_em_0001(self, banco):
        from views.os.os_model import proximo_numero_os
        assert proximo_numero_os() == "OS-0001"

    def test_proximo_numero_incrementa(self, banco):
        from views.os.os_model import salvar_os, proximo_numero_os
        salvar_os(_dados_os(), [])
        assert proximo_numero_os() == "OS-0002"

    def test_proximo_numero_formato_zero_padded(self, banco):
        from views.os.os_model import salvar_os, proximo_numero_os
        for _ in range(9):
            salvar_os(_dados_os(), [])
        assert proximo_numero_os() == "OS-0010"

    def test_proximo_numero_apos_remocao_segue_max(self, banco):
        """Mesmo se OS-0002 for removida, próximo segue a partir de MAX+1."""
        from views.os.os_model import salvar_os, proximo_numero_os
        from database import conectar
        salvar_os(_dados_os(), [])
        id2 = salvar_os(_dados_os(), [])
        salvar_os(_dados_os(), [])
        # Remove em cascata manual (FKs sem ON DELETE CASCADE, padrão do projeto)
        with conectar() as conn:
            conn.execute("DELETE FROM os_historico WHERE os_id=?", (id2,))
            conn.execute("DELETE FROM itens_os WHERE os_id=?", (id2,))
            conn.execute("DELETE FROM ordens_servico WHERE id=?", (id2,))
        assert proximo_numero_os() == "OS-0004"


# ---------------------------------------------------------------------------
# Etapa 3 — CRUD básico de OS
# ---------------------------------------------------------------------------

class TestCRUDOS:
    def test_salvar_os_retorna_id(self, banco):
        from views.os.os_model import salvar_os
        oid = salvar_os(_dados_os(), [])
        assert isinstance(oid, int) and oid > 0

    def test_salvar_os_atribui_numero(self, banco):
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [])
        os_obj = obter_os(oid)
        assert os_obj.numero == "OS-0001"

    def test_salvar_os_status_default_aberta(self, banco):
        from views.os.os_model import salvar_os, obter_os
        dados = _dados_os()
        del dados["status"]
        oid = salvar_os(dados, [])
        assert obter_os(oid).status == "aberta"

    def test_salvar_os_persiste_solicitante(self, banco):
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os("Maria Souza"), [])
        os_obj = obter_os(oid)
        assert os_obj.solicitante_nome == "Maria Souza"
        assert os_obj.solicitante_setor == "TI"
        assert os_obj.solicitante_ramal == "1234"

    def test_obter_os_inexistente_retorna_none(self, banco):
        from views.os.os_model import obter_os
        assert obter_os(9999) is None

    def test_listar_os_vazio(self, banco):
        from views.os.os_model import listar_os
        assert listar_os() == []

    def test_listar_os_ordena_por_id_desc(self, banco):
        from views.os.os_model import salvar_os, listar_os
        oid1 = salvar_os(_dados_os("Primeiro"), [])
        oid2 = salvar_os(_dados_os("Segundo"), [])
        lista = listar_os()
        assert lista[0].id == oid2
        assert lista[1].id == oid1

    def test_listar_os_carrega_itens_para_totais_corretos(self, banco):
        """REGRESSAO: listar_os deve carregar itens, senao os cards da
        listagem mostram total_materiais=0 (so valor_mao_obra)."""
        from views.os.os_model import salvar_os, listar_os
        salvar_os(_dados_os(), [
            _item("Material A", 2.0, 50.0),
            _item("Material B", 1.0, 30.0),
        ])
        lista = listar_os()
        assert len(lista) == 1
        assert len(lista[0].itens) == 2, \
            "listar_os precisa carregar itens senao a view mostra totais errados"
        assert lista[0].total_materiais == pytest.approx(130.0)
        assert lista[0].valor_total == pytest.approx(130.0)

    def test_atualizar_os_altera_campos(self, banco):
        from views.os.os_model import salvar_os, atualizar_os, obter_os
        oid = salvar_os(_dados_os(), [])
        novos = {**_dados_os(), "responsavel": "Carlos", "status": "em_andamento"}
        atualizar_os(oid, novos, [])
        os_obj = obter_os(oid)
        assert os_obj.responsavel == "Carlos"
        assert os_obj.status == "em_andamento"

    def test_cancelar_os(self, banco):
        from views.os.os_model import salvar_os, cancelar_os, obter_os
        oid = salvar_os(_dados_os(), [])
        cancelar_os(oid)
        assert obter_os(oid).status == "cancelada"


# ---------------------------------------------------------------------------
# Etapa 4 — Itens da OS (produtos/serviços, FK opcional)
# ---------------------------------------------------------------------------

class TestItensOS:
    def test_salvar_os_com_itens_cria_itens(self, banco):
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [
            _item("Material A", 2.0, 50.0),
            _item("Material B", 1.0, 30.0),
        ])
        os_obj = obter_os(oid)
        assert len(os_obj.itens) == 2

    def test_item_sem_produto_id_aceito(self, banco):
        """produto_id é FK opcional (item ad-hoc, sem cadastro prévio)."""
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [_item("Avulso", 1.0, 10.0)])
        os_obj = obter_os(oid)
        assert os_obj.itens[0].produto_id is None

    def test_item_com_produto_id_valido(self, banco):
        from views.vendas.venda_model import salvar_produto
        from views.os.os_model import salvar_os, obter_os
        pid = salvar_produto({"nome": "Parafuso M5", "tipo": "produto",
                              "preco": 0.50, "descricao": "", "ativo": True})
        oid = salvar_os(_dados_os(), [_item("Parafuso", 10.0, 0.50, produto_id=pid)])
        os_obj = obter_os(oid)
        assert os_obj.itens[0].produto_id == pid

    def test_item_aceita_servico_da_tabela_produtos(self, banco):
        """OS deve reusar produtos com tipo='servico'."""
        from views.vendas.venda_model import salvar_produto
        from views.os.os_model import salvar_os, obter_os
        sid = salvar_produto({"nome": "Hora técnica", "tipo": "servico",
                              "preco": 80.0, "descricao": "", "ativo": True})
        oid = salvar_os(_dados_os(), [_item("Serviço", 2.0, 80.0, produto_id=sid)])
        os_obj = obter_os(oid)
        assert os_obj.itens[0].produto_id == sid

    def test_subtotal_calculado_qtd_x_preco(self, banco):
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [_item("X", 3.0, 25.0)])
        os_obj = obter_os(oid)
        assert os_obj.itens[0].subtotal == pytest.approx(75.0)

    def test_atualizar_os_substitui_itens(self, banco):
        from views.os.os_model import salvar_os, atualizar_os, obter_os
        oid = salvar_os(_dados_os(), [_item("Original", 1.0, 100.0)])
        atualizar_os(oid, _dados_os(), [
            _item("Novo A", 2.0, 10.0),
            _item("Novo B", 1.0, 50.0),
        ])
        os_obj = obter_os(oid)
        assert len(os_obj.itens) == 2
        descricoes = {i.descricao for i in os_obj.itens}
        assert descricoes == {"Novo A", "Novo B"}


# ---------------------------------------------------------------------------
# Etapa 5 — Cálculos (total_materiais, valor_mao_obra, valor_total)
# ---------------------------------------------------------------------------

class TestCalculosOS:
    def test_total_materiais_sem_itens_zero(self, banco):
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [])
        assert obter_os(oid).total_materiais == pytest.approx(0.0)

    def test_total_materiais_soma_subtotais(self, banco):
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [
            _item("A", 2.0, 50.0),
            _item("B", 1.0, 30.0),
        ])
        assert obter_os(oid).total_materiais == pytest.approx(130.0)

    def test_valor_mao_obra_sem_horas_zero(self, banco):
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [])
        assert obter_os(oid).valor_mao_obra == pytest.approx(0.0)

    def test_valor_mao_obra_calculo(self, banco):
        from views.os.os_model import salvar_os, obter_os
        dados = {**_dados_os(), "valor_hora": 80.0, "horas_trabalhadas": 2.5}
        oid = salvar_os(dados, [])
        assert obter_os(oid).valor_mao_obra == pytest.approx(200.0)

    def test_valor_total_soma_materiais_e_mao_obra(self, banco):
        from views.os.os_model import salvar_os, obter_os
        dados = {**_dados_os(), "valor_hora": 100.0, "horas_trabalhadas": 1.0}
        oid = salvar_os(dados, [_item("Material", 1.0, 50.0)])
        os_obj = obter_os(oid)
        assert os_obj.total_materiais == pytest.approx(50.0)
        assert os_obj.valor_mao_obra == pytest.approx(100.0)
        assert os_obj.valor_total == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# Etapa 6 — Histórico de alterações
# ---------------------------------------------------------------------------

class TestHistoricoOS:
    def test_criar_os_registra_evento(self, banco):
        from views.os.os_model import salvar_os, listar_historico
        oid = salvar_os(_dados_os(), [])
        hist = listar_historico(oid)
        assert len(hist) == 1
        assert hist[0].campo == "criacao"

    def test_atualizar_campo_registra_alteracao(self, banco):
        from views.os.os_model import salvar_os, atualizar_os, listar_historico
        oid = salvar_os(_dados_os(), [])
        novos = {**_dados_os(), "responsavel": "Pedro"}
        atualizar_os(oid, novos, [])
        hist = listar_historico(oid)
        campos = [h.campo for h in hist]
        assert "responsavel" in campos
        evento = next(h for h in hist if h.campo == "responsavel")
        assert evento.valor_anterior == ""
        assert evento.valor_novo == "Pedro"

    def test_alteracao_sem_mudanca_nao_registra(self, banco):
        from views.os.os_model import salvar_os, atualizar_os, listar_historico
        oid = salvar_os(_dados_os(), [])
        atualizar_os(oid, _dados_os(), [])
        hist = listar_historico(oid)
        # Apenas o evento de criação deve constar
        assert len(hist) == 1
        assert hist[0].campo == "criacao"

    def test_cancelar_registra_alteracao_status(self, banco):
        from views.os.os_model import salvar_os, cancelar_os, listar_historico
        oid = salvar_os(_dados_os(), [])
        cancelar_os(oid)
        hist = listar_historico(oid)
        campos = [h.campo for h in hist]
        assert "status" in campos
        evento = next(h for h in hist if h.campo == "status")
        assert evento.valor_novo == "cancelada"


# ---------------------------------------------------------------------------
# Etapa 7 — Filtros e busca
# ---------------------------------------------------------------------------

class TestFiltrosBuscaOS:
    def test_filtrar_por_status(self, banco):
        from views.os.os_model import salvar_os, cancelar_os, listar_os
        salvar_os(_dados_os("Aberta"), [])
        cid = salvar_os(_dados_os("Cancelada"), [])
        cancelar_os(cid)
        assert len(listar_os(status="aberta")) == 1
        assert len(listar_os(status="cancelada")) == 1

    def test_filtrar_por_mes_ano(self, banco):
        from views.os.os_model import salvar_os, listar_os
        salvar_os(_dados_os("Junho", data="2025-06-10"), [])
        salvar_os(_dados_os("Julho", data="2025-07-01"), [])
        assert len(listar_os(ano=2025, mes=6)) == 1
        assert len(listar_os(ano=2025, mes=7)) == 1

    def test_filtrar_por_solicitante(self, banco):
        from views.os.os_model import salvar_os, listar_os
        salvar_os(_dados_os("Ana Silva"), [])
        salvar_os(_dados_os("Carlos Santos"), [])
        encontradas = listar_os(solicitante="ana")
        assert len(encontradas) == 1
        assert encontradas[0].solicitante_nome == "Ana Silva"

    def test_buscar_por_numero(self, banco):
        from views.os.os_model import salvar_os, listar_os
        salvar_os(_dados_os(), [])  # OS-0001
        salvar_os(_dados_os(), [])  # OS-0002
        encontradas = listar_os(busca="0001")
        assert len(encontradas) == 1
        assert encontradas[0].numero == "OS-0001"

    def test_buscar_por_texto_descricao(self, banco):
        from views.os.os_model import salvar_os, listar_os
        dados_a = {**_dados_os(), "descricao_servico": "Troca de lâmpada do corredor"}
        dados_b = {**_dados_os(), "descricao_servico": "Reparo no ar condicionado"}
        salvar_os(dados_a, [])
        salvar_os(dados_b, [])
        encontradas = listar_os(busca="lâmpada")
        assert len(encontradas) == 1

    def test_busca_case_insensitive(self, banco):
        from views.os.os_model import salvar_os, listar_os
        dados = {**_dados_os(), "descricao_servico": "Manutenção URGENTE"}
        salvar_os(dados, [])
        assert len(listar_os(busca="urgente")) == 1
        assert len(listar_os(busca="URGENTE")) == 1
        assert len(listar_os(busca="Urgente")) == 1


# ---------------------------------------------------------------------------
# Etapa 8 — Impressão PDF
# ---------------------------------------------------------------------------

class TestImprimirOS:
    def test_gera_pdf_arquivo_existe(self, banco, tmp_path):
        from views.os.imprimir_os import imprimir_os_pdf
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [_item("Parafuso", 10.0, 0.50)])
        os_obj = obter_os(oid)
        destino = tmp_path / "saida.pdf"
        imprimir_os_pdf(os_obj, destino)
        assert destino.exists()
        assert destino.stat().st_size > 0

    def test_gera_pdf_assinatura_valida(self, banco, tmp_path):
        """Primeiros bytes do arquivo devem ser %PDF (magic bytes)."""
        from views.os.imprimir_os import imprimir_os_pdf
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [_item("Cabo HDMI", 2.0, 30.0)])
        destino = tmp_path / "os.pdf"
        imprimir_os_pdf(obter_os(oid), destino)
        with destino.open("rb") as f:
            cabecalho = f.read(4)
        assert cabecalho == b"%PDF"

    def test_gera_pdf_sem_itens(self, banco, tmp_path):
        from views.os.imprimir_os import imprimir_os_pdf
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [])
        destino = tmp_path / "vazia.pdf"
        imprimir_os_pdf(obter_os(oid), destino)
        assert destino.exists()

    def test_gera_pdf_sem_mao_de_obra(self, banco, tmp_path):
        from views.os.imprimir_os import imprimir_os_pdf
        from views.os.os_model import salvar_os, obter_os
        dados = {**_dados_os(), "valor_hora": 0.0, "horas_trabalhadas": 0.0}
        oid = salvar_os(dados, [_item("X", 1.0, 50.0)])
        destino = tmp_path / "sem_mo.pdf"
        imprimir_os_pdf(obter_os(oid), destino)
        assert destino.exists()

    def test_gera_pdf_caminho_str(self, banco, tmp_path):
        """imprimir_os_pdf deve aceitar caminho str além de Path."""
        from views.os.imprimir_os import imprimir_os_pdf
        from views.os.os_model import salvar_os, obter_os
        oid = salvar_os(_dados_os(), [])
        destino = str(tmp_path / "str_path.pdf")
        imprimir_os_pdf(obter_os(oid), destino)
        from pathlib import Path as _P
        assert _P(destino).exists()

    def test_atualizar_os_atomico_historico_consistente_com_dados(self, banco):
        """atualizar_os deve ler o estado e fazer UPDATE na mesma conexão —
        senão entre o obter_os e o UPDATE outro processo pode alterar."""
        from views.os.os_model import (
            atualizar_os, listar_historico, obter_os, salvar_os,
        )
        oid = salvar_os(_dados_os(), [])

        # Atualiza um campo
        novos = {**_dados_os(), "responsavel": "Pedro"}
        atualizar_os(oid, novos, [])

        # Histórico deve refletir mudança exatamente
        hist = listar_historico(oid)
        evento_resp = next(
            (h for h in hist if h.campo == "responsavel"), None
        )
        assert evento_resp is not None
        assert evento_resp.valor_anterior == ""
        assert evento_resp.valor_novo == "Pedro"

        # Estado final correto
        atual = obter_os(oid)
        assert atual.responsavel == "Pedro"
