# Serenus — Pasta `demos/`

Esta pasta contém **arquivos de demonstração** gerados a partir dos 20 perfis
demo do `demo_manager.py`. Servem para 5 finalidades:

1. **Apresentação comercial** do software
2. **Videoaulas** mostrando o uso prático
3. **Testes manuais guiados**
4. **Massa para testes automatizados** (via `tests/test_perfis_demo.py`)
5. **Exemplos de importação** (faturas de cartão + extratos bancários)

## Estrutura por perfil

```
demos/<perfil>/
├── perfil.md                                ← descrição do perfil
├── cartoes/
│   └── fatura_<banco>_<mes>.xlsx           ← planilha importável (1 por cartão x mês)
└── extratos/
    ├── extrato_nubank_<mes>.csv            ← formato CSV Nubank (4 colunas)
    └── extrato_nubank_<mes>.ofx            ← formato OFX 1.0.2 SGML
```

Todos os arquivos seguem **exatamente os formatos que o Serenus já lê** —
foram testados em round-trip (geração → parser → DB).

## Os 20 perfis

### Cotidiano
| Chave | Cenário comercial / didático |
|---|---|
| `padrao` | Classe média padrão. Bom pra mostrar o app inteiro. |
| `apertado` | Renda baixa, 6 cartões. Demonstra fragmentação. |
| `no_verde` | Sobra ~R$ 500/mês. Cenário positivo. |

### Trajetória de dívida
| Chave | Cenário comercial / didático |
|---|---|
| `moderado_dividas` | Despesas crescentes — começo do problema. |
| `endividado_6m` | 6 meses de rotativo. Cartões 80%+. |
| `endividado_1a` | 1 ano de bola de neve. 4 cartões + fatura atrasada. |
| `bem_endividado` | Parcelas comprometem 54% da renda. 5 cartões + 3 dívidas. |
| `muito_endividado` | Crítico: 8 cartões 95%+, 2 faturas atrasadas, cheque especial. |
| `moderado_recuperando` | Pagando dívidas — cenário de recuperação. |

### Investidores
| Chave | Cenário comercial / didático |
|---|---|
| `primeiro_passo` | Tesouro + CDB iniciante. Foco em metas pequenas. |
| `em_ritmo` | Carteira diversificada de 3 anos. |
| `patrimonio_crescendo` | Carteira consolidada, FIIs + ações + cripto. |

### Profissionais / vida
| Chave | Cenário comercial / didático |
|---|---|
| `profissional_informal` | Designer freela + aluguel + vendas avulsas. Sem CLT. |
| `prestador_servico` | Eletricista. **Único** com OS + Clientes + Produtos + Vendas integrados. |
| `casal_planejando` | Casal CLT, 5 metas grandes (casa, casamento, viagem, etc). |
| `aposentado_classico` | INSS + bicos. Despesas controladas. |
| `aposentado_investidor` | Vive de dividendos. ~R$ 720k investido. |
| `freelancer_alta_renda` | Dev PJ R$ 18k/mês. Carteira agressiva + cripto. |
| `mei_loja` | Papelaria com vendas balcão diárias. |
| `estudante_universitario` | Bolsa + estágio + ajuda família. Despesas baixas. |

## Como usar em uma demonstração / videoaula

1. **Resetar dados**: Configurações > Zerar Sistema
2. **Ativar perfil**: Configurações > Modo Demonstrativo > selecione o perfil
3. **Navegar pelas telas**: o app já vai estar populado coerente com o cenário
4. **Importar arquivos** (opcional, pra reforçar a demo de importação):
   - Cartões > selecione um cartão > Importar > Excel/CSV →
     `demos/<perfil>/cartoes/fatura_*.xlsx`
   - Fluxo de Caixa > Conciliação Bancária > Importar →
     `demos/<perfil>/extratos/extrato_nubank_*.csv` (ou `.ofx`)

## Regerando os arquivos

```bash
# Todos os perfis
python demo_manager_arquivos.py

# Só um perfil específico
python demo_manager_arquivos.py prestador_servico
```

Os arquivos são determinísticos (mesmo seed `random.Random(42)` do demo).

## Aviso

Todos os dados são **fictícios**. Nomes, CPFs e CNPJs gerados são exemplos —
não correspondem a pessoas/empresas reais.
