# Apertado (Renda baixa / muitos cartões)

Chave: `apertado`

Arquivos gerados automaticamente por `demo_manager_arquivos`.
Para popular o sistema com este perfil:
```python
from demo_manager import popular_modo_demo
popular_modo_demo('apertado')
```

## Arquivos

- `cartoes/` — faturas XLSX importáveis (1 por cartão x mês)
- `extratos/` — extratos bancários CSV e OFX (Nubank-like)
