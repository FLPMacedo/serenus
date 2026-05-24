# Descrições YouTube — Como usar

Esta pasta tem **uma descrição pronta por episódio** (00 a 16).
Cada descrição segue o template definido em `youtube/templates/modelo_descricao_youtube.md`.

## Como usar

1. Grave o vídeo
2. Suba no YouTube
3. Abra `<numero>_<nome>.md` correspondente
4. Copie o bloco entre as marcações `📋 INÍCIO DA DESCRIÇÃO` e `📋 FIM DA DESCRIÇÃO`
5. Cole no campo "Descrição" do YouTube
6. **Substitua os marcadores** `<URL...>` pelos links reais quando tiver:
   - `<URL_PROXIMO_VIDEO>` → URL do próximo vídeo da série
   - `<URL_PLAYLIST>` → URL da playlist "Aprenda o Serenus"
7. Adicione as tags (estão no fim de cada arquivo, em bloco separado)
8. Publique

## Chave PIX

Todas as descrições já têm a chave PIX preenchida:

```
filipemarquesmacedo12@gmail.com
```

Se você quiser MUDAR a chave PIX no futuro, rode este comando no terminal:

```bash
# Linux/Mac/Git Bash:
cd <raiz do projeto>
find youtube docs/MANUAL_DEMOS.md -name "*.md" \
  -exec sed -i 's/filipemarquesmacedo12@gmail.com/nova_chave@email.com/g' {} +

# Ou no PowerShell:
Get-ChildItem -Recurse youtube -Filter *.md | ForEach-Object {
    (Get-Content $_.FullName) -replace 'filipemarquesmacedo12@gmail.com', 'nova_chave@email.com' |
    Set-Content $_.FullName
}
```

Não esqueça de fazer o mesmo no `youtube/README.md`, `youtube/DONATIVOS_E_PIX.md`,
`youtube/templates/modelo_descricao_youtube.md` e arquivos de `youtube/redes_sociais/`
se houver.
