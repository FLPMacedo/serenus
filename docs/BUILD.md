# Guia de Build — Serenus

> Como gerar o executável `Serenus.exe` e o instalador `SerenusSetup.exe`.

---

## Pré-requisitos

| Ferramenta | Versão mínima | Download |
|------------|--------------|---------|
| Python | 3.12 | https://www.python.org/downloads/ |
| PyInstaller | 6.x | `pip install pyinstaller` |
| Inno Setup | 6.x | https://jrsoftware.org/isinfo.php |

Instale as dependências do projeto antes de gerar o build:

```bash
pip install -r requirements.txt
pip install pyinstaller
```

---

## Estrutura de caminhos em produção

O Serenus usa o módulo `_paths.py` para resolver caminhos de forma
compatível entre desenvolvimento e bundle:

| Recurso | Em desenvolvimento | No bundle (exe) |
|---|---|---|
| Banco de dados | `serenus.db` (raiz do projeto) | `%APPDATA%\Serenus\serenus.db` |
| Backups | `backups/` (raiz do projeto) | `%APPDATA%\Serenus\backups\` |
| Tokens Google | `google_token.json` (raiz) | `%APPDATA%\Serenus\google_token.json` |
| Imagens | `imagens/` (raiz) | Extraído pelo PyInstaller em `sys._MEIPASS\imagens\` |

Os dados do usuário **nunca** ficam dentro do `.exe` — ficam em
`%APPDATA%\Serenus` e são preservados entre atualizações.

---

## Passo 1 — Gerar o executável com PyInstaller

Na raiz do projeto, execute:

```bash
pyinstaller serenus.spec
```

O processo leva alguns minutos. O executável final será gerado em:

```
dist\Serenus.exe
```

### Verificando o build

Após a geração, teste o executável **sem o ambiente virtual ativo**:

```bash
dist\Serenus.exe
```

O app deve abrir normalmente. Na primeira execução, cria automaticamente:
- `%APPDATA%\Serenus\serenus.db` (banco de dados)
- `%APPDATA%\Serenus\backups\` (pasta de backups)

---

## Passo 2 — Gerar o instalador com Inno Setup

### Opção A — Linha de comando

```bash
iscc instalador\serenus.iss
```

### Opção B — Interface gráfica

1. Abra o Inno Setup IDE
2. Arquivo → Abrir → selecione `instalador\serenus.iss`
3. Pressione **F9** (Compilar)

O instalador será gerado em:

```
instalador\output\SerenusSetup.exe
```

---

## O que o instalador faz

- Copia `dist\Serenus.exe` para `%ProgramFiles%\Serenus\` (ou pasta do usuário, sem admin)
- Cria atalho no Menu Iniciar
- Cria atalho na Área de Trabalho (opcional, desmarcado por padrão)
- Oferece opção de iniciar com o Windows
- Inclui desinstalador registrado no Painel de Controle

### Desinstalação

A desinstalação remove apenas o executável e os atalhos.
**Os dados do usuário em `%APPDATA%\Serenus` são preservados** por segurança.
Para remover tudo, exclua manualmente a pasta `%APPDATA%\Serenus`.

---

## Atualização de versão

1. Atualize `#define MyAppVersion` em `instalador\serenus.iss`
2. Rode `pyinstaller serenus.spec` novamente
3. Rode `iscc instalador\serenus.iss` novamente
4. Distribua o novo `SerenusSetup.exe`

O instalador sobrescreve o executável anterior e preserva os dados do usuário.

---

## Solução de problemas

### `ModuleNotFoundError` ao abrir o exe

Adicione o módulo em `hiddenimports` no `serenus.spec`:

```python
hiddenimports=["nome_do_modulo"],
```

Depois rode `pyinstaller serenus.spec` novamente.

### Imagem não encontrada (logo, bandeiras)

Verifique se todos os arquivos de `imagens/` estão listados em `datas` no `serenus.spec`:

```python
datas=[
    ("imagens/logo.png",      "imagens"),
    ("imagens/logo.ico",      "imagens"),
    ("imagens/visa.png",      "imagens"),
    ("imagens/mastercad.png", "imagens"),
],
```

### Antivírus bloqueia o exe

PyInstaller gera falsos positivos em alguns antivírus. Assine digitalmente o
executável com um certificado de code signing para eliminar alertas em produção.

### Inno Setup — idioma português não encontrado

Instale o arquivo de idioma:
1. Abra o Inno Setup IDE
2. Ferramentas → Configurar arquivos de idioma
3. Baixe `BrazilianPortuguese.isl` e coloque em `C:\Program Files (x86)\Inno Setup 6\Languages\`

---

## Resumo rápido

```bash
# 1. Gerar executável
pyinstaller serenus.spec

# 2. Testar executável
dist\Serenus.exe

# 3. Gerar instalador
iscc instalador\serenus.iss

# 4. Distribuir
instalador\output\SerenusSetup.exe
```
