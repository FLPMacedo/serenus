# Episódio 16 — FAQ e Troubleshooting (perguntas e erros comuns)

**Duração-alvo:** 5 min · **Perfil demo:** qualquer

---

## 🎬 Roteiro

### Cena 1 — Hook (0:00 → 0:20)
> "Antivírus bloqueou? Esqueceu a senha? Importação não pegou um item?
> Hoje eu respondo as 10 dúvidas mais frequentes sobre o Serenus."

### Cena 2 — As 10 perguntas (0:20 → 4:30)

#### 1. "O antivírus do Windows bloqueou a instalação" (0:20 → 0:45)
> "Falso positivo. O Serenus não tem certificado de code signing ainda.
> Clica em 'Mais informações' no aviso e depois 'Executar mesmo assim'.
> Se o Windows Defender quarentinou, vai em Histórico de proteção e
> clica em Permitir."

#### 2. "Esqueci a senha do app, e agora?" (0:45 → 1:15)
> "A senha fica HASHED no banco. Não tem 'esqueci minha senha' clássico.
> Mas: você pode RESETAR apagando o registro de senha no SQLite. Veja
> Documentação Técnica → seção 'Reset de senha'. Cuidado: requer
> ferramenta tipo DB Browser pra SQLite."

#### 3. "Importei a fatura PDF mas faltou alguns itens" (1:15 → 1:50)
> "Cada parser tem suas peculiaridades. Os 7 emissores suportados (Nubank,
> Itaú, Credicard, Luizacred, Digio, Will, Mercado Livre) foram testados
> com PDFs reais. Se faltou item: abre um issue no GitHub mandando ANEXO
> o PDF (anonimizado). Eu melhoro o parser."

#### 4. "Funciona no Mac? No Linux?" (1:50 → 2:15)
> "Hoje só Windows (PyInstaller bundle). O CÓDIGO é Python puro com
> customtkinter — roda em Mac/Linux se você clonar o GitHub e instalar
> as deps. Mas instalador pronto, só Windows por enquanto."

#### 5. "Posso usar em 2 computadores?" (2:15 → 2:50)
> "Sim, mas o banco fica LOCAL em cada um. Pra sincronizar: faça backup
> num PC, copia o `serenus.db` pro outro, restaura. Sincronia em tempo
> real não existe hoje (e não vai existir — é o ponto: tudo local)."

#### 6. "Como exportar TUDO meus dados?" (2:50 → 3:15)
> "Vai em cada tela e clica '⬇ Excel'. Tem em: Extrato, Carteira, Fatura,
> Contas a Pagar, Dívidas, Receitas, Projeção, Metas, IR Estimado.
> Pra TODOS os dados de uma vez: backup `.db` é um SQLite que abre em
> qualquer ferramenta (DB Browser, DBeaver)."

#### 7. "Posso editar meu plano de contas (categorias)?" (3:15 → 3:35)
> "Sim. Vai em Plano de Contas. Pode criar nova categoria, editar nome,
> desativar. Se tiver feito asneira: botão 'Restaurar Padrões' volta
> as 34 categorias originais."

#### 8. "O app trava abrindo. O que faço?" (3:35 → 4:00)
> "1. Fecha tudo. 2. Abre `%APPDATA%\Serenus\` no Explorer. 3. Renomeia
> `serenus.db` pra `serenus.db.problema`. 4. Abre o Serenus — ele cria
> banco novo zerado. 5. Funcionou? O problema era no banco. 6. Restaure
> de um backup anterior em `backups/`."

#### 9. "Posso pagar por uma versão Pro?" (4:00 → 4:20)
> "Hoje não tem. Plano: até 2027 o Serenus é 100% grátis. Depois talvez
> apareça uma Versão Pro com features extras (relatórios avançados,
> sincronia entre dispositivos). Mas a versão atual de hoje continua
> grátis pra sempre."

#### 10. "Como contribuir com o projeto?" (4:20 → 4:35)
> "3 formas:
> 1. Reporta bugs em github.com/FLPMacedo/serenus/issues
> 2. Compartilha o canal com quem precisa
> 3. PIX (descrição) — qualquer valor ajuda"

### Cena 3 — Onde achar mais ajuda (4:35 → 4:55)
**Fala:**
> "Manual do Usuário e Playbook em PDF VÊM dentro do instalador.
> Tem na pasta `docs/` depois que instalar. 80 páginas de detalhes."

### Cena 4 — Encerramento da série (4:55 → 5:30)
**Fala:**
> "Esse é o ÚLTIMO vídeo da série inicial. Obrigado por ter chegado até
> aqui!
>
> Se você viu todos os 17 vídeos: você sabe o Serenus melhor que 99%
> dos usuários.
>
> Se gostou: like, inscreve, e me marca naquele amigo que precisaria.
> PIX na descrição pra quem quiser apoiar — qualquer valor.
>
> Até a próxima série. UaiScript fora."

---

## 📝 Título: "10 dúvidas e ERROS comuns no Serenus respondidas | Ep 16 (FAQ)"
## 🖼️ Thumb: ícone ❓ grande + texto "PERGUNTAS QUE TODO MUNDO FAZ"
## 🏷️ Tags extras: serenus troubleshooting, problema antivirus, esqueci senha, app finanças mac linux
