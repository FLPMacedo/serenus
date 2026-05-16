"""
database.py — Serenus
Centraliza criação, migração e acesso ao banco de dados SQLite.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

# Banco sempre ao lado do arquivo principal do app
DIRETORIO_BASE = Path(__file__).parent
CAMINHO_BANCO = DIRETORIO_BASE / "serenus.db"


def conectar() -> sqlite3.Connection:
    """Retorna uma conexão com o banco, com suporte a chaves estrangeiras."""
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_banco():
    """Cria todas as tabelas se ainda não existirem e popula dados de exemplo."""
    conn = conectar()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            chave TEXT UNIQUE NOT NULL,
            valor TEXT
        );

        CREATE TABLE IF NOT EXISTS plano_contas (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       TEXT NOT NULL,
            tipo_custo TEXT CHECK(tipo_custo IN ('fixo', 'variavel')),
            categoria  TEXT,
            ativa      INTEGER DEFAULT 1,
            criado_em  TEXT
        );

        CREATE TABLE IF NOT EXISTS contas_pagar (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            plano_conta_id  INTEGER REFERENCES plano_contas(id),
            descricao       TEXT,
            valor           REAL NOT NULL,
            data_vencimento TEXT NOT NULL,
            data_pagamento  TEXT,
            status          TEXT CHECK(status IN ('pendente', 'pago', 'cancelado')) DEFAULT 'pendente',
            recorrente      INTEGER DEFAULT 0,
            observacao      TEXT,
            criado_em       TEXT
        );

        CREATE TABLE IF NOT EXISTS fontes_receita (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL,
            tipo          TEXT CHECK(tipo IN ('clt', 'freela', 'aluguel', 'dividendos', 'outro')),
            valor_mensal  REAL NOT NULL,
            ativa         INTEGER DEFAULT 1,
            observacao    TEXT,
            criado_em     TEXT
        );

        CREATE TABLE IF NOT EXISTS receitas_especiais (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nome              TEXT NOT NULL,
            mes               INTEGER NOT NULL,
            valor             REAL NOT NULL,
            tipo              TEXT DEFAULT 'clt',
            recorrente_anual  INTEGER DEFAULT 1,
            observacao        TEXT
        );

        CREATE TABLE IF NOT EXISTS dividas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT NOT NULL,
            tipo            TEXT CHECK(tipo IN ('cartao', 'emprestimo', 'financiamento', 'outro')),
            saldo_atual     REAL NOT NULL,
            parcela_mensal  REAL NOT NULL,
            total_parcelas  INTEGER NOT NULL,
            parcelas_pagas  INTEGER DEFAULT 0,
            dia_vencimento  INTEGER,
            taxa_juros      REAL DEFAULT 0,
            observacao      TEXT,
            ativa           INTEGER DEFAULT 1,
            criado_em       TEXT
        );

        CREATE TABLE IF NOT EXISTS backups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora   TEXT NOT NULL,
            arquivo     TEXT NOT NULL,
            tamanho_kb  REAL,
            destino     TEXT CHECK(destino IN ('local', 'google_drive')),
            status      TEXT CHECK(status IN ('ok', 'erro')),
            observacao  TEXT
        );

        CREATE TABLE IF NOT EXISTS cartoes (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nome              TEXT NOT NULL,
            banco             TEXT NOT NULL,
            bandeira          TEXT NOT NULL,
            ultimos_digitos   TEXT,
            cor_fundo         TEXT DEFAULT '#6D28D9',
            cor_texto         TEXT DEFAULT '#FFFFFF',
            limite            REAL DEFAULT 0,
            limite_disponivel REAL DEFAULT 0,
            dia_vencimento    INTEGER,
            dia_fechamento    INTEGER,
            ativo             INTEGER DEFAULT 1,
            padrao            INTEGER DEFAULT 0,
            criado_em         TEXT
        );

        CREATE TABLE IF NOT EXISTS compras_cartao (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            cartao_id              INTEGER REFERENCES cartoes(id),
            descricao              TEXT NOT NULL,
            valor_total            REAL NOT NULL,
            valor_parcela          REAL NOT NULL,
            total_parcelas         INTEGER NOT NULL,
            parcelas_pagas         INTEGER DEFAULT 0,
            mes_inicio             TEXT NOT NULL,
            categoria              TEXT,
            estabelecimento        TEXT,
            importado_visao_futura INTEGER DEFAULT 0,
            criado_em              TEXT
        );

        CREATE TABLE IF NOT EXISTS parcelas_cartao (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            compra_id       INTEGER REFERENCES compras_cartao(id),
            cartao_id       INTEGER REFERENCES cartoes(id),
            numero_parcela  INTEGER NOT NULL,
            mes_referencia  TEXT NOT NULL,
            valor           REAL NOT NULL,
            status          TEXT CHECK(status IN ('pendente','pago','cancelado')) DEFAULT 'pendente',
            data_pagamento  TEXT,
            divida_id       INTEGER REFERENCES dividas(id)
        );
    """)

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS contas_investimento (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            instituicao TEXT NOT NULL,
            tipo        TEXT NOT NULL
                        CHECK(tipo IN ('corretora','banco','tesouro','outro')),
            observacao  TEXT,
            ativa       INTEGER DEFAULT 1,
            criado_em   TEXT
        );

        CREATE TABLE IF NOT EXISTS ativos (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo                TEXT NOT NULL,
            nome                  TEXT NOT NULL,
            tipo                  TEXT NOT NULL
                                  CHECK(tipo IN ('acao','etf','fii','cdb','tesouro','fundo','cripto','outro')),
            conta_investimento_id INTEGER REFERENCES contas_investimento(id),
            indexador             TEXT,
            taxa_contratada       REAL,
            vencimento            TEXT,
            observacao            TEXT,
            ativo                 INTEGER DEFAULT 1,
            criado_em             TEXT
        );

        CREATE TABLE IF NOT EXISTS movimentacoes_investimento (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo_id                INTEGER NOT NULL REFERENCES ativos(id),
            conta_investimento_id   INTEGER NOT NULL REFERENCES contas_investimento(id),
            tipo                    TEXT NOT NULL
                                    CHECK(tipo IN ('compra','venda','aplicacao','resgate',
                                                   'dividendo','jcp','juros','amortizacao',
                                                   'taxa','imposto')),
            data                    TEXT NOT NULL,
            quantidade              REAL DEFAULT 0,
            preco_unitario          REAL DEFAULT 0,
            valor_bruto             REAL NOT NULL,
            taxas                   REAL DEFAULT 0,
            valor_liquido           REAL NOT NULL,
            observacao              TEXT,
            registrar_no_financeiro INTEGER DEFAULT 0,
            contas_pagar_id         INTEGER REFERENCES contas_pagar(id),
            criado_em               TEXT
        );

        CREATE TABLE IF NOT EXISTS posicao_cache (
            ativo_id         INTEGER PRIMARY KEY REFERENCES ativos(id),
            quantidade_atual REAL DEFAULT 0,
            custo_medio      REAL DEFAULT 0,
            valor_investido  REAL DEFAULT 0,
            valor_atual      REAL DEFAULT 0,
            lucro_realizado  REAL DEFAULT 0,
            atualizado_em    TEXT
        );

        CREATE TABLE IF NOT EXISTS metas_financeiras (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT    NOT NULL,
            valor_alvo  REAL    NOT NULL DEFAULT 0,
            valor_atual REAL    NOT NULL DEFAULT 0,
            prazo       TEXT,
            descricao   TEXT    DEFAULT '',
            criado_em   TEXT    NOT NULL
        );
    """)

    conn.commit()
    _migrar_plano_contas(conn)
    _migrar_fontes_receita(conn)
    _popular_contas_padrao(conn)
    _popular_fontes_padrao(conn)
    popular_dados_exemplo(conn)
    conn.close()


def _migrar_plano_contas(conn: sqlite3.Connection):
    """Adiciona coluna padrao a plano_contas caso não exista."""
    colunas = {row[1] for row in conn.execute("PRAGMA table_info(plano_contas)")}
    if "padrao" not in colunas:
        conn.execute("ALTER TABLE plano_contas ADD COLUMN padrao INTEGER DEFAULT 0")
    conn.commit()


def _migrar_fontes_receita(conn: sqlite3.Connection):
    """Adiciona colunas extras a fontes_receita caso não existam (migração incremental)."""
    colunas_existentes = {
        row[1] for row in conn.execute("PRAGMA table_info(fontes_receita)")
    }
    extras = [
        ("dia_pagamento",     "INTEGER"),
        ("fgts_aniversario",  "INTEGER DEFAULT 0"),
        ("fgts_mes",          "INTEGER"),
        ("fgts_valor",        "REAL"),
        ("periodicidade",     "TEXT DEFAULT 'mensal'"),
        ("origem",            "TEXT"),
    ]
    extras.append(("padrao", "INTEGER DEFAULT 0"))
    for coluna, tipo in extras:
        if coluna not in colunas_existentes:
            conn.execute(f"ALTER TABLE fontes_receita ADD COLUMN {coluna} {tipo}")
    conn.commit()


_CONTAS_PADRAO = [
    # (nome, tipo_custo, categoria)
    ("Aluguel / Financiamento imóvel", "fixo",    "Moradia"),
    ("Condomínio",                     "fixo",    "Moradia"),
    ("Água",                           "variavel","Moradia"),
    ("Luz / Energia elétrica",         "variavel","Moradia"),
    ("Gás",                            "variavel","Moradia"),
    ("Internet",                       "fixo",    "Moradia"),
    ("TV por assinatura",              "fixo",    "Moradia"),
    ("Combustível",                    "variavel","Transporte"),
    ("Estacionamento",                 "variavel","Transporte"),
    ("Transporte público",             "variavel","Transporte"),
    ("Seguro veículo",                 "fixo",    "Transporte"),
    ("IPVA",                           "fixo",    "Transporte"),
    ("Manutenção veículo",             "variavel","Transporte"),
    ("Supermercado",                   "variavel","Alimentação"),
    ("Restaurantes / Delivery",        "variavel","Alimentação"),
    ("Plano de saúde",                 "fixo",    "Saúde"),
    ("Farmácia",                       "variavel","Saúde"),
    ("Consultas / Exames",             "variavel","Saúde"),
    ("Academia",                       "fixo",    "Saúde"),
    ("Mensalidade escola/faculdade",   "fixo",    "Educação"),
    ("Cursos online",                  "variavel","Educação"),
    ("Material escolar",               "variavel","Educação"),
    ("Streaming (Netflix, Spotify…)",  "fixo",    "Serviços"),
    ("Telefone / Celular",             "fixo",    "Serviços"),
    ("Serviços digitais",              "variavel","Serviços"),
    ("Entretenimento",                 "variavel","Lazer"),
    ("Viagens",                        "variavel","Lazer"),
    ("IPTU",                           "fixo",    "Impostos"),
    ("Imposto de renda",               "fixo",    "Impostos"),
    ("Outras taxas",                   "variavel","Impostos"),
    ("Vestuário",                      "variavel","Pessoal"),
    ("Cuidados pessoais",              "variavel","Pessoal"),
    ("Presentes",                      "variavel","Pessoal"),
    ("Outros",                         "variavel","Outros"),
]


def restaurar_plano_contas_padrao() -> int:
    """
    Re-insere qualquer conta padrão que tenha sido excluída.
    Retorna o número de contas restauradas.
    """
    from datetime import datetime
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        existentes = {r[0] for r in conn.execute("SELECT nome FROM plano_contas").fetchall()}
        restauradas = 0
        for nome, tipo, cat in _CONTAS_PADRAO:
            if nome not in existentes:
                conn.execute(
                    "INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)"
                    " VALUES (?,?,?,1,1,?)",
                    (nome, tipo, cat, agora),
                )
                restauradas += 1
    return restauradas


def _popular_contas_padrao(conn: sqlite3.Connection):
    """Insere as contas padrão do sistema na primeira execução."""
    cur = conn.cursor()
    cur.execute("SELECT valor FROM configuracoes WHERE chave = 'contas_padrao_inseridas'")
    if cur.fetchone():
        return

    existentes = {r[0] for r in conn.execute("SELECT nome FROM plano_contas").fetchall()}
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for nome, tipo, cat in _CONTAS_PADRAO:
        if nome not in existentes:
            conn.execute(
                "INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, padrao, criado_em)"
                " VALUES (?,?,?,1,1,?)",
                (nome, tipo, cat, agora),
            )

    conn.execute(
        "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('contas_padrao_inseridas','true')"
    )
    conn.commit()


def _popular_fontes_padrao(conn: sqlite3.Connection):
    """Insere as fontes de receita padrão desativadas na primeira execução."""
    cur = conn.cursor()
    cur.execute("SELECT valor FROM configuracoes WHERE chave = 'fontes_padrao_inseridas'")
    if cur.fetchone():
        return

    existentes = {r[0] for r in conn.execute("SELECT nome FROM fontes_receita").fetchall()}
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    fontes = [
        ("Salário CLT",           "clt",        0.0),
        ("Freela / Serviço avulso","freela",     0.0),
        ("Aluguel recebido",       "aluguel",    0.0),
        ("Dividendos / FIIs",      "dividendos", 0.0),
        ("Pensão / Benefício",     "outro",      0.0),
    ]

    for nome, tipo, valor in fontes:
        if nome not in existentes:
            conn.execute(
                "INSERT INTO fontes_receita (nome, tipo, valor_mensal, ativa, padrao, criado_em)"
                " VALUES (?,?,?,0,1,?)",
                (nome, tipo, valor, agora),
            )

    conn.execute(
        "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('fontes_padrao_inseridas','true')"
    )
    conn.commit()


def popular_dados_exemplo(conn: sqlite3.Connection):
    """Insere dados de exemplo na primeira execução."""
    cursor = conn.cursor()

    # Verifica se já foi populado
    cursor.execute(
        "SELECT valor FROM configuracoes WHERE chave = 'dados_exemplo_inseridos'"
    )
    row = cursor.fetchone()
    if row and row["valor"] == "true":
        return

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 5 registros de plano_contas
    planos = [
        ("Aluguel",        "fixo",     "Moradia"),
        ("Conta de luz",   "variavel", "Moradia"),
        ("Internet",       "fixo",     "Serviços"),
        ("Combustível",    "variavel", "Transporte"),
        ("Plano de saúde", "fixo",     "Saúde"),
    ]
    cursor.executemany(
        "INSERT INTO plano_contas (nome, tipo_custo, categoria, ativa, criado_em) VALUES (?,?,?,1,?)",
        [(n, t, c, agora) for n, t, c in planos],
    )

    # 3 fontes de receita
    fontes = [
        ("Salário CLT",      "clt",     6800.0),
        ("Freela design",    "freela",  1200.0),
        ("Aluguel recebido", "aluguel", 1500.0),
    ]
    cursor.executemany(
        "INSERT INTO fontes_receita (nome, tipo, valor_mensal, ativa, criado_em) VALUES (?,?,?,1,?)",
        [(n, t, v, agora) for n, t, v in fontes],
    )

    # Receitas especiais padrão (13º e férias)
    cursor.executemany(
        "INSERT INTO receitas_especiais (nome, mes, valor, tipo, recorrente_anual) VALUES (?,?,?,?,1)",
        [
            ("13º Salário",     11, 6800.0, "clt"),
            ("Férias + 1/3",     6, 9066.67, "clt"),
        ],
    )

    # 4 dívidas de exemplo
    dividas = [
        ("Nubank",                  "cartao",       3200.0,  320.0, 10, 0),
        ("Itaú Visa",               "cartao",       5800.0,  450.0, 13, 0),
        ("Empréstimo Banco do Brasil", "emprestimo", 18000.0, 820.0, 22, 0),
        ("Financiamento pessoal CEF",  "financiamento", 12000.0, 580.0, 21, 0),
    ]
    cursor.executemany(
        """INSERT INTO dividas
           (nome, tipo, saldo_atual, parcela_mensal, total_parcelas, parcelas_pagas, ativa, criado_em)
           VALUES (?,?,?,?,?,?,1,?)""",
        [(n, t, s, p, tot, pg, agora) for n, t, s, p, tot, pg in dividas],
    )

    # Marca como populado
    cursor.execute(
        "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('dados_exemplo_inseridos', 'true')"
    )

    conn.commit()


# --- Helpers genéricos ---

def obter_configuracao(chave: str, padrao: str = "") -> str:
    """Retorna o valor de uma configuração pelo nome da chave."""
    with conectar() as conn:
        row = conn.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?", (chave,)
        ).fetchone()
    return row["valor"] if row else padrao


def salvar_configuracao(chave: str, valor: str):
    """Salva ou atualiza uma configuração."""
    with conectar() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
            (chave, valor),
        )


def setup_completo() -> bool:
    """Retorna True se o wizard de configuração inicial já foi concluído."""
    return obter_configuracao("setup_concluido") == "true"


# ---------------------------------------------------------------------------
# Senha de acesso
# ---------------------------------------------------------------------------

def _hash_senha(senha: str) -> str:
    import hashlib
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def tem_senha() -> bool:
    return bool(obter_configuracao("senha_hash"))


def verificar_senha(senha: str) -> bool:
    salvo = obter_configuracao("senha_hash")
    return bool(salvo) and salvo == _hash_senha(senha)


def salvar_senha(senha: str):
    salvar_configuracao("senha_hash", _hash_senha(senha))


def remover_senha():
    with conectar() as conn:
        conn.execute("DELETE FROM configuracoes WHERE chave = 'senha_hash'")


# ---------------------------------------------------------------------------
# Zerar dados do usuário (mantém configurações: tema, nome, senha)
# ---------------------------------------------------------------------------

def zerar_dados():
    """
    Apaga todos os dados financeiros do usuário.
    Mantém configurações pessoais (tema, nome, senha).
    Após zerar, re-popula apenas os padrões estruturais (plano_contas, fontes templates).
    Dados de exemplo NÃO são re-inseridos.
    """
    with conectar() as conn:
        conn.executescript("""
            DELETE FROM posicao_cache;
            DELETE FROM movimentacoes_investimento;
            DELETE FROM ativos;
            DELETE FROM contas_investimento;
            DELETE FROM parcelas_cartao;
            DELETE FROM compras_cartao;
            DELETE FROM cartoes;
            DELETE FROM contas_pagar;
            DELETE FROM plano_contas;
            DELETE FROM fontes_receita;
            DELETE FROM receitas_especiais;
            DELETE FROM dividas;
            DELETE FROM backups;
        """)
        conn.execute("""
            DELETE FROM configuracoes
            WHERE chave IN (
                'contas_padrao_inseridas',
                'fontes_padrao_inseridas',
                'bandeiras_custom'
            )
        """)
    inicializar_banco()
    # Garante que dados de exemplo não sejam re-inseridos após o reset
    salvar_configuracao("dados_exemplo_inseridos", "true")


if __name__ == "__main__":
    inicializar_banco()
    print(f"Banco inicializado em: {CAMINHO_BANCO}")

    with conectar() as conn:
        tabelas = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print("Tabelas criadas:")
        for t in tabelas:
            print(f"  - {t['name']}")

        planos = conn.execute("SELECT nome, tipo_custo, categoria FROM plano_contas").fetchall()
        print("\nPlano de contas (exemplo):")
        for p in planos:
            print(f"  {p['nome']} | {p['tipo_custo']} | {p['categoria']}")
