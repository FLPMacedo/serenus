"""
gerar_screenshots_modais.py — Captura os 14 modais de lançamento do Serenus
para uso no playbook.

Para cada modal:
1. Navega para a view pai
2. Instancia o modal e pré-preenche os campos com dados de exemplo
3. Aguarda o render terminar
4. Captura a bbox do Toplevel via PIL.ImageGrab
5. Destrói o modal

Saída: docs/screenshots/modais/NN_nome.png
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from datetime import date, timedelta

from PIL import ImageGrab

import database as db_module
from database import salvar_configuracao

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


OUTPUT = Path(__file__).parent / "docs" / "screenshots" / "modais"
OUTPUT.mkdir(parents=True, exist_ok=True)

WAIT = 0.7


def _preparar_banco():
    """Zera o banco e popula com dados ricos para os modais funcionarem."""
    from database import inicializar_banco, zerar_dados
    inicializar_banco()
    try:
        zerar_dados()
    except Exception:
        pass
    salvar_configuracao("usuario_nome", "Demonstração")
    salvar_configuracao("setup_completo", "1")
    salvar_configuracao("tema", "claro")
    salvar_configuracao("modo_ajuda", "1")
    salvar_configuracao("renda_mensal", "5000")

    from demo_manager import popular_modo_demo
    popular_modo_demo("patrimonio_crescendo")

    # Cria 1 cartão extra para o form de "Despesa no cartão"
    from views.cartoes.cartao_model import salvar_cartao, listar_cartoes
    if not listar_cartoes():
        salvar_cartao({
            "nome": "Nubank Roxo", "banco": "nubank", "bandeira": "master",
            "ultimos_digitos": "1234", "limite": 5000.0,
            "limite_disponivel": 5000.0,
            "dia_vencimento": 10, "dia_fechamento": 3,
        })

    # Cria pelo menos 1 venda a prazo com parcela pendente
    from views.vendas.venda_model import salvar_venda, listar_contas_receber
    if not listar_contas_receber(status="pendente"):
        hoje = date.today()
        salvar_venda(
            {"descricao": "Curso de educação financeira — Pedro Alves",
             "data_venda": hoje.isoformat(),
             "tipo_pagamento": "aprazo",
             "parcelas": 3,
             "data_primeira_parcela":
                (hoje + timedelta(days=10)).isoformat()},
            [{"descricao": "Curso completo (8 aulas)",
              "quantidade": 1, "preco_unit": 1200.0}],
        )


def _capturar(modal, destino: Path, *, wait: float = WAIT) -> None:
    """Espera o render e captura a bbox do Toplevel."""
    # Múltiplos updates espaçados para garantir que o layout estabilizou
    # (especialmente importante quando o modal contém scroll, preview ao vivo
    # ou frames que se expandem dinamicamente)
    for _ in range(3):
        modal.update_idletasks()
        modal.update()
        time.sleep(wait / 3)

    try:
        modal.lift()
        modal.update()
    except Exception:
        pass

    # Bbox final: usa a geometria solicitada se for maior que a renderizada
    # (alguns modais com geometry("WxH") não terminam de redimensionar a tempo)
    x = modal.winfo_rootx()
    y = modal.winfo_rooty()
    w = modal.winfo_width()
    h = modal.winfo_height()

    # Tenta extrair a geometria solicitada via .geometry()
    try:
        geo = modal.geometry()  # ex.: "740x560+100+50"
        parts = geo.split("+")[0].split("x")
        if len(parts) == 2:
            wg, hg = int(parts[0]), int(parts[1])
            w = max(w, wg)
            h = max(h, hg)
    except Exception:
        pass

    if w < 100 or h < 100:
        raise RuntimeError(f"Tamanho inválido: {w}x{h}")

    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    img.save(destino, "PNG", optimize=True)


def _fechar(modal) -> None:
    try:
        modal.grab_release()
    except Exception:
        pass
    try:
        modal.destroy()
    except Exception:
        pass


# ───────────────────────────────────────────────────────────────────────────────
# Definição dos modais (ordem que aparecerá no playbook)
# ───────────────────────────────────────────────────────────────────────────────


def modal_01_nova_despesa(app):
    """Lançamento de despesa simples (Contas a Pagar → + Nova despesa)."""
    app._navegar("contas_pagar")
    from views.contas_pagar.form_view import ContaPagarFormModal
    modal = ContaPagarFormModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    # Preenche
    modal._entry_desc.insert(0, "Conta de luz — Maio/2026")
    modal._entry_valor.delete(0, "end")
    modal._entry_valor.insert(0, "289,40")
    modal._entry_venc.delete(0, "end")
    modal._entry_venc.insert(0, date.today().strftime("15/%m/%Y"))
    try:
        modal._combo_conta.set("Luz / Energia elétrica")
    except Exception:
        pass
    return modal


def modal_02_despesa_no_cartao(app):
    """Despesa parcelada no cartão (mesmo modal, marcando 'Pagar com cartão')."""
    app._navegar("contas_pagar")
    from views.contas_pagar.form_view import ContaPagarFormModal
    modal = ContaPagarFormModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    modal._entry_desc.insert(0, "Notebook Dell Inspiron")
    modal._entry_valor.delete(0, "end")
    modal._entry_valor.insert(0, "3.500,00")
    modal._entry_venc.delete(0, "end")
    modal._entry_venc.insert(0, date.today().strftime("10/%m/%Y"))
    try:
        modal._combo_conta.set("Pessoal")
    except Exception:
        pass
    try:
        modal._recorrente_var.set(False)
    except Exception:
        pass
    # Marca pagar com cartão e expande o frame
    modal._cartao_var.set(True)
    try:
        modal._on_cartao_toggle()
    except Exception:
        pass
    modal.update()
    try:
        modal._combo_parc.set("12")
    except Exception:
        pass
    # Aumenta a altura para mostrar a seção de cartão expandida
    try:
        modal.resizable(True, True)
        modal.geometry("560x820")
    except Exception:
        pass
    modal.update_idletasks()
    return modal


def modal_03_nova_fonte_receita(app):
    """Cadastro de fonte de renda (Minhas Receitas → + Nova fonte)."""
    app._navegar("receitas")
    from views.receitas.receita_view import FonteFormModal
    modal = FonteFormModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    # Tenta preencher campos
    for attr, valor in [
        ("_entry_nome", "Salário Empresa X"),
        ("_entry_valor", "8.500,00"),
        ("_entry_dia", "5"),
    ]:
        if hasattr(modal, attr):
            w = getattr(modal, attr)
            try:
                w.delete(0, "end"); w.insert(0, valor)
            except Exception:
                pass
    if hasattr(modal, "_combo_tipo"):
        try:
            modal._combo_tipo.set("CLT")
        except Exception:
            pass
    return modal


def modal_04_nova_receita_especial(app):
    """Receita pontual (13º, férias, bônus)."""
    app._navegar("receitas")
    from views.receitas.receita_view import EspecialFormModal
    modal = EspecialFormModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    for attr, valor in [
        ("_entry_nome", "Restituição IR 2026"),
        ("_entry_valor", "2.400,00"),
    ]:
        if hasattr(modal, attr):
            w = getattr(modal, attr)
            try:
                w.delete(0, "end"); w.insert(0, valor)
            except Exception:
                pass
    return modal


def modal_05_novo_cartao(app):
    """Cadastro de cartão (Cartões → + Novo Cartão)."""
    app._navegar("cartoes")
    from views.cartoes.form_cartao import FormCartao
    modal = FormCartao(app, on_salvo=lambda *a, **k: None)
    modal.update()
    # Força altura maior para mostrar todo o form (o original é 740x560)
    try:
        modal.resizable(True, True)
        modal.geometry("980x720")
    except Exception:
        pass
    # Preenche para mostrar preview ao vivo
    modal._entry_nome.insert(0, "Inter Black")
    modal._entry_digitos.insert(0, "7890")
    modal._entry_limite.delete(0, "end")
    modal._entry_limite.insert(0, "15.000,00")
    modal._entry_vencimento.insert(0, "20")
    modal._entry_fechamento.insert(0, "13")
    try:
        modal._combo_banco.set("Banco Inter")
        modal._combo_bandeira.set("Mastercard")
        modal._atualizar_preview()
    except Exception:
        pass
    return modal


def modal_06_lancar_compra(app):
    """Lançar compra parcelada num cartão."""
    app._navegar("cartoes")
    from views.cartoes.form_compra import FormCompra
    from views.cartoes.cartao_model import listar_cartoes
    cartoes = listar_cartoes(apenas_ativos=True)
    cartao = cartoes[0] if cartoes else None
    modal = FormCompra(app, on_salvo=lambda *a, **k: None, cartao=cartao)
    modal.update()
    modal._entry_desc.insert(0, "Smartphone Galaxy S24")
    modal._entry_estab.insert(0, "Magazine Luiza")
    modal._entry_valor.delete(0, "end")
    modal._entry_valor.insert(0, "4.800,00")
    try:
        modal._combo_cat.set("Pessoal")
        modal._combo_parc.set("12")
    except Exception:
        pass
    return modal


def modal_07_importar_fatura(app):
    """Modal de importação de fatura CSV/XLSX."""
    app._navegar("cartoes")
    from views.cartoes.importar_fatura_modal import ImportarFaturaModal
    modal = ImportarFaturaModal(app, on_importado=lambda *a, **k: None)
    modal.update()
    return modal


def modal_08_novo_produto(app):
    """Cadastro de produto/serviço."""
    app._navegar("vendas")
    from views.vendas.form_produto import FormProdutoModal
    modal = FormProdutoModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    for attr, valor in [
        ("_e_nome", "Consultoria financeira (1h)"),
        ("_e_preco", "250,00"),
        ("_e_desc", "Sessão individual de consultoria financeira pessoal"),
    ]:
        if hasattr(modal, attr):
            w = getattr(modal, attr)
            try:
                w.delete(0, "end"); w.insert(0, valor)
            except Exception:
                pass
    if hasattr(modal, "_combo_tipo"):
        try:
            modal._combo_tipo.set("Serviço")
        except Exception:
            pass
    return modal


def modal_09_nova_venda(app):
    """Modal de nova venda (à vista)."""
    app._navegar("vendas")
    from views.vendas.form_venda import FormVendaModal
    modal = FormVendaModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    modal._e_desc.insert(0, "Consultoria — João Silva")
    modal._e_data.delete(0, "end")
    modal._e_data.insert(0, date.today().strftime("%d/%m/%Y"))
    modal._e_obs.insert(0, "Pago em PIX")
    # Adiciona um item se possível
    try:
        if hasattr(modal, "_adicionar_item"):
            modal._adicionar_item()
            modal.update()
            # Tenta preencher o primeiro item
            if modal._itens_rows:
                row = modal._itens_rows[0]
                if "desc" in row:
                    row["desc"].insert(0, "Consultoria financeira (1h)")
                if "qtd" in row:
                    row["qtd"].delete(0, "end"); row["qtd"].insert(0, "2")
                if "preco" in row:
                    row["preco"].delete(0, "end"); row["preco"].insert(0, "250,00")
                modal._recalcular_totais() if hasattr(modal, "_recalcular_totais") else None
    except Exception:
        pass
    return modal


def modal_10_venda_a_prazo(app):
    """Mesmo modal, mas em modo a prazo."""
    app._navegar("vendas")
    from views.vendas.form_venda import FormVendaModal
    modal = FormVendaModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    modal._e_desc.insert(0, "Curso completo — Pedro Alves")
    modal._e_data.delete(0, "end")
    modal._e_data.insert(0, date.today().strftime("%d/%m/%Y"))
    # Marca como a prazo
    try:
        if hasattr(modal, "_var_tipo"):
            modal._var_tipo.set("aprazo")
            if hasattr(modal, "_on_tipo_change"):
                modal._on_tipo_change()
        modal.update()
        if hasattr(modal, "_e_parcelas"):
            modal._e_parcelas.delete(0, "end")
            modal._e_parcelas.insert(0, "3")
        if hasattr(modal, "_e_data_p1"):
            modal._e_data_p1.delete(0, "end")
            modal._e_data_p1.insert(0,
                (date.today() + timedelta(days=10)).strftime("%d/%m/%Y"))
    except Exception:
        pass
    return modal


def modal_11_marcar_recebimento(app):
    """Modal de confirmação de recebimento de parcela."""
    app._navegar("vendas")
    from views.vendas.venda_model import listar_contas_receber
    from views.vendas.form_recebimento import FormRecebimentoModal
    pendentes = listar_contas_receber(status="pendente")
    if not pendentes:
        raise RuntimeError("Sem contas a receber pendentes")
    conta = pendentes[0]
    modal = FormRecebimentoModal(app, on_salvo=lambda *a, **k: None,
                                  conta=conta)
    modal.update()
    return modal


def modal_12_nova_divida(app):
    """Modal de nova dívida."""
    app._navegar("dividas")
    from views.visao_longo_prazo.dividas_view import DividaFormModal
    modal = DividaFormModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    for attr, valor in [
        ("_entry_nome", "Empréstimo pessoal Banco X"),
        ("_entry_saldo", "12.000,00"),
        ("_entry_parcela", "550,00"),
        ("_entry_total_parc", "24"),
        ("_entry_pagas", "4"),
        ("_entry_dia_venc", "10"),
        ("_entry_juros", "3,5"),
    ]:
        if hasattr(modal, attr):
            w = getattr(modal, attr)
            try:
                w.delete(0, "end"); w.insert(0, valor)
            except Exception:
                pass
    if hasattr(modal, "_combo_tipo"):
        try:
            modal._combo_tipo.set("Empréstimo")
        except Exception:
            pass
    return modal


def modal_13_nova_movimentacao_invest(app):
    """Modal de nova movimentação de investimento (compra de ação)."""
    app._navegar("investimentos")
    from views.investimentos.form_movimentacao import FormMovimentacaoModal
    modal = FormMovimentacaoModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    modal._e_data.delete(0, "end")
    modal._e_data.insert(0, date.today().strftime("%d/%m/%Y"))
    modal._e_qtd.insert(0, "100")
    modal._e_preco.insert(0, "32,50")
    modal._e_bruto.insert(0, "3.250,00")
    modal._e_taxas.insert(0, "5,00")
    try:
        modal._combo_tipo.set("Compra")
    except Exception:
        pass
    return modal


def modal_15_nova_os(app):
    """Modal de nova Ordem de Serviço (preenchida com exemplo realista)."""
    from views.os.form_os import FormOSModal
    from views.vendas.venda_model import salvar_produto, listar_produtos

    # Garante 1+ produto para o combo de materiais
    if not listar_produtos(apenas_ativos=True):
        salvar_produto({"nome": "Lâmpada LED 9W", "tipo": "produto",
                        "preco": 15.90, "descricao": "", "ativo": True})

    app._navegar("os")
    modal = FormOSModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    # Preenche
    modal._e_solic_nome.insert(0, "Maria Souza")
    modal._e_solic_setor.insert(0, "Recursos Humanos")
    modal._e_solic_ramal.insert(0, "2055")
    modal._e_hora_solic.insert(0, "10:30")
    modal._t_descricao.insert("1.0",
        "Trocar lâmpadas queimadas na sala de reuniões (3 unidades) "
        "e verificar o cabeamento HDMI do projetor.")
    modal._e_responsavel.insert(0, "Carlos Mendes")
    modal._e_valor_hora.delete(0, "end")
    modal._e_valor_hora.insert(0, "65,00")
    modal._e_horas.insert(0, "1,5")
    # Adiciona linha de item
    try:
        modal._add_item_row({
            "produto_id": None, "descricao": "Lâmpada LED 9W",
            "quantidade": 3.0, "preco_unit": 15.90,
            "observacao": "Sala 3º andar",
        })
        modal._atualizar_totais()
    except Exception:
        pass
    modal.update_idletasks()
    return modal


def modal_14_nova_meta(app):
    """Modal de nova meta financeira."""
    app._navegar("metas")
    from views.metas.metas_view import _FormMetaModal
    modal = _FormMetaModal(app, on_salvo=lambda *a, **k: None)
    modal.update()
    for attr, valor in [
        ("_e_nome", "Viagem Europa (família)"),
        ("_e_alvo", "60.000,00"),
        ("_e_atual", "12.500,00"),
        ("_e_prazo",
         (date.today() + timedelta(days=540)).strftime("%d/%m/%Y")),
        ("_e_desc", "Viagem em julho de 2027 — Itália, França e Portugal"),
    ]:
        if hasattr(modal, attr):
            w = getattr(modal, attr)
            try:
                w.delete(0, "end"); w.insert(0, valor)
            except Exception:
                pass
    return modal


# Lista ordenada para iteração
MODAIS = [
    ("01_nova_despesa.png",            modal_01_nova_despesa),
    ("02_despesa_no_cartao.png",       modal_02_despesa_no_cartao),
    ("03_nova_fonte_receita.png",      modal_03_nova_fonte_receita),
    ("04_nova_receita_especial.png",   modal_04_nova_receita_especial),
    ("05_novo_cartao.png",             modal_05_novo_cartao),
    ("06_lancar_compra_cartao.png",    modal_06_lancar_compra),
    ("07_importar_fatura.png",         modal_07_importar_fatura),
    ("08_novo_produto.png",            modal_08_novo_produto),
    ("09_nova_venda_avista.png",       modal_09_nova_venda),
    ("10_nova_venda_aprazo.png",       modal_10_venda_a_prazo),
    ("11_marcar_recebimento.png",      modal_11_marcar_recebimento),
    ("12_nova_divida.png",             modal_12_nova_divida),
    ("13_nova_movimentacao_invest.png", modal_13_nova_movimentacao_invest),
    ("14_nova_meta.png",               modal_14_nova_meta),
    ("15_nova_os.png",                 modal_15_nova_os),
]


def main() -> int:
    _preparar_banco()
    print(f"→ Saída: {OUTPUT}")
    from views.main_window import MainWindow
    app = MainWindow()
    app.update_idletasks(); app.update()
    try:
        app.state("zoomed")
    except Exception:
        pass
    app.update()
    time.sleep(0.6)

    sucesso = 0
    for arquivo, func in MODAIS:
        destino = OUTPUT / arquivo
        try:
            print(f"  · {func.__name__:<40} → {arquivo}")
            modal = func(app)
            _capturar(modal, destino)
            _fechar(modal)
            app.update()
            sucesso += 1
        except Exception as e:
            print(f"    ! Falhou: {type(e).__name__}: {e}")

    app.destroy()
    print(f"\n{sucesso}/{len(MODAIS)} modais capturados em {OUTPUT}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
