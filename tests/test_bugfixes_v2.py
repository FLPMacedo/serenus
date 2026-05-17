"""
test_bugfixes_v2.py — Testes de regressão para bugs encontrados na auditoria v2.

Cada classe corresponde a um bug específico identificado durante a verificação
de integridade. Os testes garantem que o comportamento corrigido permaneça
estável em futuras alterações.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from database import conectar


# ─────────────────────────────────────────────────────────────────────────────
# BUG 1 — Dupla contagem de parcelas de cartão em projecao_model
# ─────────────────────────────────────────────────────────────────────────────

class TestProjecaoCartaoSemDuplaContagem:
    """`projetar()` não pode somar a mesma parcela em `desp_variaveis` e em
    `parcelas_cartao` simultaneamente. Antes do fix, `salvar_compra_com_parcelas`
    inseria a parcela em `contas_pagar` (com plano categoria="Cartão de Crédito")
    e também em `parcelas_cartao`, fazendo o `total_saidas` da Visão Futura
    contar tudo em dobro."""

    def _criar_cartao(self) -> int:
        from views.cartoes.cartao_model import salvar_cartao
        return salvar_cartao({
            "nome": "Cartão Teste",
            "banco": "nubank",
            "bandeira": "visa",
            "limite": 5000.0,
            "limite_disponivel": 5000.0,
            "dia_vencimento": 10,
            "dia_fechamento": 1,
        })

    def test_compra_cartao_nao_duplica_no_total_saidas(self, banco):
        """Invariante: o valor da parcela deve aparecer em `parcelas_cartao`
        e NÃO em `desp_variaveis`. A diferença entre `total_saidas` antes e
        depois da compra deve ser exatamente o valor da parcela (sem dobrar)."""
        from views.cartoes.cartao_model import salvar_compra_com_parcelas
        from views.visao_futura.projecao_model import projetar

        cartao_id = self._criar_cartao()
        hoje = date.today()

        # Linha-base ANTES de criar a compra
        antes = {m.indice: m for m in projetar(meses=3, inicio_offset=0)}

        salvar_compra_com_parcelas({
            "cartao_id": cartao_id,
            "descricao": "Smartphone",
            "valor_total": 1200.0,
            "total_parcelas": 3,
            "mes_inicio": f"{hoje.year:04d}-{hoje.month:02d}",
            "categoria": "Pessoal",
            "estabelecimento": "Loja X",
        })

        depois = projetar(meses=3, inicio_offset=0)
        for mes in depois[:3]:
            base = antes[mes.indice]
            # Variáveis NÃO podem crescer (a compra é cartão)
            assert mes.desp_variaveis == pytest.approx(base.desp_variaveis, abs=0.01), \
                f"Dupla contagem em {mes.label}: variaveis subiu de "\
                f"{base.desp_variaveis} → {mes.desp_variaveis}"
            # parcelas_cartao deve ter subido R$ 400
            assert mes.parcelas_cartao - base.parcelas_cartao == \
                pytest.approx(400.0, abs=0.01), \
                f"Parcela do cartão não registrada em {mes.label}"
            # total_saidas deve subir exatamente R$ 400 (uma vez, não duas)
            assert mes.total_saidas - base.total_saidas == \
                pytest.approx(400.0, abs=0.01), \
                f"Total de saídas duplicado em {mes.label}: "\
                f"delta={mes.total_saidas - base.total_saidas}"

    def test_carregar_detalhes_nao_repete_compra_de_cartao(self, banco):
        from views.cartoes.cartao_model import salvar_compra_com_parcelas
        from views.visao_futura.projecao_model import projetar, carregar_detalhes

        cartao_id = self._criar_cartao()
        hoje = date.today()
        salvar_compra_com_parcelas({
            "cartao_id": cartao_id,
            "descricao": "TV",
            "valor_total": 600.0,
            "total_parcelas": 2,
            "mes_inicio": f"{hoje.year:04d}-{hoje.month:02d}",
            "categoria": "",
            "estabelecimento": "",
        })

        proj = projetar(meses=2, inicio_offset=0)
        det = carregar_detalhes(proj)

        # Deve aparecer SOMENTE em parcelas_cartao, jamais em desp_variaveis
        assert any("TV" in k or "Cartão" in k for k in det.parcelas_cartao.keys()), \
            "Compra não apareceu nas parcelas de cartão"
        for nome in det.desp_variaveis.keys():
            assert "Cartão" not in nome, \
                f"Despesa de cartão duplicada em variáveis: {nome}"


# ─────────────────────────────────────────────────────────────────────────────
# BUG 2 — parsear_data aceita datas inválidas
# ─────────────────────────────────────────────────────────────────────────────

class TestParsearDataInvalida:
    """`parsear_data` agora retorna string vazia para datas impossíveis em vez
    de gerar string ISO inválida que crasharia ao reler com date.fromisoformat."""

    def test_data_valida_converte_para_iso(self):
        from config import parsear_data
        assert parsear_data("25/12/2025") == "2025-12-25"
        assert parsear_data("01/01/2024") == "2024-01-01"

    def test_dia_31_em_fevereiro_invalido(self):
        from config import parsear_data
        assert parsear_data("31/02/2025") == ""

    def test_dia_inexistente_em_abril(self):
        from config import parsear_data
        assert parsear_data("31/04/2025") == ""

    def test_mes_zero_invalido(self):
        from config import parsear_data
        assert parsear_data("15/00/2025") == ""

    def test_mes_13_invalido(self):
        from config import parsear_data
        assert parsear_data("15/13/2025") == ""

    def test_texto_nao_numerico_retorna_vazio(self):
        from config import parsear_data
        assert parsear_data("abc") == ""
        assert parsear_data("01/abc/2025") == ""

    def test_string_vazia_retorna_vazio(self):
        from config import parsear_data
        assert parsear_data("") == ""
        assert parsear_data(None) == ""  # type: ignore[arg-type]

    def test_data_iso_invalida_nao_quebra_alertas(self, banco):
        """Antes do fix: salvar venda com "31/02/2025" gravaria string inválida
        e _contas_pagar crasharia em date.fromisoformat."""
        from config import parsear_data
        venc = parsear_data("31/02/2025")
        # Garante que callers não vão usar isso como data
        assert not venc


# ─────────────────────────────────────────────────────────────────────────────
# BUG 3 — _parse_valor zera valores com prefixo "R$ "
# ─────────────────────────────────────────────────────────────────────────────

class TestParseValorComPrefixo:
    """Quando o usuário exporta a fatura do banco em CSV/XLSX, o valor pode
    vir como "R$ 100,00" ou "R$ 1.234,56". Antes do fix, o `float()` jogava
    ValueError e o valor era silenciosamente convertido a 0.0."""

    def test_prefixo_real_com_decimal_br(self):
        from views.cartoes.importar_fatura_model import _parse_valor
        assert _parse_valor("R$ 100,00") == 100.00
        assert _parse_valor("R$ 1.234,56") == 1234.56

    def test_sem_prefixo_continua_funcionando(self):
        from views.cartoes.importar_fatura_model import _parse_valor
        assert _parse_valor("199,90") == 199.90
        assert _parse_valor("199.90") == 199.90
        assert _parse_valor("1.234,56") == 1234.56

    def test_numero_puro(self):
        from views.cartoes.importar_fatura_model import _parse_valor
        assert _parse_valor(100) == 100.0
        assert _parse_valor(99.99) == 99.99

    def test_string_vazia_ou_lixo_retorna_zero(self):
        from views.cartoes.importar_fatura_model import _parse_valor
        assert _parse_valor("") == 0.0
        assert _parse_valor("abc") == 0.0
        assert _parse_valor(None) == 0.0

    def test_csv_com_prefixo_real_importa_corretamente(self, tmp_path, banco):
        """Cenário de regressão: CSV exportado com valores 'R$' não pode zerar."""
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura

        csv_file = tmp_path / "fatura.csv"
        csv_file.write_text(
            "descricao,estabelecimento,categoria,parcela,valor\n"
            "Netflix,Netflix,Lazer,1/1,\"R$ 39,90\"\n"
            "Mercado,Pão,Alimentação,1/1,\"R$ 1.234,56\"\n",
            encoding="utf-8",
        )
        linhas = ler_arquivo_fatura(str(csv_file))
        assert len(linhas) == 2
        assert linhas[0]["valor"] == 39.90
        assert linhas[1]["valor"] == 1234.56


# ─────────────────────────────────────────────────────────────────────────────
# BUG 4 — _faturas_cartao inclui cartões inativos
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertaFaturaSomenteCartoesAtivos:
    """Cartão arquivado (ativo=0) com parcelas pendentes não pode gerar alerta
    de fatura — polui a tela do usuário sem que ele possa agir."""

    def test_cartao_inativo_nao_gera_alerta_de_fatura(self, banco):
        from views.cartoes.cartao_model import (
            salvar_cartao, salvar_compra_com_parcelas, alternar_ativo_cartao,
        )
        from views.alertas.alertas_model import alertas_pendentes

        cartao_id = salvar_cartao({
            "nome": "Antigo",
            "banco": "outro",
            "bandeira": "visa",
            "limite": 1000.0,
            "limite_disponivel": 1000.0,
            "dia_vencimento": 5,
            "dia_fechamento": 1,
        })
        hoje = date.today()
        salvar_compra_com_parcelas({
            "cartao_id": cartao_id,
            "descricao": "Compra antiga",
            "valor_total": 300.0,
            "total_parcelas": 3,
            "mes_inicio": f"{hoje.year:04d}-{hoje.month:02d}",
        })

        # Antes de desativar: deve ter alerta de fatura
        alertas_antes = [a for a in alertas_pendentes() if a.tipo == "fatura_cartao"]
        assert len(alertas_antes) == 1

        # Desativa o cartão
        alternar_ativo_cartao(cartao_id, False)

        # Após desativar: alerta deve sumir
        alertas_depois = [a for a in alertas_pendentes() if a.tipo == "fatura_cartao"]
        assert len(alertas_depois) == 0


# ─────────────────────────────────────────────────────────────────────────────
# BUG 5 — marcar_recebido ressuscitava parcelas canceladas
# ─────────────────────────────────────────────────────────────────────────────

class TestMarcarRecebidoIdempotente:
    """`marcar_recebido` não pode alterar parcelas com status diferente de
    'pendente'. Antes do fix, uma parcela cancelada poderia ser convertida em
    'recebido' silenciosamente — gerando crédito fantasma no extrato."""

    def _criar_venda_aprazo(self) -> int:
        from views.vendas.venda_model import salvar_venda
        hoje = date.today().isoformat()
        return salvar_venda(
            {
                "descricao": "Serviço X",
                "data_venda": hoje,
                "tipo_pagamento": "aprazo",
                "parcelas": 2,
                "data_primeira_parcela": hoje,
            },
            [{"descricao": "Serviço X", "quantidade": 1, "preco_unit": 200.0}],
        )

    def test_recebido_duas_vezes_nao_muda_data_recebimento(self, banco):
        from views.vendas.venda_model import (
            marcar_recebido, listar_contas_receber,
        )
        self._criar_venda_aprazo()
        parc_id = listar_contas_receber()[0].id

        marcar_recebido(parc_id, "2026-01-15")
        marcar_recebido(parc_id, "2026-12-31")  # segunda chamada — deve ser no-op

        parc = next(p for p in listar_contas_receber() if p.id == parc_id)
        assert parc.status == "recebido"
        assert parc.data_recebimento == "2026-01-15", \
            "Segunda chamada sobrescreveu a data de recebimento original"

    def test_parcela_cancelada_nao_pode_virar_recebida(self, banco):
        from views.vendas.venda_model import (
            marcar_recebido, listar_contas_receber, cancelar_venda,
        )
        venda_id = self._criar_venda_aprazo()
        parcelas = listar_contas_receber()
        parc_id = parcelas[0].id

        cancelar_venda(venda_id)
        marcar_recebido(parc_id, "2026-01-15")  # deve ser no-op

        parc = next(p for p in listar_contas_receber(status="cancelado")
                    if p.id == parc_id)
        assert parc.status == "cancelado"
        assert parc.data_recebimento is None

    def test_status_da_venda_nao_muda_quando_no_op(self, banco):
        from views.vendas.venda_model import (
            marcar_recebido, listar_contas_receber, cancelar_venda, obter_venda,
        )
        venda_id = self._criar_venda_aprazo()
        parc_id = listar_contas_receber()[0].id

        cancelar_venda(venda_id)
        antes = obter_venda(venda_id).status
        marcar_recebido(parc_id, "2026-01-15")
        depois = obter_venda(venda_id).status
        assert antes == depois == "cancelada"


# ─────────────────────────────────────────────────────────────────────────────
# BUG 6 — Vendas não apareciam como "Receita base/mês" no Fluxo de Caixa
# ─────────────────────────────────────────────────────────────────────────────

class TestVendasEntramNoFluxoCaixa:
    """`fluxo_model.projetar_fluxo` e `resumo_fluxo` ignoravam vendas. Quando o
    usuário cadastrava uma venda à vista, ela aparecia no Extrato e na Visão
    Mensal de Receitas, mas o card 'Receita base/mês' do Fluxo de Caixa
    permanecia inalterado — gerando a impressão de que a venda 'não entrou'."""

    def test_venda_avista_aumenta_receita_do_mes_atual(self, banco):
        from views.vendas.venda_model import salvar_venda
        from views.fluxo_caixa.fluxo_model import projetar_fluxo

        hoje_iso = date.today().isoformat()
        antes = projetar_fluxo(meses=1)[0].receita

        salvar_venda(
            {
                "descricao": "Consultoria",
                "data_venda": hoje_iso,
                "tipo_pagamento": "avista",
            },
            [{"descricao": "Consultoria", "quantidade": 1, "preco_unit": 500.0}],
        )

        depois = projetar_fluxo(meses=1)[0].receita
        assert depois - antes == pytest.approx(500.0, abs=0.01), \
            f"Venda à vista não entrou no fluxo: delta={depois - antes}"

    def test_venda_avista_aumenta_receita_base_no_resumo(self, banco):
        from views.vendas.venda_model import salvar_venda
        from views.fluxo_caixa.fluxo_model import projetar_fluxo, resumo_fluxo

        hoje_iso = date.today().isoformat()
        antes = resumo_fluxo(projetar_fluxo(meses=1))["receita_base"]

        salvar_venda(
            {"descricao": "Venda balcão", "data_venda": hoje_iso,
             "tipo_pagamento": "avista"},
            [{"descricao": "Item", "quantidade": 1, "preco_unit": 250.0}],
        )

        depois = resumo_fluxo(projetar_fluxo(meses=1))["receita_base"]
        assert depois - antes == pytest.approx(250.0, abs=0.01), \
            "Card 'Receita base/mês' não somou a venda"

    def test_venda_aprazo_pendente_nao_entra(self, banco):
        """Venda a prazo SEM recebimento NÃO pode aparecer ainda — dinheiro só
        entra no caixa quando a parcela é marcada como recebida."""
        from views.vendas.venda_model import salvar_venda
        from views.fluxo_caixa.fluxo_model import projetar_fluxo

        hoje_iso = date.today().isoformat()
        antes = projetar_fluxo(meses=1)[0].receita

        salvar_venda(
            {
                "descricao": "Serviço futuro",
                "data_venda": hoje_iso,
                "tipo_pagamento": "aprazo",
                "parcelas": 3,
                "data_primeira_parcela": hoje_iso,
            },
            [{"descricao": "Serviço", "quantidade": 1, "preco_unit": 900.0}],
        )

        depois = projetar_fluxo(meses=1)[0].receita
        assert depois == pytest.approx(antes, abs=0.01), \
            "Venda a prazo pendente entrou no caixa indevidamente"

    def test_recebivel_quitado_entra_no_fluxo(self, banco):
        from views.vendas.venda_model import (
            salvar_venda, listar_contas_receber, marcar_recebido,
        )
        from views.fluxo_caixa.fluxo_model import projetar_fluxo

        hoje_iso = date.today().isoformat()
        salvar_venda(
            {
                "descricao": "Parcelado",
                "data_venda": hoje_iso,
                "tipo_pagamento": "aprazo",
                "parcelas": 2,
                "data_primeira_parcela": hoje_iso,
            },
            [{"descricao": "Produto", "quantidade": 1, "preco_unit": 400.0}],
        )
        antes = projetar_fluxo(meses=1)[0].receita

        parc_id = listar_contas_receber(status="pendente")[0].id
        marcar_recebido(parc_id, hoje_iso)

        depois = projetar_fluxo(meses=1)[0].receita
        assert depois - antes == pytest.approx(200.0, abs=0.01), \
            "Recebível quitado não apareceu no fluxo"
