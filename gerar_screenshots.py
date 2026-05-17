"""
gerar_screenshots.py — Captura uma imagem de cada tela do Serenus para o manual.

Uso:
    python gerar_screenshots.py

Como funciona:
1. Popula o banco com perfil de demonstração (para telas terem conteúdo)
2. Abre a MainWindow SEM mainloop
3. Navega para cada rota da sidebar
4. Aguarda o render (matplotlib precisa de tempo) e captura via PIL.ImageGrab
5. Salva em docs/screenshots/NN_nome.png

Requer um display ativo (Windows com sessão de desktop).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import ImageGrab

import database as db_module
from database import (
    inicializar_banco, salvar_configuracao,
)


OUTPUT = Path(__file__).parent / "docs" / "screenshots"
OUTPUT.mkdir(parents=True, exist_ok=True)

# Tempo para o widget terminar de renderizar (matplotlib precisa de mais)
WAIT_RAPIDO = 0.6
WAIT_GRAFICO = 1.4

# Rotas da sidebar (chave_navegacao, nome_arquivo, tempo_espera_extra)
ROTAS = [
    ("dashboard",      "01_inicio_dashboard.png",     WAIT_GRAFICO),
    ("receitas",       "02_minhas_receitas.png",      WAIT_RAPIDO),
    ("contas_pagar",   "03_contas_a_pagar.png",       WAIT_RAPIDO),
    ("vendas",         "04_vendas.png",               WAIT_RAPIDO),
    ("cartoes",        "05_cartoes.png",              WAIT_RAPIDO),
    ("dividas",        "06_gerenciamento_dividas.png", WAIT_GRAFICO),
    ("plano_contas",   "07_plano_de_contas.png",      WAIT_RAPIDO),
    ("visao_futura",   "08_visao_financeira.png",     WAIT_RAPIDO),
    ("fluxo_caixa",    "09_fluxo_de_caixa_extrato.png", WAIT_RAPIDO),
    ("investimentos",  "10_investimentos.png",        WAIT_GRAFICO),
    ("metas",          "11_metas.png",                WAIT_RAPIDO),
    ("backup",         "12_backup.png",               WAIT_RAPIDO),
    ("configuracoes",  "13_configuracoes.png",        WAIT_RAPIDO),
]


def _garantir_setup_e_demo() -> None:
    """Garante que o app está com setup completo e dados de demo carregados."""
    inicializar_banco()
    # Marca setup como completo (evita o wizard inicial)
    salvar_configuracao("usuario_nome", "Demonstração")
    salvar_configuracao("renda_mensal", "5000")
    salvar_configuracao("setup_completo", "1")
    salvar_configuracao("tema", "claro")
    # Garante que o modo ajuda esteja ligado para mostrar os banners no manual
    salvar_configuracao("modo_ajuda", "1")
    # Remove senha se houver (não queremos diálogo de login)
    try:
        from database import remover_senha
        remover_senha()
    except Exception:
        pass

    # Zera o banco antes para garantir estado limpo
    print("→ Zerando dados anteriores...")
    try:
        from database import zerar_dados
        zerar_dados()
    except Exception as e:
        print(f"  ! Falha ao zerar: {e}")

    # Repõe configurações pós-zeragem
    salvar_configuracao("usuario_nome", "Demonstração")
    salvar_configuracao("renda_mensal", "5000")
    salvar_configuracao("setup_completo", "1")
    salvar_configuracao("tema", "claro")
    salvar_configuracao("modo_ajuda", "1")

    # Popula com perfil rico (carteira consolidada de investimentos)
    print("→ Carregando dados de demonstração (Patrimônio Crescendo)...")
    from demo_manager import popular_modo_demo
    try:
        n = popular_modo_demo("patrimonio_crescendo")
        print(f"  {n} lançamentos carregados")
    except Exception as e:
        print(f"  ! Falha: {e}")

    # Adiciona vendas de exemplo (perfil "patrimonio_crescendo" não tem)
    print("→ Adicionando vendas de exemplo...")
    try:
        _adicionar_vendas_demo()
    except Exception as e:
        print(f"  ! Falha ao popular vendas: {e}")


def _adicionar_vendas_demo() -> None:
    """Cria produtos + vendas à vista e a prazo para a tela ficar rica."""
    from datetime import date, timedelta
    from views.vendas.venda_model import (
        salvar_produto, salvar_venda, listar_contas_receber, marcar_recebido,
    )

    salvar_produto({"nome": "Consultoria financeira (1h)",
                    "tipo": "servico", "preco": 250.00,
                    "descricao": "Sessão individual de consultoria"})
    salvar_produto({"nome": "Curso de educação financeira",
                    "tipo": "servico", "preco": 1200.00,
                    "descricao": "Curso completo (8 aulas)"})
    salvar_produto({"nome": "Planilha personalizada",
                    "tipo": "produto", "preco": 89.90,
                    "descricao": "Planilha Excel customizada"})

    hoje = date.today()
    dias = lambda n: (hoje - timedelta(days=n)).isoformat()

    # Vendas à vista (já pagas)
    salvar_venda(
        {"descricao": "Consultoria — João Silva",
         "data_venda": dias(5), "tipo_pagamento": "avista"},
        [{"descricao": "Consultoria financeira (1h)",
          "quantidade": 2, "preco_unit": 250.00}],
    )
    salvar_venda(
        {"descricao": "Planilha — Maria Souza",
         "data_venda": dias(12), "tipo_pagamento": "avista"},
        [{"descricao": "Planilha personalizada",
          "quantidade": 1, "preco_unit": 89.90}],
    )

    # Venda a prazo — gera contas a receber
    salvar_venda(
        {"descricao": "Curso — Pedro Alves",
         "data_venda": dias(20),
         "tipo_pagamento": "aprazo",
         "parcelas": 3,
         "data_primeira_parcela": dias(-10)},  # vence em 10 dias
        [{"descricao": "Curso de educação financeira",
          "quantidade": 1, "preco_unit": 1200.00}],
    )

    # Marca a primeira parcela como recebida (mostra status "parcial")
    pendentes = listar_contas_receber(status="pendente")
    if pendentes:
        marcar_recebido(pendentes[0].id, dias(2))


def _capturar_janela(app, destino: Path, wait: float) -> None:
    """Força render completo e captura a janela inteira."""
    app.update_idletasks()
    app.update()
    time.sleep(wait)
    app.update_idletasks()
    app.update()
    time.sleep(0.2)

    x  = app.winfo_rootx()
    y  = app.winfo_rooty()
    w  = app.winfo_width()
    h  = app.winfo_height()
    bbox = (x, y, x + w, y + h)
    img = ImageGrab.grab(bbox=bbox)
    img.save(destino, "PNG", optimize=True)


def main() -> int:
    _garantir_setup_e_demo()

    print(f"→ Saída: {OUTPUT}")
    from views.main_window import MainWindow
    app = MainWindow()

    # Dá tempo da janela aparecer e atualizar layout inicial
    app.update_idletasks()
    app.update()
    # Maximiza para capturas mais ricas
    try:
        app.state("zoomed")
    except Exception:
        pass
    app.update()
    time.sleep(0.8)

    for chave, arquivo, wait in ROTAS:
        destino = OUTPUT / arquivo
        try:
            print(f"  · {chave:<16} → {arquivo}")
            app._navegar(chave)
            _capturar_janela(app, destino, wait)
        except Exception as e:
            print(f"    ! Falhou em {chave}: {e}")

    app.destroy()
    print(f"\nFeito! {len(ROTAS)} telas em {OUTPUT}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
