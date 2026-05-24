# Manual de Demonstrações — Serenus

Este guia explica como usar os **20 perfis demo** do Serenus em:

- 🎬 Videoaulas
- 💼 Apresentações comerciais
- 🧪 Testes manuais guiados
- 🤖 Testes automatizados (cobertos por `tests/test_perfis_demo.py`)

---

## 1. Como ativar um perfil demo

1. Abra o Serenus
2. Vá em **⚙️ Configurações → 🎭 Modo Demonstrativo**
3. No combo, escolha o perfil desejado
4. Clique em **Ativar Modo Demo**

⚠️ O sistema **zera os dados existentes** antes de popular o perfil.
Faça backup pelo módulo Backup se tiver dados próprios.

---

## 2. Os 20 perfis — guia de uso

### 🟢 Grupo 1 — Cotidiano (3 perfis)

#### `padrao` — Padrão (Classe Média)
**Quando usar:** demo geral, mostrar TODAS as telas. Cenário equilibrado.
**Renda:** CLT R$ 8.500 + Freela R$ 1.800. 13º e Férias.
**Despesas:** ~R$ 4.500 fixas + variáveis típicas.
**Cartões:** 2 (Nubank Gold + Itaú Visa Platinum).
**Telas-foco:** todas — é o "perfil padrão" pra videoaula introdutória.

#### `apertado` — Renda Baixa / Muitos Cartões
**Quando usar:** mostrar o problema de fragmentação de crédito.
**Renda:** CLT R$ 3.500 apenas.
**Cartões:** 6 cartões diferentes (Nubank, Bradesco, Santander, Caixa,
Magazine Luiza, Americanas).
**Roteiro sugerido:**
1. Mostre a tela de Cartões → "olha quantos cartões fragmentados"
2. Mostre o Fluxo de Caixa → "parcelas comprometem grande parte"
3. Mostre Alertas → fatura sempre estourando

#### `no_verde` — Sobra ~R$ 500/mês
**Quando usar:** cenário ideal, demo positiva. Mostra Metas funcionando.

---

### 🔴 Grupo 2 — Trajetória de dívida (6 perfis)

Estes 6 perfis contam uma **história em 6 capítulos**. Use-os em sequência
em uma videoaula sobre "como o endividamento se desenvolve":

#### `moderado_dividas` — Cap. 1: Começando a se complicar
Despesas crescem 1% ao mês. Ainda dá pra controlar.

#### `endividado_6m` — Cap. 2: Já no rotativo
3 cartões em 80%+. Despesas 1,5%/mês há 6 meses. Empréstimo recente.
**Demo:** abra Cartões → mostre o uso alto. Visão Futura → meses no
vermelho começam a aparecer.

#### `endividado_1a` — Cap. 3: 1 ano de bola de neve
4 cartões 90%+. **1 fatura atrasada visível**. Cheque especial ativo.
**Demo:** Alertas vai mostrar a fatura atrasada. Projeção piora.

#### `bem_endividado` — Cap. 4: Parcelas consomem 54% da renda
5 cartões + 3 dívidas pesadas (financiamento + 2 empréstimos).
**Demo:** Visão Futura mostra projeção bem comprometida.

#### `muito_endividado` — Cap. 5: Crítico
**8 cartões 95%+, 2 faturas em atraso (35d e 18d), cheque especial
estourado**.
**Roteiro:**
1. Alertas → vai cheio de alertas vermelhos
2. Cartões → todos no limite
3. Dívidas → 4 dívidas ativas grandes
4. Visão Futura → projeção desastrosa

#### `moderado_recuperando` — Cap. 6: Saindo do buraco
Pagando dívidas, despesas caem 0,7%/mês. **Final feliz.**
**Demo:** mostrar como o saldo livre melhora mês a mês.

---

### 📈 Grupo 3 — Investidores (3 perfis)

#### `primeiro_passo` — Começando a investir
Tesouro + CDB iniciante. Reserva de emergência em construção.
**Demo:** mostre módulo Investimentos com carteira pequena.

#### `em_ritmo` — Investidor há 3 anos
Ações + FIIs + RF diversificada.

#### `patrimonio_crescendo` — Carteira consolidada
Cripto + ETFs + FIIs + Tesouro. Várias correções de IR.

---

### 👥 Grupo 4 — Profissionais / vida (8 perfis)

#### `profissional_informal` — Designer freelancer com múltiplas rendas
**Demo única:** sem CLT, vive de Freela + Aluguel + Vendas avulsas
(12 vendas: designs, consultorias, edição de vídeo).
**Telas-foco:** Receitas (Fontes múltiplas), Vendas, Fluxo de Caixa
mostrando renda variável.

#### `prestador_servico` — Eletricista (OS + Clientes + Vendas + Produtos)
🌟 **Perfil mais rico em integração entre módulos**. Use em videoaula
específica sobre OS.
- 6 clientes cadastrados (3 residenciais + 2 comerciais com CNPJ)
- 14 produtos (mão-de-obra + materiais elétricos)
- 14 vendas de balcão
- 6 OS em **todos os status possíveis** (aberta, em_andamento,
  aguardando_peca, concluida)

**Roteiro:**
1. Clientes → mostra cadastro
2. Produtos → catálogo de materiais
3. OS → 6 ordens em estados diferentes (mostra workflow)
4. Vendas → balcão diário
5. Imprime PDF de uma OS

#### `casal_planejando` — Casal CLT planejando o futuro
**Foco:** módulo Metas. 5 metas grandes ativas (apto R$ 60k entrada,
casamento R$ 45k, lua de mel R$ 18k, reserva R$ 42k, carro R$ 85k).
**Demo:** abra Metas e mostre os 5 cards de progresso.

#### `aposentado_classico` — INSS + bicos
**Foco:** orçamento enxuto pós-aposentadoria. Plano de saúde alto,
farmácia contínua.

#### `aposentado_investidor` — Vive de dividendos (FIRE)
**Foco:** carteira robusta de FIIs + ações dividend payers + Tesouro IPCA.
~R$ 720k investido. Meta: R$ 1M.
**Demo:** módulo Investimentos com dividendos mensais visíveis.

#### `freelancer_alta_renda` — Dev PJ R$ 18k/mês
**Foco:** cartões premium + carteira agressiva (ações tech + cripto).
8 vendas (mentorias técnicas + cursos in-company).
**Demo:** Bitcoin + ações + CDB + Tesouro. Cenário "tech".

#### `mei_loja` — Papelaria com balcão diário
**Foco:** 25+ vendas balcão em 4 meses + receita especial "Vendas de
Natal". Capital de giro Sebrae como dívida.

#### `estudante_universitario` — Bolsa + estágio + ajuda família
**Foco:** orçamento mínimo (R$ 2.700 total). Aluguel república,
transporte público.

---

## 3. Roteiros sugeridos por tipo de apresentação

### 🎬 Videoaula 1 — "Conheça o Serenus em 5 minutos"
1. Ative `padrao`
2. Tour rápido: Dashboard → Cartões → Dívidas → Fluxo de Caixa → Visão Futura
3. Fechamento: Configurações → Modo Demo (mostra que tem 20 perfis)

### 🎬 Videoaula 2 — "Como sair das dívidas com o Serenus"
1. Ative `muito_endividado` → mostre o caos (Alertas vermelhos)
2. Ative `bem_endividado` → "este é o ponto de partida"
3. Mostre como usar Metas + Visão Futura pra planejar saída
4. Ative `moderado_recuperando` → "depois de 1 ano de disciplina"

### 🎬 Videoaula 3 — "Serenus pra prestadores de serviço"
1. Ative `prestador_servico`
2. Mostre Clientes (cadastrados com CNPJ pra PJ)
3. Mostre Produtos (catálogo)
4. Mostre OS (6 em estados diferentes)
5. Imprima 1 OS em PDF
6. Mostre Vendas (balcão à vista + a prazo)

### 💼 Apresentação comercial — Demo de 15 minutos
1. `padrao` (3min) — visão geral
2. `prestador_servico` (4min) — OS + clientes (diferencial)
3. `muito_endividado` (3min) — alertas + projeção (valor que entrega)
4. `aposentado_investidor` (3min) — investimentos consolidados
5. `casal_planejando` (2min) — metas grandes

---

## 4. Importação de arquivos demo

Cada perfil tem arquivos prontos em `demos/<perfil>/` para demonstrar
importação:

### Importar fatura de cartão (Excel/XLSX)
1. Cartões → selecione um cartão → botão **⬆ Importar**
2. Escolha **Excel/CSV**
3. Aponte para `demos/<perfil>/cartoes/fatura_<banco>_<mes>.xlsx`
4. Confirme

### Importar extrato bancário (CSV ou OFX)
1. Fluxo de Caixa → aba **🏦 Conciliação Bancária**
2. Cadastre uma conta (se ainda não tem)
3. Botão **⬆ Importar**
4. Aponte para `demos/<perfil>/extratos/extrato_nubank_<mes>.csv` (ou `.ofx`)
5. Confirme — vai mostrar preview, depois importar

---

## 5. Massa para testes automatizados

Os 20 perfis também são usados como massa de teste em:

```bash
pytest tests/test_perfis_demo.py
```

São **252 testes parametrizados** que rodam cada perfil em banco SQLite
temporário e validam:
- Carregamento sem erro
- Integridade cross-module (extrato, projeção, alertas, dashboard)
- Exportação Excel
- Arquivos da pasta `demos/` parseáveis (round-trip)
- Cenários específicos (muito_endividado tem alertas, prestador_servico
  tem clientes + OS, etc)

Para adicionar um perfil novo:
1. Adicione em `PERFIS_DEMO` (dict) em `demo_manager.py`
2. Crie a função `_popular_<chave>(conn, planos, rng, hoje) -> int`
3. Registre em `_PERFIL_FNS`
4. Rode `python demo_manager_arquivos.py <chave>` pra gerar os arquivos
5. Adicione assertions em `TestCenariosEspecificos` se for um cenário extremo
6. Pronto — os 240 testes parametrizados rodam automaticamente

---

## 6. Regerando arquivos demo

Se mudar a lógica de um perfil, regenere os arquivos:

```bash
# Todos os perfis (regera ~264 arquivos)
python demo_manager_arquivos.py

# Só um perfil específico
python demo_manager_arquivos.py prestador_servico
```

Os arquivos são determinísticos (seed `random.Random(42)`), então
saídas idênticas pra mesma versão do código.

---

## 7. Aviso

Todos os dados, nomes, CPFs e CNPJs são **fictícios**. Não correspondem
a pessoas ou empresas reais.
