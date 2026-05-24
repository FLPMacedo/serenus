# Estratégia do Canal UaiScript — Série Serenus

> Documento vivo. Atualize conforme aprender o que funciona.

## 1. Posicionamento

**O Serenus é o app de finanças pessoais brasileiro que importa direto do
seu banco e cartão, sem subir nada pra nuvem.**

Os 3 diferenciais que toda comunicação enfatiza:

1. **Tudo local** — banco SQLite na máquina, nada na nuvem, zero LGPD risk
2. **Importa de verdade** — 7 emissores de cartão (PDF), 3 formatos de extrato
3. **Cabe na vida real** — 20 perfis demo prontos cobrindo desde estudante até aposentado investidor

## 2. Público-alvo (3 personas)

### 👤 Persona 1: "Carlos, classe média endividado"
- 30-50 anos, CLT, 4-6 cartões, parcelas comprometem 40-60% da renda
- Quer organizar pra sair do rotativo
- **Vídeos relevantes**: 04, 05, 06, 09, 15 (perfis bem_endividado/muito_endividado)

### 👤 Persona 2: "Joana, MEI / prestadora de serviço"
- 25-45 anos, sem CLT, renda variável
- Quer separar pessoal de empresarial, controlar clientes/OS
- **Vídeos relevantes**: 04, 11, 12, 13 (perfis prestador_servico/mei_loja)

### 👤 Persona 3: "Pedro, investidor disciplinado"
- 28-55 anos, já tem reserva, investe mensalmente
- Quer ver patrimônio crescer + simular cenários
- **Vídeos relevantes**: 04, 07, 09, 10, 11 (perfis em_ritmo/patrimonio_crescendo/aposentado_investidor)

## 3. Calendário sugerido (3 meses)

### Mês 1 — Lançamento + uso básico (8 vídeos)
| Semana | Vídeo |
|--------|-------|
| 1 | 00 Teaser + 01 Apresentação (2 vídeos no mesmo dia, máximo engajamento) |
| 2 | 02 Instalação + 03 Primeiros passos |
| 3 | 04 Receitas e despesas |
| 4 | 05 Cartões + 06 Importar PDF |

### Mês 2 — Diferenciais + casos de uso (5 vídeos)
| Semana | Vídeo |
|--------|-------|
| 5 | 07 Conciliação bancária ⭐ (o diferencial mais forte) |
| 6 | 08 Lançamentos manuais |
| 7 | 09 Dívidas e projeção |
| 8 | 10 Investimentos |

### Mês 3 — Nichos + operação (4 vídeos)
| Semana | Vídeo |
|--------|-------|
| 9 | 11 Metas |
| 10 | 12 Prestador de serviço (vídeo de nicho, deve viralizar pequeno) |
| 11 | 13 MEI |
| 12 | 14 Backup + 16 FAQ |

**Vídeo 15 (perfis demo) — publicar como bônus quando quiser.**

> **Cadência sugerida**: 1-2 vídeos por semana. Não tente fazer todos
> de uma vez — burnout mata canal.

## 4. Branding visual

- **Cor principal**: roxo `#6D28D9` (mesma cor do Nubank no app + identidade Serenus)
- **Cor secundária**: verde `#10B981` (positivo, financeiro saudável)
- **Cor de destaque**: laranja `#EC7000` (alerta, atenção)
- **Fonte sugerida pra thumbnails**: Inter Bold ou Montserrat ExtraBold
- **Estilo**: telas do app + texto grande sobreposto + 1 elemento gráfico (seta, círculo)

## 5. Métricas que importam

Não persiga views — persiga **conversão** (download do app):

| Métrica | Onde ver | Meta inicial |
|---|---|---|
| **CTR da thumb** | YouTube Studio | > 4% |
| **Retenção média** | YouTube Studio | > 50% (vídeos curtos ajudam) |
| **Cliques no link da descrição** | YouTube Studio → Acessos | > 10% das views |
| **Downloads do GitHub Releases** | github.com/FLPMacedo/serenus/releases | Conta no relatório mensal |
| **PIX recebidos** | Banco | Bônus, não meta |

## 6. SEO básico — palavras-chave alvo

Pesquisar essas no YouTube e ver competição:

- "app de finanças pessoais offline"
- "controle financeiro grátis sem mensalidade"
- "importar fatura nubank pdf"
- "importar extrato banco csv"
- "planilha finanças não funciona mais"  ← cria atrito com Excel
- "MEI controle financeiro grátis"
- "fluxo de caixa pessoa física"

## 7. Estratégia de monetização

### Fase 1 (atual): gratuito + PIX
- Software 100% gratuito
- Chave PIX nas descrições e como comentário fixado
- **NÃO pedir donativo no vídeo** (deixa pra descrição) — soa mendigo
- Frase pra usar: *"Se o Serenus te ajudou, considere apoiar com qualquer valor via PIX. Link na descrição."*

### Fase 2 (depois de 6-12 meses, opcional):
- Versão Pro com recursos extra (relatórios avançados, sincronia entre dispositivos, OCR ilimitado, suporte prioritário)
- Manter versão grátis com tudo o que tem hoje
- Preço sugerido: R$ 9,90/mês ou R$ 79/ano (assinatura barata)

### Fase 3 (se viralizar):
- Patrocínios de bancos digitais / fintechs
- Curso pago sobre educação financeira usando o Serenus

## 8. Riscos e como mitigar

| Risco | Mitigação |
|---|---|
| Suporte virar bola de neve | Já tem MANUAL_DEMOS + MANUAL_USUARIO em PDF dentro do instalador. FAQ em vídeo (ep 16). |
| Bugs em produção viralizar | Sistema de backup automático pré-update já existe (instalador faz). Mostrar isso no vídeo de backup. |
| Reclamação "porque tem que instalar?" | Justificar SEMPRE no início dos vídeos: "tudo local = nada na nuvem = seus dados são seus". |
| Concorrência (Mobills, Organizze) | NÃO atacar diretamente. Posicionar como alternativa pra quem quer privacidade total. |

## 9. Próximos passos

- [ ] Criar logo do canal (atual é o do Serenus? OK pra começar)
- [ ] Banner do canal (1546×423px) com chamada da série
- [ ] Filmar os 2 primeiros vídeos antes de publicar o teaser (evita ansiedade)
- [ ] Definir intro/outro de 5s reutilizável (animação simples)
- [ ] Criar pasta no Drive/Notion com cronograma de gravação
