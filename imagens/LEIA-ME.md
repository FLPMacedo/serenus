# Logos de Bandeiras de Cartão

Coloque os arquivos PNG nesta pasta com os nomes exatos abaixo.
O sistema carrega automaticamente a imagem quando o arquivo existir.

## Arquivos esperados

| Bandeira         | Nome do arquivo    | Situação     |
|------------------|--------------------|--------------|
| Visa             | `visa.png`         | ✅ presente  |
| Mastercard       | `mastercad.png`    | ✅ presente  |
| Elo              | `elo.png`          | ⬜ ausente   |
| American Express | `amex.png`         | ⬜ ausente   |
| Hipercard        | `hipercard.png`    | ⬜ ausente   |
| Cabal            | `cabal.png`        | ⬜ ausente   |
| Diners Club      | `diners.png`       | ⬜ ausente   |
| Discover         | `discover.png`     | ⬜ ausente   |
| Hiper            | `hiper.png`        | ⬜ ausente   |
| Banescard        | `banescard.png`    | ⬜ ausente   |

## Para ativar um logo ausente

1. Coloque o arquivo PNG aqui com o nome exato da tabela acima.
2. Abra `views/cartoes/cartao_model.py` e descomente a linha correspondente em `BANDEIRAS_IMAGENS`:

```python
BANDEIRAS_IMAGENS: dict[str, str] = {
    "visa":      "visa.png",
    "master":    "mastercad.png",
    # "elo":     "elo.png",       ← remova o # desta linha
    # "amex":    "amex.png",
    # ...
}
```

## Para bandeiras customizadas

Bandeiras cadastradas pelo formulário ("✏ + Nova bandeira...") ficam salvas no banco.
Se quiser adicionar um logo para uma bandeira customizada, basta:

1. Colocar o PNG aqui com qualquer nome (ex: `minha_bandeira.png`)
2. Adicionar a entrada em `BANDEIRAS_IMAGENS` em `cartao_model.py`:

```python
"minha_bandeira": "minha_bandeira.png",
```

## Dicas para os arquivos PNG

- Fundo **transparente** (PNG com canal alfa) fica melhor sobre qualquer cor de cartão
- Tamanho recomendado: **200 × 130 px** ou maior (o sistema redimensiona para ~58 × 36 px)
- Logos oficiais em alta resolução estão disponíveis nos sites das bandeiras (seção imprensa / brand guidelines)
