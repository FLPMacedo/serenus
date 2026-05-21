"""
test_imprimir_lista.py — Testes do exportador da lista de compras
(PDF + texto/link WhatsApp).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _criar_itens_demo(banco):
    from views.compras_casa.casa_model import salvar_item
    salvar_item({
        "nome": "Arroz", "categoria": "Mercearia", "unidade": "kg",
        "marca": "Camil", "estoque_atual": 1.0, "estoque_minimo": 3.0,
    })
    salvar_item({
        "nome": "Detergente", "categoria": "Limpeza", "unidade": "un",
        "marca": "Ypê", "estoque_atual": 0.0, "estoque_minimo": 2.0,
    })


class TestFormatarTextoLista:
    def test_lista_vazia(self):
        from views.compras_casa.imprimir_lista import formatar_texto_lista
        texto = formatar_texto_lista([])
        assert "Nada precisa ser comprado" in texto

    def test_lista_com_itens(self, banco):
        from views.compras_casa.casa_model import listar_lista_compras
        from views.compras_casa.imprimir_lista import formatar_texto_lista
        _criar_itens_demo(banco)
        itens = listar_lista_compras()
        texto = formatar_texto_lista(itens)
        assert "Arroz" in texto
        assert "Camil" in texto
        assert "Detergente" in texto
        assert "Limpeza" in texto
        assert "Mercearia" in texto
        # Quantidade a comprar deve aparecer
        assert "comprar 2" in texto  # 3 - 1 = 2

    def test_titulo_padrao(self, banco):
        from views.compras_casa.casa_model import listar_lista_compras
        from views.compras_casa.imprimir_lista import formatar_texto_lista
        _criar_itens_demo(banco)
        texto = formatar_texto_lista(listar_lista_compras())
        assert "Lista de Compras" in texto


class TestGerarLinkWhatsapp:
    def test_link_basico(self):
        from views.compras_casa.imprimir_lista import gerar_link_whatsapp
        url = gerar_link_whatsapp("oi mundo")
        assert url.startswith("https://wa.me/")
        assert "oi%20mundo" in url

    def test_link_com_numero(self):
        from views.compras_casa.imprimir_lista import gerar_link_whatsapp
        url = gerar_link_whatsapp("oi", numero="(31) 99999-0000")
        # Só dígitos do número devem entrar
        assert "https://wa.me/31999990000?" in url

    def test_link_numero_sem_digitos(self):
        from views.compras_casa.imprimir_lista import gerar_link_whatsapp
        url = gerar_link_whatsapp("oi", numero="abc")
        assert url.startswith("https://wa.me/?")

    def test_caracteres_especiais_no_texto(self):
        from views.compras_casa.imprimir_lista import gerar_link_whatsapp
        url = gerar_link_whatsapp("• Arroz 2 kg\n• Feijão")
        # Quebras de linha viram %0A, bullet vira %E2%80%A2
        assert "%0A" in url


class TestImprimirListaPdf:
    def test_gera_arquivo_pdf(self, banco, tmp_path):
        from views.compras_casa.casa_model import listar_lista_compras
        from views.compras_casa.imprimir_lista import imprimir_lista_pdf
        _criar_itens_demo(banco)
        destino = tmp_path / "lista.pdf"
        imprimir_lista_pdf(listar_lista_compras(), destino)
        assert destino.exists()
        assert destino.stat().st_size > 0

    def test_pdf_assinatura(self, banco, tmp_path):
        from views.compras_casa.casa_model import listar_lista_compras
        from views.compras_casa.imprimir_lista import imprimir_lista_pdf
        _criar_itens_demo(banco)
        destino = tmp_path / "lista.pdf"
        imprimir_lista_pdf(listar_lista_compras(), destino)
        with destino.open("rb") as f:
            assert f.read(4) == b"%PDF"

    def test_pdf_lista_vazia_ok(self, banco, tmp_path):
        """Sem itens: PDF é gerado com mensagem positiva."""
        from views.compras_casa.imprimir_lista import imprimir_lista_pdf
        destino = tmp_path / "lista_vazia.pdf"
        imprimir_lista_pdf([], destino)
        assert destino.exists()

    def test_pdf_falha_preserva_anterior(self, banco, tmp_path, monkeypatch):
        """Mesma garantia atômica de imprimir_os: se pisa falhar, PDF
        anterior não é corrompido."""
        from views.compras_casa.casa_model import listar_lista_compras
        from views.compras_casa.imprimir_lista import imprimir_lista_pdf
        _criar_itens_demo(banco)

        destino = tmp_path / "lista.pdf"
        imprimir_lista_pdf(listar_lista_compras(), destino)
        bytes_orig = destino.read_bytes()

        from xhtml2pdf import pisa as pisa_real

        class _Fake:
            err = 1

        monkeypatch.setattr(pisa_real, "CreatePDF",
                             lambda h, dest, encoding=None: (
                                 dest.write(b"lixo"), _Fake())[1])

        with pytest.raises(RuntimeError):
            imprimir_lista_pdf(listar_lista_compras(), destino)

        assert destino.read_bytes() == bytes_orig
