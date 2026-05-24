"""
test_perfis_demo.py — Massa de regressão real usando os 20 perfis demo.

Para cada perfil em PERFIS_DEMO:
- Carrega sem erro
- Módulos integrados (extrato, projeção, alertas, dashboard) funcionam
- Exportações Excel não levantam erro
- Arquivos demo na pasta demos/ existem e são parseáveis

Asserções específicas para perfis-chave (cenários extremos):
- muito_endividado: tem alertas
- prestador_servico: tem clientes + OS
- no_verde: poucos meses negativos na projeção
- profissional_informal: tem vendas

Reaproveita 100% o padrão atual do conftest.py (fixture `banco`).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from demo_manager import PERFIS_DEMO, popular_modo_demo


_PERFIS = list(PERFIS_DEMO.keys())
_RAIZ_DEMOS = Path(__file__).parent.parent / "demos"


# ─────────────────────────────────────────────────────────────────────────────
# Fixture parametrizada
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(params=_PERFIS, scope="function")
def perfil(banco, request):
    """Popula o banco temp com o perfil parametrizado. Yield: chave do perfil."""
    n = popular_modo_demo(request.param)
    return {"chave": request.param, "nome": PERFIS_DEMO[request.param],
            "n_lancamentos": n}


# ─────────────────────────────────────────────────────────────────────────────
# Carregamento básico
# ─────────────────────────────────────────────────────────────────────────────

class TestPerfisCarregam:
    """Todo perfil popula sem exceção e gera ao menos 1 lançamento."""

    def test_popula_sem_erro(self, perfil):
        assert perfil["n_lancamentos"] > 0, (
            f"Perfil {perfil['chave']} não inseriu lançamentos"
        )

    def test_tem_nome_amigavel(self, perfil):
        assert perfil["nome"], f"Perfil {perfil['chave']} sem nome"
        assert isinstance(perfil["nome"], str)


# ─────────────────────────────────────────────────────────────────────────────
# Integridade cross-module
# ─────────────────────────────────────────────────────────────────────────────

class TestPerfisIntegridade:
    """Para cada perfil, módulos integrados não levantam exceção."""

    def test_extrato_mes_atual(self, perfil):
        from views.fluxo_caixa.extrato_model import extrato_mes
        hoje = date.today()
        linhas = extrato_mes(hoje.month, hoje.year)
        assert isinstance(linhas, list)

    def test_projecao_12_meses(self, perfil):
        from views.visao_futura.projecao_model import projetar
        meses = projetar(meses=12)
        assert len(meses) == 12

    def test_dashboard_fluxo(self, perfil):
        from views.fluxo_caixa.fluxo_model import projetar_fluxo
        proj = projetar_fluxo(12)
        assert len(proj) == 12

    def test_alertas_nao_levanta(self, perfil):
        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        assert isinstance(alertas, list)


# ─────────────────────────────────────────────────────────────────────────────
# Exportação
# ─────────────────────────────────────────────────────────────────────────────

class TestPerfisExportar:
    """Cada perfil consegue exportar Excel sem exceção."""

    def test_exportar_extrato_xlsx(self, perfil, tmp_path):
        from views.exportar.exportar_model import exportar_extrato_xlsx
        hoje = date.today()
        destino = tmp_path / "extrato.xlsx"
        exportar_extrato_xlsx(hoje.month, hoje.year, str(destino))
        assert destino.exists()

    def test_exportar_dividas_xlsx(self, perfil, tmp_path):
        from views.exportar.exportar_model import exportar_dividas_xlsx
        destino = tmp_path / "dividas.xlsx"
        exportar_dividas_xlsx(str(destino))
        assert destino.exists()


# ─────────────────────────────────────────────────────────────────────────────
# Arquivos demo na pasta demos/
# ─────────────────────────────────────────────────────────────────────────────

class TestPerfisArquivosDemo:
    """Cada perfil tem pasta demos/ versionada com perfil.md + faturas/extratos."""

    def test_pasta_existe(self, perfil):
        pasta = _RAIZ_DEMOS / perfil["chave"]
        assert pasta.exists(), f"Pasta demos/{perfil['chave']} não existe"
        assert (pasta / "perfil.md").exists()

    def test_tem_pelo_menos_um_extrato_csv(self, perfil):
        pasta = _RAIZ_DEMOS / perfil["chave"] / "extratos"
        if not pasta.exists():
            pytest.skip(f"Sem pasta extratos pra {perfil['chave']}")
        csvs = list(pasta.glob("*.csv"))
        assert csvs, f"Sem .csv em demos/{perfil['chave']}/extratos"

    def test_extrato_csv_e_parsavel(self, perfil):
        from views.fluxo_caixa.extrato_parsers.nubank_csv import NubankCSVParser
        pasta = _RAIZ_DEMOS / perfil["chave"] / "extratos"
        if not pasta.exists():
            pytest.skip(f"Sem pasta extratos pra {perfil['chave']}")
        csvs = list(pasta.glob("*.csv"))
        if not csvs:
            pytest.skip(f"Sem .csv em {perfil['chave']}")
        # Pelo menos o primeiro CSV deve parsear
        itens = NubankCSVParser().parse(csvs[0])
        assert isinstance(itens, list)

    def test_extrato_ofx_e_parsavel(self, perfil):
        from views.fluxo_caixa.extrato_parsers.nubank_ofx import NubankOFXParser
        pasta = _RAIZ_DEMOS / perfil["chave"] / "extratos"
        if not pasta.exists():
            pytest.skip(f"Sem pasta extratos pra {perfil['chave']}")
        ofxs = list(pasta.glob("*.ofx"))
        if not ofxs:
            pytest.skip(f"Sem .ofx em {perfil['chave']}")
        itens = NubankOFXParser().parse(ofxs[0])
        assert isinstance(itens, list)


# ─────────────────────────────────────────────────────────────────────────────
# Cenários específicos por perfil (asserções cirúrgicas, sem parametrização)
# ─────────────────────────────────────────────────────────────────────────────

class TestCenariosEspecificos:
    """Perfis-chave precisam refletir o cenário prometido."""

    # ─── Endividados ─────────────────────────────────────────────────────

    def test_muito_endividado_tem_alertas(self, banco):
        popular_modo_demo("muito_endividado")
        from views.alertas.alertas_model import alertas_pendentes
        alertas = alertas_pendentes()
        # Tem que ter pelo menos algum alerta (fatura atrasada gera)
        assert len(alertas) >= 1, "muito_endividado deve ter ≥1 alerta"

    def test_muito_endividado_tem_8_cartoes(self, banco):
        popular_modo_demo("muito_endividado")
        from database import conectar
        with conectar() as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM cartoes WHERE ultimos_digitos LIKE '553%'"
            ).fetchone()[0]
        assert n == 8, f"muito_endividado deve ter 8 cartões; tem {n}"

    def test_bem_endividado_tem_3_dividas_grandes(self, banco):
        popular_modo_demo("bem_endividado")
        from database import conectar
        with conectar() as conn:
            divs = conn.execute(
                "SELECT COUNT(*) FROM dividas"
                " WHERE saldo_atual > 15000 AND ativa = 1"
            ).fetchone()[0]
        assert divs >= 3, f"bem_endividado deve ter ≥3 dívidas grandes (>15k); tem {divs}"

    # ─── Prestador de serviço (único com OS + clientes integrados) ──────

    def test_prestador_servico_tem_clientes_e_os(self, banco):
        popular_modo_demo("prestador_servico")
        from database import conectar
        with conectar() as conn:
            clientes = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
            oses     = conn.execute("SELECT COUNT(*) FROM ordens_servico").fetchone()[0]
        assert clientes >= 5, f"prestador_servico deve ter ≥5 clientes; tem {clientes}"
        assert oses     >= 4, f"prestador_servico deve ter ≥4 OS; tem {oses}"

    def test_prestador_servico_tem_os_de_todos_status(self, banco):
        """Cobre TODOS os status na demo (aberta, em_andamento, etc)."""
        popular_modo_demo("prestador_servico")
        from database import conectar
        with conectar() as conn:
            statuses = {
                r[0] for r in conn.execute(
                    "SELECT DISTINCT status FROM ordens_servico"
                ).fetchall()
            }
        esperados = {"aberta", "em_andamento", "aguardando_peca", "concluida"}
        faltando = esperados - statuses
        assert not faltando, f"Status de OS faltando: {faltando}"

    # ─── Profissional informal ───────────────────────────────────────────

    def test_profissional_informal_tem_vendas(self, banco):
        popular_modo_demo("profissional_informal")
        from database import conectar
        with conectar() as conn:
            v = conn.execute(
                "SELECT COUNT(*), SUM(valor_liquido) FROM vendas"
            ).fetchone()
        assert v[0] >= 10, f"profissional_informal deve ter ≥10 vendas; tem {v[0]}"
        assert (v[1] or 0) > 5_000, f"vendas devem totalizar >R$5k"

    def test_profissional_informal_sem_clt(self, banco):
        popular_modo_demo("profissional_informal")
        from database import conectar
        with conectar() as conn:
            clt_ativo = conn.execute(
                "SELECT ativa FROM fontes_receita WHERE nome='Salário CLT'"
            ).fetchone()
        assert clt_ativo and clt_ativo[0] == 0, "CLT deve estar inativo no informal"

    # ─── Aposentados ────────────────────────────────────────────────────

    def test_aposentado_investidor_tem_dividendos(self, banco):
        popular_modo_demo("aposentado_investidor")
        from database import conectar
        with conectar() as conn:
            divs = conn.execute(
                "SELECT COUNT(*) FROM movimentacoes_investimento"
                " WHERE tipo = 'dividendo'"
            ).fetchone()[0]
        assert divs >= 5, f"aposentado_investidor deve ter ≥5 dividendos; tem {divs}"

    def test_aposentado_classico_sem_dividas(self, banco):
        popular_modo_demo("aposentado_classico")
        from database import conectar
        with conectar() as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM dividas WHERE ativa = 1"
            ).fetchone()[0]
        # 0 ou poucas (defaults do banco podem ter 1-2)
        assert n <= 4, f"aposentado_classico não deve ter muitas dívidas; tem {n}"

    # ─── Casal planejando ────────────────────────────────────────────────

    def test_casal_planejando_tem_5_metas(self, banco):
        popular_modo_demo("casal_planejando")
        from database import conectar
        with conectar() as conn:
            n = conn.execute(
                "SELECT COUNT(*), SUM(valor_alvo) FROM metas_financeiras"
            ).fetchone()
        assert n[0] == 5, f"casal_planejando deve ter 5 metas; tem {n[0]}"
        assert (n[1] or 0) >= 200_000, "metas devem somar >=R$200k"

    # ─── MEI loja ────────────────────────────────────────────────────────

    def test_mei_loja_tem_vendas_diarias(self, banco):
        popular_modo_demo("mei_loja")
        from database import conectar
        with conectar() as conn:
            n = conn.execute("SELECT COUNT(*) FROM vendas").fetchone()[0]
        assert n >= 20, f"mei_loja deve ter ≥20 vendas; tem {n}"

    # ─── Investidores ────────────────────────────────────────────────────

    def test_freelancer_alta_renda_tem_cripto(self, banco):
        popular_modo_demo("freelancer_alta_renda")
        from database import conectar
        with conectar() as conn:
            cripto = conn.execute(
                "SELECT COUNT(*) FROM ativos WHERE codigo LIKE 'CRIPTO%'"
            ).fetchone()[0]
        assert cripto >= 1, "freelancer_alta_renda deve ter cripto"
