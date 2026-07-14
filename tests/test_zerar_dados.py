"""
test_zerar_dados.py — Garante que zerar_dados() apaga TODAS as tabelas de
dados do usuário, inclusive as adicionadas depois da função (metas,
lançamentos manuais, conciliação bancária e agenda).

Bug corrigido: zerar_dados() não apagava lancamentos_banco /
lancamentos_manuais / regras_categoria — como elas referenciam
plano_contas / fontes_receita / contas_pagar e conectar() liga
PRAGMA foreign_keys=ON, o DELETE das tabelas-pai estourava
IntegrityError e o "Zerar sistema" falhava inteiro.
"""

from datetime import datetime

import pytest

from database import conectar, zerar_dados


AGORA = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _popular_tabelas_novas(conn):
    """Insere 1 registro em cada tabela nova, com FKs reais preenchidas."""
    plano_id = conn.execute(
        "SELECT id FROM plano_contas LIMIT 1"
    ).fetchone()[0]
    fonte_id = conn.execute(
        "SELECT id FROM fontes_receita LIMIT 1"
    ).fetchone()[0]
    cp = conn.execute(
        "INSERT INTO contas_pagar (plano_conta_id, descricao, valor,"
        " data_vencimento, criado_em) VALUES (?,?,?,?,?)",
        (plano_id, "Conta teste", 100.0, "2026-07-10", AGORA),
    )
    conta_pagar_id = cp.lastrowid

    conn.execute(
        "INSERT INTO metas_financeiras (nome, valor_alvo, criado_em)"
        " VALUES (?,?,?)", ("Meta teste", 1000.0, AGORA),
    )
    conn.execute(
        "INSERT INTO lancamentos_manuais (data, descricao, tipo,"
        " plano_conta_id, valor, criado_em) VALUES (?,?,?,?,?,?)",
        ("2026-07-01", "Saída avulsa", "saida", plano_id, 50.0, AGORA),
    )
    cb = conn.execute(
        "INSERT INTO contas_banco (nome, banco, criado_em) VALUES (?,?,?)",
        ("Conta corrente teste", "Banco Teste", AGORA),
    )
    conn.execute(
        "INSERT INTO lancamentos_banco (conta_banco_id, data, descricao,"
        " valor, identificador_unico, plano_conta_id, conta_pagar_id,"
        " importado_em) VALUES (?,?,?,?,?,?,?,?)",
        (cb.lastrowid, "2026-07-02", "Débito teste", -80.0,
         "uid-teste-1", plano_id, conta_pagar_id, AGORA),
    )
    conn.execute(
        "INSERT INTO regras_categoria (padrao, tipo, fonte_receita_id,"
        " criado_em) VALUES (?,?,?,?)", ("PIX RECEB", "entrada", fonte_id, AGORA),
    )
    conn.execute(
        "INSERT INTO agenda_eventos (titulo, data, criado_em)"
        " VALUES (?,?,?)", ("Renovar CNH", "2026-08-01", AGORA),
    )


TABELAS_NOVAS = [
    "metas_financeiras",
    "lancamentos_manuais",
    "contas_banco",
    "lancamentos_banco",
    "regras_categoria",
    "agenda_eventos",
]


class TestZerarDadosTabelasNovas:
    def test_zerar_nao_estoura_com_fk_preenchida(self, banco):
        """Com lançamentos categorizados/vinculados, zerar_dados não pode falhar."""
        with conectar() as conn:
            _popular_tabelas_novas(conn)
        zerar_dados()  # não deve levantar IntegrityError

    @pytest.mark.parametrize("tabela", TABELAS_NOVAS)
    def test_zerar_apaga_tabela(self, banco, tabela):
        with conectar() as conn:
            _popular_tabelas_novas(conn)
        zerar_dados()
        with conectar() as conn:
            n = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        assert n == 0, f"zerar_dados() deixou registros em {tabela}"
