"""
database.py — Serenus
Centraliza criação, migração e acesso ao banco de dados SQLite.
"""

import sqlite3
from datetime import datetime

from _paths import DATABASE_PATH, DADOS

# Compatível com execução normal e bundle PyInstaller
CAMINHO_BANCO = DATABASE_PATH
DADOS.mkdir(parents=True, exist_ok=True)


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
            tipo            TEXT CHECK(tipo IN ('cartao', 'emprestimo', 'financiamento',
                                                'cheque_especial', 'outro')),
            saldo_atual     REAL NOT NULL,
            parcela_mensal  REAL NOT NULL,
            total_parcelas  INTEGER NOT NULL,
            parcelas_pagas  INTEGER DEFAULT 0,
            dia_vencimento  INTEGER,
            taxa_juros      REAL DEFAULT 0,
            -- Limite de crédito disponível (usado em tipo='cheque_especial';
            -- nos outros tipos fica zerado). O saldo_atual representa o
            -- saldo utilizado/devedor; (limite_total - saldo_atual) = saldo
            -- ainda disponível pra usar do cheque especial.
            limite_total    REAL DEFAULT 0,
            observacao      TEXT,
            ativa           INTEGER DEFAULT 1,
            criado_em       TEXT
        );

        -- Eventos de juros descontados pelo banco em cheque especial.
        -- Cada lançamento gera 1 entrada aqui (histórico) e, opcionalmente,
        -- uma conta_pagar com status='pago' (referenciada por conta_pagar_id)
        -- para que o juros pago apareça no fluxo de caixa do mês.
        CREATE TABLE IF NOT EXISTS juros_cheque_especial (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            divida_id       INTEGER NOT NULL REFERENCES dividas(id),
            data            TEXT    NOT NULL,
            valor           REAL    NOT NULL,
            observacao      TEXT    DEFAULT '',
            conta_pagar_id  INTEGER REFERENCES contas_pagar(id),
            criado_em       TEXT    NOT NULL
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

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS produtos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL,
            tipo      TEXT    CHECK(tipo IN ('produto', 'servico')) DEFAULT 'produto',
            preco     REAL    NOT NULL DEFAULT 0.0,
            descricao TEXT    DEFAULT '',
            ativo     INTEGER DEFAULT 1,
            criado_em TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vendas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao      TEXT    DEFAULT '',
            data_venda     TEXT    NOT NULL,
            valor_total    REAL    NOT NULL DEFAULT 0.0,
            desconto       REAL    NOT NULL DEFAULT 0.0,
            valor_liquido  REAL    NOT NULL DEFAULT 0.0,
            tipo_pagamento TEXT    CHECK(tipo_pagamento IN ('avista', 'aprazo')) DEFAULT 'avista',
            status         TEXT    CHECK(status IN ('pendente', 'paga', 'parcial', 'cancelada')) DEFAULT 'pendente',
            observacao     TEXT    DEFAULT '',
            criado_em      TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS itens_venda (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id   INTEGER NOT NULL REFERENCES vendas(id),
            produto_id INTEGER REFERENCES produtos(id),
            descricao  TEXT    NOT NULL,
            quantidade REAL    NOT NULL DEFAULT 1.0,
            preco_unit REAL    NOT NULL,
            subtotal   REAL    NOT NULL,
            criado_em  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS contas_a_receber (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id         INTEGER REFERENCES vendas(id),
            descricao        TEXT    NOT NULL,
            valor            REAL    NOT NULL,
            data_vencimento  TEXT    NOT NULL,
            data_recebimento TEXT,
            status           TEXT    CHECK(status IN ('pendente', 'recebido', 'cancelado')) DEFAULT 'pendente',
            numero_parcela   INTEGER DEFAULT 1,
            total_parcelas   INTEGER DEFAULT 1,
            observacao       TEXT    DEFAULT '',
            criado_em        TEXT    NOT NULL
        );
    """)

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS clientes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT    NOT NULL,
            documento   TEXT    DEFAULT '',
            telefone    TEXT    DEFAULT '',
            whatsapp    TEXT    DEFAULT '',
            email       TEXT    DEFAULT '',
            cep         TEXT    DEFAULT '',
            endereco    TEXT    DEFAULT '',
            observacao  TEXT    DEFAULT '',
            criado_em   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ordens_servico (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            numero             TEXT    NOT NULL UNIQUE,
            cliente_id         INTEGER REFERENCES clientes(id),
            solicitante_nome   TEXT    NOT NULL DEFAULT '',
            solicitante_setor  TEXT    DEFAULT '',
            solicitante_ramal  TEXT    DEFAULT '',
            data_solicitacao   TEXT    NOT NULL,
            hora_solicitacao   TEXT    DEFAULT '',
            data_execucao      TEXT,
            hora_execucao      TEXT    DEFAULT '',
            descricao_servico  TEXT    DEFAULT '',
            observacoes        TEXT    DEFAULT '',
            responsavel        TEXT    DEFAULT '',
            status             TEXT    CHECK(status IN ('aberta','em_andamento','aguardando_peca','concluida','cancelada')) DEFAULT 'aberta',
            valor_hora         REAL    NOT NULL DEFAULT 0.0,
            horas_trabalhadas  REAL    NOT NULL DEFAULT 0.0,
            criado_em          TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS itens_os (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            os_id       INTEGER NOT NULL REFERENCES ordens_servico(id),
            produto_id  INTEGER REFERENCES produtos(id),
            descricao   TEXT    NOT NULL,
            quantidade  REAL    NOT NULL DEFAULT 1.0,
            preco_unit  REAL    NOT NULL,
            subtotal    REAL    NOT NULL,
            observacao  TEXT    DEFAULT '',
            criado_em   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS os_historico (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            os_id           INTEGER NOT NULL REFERENCES ordens_servico(id),
            campo           TEXT    NOT NULL,
            valor_anterior  TEXT,
            valor_novo      TEXT,
            alterado_em     TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS itens_estoque (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            categoria       TEXT    DEFAULT '',
            unidade         TEXT    DEFAULT '',
            marca           TEXT    DEFAULT '',
            estoque_atual   REAL    NOT NULL DEFAULT 0,
            estoque_minimo  REAL    NOT NULL DEFAULT 0,
            observacao      TEXT    DEFAULT '',
            ativo           INTEGER NOT NULL DEFAULT 1,
            criado_em       TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS marcas (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL UNIQUE,
            criado_em TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS lancamentos_manuais (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            data             TEXT    NOT NULL,
            descricao        TEXT    NOT NULL,
            tipo             TEXT    NOT NULL CHECK(tipo IN ('entrada', 'saida')),
            plano_conta_id   INTEGER REFERENCES plano_contas(id),
            fonte_receita_id INTEGER REFERENCES fontes_receita(id),
            valor            REAL    NOT NULL CHECK(valor > 0),
            observacao       TEXT,
            criado_em        TEXT    NOT NULL,
            CHECK (
                (tipo = 'entrada' AND fonte_receita_id IS NOT NULL AND plano_conta_id IS NULL)
                OR
                (tipo = 'saida'   AND plano_conta_id IS NOT NULL AND fonte_receita_id IS NULL)
            )
        );

        -- Contas bancárias do usuário (Nubank, Itaú, etc).
        CREATE TABLE IF NOT EXISTS contas_banco (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nome         TEXT    NOT NULL,              -- "Nubank Principal"
            banco        TEXT,                          -- "Nubank", "Itaú Unibanco"
            tipo         TEXT    DEFAULT 'corrente'
                          CHECK(tipo IN ('corrente','poupanca','digital','salario','outra')),
            agencia      TEXT,
            numero       TEXT,
            saldo_inicial REAL   DEFAULT 0,
            ativa        INTEGER DEFAULT 1,
            criado_em    TEXT    NOT NULL
        );

        -- Lançamentos importados de extratos bancários.
        CREATE TABLE IF NOT EXISTS lancamentos_banco (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            conta_banco_id      INTEGER NOT NULL REFERENCES contas_banco(id) ON DELETE CASCADE,
            data                TEXT    NOT NULL,         -- YYYY-MM-DD
            descricao           TEXT    NOT NULL,
            valor               REAL    NOT NULL,         -- positivo=entrada, negativo=saida
            identificador_unico TEXT,                     -- FITID/UUID do banco, ou hash gerado
            plano_conta_id      INTEGER REFERENCES plano_contas(id),       -- categoria saída
            fonte_receita_id    INTEGER REFERENCES fontes_receita(id),     -- categoria entrada
            conciliado          INTEGER DEFAULT 0,        -- usuário revisou?
            conta_pagar_id      INTEGER REFERENCES contas_pagar(id),       -- conciliado com qual?
            observacao          TEXT,
            importado_em        TEXT    NOT NULL,
            UNIQUE(conta_banco_id, identificador_unico)
        );

        -- Regras de categorização automática (se descrição LIKE %padrao% → categoria).
        CREATE TABLE IF NOT EXISTS regras_categoria (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            padrao           TEXT    NOT NULL,                  -- substring case-insensitive
            tipo             TEXT    NOT NULL CHECK(tipo IN ('entrada','saida')),
            plano_conta_id   INTEGER REFERENCES plano_contas(id),
            fonte_receita_id INTEGER REFERENCES fontes_receita(id),
            prioridade       INTEGER DEFAULT 0,                 -- maior = aplicada primeiro
            ativa            INTEGER DEFAULT 1,
            criado_em        TEXT    NOT NULL,
            CHECK (
                (tipo = 'entrada' AND fonte_receita_id IS NOT NULL AND plano_conta_id IS NULL)
                OR
                (tipo = 'saida'   AND plano_conta_id IS NOT NULL AND fonte_receita_id IS NULL)
            )
        );

        -- Compromissos avulsos da Agenda (lembretes manuais que não estão
        -- vinculados a contas a pagar, receitas, OS etc. — ex: "renovar CNH",
        -- "reunião com fornecedor"). Itens das outras tabelas (contas_pagar,
        -- fontes_receita, receitas_especiais, ordens_servico) são agregados
        -- via views/agenda/agenda_model.py.
        CREATE TABLE IF NOT EXISTS agenda_eventos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo      TEXT    NOT NULL,
            descricao   TEXT    DEFAULT '',
            data        TEXT    NOT NULL,                -- YYYY-MM-DD
            hora        TEXT    DEFAULT '',              -- HH:MM ou ''
            categoria   TEXT    DEFAULT 'pessoal'
                        CHECK(categoria IN ('pessoal','trabalho','saude','outro')),
            concluido   INTEGER DEFAULT 0,
            criado_em   TEXT    NOT NULL
        );
    """)

    conn.commit()
    _migrar_plano_contas(conn)
    _migrar_fontes_receita(conn)
    _migrar_tabelas_vendas(conn)
    _migrar_tabelas_os(conn)
    _migrar_tabelas_casa(conn)
    _migrar_compras_cartao(conn)
    _migrar_dividas(conn)
    _popular_contas_padrao(conn)
    _popular_fontes_padrao(conn)
    _popular_marcas_padrao(conn)
    popular_dados_exemplo(conn)
    conn.close()


def _popular_marcas_padrao(conn: sqlite3.Connection):
    """Insere as marcas do catálogo (docs/Lista de itens de compras.txt)
    na 1ª execução. Idempotente via UNIQUE e flag em configuracoes."""
    cur = conn.cursor()
    cur.execute("SELECT valor FROM configuracoes WHERE chave='marcas_padrao_inseridas'")
    if cur.fetchone():
        return
    try:
        # Import dentro pra evitar dependência circular no boot
        from views.compras_casa.catalogo import popular_marcas_iniciais
        popular_marcas_iniciais()
    except Exception:  # pragma: no cover — tolerância máxima no boot
        return
    conn.execute(
        "INSERT OR REPLACE INTO configuracoes (chave, valor)"
        " VALUES ('marcas_padrao_inseridas', 'true')"
    )
    conn.commit()


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


def _migrar_compras_cartao(conn: sqlite3.Connection):
    """Adiciona colunas de rastreio de importação a compras_cartao (migração idempotente)."""
    colunas = {row[1] for row in conn.execute("PRAGMA table_info(compras_cartao)")}
    if "importado_numero_parcela" not in colunas:
        conn.execute("ALTER TABLE compras_cartao ADD COLUMN importado_numero_parcela INTEGER")
    if "importado_mes_ref" not in colunas:
        conn.execute("ALTER TABLE compras_cartao ADD COLUMN importado_mes_ref TEXT")
    conn.commit()


def _migrar_tabelas_vendas(conn: sqlite3.Connection):
    """Garante que as tabelas do módulo de vendas existam em bancos pré-existentes."""
    tabelas_existentes = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "produtos" not in tabelas_existentes:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nome      TEXT    NOT NULL,
                tipo      TEXT    CHECK(tipo IN ('produto', 'servico')) DEFAULT 'produto',
                preco     REAL    NOT NULL DEFAULT 0.0,
                descricao TEXT    DEFAULT '',
                ativo     INTEGER DEFAULT 1,
                criado_em TEXT    NOT NULL
            )
        """)
    if "vendas" not in tabelas_existentes:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao      TEXT    DEFAULT '',
                data_venda     TEXT    NOT NULL,
                valor_total    REAL    NOT NULL DEFAULT 0.0,
                desconto       REAL    NOT NULL DEFAULT 0.0,
                valor_liquido  REAL    NOT NULL DEFAULT 0.0,
                tipo_pagamento TEXT    CHECK(tipo_pagamento IN ('avista', 'aprazo')) DEFAULT 'avista',
                status         TEXT    CHECK(status IN ('pendente', 'paga', 'parcial', 'cancelada')) DEFAULT 'pendente',
                observacao     TEXT    DEFAULT '',
                criado_em      TEXT    NOT NULL
            )
        """)
    if "itens_venda" not in tabelas_existentes:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS itens_venda (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                venda_id   INTEGER NOT NULL REFERENCES vendas(id),
                produto_id INTEGER REFERENCES produtos(id),
                descricao  TEXT    NOT NULL,
                quantidade REAL    NOT NULL DEFAULT 1.0,
                preco_unit REAL    NOT NULL,
                subtotal   REAL    NOT NULL,
                criado_em  TEXT    NOT NULL
            )
        """)
    if "contas_a_receber" not in tabelas_existentes:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contas_a_receber (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                venda_id         INTEGER REFERENCES vendas(id),
                descricao        TEXT    NOT NULL,
                valor            REAL    NOT NULL,
                data_vencimento  TEXT    NOT NULL,
                data_recebimento TEXT,
                status           TEXT    CHECK(status IN ('pendente', 'recebido', 'cancelado')) DEFAULT 'pendente',
                numero_parcela   INTEGER DEFAULT 1,
                total_parcelas   INTEGER DEFAULT 1,
                observacao       TEXT    DEFAULT '',
                criado_em        TEXT    NOT NULL
            )
        """)
    conn.commit()


def _migrar_tabelas_os(conn: sqlite3.Connection):
    """Garante que as tabelas do módulo de Ordem de Serviço existam em bancos pré-existentes."""
    tabelas_existentes = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "clientes" not in tabelas_existentes:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nome        TEXT    NOT NULL,
                documento   TEXT    DEFAULT '',
                telefone    TEXT    DEFAULT '',
                whatsapp    TEXT    DEFAULT '',
                email       TEXT    DEFAULT '',
                cep         TEXT    DEFAULT '',
                endereco    TEXT    DEFAULT '',
                observacao  TEXT    DEFAULT '',
                criado_em   TEXT    NOT NULL
            )
        """)
    if "ordens_servico" not in tabelas_existentes:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ordens_servico (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                numero             TEXT    NOT NULL UNIQUE,
                cliente_id         INTEGER REFERENCES clientes(id),
                solicitante_nome   TEXT    NOT NULL DEFAULT '',
                solicitante_setor  TEXT    DEFAULT '',
                solicitante_ramal  TEXT    DEFAULT '',
                data_solicitacao   TEXT    NOT NULL,
                hora_solicitacao   TEXT    DEFAULT '',
                data_execucao      TEXT,
                hora_execucao      TEXT    DEFAULT '',
                descricao_servico  TEXT    DEFAULT '',
                observacoes        TEXT    DEFAULT '',
                responsavel        TEXT    DEFAULT '',
                status             TEXT    CHECK(status IN ('aberta','em_andamento','aguardando_peca','concluida','cancelada')) DEFAULT 'aberta',
                valor_hora         REAL    NOT NULL DEFAULT 0.0,
                horas_trabalhadas  REAL    NOT NULL DEFAULT 0.0,
                criado_em          TEXT    NOT NULL
            )
        """)
    else:
        # Tabela já existe (banco antigo) — adiciona cliente_id se faltar
        cols_os = {r[1] for r in conn.execute(
            "PRAGMA table_info(ordens_servico)"
        ).fetchall()}
        if "cliente_id" not in cols_os:
            conn.execute(
                "ALTER TABLE ordens_servico"
                " ADD COLUMN cliente_id INTEGER REFERENCES clientes(id)"
            )
    if "itens_os" not in tabelas_existentes:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS itens_os (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                os_id       INTEGER NOT NULL REFERENCES ordens_servico(id),
                produto_id  INTEGER REFERENCES produtos(id),
                descricao   TEXT    NOT NULL,
                quantidade  REAL    NOT NULL DEFAULT 1.0,
                preco_unit  REAL    NOT NULL,
                subtotal    REAL    NOT NULL,
                observacao  TEXT    DEFAULT '',
                criado_em   TEXT    NOT NULL
            )
        """)
    if "os_historico" not in tabelas_existentes:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS os_historico (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                os_id           INTEGER NOT NULL REFERENCES ordens_servico(id),
                campo           TEXT    NOT NULL,
                valor_anterior  TEXT,
                valor_novo      TEXT,
                alterado_em     TEXT    NOT NULL
            )
        """)
    conn.commit()


def _migrar_tabelas_casa(conn: sqlite3.Connection):
    """Garante que itens_estoque e marcas existam em bancos pré-existentes,
    e adiciona a coluna `marca` em itens_estoque se faltar."""
    tabelas = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "itens_estoque" not in tabelas:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS itens_estoque (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nome            TEXT    NOT NULL,
                categoria       TEXT    DEFAULT '',
                unidade         TEXT    DEFAULT '',
                marca           TEXT    DEFAULT '',
                estoque_atual   REAL    NOT NULL DEFAULT 0,
                estoque_minimo  REAL    NOT NULL DEFAULT 0,
                observacao      TEXT    DEFAULT '',
                ativo           INTEGER NOT NULL DEFAULT 1,
                criado_em       TEXT    NOT NULL
            )
        """)
    else:
        # Tabela já existe — verifica se a coluna marca precisa ser adicionada
        cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(itens_estoque)"
        ).fetchall()}
        if "marca" not in cols:
            conn.execute(
                "ALTER TABLE itens_estoque ADD COLUMN marca TEXT DEFAULT ''"
            )
    if "marcas" not in tabelas:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS marcas (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nome      TEXT    NOT NULL UNIQUE,
                criado_em TEXT    NOT NULL
            )
        """)
    conn.commit()


def _migrar_dividas(conn: sqlite3.Connection):
    """Garante schema atualizado da tabela `dividas` em bancos pré-existentes:

    1. Adiciona a coluna `limite_total` (usada por tipo='cheque_especial').
    2. Relaxa o CHECK do `tipo` pra aceitar 'cheque_especial'. SQLite não
       permite ALTER CHECK, então faz table redefinition (cria nova tabela,
       copia dados, dropa e renomeia — operação segura dentro de transação).
    3. Cria a tabela `juros_cheque_especial` se faltar (histórico de juros
       descontados pelo banco em cheque especial).
    """
    cur = conn.cursor()
    cols = {r[1] for r in cur.execute("PRAGMA table_info(dividas)").fetchall()}

    # (1) Coluna limite_total
    if "limite_total" not in cols:
        cur.execute("ALTER TABLE dividas ADD COLUMN limite_total REAL DEFAULT 0")

    # (2) CHECK do tipo — só rebuilda se for um schema antigo (sem cheque_especial)
    row = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='dividas'"
    ).fetchone()
    schema_atual = (row[0] if row else "") or ""
    if "cheque_especial" not in schema_atual:
        # Table redefinition: cria com schema novo, copia dados, dropa e renomeia
        cur.executescript("""
            CREATE TABLE dividas_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nome            TEXT NOT NULL,
                tipo            TEXT CHECK(tipo IN ('cartao', 'emprestimo', 'financiamento',
                                                    'cheque_especial', 'outro')),
                saldo_atual     REAL NOT NULL,
                parcela_mensal  REAL NOT NULL,
                total_parcelas  INTEGER NOT NULL,
                parcelas_pagas  INTEGER DEFAULT 0,
                dia_vencimento  INTEGER,
                taxa_juros      REAL DEFAULT 0,
                limite_total    REAL DEFAULT 0,
                observacao      TEXT,
                ativa           INTEGER DEFAULT 1,
                criado_em       TEXT
            );
            INSERT INTO dividas_new
                (id, nome, tipo, saldo_atual, parcela_mensal, total_parcelas,
                 parcelas_pagas, dia_vencimento, taxa_juros, limite_total,
                 observacao, ativa, criado_em)
            SELECT id, nome, tipo, saldo_atual, parcela_mensal, total_parcelas,
                   parcelas_pagas, dia_vencimento, taxa_juros,
                   COALESCE(limite_total, 0),
                   observacao, ativa, criado_em
            FROM dividas;
            DROP TABLE dividas;
            ALTER TABLE dividas_new RENAME TO dividas;
        """)

    # (3) Histórico de juros descontados em cheque especial
    cur.execute("""
        CREATE TABLE IF NOT EXISTS juros_cheque_especial (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            divida_id       INTEGER NOT NULL REFERENCES dividas(id),
            data            TEXT    NOT NULL,
            valor           REAL    NOT NULL,
            observacao      TEXT    DEFAULT '',
            conta_pagar_id  INTEGER REFERENCES contas_pagar(id),
            criado_em       TEXT    NOT NULL
        )
    """)
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
    ("Juros — Cheque Especial",        "variavel","Despesas Bancárias"),
    ("Tarifas bancárias",              "fixo",    "Despesas Bancárias"),
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
            DELETE FROM juros_cheque_especial;
            -- Filhas de plano_contas/fontes_receita/contas_pagar: apagar ANTES
            -- das pais (foreign_keys=ON faria o DELETE das pais falhar).
            DELETE FROM lancamentos_banco;
            DELETE FROM contas_banco;
            DELETE FROM regras_categoria;
            DELETE FROM lancamentos_manuais;
            DELETE FROM agenda_eventos;
            DELETE FROM metas_financeiras;
            DELETE FROM contas_pagar;
            DELETE FROM plano_contas;
            DELETE FROM fontes_receita;
            DELETE FROM receitas_especiais;
            DELETE FROM dividas;
            DELETE FROM backups;
            DELETE FROM contas_a_receber;
            DELETE FROM itens_venda;
            DELETE FROM vendas;
            DELETE FROM os_historico;
            DELETE FROM itens_os;
            DELETE FROM ordens_servico;
            DELETE FROM clientes;
            DELETE FROM itens_estoque;
            DELETE FROM marcas;
            DELETE FROM produtos;
        """)
        conn.execute("""
            DELETE FROM configuracoes
            WHERE chave IN (
                'contas_padrao_inseridas',
                'fontes_padrao_inseridas',
                'bandeiras_custom'
            )
        """)
        # BUGFIX: marca dados_exemplo_inseridos como 'true' ANTES de chamar
        # inicializar_banco(). Antes, a flag era setada DEPOIS — e o
        # popular_dados_exemplo() chamado por inicializar_banco() re-inseria
        # "13º Salário" e "Férias + 1/3" em receitas_especiais. Resultado:
        # o usuário zerava o sistema mas essas 2 entradas voltavam sozinhas.
        conn.execute(
            "INSERT OR REPLACE INTO configuracoes (chave, valor) "
            "VALUES ('dados_exemplo_inseridos', 'true')"
        )
    inicializar_banco()
    # Redundante mas mantido por garantia (caso o INSERT OR REPLACE acima
    # seja perdido em algum edge case de transação).
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
