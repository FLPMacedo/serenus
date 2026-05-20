"""
os_model.py — Model do módulo de Ordem de Serviço (OS Interna) do Serenus.

Responsabilidades:
- Numeração sequencial automática (OS-NNNN)
- CRUD de ordens de serviço com itens (materiais/serviços reusando produtos)
- Cálculos de totais (materiais, mão de obra, valor total) na própria OS
- Histórico de alterações (auditoria campo a campo)
- Filtros e busca textual

A OS interna NÃO gera lançamento financeiro automático — os valores são
apenas para compreensão/relatório do serviço. Lançamento em contas_pagar
ou receitas é manual, fora deste módulo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from database import conectar


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ItemOS:
    id:         int
    os_id:      int
    produto_id: Optional[int]
    descricao:  str
    quantidade: float
    preco_unit: float
    subtotal:   float
    observacao: str
    criado_em:  str


@dataclass
class OSHistorico:
    id:             int
    os_id:          int
    campo:          str
    valor_anterior: Optional[str]
    valor_novo:     Optional[str]
    alterado_em:    str


@dataclass
class OrdemServico:
    id:                 int
    numero:             str
    cliente_id:         Optional[int]
    solicitante_nome:   str
    solicitante_setor:  str
    solicitante_ramal:  str
    data_solicitacao:   str
    hora_solicitacao:   str
    data_execucao:      Optional[str]
    hora_execucao:      str
    descricao_servico:  str
    observacoes:        str
    responsavel:        str
    status:             str
    valor_hora:         float
    horas_trabalhadas:  float
    criado_em:          str
    itens: list[ItemOS] = field(default_factory=list)

    @property
    def total_materiais(self) -> float:
        return round(sum(i.subtotal for i in self.itens), 2)

    @property
    def valor_mao_obra(self) -> float:
        return round(self.valor_hora * self.horas_trabalhadas, 2)

    @property
    def valor_total(self) -> float:
        return round(self.total_materiais + self.valor_mao_obra, 2)


# ---------------------------------------------------------------------------
# Conversores privados
# ---------------------------------------------------------------------------

def _row_to_os(r) -> OrdemServico:
    d = dict(r)
    return OrdemServico(
        id=d["id"],
        numero=d["numero"],
        cliente_id=d.get("cliente_id"),
        solicitante_nome=d.get("solicitante_nome") or "",
        solicitante_setor=d.get("solicitante_setor") or "",
        solicitante_ramal=d.get("solicitante_ramal") or "",
        data_solicitacao=d["data_solicitacao"],
        hora_solicitacao=d.get("hora_solicitacao") or "",
        data_execucao=d.get("data_execucao"),
        hora_execucao=d.get("hora_execucao") or "",
        descricao_servico=d.get("descricao_servico") or "",
        observacoes=d.get("observacoes") or "",
        responsavel=d.get("responsavel") or "",
        status=d["status"],
        valor_hora=float(d.get("valor_hora") or 0.0),
        horas_trabalhadas=float(d.get("horas_trabalhadas") or 0.0),
        criado_em=d["criado_em"],
    )


def _row_to_item_os(r) -> ItemOS:
    d = dict(r)
    return ItemOS(
        id=d["id"],
        os_id=d["os_id"],
        produto_id=d.get("produto_id"),
        descricao=d["descricao"],
        quantidade=float(d["quantidade"]),
        preco_unit=float(d["preco_unit"]),
        subtotal=float(d["subtotal"]),
        observacao=d.get("observacao") or "",
        criado_em=d["criado_em"],
    )


def _row_to_historico(r) -> OSHistorico:
    d = dict(r)
    return OSHistorico(
        id=d["id"],
        os_id=d["os_id"],
        campo=d["campo"],
        valor_anterior=d.get("valor_anterior"),
        valor_novo=d.get("valor_novo"),
        alterado_em=d["alterado_em"],
    )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

_CAMPOS_RASTREADOS_OS = [
    "cliente_id",
    "solicitante_nome", "solicitante_setor", "solicitante_ramal",
    "data_solicitacao", "hora_solicitacao",
    "data_execucao",    "hora_execucao",
    "descricao_servico", "observacoes",
    "responsavel", "status",
    "valor_hora", "horas_trabalhadas",
]


def _fim_mes(mes: int, ano: int) -> str:
    if mes < 12:
        return f"{ano:04d}-{mes + 1:02d}-01"
    return f"{ano + 1:04d}-01-01"


def _registrar_alteracao(conn, os_id: int, campo: str,
                          anterior, novo, agora: str) -> None:
    """Insere um registro de alteração em os_historico."""
    conn.execute(
        "INSERT INTO os_historico"
        " (os_id, campo, valor_anterior, valor_novo, alterado_em)"
        " VALUES (?,?,?,?,?)",
        (
            os_id,
            campo,
            None if anterior is None else str(anterior),
            None if novo is None else str(novo),
            agora,
        ),
    )


def _persistir_itens(conn, os_id: int, itens: list[dict], agora: str) -> None:
    """Insere a lista de itens da OS, calculando subtotal.

    Rejeita preco_unit < 0 e quantidade <= 0 (defesa em profundidade —
    UI também valida, mas model é o gatekeeper).
    """
    for it in itens:
        quantidade = float(it["quantidade"])
        preco_unit = float(it["preco_unit"])
        if preco_unit < 0:
            raise ValueError(
                f"Preço unitário não pode ser negativo (item '{it.get('descricao', '?')}')."
            )
        if quantidade <= 0:
            raise ValueError(
                f"Quantidade deve ser maior que zero (item '{it.get('descricao', '?')}')."
            )
        subtotal = round(quantidade * preco_unit, 2)
        conn.execute(
            """INSERT INTO itens_os
               (os_id, produto_id, descricao, quantidade,
                preco_unit, subtotal, observacao, criado_em)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                os_id,
                it.get("produto_id"),
                it["descricao"],
                float(it["quantidade"]),
                float(it["preco_unit"]),
                subtotal,
                it.get("observacao", ""),
                agora,
            ),
        )


# ---------------------------------------------------------------------------
# Numeração
# ---------------------------------------------------------------------------

def proximo_numero_os() -> str:
    """Retorna o próximo número sequencial no formato 'OS-NNNN'.

    Segue MAX(numero) + 1 — gaps por exclusão não são reusados.
    """
    with conectar() as conn:
        row = conn.execute(
            "SELECT MAX(CAST(SUBSTR(numero, 4) AS INTEGER)) AS max_num"
            " FROM ordens_servico WHERE numero LIKE 'OS-%'"
        ).fetchone()
    max_num = row["max_num"] if row and row["max_num"] is not None else 0
    return f"OS-{max_num + 1:04d}"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def _validar_dados_os(dados: dict) -> None:
    """Valida valor_hora e horas_trabalhadas (>= 0). Levanta ValueError."""
    vh = float(dados.get("valor_hora", 0.0) or 0.0)
    ht = float(dados.get("horas_trabalhadas", 0.0) or 0.0)
    if vh < 0:
        raise ValueError(f"Valor por hora não pode ser negativo (recebido: {vh}).")
    if ht < 0:
        raise ValueError(f"Horas trabalhadas não pode ser negativo (recebido: {ht}).")


def salvar_os(dados: dict, itens: list[dict]) -> int:
    """Cria uma nova OS com seus itens, gera numero e registra histórico."""
    _validar_dados_os(dados)
    agora  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    numero = proximo_numero_os()

    with conectar() as conn:
        cur = conn.execute(
            """INSERT INTO ordens_servico
               (numero, cliente_id,
                solicitante_nome, solicitante_setor, solicitante_ramal,
                data_solicitacao, hora_solicitacao,
                data_execucao, hora_execucao,
                descricao_servico, observacoes,
                responsavel, status,
                valor_hora, horas_trabalhadas, criado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                numero,
                dados.get("cliente_id"),
                dados.get("solicitante_nome", ""),
                dados.get("solicitante_setor", ""),
                dados.get("solicitante_ramal", ""),
                dados["data_solicitacao"],
                dados.get("hora_solicitacao", ""),
                dados.get("data_execucao"),
                dados.get("hora_execucao", ""),
                dados.get("descricao_servico", ""),
                dados.get("observacoes", ""),
                dados.get("responsavel", ""),
                dados.get("status", "aberta"),
                float(dados.get("valor_hora", 0.0)),
                float(dados.get("horas_trabalhadas", 0.0)),
                agora,
            ),
        )
        os_id = cur.lastrowid
        _persistir_itens(conn, os_id, itens, agora)
        _registrar_alteracao(conn, os_id, "criacao", None, numero, agora)

    return os_id


def _obter_os_em_conn(conn, id: int) -> "OrdemServico | None":
    """Versão interna de obter_os que reusa uma conexão já aberta —
    permite atomicidade quando combinada com UPDATE/INSERT na mesma transação."""
    row = conn.execute(
        "SELECT * FROM ordens_servico WHERE id=?", (id,)
    ).fetchone()
    if row is None:
        return None
    os_obj = _row_to_os(row)
    itens_rows = conn.execute(
        "SELECT * FROM itens_os WHERE os_id=? ORDER BY id", (id,)
    ).fetchall()
    os_obj.itens = [_row_to_item_os(r) for r in itens_rows]
    return os_obj


def atualizar_os(id: int, dados: dict, itens: list[dict]) -> None:
    """Atualiza campos da OS, substitui itens e registra diffs no histórico.

    Itens são substituídos via delete + insert (mais simples e atômico).
    Mudanças nos campos rastreados geram entradas em os_historico; campos
    sem alteração são ignorados.

    Toda a operação roda em uma única conexão SQLite — o SELECT (snapshot
    atual), o cálculo de diffs, o UPDATE dos campos e o DELETE+INSERT dos
    itens compartilham a mesma transação, garantindo atomicidade.
    """
    _validar_dados_os(dados)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with conectar() as conn:
        atual = _obter_os_em_conn(conn, id)
        if atual is None:
            return

        for campo in _CAMPOS_RASTREADOS_OS:
            valor_anterior = getattr(atual, campo)
            valor_novo     = dados.get(campo, valor_anterior)
            # Normaliza tipos para comparação justa (float vs int, None vs "")
            if isinstance(valor_anterior, float) or isinstance(valor_novo, float):
                try:
                    if float(valor_anterior or 0.0) == float(valor_novo or 0.0):
                        continue
                except (TypeError, ValueError):
                    pass
            if valor_anterior == valor_novo:
                continue
            _registrar_alteracao(conn, id, campo, valor_anterior, valor_novo, agora)

        conn.execute(
            """UPDATE ordens_servico SET
                cliente_id=?,
                solicitante_nome=?, solicitante_setor=?, solicitante_ramal=?,
                data_solicitacao=?, hora_solicitacao=?,
                data_execucao=?,    hora_execucao=?,
                descricao_servico=?, observacoes=?,
                responsavel=?, status=?,
                valor_hora=?, horas_trabalhadas=?
               WHERE id=?""",
            (
                dados.get("cliente_id",        atual.cliente_id),
                dados.get("solicitante_nome",  atual.solicitante_nome),
                dados.get("solicitante_setor", atual.solicitante_setor),
                dados.get("solicitante_ramal", atual.solicitante_ramal),
                dados.get("data_solicitacao",  atual.data_solicitacao),
                dados.get("hora_solicitacao",  atual.hora_solicitacao),
                dados.get("data_execucao",     atual.data_execucao),
                dados.get("hora_execucao",     atual.hora_execucao),
                dados.get("descricao_servico", atual.descricao_servico),
                dados.get("observacoes",       atual.observacoes),
                dados.get("responsavel",       atual.responsavel),
                dados.get("status",            atual.status),
                float(dados.get("valor_hora", atual.valor_hora)),
                float(dados.get("horas_trabalhadas", atual.horas_trabalhadas)),
                id,
            ),
        )

        conn.execute("DELETE FROM itens_os WHERE os_id=?", (id,))
        _persistir_itens(conn, id, itens, agora)


def cancelar_os(id: int) -> None:
    """Marca a OS como cancelada e registra a transição no histórico.

    No-op se a OS já estiver cancelada ou não existir.
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        row = conn.execute(
            "SELECT status FROM ordens_servico WHERE id=?", (id,)
        ).fetchone()
        if row is None or row["status"] == "cancelada":
            return
        _registrar_alteracao(conn, id, "status", row["status"], "cancelada", agora)
        conn.execute(
            "UPDATE ordens_servico SET status='cancelada' WHERE id=?", (id,)
        )


def obter_os(id: int) -> OrdemServico | None:
    """Obtém uma OS pelo id com seus itens carregados."""
    with conectar() as conn:
        row = conn.execute(
            "SELECT * FROM ordens_servico WHERE id=?", (id,)
        ).fetchone()
        if row is None:
            return None
        os_obj = _row_to_os(row)
        itens  = conn.execute(
            "SELECT * FROM itens_os WHERE os_id=? ORDER BY id", (id,)
        ).fetchall()
    os_obj.itens = [_row_to_item_os(r) for r in itens]
    return os_obj


def listar_os(status: str | None = None,
              ano:    int | None = None,
              mes:    int | None = None,
              solicitante: str | None = None,
              busca:  str | None = None,
              cliente_id: int | None = None) -> list[OrdemServico]:
    """Lista ordens de serviço com filtros opcionais.

    - status: 'aberta' | 'em_andamento' | 'aguardando_peca' | 'concluida' | 'cancelada'
    - ano + mes: filtra por mês de data_solicitacao
    - solicitante: LIKE case-insensitive em solicitante_nome
    - busca: LIKE case-insensitive em numero, solicitante_nome,
             descricao_servico, observacoes (filtragem em Python para unicode seguro)
    - cliente_id: retorna apenas OS vinculadas ao cliente indicado
    """
    sql    = "SELECT * FROM ordens_servico"
    conds  = []
    params: list = []

    if status:
        conds.append("status = ?")
        params.append(status)

    if ano is not None and mes is not None:
        inicio = f"{ano:04d}-{mes:02d}-01"
        fim    = _fim_mes(mes, ano)
        conds.append("data_solicitacao >= ? AND data_solicitacao < ?")
        params.extend([inicio, fim])

    if solicitante:
        conds.append("LOWER(solicitante_nome) LIKE ?")
        params.append(f"%{solicitante.lower()}%")

    if cliente_id is not None:
        conds.append("cliente_id = ?")
        params.append(cliente_id)

    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY id DESC"

    with conectar() as conn:
        rows = conn.execute(sql, params).fetchall()
        lista = [_row_to_os(r) for r in rows]

        # Carrega itens em batch (1 query) para popular as properties
        # total_materiais e valor_total — usadas pelos cards da listagem.
        if lista:
            os_ids       = [o.id for o in lista]
            placeholders = ",".join("?" * len(os_ids))
            itens_rows   = conn.execute(
                f"SELECT * FROM itens_os WHERE os_id IN ({placeholders})"
                " ORDER BY os_id, id",
                os_ids,
            ).fetchall()
            itens_por_os: dict[int, list[ItemOS]] = {}
            for r in itens_rows:
                itens_por_os.setdefault(r["os_id"], []).append(
                    _row_to_item_os(r)
                )
            for o in lista:
                o.itens = itens_por_os.get(o.id, [])

    if busca:
        b = busca.lower()
        lista = [
            o for o in lista
            if (b in o.numero.lower()
                or b in o.solicitante_nome.lower()
                or b in o.descricao_servico.lower()
                or b in o.observacoes.lower())
        ]

    return lista


# ---------------------------------------------------------------------------
# Histórico
# ---------------------------------------------------------------------------

def listar_historico(os_id: int) -> list[OSHistorico]:
    """Lista alterações da OS ordenadas da mais recente para a mais antiga."""
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM os_historico WHERE os_id=?"
            " ORDER BY alterado_em DESC, id DESC",
            (os_id,),
        ).fetchall()
    return [_row_to_historico(r) for r in rows]
