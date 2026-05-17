# Serenus — Playbook Prático

> Guia hands-on para começar a usar o Serenus do zero e dominar todos os módulos.
> Versão 2.1.0 · Português BR

---

## Como ler este playbook

Cada capítulo é um **fluxo prático completo** — começa com um objetivo, mostra o caminho clique a clique e termina com dicas para evitar armadilhas comuns.

- 🎯 **Objetivo** — o que você vai conseguir ao final do capítulo
- 👣 **Passo a passo** — sequência exata de cliques
- 💡 **Dica** — atalhos, opções escondidas e boas práticas
- ⚠️ **Cuidado** — armadilhas comuns que custam tempo

A maioria dos capítulos é independente — você pode pular direto para o módulo que precisa. Mas se é a primeira vez no Serenus, leia em ordem os capítulos **1 a 3**.

---

## Sumário

1. [Primeiro acesso e instalação](#1-primeiro-acesso-e-instalação)
2. [Explorando com Modo Demo](#2-explorando-com-modo-demo)
3. [Cadastrando suas receitas](#3-cadastrando-suas-receitas)
4. [Lançando despesas](#4-lançando-despesas)
5. [Cartões de crédito](#5-cartões-de-crédito)
6. [Importando faturas CSV/XLSX](#6-importando-faturas-csvxlsx)
7. [Vendas e contas a receber](#7-vendas-e-contas-a-receber)
8. [Acompanhando o Fluxo de Caixa](#8-acompanhando-o-fluxo-de-caixa)
9. [Planejando 5 anos à frente — Visão Financeira](#9-planejando-5-anos-à-frente--visão-financeira)
10. [Personalizando o Plano de Contas](#10-personalizando-o-plano-de-contas)
11. [Gerenciando dívidas](#11-gerenciando-dívidas)
12. [Carteira de investimentos](#12-carteira-de-investimentos)
13. [Definindo metas financeiras](#13-definindo-metas-financeiras)
14. [Backup local e Google Drive](#14-backup-local-e-google-drive)
15. [Configurações e personalização](#15-configurações-e-personalização)
16. [Dicas avançadas e atalhos](#16-dicas-avançadas-e-atalhos)

---

## 1. Primeiro acesso e instalação

🎯 **Objetivo:** Instalar o Serenus, criar seu perfil e ver a tela inicial pela primeira vez.

### 1.1 Instalação

1. Baixe o `SerenusSetup.exe` distribuído pelo vendedor.
2. Execute o instalador — o assistente em português guia toda a instalação.
3. Marque (opcional) "Criar ícone na Área de Trabalho" e "Iniciar com o Windows".
4. Clique em **Instalar** e depois **Concluir**.

O Serenus será instalado em `%ProgramFiles%\Serenus\` (ou pasta do usuário se você não for administrador). Os dados do app ficam em `%APPDATA%\Serenus\` — separados do executável, preservados em atualizações futuras.

### 1.2 Setup inicial

Na primeira execução o app pede:

1. **Nome de exibição** — aparece no canto da sidebar (pode ser apelido).
2. **Renda mensal estimada** — pode deixar zerado e cadastrar suas fontes depois.
3. **Tema** — claro ou escuro (pode trocar depois em Configurações).

Clique em **Começar** e o Serenus abre direto no Dashboard.

![Tela inicial com cards de receita, parcelas, saldo livre e gráfico de projeção](screenshots/01_inicio_dashboard.png)

💡 **Dica:** Note o banner azul-claro no topo da tela. É o **Modo Ajuda** — explica o que se faz em cada tela. Quando você já estiver familiarizado, desligue em **Configurações → 💡 Dicas de uso**.

⚠️ **Cuidado:** Não há login por padrão. Se o computador é compartilhado, ative uma senha em **Configurações → 🔒 Senha de acesso** antes de cadastrar dados sensíveis.

---

## 2. Explorando com Modo Demo

🎯 **Objetivo:** Conhecer todos os módulos do Serenus sem digitar nada — usando perfis de demonstração com dados pré-carregados.

### 2.1 Quando usar

- Quer **testar o app antes de cadastrar dados reais**.
- Quer **mostrar para alguém** como o sistema funciona.
- Está **aprendendo um módulo novo** (ex.: Investimentos) e não quer mexer no banco real.

### 2.2 Como ativar

1. Vá em **⚙️ Configurações** na sidebar.
2. Role até a seção **Dados de Demonstração**.
3. Escolha um perfil no dropdown — há 8 perfis prontos:
   - **Padrão** — classe média, sem investimentos
   - **Apertado** — renda baixa com muitos cartões
   - **Moderado entrando em dívidas** — uso recente do cartão
   - **Moderado saindo das dívidas** — quitação em andamento
   - **No verde** — sobra mensal de ~R$500
   - **Primeiro Passo** — começando a investir
   - **Em Ritmo** — investidor há 3 anos
   - **Patrimônio Crescendo** — carteira consolidada (FIIs, ações, CDBs)
4. Clique em **Carregar perfil**.

O Serenus **apaga os dados anteriores** e popula com o perfil escolhido. Navegue pelos módulos — tudo já vem preenchido com histórico realista de até 60 meses.

💡 **Dica:** Para o **Patrimônio Crescendo**, abra **📈 Investimentos** para ver uma carteira com 11 ativos e gráficos de alocação. Excelente para entender o módulo.

⚠️ **Cuidado:** Carregar um perfil demo **substitui** o banco atual. Faça **💾 Backup** antes se tiver dados reais cadastrados.

---

## 3. Cadastrando suas receitas

🎯 **Objetivo:** Registrar todas as suas fontes de renda (salário, freelas, aluguéis) para o Serenus calcular sua receita base mensal automaticamente.

![Minhas Receitas — fontes de renda ativas com valores mensais](screenshots/02_minhas_receitas.png)

### 3.1 Cadastrando uma fonte CLT (salário)

1. Sidebar → **💰 Minhas Receitas**.
2. Aba **Fontes de Renda** → clique em **+ Nova fonte**.
3. Preencha:
   - **Nome:** "Salário Empresa X"
   - **Tipo:** CLT
   - **Valor mensal líquido:** R$ 5.000,00 (use a máscara — digite só números)
   - **Dia do pagamento:** 5
4. Marque **FGTS Aniversário** se você usa essa modalidade.
5. Clique em **Salvar**.

O Serenus cria automaticamente **2 receitas especiais** vinculadas:
- 13º Salário em dezembro (valor = salário)
- Férias + 1/3 em junho (valor = salário × 4/3)

Você verá essas entradas pré-criadas na aba **Receitas Especiais** — pode editar mês e valor se preferir outro período.

### 3.2 Cadastrando renda variável (freela / aluguel)

1. Mesma tela → **+ Nova fonte**.
2. **Tipo:** Freela / Serviço (ou Aluguel recebido)
3. **Valor mensal médio:** valor médio dos últimos 3 meses
4. **Periodicidade:** Mensal | Bimestral | Anual
5. Salvar.

💡 **Dica:** Se sua renda freela varia muito, cadastre um valor conservador. As **vendas reais** (módulo Vendas) também entram automaticamente como receita do mês, então você não perde o valor cheio.

### 3.3 Receitas especiais avulsas (bônus, 14º, restituição)

1. Aba **Receitas Especiais** → **+ Nova receita**.
2. Nome, mês (0-Jan a 11-Dez), valor.
3. Marque **Recorrente anual** se acontece todo ano.

💡 **Visão Mensal:** A terceira aba mostra o total previsto do mês selecionado, incluindo **vendas já realizadas**. Use os botões ◀ ▶ para navegar entre meses.

⚠️ **Cuidado:** O campo `mes` das receitas especiais é **0-based** internamente (0 = janeiro, 11 = dezembro). Você seleciona pelo nome do mês, sem se preocupar com isso.

---

## 4. Lançando despesas

🎯 **Objetivo:** Registrar contas a pagar do mês, criar despesas recorrentes e parcelar no cartão de crédito.

![Contas a Pagar — listagem mensal com filtros e total](screenshots/03_contas_a_pagar.png)

### 4.1 Lançando uma despesa simples

1. Sidebar → **💸 Contas a Pagar**.
2. **+ Nova despesa**.
3. Preencha:
   - **Descrição:** "Internet abril"
   - **Conta (plano):** Internet (escolha da lista)
   - **Valor:** 149,90 (digite só os dígitos, a máscara formata)
   - **Vencimento:** DD/MM/AAAA — máscara automática
   - **Status:** Pendente (padrão)
4. Salvar.

A despesa aparece na lista do mês corrente. Quando pagar, clique no botão **✓ Pago** ao lado — o sistema grava a data de pagamento e move pro extrato como saída efetiva.

### 4.2 Despesa recorrente

1. Mesma tela → **+ Nova despesa**.
2. Marque **Recorrente mensal**.
3. Indique quantos meses replicar (até 12 — padrão do Plano de Contas).
4. Salvar.

O Serenus cria **uma despesa idêntica em cada um dos próximos N meses**, com a mesma conta, valor e dia de vencimento.

💡 **Reajuste em lote:** Ao editar uma despesa recorrente, o Serenus pergunta:
- **Apenas esta** — altera só o lançamento atual.
- **Esta e as próximas** — altera todos os pendentes futuros do mesmo plano.

Use "Esta e as próximas" quando o aluguel sobe, o plano de saúde reajusta, etc.

### 4.3 Pagando no cartão de crédito (parcelado)

1. Em **+ Nova despesa**, marque **Pagar com cartão de crédito**.
2. Selecione o **cartão** no dropdown.
3. Escolha:
   - **À vista** — uma única parcela.
   - **Parcelado** — informe o número de parcelas (1 a 24) e a fatura inicial.
4. Veja o **preview**: "12x de R$ 100,00 — começa em Mai/2026, termina em Abr/2027".
5. Salvar.

O Serenus cria automaticamente:
- O registro em `compras_cartao` (controle de fatura)
- As N parcelas em `parcelas_cartao` (cada uma com mês de referência)
- N entradas em `contas_pagar` (uma por mês, para o Fluxo de Caixa)

⚠️ **Cuidado:** Se você **excluir** uma parcela individualmente em Contas a Pagar, a parcela do cartão correspondente fica órfã. Para cancelar uma compra inteira, use o módulo **💳 Cartões → Ver faturas** e exclua a compra de lá.

### 4.4 Filtrando e buscando

- **Status:** Todos | Pendente | Pago | Cancelado
- **Tipo:** Todos | Fixo | Variável
- **Busca:** campo de texto no topo (procura em descrição e plano)

A barra superior tem navegação **◀ Mês ▶** para olhar meses anteriores ou futuros.

---

## 5. Cartões de crédito

🎯 **Objetivo:** Cadastrar seus cartões, lançar compras parceladas e gerenciar a fatura mensal.

![Cartões — grade visual com Itaú Visa Platinum e Nubank Gold](screenshots/05_cartoes.png)

### 5.1 Cadastrando um cartão

1. Sidebar → **💳 Cartões** → **+ Novo Cartão**.
2. Preencha:
   - **Nome:** "Itaú Platinum" (apelido livre)
   - **Banco:** Itaú (a cor de fundo do card muda automaticamente)
   - **Bandeira:** Visa (logo da bandeira aparece no preview)
   - **Últimos 4 dígitos:** 7891 (opcional, fica mascarado no card)
   - **Limite total:** 12.000
   - **Dia de fechamento:** 1
   - **Dia de vencimento:** 15
3. **Preview ao vivo** mostra como o card vai aparecer na grade. Ajuste cores se quiser.
4. Salvar.

💡 **Bandeira customizada:** No dropdown de bandeira, escolha **+ Nova bandeira...** para cadastrar bandeiras regionais que não estão na lista padrão (ex.: Banescard, Cabal).

### 5.2 Lançando uma compra no cartão

Na grade de cartões, clique em **+ Lançar** no cartão desejado.

1. **Descrição:** "Smartphone"
2. **Estabelecimento:** "Magazine X"
3. **Categoria:** opcional (ex.: Pessoal, Eletrônicos)
4. **Valor total:** 1.200,00
5. **Número de parcelas:** 3
6. **Mês de referência inicial:** Maio/2026 (padrão = mês atual)
7. Veja o preview: "3× de R$ 400,00 · Mai/2026 → Jul/2026"
8. **Salvar**.

O sistema:
- Debita o `limite_disponivel` em R$ 1.200,00.
- Cria 3 parcelas (`parcelas_cartao`) em Mai, Jun, Jul/2026.
- Cria 3 entradas em `contas_pagar` (uma por mês).
- Atualiza a **dívida do cartão** (visível em **📉 Gerenc. Dívidas**).

⚠️ **Cuidado:** A última parcela pode ter centavos diferentes (absorve arredondamento). Ex.: R$ 100/3 = R$ 33,33 + R$ 33,33 + **R$ 33,34**.

### 5.3 Ver faturas mensais

Clique em **Ver faturas** no cartão.

- Navegue mês a mês com **◀ ▶**.
- Cada compra aparece com sua parcela atual (ex.: "3/12 — Smartphone").
- Total pendente do mês no rodapé.
- Botão **✓ Marcar todas pagas** — útil quando pagou a fatura inteira no boleto.

### 5.4 Desativando um cartão

Use o botão **Desativar** no cartão. Ele:
- Some da grade principal (a menos que você marque **Mostrar inativos**).
- Para de gerar alertas de fatura.
- **Preserva o histórico** — todas as compras antigas continuam visíveis e contabilizadas no extrato.

---

## 6. Importando faturas CSV/XLSX

🎯 **Objetivo:** Importar a fatura do banco em vez de digitar cada compra manualmente.

### 6.1 Quando usar

Quando seu banco oferece **download da fatura** em CSV ou Excel (Nubank, Itaú, C6 etc.). Em vez de digitar 30 lançamentos, você importa em segundos.

### 6.2 Preparando o arquivo

O arquivo precisa ter 5 colunas (a ordem não importa, mas os **nomes** devem bater):

| descricao         | estabelecimento | categoria | parcela | valor   |
|-------------------|-----------------|-----------|---------|---------|
| Netflix           | Netflix         | Lazer     | 1/1     | 39,90   |
| Smartphone        | Magazine X      | Pessoal   | 3/12    | 200,00  |
| Mercado           | Mercado Bom     | Aliment.  | 1/1     | 1.234,56|

Detalhes:
- **descricao** (obrigatório) — nome da compra
- **valor** (obrigatório, > 0) — aceita "R$ 100,00", "1.234,56", "199.90"
- **parcela** (opcional) — formatos "N/M", "N de M" ou vazio (=1/1)
- **estabelecimento** e **categoria** — descritivos

💡 **Template pronto:** No modal de importação clique em **⬇ Template XLSX** para baixar um arquivo já formatado.

### 6.3 Importando

1. Sidebar → **💳 Cartões** → botão **⬆ Importar Fatura** no topo.
2. Escolha o **cartão** no dropdown.
3. Selecione o **mês da fatura** (ex.: "Maio 2026" — o mês das parcelas que estão sendo cobradas).
4. Marque (ou não) **Criar histórico das parcelas já pagas**.
5. Clique em **📂 Abrir arquivo** e selecione o CSV/XLSX.
6. O Serenus mostra uma **pré-visualização** de até 5 linhas com erros (se houver).
7. Corrija problemas no arquivo se necessário e reabra.
8. Clique em **⬆ Importar**.

Ao final aparece: "X item(ns) importado(s) · Y duplicata(s) ignorada(s) · Z erro(s)".

### 6.4 Como funciona a detecção de parcelas

Para uma compra "Smartphone 7/12" importada no mês de **Mai/2026**:

- **Mês inicial calculado:** Nov/2025 (Mai/2026 − 6 meses)
- **Parcelas 1 a 6 (Nov/25 a Abr/26):** criadas como **pago** (se você marcou "criar histórico")
- **Parcela 7 (Mai/26):** criada como **pendente** (a fatura atual)
- **Parcelas 8 a 12 (Jun/26 a Out/26):** criadas como **pendente**

Só as parcelas pendentes geram entradas em `contas_pagar`.

### 6.5 Deduplicação

Importar duas vezes o mesmo arquivo? Tudo bem — o Serenus identifica duplicatas pela chave `(cartão, descrição, mês da parcela, número da parcela)` e ignora.

| Cenário | Resultado |
|---|---|
| Importar a mesma fatura 2 vezes | **Tudo ignorado** (duplicatas) |
| Importar fatura de Maio e depois Junho com mesma compra Smartphone (8/12) | **Adiciona só a parcela 8** |
| Compra teve mais parcelas que o esperado (era 6/12, virou 1/9) | **Adiciona delta** (parcelas 7, 8, 9) |

⚠️ **Cuidado:** Se a descrição tiver typos diferentes entre faturas ("Netflix" vs "NETFLIX *"), o Serenus trata como compras separadas. Padronize antes de importar.

---

## 7. Vendas e contas a receber

🎯 **Objetivo:** Registrar vendas de produtos/serviços, controlar contas a receber e ver o dinheiro entrar no Fluxo de Caixa.

![Vendas — vendas à vista pagas com total do mês](screenshots/04_vendas.png)

### 7.1 Cadastrando produtos e serviços

Antes de vender, cadastre o que você vende:

1. Sidebar → **🛒 Vendas** → botão **📦 Produtos**.
2. **+ Novo produto**.
3. Preencha:
   - **Nome:** "Consultoria 1h"
   - **Tipo:** Serviço (ou Produto)
   - **Preço sugerido:** 250,00
   - **Descrição:** detalhes opcionais
4. Salvar.

Você não precisa cadastrar produtos primeiro — pode usar descrições livres na hora da venda — mas cadastrar facilita reuso.

### 7.2 Venda à vista (dinheiro entra hoje)

1. Em **🛒 Vendas** → **+ Nova venda**.
2. **Cliente / Descrição:** "Consultoria — João Silva"
3. **Data:** padrão = hoje
4. **Tipo de pagamento:** À vista
5. Em **Itens**, clique em **+ Adicionar item**:
   - Escolha o produto no dropdown (ou descrição livre)
   - Quantidade, preço unitário (preenche automático)
6. Repita para mais itens.
7. **Desconto** (opcional): R$ 50,00
8. Confira o **Total líquido**.
9. Salvar.

O Serenus cria:
- Venda com status **paga**
- Itens vinculados
- **Crédito no Fluxo de Caixa** na data da venda

A venda já aparece no card "Receita base/mês" do Dashboard.

### 7.3 Venda a prazo (gera recebíveis)

1. **+ Nova venda** → **Tipo:** A prazo
2. **Número de parcelas:** 3
3. **Data da primeira parcela:** ex. 10/06/2026
4. Itens normalmente.
5. Salvar.

O Serenus cria:
- Venda com status **pendente**
- N entradas em **contas_a_receber** (uma por parcela)
- **NÃO** cria crédito imediato — dinheiro só entra quando você marcar como recebido.

### 7.4 Marcando recebimento

Quando o cliente pagar uma parcela:

1. Em **🛒 Vendas** → aba **A Receber**.
2. Encontre a parcela na lista.
3. Clique em **✓ Receber**.
4. No modal, confirme a data de recebimento.
5. Salvar.

O Serenus:
- Marca a parcela como **recebido**
- Atualiza o status da venda:
  - Última parcela recebida → venda vira **paga**
  - Parcial → venda vira **parcial**
- Cria crédito no Fluxo de Caixa na data informada.

⚠️ **Cuidado:** Tentar marcar recebida uma parcela já **cancelada** (após `Cancelar venda`) é ignorado pelo sistema. Para "voltar" uma venda cancelada, refaça o cadastro.

### 7.5 Alertas de recebíveis

A sidebar mostra **🔔 Alertas (N)** quando há:
- Recebíveis **vencidos** (vermelho — urgência alta)
- Recebíveis **vencendo em 7 dias** (laranja — urgência média)

Clique no botão para ver a lista completa.

---

## 8. Acompanhando o Fluxo de Caixa

🎯 **Objetivo:** Ver o extrato consolidado de todas as entradas e saídas, com gráfico e filtros.

![Fluxo de Caixa — extrato detalhado mês a mês](screenshots/09_fluxo_de_caixa_extrato.png)

### 8.1 O que entra no extrato

| Origem | Quando aparece |
|---|---|
| 💰 Fontes de receita | Todo mês (com base em `dia_pagamento`) |
| 🎁 Receitas especiais | No mês cadastrado (13º, férias, etc.) |
| 🛒 Vendas à vista | No `data_venda` (status = paga) |
| 🛒 Recebíveis quitados | No `data_recebimento` |
| 📈 Rendimentos de investimentos | No mês da movimentação (dividendos, juros, JCP) |
| 💸 Contas a pagar | No `data_vencimento` (todas, exceto canceladas) |

### 8.2 Navegando

1. Sidebar → **🔄 Fluxo de Caixa**.
2. Use **◀ ▶** para navegar entre meses.
3. **Busca:** filtro por descrição ou categoria.
4. **Radio:** Todos | Receitas | Despesas.
5. **Saldo acumulado** na coluna mais à direita — ajuda a ver quando o caixa fica negativo.

### 8.3 Exportando para Excel

Botão **⬇ Excel** no topo:
- Arquivo: `extrato_2026_05.xlsx`
- 1 aba com extrato completo
- Cores: créditos em verde, débitos em vermelho
- Linha de totais no final

💡 **Dica:** O extrato exportado tem mesmas regras de cálculo da tela — bate exatamente com o saldo mostrado. Use para conciliar com o extrato do banco real.

---

## 9. Planejando 5 anos à frente — Visão Financeira

🎯 **Objetivo:** Projetar receitas, despesas e saldo dos próximos 60 meses.

![Visão Financeira — planilha 5 anos com cores por saldo](screenshots/08_visao_financeira.png)

### 9.1 Estrutura da planilha

| Coluna | O que mostra |
|---|---|
| Mês | Mai/2026 … Abr/2031 |
| Receitas | Soma de fontes + especiais + vendas (real ou previsto) |
| Desp. Fixas | Contas com `tipo_custo=fixo` |
| Desp. Var. | Contas com `tipo_custo=variavel` |
| Parc. Cartão | Soma de `parcelas_cartao` do mês |
| Dívidas | Parcelas mensais de empréstimos/financiamentos |
| Total Saídas | Soma de todas as despesas |
| Saldo | Receitas − Total Saídas |

### 9.2 Cores das linhas

- 🟦 **Azul claro** — mês atual (você está aqui)
- 🟢 **Verde** — saldo positivo > R$ 500 (folga)
- 🟡 **Amarelo** — saldo entre R$ 0 e R$ 500 (apertado)
- 🔴 **Vermelho** — saldo negativo (déficit projetado)

### 9.3 Expandindo categorias

Clique em qualquer categoria do cabeçalho (ex.: "Desp. Fixas") para ver os **sub-itens que a compõem em cada mês**. Útil para identificar "qual conta está pesando mais em julho?".

### 9.4 Cenários

Use o seletor **Horizonte: 6m | 1 ano | 1,5 anos | 2 anos | 3 anos | 5 anos** no Dashboard inicial. A Visão Financeira sempre projeta 60 meses, mas você pode comparar com cenários menores.

⚠️ **Cuidado:** A projeção de fixas futuras usa o **último mês com lançamentos como base**. Se você só cadastrou aluguel para mai/26 a dez/26, o sistema projeta aluguel para 2027+ baseado em dez/26. Cadastre fixas com calma para refletir reajustes esperados.

---

## 10. Personalizando o Plano de Contas

🎯 **Objetivo:** Adaptar as categorias de despesas ao seu estilo de vida.

![Plano de Contas — categorias customizáveis](screenshots/07_plano_de_contas.png)

### 10.1 Categorias padrão

O Serenus já vem com **34 contas padrão** organizadas em:
- Moradia, Transporte, Alimentação, Saúde, Educação
- Serviços, Lazer, Impostos, Pessoal
- Cartão de Crédito, Outros

### 10.2 Criando categoria personalizada

1. Sidebar → **📋 Plano de Contas** → **+ Nova conta**.
2. **Nome:** "Coleção de vinis"
3. **Tipo:** Variável (gasta diferente todo mês) ou Fixo (mesmo valor)
4. **Categoria:** Lazer (ou crie novo grupo)
5. Salvar.

A conta nova já fica disponível no dropdown ao **lançar uma despesa**.

### 10.3 Excluindo uma conta

Botão **🗑** ao lado da conta.

- **Conta sem lançamentos** → exclui direto.
- **Conta com lançamentos** → o sistema bloqueia e mostra a quantidade.
- **Conta padrão** → também pode ser excluída se quiser limpar.

### 10.4 Restaurando padrões

Após excluir várias contas padrão, o botão **↩ Restaurar padrões** no topo recria **só as faltantes** (não duplica as que ainda existem).

💡 **Dica:** Você pode **desativar** uma conta em vez de excluir (botão **Desativar**). Ela some do dropdown mas mantém o histórico — útil para serviços que você cancelou mas quer manter o histórico.

---

## 11. Gerenciando dívidas

🎯 **Objetivo:** Centralizar empréstimos, financiamentos e parcelados grandes, e ver a projeção de quitação.

![Gerenciamento de Dívidas — dashboard com evolução do saldo e parcelas mensais](screenshots/06_gerenciamento_dividas.png)

### 11.1 O que cadastrar aqui

- 🏦 Empréstimo pessoal
- 🏠 Financiamento imobiliário
- 🚗 Financiamento de veículo
- 💳 Cartão de crédito *(criado automaticamente quando você lança compras)*
- Outros parcelamentos longos

### 11.2 Cadastrando uma dívida

1. Sidebar → **📉 Gerenc. Dívidas** → aba **Minhas Dívidas** → **+ Nova dívida**.
2. Preencha:
   - **Nome:** "Financ. apê alugado (BB)"
   - **Tipo:** Financiamento
   - **Saldo atual:** R$ 160.800,00
   - **Parcela mensal:** R$ 1.350,00
   - **Total de parcelas:** 240
   - **Parcelas pagas:** 60
   - **Dia de vencimento:** 10
   - **Taxa de juros (%a.a.):** 8,5 (informativo)
3. Salvar.

### 11.3 Dashboard de dívidas

A aba **Dashboard** mostra:
- **KPIs:** Total devedor · Parcela mensal · Quantidade de dívidas · Data de quitação total
- **Gráfico de evolução do saldo devedor** — visualização cair a zero ao longo do tempo
- **Barras de parcelas por mês** — cargas mensais visuais

### 11.4 Cartão como dívida

Não cadastre manualmente o cartão como dívida — **o Serenus já mantém uma dívida automática para cada cartão** com base nas parcelas pendentes. Você verá no dashboard "Cartão Itaú", "Cartão Nubank" etc.

⚠️ **Cuidado:** Se você excluir manualmente a dívida de um cartão, ela é **recriada automaticamente** na próxima atualização (lançar compra, marcar parcela paga). É proposital — mantém o saldo devedor consistente.

---

## 12. Carteira de investimentos

🎯 **Objetivo:** Acompanhar ações, FIIs, renda fixa, criptomoedas e fundos com custo médio, lucro realizado e IR estimado.

![Investimentos — carteira com 11 ativos consolidados](screenshots/10_investimentos.png)

### 12.1 Estrutura do módulo

A tela tem 4 abas:

1. **Carteira** — posição atual de cada ativo (custo médio, valor atual, L/P)
2. **Movimentações** — histórico de compras, vendas, dividendos, juros
3. **Dashboard** — gráficos de alocação por tipo, evolução do patrimônio, IR estimado
4. **Ativos / Contas** — cadastro de corretoras e ativos

### 12.2 Cadastrando uma corretora

1. Aba **Ativos / Contas** → **+ Nova conta**.
2. Preencha:
   - **Nome:** "Rico — XP Investimentos"
   - **Tipo:** Corretora
   - **Instituição:** XP Investimentos
3. Salvar.

### 12.3 Cadastrando um ativo

1. Aba **Ativos / Contas** → **+ Novo ativo**.
2. Preencha:
   - **Código:** "PETR4"
   - **Nome:** "Petrobrás PN"
   - **Tipo:** Ação (ETF, FII, CDB, Tesouro, Fundo, Cripto, Outro)
   - **Conta:** Rico — XP
   - Para renda fixa: indexador (CDI/SELIC/IPCA/Prefixado), taxa contratada, vencimento
3. Salvar.

### 12.4 Registrando uma compra

1. Aba **Movimentações** → **+ Nova movimentação**.
2. Preencha:
   - **Ativo:** PETR4
   - **Tipo:** Compra
   - **Data:** DD/MM/AAAA
   - **Quantidade:** 100
   - **Preço unitário:** 30,00
   - **Taxas:** 5,00 (corretagem + emolumentos)
   - **Valor bruto:** 3.000,00 (calculado)
   - **Valor líquido:** 3.005,00 (com taxas)
3. Marque **Registrar no financeiro** se quiser que crie uma entrada em **Contas a Pagar** (para o caixa).
4. Salvar.

O Serenus recalcula automaticamente o **custo médio** do ativo.

### 12.5 Registrando uma venda

Mesmo fluxo, mas **Tipo: Venda**. O sistema calcula:
- Lucro/prejuízo realizado = (valor de venda) − (custo médio × quantidade)
- Atualiza qtd_atual (se zera, posição fechada)

⚠️ **Não é possível vender mais do que você tem.** O sistema bloqueia overselling.

### 12.6 Dividendos e juros

**Tipo: Dividendo** (ou JCP, Juros) — não altera quantidade, mas:
- Cria crédito no Fluxo de Caixa
- Soma em "Rendimentos recebidos" no dashboard

### 12.7 IR estimado

O Dashboard mostra um card **IR Estimado** com:
- **Ações/ETFs/Crypto:** 15% sobre lucro
- **FII:** 20% sobre lucro
- **Renda Fixa:** alíquota regressiva (22,5% → 15% conforme prazo)

Útil para reservar dinheiro pro DARF mensal.

💡 **Cotação automática:** Botão **🌐 Buscar API** atualiza preços via brapi.dev (sem chave, sem cadastro). Funciona para ativos brasileiros (BOVESPA/CRIPTO). Para outros, edite manualmente o "valor atual" no ativo.

---

## 13. Definindo metas financeiras

🎯 **Objetivo:** Acompanhar objetivos (viagem, reserva, casa) com barra de progresso e cálculo de quanto poupar por mês.

![Metas Financeiras — 4 metas com barras de progresso](screenshots/11_metas.png)

### 13.1 Criando uma meta

1. Sidebar → **🎯 Metas** → **+ Nova meta**.
2. Preencha:
   - **Nome:** "Viagem Europa (família)"
   - **Valor alvo:** R$ 60.000,00
   - **Valor atual (acumulado):** R$ 28.800,00
   - **Prazo:** DD/MM/AAAA (opcional)
   - **Descrição:** opcional
3. Salvar.

O Serenus calcula:
- **Progresso:** 48%
- **Economia mensal necessária:** R$ 2.578,51/mês para atingir no prazo
- **Dias restantes:** 363 dias

### 13.2 Depositando

Quando você poupar algo:

1. Clique em **💰 Depositar** na meta.
2. Informe o valor (ex.: R$ 1.500).
3. Salvar.

O `valor_atual` é atualizado. Se chegou a 100%, a meta fica **verde com ✓**.

### 13.3 Exportando para Excel

Botão **⬇ Excel** no topo da tela.

⚠️ **Cuidado:** Metas no Serenus são **rastreadores manuais** — depósitos não são automaticamente debitados do Fluxo de Caixa. Se você quer que o depósito vire saída real, lance manualmente em **💸 Contas a Pagar** com plano "Reserva / Poupança".

---

## 14. Backup local e Google Drive

🎯 **Objetivo:** Garantir que seus dados não se percam se o computador falhar.

![Backup — botões manuais e configuração do Google Drive](screenshots/12_backup.png)

### 14.1 Backup local manual

1. Sidebar → **💾 Backup** → **Criar backup agora**.
2. Escolha a pasta de destino (padrão: `%APPDATA%\Serenus\backups\`).
3. O arquivo gerado é `serenus_AAAA-MM-DD_HHMMSS.db`.

### 14.2 Backup automático

A cada inicialização do Serenus, o sistema checa se um backup automático é necessário:
- **Frequência:** semanal por padrão (configurável)
- **Retenção:** mantém os 10 backups mais recentes

Tudo roda em background — não bloqueia a abertura do app.

### 14.3 Restaurando um backup

1. **Backup** → **Restaurar backup**.
2. Selecione o arquivo `.db`.
3. Confirme — o backup **substitui o banco atual**.

⚠️ **Recomendado:** Faça um backup **antes** de restaurar — caso queira reverter.

### 14.4 Integração com Google Drive

1. **Backup** → **Conectar com Google Drive**.
2. Autorize no navegador (OAuth padrão).
3. Cole o código gerado.
4. Pronto — cada backup local é enviado também para uma pasta `Serenus/` no seu Drive.

💡 **Dica:** Use Google Drive como cópia secundária — não como única. Se sua conta Google for comprometida, você ainda tem o `.db` local.

---

## 15. Configurações e personalização

🎯 **Objetivo:** Adaptar o Serenus ao seu gosto e proteger seus dados.

![Configurações — perfil, modo ajuda, senha, demo e zerar](screenshots/13_configuracoes.png)

### 15.1 Perfil

- **Nome de exibição:** aparece na sidebar.
- **Tema:** Claro ou Escuro (atalho: `/` na sidebar).

### 15.2 Modo ajuda

A nova opção **💡 Dicas de uso** liga/desliga os banners de ajuda no topo de cada tela e os tooltips ao passar o mouse em botões.

- **Ligado** (padrão para novos usuários): aparecem banners explicativos em todas as telas.
- **Desligado:** UI fica mais limpa.

As mudanças se aplicam ao **trocar de tela** (a tela atual mantém o estado).

### 15.3 Senha de acesso

1. **🔒 Senha de acesso** → **Definir senha**.
2. Digite e confirme uma senha numérica (mínimo 4 dígitos).
3. Salvar.

Da próxima vez que abrir o Serenus, será pedida a senha. Para **remover**, mesma seção → **Remover senha**.

⚠️ **Cuidado:** Senha esquecida = sem acesso. O Serenus não tem "esqueci minha senha" — recupere pelo backup mais recente.

### 15.4 Dados de demonstração

Já coberto no [Capítulo 2](#2-explorando-com-modo-demo).

### 15.5 Zerar sistema

Botão **🗑 Zerar sistema** — apaga **todos** os dados financeiros mas mantém:
- Seu nome de usuário
- Tema escolhido
- Configurações de senha

Use para começar do zero sem reinstalar o app.

---

## 16. Dicas avançadas e atalhos

### 16.1 Atalhos de teclado

| Atalho | Onde | O que faz |
|---|---|---|
| `Esc` | Qualquer modal | Fecha o modal |
| `Tab` | Formulários | Pula para o próximo campo |
| `Enter` | Formulários | Submete / salva |
| `/` | Sidebar | Alterna tema claro/escuro |

### 16.2 Máscaras automáticas

Os campos de **valor** aceitam dígitos contínuos:
- Digite `100` → vira `R$ 1,00`
- Digite `12345` → vira `R$ 123,45`
- Digite `1000000` → vira `R$ 10.000,00`

Os campos de **data** seguem `DD/MM/AAAA`:
- Digite `25122025` → vira `25/12/2025` automaticamente

### 16.3 Boas práticas

- **Lance despesas no mês em que ocorrem**, não no de vencimento — dá mais clareza no extrato.
- **Use o filtro de busca** em vez de scroll quando a lista cresce. Funciona em descrição e plano.
- **Backup semanal** mínimo — ainda mais se você lança muitas vendas.
- **Marque despesas como pagas** assim que pagar — alimenta o saldo livre do Dashboard com precisão.
- **Categoria correta** em cada despesa — relatórios e Visão Futura ficam muito mais úteis.

### 16.4 Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| Card "Receita base/mês" zerado | Sem fontes cadastradas | Vá em Minhas Receitas → Nova fonte |
| Cartão não aparece no dropdown ao lançar despesa | Cartão inativo | Marque "Mostrar inativos" em 💳 Cartões |
| Importação de fatura zerou valores | Coluna `valor` com formato estranho | Veja capítulo [6.2 — Preparando o arquivo](#62-preparando-o-arquivo) |
| Banner de ajuda não some | Você está na mesma tela | Mude de tela após desligar em Configurações |
| Erro "data inválida" ao salvar | Data 31/02, 31/04 etc. | Use uma data real |
| Visão Financeira mostra muito vermelho | Faltam receitas / sobram fixas | Confira fontes em Minhas Receitas |

### 16.5 Onde encontrar ajuda extra

- **Manual completo:** `docs/MANUAL_USUARIO.md`
- **Documentação técnica:** `docs/DOCUMENTACAO_TECNICA.md`
- **Build do executável:** `docs/BUILD.md`
- **GitHub:** [github.com/FLPMacedo/serenus](https://github.com/FLPMacedo/serenus)

---

*Serenus Playbook v2.1.0 — última atualização: 2026-05-17*
