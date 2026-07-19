"""
agenda_model.py — Agenda agregada de compromissos do Serenus.

Combina em uma única visão cronológica:

  • Contas a pagar (com vencimento no período)
  • Receitas previstas (fontes ativas + receitas especiais)
  • Ordens de Serviço (com data_execucao agendada)
  • Eventos avulsos (lembretes manuais — tabela agenda_eventos)

Cada item agregado vira um dict no formato:

    {
        "tipo":     "despesa" | "receita" | "os" | "evento",
        "data":     "YYYY-MM-DD",
        "hora":     "HH:MM" | "",
        "titulo":   "Nome curto",
        "subtitulo":"Detalhe (opcional)",
        "valor":    float (negativo=saída, positivo=entrada) | None,
        "ref_id":   id do registro de origem,
        "concluido":bool,           # só faz sentido para 'evento' e 'despesa(pago)'
        "cor":      "#hex",         # cor sugerida pra UI
    }

A tabela `agenda_eventos` armazena apenas os compromissos AVULSOS — os
demais são lidos das tabelas existentes via JOIN/SELECT.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from database import conectar


# ---------------------------------------------------------------------------
# Cores (paleta consistente com o resto do app)
# ---------------------------------------------------------------------------

COR_DESPESA = "#DC2626"      # vermelho (alerta)
COR_RECEITA = "#16A34A"      # verde (positivo)
COR_OS      = "#2563EB"      # azul
COR_EVENTO  = "#7C3AED"      # roxo (pessoal)


# ---------------------------------------------------------------------------
# Eventos avulsos — tabela agenda_eventos
# ---------------------------------------------------------------------------

CATEGORIAS_EVENTO = ("pessoal", "trabalho", "saude", "outro")


@dataclass
class EventoAgenda:
    id:         int
    titulo:     str
    descricao:  str
    data:       str        # YYYY-MM-DD
    hora:       str        # HH:MM ou ''
    categoria:  str
    concluido:  bool
    criado_em:  str


def _row_to_evento(r) -> EventoAgenda:
    d = dict(r)
    return EventoAgenda(
        id        = d["id"],
        titulo    = d["titulo"],
        descricao = d.get("descricao") or "",
        data      = d["data"],
        hora      = d.get("hora") or "",
        categoria = d.get("categoria") or "outro",
        concluido = bool(d.get("concluido", 0)),
        criado_em = d.get("criado_em") or "",
    )


def salvar_evento(dados: dict, id: Optional[int] = None) -> int:
    """Cria/atualiza um evento avulso. Retorna o id."""
    titulo = (dados.get("titulo") or "").strip()
    if not titulo:
        raise ValueError("Título do evento é obrigatório.")
    data_iso = (dados.get("data") or "").strip()
    if not data_iso:
        raise ValueError("Data do evento é obrigatória.")
    categoria = dados.get("categoria") or "pessoal"
    if categoria not in CATEGORIAS_EVENTO:
        raise ValueError(f"Categoria inválida: {categoria}")

    hora = (dados.get("hora") or "").strip()
    descricao = (dados.get("descricao") or "").strip()
    concluido = int(bool(dados.get("concluido", False)))
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with conectar() as conn:
        if id is not None:
            conn.execute("""
                UPDATE agenda_eventos
                SET titulo=?, descricao=?, data=?, hora=?, categoria=?, concluido=?
                WHERE id=?
            """, (titulo, descricao, data_iso, hora, categoria, concluido, id))
            return id
        else:
            cur = conn.execute("""
                INSERT INTO agenda_eventos
                (titulo, descricao, data, hora, categoria, concluido, criado_em)
                VALUES (?,?,?,?,?,?,?)
            """, (titulo, descricao, data_iso, hora, categoria, concluido, agora))
            return cur.lastrowid


def excluir_evento(id: int) -> None:
    with conectar() as conn:
        conn.execute("DELETE FROM agenda_eventos WHERE id=?", (id,))


def alternar_concluido_evento(id: int, concluido: bool) -> None:
    with conectar() as conn:
        conn.execute("UPDATE agenda_eventos SET concluido=? WHERE id=?",
                     (int(concluido), id))


def listar_eventos_periodo(data_ini: str, data_fim: str) -> list[EventoAgenda]:
    """Lista eventos avulsos no intervalo (inclusive). Datas em YYYY-MM-DD."""
    with conectar() as conn:
        rows = conn.execute("""
            SELECT * FROM agenda_eventos
            WHERE data BETWEEN ? AND ?
            ORDER BY data, hora, titulo
        """, (data_ini, data_fim)).fetchall()
    return [_row_to_evento(r) for r in rows]


def obter_evento(id: int) -> Optional[EventoAgenda]:
    with conectar() as conn:
        r = conn.execute("SELECT * FROM agenda_eventos WHERE id=?", (id,)).fetchone()
    return _row_to_evento(r) if r else None


# ---------------------------------------------------------------------------
# Agregador — junta despesas, receitas, OS e eventos num único feed
# ---------------------------------------------------------------------------

def _despesas_periodo(conn, data_ini: str, data_fim: str) -> list[dict]:
    """Contas a pagar com vencimento no intervalo."""
    rows = conn.execute("""
        SELECT cp.id, cp.descricao, cp.valor, cp.data_vencimento, cp.status,
               pc.nome AS plano_nome
        FROM contas_pagar cp
        LEFT JOIN plano_contas pc ON pc.id = cp.plano_conta_id
        WHERE cp.data_vencimento BETWEEN ? AND ?
          AND cp.status != 'cancelado'
        ORDER BY cp.data_vencimento, cp.descricao
    """, (data_ini, data_fim)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        out.append({
            "tipo":      "despesa",
            "data":      d["data_vencimento"],
            "hora":      "",
            "titulo":    d.get("plano_nome") or "Despesa",
            "subtitulo": d.get("descricao") or "",
            "valor":     -abs(float(d["valor"] or 0.0)),
            "ref_id":    d["id"],
            "concluido": (d.get("status") == "pago"),
            "cor":       COR_DESPESA,
            "status":    d.get("status") or "pendente",
        })
    return out


def _receitas_especiais_periodo(conn, data_ini: str, data_fim: str) -> list[dict]:
    """
    Receitas especiais caem no mês configurado. Como a tabela guarda só `mes`
    (0..11), expandimos para cada ano dentro do período onde o mês cai.
    Mostramos no DIA 1 do mês (default — usuário sabe que é receita mensal).
    """
    rows = conn.execute("SELECT * FROM receitas_especiais ORDER BY mes").fetchall()
    if not rows:
        return []
    di = datetime.strptime(data_ini, "%Y-%m-%d").date()
    df = datetime.strptime(data_fim, "%Y-%m-%d").date()
    out = []
    # itera ano-mês dentro do range
    ano, mes = di.year, di.month
    while (ano, mes) <= (df.year, df.month):
        for r in rows:
            d = dict(r)
            if int(d["mes"]) + 1 != mes:   # tabela usa 0..11; mês iter usa 1..12
                continue
            dia = 1
            try:
                data_evt = date(ano, mes, dia)
            except ValueError:
                continue
            if data_evt < di or data_evt > df:
                continue
            out.append({
                "tipo":      "receita",
                "data":      data_evt.isoformat(),
                "hora":      "",
                "titulo":    d["nome"],
                "subtitulo": "Receita especial",
                "valor":     float(d["valor"] or 0.0),
                "ref_id":    d["id"],
                "concluido": False,
                "cor":       COR_RECEITA,
                "status":    "previsto",
            })
        # next month
        if mes == 12:
            ano, mes = ano + 1, 1
        else:
            mes += 1
    return out


DIA_PAGAMENTO_PADRAO = 5  # fallback quando a fonte não tem dia_pagamento


def _receitas_fontes_periodo(conn, data_ini: str, data_fim: str) -> list[dict]:
    """
    Fontes de receita ativas — geram uma entrada por mês no período.

    Se a fonte não tem `dia_pagamento` configurado, usa dia 5 como padrão
    (típico de salário/freela no Brasil) e marca no subtítulo como
    "dia previsto" pra deixar claro pro usuário que pode editar a fonte
    pra definir o dia real.

    Fontes bimestrais/anuais seguem a MESMA convenção do resto do app
    (Receitas, Projeção, Fluxo de Caixa): o valor é rateado por mês
    (÷2 / ÷12) — não há mês-âncora cadastrado pra saber em qual mês o
    pagamento realmente cai. O subtítulo marca "média mensal".
    """
    rows = conn.execute("""
        SELECT id, nome, tipo, valor_mensal, dia_pagamento, periodicidade
        FROM fontes_receita
        WHERE ativa = 1
    """).fetchall()
    if not rows:
        return []
    import calendar as _cal
    di = datetime.strptime(data_ini, "%Y-%m-%d").date()
    df = datetime.strptime(data_fim, "%Y-%m-%d").date()
    out = []
    ano, mes = di.year, di.month
    while (ano, mes) <= (df.year, df.month):
        for r in rows:
            d = dict(r)
            periodicidade = d.get("periodicidade") or "mensal"
            valor = float(d["valor_mensal"] or 0.0)
            if periodicidade == "bimestral":
                valor /= 2
            elif periodicidade == "anual":
                valor /= 12

            dia_pag = d.get("dia_pagamento")
            estimado = dia_pag is None
            dia = int(dia_pag) if dia_pag is not None else DIA_PAGAMENTO_PADRAO
            # Se o dia configurado não existe no mês (ex: 31 em fevereiro),
            # usa o último dia do mês — mais útil que pular silenciosamente.
            ultimo_dia = _cal.monthrange(ano, mes)[1]
            if dia > ultimo_dia:
                dia = ultimo_dia
            try:
                data_evt = date(ano, mes, dia)
            except ValueError:
                continue
            if data_evt < di or data_evt > df:
                continue

            tipo = d.get("tipo") or "receita"
            sub = f"Fonte ({tipo})"
            if periodicidade != "mensal":
                sub += f" — média mensal ({periodicidade})"
            if estimado:
                sub += " — dia previsto"

            out.append({
                "tipo":      "receita",
                "data":      data_evt.isoformat(),
                "hora":      "",
                "titulo":    d["nome"],
                "subtitulo": sub,
                "valor":     valor,
                "ref_id":    d["id"],
                "concluido": False,
                "cor":       COR_RECEITA,
                "status":    "previsto",
            })
        if mes == 12:
            ano, mes = ano + 1, 1
        else:
            mes += 1
    return out


def _os_periodo(conn, data_ini: str, data_fim: str) -> list[dict]:
    """Ordens de Serviço com data_execucao no intervalo."""
    # A tabela ordens_servico existe se o módulo OS foi inicializado
    try:
        rows = conn.execute("""
            SELECT id, numero, descricao_servico, data_execucao, hora_execucao,
                   status, solicitante_nome
            FROM ordens_servico
            WHERE data_execucao IS NOT NULL
              AND data_execucao BETWEEN ? AND ?
            ORDER BY data_execucao, hora_execucao
        """, (data_ini, data_fim)).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        d = dict(r)
        # numero é TEXT ("OS-0003") — usa direto, sem reformatar
        out.append({
            "tipo":      "os",
            "data":      d["data_execucao"],
            "hora":      d.get("hora_execucao") or "",
            "titulo":    str(d["numero"]),
            "subtitulo": (d.get("descricao_servico") or "")[:80]
                          or d.get("solicitante_nome") or "",
            "valor":     None,
            "ref_id":    d["id"],
            "concluido": (d.get("status") == "concluida"),
            "cor":       COR_OS,
            "status":    d.get("status") or "aberta",
        })
    return out


def _eventos_avulsos_periodo(data_ini: str, data_fim: str) -> list[dict]:
    eventos = listar_eventos_periodo(data_ini, data_fim)
    return [{
        "tipo":      "evento",
        "data":      e.data,
        "hora":      e.hora,
        "titulo":    e.titulo,
        "subtitulo": e.descricao,
        "valor":     None,
        "ref_id":    e.id,
        "concluido": e.concluido,
        "cor":       COR_EVENTO,
        "status":    "ok",
        "categoria": e.categoria,
    } for e in eventos]


def compromissos_periodo(data_ini: str, data_fim: str,
                         tipos: Optional[set[str]] = None) -> list[dict]:
    """
    Retorna lista cronológica de compromissos no intervalo (inclusive).

    `tipos` restringe quais tipos retornar (subset de
    {'despesa','receita','os','evento'}). Se None, retorna todos.
    """
    if tipos is None:
        tipos = {"despesa", "receita", "os", "evento"}

    itens: list[dict] = []
    with conectar() as conn:
        if "despesa" in tipos:
            itens.extend(_despesas_periodo(conn, data_ini, data_fim))
        if "receita" in tipos:
            itens.extend(_receitas_especiais_periodo(conn, data_ini, data_fim))
            itens.extend(_receitas_fontes_periodo(conn, data_ini, data_fim))
        if "os" in tipos:
            itens.extend(_os_periodo(conn, data_ini, data_fim))
    if "evento" in tipos:
        itens.extend(_eventos_avulsos_periodo(data_ini, data_fim))

    itens.sort(key=lambda x: (x["data"], x.get("hora") or "", x["titulo"]))
    return itens


def compromissos_mes(ano: int, mes: int,
                     tipos: Optional[set[str]] = None) -> list[dict]:
    """Atalho — compromissos do mês inteiro (ano, mes 1..12)."""
    import calendar as _cal
    ultimo = _cal.monthrange(ano, mes)[1]
    di = date(ano, mes, 1).isoformat()
    df = date(ano, mes, ultimo).isoformat()
    return compromissos_periodo(di, df, tipos)


def proximos_dias(num_dias: int = 30,
                  tipos: Optional[set[str]] = None,
                  base: Optional[date] = None) -> list[dict]:
    """Compromissos dos próximos N dias a partir de `base` (default=hoje)."""
    base = base or date.today()
    df = base + timedelta(days=num_dias)
    return compromissos_periodo(base.isoformat(), df.isoformat(), tipos)


def agrupar_por_dia(itens: list[dict]) -> dict[str, list[dict]]:
    """{ 'YYYY-MM-DD': [item, item, ...] } preservando ordem de hora."""
    out: dict[str, list[dict]] = {}
    for it in itens:
        out.setdefault(it["data"], []).append(it)
    return out
