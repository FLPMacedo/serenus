"""
cartao_model.py — Lógica de negócio para Cartões de Crédito (Módulo 7).
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

from database import conectar, salvar_configuracao

# ---------------------------------------------------------------------------
# Constantes de design
# ---------------------------------------------------------------------------

CORES_BANCO: dict[str, str] = {
    "nubank":      "#6D28D9",
    "itau":        "#EC7000",
    "bradesco":    "#CC0000",
    "santander":   "#CC0000",
    "c6":          "#1A1A1A",
    "inter":       "#FF6600",
    "mercadopago": "#009EE3",
    "willbank":    "#00C4B4",
    "credicard":   "#CC0000",
    "magalu":      "#0086FF",
    "caixa":       "#006494",
    "bb":          "#FFCD00",
    "outro":       "#374151",
}

NOMES_BANCOS: dict[str, str] = {
    "nubank":      "Nubank",
    "itau":        "Itaú",
    "bradesco":    "Bradesco",
    "santander":   "Santander",
    "c6":          "C6 Bank",
    "inter":       "Banco Inter",
    "mercadopago": "Mercado Pago",
    "willbank":    "Will Bank",
    "credicard":   "Credicard",
    "magalu":      "Magalu",
    "caixa":       "Caixa",
    "bb":          "Banco do Brasil",
    "outro":       "Outro",
}

CORES_BANDEIRA: dict[str, str] = {
    "visa":      "#1A1F71",
    "master":    "#EB001B",
    "elo":       "#C8A200",
    "amex":      "#007B5E",
    "hipercard": "#CC0000",
    "cabal":     "#006DB0",
    "diners":    "#004A97",
    "discover":  "#F76F20",
    "hiper":     "#CC1C1C",
    "banescard": "#005BAA",
}

# Mapeamento bandeira → nome do arquivo em /imagens/
# Adicione mais arquivos PNG em /imagens/ e registre aqui.
BANDEIRAS_IMAGENS: dict[str, str] = {
    "visa":   "visa.png",
    "master": "mastercad.png",   # nome preservado conforme arquivo existente
    # "elo":   "elo.png",        # adicione elo.png em /imagens/ para ativar
    # "amex":  "amex.png",       # idem
}

BANDEIRAS = ["visa", "master", "elo", "amex", "hipercard",
             "cabal", "diners", "discover", "hiper", "banescard"]
BANDEIRAS_LABEL = [
    "Visa", "Mastercard", "Elo", "American Express", "Hipercard",
    "Cabal", "Diners Club", "Discover", "Hiper", "Banescard",
]


# ---------------------------------------------------------------------------
# Utilitários de imagem de bandeira
# ---------------------------------------------------------------------------

from _paths import IMAGENS_DIR as _IMAGENS_DIR


def carregar_logo_bandeira(bandeira: str, size: tuple[int, int] = (58, 36)):
    """
    Retorna CTkImage com o logo da bandeira, ou None se não houver arquivo.
    `size` = (largura, altura) em pixels dentro do card.
    """
    import customtkinter as _ctk
    filename = BANDEIRAS_IMAGENS.get(bandeira)
    if not filename:
        return None
    path = _IMAGENS_DIR / filename
    if not path.exists():
        return None
    try:
        from PIL import Image as _Img
        img = _Img.open(path).convert("RGBA")
        img.thumbnail(size, _Img.LANCZOS)
        return _ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Bandeiras customizadas (armazenadas em configuracoes como lista CSV)
# ---------------------------------------------------------------------------

_CUSTOM_KEY = "bandeiras_custom"


def listar_bandeiras_custom() -> list[str]:
    """Retorna lista de chaves de bandeiras customizadas cadastradas pelo usuário."""
    from database import obter_configuracao
    raw = obter_configuracao(_CUSTOM_KEY, "")
    return [b.strip() for b in raw.split(",") if b.strip()]


def salvar_bandeira_custom(nome: str) -> str:
    """
    Cadastra uma nova bandeira customizada.
    Retorna a chave gerada (lowercase sem espaços).
    """
    from database import salvar_configuracao
    chave = nome.strip().lower().replace(" ", "_")
    existentes = listar_bandeiras_custom()
    if chave not in existentes:
        existentes.append(chave)
        salvar_configuracao(_CUSTOM_KEY, ",".join(existentes))
    # Registra o label se ainda não existir
    if chave not in BANDEIRAS:
        BANDEIRAS.append(chave)
        BANDEIRAS_LABEL.append(nome.strip().title())
    return chave


def bandeiras_disponiveis() -> tuple[list[str], list[str]]:
    """
    Retorna (chaves, labels) de todas as bandeiras: padrão + customizadas.
    Inclui a opção especial '+ Nova bandeira...' no final.
    """
    custom = listar_bandeiras_custom()
    chaves = list(BANDEIRAS)
    labels = list(BANDEIRAS_LABEL)
    for c in custom:
        if c not in chaves:
            chaves.append(c)
            labels.append(c.replace("_", " ").title())
    chaves.append("__nova__")
    labels.append("✏  + Nova bandeira...")
    return chaves, labels


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Cartao:
    id:                int
    nome:              str
    banco:             str
    bandeira:          str
    ultimos_digitos:   str
    cor_fundo:         str
    cor_texto:         str
    limite:            float
    limite_disponivel: float
    dia_vencimento:    Optional[int]
    dia_fechamento:    Optional[int]
    ativo:             bool
    padrao:            bool
    criado_em:         str


@dataclass
class CompraCartao:
    id:                     int
    cartao_id:              int
    descricao:              str
    valor_total:            float
    valor_parcela:          float
    total_parcelas:         int
    parcelas_pagas:         int
    mes_inicio:             str
    categoria:              str
    estabelecimento:        str
    importado_visao_futura: bool
    criado_em:              str


@dataclass
class ParcelaCartao:
    id:             int
    compra_id:      int
    cartao_id:      int
    numero_parcela: int
    mes_referencia: str
    valor:          float
    status:         str
    data_pagamento: Optional[str]
    divida_id:      Optional[int]
    # joined (não persistidos)
    descricao:      str = ""
    estabelecimento: str = ""
    total_parcelas: int = 1


# ---------------------------------------------------------------------------
# CRUD — Cartões
# ---------------------------------------------------------------------------

def listar_cartoes(apenas_ativos: bool = False) -> list[Cartao]:
    sql = "SELECT * FROM cartoes"
    if apenas_ativos:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY nome"
    with conectar() as conn:
        rows = conn.execute(sql).fetchall()
    return [_row_to_cartao(r) for r in rows]


def _row_to_cartao(r) -> Cartao:
    d = dict(r)
    return Cartao(
        id=d["id"], nome=d["nome"], banco=d["banco"],
        bandeira=d["bandeira"],
        ultimos_digitos=d.get("ultimos_digitos") or "",
        cor_fundo=d.get("cor_fundo") or "#6D28D9",
        cor_texto=d.get("cor_texto") or "#FFFFFF",
        limite=d.get("limite") or 0.0,
        limite_disponivel=d.get("limite_disponivel") or 0.0,
        dia_vencimento=d.get("dia_vencimento"),
        dia_fechamento=d.get("dia_fechamento"),
        ativo=bool(d.get("ativo", 1)),
        padrao=bool(d.get("padrao", 0)),
        criado_em=d.get("criado_em") or "",
    )


def salvar_cartao(dados: dict, id: Optional[int] = None) -> int:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        if id:
            conn.execute("""
                UPDATE cartoes SET nome=?, banco=?, bandeira=?, ultimos_digitos=?,
                    cor_fundo=?, cor_texto=?, limite=?, limite_disponivel=?,
                    dia_vencimento=?, dia_fechamento=?
                WHERE id=?
            """, (
                dados["nome"], dados["banco"], dados["bandeira"],
                dados.get("ultimos_digitos", ""),
                dados.get("cor_fundo", "#6D28D9"),
                dados.get("cor_texto", "#FFFFFF"),
                dados.get("limite", 0.0),
                dados.get("limite_disponivel", dados.get("limite", 0.0)),
                dados.get("dia_vencimento"),
                dados.get("dia_fechamento"),
                id,
            ))
            return id
        else:
            cur = conn.execute("""
                INSERT INTO cartoes
                (nome, banco, bandeira, ultimos_digitos, cor_fundo, cor_texto,
                 limite, limite_disponivel, dia_vencimento, dia_fechamento, ativo, criado_em)
                VALUES (?,?,?,?,?,?,?,?,?,?,1,?)
            """, (
                dados["nome"], dados["banco"], dados["bandeira"],
                dados.get("ultimos_digitos", ""),
                dados.get("cor_fundo", "#6D28D9"),
                dados.get("cor_texto", "#FFFFFF"),
                dados.get("limite", 0.0),
                dados.get("limite", 0.0),
                dados.get("dia_vencimento"),
                dados.get("dia_fechamento"),
                agora,
            ))
            cartao_id = cur.lastrowid
            # Cria plano_conta vinculado ao cartão
            conn.execute("""
                INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)
                VALUES (?,?,?,1,0,?)
            """, (f"Cartão {dados['nome']}", "variavel", "Cartão de Crédito", agora))
            return cartao_id


def alternar_ativo_cartao(id: int, ativo: bool):
    with conectar() as conn:
        conn.execute("UPDATE cartoes SET ativo=? WHERE id=?", (int(ativo), id))


# ---------------------------------------------------------------------------
# CRUD — Compras e Parcelas
# ---------------------------------------------------------------------------

def listar_compras(cartao_id: int) -> list[CompraCartao]:
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM compras_cartao WHERE cartao_id=? ORDER BY mes_inicio DESC, id DESC",
            (cartao_id,)
        ).fetchall()
    return [_row_to_compra(r) for r in rows]


def _row_to_compra(r) -> CompraCartao:
    d = dict(r)
    return CompraCartao(
        id=d["id"], cartao_id=d["cartao_id"],
        descricao=d["descricao"], valor_total=d["valor_total"],
        valor_parcela=d["valor_parcela"], total_parcelas=d["total_parcelas"],
        parcelas_pagas=d.get("parcelas_pagas", 0),
        mes_inicio=d["mes_inicio"],
        categoria=d.get("categoria") or "",
        estabelecimento=d.get("estabelecimento") or "",
        importado_visao_futura=bool(d.get("importado_visao_futura", 0)),
        criado_em=d.get("criado_em") or "",
    )


def _ultimo_dia_mes(ano: int, mes: int) -> int:
    import calendar
    return calendar.monthrange(ano, mes)[1]


def salvar_compra_com_parcelas(dados: dict) -> dict:
    """
    Cria compra, gera todas as parcelas e lança cada uma em contas_pagar.
    Também integra com dividas e salva o último cartão usado.
    Retorna dict com info para o toast.
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = round(float(dados["valor_total"]), 2)
    n = int(dados["total_parcelas"])
    parcela_base = round(total / n, 2)
    ultima_parcela = round(total - parcela_base * (n - 1), 2)

    mes_inicio = dados["mes_inicio"]  # "YYYY-MM"
    ano_ini, mes_ini = int(mes_inicio[:4]), int(mes_inicio[5:7])
    cartao_id = dados["cartao_id"]

    # Salva último cartão usado (MELHORIA 1)
    salvar_configuracao("ultimo_cartao_id", str(cartao_id))

    with conectar() as conn:
        cartao_row = conn.execute("SELECT * FROM cartoes WHERE id=?", (cartao_id,)).fetchone()
        nome_cartao = cartao_row["nome"] if cartao_row else "Cartão"
        dia_venc = cartao_row["dia_vencimento"] if cartao_row else 10

        # Busca ou cria plano_conta para o cartão
        nome_plano = f"Cartão {nome_cartao}"
        plano_row = conn.execute(
            "SELECT id FROM plano_contas WHERE nome=?", (nome_plano,)
        ).fetchone()
        if plano_row:
            plano_id = plano_row["id"]
        else:
            cur_p = conn.execute("""
                INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)
                VALUES (?,?,?,1,0,?)
            """, (nome_plano, "variavel", "Cartão de Crédito", agora))
            plano_id = cur_p.lastrowid

        # Cria registro da compra
        cur = conn.execute("""
            INSERT INTO compras_cartao
            (cartao_id, descricao, valor_total, valor_parcela, total_parcelas,
             parcelas_pagas, mes_inicio, categoria, estabelecimento, criado_em)
            VALUES (?,?,?,?,?,0,?,?,?,?)
        """, (
            cartao_id, dados["descricao"], total, parcela_base, n,
            mes_inicio, dados.get("categoria", ""),
            dados.get("estabelecimento", ""), agora,
        ))
        compra_id = cur.lastrowid

        # Gera parcelas + lança em contas_pagar (MELHORIA 4)
        mes_fim_label = ""
        for i in range(n):
            mes_r = mes_ini + i
            ano_r = ano_ini + (mes_r - 1) // 12
            mes_r = ((mes_r - 1) % 12) + 1
            ref = f"{ano_r:04d}-{mes_r:02d}"
            valor = ultima_parcela if i == n - 1 else parcela_base

            conn.execute("""
                INSERT INTO parcelas_cartao
                (compra_id, cartao_id, numero_parcela, mes_referencia, valor, status)
                VALUES (?,?,?,?,?,'pendente')
            """, (compra_id, cartao_id, i + 1, ref, valor))

            # Lança em contas_pagar com data_vencimento correta
            dia_v = min(dia_venc or 10, _ultimo_dia_mes(ano_r, mes_r))
            data_venc_str = f"{ano_r:04d}-{mes_r:02d}-{dia_v:02d}"
            desc_cp = f"Parcela {i+1}/{n} — {dados['descricao']}"
            if dados.get("estabelecimento"):
                desc_cp = f"Parcela {i+1}/{n} — {dados['estabelecimento']}"
            conn.execute("""
                INSERT INTO contas_pagar
                (plano_conta_id, descricao, valor, data_vencimento, status, recorrente, criado_em)
                VALUES (?,?,?,?,'pendente',0,?)
            """, (plano_id, desc_cp, valor, data_venc_str, agora))

            if i == n - 1:
                from config import NOMES_MESES
                mes_fim_label = f"{NOMES_MESES[mes_r - 1][:3]}/{ano_r}"

        # Atualiza limite_disponivel
        conn.execute(
            "UPDATE cartoes SET limite_disponivel = MAX(0, limite_disponivel - ?) WHERE id=?",
            (total, cartao_id)
        )

        # Integra com dividas
        nome_divida = f"Cartão {nome_cartao}"
        divida_row = conn.execute(
            "SELECT id FROM dividas WHERE nome=? AND tipo='cartao'", (nome_divida,)
        ).fetchone()

        hoje = date.today()
        mes_atual = f"{hoje.year:04d}-{hoje.month:02d}"

        total_pendente = conn.execute("""
            SELECT COALESCE(SUM(valor), 0) FROM parcelas_cartao
            WHERE cartao_id=? AND status='pendente'
        """, (cartao_id,)).fetchone()[0]

        parcela_mes = conn.execute("""
            SELECT COALESCE(SUM(valor), 0) FROM parcelas_cartao
            WHERE cartao_id=? AND mes_referencia=? AND status='pendente'
        """, (cartao_id, mes_atual)).fetchone()[0]

        if divida_row:
            conn.execute(
                "UPDATE dividas SET saldo_atual=?, parcela_mensal=? WHERE id=?",
                (total_pendente, parcela_mes, divida_row["id"])
            )
        else:
            conn.execute("""
                INSERT INTO dividas
                (nome, tipo, saldo_atual, parcela_mensal, total_parcelas, parcelas_pagas,
                 dia_vencimento, taxa_juros, ativa, criado_em)
                VALUES (?,?,?,?,0,0,?,0,1,?)
            """, (nome_divida, "cartao", total_pendente, parcela_mes, dia_venc, agora))

    return {"compra_id": compra_id, "n": n, "mes_fim": mes_fim_label}


def listar_parcelas_mes(cartao_id: int, mes: int, ano: int) -> list[ParcelaCartao]:
    ref = f"{ano:04d}-{mes:02d}"
    with conectar() as conn:
        rows = conn.execute("""
            SELECT p.*, c.descricao as comp_desc, c.estabelecimento, c.total_parcelas
            FROM parcelas_cartao p
            JOIN compras_cartao c ON c.id = p.compra_id
            WHERE p.cartao_id=? AND p.mes_referencia=?
            ORDER BY p.id
        """, (cartao_id, ref)).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        obj = ParcelaCartao(
            id=d["id"], compra_id=d["compra_id"], cartao_id=d["cartao_id"],
            numero_parcela=d["numero_parcela"], mes_referencia=d["mes_referencia"],
            valor=d["valor"], status=d["status"],
            data_pagamento=d.get("data_pagamento"),
            divida_id=d.get("divida_id"),
        )
        obj.descricao = d.get("comp_desc") or ""
        obj.estabelecimento = d.get("estabelecimento") or ""
        obj.total_parcelas = d.get("total_parcelas") or 1
        result.append(obj)
    return result


def marcar_parcela_paga(id: int):
    """Marca uma parcela como paga. No-op se já estiver paga ou cancelada
    — evita sobrescrever data_pagamento original."""
    hoje = date.today().isoformat()
    with conectar() as conn:
        cur = conn.execute(
            "UPDATE parcelas_cartao SET status='pago', data_pagamento=?"
            " WHERE id=? AND status='pendente'",
            (hoje, id),
        )
        if cur.rowcount == 0:
            return  # já estava paga/cancelada
        row = conn.execute("SELECT cartao_id FROM parcelas_cartao WHERE id=?", (id,)).fetchone()
        if row:
            _atualizar_divida_cartao(conn, row["cartao_id"])


def marcar_todas_pagas(cartao_id: int, mes: int, ano: int):
    ref = f"{ano:04d}-{mes:02d}"
    hoje = date.today().isoformat()
    with conectar() as conn:
        conn.execute("""
            UPDATE parcelas_cartao SET status='pago', data_pagamento=?
            WHERE cartao_id=? AND mes_referencia=? AND status='pendente'
        """, (hoje, cartao_id, ref))
        _atualizar_divida_cartao(conn, cartao_id)


def _atualizar_divida_cartao(conn, cartao_id: int):
    cartao_row = conn.execute("SELECT nome FROM cartoes WHERE id=?", (cartao_id,)).fetchone()
    if not cartao_row:
        return
    nome_divida = f"Cartão {cartao_row['nome']}"
    hoje = date.today()
    mes_atual = f"{hoje.year:04d}-{hoje.month:02d}"

    total_pendente = conn.execute("""
        SELECT COALESCE(SUM(valor), 0) FROM parcelas_cartao
        WHERE cartao_id=? AND status='pendente'
    """, (cartao_id,)).fetchone()[0]

    parcela_mes = conn.execute("""
        SELECT COALESCE(SUM(valor), 0) FROM parcelas_cartao
        WHERE cartao_id=? AND mes_referencia=? AND status='pendente'
    """, (cartao_id, mes_atual)).fetchone()[0]

    result = conn.execute("""
        UPDATE dividas SET saldo_atual=?, parcela_mensal=?
        WHERE nome=? AND tipo='cartao'
    """, (total_pendente, parcela_mes, nome_divida))

    if result.rowcount == 0 and total_pendente > 0:
        # Dívida foi excluída manualmente — recria automaticamente
        from datetime import datetime as _dt
        agora = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        cartao_info = conn.execute(
            "SELECT dia_vencimento FROM cartoes WHERE id=?", (cartao_id,)
        ).fetchone()
        dia_venc = cartao_info["dia_vencimento"] if cartao_info else None
        conn.execute("""
            INSERT INTO dividas
            (nome, tipo, saldo_atual, parcela_mensal, total_parcelas,
             parcelas_pagas, dia_vencimento, taxa_juros, ativa, criado_em)
            VALUES (?,?,?,?,0,0,?,0.0,1,?)
        """, (nome_divida, "cartao", total_pendente, parcela_mes, dia_venc, agora))


def total_fatura_mes(cartao_id: int, mes: int, ano: int) -> dict:
    ref = f"{ano:04d}-{mes:02d}"
    with conectar() as conn:
        rows = conn.execute("""
            SELECT status, SUM(valor) as total FROM parcelas_cartao
            WHERE cartao_id=? AND mes_referencia=?
            GROUP BY status
        """, (cartao_id, ref)).fetchall()

    totais = {"pendente": 0.0, "pago": 0.0, "total": 0.0}
    for r in rows:
        totais[r["status"]] = r["total"] or 0.0
        totais["total"] += r["total"] or 0.0
    return totais


def registrar_compra_parcelas(dados: dict) -> int:
    """
    Cria compras_cartao + parcelas_cartao a partir de uma despesa já lançada
    em contas_pagar. Não toca em contas_pagar.
    Chaves obrigatórias em dados: cartao_id, descricao, valor_total,
    total_parcelas, mes_inicio ("YYYY-MM").
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = round(float(dados["valor_total"]), 2)
    n = int(dados["total_parcelas"])
    parcela_base = round(total / n, 2)
    ultima_parcela = round(total - parcela_base * (n - 1), 2)
    cartao_id = dados["cartao_id"]

    mes_inicio = dados["mes_inicio"]
    ano_ini, mes_ini = int(mes_inicio[:4]), int(mes_inicio[5:7])

    with conectar() as conn:
        cur = conn.execute("""
            INSERT INTO compras_cartao
            (cartao_id, descricao, valor_total, valor_parcela, total_parcelas,
             parcelas_pagas, mes_inicio, categoria, estabelecimento, criado_em)
            VALUES (?,?,?,?,?,0,?,?,?,?)
        """, (
            cartao_id, dados["descricao"], total, parcela_base, n,
            mes_inicio, dados.get("categoria", ""),
            dados.get("estabelecimento", ""), agora,
        ))
        compra_id = cur.lastrowid

        for i in range(n):
            mes_r = mes_ini + i
            ano_r = ano_ini + (mes_r - 1) // 12
            mes_r = ((mes_r - 1) % 12) + 1
            ref = f"{ano_r:04d}-{mes_r:02d}"
            valor = ultima_parcela if i == n - 1 else parcela_base
            conn.execute("""
                INSERT INTO parcelas_cartao
                (compra_id, cartao_id, numero_parcela, mes_referencia, valor, status)
                VALUES (?,?,?,?,?,'pendente')
            """, (compra_id, cartao_id, i + 1, ref, valor))

        conn.execute(
            "UPDATE cartoes SET limite_disponivel = MAX(0, limite_disponivel - ?) WHERE id=?",
            (total, cartao_id)
        )
        _atualizar_divida_cartao(conn, cartao_id)

    return compra_id


def lancar_fatura_contas_pagar(cartao_id: int, mes: int, ano: int):
    """Cria lançamento em contas_pagar para a fatura do mês."""
    ref = f"{ano:04d}-{mes:02d}"
    with conectar() as conn:
        cartao = conn.execute("SELECT * FROM cartoes WHERE id=?", (cartao_id,)).fetchone()
        if not cartao:
            return

        total = conn.execute("""
            SELECT COALESCE(SUM(valor), 0) FROM parcelas_cartao
            WHERE cartao_id=? AND mes_referencia=? AND status='pendente'
        """, (cartao_id, ref)).fetchone()[0]

        if total <= 0:
            return

        # Busca ou cria plano_conta para o cartão
        nome_plano = f"Cartão {cartao['nome']}"
        plano = conn.execute(
            "SELECT id FROM plano_contas WHERE nome=?", (nome_plano,)
        ).fetchone()
        if not plano:
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.execute("""
                INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)
                VALUES (?,?,?,1,0,?)
            """, (nome_plano, "variavel", "Cartão de Crédito", agora))
            plano_id = cur.lastrowid
        else:
            plano_id = plano["id"]

        # Data de vencimento da fatura — capa o dia ao último dia do mês
        # pra evitar gravar datas inválidas como '2026-02-31'.
        from calendar import monthrange
        dia_venc = cartao["dia_vencimento"] or 10
        ultimo_dia = monthrange(ano, mes)[1]
        dia_seguro = min(int(dia_venc), ultimo_dia)
        venc = f"{ano:04d}-{mes:02d}-{dia_seguro:02d}"

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO contas_pagar
            (plano_conta_id, descricao, valor, data_vencimento, status, recorrente, criado_em)
            VALUES (?,?,?,?,'pendente',0,?)
        """, (plano_id, f"Fatura {cartao['nome']} — {mes:02d}/{ano}", total, venc, agora))


def prever_efeito_importacao(linhas: list[dict],
                              criar_historico: bool = True) -> dict:
    """Calcula um resumo do que SERIA criado no banco se as linhas fossem
    importadas, sem tocar em nada. Usado pelo modal para mostrar o impacto
    ao usuário antes de confirmar.

    Para cada linha:
      - 1 parcela atual (do mes_referencia)
      - (numero - 1) parcelas históricas (se criar_historico=True)
      - (total - numero) parcelas futuras

    NÃO detecta duplicatas (exigiria query no banco). Linhas com parcela
    no formato inválido entram em n_compras mas não somam parcelas.

    Retorna dict com:
      n_compras, n_parcelas_total, n_parcelas_historicas,
      n_parcelas_atuais, n_parcelas_futuras, soma_atual, soma_futura
    """
    from views.cartoes.importar_fatura_model import parsear_parcela

    n_compras = len(linhas)
    n_hist = n_atu = n_fut = 0
    soma_atu = soma_fut = 0.0

    for linha in linhas:
        try:
            num, total = parsear_parcela(linha.get("parcela", "") or "1/1")
        except ValueError:
            continue  # linha sem parcela válida não soma

        try:
            valor = float(linha.get("valor", 0) or 0)
        except (TypeError, ValueError):
            valor = 0.0

        n_atu += 1
        soma_atu += valor

        if criar_historico:
            n_hist += max(0, num - 1)

        futuras = max(0, total - num)
        n_fut += futuras
        soma_fut += valor * futuras

    return {
        "n_compras":             n_compras,
        "n_parcelas_total":      n_hist + n_atu + n_fut,
        "n_parcelas_historicas": n_hist,
        "n_parcelas_atuais":     n_atu,
        "n_parcelas_futuras":    n_fut,
        "soma_atual":            round(soma_atu, 2),
        "soma_futura":           round(soma_fut, 2),
    }


def importar_compra_fatura(dados: dict) -> int | None:
    """
    Importa uma compra a partir de uma linha de fatura de cartão.

    Chaves obrigatórias em dados:
        cartao_id, descricao, numero_parcela, total_parcelas,
        valor_parcela, mes_referencia ("YYYY-MM")
    Opcionais:
        estabelecimento, categoria, criar_historico (bool, default True),
        data_vencimento ("YYYY-MM-DD") — sobrescreve o cálculo automático
            APENAS para a parcela do mes_referencia. Parcelas futuras
            seguem o dia_vencimento do cartão.

    Retorna compra_id (int > 0) ou None se duplicata exata.
    Se total_parcelas mudou (delta), adiciona parcelas faltantes e retorna 0.
    """
    agora      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cartao_id  = int(dados["cartao_id"])
    descricao  = str(dados["descricao"]).strip()
    numero     = int(dados["numero_parcela"])
    total      = int(dados["total_parcelas"])
    # valor_parcela pode ser pytest.approx em testes — extrai float real
    vp_raw = dados["valor_parcela"]
    try:
        valor_parc = round(float(vp_raw), 2)
    except (TypeError, ValueError):
        valor_parc = round(float(getattr(vp_raw, "expected", 0.0)), 2)
    mes_ref    = str(dados["mes_referencia"])  # "YYYY-MM" — mês da parcela atual
    criar_hist = bool(dados.get("criar_historico", True))
    # Vencimento explícito do cabeçalho da fatura (sobrescreve dia_vencimento
    # do cartão apenas para a parcela do mes_referencia). Formato ISO.
    venc_explicito = dados.get("data_vencimento") or None

    # mes_ref é o mês da parcela `numero`. Recalcula o mes_inicio (parcela 1).
    ano_ref  = int(mes_ref[:4])
    mes_num  = int(mes_ref[5:7])
    # Retrocede (numero - 1) meses para chegar ao mês da parcela 1
    mes_abs  = (ano_ref * 12 + mes_num - 1) - (numero - 1)
    ano_ini  = mes_abs // 12
    mes_ini  = mes_abs % 12 + 1
    mes_inicio = f"{ano_ini:04d}-{mes_ini:02d}"

    with conectar() as conn:
        cartao_row = conn.execute("SELECT * FROM cartoes WHERE id=?", (cartao_id,)).fetchone()
        nome_cartao = cartao_row["nome"] if cartao_row else "Cartão"
        dia_venc    = cartao_row["dia_vencimento"] if cartao_row else 10

        # ── Busca ou cria plano_conta ──────────────────────────────────────
        nome_plano = f"Cartão {nome_cartao}"
        plano_row  = conn.execute(
            "SELECT id FROM plano_contas WHERE nome=?", (nome_plano,)
        ).fetchone()
        if plano_row:
            plano_id = plano_row["id"]
        else:
            cur_p = conn.execute("""
                INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)
                VALUES (?,?,?,1,0,?)
            """, (nome_plano, "variavel", "Cartão de Crédito", agora))
            plano_id = cur_p.lastrowid

        # ── Deduplicação: chave (cartao_id, descricao, mes_ref_import, numero_parcela_import) ──
        # Usa colunas rastreadas no momento do import para evitar falsos positivos
        # com parcelas derivadas de outras compras com a mesma descrição.
        existente = conn.execute("""
            SELECT id, total_parcelas
            FROM compras_cartao
            WHERE cartao_id = ? AND descricao = ?
              AND importado_mes_ref = ? AND importado_numero_parcela = ?
        """, (cartao_id, descricao, mes_ref, numero)).fetchone()

        if existente:
            compra_id_ex  = existente["id"]
            total_ex      = existente["total_parcelas"]

            if total_ex == total:
                # Duplicata exata — ignora
                return None

            # Delta: total_parcelas aumentou — adiciona apenas parcelas faltantes
            # Descobre a última parcela já registrada
            ultima_ex = conn.execute(
                "SELECT MAX(numero_parcela) FROM parcelas_cartao WHERE compra_id=?",
                (compra_id_ex,)
            ).fetchone()[0] or 0

            # Atualiza total_parcelas na compra
            conn.execute(
                "UPDATE compras_cartao SET total_parcelas=? WHERE id=?",
                (total, compra_id_ex)
            )

            debito_extra = 0.0
            for i in range(ultima_ex, total):
                mes_r = mes_ini + i
                ano_r = ano_ini + (mes_r - 1) // 12
                mes_r = ((mes_r - 1) % 12) + 1
                ref   = f"{ano_r:04d}-{mes_r:02d}"
                # Última parcela absorve resíduo
                v = round(valor_parc * total - valor_parc * (total - 1), 2) if i == total - 1 else valor_parc

                conn.execute("""
                    INSERT INTO parcelas_cartao
                    (compra_id, cartao_id, numero_parcela, mes_referencia, valor, status)
                    VALUES (?,?,?,?,?,'pendente')
                """, (compra_id_ex, cartao_id, i + 1, ref, v))

                dia_v        = min(dia_venc or 10, _ultimo_dia_mes(ano_r, mes_r))
                data_venc_str = f"{ano_r:04d}-{mes_r:02d}-{dia_v:02d}"
                # Vencimento explícito sobrescreve apenas a parcela do mes_referencia
                if venc_explicito and ref == mes_ref:
                    data_venc_str = venc_explicito
                desc_cp      = f"Parcela {i+1}/{total} — {descricao}"
                if dados.get("estabelecimento"):
                    desc_cp = f"Parcela {i+1}/{total} — {dados['estabelecimento']}"
                conn.execute("""
                    INSERT INTO contas_pagar
                    (plano_conta_id, descricao, valor, data_vencimento, status, recorrente, criado_em)
                    VALUES (?,?,?,?,'pendente',0,?)
                """, (plano_id, desc_cp, v, data_venc_str, agora))
                debito_extra += v

            conn.execute(
                "UPDATE cartoes SET limite_disponivel = MAX(0, limite_disponivel - ?) WHERE id=?",
                (debito_extra, cartao_id)
            )
            _atualizar_divida_cartao(conn, cartao_id)
            return 0  # sinal de delta aplicado

        # ── Nova compra ────────────────────────────────────────────────────
        parcelas_pagas = numero - 1
        cur = conn.execute("""
            INSERT INTO compras_cartao
            (cartao_id, descricao, valor_total, valor_parcela, total_parcelas,
             parcelas_pagas, mes_inicio, categoria, estabelecimento,
             importado_numero_parcela, importado_mes_ref, criado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            cartao_id, descricao,
            round(valor_parc * total, 2), valor_parc, total,
            parcelas_pagas, mes_inicio,
            dados.get("categoria", ""), dados.get("estabelecimento", ""),
            numero, mes_ref, agora,
        ))
        compra_id = cur.lastrowid

        # ── Parcelas históricas (passadas) ─────────────────────────────────
        if criar_hist and numero > 1:
            for i in range(numero - 1):  # parcelas 1 … numero-1
                mes_r = mes_ini + i
                ano_r = ano_ini + (mes_r - 1) // 12
                mes_r = ((mes_r - 1) % 12) + 1
                ref   = f"{ano_r:04d}-{mes_r:02d}"
                conn.execute("""
                    INSERT INTO parcelas_cartao
                    (compra_id, cartao_id, numero_parcela, mes_referencia, valor, status)
                    VALUES (?,?,?,?,?,'pago')
                """, (compra_id, cartao_id, i + 1, ref, valor_parc))

        # ── Parcelas pendentes (numero … total) ────────────────────────────
        restantes = total - numero + 1
        debito    = 0.0
        for j in range(restantes):
            i   = numero - 1 + j  # índice absoluto 0-based
            mes_r = mes_ini + i
            ano_r = ano_ini + (mes_r - 1) // 12
            mes_r = ((mes_r - 1) % 12) + 1
            ref   = f"{ano_r:04d}-{mes_r:02d}"
            # Última parcela (do total) absorve resíduo do arredondamento
            v = round(valor_parc * total - valor_parc * (total - 1), 2) if i == total - 1 else valor_parc

            conn.execute("""
                INSERT INTO parcelas_cartao
                (compra_id, cartao_id, numero_parcela, mes_referencia, valor, status)
                VALUES (?,?,?,?,?,'pendente')
            """, (compra_id, cartao_id, i + 1, ref, v))

            dia_v         = min(dia_venc or 10, _ultimo_dia_mes(ano_r, mes_r))
            data_venc_str = f"{ano_r:04d}-{mes_r:02d}-{dia_v:02d}"
            # Vencimento explícito sobrescreve apenas a parcela do mes_referencia
            if venc_explicito and ref == mes_ref:
                data_venc_str = venc_explicito
            desc_cp       = f"Parcela {i+1}/{total} — {descricao}"
            if dados.get("estabelecimento"):
                desc_cp = f"Parcela {i+1}/{total} — {dados['estabelecimento']}"
            conn.execute("""
                INSERT INTO contas_pagar
                (plano_conta_id, descricao, valor, data_vencimento, status, recorrente, criado_em)
                VALUES (?,?,?,?,'pendente',0,?)
            """, (plano_id, desc_cp, v, data_venc_str, agora))
            debito += v

        # ── Atualiza limite ────────────────────────────────────────────────
        conn.execute(
            "UPDATE cartoes SET limite_disponivel = MAX(0, limite_disponivel - ?) WHERE id=?",
            (debito, cartao_id)
        )
        _atualizar_divida_cartao(conn, cartao_id)

    return compra_id
