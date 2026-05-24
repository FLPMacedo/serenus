# Episódio 07 — Conciliação Bancária (CSV/OFX/PDF do banco) ⭐⭐

**Duração-alvo:** 6 min (segundo vídeo-âncora da série)
**Perfil demo:** `padrao` ou `prestador_servico`
**Arquivos:** `demos/<perfil>/extratos/extrato_nubank_*.csv` e `.ofx`

---

## 🎬 Roteiro

### Cena 1 — Hook (0:00 → 0:25)
**Tela:** mostra o app do Nubank no celular abrindo "Extrato" + opções de exportar.
**Fala:**
> "Você baixa o extrato do seu banco em CSV. Mas o que faz com ele depois?
> Abre no Excel, fica horas categorizando, sente medo de errar. O Serenus
> resolve isso com um módulo dedicado: Conciliação Bancária. Vamos importar
> 31 lançamentos de um mês inteiro do Nubank em 2 cliques."

### Cena 2 — Onde fica (0:25 → 0:50)
**Tela:** Fluxo de Caixa → aba **🏦 Conciliação Bancária** (nova!)
**Fala:**
> "Na tela de Fluxo de Caixa, agora tem 2 abas: Movimentações (a antiga)
> e Conciliação Bancária. Vamos focar na nova."

### Cena 3 — Cadastrar a conta bancária (0:50 → 1:40)
**Tela:** botão **+ Conta**
**Fala:**
> "Primeiro cadastra a conta: nome 'Nubank Principal', banco Nubank, tipo
> 'Conta Digital', saldo inicial — coloca o saldo que tá no banco no
> momento. Isso vai servir de base pro cálculo do saldo atual depois das
> importações."

### Cena 4 — Importar extrato (CSV) (1:40 → 3:30)
**Tela:** **⬆ Importar** → escolhe CSV do Nubank.

**Demonstração:**
- Seleciona arquivo: `demos/padrao/extratos/extrato_nubank_2026-05.csv`
- Preview mostra: 31 itens, período X até Y, entradas R$ Z, saídas R$ W
- Clica **⬆ Importar**

**Fala:**
> "Selecionei o CSV. Ele já detecta que é Nubank (pelo formato), conta os
> 31 lançamentos, mostra entradas e saídas. Confirmo e importo.
>
> Resultado: 31 novos, 0 duplicados. Olha aí na lista — vieram TODOS:
> PIX recebido, PIX enviado, pagamento de boleto, compra no débito, etc."

### Cena 5 — Categorização automática com Regras (3:30 → 4:30)
**Tela:** botão **⚙ Regras**
**Fala:**
> "Mas eu não quero categorizar 31 itens na mão. Vou criar uma REGRA AUTOMÁTICA."

**Demonstração:**
- Cria regra: padrão "LANCHONETE" → tipo saída → categoria "Restaurantes / Delivery"
- Cria outra: "POSTO" → "Combustível"
- Fecha o modal

> "Próxima vez que importar, qualquer transação com 'LANCHONETE' na descrição
> vai automaticamente pra categoria Restaurantes. Mas tem o botão **↻ Re-aplicar
> regras** que roda nas transações JÁ importadas — sem sobrescrever as que
> você categorizou manualmente."

### Cena 6 — Conciliar com conta_pagar (4:30 → 5:30)
**Tela:** duplo-clique numa linha de saída tipo "Pagamento de boleto".
**Fala:**
> "Aqui vem o pulo do gato. Quando você paga uma conta programada (tipo
> aluguel ou luz), ela aparece DUAS vezes: uma em Contas a Pagar e outra
> no extrato bancário. Pra não duplicar nos relatórios, eu vinculo as duas.
>
> Duplo-clique na linha → seção 'Vincular com conta a pagar' → ele já
> mostra as candidatas com data e valor próximos. Escolho a certa. Salvo.
>
> Olha o ícone 🔗 que apareceu na linha — vinculada."

### Cena 7 — Marcar conciliado (5:30 → 5:50)
**Fala:**
> "Por último, o checkbox '✓' à direita de cada linha. Marca quando você
> conferiu. Filtra por 'Pendentes' pra focar só no que falta."

### Cena 8 — CTA (5:50 → 6:00)
> "Conciliação é o ÚNICO recurso que diferencia o Serenus de uma planilha.
> Próximo: lançamentos manuais. Like, inscreve, PIX. Tchau."

---

## 📝 Título: "Importando EXTRATO BANCÁRIO no Serenus (CSV, OFX, PDF) | Ep 7"
## 🖼️ Thumb: arquivo CSV → seta → tela do Serenus organizada + "EM 2 CLIQUES"
## 🏷️ Tags: extrato bancário nubank, importar ofx, conciliação bancária, importar csv banco, fluxo de caixa pessoa física
