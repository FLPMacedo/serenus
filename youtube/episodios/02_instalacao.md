# Episódio 02 — Como Baixar e Instalar o Serenus

**Duração-alvo:** 3 minutos
**Objetivo:** zero atrito até a pessoa ter o app instalado e abrindo
**Perfil demo:** nenhum (mostra instalação real, da primeira vez)

---

## 🎬 Roteiro completo

### Cena 1 — Hook (0:00 → 0:15)

**Tela:** página do GitHub Releases aberta.

**Fala:**
> "3 minutos. É o que você precisa pra baixar o Serenus, instalar, e ter
> ele aberto no seu computador. Vem que eu mostro."

---

### Cena 2 — Onde baixar (0:15 → 0:45)

**Tela:** browser navegando até https://github.com/FLPMacedo/serenus/releases

**Fala:**
> "Abre o GitHub do projeto. O link tá na descrição. Vai em 'Releases'
> no menu da direita. A última versão liberada — hoje é a 2.3 — fica
> no topo."

**Visual:** zoom no nome do arquivo `SerenusSetup.exe` (60 MB).

---

### Cena 3 — Download (0:45 → 1:10)

**Tela:** clica no `SerenusSetup.exe`, download começa.

**Fala:**
> "Clica no SerenusSetup.exe. É um único arquivo, não precisa de Python
> nem nada — é um executável completo de 60 MB. Espera baixar."

**Visual:** mostra a barra de download. Acelera o vídeo se demorar.

---

### Cena 4 — Instalação (1:10 → 2:15)

**Tela:** roda o SerenusSetup.exe.

**Fala enquanto avança nas telas:**
> "Abre o instalador. Pode aparecer um aviso do Windows Defender — é
> normal, o executável não tem certificado de code signing ainda. Clica
> em 'Mais informações' e depois 'Executar mesmo assim'.
>
> Próxima tela: idioma português. Próxima: leia os termos se quiser.
> Próxima: onde instalar — pode deixar o padrão `C:\Users\Seu\Serenus`.
>
> Tem 2 opções pra marcar:
> - Criar atalho na área de trabalho — recomendo marcar
> - Iniciar com o Windows — só marca se você usa todo dia
>
> Próxima e Instalar."

**Visual:** barra de progresso. Acelera.

---

### Cena 5 — Primeira abertura (2:15 → 2:45)

**Tela:** Serenus abre pela primeira vez, mostra wizard de setup.

**Fala:**
> "Abre o Serenus. Na primeira vez ele pede algumas informações básicas:
> seu nome, renda mensal estimada... Isso é só pra personalizar o
> dashboard. Pode pular se quiser, depois ajusta nas Configurações."

**Visual:** preenche rapidamente o wizard.

---

### Cena 6 — Onde ficam os dados (2:45 → 3:15)

**Tela:** abre o Explorer no caminho `%APPDATA%\Serenus\`

**Fala:**
> "Importante: o banco de dados fica AQUI: `%APPDATA%\Serenus\`. Tem o
> `serenus.db` que é onde TODOS os seus dados ficam, e a pasta `backups`
> que o próprio app gera automaticamente. Nada vai pra nuvem.
>
> Se você desinstalar o app, esses dados FICAM. Pra remover tudo de
> verdade, apaga essa pasta manualmente."

---

### Cena 7 — CTA (3:15 → 3:30)

**Fala:**
> "Pronto, app instalado. No próximo vídeo vou mostrar os primeiros
> passos: setup inicial, senha, ativar Modo Demo pra você testar tudo.
>
> Curtiu? Like e inscreve. PIX na descrição. Tchau."

---

## 📋 Anotações de produção

- **Conta de gravação**: use uma conta de usuário NOVA do Windows, ou pelo
  menos rode o instalador num PC sem instalação prévia, pra mostrar
  a experiência real do primeiro uso.
- **Cuidado com avisos antivírus**: alguns podem bloquear `SerenusSetup.exe`.
  Mostre como liberar (Windows Defender > Histórico de proteção > Permitir).
- **Acelere o que for chato**: barra de download, progresso de instalação —
  velocidade 2x ou cortes.

## 📝 Título sugerido

```
Como BAIXAR e INSTALAR o Serenus no Windows em 3 minutos | Ep 2
```

Alternativas:
- "Instalando o Serenus: passo a passo do zero"
- "Tutorial: download e instalação do Serenus (grátis)"

## 🖼️ Thumbnail sugerida

- **Texto grande:** "INSTALANDO EM 3 MIN"
- **Subtexto:** "Serenus Windows"
- **Imagem:** screenshot do instalador rodando + logo Serenus + logo Windows
- **Seta vermelha** apontando pro botão "Instalar"

## ⚠️ Pontos críticos pra abordar

1. **Aviso do Windows Defender** — explicar que é falso positivo
2. **Onde ficam os dados** — `%APPDATA%\Serenus\` (gerar tranquilidade)
3. **Backup automático** — primeira instalação já cria pasta `backups/`
4. **Pode desinstalar a qualquer hora** — dados ficam preservados
