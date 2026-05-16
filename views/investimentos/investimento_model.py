"""
investimento_model.py — Serenus Investimentos
Dataclasses, CRUD, cálculo de posição e integração com o módulo financeiro.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from database import conectar


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ContaInvestimento:
    id: int
    nome: str
    instituicao: str
    tipo: str          # 'corretora' | 'banco' | 'tesouro' | 'outro'
    observacao: str
    ativa: bool
    criado_em: str


@dataclass
class Ativo:
    id: int
    codigo: str
    nome: str
    tipo: str          # 'acao' | 'etf' | 'fii' | 'cdb' | 'tesouro' | 'fundo' | 'cripto' | 'outro'
    conta_investimento_id: Optional[int]
    conta_nome: str
    indexador: Optional[str]
    taxa_contratada: Optional[float]
    vencimento: Optional[str]
    observacao: str
    ativo: bool
    criado_em: str


@dataclass
class Movimentacao:
    id: int
    ativo_id: int
    ativo_codigo: str
    ativo_nome: str
    conta_investimento_id: int
    conta_nome: str
    tipo: str
    data: str
    quantidade: float
    preco_unitario: float
    valor_bruto: float
    taxas: float
    valor_liquido: float
    observacao: str
    registrar_no_financeiro: bool
    contas_pagar_id: Optional[int]
    criado_em: str


@dataclass
class Posicao:
    ativo_id: int
    codigo: str
    nome: str
    tipo: str
    conta_nome: str
    quantidade_atual: float
    custo_medio: float
    valor_investido: float
    valor_atual: float
    lucro_realizado: float
    lucro_nao_realizado: float
    rentabilidade_pct: float
    rendimentos_recebidos: float
    vencimento: Optional[str]
    indexador: Optional[str]
    taxa_contratada: Optional[float]


# ─────────────────────────────────────────────────────────────────────────────
# ContaInvestimento — CRUD
# ─────────────────────────────────────────────────────────────────────────────

def listar_contas_investimento(apenas_ativas: bool = False) -> list[ContaInvestimento]:
    sql = "SELECT * FROM contas_investimento"
    if apenas_ativas:
        sql += " WHERE ativa = 1"
    sql += " ORDER BY nome"
    with conectar() as conn:
        rows = conn.execute(sql).fetchall()
    return [ContaInvestimento(
        id=r["id"], nome=r["nome"], instituicao=r["instituicao"],
        tipo=r["tipo"], observacao=r["observacao"] or "",
        ativa=bool(r["ativa"]), criado_em=r["criado_em"] or "",
    ) for r in rows]


def salvar_conta_investimento(dados: dict, id: Optional[int] = None) -> int:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        if id is not None:
            conn.execute(
                "UPDATE contas_investimento SET nome=?, instituicao=?, tipo=?, observacao=? WHERE id=?",
                (dados["nome"], dados["instituicao"], dados["tipo"],
                 dados.get("observacao", ""), id),
            )
            return id
        cur = conn.execute(
            "INSERT INTO contas_investimento (nome, instituicao, tipo, observacao, ativa, criado_em)"
            " VALUES (?,?,?,?,1,?)",
            (dados["nome"], dados["instituicao"], dados["tipo"],
             dados.get("observacao", ""), agora),
        )
        return cur.lastrowid


def alternar_ativa_conta_inv(id: int, ativa: bool) -> None:
    with conectar() as conn:
        conn.execute("UPDATE contas_investimento SET ativa=? WHERE id=?", (int(ativa), id))


def excluir_conta_investimento(id: int) -> tuple[bool, str]:
    with conectar() as conn:
        uso = conn.execute(
            "SELECT COUNT(*) AS n FROM ativos WHERE conta_investimento_id=?", (id,)
        ).fetchone()["n"]
        if uso:
            return False, "Conta possui ativos vinculados. Remova-os antes."
        conn.execute("DELETE FROM contas_investimento WHERE id=?", (id,))
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# Ativo — CRUD
# ─────────────────────────────────────────────────────────────────────────────

def listar_ativos(apenas_ativos: bool = False,
                  conta_id: Optional[int] = None) -> list[Ativo]:
    sql = """
        SELECT a.*, COALESCE(ci.nome, '') AS conta_nome
        FROM   ativos a
        LEFT JOIN contas_investimento ci ON ci.id = a.conta_investimento_id
    """
    filtros, params = [], []
    if apenas_ativos:
        filtros.append("a.ativo = 1")
    if conta_id:
        filtros.append("a.conta_investimento_id = ?")
        params.append(conta_id)
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    sql += " ORDER BY a.tipo, a.codigo"
    with conectar() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Ativo(
        id=r["id"], codigo=r["codigo"], nome=r["nome"], tipo=r["tipo"],
        conta_investimento_id=r["conta_investimento_id"],
        conta_nome=r["conta_nome"],
        indexador=r["indexador"], taxa_contratada=r["taxa_contratada"],
        vencimento=r["vencimento"], observacao=r["observacao"] or "",
        ativo=bool(r["ativo"]), criado_em=r["criado_em"] or "",
    ) for r in rows]


def salvar_ativo(dados: dict, id: Optional[int] = None) -> int:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        if id is not None:
            conn.execute("""
                UPDATE ativos SET codigo=?, nome=?, tipo=?,
                  conta_investimento_id=?, indexador=?, taxa_contratada=?,
                  vencimento=?, observacao=?
                WHERE id=?
            """, (dados["codigo"], dados["nome"], dados["tipo"],
                  dados.get("conta_investimento_id"), dados.get("indexador"),
                  dados.get("taxa_contratada"), dados.get("vencimento") or None,
                  dados.get("observacao", ""), id))
            return id
        cur = conn.execute("""
            INSERT INTO ativos (codigo, nome, tipo, conta_investimento_id,
              indexador, taxa_contratada, vencimento, observacao, ativo, criado_em)
            VALUES (?,?,?,?,?,?,?,?,1,?)
        """, (dados["codigo"], dados["nome"], dados["tipo"],
              dados.get("conta_investimento_id"), dados.get("indexador"),
              dados.get("taxa_contratada"), dados.get("vencimento") or None,
              dados.get("observacao", ""), agora))
        return cur.lastrowid


def alternar_ativo_ativo(id: int, ativo: bool) -> None:
    with conectar() as conn:
        conn.execute("UPDATE ativos SET ativo=? WHERE id=?", (int(ativo), id))


def excluir_ativo(id: int) -> tuple[bool, str]:
    with conectar() as conn:
        uso = conn.execute(
            "SELECT COUNT(*) AS n FROM movimentacoes_investimento WHERE ativo_id=?", (id,)
        ).fetchone()["n"]
        if uso:
            return False, "Ativo possui movimentações. Não pode ser excluído."
        conn.execute("DELETE FROM posicao_cache WHERE ativo_id=?", (id,))
        conn.execute("DELETE FROM ativos WHERE id=?", (id,))
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# Movimentação — CRUD
# ─────────────────────────────────────────────────────────────────────────────

def listar_movimentacoes(ativo_id: Optional[int] = None,
                          conta_id: Optional[int] = None,
                          mes: Optional[int] = None,
                          ano: Optional[int] = None,
                          tipo: Optional[str] = None) -> list[Movimentacao]:
    sql = """
        SELECT m.*, a.codigo AS ativo_codigo, a.nome AS ativo_nome,
               ci.nome AS conta_nome
        FROM   movimentacoes_investimento m
        JOIN   ativos a ON a.id = m.ativo_id
        JOIN   contas_investimento ci ON ci.id = m.conta_investimento_id
        WHERE  1=1
    """
    params = []
    if ativo_id:
        sql += " AND m.ativo_id = ?"
        params.append(ativo_id)
    if conta_id:
        sql += " AND m.conta_investimento_id = ?"
        params.append(conta_id)
    if mes and ano:
        inicio = f"{ano:04d}-{mes:02d}-01"
        fim    = f"{ano:04d}-{mes+1:02d}-01" if mes < 12 else f"{ano+1:04d}-01-01"
        sql += " AND m.data >= ? AND m.data < ?"
        params += [inicio, fim]
    if tipo:
        sql += " AND m.tipo = ?"
        params.append(tipo)
    sql += " ORDER BY m.data DESC, m.id DESC"
    with conectar() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Movimentacao(
        id=r["id"], ativo_id=r["ativo_id"],
        ativo_codigo=r["ativo_codigo"], ativo_nome=r["ativo_nome"],
        conta_investimento_id=r["conta_investimento_id"],
        conta_nome=r["conta_nome"], tipo=r["tipo"],
        data=r["data"], quantidade=r["quantidade"] or 0.0,
        preco_unitario=r["preco_unitario"] or 0.0,
        valor_bruto=r["valor_bruto"], taxas=r["taxas"] or 0.0,
        valor_liquido=r["valor_liquido"],
        observacao=r["observacao"] or "",
        registrar_no_financeiro=bool(r["registrar_no_financeiro"]),
        contas_pagar_id=r["contas_pagar_id"],
        criado_em=r["criado_em"] or "",
    ) for r in rows]


def salvar_movimentacao(dados: dict) -> int:
    """
    Salva movimentação e, se registrar_no_financeiro=True,
    gera o lançamento financeiro correspondente.
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reg_fin = bool(dados.get("registrar_no_financeiro", False))

    with conectar() as conn:
        cur = conn.execute("""
            INSERT INTO movimentacoes_investimento
              (ativo_id, conta_investimento_id, tipo, data, quantidade,
               preco_unitario, valor_bruto, taxas, valor_liquido,
               observacao, registrar_no_financeiro, criado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (dados["ativo_id"], dados["conta_investimento_id"],
              dados["tipo"], dados["data"],
              dados.get("quantidade", 0), dados.get("preco_unitario", 0),
              dados["valor_bruto"], dados.get("taxas", 0),
              dados["valor_liquido"], dados.get("observacao", ""),
              int(reg_fin), agora))
        mov_id = cur.lastrowid

    if reg_fin:
        cp_id = _gerar_lancamento_financeiro(dados, mov_id)
        if cp_id:
            with conectar() as conn:
                conn.execute(
                    "UPDATE movimentacoes_investimento SET contas_pagar_id=? WHERE id=?",
                    (cp_id, mov_id),
                )

    _recalcular_posicao(dados["ativo_id"])
    return mov_id


def excluir_movimentacao(id: int) -> None:
    with conectar() as conn:
        row = conn.execute(
            "SELECT contas_pagar_id, ativo_id FROM movimentacoes_investimento WHERE id=?",
            (id,),
        ).fetchone()
        cp_id    = row["contas_pagar_id"] if row else None
        ativo_id = row["ativo_id"] if row else None
        # Apaga o filho antes do pai para respeitar a FK
        conn.execute("DELETE FROM movimentacoes_investimento WHERE id=?", (id,))
        if cp_id:
            conn.execute("DELETE FROM contas_pagar WHERE id=?", (cp_id,))
    if ativo_id:
        _recalcular_posicao(ativo_id)


# ─────────────────────────────────────────────────────────────────────────────
# Integração financeira — saídas geram contas_pagar
# ─────────────────────────────────────────────────────────────────────────────

_LABELS_MOV = {
    "compra": "Compra", "aplicacao": "Aplicação",
    "taxa": "Taxa",     "imposto": "Imposto IR",
}

_PLANO_APLICACAO = "Investimentos — Aplicação"
_PLANO_TAXAS     = "Investimentos — Taxas e Impostos"


def _obter_plano_investimento(conn, nome: str) -> int:
    row = conn.execute(
        "SELECT id FROM plano_contas WHERE nome=? LIMIT 1", (nome,)
    ).fetchone()
    if row:
        return row["id"]
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        "INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)"
        " VALUES (?,'variavel','Investimentos',1,0,?)",
        (nome, agora),
    )
    return cur.lastrowid


def _gerar_lancamento_financeiro(dados: dict, mov_id: int) -> Optional[int]:
    """
    Cria contas_pagar para movimentações de saída (compra, aplicação, taxa, imposto).
    Entradas (venda, dividendo, etc.) são lidas diretamente pelo extrato via
    rendimentos_financeiros_mes() — não geram contas_pagar.

    # FUTURE: quando houver módulo de receitas avulsas com data completa,
    # as entradas também poderão ser geradas automaticamente aqui.
    """
    from config import MOV_INV_SAIDA
    if dados["tipo"] not in MOV_INV_SAIDA:
        return None

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        nome_plano = (
            _PLANO_TAXAS if dados["tipo"] in ("taxa", "imposto")
            else _PLANO_APLICACAO
        )
        plano_id = _obter_plano_investimento(conn, nome_plano)

        codigo_row = conn.execute(
            "SELECT codigo FROM ativos WHERE id=?", (dados["ativo_id"],)
        ).fetchone()
        codigo = codigo_row["codigo"] if codigo_row else "?"
        desc = f"{_LABELS_MOV.get(dados['tipo'], dados['tipo'])} — {codigo}"

        cur = conn.execute("""
            INSERT INTO contas_pagar
              (plano_conta_id, descricao, valor, data_vencimento, data_pagamento,
               status, recorrente, observacao, criado_em)
            VALUES (?,?,?,?,?,'pago',0,?,?)
        """, (plano_id, desc, dados["valor_liquido"],
              dados["data"], dados["data"],
              f"Mov. investimento #{mov_id}", agora))
        return cur.lastrowid


# ─────────────────────────────────────────────────────────────────────────────
# Cálculo de posição — custo médio ponderado
# ─────────────────────────────────────────────────────────────────────────────

def _recalcular_posicao(ativo_id: int) -> None:
    """
    Reconstrói custo médio e posição a partir do histórico completo de movimentações.
    Grava resultado em posicao_cache.
    """
    with conectar() as conn:
        rows = conn.execute("""
            SELECT tipo, quantidade, valor_liquido
            FROM   movimentacoes_investimento
            WHERE  ativo_id = ?
            ORDER  BY data, id
        """, (ativo_id,)).fetchall()

    qtd_atual      = 0.0
    valor_investido = 0.0  # custo total acumulado
    lucro_realizado = 0.0

    for r in rows:
        tipo = r["tipo"]
        qtd  = r["quantidade"] or 0.0
        val  = r["valor_liquido"] or 0.0

        if tipo in ("compra", "aplicacao"):
            valor_investido += val
            qtd_atual += qtd

        elif tipo == "venda":
            if qtd > 0 and qtd_atual > 0:
                proporcao = min(1.0, qtd / qtd_atual)
                custo_vendido = valor_investido * proporcao
                lucro_realizado += val - custo_vendido
                valor_investido  = max(0.0, valor_investido - custo_vendido)
                qtd_atual        = max(0.0, qtd_atual - qtd)

        elif tipo == "resgate":
            if valor_investido > 0:
                proporcao = min(1.0, val / valor_investido)
                lucro_realizado += val - (valor_investido * proporcao)
                valor_investido  = max(0.0, valor_investido * (1 - proporcao))
            if qtd > 0:
                qtd_atual = max(0.0, qtd_atual - qtd)

        elif tipo == "amortizacao":
            # Amortização reduz o valor investido (devolução parcial de principal)
            valor_investido = max(0.0, valor_investido - val)

    custo_medio = valor_investido / qtd_atual if qtd_atual > 0 else 0.0

    with conectar() as conn:
        cache = conn.execute(
            "SELECT valor_atual FROM posicao_cache WHERE ativo_id=?", (ativo_id,)
        ).fetchone()
        # Preserva valor_atual informado manualmente; fallback = valor_investido
        valor_atual = (cache["valor_atual"] or 0.0) if cache else 0.0
        if valor_atual <= 0:
            valor_atual = valor_investido
        # Posição fechada — reset para não aparecer no filtro apenas_com_saldo
        if valor_investido <= 0 and qtd_atual <= 0:
            valor_atual = 0.0

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT OR REPLACE INTO posicao_cache
              (ativo_id, quantidade_atual, custo_medio, valor_investido,
               valor_atual, lucro_realizado, atualizado_em)
            VALUES (?,?,?,?,?,?,?)
        """, (ativo_id, qtd_atual, custo_medio, valor_investido,
              valor_atual, lucro_realizado, agora))


def atualizar_valor_atual(ativo_id: int, valor_atual: float) -> None:
    """Atualiza o valor atual (cotação manual) e recalcula lucro não realizado."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        existe = conn.execute(
            "SELECT ativo_id FROM posicao_cache WHERE ativo_id=?", (ativo_id,)
        ).fetchone()
        if existe:
            conn.execute(
                "UPDATE posicao_cache SET valor_atual=?, atualizado_em=? WHERE ativo_id=?",
                (valor_atual, agora, ativo_id),
            )
        else:
            conn.execute(
                "INSERT INTO posicao_cache (ativo_id, valor_atual, atualizado_em) VALUES (?,?,?)",
                (ativo_id, valor_atual, agora),
            )


# ─────────────────────────────────────────────────────────────────────────────
# Consultas de posição e relatórios
# ─────────────────────────────────────────────────────────────────────────────

def listar_posicoes(apenas_com_saldo: bool = True) -> list[Posicao]:
    """Posição atual de todos os ativos, calculada do cache."""
    with conectar() as conn:
        rows = conn.execute("""
            SELECT a.id, a.codigo, a.nome, a.tipo,
                   a.vencimento, a.indexador, a.taxa_contratada,
                   COALESCE(ci.nome, '') AS conta_nome,
                   COALESCE(pc.quantidade_atual, 0) AS quantidade_atual,
                   COALESCE(pc.custo_medio,      0) AS custo_medio,
                   COALESCE(pc.valor_investido,  0) AS valor_investido,
                   COALESCE(pc.valor_atual,       0) AS valor_atual,
                   COALESCE(pc.lucro_realizado,   0) AS lucro_realizado
            FROM   ativos a
            LEFT JOIN contas_investimento ci ON ci.id = a.conta_investimento_id
            LEFT JOIN posicao_cache pc        ON pc.ativo_id = a.id
            WHERE  a.ativo = 1
            ORDER  BY a.tipo, a.codigo
        """).fetchall()

        rendimentos_map = {
            r["ativo_id"]: r["total"]
            for r in conn.execute("""
                SELECT ativo_id, COALESCE(SUM(valor_liquido), 0) AS total
                FROM   movimentacoes_investimento
                WHERE  tipo IN ('dividendo','jcp','juros','amortizacao')
                GROUP  BY ativo_id
            """).fetchall()
        }

    resultado = []
    for r in rows:
        val_inv = r["valor_investido"]
        val_atu = r["valor_atual"]
        if apenas_com_saldo and val_inv <= 0 and val_atu <= 0:
            continue
        lucro_nao_real = val_atu - val_inv
        rent = ((val_atu / val_inv) - 1) * 100 if val_inv > 0 else 0.0
        resultado.append(Posicao(
            ativo_id=r["id"], codigo=r["codigo"], nome=r["nome"],
            tipo=r["tipo"], conta_nome=r["conta_nome"],
            quantidade_atual=r["quantidade_atual"],
            custo_medio=r["custo_medio"],
            valor_investido=val_inv, valor_atual=val_atu,
            lucro_realizado=r["lucro_realizado"],
            lucro_nao_realizado=lucro_nao_real,
            rentabilidade_pct=rent,
            rendimentos_recebidos=rendimentos_map.get(r["id"], 0.0),
            vencimento=r["vencimento"],
            indexador=r["indexador"],
            taxa_contratada=r["taxa_contratada"],
        ))
    return resultado


def resumo_carteira() -> dict:
    posicoes = listar_posicoes(apenas_com_saldo=False)
    total_inv = sum(p.valor_investido for p in posicoes)
    total_atu = sum(p.valor_atual for p in posicoes)
    return {
        "total_investido":    total_inv,
        "total_atual":        total_atu,
        "lucro_realizado":    sum(p.lucro_realizado for p in posicoes),
        "rendimentos":        sum(p.rendimentos_recebidos for p in posicoes),
        "lucro_nao_realizado": total_atu - total_inv,
        "rentabilidade_pct":  ((total_atu / total_inv) - 1) * 100 if total_inv > 0 else 0.0,
    }


def alocacao_por_tipo() -> dict[str, float]:
    """Alocação percentual por tipo de ativo (valor atual)."""
    posicoes = listar_posicoes()
    por_tipo: dict[str, float] = {}
    total = sum(p.valor_atual for p in posicoes)
    if total <= 0:
        return {}
    for p in posicoes:
        por_tipo[p.tipo] = por_tipo.get(p.tipo, 0.0) + p.valor_atual
    return {t: round(v / total * 100, 1)
            for t, v in sorted(por_tipo.items(), key=lambda x: -x[1])}


def rendimentos_por_mes(ano: int) -> dict[int, float]:
    """Rendimentos recebidos mês a mês para um ano."""
    with conectar() as conn:
        rows = conn.execute("""
            SELECT CAST(strftime('%m', data) AS INTEGER) AS mes,
                   SUM(valor_liquido) AS total
            FROM   movimentacoes_investimento
            WHERE  tipo IN ('dividendo','jcp','juros','amortizacao')
              AND  strftime('%Y', data) = ?
            GROUP  BY mes
        """, (str(ano),)).fetchall()
    return {r["mes"]: round(r["total"], 2) for r in rows}


def vencimentos_proximos(meses: int = 12) -> list[dict]:
    """Ativos de renda fixa com vencimento nos próximos N meses."""
    hoje  = date.today()
    m_fim = hoje.month - 1 + meses
    ano_f = hoje.year + m_fim // 12
    mes_f = m_fim % 12 + 1
    import calendar
    ultimo_dia = calendar.monthrange(ano_f, mes_f)[1]
    limite = f"{ano_f:04d}-{mes_f:02d}-{ultimo_dia:02d}"
    with conectar() as conn:
        rows = conn.execute("""
            SELECT a.codigo, a.nome, a.tipo, a.vencimento,
                   a.taxa_contratada, a.indexador,
                   COALESCE(pc.valor_atual, pc.valor_investido, 0) AS valor_estimado
            FROM   ativos a
            LEFT JOIN posicao_cache pc ON pc.ativo_id = a.id
            WHERE  a.vencimento IS NOT NULL AND a.vencimento != ''
              AND  a.vencimento >= ? AND a.vencimento <= ?
              AND  a.ativo = 1
            ORDER  BY a.vencimento
        """, (hoje.strftime("%Y-%m-%d"), limite)).fetchall()
    return [dict(r) for r in rows]


def estimar_valor_atual_rf(valor_investido: float, taxa_anual: float,
                            data_aplicacao: str,
                            data_base: Optional[str] = None) -> float:
    """
    Estimativa de valor atual por juros compostos simples.
    taxa_anual em % a.a. (ex: 13.5 → 13,5% a.a.).

    # FUTURE: plugar indexadores reais (CDI, SELIC, IPCA) via cotacao_service
    # quando o serviço de API estiver disponível.
    """
    if valor_investido <= 0 or taxa_anual <= 0:
        return valor_investido
    try:
        d_ini = date.fromisoformat(data_aplicacao)
        d_fim = date.fromisoformat(data_base) if data_base else date.today()
        dias  = (d_fim - d_ini).days
        if dias <= 0:
            return valor_investido
        return round(valor_investido * ((1 + taxa_anual / 100) ** (dias / 365)), 2)
    except Exception:
        return valor_investido


# ─────────────────────────────────────────────────────────────────────────────
# Leitura para o extrato financeiro (entradas de investimento)
# ─────────────────────────────────────────────────────────────────────────────

def rendimentos_financeiros_mes(mes: int, ano: int) -> list[dict]:
    """
    Retorna entradas de investimento do mês (venda, resgate, dividendo, etc.)
    com registrar_no_financeiro=1, para exibição no Extrato de Caixa.
    """
    inicio = f"{ano:04d}-{mes:02d}-01"
    fim    = f"{ano:04d}-{mes+1:02d}-01" if mes < 12 else f"{ano+1:04d}-01-01"
    with conectar() as conn:
        rows = conn.execute("""
            SELECT m.data, m.tipo, m.valor_liquido, a.codigo
            FROM   movimentacoes_investimento m
            JOIN   ativos a ON a.id = m.ativo_id
            WHERE  m.registrar_no_financeiro = 1
              AND  m.tipo IN ('venda','resgate','dividendo','jcp','juros','amortizacao')
              AND  m.data >= ? AND m.data < ?
            ORDER  BY m.data
        """, (inicio, fim)).fetchall()

    _labels = {
        "venda": "Venda", "resgate": "Resgate", "dividendo": "Dividendo",
        "jcp": "JCP", "juros": "Juros/Rendimento", "amortizacao": "Amortização",
    }
    return [{
        "data":      r["data"],
        "descricao": f"{_labels.get(r['tipo'], r['tipo'])} — {r['codigo']}",
        "categoria": "Rendimento de investimento",
        "debito":    0.0,
        "credito":   r["valor_liquido"],
        "tipo":      "receita",
        "status":    "",
    } for r in rows]
