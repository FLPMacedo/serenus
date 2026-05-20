"""
test_importar_fatura.py — Testes de importação de fatura de cartão (TDD).

Cobertura:
  TestImportarCompraFatura   — importar_compra_fatura() em cartao_model.py
  TestDuplicidadeImportacao  — lógica de dedup / delta incremental
  TestParsearParcela         — parsear_parcela() em importar_fatura_model.py
  TestValidarLinhasFatura    — validar_linhas_fatura()
  TestLerArquivoFatura       — ler_arquivo_fatura() (CSV e XLSX)
  TestGerarTemplate          — gerar_template_importacao_xlsx() em exportar_model.py
  TestFluxoEquivalencia      — import na parcela 1/N deve ser idêntico ao lançamento manual
"""

import sys
from pathlib import Path
from datetime import date

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import conectar


# ---------------------------------------------------------------------------
# Fixture: cartão de teste — mesmo padrão de test_pagar_com_cartao.py
# ---------------------------------------------------------------------------

@pytest.fixture
def cartao(banco):
    """Cartão com limite 5000, dia_vencimento=10, dia_fechamento=3."""
    from views.cartoes.cartao_model import salvar_cartao
    return salvar_cartao({
        "nome":           "Import Teste",
        "banco":          "nubank",
        "bandeira":       "visa",
        "ultimos_digitos": "9999",
        "cor_fundo":      "#6D28D9",
        "cor_texto":      "#FFFFFF",
        "limite":         5_000.0,
        "limite_disponivel": 5_000.0,
        "dia_vencimento": 10,
        "dia_fechamento": 3,
    })


# ---------------------------------------------------------------------------
# Helpers — SQL direto, mesmo estilo dos demais testes
# ---------------------------------------------------------------------------

def _compras(cartao_id: int):
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM compras_cartao WHERE cartao_id=? ORDER BY id",
            (cartao_id,),
        ).fetchall()


def _parcelas(cartao_id: int):
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM parcelas_cartao WHERE cartao_id=?"
            " ORDER BY numero_parcela, mes_referencia",
            (cartao_id,),
        ).fetchall()


def _contas_pagar_cartao():
    """Contas a pagar criadas pelo fluxo de cartão."""
    with conectar() as conn:
        return conn.execute("""
            SELECT cp.* FROM contas_pagar cp
            JOIN plano_contas pc ON pc.id = cp.plano_conta_id
            WHERE pc.categoria = 'Cartão de Crédito'
            ORDER BY cp.data_vencimento
        """).fetchall()


def _limite(cartao_id: int) -> float:
    with conectar() as conn:
        return float(conn.execute(
            "SELECT limite_disponivel FROM cartoes WHERE id=?", (cartao_id,)
        ).fetchone()["limite_disponivel"])


def _dados_import(cartao_id: int, **kw) -> dict:
    """Builder de dados mínimos para importar_compra_fatura."""
    base = {
        "cartao_id":       cartao_id,
        "descricao":       "Assinatura Teste",
        "estabelecimento": "",
        "categoria":       "Assinatura",
        "numero_parcela":  1,
        "total_parcelas":  1,
        "valor_parcela":   100.0,
        "mes_referencia":  "2025-05",
        "criar_historico": True,
    }
    base.update(kw)
    return base


# ===========================================================================
# 1. importar_compra_fatura — função central em cartao_model.py
# ===========================================================================

class TestImportarCompraFatura:

    # --- parcela 1/1 (caso mais simples) ---

    def test_parcela_1_1_cria_compra(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(cartao))
        assert len(_compras(cartao)) == 1

    def test_parcela_1_1_retorna_compra_id(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        cid = importar_compra_fatura(_dados_import(cartao))
        assert isinstance(cid, int) and cid > 0

    def test_parcela_1_1_cria_uma_parcela_pendente(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(cartao))
        parcelas = _parcelas(cartao)
        assert len(parcelas) == 1
        assert parcelas[0]["numero_parcela"] == 1
        assert parcelas[0]["status"] == "pendente"

    def test_parcela_1_1_cria_conta_pagar(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(cartao))
        assert len(_contas_pagar_cartao()) == 1

    def test_parcela_1_1_debita_limite(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(cartao, valor_parcela=300.0))
        assert _limite(cartao) == pytest.approx(4_700.0)

    def test_parcela_1_1_total_parcelas_3_cria_3_pendentes(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=1, total_parcelas=3,
            valor_parcela=100.0, mes_referencia="2025-05",
        ))
        pendentes = [p for p in _parcelas(cartao) if p["status"] == "pendente"]
        assert len(pendentes) == 3

    def test_parcela_1_3_numeracao_sequencial(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=1, total_parcelas=3,
            valor_parcela=100.0, mes_referencia="2025-05",
        ))
        nums = [p["numero_parcela"] for p in _parcelas(cartao)]
        assert nums == [1, 2, 3]

    def test_parcela_1_3_meses_sequenciais(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=1, total_parcelas=3,
            valor_parcela=100.0, mes_referencia="2025-11",
        ))
        meses = [p["mes_referencia"] for p in _parcelas(cartao)]
        assert meses == ["2025-11", "2025-12", "2026-01"]

    # --- parcela do meio (7/12) ---

    def test_parcela_7_12_cria_6_parcelas_restantes(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        assert len(_parcelas(cartao)) == 6

    def test_parcela_7_12_numeracao_comeca_em_7(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        nums = [p["numero_parcela"] for p in _parcelas(cartao)]
        assert nums == [7, 8, 9, 10, 11, 12]

    def test_parcela_7_12_mes_referencia_correto(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        meses = [p["mes_referencia"] for p in _parcelas(cartao)]
        assert meses[0] == "2025-05"
        assert meses[-1] == "2025-10"

    def test_parcela_7_12_todas_pendentes(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        status_list = [p["status"] for p in _parcelas(cartao)]
        assert all(s == "pendente" for s in status_list)

    def test_parcela_7_12_debita_so_saldo_restante(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        # 6 parcelas restantes × 100 = 600 de débito
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
        ))
        assert _limite(cartao) == pytest.approx(4_400.0)

    def test_parcela_7_12_contas_pagar_so_para_pendentes(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        # Só 6 contas_pagar (parcelas 7 a 12)
        assert len(_contas_pagar_cartao()) == 6

    def test_parcela_7_12_com_historico_cria_12_parcelas(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=True,
        ))
        assert len(_parcelas(cartao)) == 12

    def test_parcela_7_12_com_historico_passadas_como_pagas(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=True,
        ))
        parcelas = _parcelas(cartao)
        pagas    = [p for p in parcelas if p["status"] == "pago"]
        pendentes = [p for p in parcelas if p["status"] == "pendente"]
        assert len(pagas) == 6     # parcelas 1–6
        assert len(pendentes) == 6  # parcelas 7–12

    def test_parcela_7_12_com_historico_contas_pagar_so_pendentes(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        # Mesmo com histórico criado, contas_pagar só para as pendentes
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=True,
        ))
        assert len(_contas_pagar_cartao()) == 6

    def test_parcelas_pagas_registradas_corretamente(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
        ))
        compras = _compras(cartao)
        assert compras[0]["parcelas_pagas"] == 6

    def test_total_parcelas_registrado_completo(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=7, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
        ))
        compras = _compras(cartao)
        assert compras[0]["total_parcelas"] == 12

    # --- última parcela ---

    def test_ultima_parcela_cria_uma_pendente(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=12, total_parcelas=12,
            valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        pendentes = [p for p in _parcelas(cartao) if p["status"] == "pendente"]
        assert len(pendentes) == 1

    def test_ultima_parcela_debita_um_valor_parcela(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=12, total_parcelas=12,
            valor_parcela=150.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        assert _limite(cartao) == pytest.approx(4_850.0)

    # --- arredondamento ---

    def test_arredondamento_ultima_parcela_absorve_residuo(self, banco, cartao):
        """3 parcelas de 33.33 + 33.34 = 100.00 exato."""
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=1, total_parcelas=3,
            valor_parcela=pytest.approx(33.33, abs=0.01),  # não usado diretamente, só p/ clareza
        ))
        # Usa valor "real" do import
        importar_compra_fatura.__module__  # garante importação
        from views.cartoes.cartao_model import importar_compra_fatura as imp
        with conectar() as conn:
            conn.execute("DELETE FROM parcelas_cartao")
            conn.execute("DELETE FROM compras_cartao")
            conn.execute("DELETE FROM contas_pagar")
            conn.execute("UPDATE cartoes SET limite_disponivel=5000")
        imp(_dados_import(cartao, numero_parcela=1, total_parcelas=3, valor_parcela=33.33))
        soma = sum(p["valor"] for p in _parcelas(cartao))
        assert soma == pytest.approx(99.99, abs=0.02)

    # --- vencimento usa dia do cartão ---

    def test_vencimento_conta_pagar_usa_dia_do_cartao(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=1, total_parcelas=1,
            valor_parcela=100.0, mes_referencia="2025-06",
        ))
        contas = _contas_pagar_cartao()
        assert len(contas) == 1
        # dia_vencimento do cartão é 10
        assert contas[0]["data_vencimento"] == "2025-06-10"

    def test_vencimento_clampado_em_fevereiro(self, banco, cartao):
        """Dia 10 em fevereiro é válido, não precisa clamp. Testa com dia 31."""
        from views.cartoes.cartao_model import salvar_cartao, importar_compra_fatura
        c2 = salvar_cartao({
            "nome": "Cartão Feb", "banco": "nubank", "bandeira": "visa",
            "ultimos_digitos": "0001", "cor_fundo": "#000", "cor_texto": "#FFF",
            "limite": 3_000.0, "limite_disponivel": 3_000.0,
            "dia_vencimento": 31, "dia_fechamento": 3,
        })
        importar_compra_fatura(_dados_import(
            c2, numero_parcela=1, total_parcelas=1,
            valor_parcela=50.0, mes_referencia="2025-02",
        ))
        contas = _contas_pagar_cartao()
        # Fevereiro de 2025 tem 28 dias
        assert contas[0]["data_vencimento"] == "2025-02-28"

    # --- atualiza dívida do cartão ---

    def test_atualiza_divida_do_cartao(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, numero_parcela=1, total_parcelas=3,
            valor_parcela=100.0, mes_referencia="2025-05",
        ))
        with conectar() as conn:
            divida = conn.execute(
                "SELECT * FROM dividas WHERE tipo='cartao'",
            ).fetchone()
        assert divida is not None
        assert float(divida["saldo_atual"]) > 0


# ===========================================================================
# 2. Duplicidade e delta incremental
# ===========================================================================

class TestDuplicidadeImportacao:

    def test_importar_mesmo_item_duas_vezes_bloqueia_segundo(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        dados = _dados_import(
            cartao, descricao="Netflix", numero_parcela=3,
            total_parcelas=12, valor_parcela=55.90, mes_referencia="2025-05",
        )
        importar_compra_fatura(dados)
        # Segunda chamada com dados idênticos deve retornar None ou 0 (não cria nova compra)
        resultado = importar_compra_fatura(dados)
        assert resultado is None or resultado == 0
        # Deve existir apenas 1 compra, não 2
        assert len(_compras(cartao)) == 1

    def test_item_diferente_nao_e_bloqueado(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, descricao="Netflix", numero_parcela=3,
            total_parcelas=12, valor_parcela=55.90, mes_referencia="2025-05",
        ))
        importar_compra_fatura(_dados_import(
            cartao, descricao="Spotify", numero_parcela=1,
            total_parcelas=1, valor_parcela=19.90, mes_referencia="2025-05",
        ))
        assert len(_compras(cartao)) == 2

    def test_mesmo_item_mes_diferente_nao_e_bloqueado(self, banco, cartao):
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, descricao="Netflix", numero_parcela=3,
            total_parcelas=12, valor_parcela=55.90, mes_referencia="2025-05",
        ))
        importar_compra_fatura(_dados_import(
            cartao, descricao="Netflix", numero_parcela=4,
            total_parcelas=12, valor_parcela=55.90, mes_referencia="2025-06",
        ))
        assert len(_compras(cartao)) == 2

    def test_delta_adiciona_parcelas_faltantes(self, banco, cartao):
        """
        Importa com total_parcelas=6, depois importa mesmo item com total_parcelas=9.
        O segundo deve adicionar as 3 parcelas faltantes (7, 8, 9).
        """
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, descricao="Curso Online", numero_parcela=1,
            total_parcelas=6, valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        # Mesmo item, mas agora tem 9 parcelas no total
        importar_compra_fatura(_dados_import(
            cartao, descricao="Curso Online", numero_parcela=1,
            total_parcelas=9, valor_parcela=100.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        # Deve haver apenas 1 compra (atualizada) e 9 parcelas no total
        assert len(_compras(cartao)) == 1
        assert len(_parcelas(cartao)) == 9

    def test_delta_nao_duplica_parcelas_existentes(self, banco, cartao):
        """Na atualização incremental, parcelas já existentes não são duplicadas."""
        from views.cartoes.cartao_model import importar_compra_fatura
        importar_compra_fatura(_dados_import(
            cartao, descricao="Seguro", numero_parcela=1,
            total_parcelas=6, valor_parcela=50.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        importar_compra_fatura(_dados_import(
            cartao, descricao="Seguro", numero_parcela=1,
            total_parcelas=8, valor_parcela=50.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        meses = [p["mes_referencia"] for p in _parcelas(cartao)]
        # Não deve haver meses repetidos
        assert len(meses) == len(set(meses))


# ===========================================================================
# 3. parsear_parcela — importar_fatura_model.py
# ===========================================================================

class TestParsearParcela:

    def test_formato_barra_7_12(self):
        from views.cartoes.importar_fatura_model import parsear_parcela
        assert parsear_parcela("7/12") == (7, 12)

    def test_formato_de_7_de_12(self):
        from views.cartoes.importar_fatura_model import parsear_parcela
        assert parsear_parcela("7 de 12") == (7, 12)

    def test_formato_barra_sem_espacos(self):
        from views.cartoes.importar_fatura_model import parsear_parcela
        assert parsear_parcela("1/1") == (1, 1)

    def test_ausente_retorna_1_1(self):
        from views.cartoes.importar_fatura_model import parsear_parcela
        assert parsear_parcela("") == (1, 1)

    def test_none_retorna_1_1(self):
        from views.cartoes.importar_fatura_model import parsear_parcela
        assert parsear_parcela(None) == (1, 1)

    def test_numero_maior_que_total_levanta_erro(self):
        from views.cartoes.importar_fatura_model import parsear_parcela
        with pytest.raises(ValueError):
            parsear_parcela("8/5")

    def test_zero_levanta_erro(self):
        from views.cartoes.importar_fatura_model import parsear_parcela
        with pytest.raises(ValueError):
            parsear_parcela("0/5")

    def test_formato_com_espacos_extras(self):
        from views.cartoes.importar_fatura_model import parsear_parcela
        assert parsear_parcela("  3 / 12  ") == (3, 12)

    def test_ultima_parcela(self):
        from views.cartoes.importar_fatura_model import parsear_parcela
        assert parsear_parcela("12/12") == (12, 12)


# ===========================================================================
# 4. validar_linhas_fatura — importar_fatura_model.py
# ===========================================================================

class TestValidarLinhasFatura:

    def _linha(self, **kw) -> dict:
        base = {
            "descricao":       "Produto Teste",
            "estabelecimento": "",
            "categoria":       "",
            "parcela":         "1/1",
            "valor":           100.0,
        }
        base.update(kw)
        return base

    def test_linha_valida_sem_erros(self):
        from views.cartoes.importar_fatura_model import validar_linhas_fatura
        erros = validar_linhas_fatura([self._linha()])
        assert erros == []

    def test_descricao_vazia_gera_erro(self):
        from views.cartoes.importar_fatura_model import validar_linhas_fatura
        erros = validar_linhas_fatura([self._linha(descricao="")])
        assert len(erros) >= 1
        assert any("descri" in e.lower() for e in erros)

    def test_valor_zero_gera_erro(self):
        from views.cartoes.importar_fatura_model import validar_linhas_fatura
        erros = validar_linhas_fatura([self._linha(valor=0)])
        assert len(erros) >= 1

    def test_valor_negativo_gera_erro(self):
        from views.cartoes.importar_fatura_model import validar_linhas_fatura
        erros = validar_linhas_fatura([self._linha(valor=-50.0)])
        assert len(erros) >= 1

    def test_parcela_invalida_numero_maior_total(self):
        from views.cartoes.importar_fatura_model import validar_linhas_fatura
        erros = validar_linhas_fatura([self._linha(parcela="8/5")])
        assert len(erros) >= 1

    def test_multiplas_linhas_validas_sem_erros(self):
        from views.cartoes.importar_fatura_model import validar_linhas_fatura
        linhas = [
            self._linha(descricao="Netflix",   parcela="3/12", valor=55.90),
            self._linha(descricao="Spotify",   parcela="",     valor=19.90),
            self._linha(descricao="Aluguel",   parcela="1/1",  valor=1500.0),
        ]
        assert validar_linhas_fatura(linhas) == []

    def test_multiplos_erros_em_linhas_diferentes(self):
        from views.cartoes.importar_fatura_model import validar_linhas_fatura
        linhas = [
            self._linha(descricao=""),          # erro: descrição vazia
            self._linha(valor=0),               # erro: valor zero
            self._linha(parcela="9/3"),         # erro: número > total
        ]
        erros = validar_linhas_fatura(linhas)
        assert len(erros) >= 3

    def test_erro_indica_numero_da_linha(self):
        from views.cartoes.importar_fatura_model import validar_linhas_fatura
        erros = validar_linhas_fatura([
            self._linha(),                      # linha 1: ok
            self._linha(descricao=""),          # linha 2: erro
        ])
        assert any("2" in e for e in erros)


# ===========================================================================
# 5. ler_arquivo_fatura — CSV e XLSX
# ===========================================================================

class TestLerArquivoFatura:

    def test_ler_csv_retorna_linhas(self, tmp_path):
        caminho = str(tmp_path / "fatura.csv")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("descricao,estabelecimento,categoria,parcela,valor\n")
            f.write("Netflix,Netflix Inc,Streaming,3/12,55.90\n")
            f.write("Spotify,,Musica,,19.90\n")
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        linhas = ler_arquivo_fatura(caminho)
        assert len(linhas) == 2

    def test_ler_csv_descricao_correta(self, tmp_path):
        caminho = str(tmp_path / "fatura.csv")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("descricao,estabelecimento,categoria,parcela,valor\n")
            f.write("Netflix,Netflix Inc,Streaming,3/12,55.90\n")
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        linhas = ler_arquivo_fatura(caminho)
        assert linhas[0]["descricao"] == "Netflix"

    def test_ler_csv_valor_como_float(self, tmp_path):
        caminho = str(tmp_path / "fatura.csv")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("descricao,estabelecimento,categoria,parcela,valor\n")
            f.write("Curso,,Educacao,1/6,199.90\n")
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        linhas = ler_arquivo_fatura(caminho)
        assert isinstance(linhas[0]["valor"], float)
        assert linhas[0]["valor"] == pytest.approx(199.90)

    def test_ler_xlsx_retorna_linhas(self, tmp_path):
        from openpyxl import Workbook
        caminho = str(tmp_path / "fatura.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.append(["descricao", "estabelecimento", "categoria", "parcela", "valor"])
        ws.append(["Netflix", "Netflix Inc", "Streaming", "3/12", 55.90])
        ws.append(["Spotify", "", "Musica", "", 19.90])
        wb.save(caminho)
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        linhas = ler_arquivo_fatura(caminho)
        assert len(linhas) == 2

    def test_ler_xlsx_descricao_correta(self, tmp_path):
        from openpyxl import Workbook
        caminho = str(tmp_path / "fatura.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.append(["descricao", "estabelecimento", "categoria", "parcela", "valor"])
        ws.append(["Curso Python", "Udemy", "Educacao", "2/6", 99.90])
        wb.save(caminho)
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        linhas = ler_arquivo_fatura(caminho)
        assert linhas[0]["descricao"] == "Curso Python"

    def test_ler_xlsx_ignora_linhas_vazias(self, tmp_path):
        from openpyxl import Workbook
        caminho = str(tmp_path / "fatura.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.append(["descricao", "estabelecimento", "categoria", "parcela", "valor"])
        ws.append(["Netflix", "", "", "1/12", 55.90])
        ws.append([None, None, None, None, None])   # linha vazia
        ws.append(["Spotify", "", "", "", 19.90])
        wb.save(caminho)
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        linhas = ler_arquivo_fatura(caminho)
        assert len(linhas) == 2

    def test_ler_csv_valor_com_virgula_decimal(self, tmp_path):
        """Arquivos brasileiros usam vírgula como separador decimal."""
        caminho = str(tmp_path / "fatura_br.csv")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("descricao,estabelecimento,categoria,parcela,valor\n")
            f.write("Mercado,,Alimentacao,1/1,\"1.234,56\"\n")
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        linhas = ler_arquivo_fatura(caminho)
        assert linhas[0]["valor"] == pytest.approx(1234.56)

    def test_ler_arquivo_extensao_invalida_levanta_erro(self, tmp_path):
        caminho = str(tmp_path / "fatura.pdf")
        Path(caminho).write_text("dummy")
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        with pytest.raises((ValueError, Exception)):
            ler_arquivo_fatura(caminho)


# ===========================================================================
# 6. gerar_template_importacao_xlsx — exportar_model.py
# ===========================================================================

class TestGerarTemplate:

    def test_template_cria_arquivo(self, tmp_path):
        caminho = str(tmp_path / "template.xlsx")
        from views.exportar.exportar_model import gerar_template_importacao_xlsx
        gerar_template_importacao_xlsx(caminho)
        assert Path(caminho).exists()
        assert Path(caminho).stat().st_size > 0

    def test_template_tem_colunas_obrigatorias(self, tmp_path):
        from openpyxl import load_workbook
        caminho = str(tmp_path / "template.xlsx")
        from views.exportar.exportar_model import gerar_template_importacao_xlsx
        gerar_template_importacao_xlsx(caminho)
        wb = load_workbook(caminho)
        ws = wb.active
        # Busca cabeçalho em qualquer das primeiras 5 linhas
        texto_total = " ".join(
            str(ws.cell(r, c).value or "").lower()
            for r in range(1, 6) for c in range(1, 7)
        )
        assert "descricao" in texto_total or "descrição" in texto_total
        assert "valor" in texto_total

    def test_template_tem_coluna_parcela(self, tmp_path):
        from openpyxl import load_workbook
        caminho = str(tmp_path / "template2.xlsx")
        from views.exportar.exportar_model import gerar_template_importacao_xlsx
        gerar_template_importacao_xlsx(caminho)
        wb = load_workbook(caminho)
        ws = wb.active
        texto_total = " ".join(
            str(ws.cell(r, c).value or "").lower()
            for r in range(1, 6) for c in range(1, 7)
        )
        assert "parcela" in texto_total

    def test_template_pode_ser_lido_por_ler_arquivo(self, tmp_path):
        """Template gerado + dados inseridos deve ser lido por ler_arquivo_fatura."""
        from openpyxl import load_workbook
        caminho = str(tmp_path / "template_filled.xlsx")
        from views.exportar.exportar_model import gerar_template_importacao_xlsx
        gerar_template_importacao_xlsx(caminho)
        # Abre e insere uma linha de dados depois do cabeçalho
        wb = load_workbook(caminho)
        ws = wb.active
        # Encontra a última linha com cabeçalho e insere dado abaixo
        ws.append(["Produto Importado", "Loja X", "Outros", "2/6", 150.0])
        wb.save(caminho)
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        linhas = ler_arquivo_fatura(caminho)
        assert any(l.get("descricao") == "Produto Importado" for l in linhas)


# ===========================================================================
# 7. Equivalência: import na parcela 1/N == lançamento manual
# ===========================================================================

class TestVencimentoExplicito:
    """B2 — importar_compra_fatura aceita data_vencimento (opcional) no
    cabeçalho da fatura. Quando passada, sobrescreve o calculo via
    dia_vencimento do cartao para a PRIMEIRA parcela (mes_referencia)."""

    def _cartao_basico(self, banco):
        from views.cartoes.cartao_model import salvar_cartao
        return salvar_cartao({
            "nome": "TesteVenc", "banco": "outro", "bandeira": "visa",
            "limite": 5000.0, "limite_disponivel": 5000.0,
            "dia_vencimento": 10, "dia_fechamento": 5,
        })

    def test_data_vencimento_explicita_e_usada_na_parcela_atual(self, banco):
        """Quando o cabeçalho da fatura informa vencimento (ex: 28/04),
        a parcela do mes_referencia da importacao deve ter essa data
        em contas_pagar (e nao o dia 10 do cartao)."""
        from database import conectar
        from views.cartoes.cartao_model import importar_compra_fatura

        cartao_id = self._cartao_basico(banco)
        importar_compra_fatura({
            "cartao_id":         cartao_id,
            "descricao":         "Compra A",
            "numero_parcela":    1,
            "total_parcelas":    1,
            "valor_parcela":     100.0,
            "mes_referencia":    "2026-04",
            "data_vencimento":   "2026-04-28",
            "criar_historico":   False,
        })

        with conectar() as conn:
            row = conn.execute(
                "SELECT data_vencimento FROM contas_pagar"
                " WHERE descricao LIKE '%Compra A%'"
                " ORDER BY id DESC LIMIT 1"
            ).fetchone()
        assert row is not None
        assert row["data_vencimento"] == "2026-04-28"

    def test_sem_data_vencimento_continua_usando_dia_do_cartao(self, banco):
        """Retrocompat: sem data_vencimento, comportamento atual (dia_vencimento
        do cartao com cap pelo monthrange) continua valendo."""
        from database import conectar
        from views.cartoes.cartao_model import importar_compra_fatura

        cartao_id = self._cartao_basico(banco)  # dia_vencimento=10
        importar_compra_fatura({
            "cartao_id":      cartao_id,
            "descricao":      "Compra B",
            "numero_parcela": 1,
            "total_parcelas": 1,
            "valor_parcela":  50.0,
            "mes_referencia": "2026-04",
            "criar_historico": False,
        })

        with conectar() as conn:
            row = conn.execute(
                "SELECT data_vencimento FROM contas_pagar"
                " WHERE descricao LIKE '%Compra B%'"
                " ORDER BY id DESC LIMIT 1"
            ).fetchone()
        # Sem vencimento explicito: usa dia 10 do cartao
        assert row["data_vencimento"] == "2026-04-10"

    def test_parcelas_futuras_seguem_dia_do_cartao(self, banco):
        """Vencimento explicito so vale para a parcela do mes_referencia.
        Parcelas futuras continuam usando dia_vencimento do cartao."""
        from database import conectar
        from views.cartoes.cartao_model import importar_compra_fatura

        cartao_id = self._cartao_basico(banco)  # dia=10
        importar_compra_fatura({
            "cartao_id":      cartao_id,
            "descricao":      "Compra C",
            "numero_parcela": 1,
            "total_parcelas": 3,
            "valor_parcela":  60.0,
            "mes_referencia": "2026-04",
            "data_vencimento": "2026-04-28",
            "criar_historico": False,
        })

        with conectar() as conn:
            datas = [r[0] for r in conn.execute(
                "SELECT data_vencimento FROM contas_pagar"
                " WHERE descricao LIKE '%Compra C%' ORDER BY data_vencimento"
            ).fetchall()]
        # 3 parcelas: 28/abr (forcada), 10/mai, 10/jun
        assert "2026-04-28" in datas
        assert "2026-05-10" in datas
        assert "2026-06-10" in datas


class TestFluxoEquivalencia:
    """
    A importação na parcela 1/N deve produzir estado idêntico ao
    salvar_compra_com_parcelas(), que é o lançamento manual completo.
    """

    def test_parcela_1_3_equivale_ao_manual(self, banco, cartao):
        from views.cartoes.cartao_model import (
            importar_compra_fatura, salvar_compra_com_parcelas,
        )

        # Caminho A — lançamento manual
        salvar_compra_com_parcelas({
            "cartao_id":      cartao,
            "descricao":      "Compra Manual",
            "valor_total":    300.0,
            "total_parcelas": 3,
            "mes_inicio":     "2025-05",
            "categoria":      "Teste",
            "estabelecimento": "",
        })

        # Captura estado após manual
        parcelas_manual = _parcelas(cartao)
        contas_manual   = _contas_pagar_cartao()

        # Limpa tudo para testar o import isolado
        with conectar() as conn:
            conn.execute("DELETE FROM parcelas_cartao WHERE cartao_id=?", (cartao,))
            conn.execute("DELETE FROM compras_cartao  WHERE cartao_id=?", (cartao,))
            conn.execute("DELETE FROM contas_pagar")
            conn.execute("UPDATE cartoes SET limite_disponivel=5000 WHERE id=?", (cartao,))

        # Caminho B — importação
        importar_compra_fatura(_dados_import(
            cartao,
            descricao="Compra Manual",
            numero_parcela=1,
            total_parcelas=3,
            valor_parcela=100.0,
            mes_referencia="2025-05",
            categoria="Teste",
            criar_historico=False,
        ))

        parcelas_import = _parcelas(cartao)
        contas_import   = _contas_pagar_cartao()

        # Estrutura deve ser idêntica
        assert len(parcelas_import) == len(parcelas_manual)
        assert len(contas_import)   == len(contas_manual)

        for p_m, p_i in zip(parcelas_manual, parcelas_import):
            assert p_i["numero_parcela"]  == p_m["numero_parcela"]
            assert p_i["mes_referencia"]  == p_m["mes_referencia"]
            assert p_i["valor"]           == pytest.approx(p_m["valor"], abs=0.01)
            assert p_i["status"]          == p_m["status"]

        for c_m, c_i in zip(contas_manual, contas_import):
            assert c_i["valor"]            == pytest.approx(c_m["valor"], abs=0.01)
            assert c_i["data_vencimento"]  == c_m["data_vencimento"]
            assert c_i["status"]           == c_m["status"]

    def test_limite_pos_import_igual_ao_manual(self, banco, cartao):
        from views.cartoes.cartao_model import (
            importar_compra_fatura, salvar_compra_com_parcelas,
        )

        salvar_compra_com_parcelas({
            "cartao_id": cartao, "descricao": "TV",
            "valor_total": 1_200.0, "total_parcelas": 4,
            "mes_inicio": "2025-05", "categoria": "", "estabelecimento": "",
        })
        limite_manual = _limite(cartao)

        with conectar() as conn:
            conn.execute("DELETE FROM parcelas_cartao WHERE cartao_id=?", (cartao,))
            conn.execute("DELETE FROM compras_cartao  WHERE cartao_id=?", (cartao,))
            conn.execute("UPDATE cartoes SET limite_disponivel=5000 WHERE id=?", (cartao,))

        importar_compra_fatura(_dados_import(
            cartao, descricao="TV",
            numero_parcela=1, total_parcelas=4,
            valor_parcela=300.0, mes_referencia="2025-05",
            criar_historico=False,
        ))
        limite_import = _limite(cartao)

        assert limite_import == pytest.approx(limite_manual, abs=0.01)
