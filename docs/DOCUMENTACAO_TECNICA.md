# Serenus — Documentação Técnica

> Para desenvolvedores · Português BR

---

## Sumário

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Estrutura de Diretórios](#2-estrutura-de-diretórios)
3. [Banco de Dados](#3-banco-de-dados)
4. [Camada de Dados (Models)](#4-camada-de-dados-models)
5. [Camada de Apresentação (Views)](#5-camada-de-apresentação-views)
6. [Configuração e Constantes](#6-configuração-e-constantes)
7. [Módulo de Demonstração](#7-módulo-de-demonstração)
8. [Módulo de Exportação Excel](#8-módulo-de-exportação-excel)
9. [Sistema de Testes](#9-sistema-de-testes)
10. [Convenções e Padrões](#10-convenções-e-padrões)
11. [Bugs Corrigidos (histórico)](#11-bugs-corrigidos-histórico)
12. [Dependências Externas](#12-dependências-externas)

---

## 1. Visão Geral da Arquitetura

O Serenus segue uma arquitetura em **duas camadas** sem framework MVC explícito:

```
┌─────────────────────────────────────────────┐
│              main.py (entry point)          │
├─────────────────────────────────────────────┤
│         views/main_window.py                │
│     (janela principal + roteamento)         │
├──────────────────┬──────────────────────────┤
│   Views (.py)    │      Models (.py)        │
│  CustomTkinter   │  Lógica + SQLite direto  │
├──────────────────┴──────────────────────────┤
│         database.py (conexão + DDL)         │
├─────────────────────────────────────────────┤
│           serenus.db (SQLite)               │
└─────────────────────────────────────────────┘
```

**Decisões de design:**
- Sem ORM — SQL puro via `sqlite3` com `row_factory = sqlite3.Row`
- Sem injeção de dependência — `database.conectar()` é importada diretamente nos models
- Views criam e destroem `CTkFrame`s dinamicamente ao navegar
- Cada módulo tem seu `_model.py` isolado; a view nunca acessa o banco diretamente

---

## 2. Estrutura de Diretórios

```
E:\_Projeto_Serenus\
│
├── main.py                     # Entry point — inicializa banco e abre a janela
├── database.py                 # Conexão, DDL (CREATE TABLE), seed de dados padrão
├── config.py                   # Constantes globais, temas, formatadores
├── demo_manager.py             # 8 perfis de dados de demonstração
│
├── views/
│   ├── main_window.py          # Janela raiz: sidebar + área de conteúdo
│   ├── setup_view.py           # Tela de setup inicial (nome do usuário)
│   ├── auth_dialog.py          # Diálogo de autenticação (PIN)
│   │
│   ├── contas_pagar/
│   │   ├── conta_model.py      # CRUD: plano_contas + contas_pagar
│   │   ├── lista_view.py       # Tela principal de Contas a Pagar
│   │   ├── form_view.py        # Modal de nova/editar despesa (+ pagar com cartão)
│   │   └── plano_view.py       # Tela de Plano de Contas
│   │
│   ├── receitas/
│   │   ├── receita_model.py    # CRUD: fontes_receita + receitas_especiais
│   │   └── receita_view.py     # Tela com duas abas (Fontes / Especiais)
│   │
│   ├── cartoes/
│   │   ├── cartao_model.py     # CRUD: cartoes + compras_cartao + parcelas_cartao
│   │   ├── cartoes_view.py     # Tela principal (lista de cartões)
│   │   ├── form_cartao.py      # Modal de novo/editar cartão
│   │   ├── form_compra.py      # Modal de nova compra no cartão
│   │   └── faturas_view.py     # Tela de faturas mensais
│   │
│   ├── visao_longo_prazo/
│   │   ├── divida_model.py     # CRUD + projeção: dividas
│   │   └── dividas_view.py     # Tela de dívidas com gráfico de evolução
│   │
│   ├── visao_futura/
│   │   ├── projecao_model.py   # Cálculo de projeção financeira mensal
│   │   └── visao_futura_view.py# Tela com abas (Projeção / Receitas vs Despesas)
│   │
│   ├── fluxo_caixa/
│   │   ├── fluxo_model.py      # Projeção de fluxo (MesFluxo + resumo)
│   │   ├── fluxo_view.py       # Tela de Fluxo de Caixa (tela inicial do app)
│   │   ├── extrato_model.py    # Extrato de lançamentos reais
│   │   └── extrato_view.py     # Tela de extrato com busca e filtros
│   │
│   ├── investimentos/
│   │   ├── investimento_model.py  # CRUD: contas_inv + ativos + movimentacoes + posicao_cache
│   │   ├── carteira_view.py       # Tela principal (4 abas)
│   │   ├── form_conta_inv.py      # Modal de conta de investimento
│   │   ├── form_ativo.py          # Modal de ativo
│   │   ├── form_movimentacao.py   # Modal de movimentação
│   │   ├── cotacao_service.py     # Busca de cotações (yfinance / manual)
│   │   └── ir_model.py            # Cálculo de IR sobre lucros realizados
│   │
│   ├── metas/
│   │   ├── metas_model.py      # CRUD: metas_financeiras + cálculos de progresso
│   │   └── metas_view.py       # Tela de metas com barras de progresso
│   │
│   ├── alertas/
│   │   ├── alertas_model.py    # Geração de alertas (contas, cartão, renda fixa)
│   │   └── alertas_view.py     # Modal lateral de alertas
│   │
│   ├── exportar/
│   │   └── exportar_model.py   # 9 funções de exportação para .xlsx (openpyxl)
│   │
│   ├── backup/
│   │   └── backup_view.py      # Tela de backup/restauração
│   │
│   └── configuracoes/
│       └── config_view.py      # Tela de configurações e dados de demonstração
│
├── tests/
│   ├── conftest.py             # Fixture `banco` — DB SQLite em memória
│   ├── test_alertas_model.py
│   ├── test_busca_filtro.py
│   ├── test_cotacao_ir.py
│   ├── test_exportar_model.py
│   ├── test_exportar_todos.py
│   ├── test_investimento_model.py
│   ├── test_metas_model.py
│   └── test_pagar_com_cartao.py
│
└── docs/
    ├── MANUAL_USUARIO.md
    └── DOCUMENTACAO_TECNICA.md
```

---

## 3. Banco de Dados

### 3.1 Arquivo e localização

```python
# config.py
DATABASE_PATH = Path(__file__).parent / "serenus.db"
```

O banco fica na raiz do projeto. Em testes, o `conftest.py` injeta um banco em memória via monkey-patch de `database.conectar`.

### 3.2 Conexão

```python
# database.py
def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row   # acesso por nome de coluna
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

Uso padrão nos models:
```python
with conectar() as conn:
    rows = conn.execute("SELECT ...", params).fetchall()
```
O `with` faz `commit` ao sair sem exceção e `rollback` em caso de erro.

### 3.3 Esquema (tabelas principais)

| Tabela | Descrição |
|--------|-----------|
| `plano_contas` | Categorias de despesas (fixo/variável) |
| `contas_pagar` | Lançamentos de despesas |
| `fontes_receita` | Fontes de renda recorrentes |
| `receitas_especiais` | Receitas pontuais (13º, férias, bônus) |
| `cartoes` | Cartões de crédito |
| `compras_cartao` | Compras parceladas |
| `parcelas_cartao` | Parcelas individuais |
| `dividas` | Empréstimos e financiamentos |
| `contas_investimento` | Contas em corretoras/bancos |
| `ativos` | Ativos individuais (ações, FIIs, CDBs) |
| `movimentacoes_investimento` | Histórico de compras, vendas, rendimentos |
| `posicao_cache` | Cache calculado da posição atual por ativo |
| `metas_financeiras` | Objetivos financeiros |
| `configuracoes` | Chave-valor para preferências |

### 3.4 Indexação de meses em `receitas_especiais`

> ⚠️ **Convenção obrigatória:** o campo `mes` usa **indexação 0-based** (0 = Janeiro, 11 = Dezembro).

Esta convenção é usada em:
- `receita_model._gerar_especiais_clt` (insere `mes=5` para Junho, `mes=11` para Dezembro)
- `receita_model.total_previsto_mes(mes_0, ano)` — recebe `mes_0 = 0..11`
- `fluxo_model` — itera meses como `date.month - 1`
- Visualização: `NOMES_MESES[e.mes]` (guarda com `if 0 <= e.mes <= 11 else "—"`)

**Nunca** inserir meses como 1-12 nesta tabela.

---

## 4. Camada de Dados (Models)

### 4.1 Padrão de CRUD

Todos os models seguem o mesmo padrão:

```python
@dataclass
class Entidade:
    id: int
    campo: str
    ...

def listar_entidades(...) -> list[Entidade]: ...
def salvar_entidade(dados: dict, id: Optional[int] = None) -> int: ...
def excluir_entidade(id: int): ...
```

**Regra crítica:** A verificação de `id` para decidir INSERT vs UPDATE usa `if id is not None:` (não `if id:`), pois `id=0` seria falsy mas válido.

### 4.2 conta_model.py

```python
# Fluxo de atualizar recorrentes futuros
def atualizar_recorrentes_futuros(conta_id: int, dados: dict) -> int:
    # Busca plano_conta_id da conta editada
    # Se plano_conta_id IS NULL: usa "IS NULL" no WHERE (não "= NULL")
    # Se não: usa "= ?"
    # Atualiza todos os pendentes futuros com mesmo plano e recorrente=1
```

> **Atenção SQL:** `WHERE campo = NULL` nunca faz match em SQL; usar `WHERE campo IS NULL`.

### 4.3 cartao_model.py

Função central: `registrar_compra_parcelas(dados: dict) -> int`

Fluxo:
1. Calcula `parcela_base` e `ultima_parcela` (absorve arredondamento)
2. Insere `compras_cartao`
3. Insere N registros em `parcelas_cartao` com `mes_referencia = "YYYY-MM"`
4. Debita `limite_disponivel` em `cartoes`
5. Chama `_atualizar_divida_cartao(conn, cartao_id)` para sincronizar `dividas`

`_atualizar_divida_cartao`:
- Calcula saldo total das parcelas pendentes
- Faz UPDATE em `dividas WHERE nome=? AND tipo='cartao'`
- Se `rowcount == 0` e há saldo pendente: recria a dívida (INSERT)

### 4.4 investimento_model.py

**Posição cache:**

```python
def _recalcular_posicao(ativo_id: int) -> None:
    # Lê movimentacoes_investimento ordenadas por data
    # Calcula: qtd_atual, val_inv, lucro_realizado
    # Preserva valor_atual manual se > 0 e posição ainda aberta
    # Se posição fechada: valor_atual = 0
    # Grava em posicao_cache (INSERT OR REPLACE)
```

Tipos de movimentação e impacto na posição:

| Tipo | `qtd_atual` | `val_inv` | `lucro_realizado` |
|------|-------------|-----------|-------------------|
| compra / aplicacao | + qtd | + val_liq | — |
| venda | − qtd (prop) | − custo proporcional | + (val − custo) |
| resgate | — | − val proporcional | + (val − custo) |
| amortizacao | — | − val | — |
| dividendo / juros / taxa / imposto | — | — | — |

**Integração financeira:** se `registrar_no_financeiro=True` e o tipo está em `MOV_INV_SAIDA` (compra, aplicacao, taxa, imposto), cria registro em `contas_pagar` automaticamente.

### 4.5 divida_model.py

```python
def projetar_evolucao(dividas, meses=36):
    # Para cada mês i de 0..max_parcelas:
    #   saldo = Σ max(0, d.saldo_atual - d.parcela_mensal * i) para dividas com restantes > i
    # Interrompe quando saldo <= 0 E i >= meses (evita corte prematuro)
```

### 4.6 ir_model.py

Calcula IR sobre lucros realizados por tipo de ativo:

| Tipo | Alíquota |
|------|----------|
| acao, etf | 15% |
| fii | 20% |
| cripto | 15% |
| cdb/lc (até 180 dias) | 22,5% |
| cdb/lc (181–360 dias) | 20% |
| cdb/lc (361–720 dias) | 17,5% |
| cdb/lc (>720 dias) | 15% |
| tesouro | idem CDB (regressivo) |

---

## 5. Camada de Apresentação (Views)

### 5.1 main_window.py

```python
class MainWindow(ctk.CTk):
    def _navegar(self, chave: str):
        # Destroi a view atual
        # Cria nova view via _criar_view(chave)
        # Posiciona com .grid(row=0, column=0, sticky="nsew")
    
    def _criar_view(self, chave: str) -> ctk.CTkFrame:
        # Mapa chave → lambda(parent) → View
        # "dashboard" → FluxoCaixaView(p, modo_inicio=True)
        # "fluxo_caixa" → ExtratoCaixaView(p)
        ...
```

A tela inicial padrão (`"dashboard"`) carrega `FluxoCaixaView` com `modo_inicio=True`, que exibe a data de hoje no título em vez de "🔄 Fluxo de Caixa".

### 5.2 Padrão de View

```python
class XView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cores = get_tema(obter_configuracao("tema", "claro"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        # cabeçalho em row=0
        # conteúdo em row=1 (CTkScrollableFrame ou CTkTabview)
        self._carregar()
    
    def _carregar(self):
        # Lê dados do model e reconstrói os widgets
        ...
```

### 5.3 Regras de geometry manager

> **Nunca misturar `pack` e `grid` em um mesmo frame pai.**

Cada frame usa exclusivamente um dos dois. Quando um widget filho tem filhos próprios, esses filhos podem usar qualquer manager internamente.

Erro frequente: um frame posicionado com `.grid()` e depois chamando `.pack_configure()` no mesmo frame. Isso causa `TclError: cannot use geometry manager pack inside ... which already has slaves managed by grid`.

### 5.4 Formulários modais

Formulários são `ctk.CTkToplevel` com `grab_set()`. Ao salvar:
1. Chama a função do model
2. Chama `self._on_salvo(msg=...)` callback passado pelo caller
3. Chama `self.destroy()`

### 5.5 cartera_view.py — InvestimentosView

4 abas: Carteira | Movimentações | Dashboard | Ativos / Contas

**Dashboard — `_draw_alocacao`:**
- Canvas separado de 58px para a barra colorida
- Frame CTk com grade de 2 colunas para a legenda (sem canvas — usa `CTkFrame` com `fg_color` como quadradinho colorido)

---

## 6. Configuração e Constantes

### 6.1 config.py — principais exports

```python
DATABASE_PATH: Path          # caminho do banco SQLite
SIDEBAR_WIDTH: int           # largura da sidebar (220)
MIN_WIDTH, MIN_HEIGHT: int   # tamanho mínimo da janela
NOMES_MESES: list[str]       # ["Janeiro", ..., "Dezembro"] — índice 0-based
LABEL_TIPO_ATIVO: dict       # {"acao": "Ação", "fii": "FII", ...}
LABEL_TIPO_MOV_INV: dict     # nomes amigáveis para tipos de movimentação
CORES_TIPO_ATIVO: dict       # cores hex por tipo de ativo
MOV_INV_SAIDA: set[str]      # tipos que geram saída financeira: {"compra","aplicacao","taxa","imposto"}
NOMES_BANCOS: dict           # {"nubank": "Nubank", ...}

def get_tema(nome: str) -> dict:
    # Retorna dict de cores para "claro" ou "escuro"
    # Chaves: fundo, card, sidebar, texto, texto_mudo, primario,
    #         borda, positivo, negativo, alerta, ...

def formatar_moeda(valor: float) -> str:
    # "R$ 1.234,56"

def parsear_data(texto: str) -> str:
    # Aceita "DD/MM/YYYY" ou "YYYY-MM-DD", retorna "YYYY-MM-DD"
```

### 6.2 database.py — funções principais

```python
def inicializar_banco() -> None:
    # Cria todas as tabelas (CREATE TABLE IF NOT EXISTS)
    # Executa _popular_fontes_padrao() e popular_dados_exemplo()
    # Insere planos de contas padrão

def popular_dados_exemplo() -> None:
    # Insere dados iniciais (dividas de exemplo, fontes padrão)
    # Chamado apenas se banco está vazio

def salvar_configuracao(chave: str, valor: str) -> None:
def obter_configuracao(chave: str, padrao: str = "") -> str:
    # Chave-valor em tabela `configuracoes`
```

---

## 7. Módulo de Demonstração

**Arquivo:** `demo_manager.py`

### 7.1 Entry point

```python
def popular_modo_demo(perfil: str = "padrao") -> int:
    # Chama a função do perfil selecionado
    # Retorna total de lançamentos em contas_pagar inseridos
```

### 7.2 Perfis disponíveis

Registrados em `PERFIS_DEMO: dict[str, str]` e `_PERFIL_FNS: dict[str, Callable]`.

Cada função de perfil `_popular_X(conn, planos, rng, hoje)`:
1. Atualiza `fontes_receita` (UPDATE por nome)
2. Recria `receitas_especiais` (DELETE + INSERT)
3. Chama `_inserir_lancamentos()` para gerar contas a pagar com histórico
4. Chama `_inserir_cartao()` + `_inserir_compras()` para cartões
5. Chama `_inserir_dividas()` para dívidas
6. Chama `_popular_investimentos_X()` (perfis 6–8)
7. Chama `_inserir_metas()` (perfis 6–8)

### 7.3 Helpers reutilizáveis

```python
def _mes_add(ref: date, n: int) -> tuple[int, int]:
    # Retorna (ano, mes) para ref + N meses

def _inserir_lancamentos(conn, planos, fixas, variaveis, hoje, rng,
                          offset_range=range(-60, 61), fator_fn=None):
    # Gera contas_pagar históricas e futuras
    # fixas: list[(nome_plano, valor_base, dia_venc)]
    # variaveis: list[(nome_plano, lo, hi, dia_venc, prob)]
    # fator_fn: callable(offset) → multiplicador (para perfis crescentes/decrescentes)

def _criar_ativos_inv(conn, ativos_def, agora) -> dict[str, int]:
    # ativos_def: list[(codigo, nome, tipo, conta_id, indexador, taxa, vencimento)]
    # Retorna {codigo: ativo_id}

def _inserir_movimentacoes_inv(conn, rng, hoje, ativo_ids, movs):
    # movs: list[(codigo, tipo, qtd, val, offset_meses)]
    # Integra com contas_pagar para saídas históricas

def _recalcular_posicoes_demo(conn, ativo_ids):
    # Recalcula posicao_cache para todos os ativos inseridos
    # Aplica variação aleatória determinística (seed = hash(codigo))

def _inserir_metas(conn, metas):
    # metas: list[(nome, valor_alvo, valor_atual, prazo_iso|None, descricao)]

def _data_offset_str(ref, meses, dia=15) -> str:
    # Data ISO para ref + N meses, fixada no dia informado
```

---

## 8. Módulo de Exportação Excel

**Arquivo:** `views/exportar/exportar_model.py`

### 8.1 Helpers internos

```python
_FILL_HDR   # PatternFill azul-marinho (#1E3A5F)
_FILL_ALT   # PatternFill cinza claro (#F3F4F6) — linhas pares
_FILL_TOT   # PatternFill azul claro (#DBEAFE) — linha de totais
_FONT_HDR   # Font branca negrito
_ALIGN_CTR  # Alignment centralizado
_BORDER     # Border fina em todos os lados

def _aplicar_cabecalho(ws, cols, widths):
    # Aplica estilo _FILL_HDR + _FONT_HDR + _ALIGN_CTR na linha 1
    # Define larguras de coluna

def _cel_moeda(ws, row, col, valor):
    # Insere valor float com format_code 'R#,##0.00'

def _linha_totais(ws, row, col_label, label, col_val, valor):
    # Linha com _FILL_TOT e font negrito
```

### 8.2 Funções exportadoras

| Função | Entrada | Saída |
|--------|---------|-------|
| `exportar_extrato_xlsx(mes, ano, caminho)` | mês/ano | 1 aba: Extrato |
| `exportar_carteira_xlsx(caminho)` | — | 1 aba: Carteira |
| `exportar_fatura_xlsx(cartao_id, mes, ano, caminho)` | cartão/mês/ano | 1 aba: Fatura |
| `exportar_contas_pagar_xlsx(mes, ano, caminho)` | mês/ano | 2 abas: Despesas + Resumo |
| `exportar_dividas_xlsx(caminho)` | — | 2 abas: Dívidas Ativas + Projeção |
| `exportar_receitas_xlsx(caminho)` | — | 2 abas: Fontes + Especiais |
| `exportar_projecao_xlsx(caminho, meses=60)` | meses | 1 aba: Projeção N Meses |
| `exportar_metas_xlsx(caminho)` | — | 1 aba: Metas |
| `exportar_ir_xlsx(caminho)` | — | 1 aba: IR Estimado |

---

## 9. Sistema de Testes

### 9.1 Configuração

```python
# tests/conftest.py
@pytest.fixture
def banco(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    conn_factory = lambda: sqlite3.connect(str(db_path))
    monkeypatch.setattr("database.conectar", conn_factory)
    database.inicializar_banco()
    yield
```

O fixture `banco` injeta um banco temporário limpo para cada teste, garantindo isolamento total.

### 9.2 Cobertura atual

| Arquivo de teste | O que cobre | Testes |
|-----------------|-------------|--------|
| `test_alertas_model.py` | Geração de alertas por tipo/urgência | 19 |
| `test_busca_filtro.py` | Busca em contas_pagar e extrato | 14 |
| `test_cotacao_ir.py` | CotacaoService + cálculo de IR | 16 |
| `test_exportar_model.py` | Exportar extrato, carteira, fatura | 9 |
| `test_exportar_todos.py` | Exportar contas, dívidas, receitas, projeção, metas, IR | 44 |
| `test_investimento_model.py` | Compras, vendas, posição, integração financeira | 53 |
| `test_metas_model.py` | CRUD, progresso, prazo | 17 |
| `test_pagar_com_cartao.py` | Parcelas, limite, integração com contas_pagar | 14 |
| **Total** | | **186** |

### 9.3 Executando os testes

```bash
cd E:\_Projeto_Serenus
python -m pytest tests/ -v          # verbose
python -m pytest tests/ -q          # resumido
python -m pytest tests/test_X.py   # módulo específico
```

### 9.4 Padrão TDD adotado

1. Escrever o teste que falha
2. Implementar o mínimo para passar
3. Verificar 100% dos testes ainda passando (sem regressão)

### 9.5 Atenção: dados de seed

`inicializar_banco()` chama `popular_dados_exemplo()` que insere 4 dívidas e 8 fontes de receita por padrão. Testes que verificam "banco vazio" devem limpar essas tabelas explicitamente:

```python
def _limpar_dividas(banco):
    from database import conectar
    with conectar() as c:
        c.execute("DELETE FROM dividas")

def _limpar_fontes(banco):
    from database import conectar
    with conectar() as c:
        c.execute("DELETE FROM fontes_receita")
        c.execute("DELETE FROM receitas_especiais")
```

---

## 10. Convenções e Padrões

### 10.1 Nomenclatura

| Elemento | Convenção | Exemplo |
|----------|-----------|---------|
| Classe de View | PascalCase + `View` | `ContasPagarView` |
| Classe de Model (data) | PascalCase | `ContaPagar`, `Divida` |
| Função de listagem | `listar_X` | `listar_contas` |
| Função de salvamento | `salvar_X` | `salvar_conta` |
| Função de exclusão | `excluir_X` | `excluir_conta` |
| Widget privado | `_widget_nome` | `self._entry_valor` |
| Método privado | `_verbo_substantivo` | `_carregar`, `_on_salvo` |

### 10.2 Passagem de dados para forms

```python
# Abrindo um form modal
def _editar(self, conta: ContaPagar):
    from views.contas_pagar.form_view import ContaPagarFormModal
    ContaPagarFormModal(
        self,
        conta=conta,
        planos=self._planos,
        on_salvo=self._on_form_salvo,
    )

# Callback padrão
def _on_form_salvo(self, msg: str = "Salvo com sucesso."):
    self._carregar()
    self._toast(msg)
```

### 10.3 Toast de feedback

Views com `CTkScrollableFrame` implementam `_toast(msg)`:

```python
def _toast(self, msg: str, duracao_ms: int = 2500):
    lbl = ctk.CTkLabel(self, text=msg, fg_color=cores["primario"], ...)
    lbl.place(relx=0.5, rely=0.95, anchor="center")
    self.after(duracao_ms, lbl.destroy)
```

Views sem scroll usam `tkinter.messagebox.showinfo`.

### 10.4 Temas

```python
cores = get_tema(obter_configuracao("tema", "claro"))
# Chaves obrigatórias: fundo, card, sidebar, texto, texto_mudo,
#                      primario, borda, positivo, negativo, alerta
```

Todo widget que usa cor deve ler de `self._cores`, nunca hardcodar hex.

---

## 11. Bugs Corrigidos (histórico)

| # | Onde | Descrição | Impacto |
|---|------|-----------|---------|
| 1 | `demo_manager.py` / perfil `em_ritmo` | Meses inseridos como 1-indexed (ex: `mes=12`) em vez de 0-indexed. `mes=12` causava `IndexError` em exportação | Crash |
| 2 | Todos os models com `salvar_X` | `if id:` não diferencia `id=0` de `id=None`; corrigido para `if id is not None:` | Silencioso |
| 3 | `conta_model.atualizar_recorrentes_futuros` | `WHERE plano_conta_id = NULL` nunca faz match em SQL; tratado com ramo `IS NULL` | Dados errados |
| 4 | `divida_model.projetar_evolucao` | `break` quando `saldo <= 0` truncava o gráfico prematuramente; condição mudada para `saldo <= 0 and i >= meses` | Dados errados |
| 5 | `exportar_model.exportar_receitas_xlsx` | `NOMES_MESES[e.mes]` sem guard; adicionado `if 0 <= e.mes <= 11` | Crash |
| 6 | `cartao_model._atualizar_divida_cartao` | Só fazia UPDATE; se a dívida do cartão fosse excluída manualmente, o UPDATE não afetava nenhuma linha. Adicionado INSERT de fallback | Dados errados |
| 7 | `carteira_view._draw_vencimentos` | Chamava `parent.pack_configure()` em frame gerenciado por `grid` | Crash ao abrir Investimentos |
| 8 | `receita_view._linha` | `NOMES_MESES[e.mes]` sem guard; corrigido para `NOMES_MESES[e.mes] if 0 <= e.mes <= 11 else "—"` | Crash ao abrir Receitas |
| 9 | `carteira_view._draw_alocacao` | Canvas de altura fixa (180px) para legenda causava sobreposição de texto; refatorado para widgets CTk em grade 2 colunas | Visual |
| 10 | `metas_view.py` linha 226 | Aspas tipográficas (`"`) dentro de f-string com aspas duplas causavam `SyntaxError` | Crash no startup |

---

## 12. Dependências Externas

```
customtkinter >= 5.2    # UI principal
Pillow >= 10.0          # Processamento de imagens (logo)
openpyxl >= 3.1         # Exportação Excel
matplotlib >= 3.7       # Gráficos (canvas integrado no tkinter)
numpy >= 1.24           # Cálculos para gráficos matplotlib
yfinance >= 0.2         # Cotações de ativos (opcional — fallback manual)
pytest >= 7.0           # Testes
```

Instalação:
```bash
pip install customtkinter pillow openpyxl matplotlib numpy yfinance pytest
```

Python mínimo: **3.12** (uso de `match/case` e type hints modernos em algumas partes).

---

*Serenus — Documentação Técnica v1.0*
