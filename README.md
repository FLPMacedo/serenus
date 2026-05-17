# Serenus — Finanças Pessoais

> Aplicativo desktop de finanças pessoais, desenvolvido em Python com CustomTkinter e SQLite.  
> Todos os dados ficam salvos localmente — nenhuma informação é enviada para a internet.

**Versão atual: 2.0**

---

## O que é o Serenus?

O **Serenus** é um software de finanças pessoais para Windows, pensado para quem quer
controlar receitas, despesas, dívidas, investimentos, vendas e metas em um único lugar —
sem depender de planilhas ou aplicativos online.

Na primeira vez que abre, o app pede seu nome e configura o perfil.
A partir daí, tudo fica salvo localmente no seu computador, de forma segura e privada.

### Principais funcionalidades

| Módulo | O que faz |
|--------|-----------|
| 💰 Minhas Receitas | Cadastro de salário, renda extra, 13º, férias e bônus |
| 💸 Contas a Pagar | Registro de despesas mensais, parcelamento no cartão e recorrências |
| 💳 Cartões | Faturas, compras parceladas, limite disponível e **importação de fatura CSV/XLSX** |
| 🛒 Vendas | Venda de produtos/serviços à vista ou a prazo, contas a receber |
| 📉 Dívidas | Projeção mês a mês da evolução de empréstimos e financiamentos |
| 📋 Plano de Contas | Categorização personalizada de despesas |
| 📊 Visão Financeira | Projeção de saldo para os próximos 5 anos |
| 🔄 Fluxo de Caixa | Resumo de receitas × despesas com extrato detalhado |
| 📈 Investimentos | Carteira de renda variável, fixa e fundos com cálculo de IR |
| 🎯 Metas | Acompanhamento de objetivos financeiros com barra de progresso |
| 🔔 Alertas | Notificações automáticas de contas vencidas, faturas e recebíveis |
| 💾 Backup | Backup e restauração local dos dados |

### Destaques

- **100% local** — banco de dados SQLite no seu computador, sem nuvem obrigatória
- **Sem assinatura** — instala uma vez e usa para sempre
- **Dados de demonstração** — 8 perfis prontos para explorar o sistema sem cadastrar nada
- **Exportação Excel** — cada módulo gera `.xlsx` formatado com totais e cores
- **Importação de fatura** — importe extratos CSV/XLSX do banco com detecção automática de parcelas
- **Vendas integradas** — receitas de vendas entram automaticamente no Fluxo de Caixa
- **Backup Google Drive** *(opcional)* — integração configurável para salvar na nuvem

---

## Instalador disponível

O executável e o instalador para Windows **não estão neste repositório**
(são arquivos grandes gerados a partir deste código-fonte).

**Se tiver interesse em obter o instalador compilado, entre em contato.**

---

## Requisitos para rodar pelo código-fonte

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

Na primeira execução o app pergunta seu nome e cria o banco `serenus.db`
automaticamente em `%APPDATA%\Serenus\` (Windows).

---

## Dados de demonstração

Para explorar o sistema sem precisar cadastrar dados manualmente:

1. Abra o app → **Configurações → Dados de demonstração**
2. Selecione um dos 8 perfis disponíveis
3. Clique em **Carregar perfil**

---

## Estrutura do projeto

```
serenus/
│
├── main.py                   # Entry point
├── database.py               # Conexão SQLite, DDL e seed inicial
├── config.py                 # Constantes, temas e formatadores globais
├── _paths.py                 # Resolução de caminhos (dev ↔ bundle PyInstaller)
├── demo_manager.py           # 8 perfis de dados de demonstração
├── backup_manager.py         # Lógica de backup local
├── google_drive.py           # Integração opcional com Google Drive
├── requirements.txt          # Dependências Python
│
├── views/                    # Interface gráfica (CustomTkinter)
│   ├── main_window.py        # Janela principal + roteamento de telas
│   ├── setup_view.py         # Wizard de configuração inicial (primeiro acesso)
│   ├── contas_pagar/         # Módulo Contas a Pagar
│   ├── receitas/             # Módulo Minhas Receitas
│   ├── cartoes/              # Módulo Cartões (+ importação de fatura)
│   ├── vendas/               # Módulo Vendas e Serviços
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
├── instalador/               # Script Inno Setup para geração do instalador
├── docs/                     # Documentação
│   ├── MANUAL_USUARIO.md
│   ├── DOCUMENTACAO_TECNICA.md
│   └── BUILD.md              # Como gerar o executável e instalador
│
└── tests/                    # Testes automatizados (pytest)
```

---

## Rodando os testes

```bash
pytest tests/ -v
```

Todos os testes usam banco em memória — nenhum dado real é afetado.

**Cobertura atual: 333 testes — 333/333 passando.**

---

## Como gerar o instalador

Consulte [`docs/BUILD.md`](docs/BUILD.md) para o passo a passo completo usando
PyInstaller + Inno Setup.

---

## Novidades da v2.0

- **Importação de fatura CSV/XLSX** — importe extratos do banco diretamente no módulo Cartões.
  O sistema detecta parcelas (ex: "7/12"), cria o histórico de parcelas já pagas e gera
  automaticamente as próximas pendentes e contas a pagar correspondentes.
- **Módulo Vendas** — registre vendas de produtos e serviços à vista ou a prazo.
  Vendas à vista entram no Fluxo de Caixa imediatamente; vendas a prazo entram conforme
  os recebimentos são quitados.
- **Alertas de recebíveis** — notificações para contas a receber vencidas ou vencendo.
- **Template XLSX** — baixe o modelo de planilha para preenchimento e importação de fatura.

---

## Licença

Uso pessoal. Todos os direitos reservados.
