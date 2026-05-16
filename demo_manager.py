"""
demo_manager.py — Dados demonstrativos para o Serenus.
8 perfis financeiros: padrão, apertado, moderado_dividas,
moderado_recuperando, no_verde, primeiro_passo, em_ritmo,
patrimonio_crescendo.
"""
from __future__ import annotations
import random
from datetime import date, datetime

from database import conectar, salvar_configuracao

_RNG = random.Random(42)

PERFIS_DEMO: dict[str, str] = {
    "padrao":               "Padrão (Classe Média)",
    "apertado":             "Apertado (Renda baixa / muitos cartões)",
    "moderado_dividas":     "Moderado entrando em dívidas",
    "moderado_recuperando": "Moderado saindo das dívidas",
    "no_verde":             "No verde (Sobra ~R$500/mês)",
    "primeiro_passo":       "Primeiro Passo (Começando a investir)",
    "em_ritmo":             "Em Ritmo (Investidor há 3 anos)",
    "patrimonio_crescendo": "Patrimônio Crescendo (Carteira consolidada)",
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers comuns
# ──────────────────────────────────────────────────────────────────────────────

def _mes_add(ref: date, n: int) -> tuple[int, int]:
    m = ref.month - 1 + n
    return ref.year + m // 12, m % 12 + 1


def _fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _dia_seguro(ano: int, mes: int, dia: int) -> int:
    import calendar
    return min(dia, calendar.monthrange(ano, mes)[1])


def _inserir_lancamentos(
    conn,
    planos: dict[str, int],
    fixas: list[tuple],     # (nome, valor_base, dia_venc)
    variaveis: list[tuple], # (nome, lo, hi, dia_venc, prob)
    hoje: date,
    rng: random.Random,
    offset_range: range = range(-60, 61),
    fator_fn=None,          # callable(offset) → float multiplicador; None = 1.0
) -> int:
    agora = _agora()
    hoje_mes = date(hoje.year, hoje.month, 1)
    total = 0

    for offset in offset_range:
        ano, mes = _mes_add(hoje, offset)
        alvo = date(ano, mes, 1)
        is_passado = alvo < hoje_mes
        fator = fator_fn(offset) if fator_fn else 1.0

        for nome, val_base, dia_v in fixas:
            pid = planos.get(nome)
            if not pid:
                continue
            valor = round(val_base * fator * rng.uniform(0.98, 1.02), 2)
            dia = _dia_seguro(ano, mes, dia_v)
            venc = _fmt(date(ano, mes, dia))
            if is_passado:
                dpag = _dia_seguro(ano, mes, dia_v + rng.randint(0, 5))
                conn.execute(
                    "INSERT INTO contas_pagar (plano_conta_id, valor, data_vencimento,"
                    " data_pagamento, status, recorrente, criado_em)"
                    " VALUES (?,?,?,?,'pago',1,?)",
                    (pid, valor, venc, _fmt(date(ano, mes, dpag)), agora),
                )
            else:
                conn.execute(
                    "INSERT INTO contas_pagar (plano_conta_id, valor, data_vencimento,"
                    " status, recorrente, criado_em) VALUES (?,?,?,'pendente',1,?)",
                    (pid, valor, venc, agora),
                )
            total += 1

        for item in variaveis:
            nome, lo, hi, dia_v = item[0], item[1], item[2], item[3]
            prob = item[4] if len(item) > 4 else 1.0
            pid = planos.get(nome)
            if not pid:
                continue
            if rng.random() > prob:
                continue
            lo_f = round(lo * fator, 2)
            hi_f = round(hi * fator, 2)
            valor = round(rng.uniform(max(lo_f, 50), max(hi_f, 51)), 2)
            dia = _dia_seguro(ano, mes, dia_v)
            venc = _fmt(date(ano, mes, dia))
            if is_passado:
                dpag = _dia_seguro(ano, mes, dia_v + rng.randint(0, 7))
                conn.execute(
                    "INSERT INTO contas_pagar (plano_conta_id, valor, data_vencimento,"
                    " data_pagamento, status, recorrente, criado_em)"
                    " VALUES (?,?,?,?,'pago',0,?)",
                    (pid, valor, venc, _fmt(date(ano, mes, dpag)), agora),
                )
            else:
                conn.execute(
                    "INSERT INTO contas_pagar (plano_conta_id, valor, data_vencimento,"
                    " status, recorrente, criado_em) VALUES (?,?,?,'pendente',0,?)",
                    (pid, valor, venc, agora),
                )
            total += 1

    return total


def _inserir_cartao(conn, nome, banco, bandeira, digitos, cor_bg, cor_tx,
                    limite, disponivel, dia_venc, dia_fech, agora) -> int:
    cur = conn.execute(
        "INSERT INTO cartoes (nome, banco, bandeira, ultimos_digitos, cor_fundo, cor_texto,"
        " limite, limite_disponivel, dia_vencimento, dia_fechamento, ativo, criado_em)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,1,?)",
        (nome, banco, bandeira, digitos, cor_bg, cor_tx,
         limite, disponivel, dia_venc, dia_fech, agora),
    )
    return cur.lastrowid


def _inserir_compras(conn, compras: list[tuple], hoje: date):
    agora = _agora()
    hoje_mes = date(hoje.year, hoje.month, 1)
    for cid, desc, total_v, n, off_ini in compras:
        ano_i, mes_i = _mes_add(hoje, off_ini)
        mes_inicio = f"{ano_i:04d}-{mes_i:02d}"
        base = round(total_v / n, 2)
        ultima = round(total_v - base * (n - 1), 2)
        cur = conn.execute(
            "INSERT INTO compras_cartao (cartao_id, descricao, valor_total, valor_parcela,"
            " total_parcelas, parcelas_pagas, mes_inicio, categoria, criado_em)"
            " VALUES (?,?,?,?,?,0,?,'Outros',?)",
            (cid, desc, total_v, base, n, mes_inicio, agora),
        )
        compra_id = cur.lastrowid
        for i in range(n):
            ano_p, mes_p = _mes_add(hoje, off_ini + i)
            ref = f"{ano_p:04d}-{mes_p:02d}"
            alvo_p = date(ano_p, mes_p, 1)
            v = ultima if i == n - 1 else base
            st = "pago" if alvo_p < hoje_mes else "pendente"
            conn.execute(
                "INSERT INTO parcelas_cartao (compra_id, cartao_id, numero_parcela,"
                " mes_referencia, valor, status) VALUES (?,?,?,?,?,?)",
                (compra_id, cid, i + 1, ref, v, st),
            )


def _inserir_dividas(conn, dividas: list[tuple]):
    agora = _agora()
    conn.executemany(
        "INSERT INTO dividas (nome, tipo, saldo_atual, parcela_mensal, total_parcelas,"
        " parcelas_pagas, dia_vencimento, taxa_juros, ativa, criado_em)"
        " VALUES (?,?,?,?,?,?,?,?,1,?)",
        [(*d, agora) for d in dividas],
    )


def _inserir_metas(conn, metas: list[tuple]) -> None:
    """Insere metas financeiras.
    Tuple: (nome, valor_alvo, valor_atual, prazo_iso|None, descricao)
    """
    agora = _agora()
    for nome, valor_alvo, valor_atual, prazo, descricao in metas:
        conn.execute(
            "INSERT INTO metas_financeiras"
            " (nome, valor_alvo, valor_atual, prazo, descricao, criado_em)"
            " VALUES (?,?,?,?,?,?)",
            (nome, valor_alvo, valor_atual, prazo, descricao, agora),
        )


def _data_offset_str(ref: date, meses: int, dia: int = 15) -> str:
    """Retorna data ISO para ref + N meses, fixada no dia informado."""
    ano, mes = _mes_add(ref, meses)
    d = _dia_seguro(ano, mes, dia)
    return f"{ano:04d}-{mes:02d}-{d:02d}"


def _inserir_movimentacoes_inv(conn, rng: random.Random, hoje: date,
                                ativo_ids: dict[str, int],
                                movs: list[tuple]) -> None:
    """
    Processa lista de movimentações de investimento.
    Cada tuple: (codigo, tipo, qtd, val, offset_meses)
    Registra automaticamente em contas_pagar os lançamentos históricos de saída.
    """
    from config import MOV_INV_SAIDA
    agora    = _agora()
    hoje_mes = date(hoje.year, hoje.month, 1)

    for codigo, tipo, qtd, val, offset in movs:
        aid = ativo_ids.get(codigo)
        if not aid:
            continue

        data_str = _data_offset_str(hoje, offset)
        data_dt  = date.fromisoformat(data_str)

        conta_row = conn.execute(
            "SELECT conta_investimento_id FROM ativos WHERE id=?", (aid,)
        ).fetchone()
        conta_id = conta_row["conta_investimento_id"] if conta_row else None

        if tipo in ("compra", "venda") and qtd > 0:
            val_bruto  = round(qtd * val, 2)
            preco_unit = val
        else:
            val_bruto  = val
            preco_unit = 0.0
            qtd        = qtd

        taxas = 0.0
        if tipo in ("compra", "venda") and val_bruto > 100:
            taxas = round(rng.uniform(2.0, 8.0), 2)

        if tipo in MOV_INV_SAIDA:
            val_liq = round(val_bruto + taxas, 2)
        else:
            val_liq = round(max(0.0, val_bruto - taxas), 2)

        reg_fin = tipo in MOV_INV_SAIDA and data_dt < hoje_mes
        contas_pagar_id = None

        if reg_fin:
            plano_nome = ("Investimentos — Taxas e Impostos"
                          if tipo in ("taxa", "imposto")
                          else "Investimentos — Aplicação")
            plano_row = conn.execute(
                "SELECT id FROM plano_contas WHERE nome=?", (plano_nome,)
            ).fetchone()
            if plano_row:
                plano_id = plano_row["id"]
            else:
                cur2 = conn.execute(
                    "INSERT INTO plano_contas"
                    " (nome, tipo_custo, categoria, ativa, padrao, criado_em)"
                    " VALUES (?,'variavel','Investimentos',1,0,?)",
                    (plano_nome, agora))
                plano_id = cur2.lastrowid

            cur2 = conn.execute(
                "INSERT INTO contas_pagar"
                " (plano_conta_id, descricao, valor, data_vencimento, data_pagamento,"
                "  status, recorrente, observacao, criado_em)"
                " VALUES (?,?,?,?,?,'pago',0,?,?)",
                (plano_id, f"{tipo.capitalize()} — {codigo}",
                 val_liq, data_str, data_str, "Demo", agora))
            contas_pagar_id = cur2.lastrowid

        conn.execute(
            "INSERT INTO movimentacoes_investimento"
            " (ativo_id, conta_investimento_id, tipo, data, quantidade,"
            "  preco_unitario, valor_bruto, taxas, valor_liquido,"
            "  observacao, registrar_no_financeiro, contas_pagar_id, criado_em)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (aid, conta_id, tipo, data_str, qtd,
             preco_unit, val_bruto, taxas, val_liq,
             "", int(reg_fin), contas_pagar_id, agora))


def _criar_ativos_inv(conn, ativos_def: list[tuple], agora: str) -> dict[str, int]:
    """
    Insere ativos e retorna dict {codigo: ativo_id}.
    Tuple: (codigo, nome, tipo, conta_id, indexador, taxa, vencimento)
    """
    ativo_ids: dict[str, int] = {}
    for codigo, nome, tipo, conta_id, indexador, taxa, venc in ativos_def:
        cur = conn.execute(
            "INSERT INTO ativos"
            " (codigo, nome, tipo, conta_investimento_id,"
            "  indexador, taxa_contratada, vencimento, observacao, ativo, criado_em)"
            " VALUES (?,?,?,?,?,?,?,?,1,?)",
            (codigo, nome, tipo, conta_id, indexador, taxa, venc, "", agora),
        )
        ativo_ids[codigo] = cur.lastrowid
    return ativo_ids


# ──────────────────────────────────────────────────────────────────────────────
# Perfil 1 — Padrão (classe média)
# ──────────────────────────────────────────────────────────────────────────────

def _popular_padrao(conn, planos, rng, hoje) -> int:
    conn.execute("UPDATE fontes_receita SET valor_mensal=8500.0, ativa=1, periodicidade='mensal' WHERE nome='Salário CLT'")
    conn.execute("UPDATE fontes_receita SET valor_mensal=1800.0, ativa=1, periodicidade='mensal' WHERE nome='Freela / Serviço avulso'")
    conn.execute("DELETE FROM receitas_especiais")
    conn.executemany(
        "INSERT INTO receitas_especiais (nome, mes, valor, tipo, recorrente_anual) VALUES (?,?,?,?,1)",
        [("13º Salário", 11, 8_500.00, "clt"), ("Férias + 1/3", 6, 11_333.33, "clt")],
    )

    fixas = [
        ("Aluguel / Financiamento imóvel", 1_800.00, 5),
        ("Internet",                        129.90,  10),
        ("Streaming (Netflix, Spotify…)",    79.90,  10),
        ("Plano de saúde",                  420.00,  15),
        ("Telefone / Celular",               89.90,  10),
        ("Academia",                         99.00,  10),
        ("TV por assinatura",                75.90,  10),
        ("Seguro veículo",                  220.00,  20),
    ]
    variaveis = [
        ("Supermercado",            700,  1_200, 15, 1.0),
        ("Combustível",             350,    600, 20, 1.0),
        ("Restaurantes / Delivery", 200,    480, 20, 1.0),
        ("Farmácia",                 50,    220, 20, 1.0),
        ("Água",                     85,    160, 18, 1.0),
        ("Luz / Energia elétrica",  150,    340, 12, 1.0),
        ("Manutenção veículo",        0,    400, 20, 0.4),
    ]
    total = _inserir_lancamentos(conn, planos, fixas, variaveis, hoje, rng)

    agora = _agora()
    id_nu  = _inserir_cartao(conn, "Nubank Gold",         "nubank", "master", "4532", "#6D28D9", "#FFFFFF", 8_000,  4_200, 1,  22, agora)
    id_it  = _inserir_cartao(conn, "Itaú Visa Platinum",  "itau",   "visa",   "7891", "#EC7000", "#FFFFFF", 12_000, 7_500, 15,  5, agora)

    _inserir_compras(conn, [
        (id_nu, "SmartTV Samsung 55\"",    3_600.0, 12,  -9),
        (id_nu, "Notebook Dell Inspiron",  5_400.0, 18, -14),
        (id_nu, "Reforma do banheiro",     2_400.0, 10,  -5),
        (id_it, "iPhone 15 Pro",           7_200.0, 24, -20),
        (id_it, "Pacote viagem Cancún",    4_200.0,  6,  -3),
        (id_it, "Móveis sala e quarto",    3_600.0, 12,   2),
        (id_nu, "Geladeira Brastemp",      2_800.0,  8,   1),
    ], hoje)

    _inserir_dividas(conn, [
        ("Empréstimo pessoal BB",      "emprestimo",    22_000.0,   980.0, 36, 14, 15, 1.89),
        ("Financiamento Hyundai HB20", "financiamento", 47_000.0, 1_350.0, 48,  8, 10, 1.45),
    ])
    return total


# ──────────────────────────────────────────────────────────────────────────────
# Perfil 2 — Apertado
# ──────────────────────────────────────────────────────────────────────────────

def _popular_apertado(conn, planos, rng, hoje) -> int:
    conn.execute("UPDATE fontes_receita SET valor_mensal=3500.0, ativa=1, periodicidade='mensal' WHERE nome='Salário CLT'")
    conn.execute("UPDATE fontes_receita SET ativa=0 WHERE nome='Freela / Serviço avulso'")
    conn.execute("DELETE FROM receitas_especiais")
    conn.executemany(
        "INSERT INTO receitas_especiais (nome, mes, valor, tipo, recorrente_anual) VALUES (?,?,?,?,1)",
        [("13º Salário", 11, 3_500.00, "clt")],
    )

    fixas = [
        ("Aluguel / Financiamento imóvel",  900.00, 5),
        ("Internet",                         89.90, 10),
        ("Streaming (Netflix, Spotify…)",    39.90, 10),
        ("Plano de saúde",                  180.00, 15),
        ("Telefone / Celular",               79.90, 10),
    ]
    variaveis = [
        ("Supermercado",            600,  900, 15, 1.0),
        ("Combustível",             200,  380, 20, 1.0),
        ("Restaurantes / Delivery",  80,  200, 20, 1.0),
        ("Farmácia",                 30,  150, 20, 1.0),
        ("Água",                     60,  110, 18, 1.0),
        ("Luz / Energia elétrica",   90,  200, 12, 1.0),
    ]
    total = _inserir_lancamentos(conn, planos, fixas, variaveis, hoje, rng)

    agora = _agora()
    cartoes_cfg = [
        ("Nubank",           "nubank", "master", "1111", "#6D28D9", "#FFFFFF", 1_500,   400,  1, 22),
        ("Bradesco Visa",    "bradesco","visa",  "2222", "#CC092F", "#FFFFFF", 2_000,   200, 10,  1),
        ("Santander MC",     "santander","master","3333","#EC0000", "#FFFFFF", 3_000,   600, 15,  5),
        ("Caixa Visa",       "caixa",  "visa",   "4444", "#006BB5", "#FFFFFF", 2_500,   100, 20, 10),
        ("Magazine Luiza",   "magalu", "master", "5555", "#0066CC", "#FFFFFF", 1_800,   300,  5, 26),
        ("Americanas Card",  "americanas","visa", "6666","#CC0000","#FFFFFF",  2_000,   500, 12,  3),
    ]
    ids = []
    for nome, banco, band, dig, cbg, ctx, lim, disp, dv, df in cartoes_cfg:
        ids.append(_inserir_cartao(conn, nome, banco, band, dig, cbg, ctx, lim, disp, dv, df, agora))

    _inserir_compras(conn, [
        (ids[0], "Celular Motorola G",      1_200.0, 10, -8),
        (ids[1], "Eletrodoméstico",           800.0,  8, -4),
        (ids[2], "Curso online",              600.0,  6, -2),
        (ids[3], "Roupa / Calçados",          500.0,  5, -1),
        (ids[4], "TV 43\" LG",               1_500.0, 12, -6),
        (ids[5], "Material escolar",           400.0,  4, -3),
    ], hoje)

    _inserir_dividas(conn, [
        ("Empréstimo Nubank",      "emprestimo",  8_000.0,  430.0, 24, 6,  5, 2.99),
        ("Cheque especial Bradesco","emprestimo", 3_500.0,  300.0, 18, 2, 10, 3.50),
        ("Financiamento celular",  "financiamento",1_200.0, 120.0, 10, 0, 15, 1.99),
    ])
    return total


# ──────────────────────────────────────────────────────────────────────────────
# Perfil 3 — Moderado entrando em dívidas
# ──────────────────────────────────────────────────────────────────────────────

def _popular_moderado_dividas(conn, planos, rng, hoje) -> int:
    conn.execute("UPDATE fontes_receita SET valor_mensal=6500.0, ativa=1, periodicidade='mensal' WHERE nome='Salário CLT'")
    conn.execute("UPDATE fontes_receita SET valor_mensal=800.0, ativa=1, periodicidade='mensal' WHERE nome='Freela / Serviço avulso'")
    conn.execute("DELETE FROM receitas_especiais")
    conn.executemany(
        "INSERT INTO receitas_especiais (nome, mes, valor, tipo, recorrente_anual) VALUES (?,?,?,?,1)",
        [("13º Salário", 11, 6_500.00, "clt"), ("Férias + 1/3", 6, 8_666.67, "clt")],
    )

    fixas = [
        ("Aluguel / Financiamento imóvel", 1_400.00, 5),
        ("Internet",                         109.90, 10),
        ("Streaming (Netflix, Spotify…)",     59.90, 10),
        ("Plano de saúde",                   280.00, 15),
        ("Telefone / Celular",                89.90, 10),
        ("Academia",                          79.00, 10),
        ("Seguro veículo",                   180.00, 20),
    ]

    # Despesas crescem ~1% ao mês (piora gradual)
    def fator_crescente(offset: int) -> float:
        return max(0.85, 1.0 + offset * 0.01)

    variaveis = [
        ("Supermercado",            600,  1_000, 15, 1.0),
        ("Combustível",             300,    520, 20, 1.0),
        ("Restaurantes / Delivery", 200,    500, 20, 1.0),
        ("Farmácia",                 50,    180, 20, 1.0),
        ("Água",                     70,    130, 18, 1.0),
        ("Luz / Energia elétrica",  120,    280, 12, 1.0),
        ("Manutenção veículo",         0,   500, 20, 0.5),
    ]
    total = _inserir_lancamentos(conn, planos, fixas, variaveis, hoje, rng,
                                  fator_fn=fator_crescente)

    agora = _agora()
    id_nu = _inserir_cartao(conn, "Nubank Platinum", "nubank", "master", "9012",
                             "#6D28D9", "#FFFFFF", 10_000, 2_000, 1, 22, agora)
    id_it = _inserir_cartao(conn, "Itaú MC Gold",    "itau",   "master", "3456",
                             "#EC7000", "#FFFFFF",  8_000, 1_500, 15,  5, agora)

    _inserir_compras(conn, [
        (id_nu, "MacBook Air",         6_000.0, 18,  -8),
        (id_nu, "Ar-condicionado",     3_200.0, 12,  -4),
        (id_it, "Viagem Europa",       8_500.0, 24, -12),
        (id_it, "Reforma cozinha",     4_000.0, 10,  -2),
        (id_nu, "iPhone 14",           5_000.0, 18,   0),
        (id_it, "Moto Honda CB",      12_000.0, 36,   3),
    ], hoje)

    _inserir_dividas(conn, [
        ("Empréstimo pessoal CEF",    "emprestimo",    18_000.0,  850.0, 30, 5, 10, 2.10),
        ("Financiamento Honda Civic", "financiamento", 60_000.0, 1_800.0, 48, 3, 20, 1.55),
    ])
    return total


# ──────────────────────────────────────────────────────────────────────────────
# Perfil 4 — Moderado saindo das dívidas
# ──────────────────────────────────────────────────────────────────────────────

def _popular_moderado_recuperando(conn, planos, rng, hoje) -> int:
    conn.execute("UPDATE fontes_receita SET valor_mensal=7200.0, ativa=1, periodicidade='mensal' WHERE nome='Salário CLT'")
    conn.execute("UPDATE fontes_receita SET valor_mensal=1200.0, ativa=1, periodicidade='mensal' WHERE nome='Freela / Serviço avulso'")
    conn.execute("DELETE FROM receitas_especiais")
    conn.executemany(
        "INSERT INTO receitas_especiais (nome, mes, valor, tipo, recorrente_anual) VALUES (?,?,?,?,1)",
        [("13º Salário", 11, 7_200.00, "clt"), ("Férias + 1/3", 6, 9_600.00, "clt")],
    )

    fixas = [
        ("Aluguel / Financiamento imóvel", 1_500.00, 5),
        ("Internet",                         119.90, 10),
        ("Streaming (Netflix, Spotify…)",     49.90, 10),
        ("Plano de saúde",                   310.00, 15),
        ("Telefone / Celular",                89.90, 10),
        ("Academia",                          89.00, 10),
    ]

    # Despesas decrescem ~0.7% ao mês (melhora gradual do passado para o futuro)
    def fator_decrescente(offset: int) -> float:
        return max(0.70, 1.0 - offset * 0.007)

    variaveis = [
        ("Supermercado",            550,  900, 15, 1.0),
        ("Combustível",             280,  450, 20, 1.0),
        ("Restaurantes / Delivery", 120,  350, 20, 1.0),
        ("Farmácia",                 40,  150, 20, 1.0),
        ("Água",                     70,  120, 18, 1.0),
        ("Luz / Energia elétrica",  110,  240, 12, 1.0),
        ("Manutenção veículo",         0,  300, 20, 0.3),
    ]
    total = _inserir_lancamentos(conn, planos, fixas, variaveis, hoje, rng,
                                  fator_fn=fator_decrescente)

    agora = _agora()
    id_nu = _inserir_cartao(conn, "Nubank",       "nubank", "master", "1234",
                             "#6D28D9", "#FFFFFF", 6_000, 3_500, 1, 22, agora)
    id_bb = _inserir_cartao(conn, "BB Visa Gold", "bb",     "visa",   "5678",
                             "#FFCC00", "#003300", 5_000, 2_800, 10,  1, agora)

    _inserir_compras(conn, [
        (id_nu, "Notebook usado",    1_800.0,  9, -18),
        (id_bb, "TV 50\" Samsung",   2_500.0, 10, -22),
        (id_nu, "Celular Samsung",   2_000.0, 12,  -6),
    ], hoje)

    # Dívidas já bastante pagas — poucas parcelas restantes
    _inserir_dividas(conn, [
        ("Empréstimo BB (quitando)",   "emprestimo",    5_000.0,  700.0, 30, 23, 15, 1.79),
        ("Financ. Volkswagen Gol",     "financiamento", 14_000.0, 650.0, 36, 24, 10, 1.35),
    ])
    return total


# ──────────────────────────────────────────────────────────────────────────────
# Perfil 5 — No verde
# ──────────────────────────────────────────────────────────────────────────────

def _popular_no_verde(conn, planos, rng, hoje) -> int:
    conn.execute("UPDATE fontes_receita SET valor_mensal=7000.0, ativa=1, periodicidade='mensal' WHERE nome='Salário CLT'")
    conn.execute("UPDATE fontes_receita SET valor_mensal=600.0,  ativa=1, periodicidade='bimestral' WHERE nome='Freela / Serviço avulso'")
    conn.execute("DELETE FROM receitas_especiais")
    conn.executemany(
        "INSERT INTO receitas_especiais (nome, mes, valor, tipo, recorrente_anual) VALUES (?,?,?,?,1)",
        [("13º Salário", 11, 7_000.00, "clt"), ("Férias + 1/3", 6, 9_333.33, "clt")],
    )

    fixas = [
        ("Aluguel / Financiamento imóvel", 1_350.00, 5),
        ("Internet",                         109.90, 10),
        ("Streaming (Netflix, Spotify…)",     49.90, 10),
        ("Plano de saúde",                   290.00, 15),
        ("Telefone / Celular",                79.90, 10),
        ("Academia",                          79.00, 10),
    ]
    variaveis = [
        ("Supermercado",            480,  750, 15, 1.0),
        ("Combustível",             250,  400, 20, 1.0),
        ("Restaurantes / Delivery", 100,  280, 20, 1.0),
        ("Farmácia",                 30,  120, 20, 1.0),
        ("Água",                     65,  110, 18, 1.0),
        ("Luz / Energia elétrica",  100,  210, 12, 1.0),
        ("Manutenção veículo",         0,  250, 20, 0.25),
    ]
    total = _inserir_lancamentos(conn, planos, fixas, variaveis, hoje, rng)

    agora = _agora()
    id_nu = _inserir_cartao(conn, "Nubank Ultravioleta", "nubank", "master", "0001",
                             "#6D28D9", "#FFFFFF", 12_000, 9_500, 1, 22, agora)

    _inserir_compras(conn, [
        (id_nu, "Notebook Lenovo",   3_200.0, 10, -14),
        (id_nu, "Câmera Sony",       2_800.0,  8,  -6),
        (id_nu, "Bicicleta Trek",    1_600.0,  6,  -2),
    ], hoje)

    # Sem dívidas ativas relevantes
    _inserir_dividas(conn, [
        ("Financ. apartamento (2 parcelas)", "financiamento", 1_800.0, 900.0, 24, 22, 5, 0.80),
    ])
    return total


# ──────────────────────────────────────────────────────────────────────────────
# Perfil 6 — Primeiro Passo (Começando a investir)
# ──────────────────────────────────────────────────────────────────────────────

def _popular_primeiro_passo(conn, planos, rng, hoje) -> int:
    conn.execute("UPDATE fontes_receita SET valor_mensal=5500.0, ativa=1, periodicidade='mensal' WHERE nome='Salário CLT'")
    conn.execute("UPDATE fontes_receita SET ativa=0 WHERE nome='Freela / Serviço avulso'")
    conn.execute("DELETE FROM receitas_especiais")
    conn.executemany(
        "INSERT INTO receitas_especiais (nome, mes, valor, tipo, recorrente_anual) VALUES (?,?,?,?,1)",
        [("13º Salário", 11, 5_500.00, "clt")],
    )

    fixas = [
        ("Aluguel / Financiamento imóvel",  900.00, 5),
        ("Internet",                          89.90, 10),
        ("Streaming (Netflix, Spotify…)",     39.90, 10),
        ("Plano de saúde",                   190.00, 15),
        ("Telefone / Celular",                79.90, 10),
        ("Academia",                          69.00, 10),
    ]
    variaveis = [
        ("Supermercado",            500,  800, 15, 1.0),
        ("Combustível",             200,  380, 20, 1.0),
        ("Restaurantes / Delivery",  80,  220, 20, 1.0),
        ("Farmácia",                 30,  120, 20, 1.0),
        ("Água",                     60,  110, 18, 1.0),
        ("Luz / Energia elétrica",   90,  190, 12, 1.0),
        ("Manutenção veículo",         0,  300, 20, 0.25),
    ]
    total = _inserir_lancamentos(conn, planos, fixas, variaveis, hoje, rng,
                                  offset_range=range(-12, 7))

    agora = _agora()
    id_nu = _inserir_cartao(conn, "Nubank", "nubank", "master", "3311",
                             "#6D28D9", "#FFFFFF", 3_000, 1_800, 1, 22, agora)

    _inserir_compras(conn, [
        (id_nu, "Notebook usado",    1_500.0, 10, -9),
        (id_nu, "Celular Motorola",    900.0,  6, -3),
    ], hoje)

    # Sem dívidas — perfil disciplinado no início
    _inserir_dividas(conn, [
        ("Financ. moto (últimas parcelas)", "financiamento", 2_400.0, 400.0, 12, 6, 10, 1.20),
    ])

    # ── Investimentos ─────────────────────────────────────────────────────
    _popular_investimentos_primeiro_passo(conn, rng, hoje)

    # ── Metas ─────────────────────────────────────────────────────────────
    _inserir_metas(conn, [
        ("Fundo de Emergência",
         20_000.0, 15_600.0,
         _data_offset_str(hoje, 6),
         "6 meses de despesas — quase lá!"),
        ("Entrada carro usado",
         20_000.0, 4_400.0,
         _data_offset_str(hoje, 18),
         "Guardar R$900/mês nos próximos 18 meses"),
        ("Viagem Nordeste",
         5_000.0, 5_000.0,
         None,
         "Meta concluída! Viagem realizada com sucesso"),
    ])

    return total


def _popular_investimentos_primeiro_passo(conn, rng: random.Random, hoje: date) -> None:
    """1 conta, 3 ativos, 12 meses de histórico — perfil iniciante."""
    agora = _agora()

    cur = conn.execute(
        "INSERT INTO contas_investimento (nome, instituicao, tipo, observacao, ativa, criado_em)"
        " VALUES ('Nubank Reserva','Nubank','banco','Reserva de emergência e primeiros investimentos',1,?)",
        (agora,),
    )
    id_nu = cur.lastrowid

    ativos_def = [
        ("CDB-NU-110CDI", "CDB Nubank 110% CDI",  "cdb",    id_nu, "cdi",   110.0, f"{hoje.year + 2}-{hoje.month:02d}-01"),
        ("TNLP-SELIC-27", "Tesouro Selic 2027",   "tesouro", id_nu, "selic", 100.0, "2027-03-01"),
        ("MXRF11",        "Maxi Renda FII",        "fii",     id_nu, None,    None,  None),
    ]
    ativo_ids = _criar_ativos_inv(conn, ativos_def, agora)

    movs = [
        # CDB: aportes mensais pequenos ao longo de 12 meses
        ("CDB-NU-110CDI", "aplicacao", 0, 3_000.00, -12),
        ("CDB-NU-110CDI", "aplicacao", 0, 3_000.00,  -9),
        ("CDB-NU-110CDI", "juros",     0,   180.00,  -6),
        ("CDB-NU-110CDI", "aplicacao", 0, 3_000.00,  -6),
        ("CDB-NU-110CDI", "juros",     0,   210.00,  -3),
        ("CDB-NU-110CDI", "aplicacao", 0, 3_000.00,  -3),
        # Tesouro: aporte único
        ("TNLP-SELIC-27", "aplicacao", 0, 2_000.00,  -8),
        ("TNLP-SELIC-27", "juros",     0,   110.00,  -2),
        # MXRF11: primeiras cotas + dividendo
        ("MXRF11", "compra",    100, 10.20,  -5),
        ("MXRF11", "dividendo",   0,  72.00, -2),
    ]
    _inserir_movimentacoes_inv(conn, rng, hoje, ativo_ids, movs)
    _recalcular_posicoes_demo(conn, ativo_ids)


# ──────────────────────────────────────────────────────────────────────────────
# Perfil 7 — Em Ritmo (Investidor há 3 anos)
# ──────────────────────────────────────────────────────────────────────────────

def _popular_em_ritmo(conn, planos, rng, hoje) -> int:
    conn.execute("UPDATE fontes_receita SET valor_mensal=9500.0, ativa=1, periodicidade='mensal' WHERE nome='Salário CLT'")
    conn.execute("UPDATE fontes_receita SET valor_mensal=1200.0, ativa=1, periodicidade='bimestral' WHERE nome='Freela / Serviço avulso'")
    conn.execute("DELETE FROM receitas_especiais")
    conn.executemany(
        "INSERT INTO receitas_especiais (nome, mes, valor, tipo, recorrente_anual) VALUES (?,?,?,?,1)",
        [
            ("13º Salário",        11, 9_500.00, "clt"),   # Dezembro (0-indexed)
            ("Férias + 1/3",        5, 12_666.67, "clt"),  # Junho (0-indexed)
            ("Dividendos FII",      2,   820.00, "outra"), # Março
            ("Dividendos FII",      5,   850.00, "outra"), # Junho
            ("Dividendos FII",      8,   840.00, "outra"), # Setembro
            ("Dividendos FII",     11,   870.00, "outra"), # Dezembro
        ],
    )

    fixas = [
        ("Aluguel / Financiamento imóvel", 1_500.00, 5),
        ("Internet",                         119.90, 10),
        ("Streaming (Netflix, Spotify…)",     69.90, 10),
        ("Plano de saúde",                   380.00, 15),
        ("Telefone / Celular",                99.90, 10),
        ("Academia",                          99.00, 10),
        ("Seguro veículo",                   260.00, 20),
    ]
    variaveis = [
        ("Supermercado",            700,  1_100, 15, 1.0),
        ("Combustível",             320,    520, 20, 1.0),
        ("Restaurantes / Delivery", 200,    480, 20, 1.0),
        ("Farmácia",                 50,    180, 20, 1.0),
        ("Água",                     80,    140, 18, 1.0),
        ("Luz / Energia elétrica",  140,    300, 12, 1.0),
        ("Manutenção veículo",         0,   400, 20, 0.35),
    ]
    total = _inserir_lancamentos(conn, planos, fixas, variaveis, hoje, rng,
                                  offset_range=range(-36, 13))

    agora = _agora()
    id_nu = _inserir_cartao(conn, "Nubank Gold",       "nubank",    "master", "7722",
                             "#6D28D9", "#FFFFFF", 8_000, 5_200, 1,  22, agora)
    id_st = _inserir_cartao(conn, "Santander Free",    "santander", "master", "4499",
                             "#EC0000", "#FFFFFF", 6_000, 3_800, 15,  5, agora)

    _inserir_compras(conn, [
        (id_nu, "SmartTV Samsung 55\"",   2_800.0,  10, -14),
        (id_nu, "Celular Samsung S24",    3_500.0,  12,  -6),
        (id_st, "Viagem Gramado",         3_200.0,   6,  -4),
        (id_st, "Notebook Dell",          4_200.0,  12,  -2),
        (id_nu, "Ar-condicionado",        2_400.0,   8,   1),
    ], hoje)

    # Carro financiado — metade pago
    _inserir_dividas(conn, [
        ("Financ. Honda Fit (metade)", "financiamento", 22_000.0, 850.0, 48, 24, 10, 1.35),
    ])

    # ── Investimentos ─────────────────────────────────────────────────────
    _popular_investimentos_em_ritmo(conn, rng, hoje)

    # ── Metas ─────────────────────────────────────────────────────────────
    _inserir_metas(conn, [
        ("Reserva de Emergência",
         50_000.0, 50_000.0,
         None,
         "Meta concluída! Reserva completa de 6 meses"),
        ("Entrada Apartamento",
         120_000.0, 69_600.0,
         _data_offset_str(hoje, 24),
         "Guardar R$2.100/mês para ter entrada em 2 anos"),
        ("Aposentadoria Antecipada",
         2_000_000.0, 360_000.0,
         _data_offset_str(hoje, 216),
         "18% da jornada — aporte mensal de R$1.500"),
        ("Intercâmbio do Filho",
         45_000.0, 19_800.0,
         _data_offset_str(hoje, 12),
         "Guardar R$2.100/mês para Canada no próximo ano"),
    ])

    return total


def _popular_investimentos_em_ritmo(conn, rng: random.Random, hoje: date) -> None:
    """2 contas, 6 ativos, 36 meses — investidor em crescimento."""
    agora = _agora()

    cur = conn.execute(
        "INSERT INTO contas_investimento (nome, instituicao, tipo, observacao, ativa, criado_em)"
        " VALUES ('XP Investimentos','XP Investimentos','corretora','Ações e FIIs',1,?)",
        (agora,),
    )
    id_xp = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO contas_investimento (nome, instituicao, tipo, observacao, ativa, criado_em)"
        " VALUES ('BTG Pactual','BTG Pactual','corretora','Renda fixa e Tesouro',1,?)",
        (agora,),
    )
    id_btg = cur.lastrowid

    ativos_def = [
        ("PETR4",          "Petrobrás PN",              "acao",    id_xp,  None,    None,  None),
        ("VALE3",          "Vale ON",                    "acao",    id_xp,  None,    None,  None),
        ("HGLG11",         "CSHG Logística FII",         "fii",     id_xp,  None,    None,  None),
        ("MXRF11",         "Maxi Renda FII",             "fii",     id_xp,  None,    None,  None),
        ("CDB-BTG-120CDI", "CDB BTG 120% CDI",           "cdb",     id_btg, "cdi",  120.0, f"{hoje.year + 1}-{hoje.month:02d}-01"),
        ("TNLP-IPCA-35",   "Tesouro IPCA+ 2035",         "tesouro", id_btg, "ipca",   6.5, "2035-05-15"),
    ]
    ativo_ids = _criar_ativos_inv(conn, ativos_def, agora)

    movs = [
        # Ações — compras escalonadas ao longo de 3 anos
        ("PETR4",  "compra",   100, 26.80,  -36),
        ("PETR4",  "compra",    80, 30.40,  -24),
        ("PETR4",  "dividendo",  0, 310.00, -18),
        ("PETR4",  "compra",    50, 33.50,  -12),
        ("PETR4",  "dividendo",  0, 280.00,  -6),
        ("VALE3",  "compra",    80, 58.00,  -30),
        ("VALE3",  "dividendo",  0, 390.00, -18),
        ("VALE3",  "venda",     30, 65.20,  -10),  # venda parcial com lucro
        ("VALE3",  "dividendo",  0, 340.00,  -6),
        ("VALE3",  "imposto",    0,  28.00, -10),  # IR sobre venda
        # FIIs
        ("HGLG11", "compra",    60, 155.00, -28),
        ("HGLG11", "dividendo",  0, 510.00, -18),
        ("HGLG11", "dividendo",  0, 525.00, -12),
        ("HGLG11", "dividendo",  0, 540.00,  -6),
        ("MXRF11", "compra",   300, 10.05,  -24),
        ("MXRF11", "compra",   100, 10.30,  -12),
        ("MXRF11", "dividendo",  0, 220.00, -18),
        ("MXRF11", "dividendo",  0, 225.00, -12),
        ("MXRF11", "dividendo",  0, 230.00,  -6),
        # Renda fixa
        ("CDB-BTG-120CDI", "aplicacao", 0, 25_000.00, -30),
        ("CDB-BTG-120CDI", "aplicacao", 0, 10_000.00, -18),
        ("CDB-BTG-120CDI", "juros",     0,  1_200.00, -12),
        ("CDB-BTG-120CDI", "juros",     0,  1_280.00,  -6),
        ("TNLP-IPCA-35",   "aplicacao", 0, 20_000.00, -36),
        ("TNLP-IPCA-35",   "aplicacao", 0, 10_000.00, -18),
        ("TNLP-IPCA-35",   "juros",     0,  1_050.00, -12),
        # Taxas
        ("PETR4", "taxa", 0, 5.80, -36),
        ("VALE3", "taxa", 0, 4.50, -30),
    ]
    _inserir_movimentacoes_inv(conn, rng, hoje, ativo_ids, movs)
    _recalcular_posicoes_demo(conn, ativo_ids)


# ──────────────────────────────────────────────────────────────────────────────
# Perfil 8 — Patrimônio Crescendo (Carteira consolidada)
# ──────────────────────────────────────────────────────────────────────────────

def _popular_patrimonio_crescendo(conn, planos, rng, hoje) -> int:
    conn.execute("UPDATE fontes_receita SET valor_mensal=14000.0, ativa=1, periodicidade='mensal' WHERE nome='Salário CLT'")
    conn.execute("UPDATE fontes_receita SET valor_mensal=3500.0,  ativa=1, periodicidade='mensal' WHERE nome='Freela / Serviço avulso'")
    conn.execute("DELETE FROM receitas_especiais")
    conn.executemany(
        "INSERT INTO receitas_especiais (nome, mes, valor, tipo, recorrente_anual) VALUES (?,?,?,?,1)",
        [
            ("13º Salário",       11, 14_000.00, "clt"),
            ("Férias + 1/3",       6, 18_666.67, "clt"),
            ("Dividendos FII",     1,  2_400.00, "outra"),
            ("Dividendos FII",     4,  2_600.00, "outra"),
            ("Dividendos FII",     7,  2_500.00, "outra"),
            ("Dividendos FII",    10,  2_700.00, "outra"),
            ("Aluguel imóvel",     0,  1_800.00, "outra"),
        ],
    )

    fixas = [
        ("Aluguel / Financiamento imóvel", 2_800.00, 5),
        ("Internet",                         149.90, 10),
        ("Streaming (Netflix, Spotify…)",     99.90, 10),
        ("Plano de saúde",                   680.00, 15),
        ("Telefone / Celular",               129.90, 10),
        ("Academia",                         149.00, 10),
        ("TV por assinatura",                 75.90, 10),
        ("Seguro veículo",                   420.00, 20),
    ]
    variaveis = [
        ("Supermercado",            900,  1_600, 15, 1.0),
        ("Combustível",             450,    700, 20, 1.0),
        ("Restaurantes / Delivery", 400,    900, 20, 1.0),
        ("Farmácia",                 80,    300, 20, 1.0),
        ("Água",                    100,    180, 18, 1.0),
        ("Luz / Energia elétrica",  200,    450, 12, 1.0),
        ("Manutenção veículo",        0,    600, 20, 0.5),
    ]
    total = _inserir_lancamentos(conn, planos, fixas, variaveis, hoje, rng)

    agora = _agora()
    id_nu = _inserir_cartao(conn, "Nubank Ultravioleta",   "nubank", "master", "0000",
                             "#6D28D9", "#FFFFFF", 40_000, 30_000, 1,  22, agora)
    id_xp = _inserir_cartao(conn, "XP Investimentos Visa", "xp",     "visa",   "1001",
                             "#000000", "#FFFF00", 30_000, 20_000, 10,  1, agora)
    id_it = _inserir_cartao(conn, "Itaú Personnalité",     "itau",   "visa",   "2002",
                             "#EC7000", "#FFFFFF", 25_000, 18_000, 15,  5, agora)

    _inserir_compras(conn, [
        (id_nu, "iPhone 15 Pro Max",     8_500.0, 12,  -4),
        (id_xp, "MacBook Pro M3",       15_000.0, 12,  -8),
        (id_it, "Viagem Japão",         18_000.0, 18, -10),
        (id_nu, "Home theater Sony",     6_000.0, 10,  -2),
        (id_xp, "Câmera Sony A7",        9_000.0, 12,  -6),
        (id_it, "Reforma escritório",    5_500.0,  8,   0),
        (id_nu, "Equipamento academia",  4_000.0,  6,   2),
    ], hoje)

    _inserir_dividas(conn, [
        ("Financ. apê alugado (BB)", "financiamento", 180_000.0, 1_600.0, 240, 48, 5, 0.70),
    ])

    # ── Investimentos ─────────────────────────────────────────────────────
    _popular_investimentos_patrimonio(conn, rng, hoje)

    # ── Metas ─────────────────────────────────────────────────────────────
    _inserir_metas(conn, [
        ("Independência Financeira",
         3_000_000.0, 810_000.0,
         _data_offset_str(hoje, 120),
         "27% concluído — carteira gerando renda passiva crescente"),
        ("Casa de Praia",
         450_000.0, 319_500.0,
         _data_offset_str(hoje, 36),
         "71% do valor — faltam ~R$130k em 3 anos"),
        ("Educação dos Filhos",
         200_000.0, 200_000.0,
         None,
         "Meta concluída! Fundo educacional 100% aportado"),
        ("Viagem Europa (família)",
         60_000.0, 28_800.0,
         _data_offset_str(hoje, 12),
         "48% — guardando R$2.600/mês para viajar em 1 ano"),
    ])

    return total


def _popular_investimentos_patrimonio(conn, rng: random.Random, hoje: date) -> None:
    """4 contas, 11 ativos, 48+ meses — carteira consolidada."""
    agora = _agora()

    cur = conn.execute(
        "INSERT INTO contas_investimento (nome, instituicao, tipo, observacao, ativa, criado_em)"
        " VALUES ('Rico — XP Investimentos','XP Investimentos','corretora','Conta principal',1,?)",
        (agora,),
    )
    id_rico = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO contas_investimento (nome, instituicao, tipo, observacao, ativa, criado_em)"
        " VALUES ('BTG Pactual','BTG Pactual','corretora','Renda fixa e FIIs',1,?)",
        (agora,),
    )
    id_btg = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO contas_investimento (nome, instituicao, tipo, observacao, ativa, criado_em)"
        " VALUES ('Nubank Reserva','Nubank','banco','CDB emergência',1,?)",
        (agora,),
    )
    id_nu = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO contas_investimento (nome, instituicao, tipo, observacao, ativa, criado_em)"
        " VALUES ('Tesouro Direto','Secretaria do Tesouro Nacional','tesouro','Previdência pública',1,?)",
        (agora,),
    )
    id_td = cur.lastrowid

    ativos_def = [
        ("PETR4",          "Petrobrás PN",             "acao",    id_rico, None,    None,  None),
        ("VALE3",          "Vale ON",                   "acao",    id_rico, None,    None,  None),
        ("BOVA11",         "iShares Ibovespa ETF",      "etf",     id_rico, None,    None,  None),
        ("HGLG11",         "CSHG Logística FII",        "fii",     id_rico, None,    None,  None),
        ("MXRF11",         "Maxi Renda FII",            "fii",     id_rico, None,    None,  None),
        ("KNRI11",         "Kinea Renda Imobiliária",   "fii",     id_btg,  None,    None,  None),
        ("CDB-NU-130CDI",  "CDB Nubank 130% CDI",       "cdb",     id_nu,   "cdi",  130.0, f"{hoje.year + 2}-{hoje.month:02d}-01"),
        ("CDB-BTG-120CDI", "CDB BTG 120% CDI",          "cdb",     id_btg,  "cdi",  120.0, f"{hoje.year + 1}-{hoje.month:02d}-01"),
        ("TNLP-SELIC-27",  "Tesouro Selic 2027",        "tesouro", id_td,   "selic",100.0, "2027-03-01"),
        ("TNLP-IPCA-35",   "Tesouro IPCA+ 2035",        "tesouro", id_td,   "ipca",   6.5, "2035-05-15"),
        ("CRIPTO-BTC",     "Bitcoin",                   "cripto",  id_rico, None,    None,  None),
    ]
    ativo_ids = _criar_ativos_inv(conn, ativos_def, agora)

    movs = [
        # Ações
        ("PETR4",  "compra",   200, 28.50,  -48),
        ("PETR4",  "compra",   100, 31.20,  -36),
        ("PETR4",  "dividendo",  0, 480.00, -24),
        ("PETR4",  "dividendo",  0, 420.00, -12),
        ("PETR4",  "compra",    50, 34.80,   -3),
        ("VALE3",  "compra",   150, 62.00,  -42),
        ("VALE3",  "venda",     50, 68.50,  -12),
        ("VALE3",  "dividendo",  0, 620.00, -24),
        ("VALE3",  "dividendo",  0, 580.00,  -6),
        # ETF
        ("BOVA11", "compra",    80, 108.00, -36),
        ("BOVA11", "compra",    40, 115.00,  -6),
        # FIIs
        ("HGLG11", "compra",   100, 158.00, -42),
        ("HGLG11", "dividendo",  0, 850.00, -30),
        ("HGLG11", "dividendo",  0, 870.00, -18),
        ("HGLG11", "dividendo",  0, 890.00, -12),
        ("HGLG11", "dividendo",  0, 910.00,  -6),
        ("HGLG11", "dividendo",  0, 920.00,  -1),
        ("MXRF11", "compra",   500, 10.10,  -36),
        ("MXRF11", "dividendo",  0, 350.00, -24),
        ("MXRF11", "dividendo",  0, 360.00, -12),
        ("MXRF11", "dividendo",  0, 370.00,  -6),
        ("MXRF11", "dividendo",  0, 375.00,  -1),
        ("KNRI11", "compra",    60, 142.00, -30),
        ("KNRI11", "dividendo",  0, 490.00, -18),
        ("KNRI11", "dividendo",  0, 500.00,  -6),
        # CDB
        ("CDB-NU-130CDI",  "aplicacao", 0, 20_000.00, -24),
        ("CDB-BTG-120CDI", "aplicacao", 0, 15_000.00, -36),
        ("CDB-BTG-120CDI", "juros",     0,    720.00, -12),
        ("CDB-BTG-120CDI", "juros",     0,    750.00,  -6),
        # Tesouro
        ("TNLP-SELIC-27", "aplicacao", 0, 30_000.00, -48),
        ("TNLP-SELIC-27", "juros",     0,  1_800.00, -36),
        ("TNLP-SELIC-27", "juros",     0,  1_950.00, -12),
        ("TNLP-IPCA-35",  "aplicacao", 0, 25_000.00, -42),
        # Cripto
        ("CRIPTO-BTC", "compra", 0.05, 185_000.00, -30),
        ("CRIPTO-BTC", "compra", 0.03, 260_000.00,  -8),
        # Taxas e impostos
        ("PETR4", "taxa",    0,  8.50, -48),
        ("VALE3", "taxa",    0,  6.00, -42),
        ("VALE3", "imposto", 0, 45.00, -12),
    ]
    _inserir_movimentacoes_inv(conn, rng, hoje, ativo_ids, movs)
    _recalcular_posicoes_demo(conn, ativo_ids)


def _recalcular_posicoes_demo(conn, ativo_ids: dict[str, int]) -> None:
    """Calcula e grava posicao_cache para todos os ativos do demo."""
    agora = _agora()
    for codigo, ativo_id in ativo_ids.items():
        rows = conn.execute(
            "SELECT tipo, quantidade, valor_liquido FROM movimentacoes_investimento"
            " WHERE ativo_id=? ORDER BY data, id",
            (ativo_id,),
        ).fetchall()

        qtd_atual = 0.0
        val_inv   = 0.0
        lucro_r   = 0.0

        for r in rows:
            tipo = r["tipo"]
            qtd  = r["quantidade"] or 0.0
            val  = r["valor_liquido"] or 0.0

            if tipo in ("compra", "aplicacao"):
                val_inv   += val
                qtd_atual += qtd
            elif tipo == "venda":
                if qtd > 0 and qtd_atual > 0:
                    prop = min(1.0, qtd / qtd_atual)
                    custo = val_inv * prop
                    lucro_r  += val - custo
                    val_inv   = max(0.0, val_inv - custo)
                    qtd_atual = max(0.0, qtd_atual - qtd)
            elif tipo == "resgate":
                if val_inv > 0:
                    prop = min(1.0, val / val_inv)
                    lucro_r += val - (val_inv * prop)
                    val_inv  = max(0.0, val_inv * (1 - prop))
            elif tipo == "amortizacao":
                val_inv = max(0.0, val_inv - val)

        custo_medio = val_inv / qtd_atual if qtd_atual > 0 else 0.0
        # Valor atual = valor investido ± variação aleatória realista
        import random as _rnd
        variacao = _rnd.Random(hash(codigo) % 2**32).uniform(0.85, 1.25)
        val_atual = round(val_inv * variacao, 2) if val_inv > 0 else 0.0

        conn.execute(
            "INSERT OR REPLACE INTO posicao_cache"
            " (ativo_id, quantidade_atual, custo_medio, valor_investido,"
            "  valor_atual, lucro_realizado, atualizado_em)"
            " VALUES (?,?,?,?,?,?,?)",
            (ativo_id, qtd_atual, custo_medio, val_inv,
             val_atual, lucro_r, agora),
        )


# ──────────────────────────────────────────────────────────────────────────────
# Entry point público
# ──────────────────────────────────────────────────────────────────────────────

_PERFIL_FNS = {
    "padrao":               _popular_padrao,
    "apertado":             _popular_apertado,
    "moderado_dividas":     _popular_moderado_dividas,
    "moderado_recuperando": _popular_moderado_recuperando,
    "no_verde":             _popular_no_verde,
    "primeiro_passo":       _popular_primeiro_passo,
    "em_ritmo":             _popular_em_ritmo,
    "patrimonio_crescendo": _popular_patrimonio_crescendo,
}


def popular_modo_demo(perfil: str = "padrao") -> int:
    """
    Popula o banco com dados demonstrativos do perfil escolhido.
    Deve ser chamado após zerar_dados().
    Retorna o total de lançamentos em contas_pagar inseridos.
    """
    fn = _PERFIL_FNS.get(perfil, _popular_padrao)
    rng = random.Random(42)
    hoje = date.today()

    with conectar() as conn:
        planos = {
            r["nome"]: r["id"]
            for r in conn.execute("SELECT id, nome FROM plano_contas").fetchall()
        }
        total = fn(conn, planos, rng, hoje)

    salvar_configuracao("dados_exemplo_inseridos", "true")
    return total
