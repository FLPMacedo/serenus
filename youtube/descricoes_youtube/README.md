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
7. Adicione as tags (estão no fim da descrição, separadas)
8. Publique

## Placeholder `<SEU_EMAIL_PIX>`

Todas as descrições usam o placeholder `<SEU_EMAIL_PIX>` pro PIX.

Substitua **TUDO de uma vez** com este comando no terminal:

```bash
cd youtube/descricoes_youtube
# Linux/Mac/Git Bash:
find . -name "*.md" -exec sed -i 's/<SEU_EMAIL_PIX>/seu_email@exemplo.com/g' {} +

# Ou no PowerShell:
Get-ChildItem *.md | ForEach-Object {
    (Get-Content $_.FullName) -replace '<SEU_EMAIL_PIX>', 'seu_email@exemplo.com' |
    Set-Content $_.FullName
}
```

Não esqueça de fazer o mesmo no `youtube/README.md`, `youtube/DONATIVOS_E_PIX.md`
e `youtube/redes_sociais/`.
