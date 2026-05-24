# Episódio 14 — Backup e Segurança dos Dados

**Duração-alvo:** 4 min · **Perfil demo:** qualquer (foco em backup)

---

## 🎬 Roteiro

### Cena 1 — Hook (0:00 → 0:20)
> "HD pifou. Trocou de notebook. Reinstalou Windows. E os 2 anos de
> dados financeiros que você cadastrou no Serenus? Hoje vou mostrar
> como NUNCA perder isso."

### Cena 2 — Onde estão os dados (0:20 → 0:50)
**Tela:** Explorer abrindo `%APPDATA%\Serenus\`
**Fala:**
> "Recap rápido: tudo do Serenus fica nessa pasta `%APPDATA%\Serenus\`.
> 2 coisas importantes:
> - `serenus.db` — TODOS os seus dados
> - `backups/` — backups automáticos"

### Cena 3 — Backup MANUAL (0:50 → 1:45)
**Tela:** sidebar → 💾 Backup (`12_backup.png`)
**Fala:**
> "Tela de Backup tem duas seções:
>
> **1. Backup manual local** — clica em '💾 Criar backup' e ele copia o
> `serenus.db` pra pasta `backups/` com timestamp no nome. Recomendo
> fazer 1x por semana se você usa o app diariamente."

**Visual:** clica em Criar backup, mostra arquivo novo aparecendo na lista.

### Cena 4 — Backup automático pré-atualização (1:45 → 2:30)
**Fala:**
> "**2. Backup automático** — toda vez que você ATUALIZA o Serenus
> (instala uma versão nova por cima), o INSTALADOR faz backup
> automaticamente antes. Olha aqui na lista — esses com 'pre-update' são
> exatamente isso. Se a versão nova quebrar alguma coisa, é só restaurar."

### Cena 5 — Restaurar (2:30 → 3:15)
**Tela:** lista de backups → clica em um → **🔄 Restaurar**
**Fala:**
> "Pra restaurar: escolhe o backup na lista, clica em Restaurar, confirma.
> O Serenus FECHA, troca o banco, e na próxima vez que você abrir, tá
> tudo como no momento daquele backup.
>
> Atenção: backup é SOBRESCREVE. Tudo que você cadastrou DEPOIS do
> backup vai sumir. Por isso eu sempre faço um backup ANTES de restaurar
> outro."

### Cena 6 — Google Drive (3:15 → 3:45)
**Fala:**
> "Tem também a opção de mandar backup pro Google Drive. Você autoriza
> uma vez e ele manda automaticamente. Pra quem tem medo de perder o
> HD físico, é uma camada extra. Configura em Configurações → Google Drive."

### Cena 7 — Senha (3:45 → 4:00)
**Fala:**
> "Pra segurança: defina uma SENHA pra abrir o Serenus em Configurações.
> Mesmo se alguém pegar seu PC, não consegue ver os dados sem a senha."

### Cena 8 — CTA (4:00 → 4:15)
> "Próximo (penúltimo!): tour pelos 20 perfis demo. Like, inscreve, PIX. Tchau."

---

## 📝 Título: "BACKUP automático no Serenus (local + Google Drive) | Ep 14"
## 🖼️ Thumb: ícone de disco rígido com check verde + "NUNCA MAIS PERCA"
