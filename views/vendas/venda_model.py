"""
venda_model.py — Model do módulo de Vendas do Serenus.

Responsabilidades:
- CRUD de produtos e serviços
- Registro de vendas à vista e a prazo
- Geração e quitação de contas a receber
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from database import conectar


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Produto:
    id:        int
    nome:      str
    tipo:      str    # 'produto' | 'servico'
    preco:     float
    descricao: str
    ativo:     bool
    criado_em: str


@dataclass
class ItemVenda:
    id:         int
    venda_id:   int
    produto_id: Optional[int]
    descricao:  str
    quantidade: float
    preco_unit: float
    subtotal:   float
    criado_em:  str


@dataclass
class ContaReceber:
    id:               int
    venda_id:         Optional[int]
    descricao:        str
    valor:            float
    data_vencimento:  str
    data_recebimento: Optional[str]
    status:           str    # 'pendente' | 'recebido' | 'cancelado'
    numero_parcela:   int
    total_parcelas:   int
    observacao:       str
    criado_em:        str


@dataclass
class Venda:
    id:             int
    descricao:      str
    data_venda:     str
    valor_total:    float
    desconto:       float
    valor_liquido:  float
    tipo_pagamento: str   # 'avista' | 'aprazo'
    status:         str   # 'pendente' | 'paga' | 'parcial' | 'cancelada'
    observacao:     str
    criado_em:      str
    itens:                  list[ItemVenda] = field(default_factory=list)
    recebimentos_pendentes: int = 0
    recebimentos_recebidos: int = 0


# ---------------------------------------------------------------------------
# Conversores privados
# ---------------------------------------------------------------------------

def _row_to_produto(r) -> Produto:
    d = dict(r)
    return Produto(
        id=d["id"],
        nome=d["nome"],
        tipo=d.get("tipo") or "produto",
        preco=float(d["preco"]),
        descricao=d.get("descricao") or "",
        ativo=bool(d["ativo"]),
        criado_em=d["criado_em"],
    )


def _row_to_item(r) -> ItemVenda:
    d = dict(r)
    return ItemVenda(
        id=d["id"],
        venda_id=d["venda_id"],
        produto_id=d.get("produto_id"),
        descricao=d["descricao"],
        quantidade=float(d["quantidade"]),
        preco_unit=float(d["preco_unit"]),
        subtotal=float(d["subtotal"]),
        criado_em=d["criado_em"],
    )


def _row_to_conta_receber(r) -> ContaReceber:
    d = dict(r)
    return ContaReceber(
        id=d["id"],
        venda_id=d.get("venda_id"),
        descricao=d["descricao"],
        valor=float(d["valor"]),
        data_vencimento=d["data_vencimento"],
        data_recebimento=d.get("data_recebimento"),
        status=d["status"],
        numero_parcela=d.get("numero_parcela") or 1,
        total_parcelas=d.get("total_parcelas") or 1,
        observacao=d.get("observacao") or "",
        criado_em=d["criado_em"],
    )


def _row_to_venda(r) -> Venda:
    d = dict(r)
    return Venda(
        id=d["id"],
        descricao=d.get("descricao") or "",
        data_venda=d["data_venda"],
        valor_total=float(d["valor_total"]),
        desconto=float(d["desconto"]),
        valor_liquido=float(d["valor_liquido"]),
        tipo_pagamento=d["tipo_pagamento"],
        status=d["status"],
        observacao=d.get("observacao") or "",
        criado_em=d["criado_em"],
        recebimentos_pendentes=d.get("recebimentos_pendentes") or 0,
        recebimentos_recebidos=d.get("recebimentos_recebidos") or 0,
    )


# ---------------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------------

def listar_produtos(apenas_ativos: bool = False) -> list[Produto]:
    sql = "SELECT * FROM produtos"
    if apenas_ativos:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY nome"
    with conectar() as conn:
        rows = conn.execute(sql).fetchall()
    return [_row_to_produto(r) for r in rows]


def salvar_produto(dados: dict, id: int | None = None) -> int:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        if id:
            conn.execute(
                "UPDATE produtos SET nome=?, tipo=?, preco=?, descricao=?, ativo=?"
                " WHERE id=?",
                (dados["nome"], dados.get("tipo", "produto"), float(dados["preco"]),
                 dados.get("descricao", ""), int(bool(dados.get("ativo", True))), id),
            )
            return id
        cur = conn.execute(
            "INSERT INTO produtos (nome, tipo, preco, descricao, ativo, criado_em)"
            " VALUES (?,?,?,?,?,?)",
            (dados["nome"], dados.get("tipo", "produto"), float(dados["preco"]),
             dados.get("descricao", ""), int(bool(dados.get("ativo", True))), agora),
        )
        return cur.lastrowid


def excluir_produto(id: int) -> tuple[bool, str]:
    with conectar() as conn:
        usado = conn.execute(
            "SELECT COUNT(*) FROM itens_venda WHERE produto_id=?", (id,)
        ).fetchone()[0]
        if usado > 0:
            return False, "Produto possui vendas registradas e não pode ser excluído."
        conn.execute("DELETE FROM produtos WHERE id=?", (id,))
    return True, ""


# ---------------------------------------------------------------------------
# Vendas — helpers internos
# ---------------------------------------------------------------------------

def _proximos_meses(data_iso: str, n: int) -> list[str]:
    """Retorna n datas mensais consecutivas a partir de data_iso (mesmo dia)."""
    d = date.fromisoformat(data_iso)
    datas = []
    for i in range(n):
        total = d.month - 1 + i
        ano   = d.year + total // 12
        mes   = total % 12 + 1
        dia   = min(d.day, monthrange(ano, mes)[1])
        datas.append(date(ano, mes, dia).isoformat())
    return datas


def _fim_mes(mes: int, ano: int) -> str:
    if mes < 12:
        return f"{ano:04d}-{mes + 1:02d}-01"
    return f"{ano + 1:04d}-01-01"


# ---------------------------------------------------------------------------
# Vendas — CRUD
# ---------------------------------------------------------------------------

def listar_vendas(mes: int, ano: int,
                  status: str | None = None) -> list[Venda]:
    inicio = f"{ano:04d}-{mes:02d}-01"
    fim    = _fim_mes(mes, ano)
    sql = """
        SELECT v.*,
               (SELECT COUNT(*) FROM contas_a_receber cr
                WHERE cr.venda_id = v.id AND cr.status = 'pendente') AS recebimentos_pendentes,
               (SELECT COUNT(*) FROM contas_a_receber cr
                WHERE cr.venda_id = v.id AND cr.status = 'recebido') AS recebimentos_recebidos
        FROM vendas v
        WHERE v.data_venda >= ? AND v.data_venda < ?
    """
    params: list = [inicio, fim]
    if status:
        sql += " AND v.status = ?"
        params.append(status)
    sql += " ORDER BY v.data_venda DESC, v.id DESC"
    with conectar() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_venda(r) for r in rows]


def obter_venda(id: int) -> Venda | None:
    with conectar() as conn:
        row = conn.execute("""
            SELECT v.*,
                   (SELECT COUNT(*) FROM contas_a_receber cr
                    WHERE cr.venda_id = v.id AND cr.status = 'pendente') AS recebimentos_pendentes,
                   (SELECT COUNT(*) FROM contas_a_receber cr
                    WHERE cr.venda_id = v.id AND cr.status = 'recebido') AS recebimentos_recebidos
            FROM vendas v WHERE v.id = ?
        """, (id,)).fetchone()
        if not row:
            return None
        venda = _row_to_venda(row)
        itens = conn.execute(
            "SELECT * FROM itens_venda WHERE venda_id=? ORDER BY id", (id,)
        ).fetchall()
    venda.itens = [_row_to_item(r) for r in itens]
    return venda


def salvar_venda(dados: dict, itens: list[dict]) -> int:
    """
    Cria uma venda com seus itens.
    À vista → status='paga', sem contas_a_receber.
    A prazo → status='pendente', gera N parcelas em contas_a_receber.
    Espera dados['parcelas'] e dados['data_primeira_parcela'] para a prazo.
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tipo  = dados.get("tipo_pagamento", "avista")

    for item in itens:
        item["subtotal"] = round(float(item["quantidade"]) * float(item["preco_unit"]), 2)

    valor_total   = round(sum(i["subtotal"] for i in itens), 2)
    desconto      = round(float(dados.get("desconto", 0.0)), 2)
    valor_liquido = round(valor_total - desconto, 2)
    status        = "paga" if tipo == "avista" else "pendente"

    with conectar() as conn:
        cur = conn.execute(
            """INSERT INTO vendas
               (descricao, data_venda, valor_total, desconto, valor_liquido,
                tipo_pagamento, status, observacao, criado_em)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (dados.get("descricao", ""), dados["data_venda"],
             valor_total, desconto, valor_liquido,
             tipo, status, dados.get("observacao", ""), agora),
        )
        venda_id = cur.lastrowid

        for item in itens:
            conn.execute(
                """INSERT INTO itens_venda
                   (venda_id, produto_id, descricao, quantidade,
                    preco_unit, subtotal, criado_em)
                   VALUES (?,?,?,?,?,?,?)""",
                (venda_id, item.get("produto_id"), item["descricao"],
                 float(item["quantidade"]), float(item["preco_unit"]),
                 item["subtotal"], agora),
            )

        if tipo == "aprazo":
            n_parcelas   = max(1, int(dados.get("parcelas", 1)))
            data_inicio  = dados.get("data_primeira_parcela") or dados["data_venda"]
            val_parcela  = round(valor_liquido / n_parcelas, 2)
            datas        = _proximos_meses(data_inicio, n_parcelas)
            desc_base    = dados.get("descricao") or "Venda"

            for i, dt in enumerate(datas, start=1):
                # Última parcela absorve diferença de arredondamento
                v = (val_parcela if i < n_parcelas
                     else round(valor_liquido - val_parcela * (n_parcelas - 1), 2))
                conn.execute(
                    """INSERT INTO contas_a_receber
                       (venda_id, descricao, valor, data_vencimento, status,
                        numero_parcela, total_parcelas, observacao, criado_em)
                       VALUES (?,?,?,?,'pendente',?,?,'',?)""",
                    (venda_id, f"{desc_base} ({i}/{n_parcelas})",
                     v, dt, i, n_parcelas, agora),
                )

    return venda_id


def cancelar_venda(id: int) -> None:
    with conectar() as conn:
        conn.execute("UPDATE vendas SET status='cancelada' WHERE id=?", (id,))
        conn.execute(
            "UPDATE contas_a_receber SET status='cancelado'"
            " WHERE venda_id=? AND status='pendente'",
            (id,),
        )


# ---------------------------------------------------------------------------
# Contas a receber
# ---------------------------------------------------------------------------

def listar_contas_receber(status: str | None = None) -> list[ContaReceber]:
    sql    = "SELECT * FROM contas_a_receber"
    params: list = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY data_vencimento, id"
    with conectar() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_conta_receber(r) for r in rows]


def marcar_recebido(id: int, data_recebimento: str) -> None:
    """Marca uma parcela como recebida. No-op se já estiver recebida ou cancelada
    — evita ressuscitar parcelas canceladas ou sobrescrever data_recebimento."""
    with conectar() as conn:
        cur = conn.execute(
            "UPDATE contas_a_receber"
            " SET status='recebido', data_recebimento=?"
            " WHERE id=? AND status='pendente'",
            (data_recebimento, id),
        )
        if cur.rowcount == 0:
            return
        row = conn.execute(
            "SELECT venda_id FROM contas_a_receber WHERE id=?", (id,)
        ).fetchone()
        if not row or not row["venda_id"]:
            return
        venda_id = row["venda_id"]

        counts = conn.execute("""
            SELECT
                SUM(CASE WHEN status='recebido' THEN 1 ELSE 0 END) AS recebidos,
                SUM(CASE WHEN status='pendente' THEN 1 ELSE 0 END) AS pendentes
            FROM contas_a_receber
            WHERE venda_id=? AND status != 'cancelado'
        """, (venda_id,)).fetchone()

        if counts["pendentes"] == 0:
            novo_status = "paga"
        elif counts["recebidos"] > 0:
            novo_status = "parcial"
        else:
            novo_status = "pendente"

        conn.execute(
            "UPDATE vendas SET status=? WHERE id=?", (novo_status, venda_id)
        )
