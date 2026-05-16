# Serenus — Finanças Pessoais

> Aplicativo desktop de finanças pessoais, desenvolvido em Python com CustomTkinter e SQLite.  
> Todos os dados ficam salvos localmente — nenhuma informação é enviada para a internet.

---

## Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| 💰 Minhas Receitas | Cadastro de fontes de renda e receitas especiais (13º, férias, bônus) |
| 💸 Contas a Pagar | Registro e acompanhamento de despesas mensais com suporte a parcelamento no cartão |
| 💳 Cartões | Controle de faturas e compras parceladas |
| 📉 Dívidas | Projeção de evolução de empréstimos e financiamentos |
| 📋 Plano de Contas | Categorização de despesas |
| 📊 Visão Financeira | Projeção de saldo para os próximos meses |
| 🔄 Fluxo de Caixa | Resumo de receitas × despesas com gráficos |
| 📈 Investimentos | Carteira de renda variável, fixa e fundos com cálculo de IR |
| 🎯 Metas | Acompanhamento de objetivos financeiros com barra de progresso |
| 💾 Backup | Backup e restauração local dos dados |

---

## Requisitos

- **Python 3.12+**
- Dependências listadas em `requirements.txt`

---

## Como rodar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/serenus.git
cd serenus
```

### 2. Crie e ative um ambiente virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Execute o aplicativo

```bash
python main.py
```

Na primeira execução, o banco de dados `serenus.db` é criado automaticamente na raiz do projeto.

---

## Dados de demonstração

Para explorar o sistema sem precisar cadastrar dados manualmente:

1. Abra o app → **Configurações → Dados de demonstração**
2. Selecione um dos 8 perfis disponíveis (Padrão, Apertado, Investidor iniciante etc.)
3. Clique em **Carregar perfil**

---

## Estrutura do projeto

```
serenus/
│
├── main.py                   # Entry point
├── database.py               # Conexão SQLite, DDL e seed inicial
├── config.py                 # Constantes, temas e formatadores globais
├── demo_manager.py           # 8 perfis de dados de demonstração
├── backup_manager.py         # Lógica de backup local e integração Google Drive
├── google_drive.py           # Integração opcional com Google Drive
├── pytest.ini                # Configuração dos testes
├── requirements.txt          # Dependências Python
│
├── views/                    # Interface gráfica (CustomTkinter)
│   ├── main_window.py        # Janela principal + roteamento de telas
│   ├── contas_pagar/         # Módulo Contas a Pagar
│   ├── receitas/             # Módulo Minhas Receitas
│   ├── cartoes/              # Módulo Cartões
│   ├── visao_longo_prazo/    # Módulo Dívidas
│   ├── visao_futura/         # Módulo Visão Financeira
│   ├── fluxo_caixa/          # Módulo Fluxo de Caixa
│   ├── investimentos/        # Módulo Investimentos
│   ├── metas/                # Módulo Metas
│   ├── alertas/              # Sistema de alertas automáticos
│   ├── exportar/             # Exportação para Excel (.xlsx)
│   ├── backup/               # Tela de backup
│   └── configuracoes/        # Tela de configurações
│
├── imagens/                  # Ícone e logos do app
├── docs/                     # Documentação
│   ├── MANUAL_USUARIO.md
│   └── DOCUMENTACAO_TECNICA.md
│
└── tests/                    # Testes automatizados (pytest)
```

---

## Rodando os testes

```bash
pytest tests/ -v
```

Todos os testes usam banco em memória — nenhum dado real é afetado.

---

## Exportação para Excel

Cada módulo possui um botão **⬇ Excel** que gera arquivos `.xlsx` formatados com:
- Cabeçalho estilizado
- Linhas alternadas
- Linha de totais
- Coluna de valores em formato moeda brasileira

---

## Integração com Google Drive *(opcional)*

Para habilitar o backup automático no Google Drive:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto e ative a **Google Drive API**
3. Gere credenciais OAuth 2.0 e baixe o `client_secrets.json`
4. Coloque o arquivo na raiz do projeto
5. No app: **Backup → Configurar Google Drive**

> ⚠️ Nunca versione o `client_secrets.json` ou `google_token.json` — eles estão no `.gitignore`.

---

## Licença

Uso pessoal. Todos os direitos reservados.
