# Serenus — Manual do Usuário

> Versão 1.0 · Português BR

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Primeiros Passos](#2-primeiros-passos)
3. [Minhas Receitas](#3-minhas-receitas)
4. [Contas a Pagar](#4-contas-a-pagar)
5. [Cartões de Crédito](#5-cartões-de-crédito)
6. [Gerenciamento de Dívidas](#6-gerenciamento-de-dívidas)
7. [Plano de Contas](#7-plano-de-contas)
8. [Visão Financeira (Projeção)](#8-visão-financeira-projeção)
9. [Fluxo de Caixa](#9-fluxo-de-caixa)
10. [Investimentos](#10-investimentos)
11. [Metas Financeiras](#11-metas-financeiras)
12. [Backup e Restauração](#12-backup-e-restauração)
13. [Configurações](#13-configurações)
14. [Exportação para Excel](#14-exportação-para-excel)
15. [Alertas Automáticos](#15-alertas-automáticos)
16. [Modo Demonstração](#16-modo-demonstração)

---

## 1. Visão Geral

O **Serenus** é um aplicativo de finanças pessoais instalado localmente no seu computador. Todos os dados ficam salvos em um banco de dados SQLite no próprio computador — nenhuma informação é enviada para a internet.

**Módulos disponíveis:**

| Módulo | O que faz |
|--------|-----------|
| Minhas Receitas | Cadastra fontes de renda e receitas especiais (13º, férias, bônus) |
| Contas a Pagar | Registra e acompanha despesas mensais |
| Cartões de Crédito | Controla faturas e compras parceladas |
| Gerenc. Dívidas | Projeta a evolução de empréstimos e financiamentos |
| Plano de Contas | Categoriza as despesas em grupos |
| Visão Financeira | Projeção de saldo para os próximos meses |
| Fluxo de Caixa | Resumo de receitas x despesas com gráfico |
| Investimentos | Carteira de renda variável, fixa e fundos |
| Metas | Acompanha objetivos financeiros com progresso |
| Backup | Salva e restaura todos os dados |
| Configurações | Preferências do usuário e dados de demonstração |

---

## 2. Primeiros Passos

### 2.1 Iniciando o aplicativo

Execute `main.py` com Python 3.12+. Na primeira execução o banco de dados é criado automaticamente e os dados padrão são inseridos.

### 2.2 Alternando o tema

No rodapé da barra lateral, clique em **☀️ / 🌙 Alternar tema** para mudar entre claro e escuro.

### 2.3 Dados de demonstração

Se quiser explorar o sistema com dados prontos antes de cadastrar os seus:

1. Acesse **Configurações**
2. Clique em **Dados de demonstração**
3. Escolha um dos perfis disponíveis:
   - **Padrão (Classe Média)** — renda ~R$10.300/mês, 2 cartões, 2 dívidas
   - **Apertado** — renda ~R$3.500/mês, 6 cartões, 3 dívidas
   - **Moderado entrando em dívidas** — despesas crescentes
   - **Moderado saindo das dívidas** — fase de recuperação
   - **No verde** — sobra de ~R$500/mês, 1 dívida pequena
   - **Primeiro Passo** — começa a investir, 3 ativos, 3 metas
   - **Em Ritmo** — investidor há 3 anos, 6 ativos, 4 metas
   - **Patrimônio Crescendo** — carteira consolidada, 11 ativos, 4 metas
4. Clique em **Carregar perfil** e confirme. **Atenção:** esta ação apaga todos os dados atuais.
5. Para voltar ao estado limpo, clique em **Zerar dados**.

---

## 3. Minhas Receitas

### 3.1 Fontes de receita

São as rendas recorrentes (salário, aluguel, freela etc.).

**Como cadastrar:**
1. Clique em **+ Nova fonte**
2. Preencha: Nome, Tipo (CLT, Freela, Aluguel, Dividendos, Outro), Valor mensal, Periodicidade
3. Para CLT: o sistema cria automaticamente o **13º Salário** e **Férias + 1/3** em receitas especiais
4. Clique em **Salvar**

**Como ativar/desativar:** clique no ícone de olho (👁) na linha da fonte. Fontes inativas não entram nos cálculos.

**Como editar:** clique no ícone de lápis (✏). Para excluir, use o ícone de lixeira (🗑).

### 3.2 Receitas especiais

São receitas pontuais (13º, férias, bônus, FGTS etc.).

**Como cadastrar:**
1. Na aba **Receitas Especiais**, clique em **+ Nova**
2. Preencha: Nome, Mês de recebimento, Valor, Tipo, se é recorrente a cada ano
3. Clique em **Salvar**

> **Dica:** Receitas geradas automaticamente (13º e Férias) já aparecem aqui ao cadastrar uma fonte CLT.

---

## 4. Contas a Pagar

### 4.1 Registrando uma despesa

1. Clique em **+ Nova despesa**
2. Preencha:
   - **Conta:** selecione a categoria do Plano de Contas
   - **Valor** e **Data de vencimento**
   - **Status:** Pendente ou Pago
   - **Recorrente:** marque se a despesa se repete todo mês. Informe quantos meses lançar de uma vez (1 a 60)
3. Clique em **Salvar**

### 4.2 Pagar com cartão de crédito

Ao registrar uma nova despesa, marque **Pagar com cartão de crédito**:
1. Selecione o cartão
2. Escolha o modo: **Valor total** (divide automaticamente) ou **Valor da parcela** (calcula o total)
3. Informe o número de parcelas
4. O preview mostra o detalhamento de cada parcela por mês
5. Ao salvar, a despesa é registrada em Contas a Pagar e as parcelas são lançadas no cartão

### 4.3 Navegando por meses

Use as setas **‹** e **›** no topo para navegar entre meses. O filtro de status (Todos / Pendentes / Pagos) e o filtro por tipo de custo estão na barra de filtros.

### 4.4 Marcar como pago

Clique no ícone ✅ na linha da despesa. A data de pagamento é registrada como hoje.

### 4.5 Editar recorrentes

Ao editar uma despesa recorrente, o sistema pergunta se deseja atualizar só este mês ou todos os meses futuros pendentes.

### 4.6 Busca

Use o campo de busca no topo para localizar despesas por descrição ou nome da conta. A busca funciona em todos os meses.

---

## 5. Cartões de Crédito

### 5.1 Cadastrando um cartão

1. Clique em **+ Novo cartão**
2. Preencha: nome, banco, bandeira, últimos 4 dígitos, limite, dia de vencimento e fechamento, cor de fundo/texto
3. Clique em **Salvar**

### 5.2 Registrando uma compra

1. Em um cartão, clique em **+ Nova compra**
2. Preencha: descrição, valor total, número de parcelas e mês de início
3. O sistema cria automaticamente as parcelas mensais e debita o limite

### 5.3 Visualizando faturas

Clique em **Ver fatura** no card de um cartão. A fatura mostra todas as parcelas do mês selecionado (use as setas para navegar). É possível marcar parcelas como pagas individualmente ou pagar a fatura inteira de uma vez.

### 5.4 Exportando a fatura

Na tela de fatura, clique em **⬇ Excel** para baixar a fatura do mês em planilha.

---

## 6. Gerenciamento de Dívidas

### 6.1 Cadastrando uma dívida

1. Clique em **+ Nova dívida**
2. Preencha: nome, tipo (empréstimo, financiamento, cartão), saldo atual, parcela mensal, total de parcelas, parcelas já pagas, dia de vencimento e taxa de juros
3. Clique em **Salvar**

### 6.2 Gráfico de evolução

O gráfico mostra a evolução do saldo total de todas as dívidas ativas ao longo do tempo, mês a mês, até a quitação da última dívida.

### 6.3 Exportando

Clique em **⬇ Excel** no cabeçalho para exportar a lista de dívidas e a projeção de evolução.

---

## 7. Plano de Contas

O Plano de Contas organiza suas despesas em categorias. Cada despesa em **Contas a Pagar** é vinculada a uma conta do plano.

**Contas padrão** (não podem ser excluídas, apenas inativadas):
Aluguel, Internet, Supermercado, Combustível, Saúde, Lazer, entre outras.

**Como criar uma conta personalizada:**
1. Clique em **+ Nova conta**
2. Preencha: nome, tipo de custo (fixo ou variável), categoria livre
3. Clique em **Salvar**

**Como inativar:** clique no ícone de olho (👁). Contas inativas não aparecem nas opções de nova despesa.

**Como excluir:** só é possível excluir contas sem nenhum lançamento vinculado.

---

## 8. Visão Financeira (Projeção)

### 8.1 Aba Projeção

Mostra a projeção mês a mês do saldo financeiro considerando:
- Receitas das fontes ativas (mensais, bimestrais, anuais)
- Receitas especiais (13º, férias, bônus)
- Despesas recorrentes e pendentes registradas
- Parcelas de cartão de crédito

**Horizonte:** selecione 3, 6, 12, 24 ou 36 meses.

Cores das linhas:
- 🔵 Azul — mês atual
- 🟢 Verde — saldo positivo acima de R$500
- 🟡 Amarelo — saldo positivo entre R$0 e R$499
- 🔴 Vermelho — saldo negativo

### 8.2 Aba Receitas vs Despesas

Gráfico de barras comparando receitas e despesas mês a mês no horizonte selecionado.

### 8.3 Exportando

Clique em **⬇ Excel** para baixar a projeção completa em planilha.

---

## 9. Fluxo de Caixa

O Fluxo de Caixa é a tela inicial do Serenus e mostra uma visão rápida da situação atual:

- **Cards de resumo:** saldo médio, receita média, despesa média, meses no azul/vermelho
- **Seletor de horizonte:** escolha 3, 6, 12, 24 ou 36 meses
- **Alertas automáticos:** contas vencendo em breve, saldo negativo previsto
- **Gráfico:** receitas vs despesas vs saldo ao longo do tempo
- **Tabela mensal:** detalhe mês a mês com receita, despesa, parcelas de cartão e saldo

---

## 10. Investimentos

### 10.1 Cadastrando uma conta de investimento

1. Na aba **Ativos / Contas**, clique em **+ Conta**
2. Informe nome, instituição e tipo (corretora, banco, tesouro)
3. Clique em **Salvar**

### 10.2 Cadastrando um ativo

1. Na aba **Ativos / Contas**, clique em **+ Ativo**
2. Informe código (ex: PETR4), nome, tipo (ação, FII, CDB, Tesouro, ETF, cripto) e conta vinculada
3. Para renda fixa: informe indexador, taxa e vencimento
4. Clique em **Salvar**

### 10.3 Registrando movimentações

1. Na aba **Movimentações**, clique em **+ Movimentação**
2. Selecione o ativo, tipo (compra, venda, aplicação, resgate, dividendo, juros, taxa, imposto) e data
3. Para ações: informe quantidade e preço unitário. Para renda fixa: informe apenas o valor
4. Marque **Registrar no financeiro** para que o valor entre no fluxo de caixa (recomendado para compras e aplicações)

### 10.4 Aba Carteira

Mostra todas as posições ativas com:
- Quantidade, custo médio, valor investido
- Valor atual, lucro/prejuízo, rentabilidade %
- Rendimentos recebidos (dividendos, juros)

Clique no ícone ✏ de um ativo para atualizar o valor de mercado manualmente.

### 10.5 Aba Dashboard

- **Alocação por classe:** gráfico de barra com legenda mostrando % por tipo de ativo
- **Rendimentos mensais:** barras com os rendimentos recebidos mês a mês no ano atual
- **Vencimentos próximos:** ativos de renda fixa com vencimento nos próximos 12 meses
- **IR estimado:** lucros realizados com alíquota e IR calculado por ativo

### 10.6 Exportando

- **Carteira:** botão **⬇ Excel** na aba Carteira
- **IR Estimado:** botão **⬇ Excel** no card de IR no Dashboard

---

## 11. Metas Financeiras

### 11.1 Criando uma meta

1. Clique em **+ Nova meta**
2. Preencha: nome, valor alvo, valor já guardado, prazo (opcional) e descrição
3. Clique em **Salvar**

### 11.2 Acompanhando o progresso

Cada meta exibe:
- Barra de progresso com % concluído
- Dias restantes até o prazo (ou "sem prazo")
- Valor necessário por mês para atingir a meta no prazo

### 11.3 Atualizando o valor atual

Clique no ícone ✏ e atualize o campo **Valor já guardado**.

### 11.4 Exportando

Clique em **⬇ Excel** para baixar todas as metas com progresso e prazo.

---

## 12. Backup e Restauração

### 12.1 Fazendo backup

1. Acesse **Backup**
2. Clique em **Fazer backup agora**
3. O arquivo `serenus_backup_YYYYMMDD_HHMMSS.db` é salvo na pasta `backups/` do sistema

### 12.2 Restaurando um backup

1. Acesse **Backup**
2. Selecione um arquivo de backup na lista
3. Clique em **Restaurar selecionado** e confirme
4. O sistema reinicia com os dados restaurados

> **Atenção:** a restauração substitui todos os dados atuais. Recomenda-se fazer um backup antes de restaurar.

---

## 13. Configurações

| Opção | Descrição |
|-------|-----------|
| Nome do usuário | Exibido no topo da barra lateral |
| Tema | Claro ou Escuro |
| Dados de demonstração | Carrega um perfil de exemplo |
| Zerar dados | Apaga tudo e recomeça do zero |

---

## 14. Exportação para Excel

Cada módulo com relatórios possui um botão **⬇ Excel** no cabeçalho. Ao clicar:
1. Uma janela de seleção de pasta se abre
2. Escolha onde salvar o arquivo `.xlsx`
3. O arquivo é salvo e uma confirmação aparece na tela

**Planilhas exportadas por módulo:**

| Módulo | Arquivo | Abas |
|--------|---------|------|
| Contas a Pagar | `contas_pagar_MM-YYYY.xlsx` | Despesas, Resumo |
| Dívidas | `dividas.xlsx` | Dívidas Ativas, Projeção |
| Receitas | `receitas.xlsx` | Fontes de Receita, Receitas Especiais |
| Visão Financeira | `projecao_financeira.xlsx` | Projeção N Meses |
| Metas | `metas.xlsx` | Metas |
| IR Estimado | `ir_estimado.xlsx` | IR Estimado |
| Carteira | `carteira.xlsx` | Carteira |
| Fatura | `fatura_CARTAO_MM-YYYY.xlsx` | Fatura |
| Extrato | `extrato_MM-YYYY.xlsx` | Extrato |

---

## 15. Alertas Automáticos

O sino 🔔 no rodapé da barra lateral exibe o total de alertas pendentes. Os alertas são gerados automaticamente:

| Tipo | Condição | Urgência |
|------|----------|---------|
| Conta vencida | Data de vencimento < hoje e status pendente | Alta |
| Conta vencendo | Vence nos próximos 7 dias | Média |
| Fatura do mês | Parcela de cartão no mês atual | Média |
| Renda fixa vencendo | Ativo com vencimento nos próximos 30 dias | Alta |
| Renda fixa vencida | Ativo com vencimento passado | Alta |

---

## 16. Modo Demonstração

Para resetar e experimentar um perfil diferente:

1. Vá em **Configurações → Dados de demonstração**
2. Selecione o perfil desejado
3. Clique em **Carregar perfil**

Os dados de todos os módulos são populados automaticamente: contas a pagar, receitas, cartões, dívidas, investimentos e metas — com histórico de meses anteriores e projeção futura já preenchidos.

---

*Serenus — Suas finanças, com clareza.*
