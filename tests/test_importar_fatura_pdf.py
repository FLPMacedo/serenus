"""
test_importar_fatura_pdf.py — Testes do módulo de importação de fatura por PDF.

Cobertura por etapa:
  Etapa 1 — Classes de erro, pdf_tem_senha, extrair_texto_pdf
  Etapa 2 — Parser base + registry + detectar_layout
  Etapa 3 — Parser Nubank
  Etapa 4 — Parser Itaú
  Etapa 5 — Pipeline completo + salvar_como_xlsx + equivalência com Excel
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Fixtures (paths dos PDFs reais em faturas_modelos/)
# ---------------------------------------------------------------------------

_ROOT          = Path(__file__).parent.parent
_FATURAS_DIR   = _ROOT / "faturas_modelos"
_PDF_NUBANK    = _FATURAS_DIR / "Nubank_2026-05-16.pdf"
_PDF_VISA      = _FATURAS_DIR / "Fatura_VISA_100487777044_17-04-2026.pdf"
_PDF_MASTER    = _FATURAS_DIR / "Fatura_MASTERCARD_100260985621_17-04-2026.pdf"
_PDF_DESCONHEC = _FATURAS_DIR / "bl.422876104_41045582515_000104202602.04062026080300.temp.output.pdf"
_SENHA_ITAU    = "10544"


# ---------------------------------------------------------------------------
# Etapa 1 — Detecção de senha
# ---------------------------------------------------------------------------

class TestPdfTemSenha:
    def test_nubank_sem_senha(self):
        from views.cartoes.importar_fatura_pdf_model import pdf_tem_senha
        assert pdf_tem_senha(str(_PDF_NUBANK)) is False

    def test_visa_tem_senha(self):
        from views.cartoes.importar_fatura_pdf_model import pdf_tem_senha
        assert pdf_tem_senha(str(_PDF_VISA)) is True

    def test_mastercard_tem_senha(self):
        from views.cartoes.importar_fatura_pdf_model import pdf_tem_senha
        assert pdf_tem_senha(str(_PDF_MASTER)) is True

    def test_pdf_desconhecido_sem_senha(self):
        from views.cartoes.importar_fatura_pdf_model import pdf_tem_senha
        assert pdf_tem_senha(str(_PDF_DESCONHEC)) is False

    def test_arquivo_inexistente_levanta(self):
        from views.cartoes.importar_fatura_pdf_model import (
            PDFCorrompidoError, pdf_tem_senha,
        )
        with pytest.raises((FileNotFoundError, PDFCorrompidoError)):
            pdf_tem_senha("/caminho/que/nao/existe.pdf")

    def test_arquivo_corrompido_levanta(self, tmp_path):
        from views.cartoes.importar_fatura_pdf_model import (
            PDFCorrompidoError, pdf_tem_senha,
        )
        bad = tmp_path / "corrompido.pdf"
        bad.write_bytes(b"isto nao eh um PDF de verdade")
        with pytest.raises(PDFCorrompidoError):
            pdf_tem_senha(str(bad))


# ---------------------------------------------------------------------------
# Etapa 1 — Extração de texto
# ---------------------------------------------------------------------------

class TestExtrairTextoPdf:
    def test_nubank_extrai_texto_sem_senha(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        assert isinstance(texto, str)
        assert len(texto) > 100  # fatura tem mais que 100 chars
        # Deve mencionar "Nubank" em algum lugar
        assert "nubank" in texto.lower()

    def test_visa_extrai_texto_com_senha_correta(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        texto = extrair_texto_pdf(str(_PDF_VISA), senha=_SENHA_ITAU)
        assert isinstance(texto, str)
        assert len(texto) > 100

    def test_mastercard_extrai_texto_com_senha_correta(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        texto = extrair_texto_pdf(str(_PDF_MASTER), senha=_SENHA_ITAU)
        assert isinstance(texto, str)
        assert len(texto) > 100

    def test_visa_senha_errada_levanta(self):
        from views.cartoes.importar_fatura_pdf_model import (
            PDFSenhaIncorretaError, extrair_texto_pdf,
        )
        with pytest.raises(PDFSenhaIncorretaError):
            extrair_texto_pdf(str(_PDF_VISA), senha="senha_errada")

    def test_visa_sem_senha_quando_protegido_levanta(self):
        from views.cartoes.importar_fatura_pdf_model import (
            PDFSenhaIncorretaError, extrair_texto_pdf,
        )
        with pytest.raises(PDFSenhaIncorretaError):
            extrair_texto_pdf(str(_PDF_VISA), senha=None)

    def test_nubank_com_senha_ignora_senha_se_nao_for_protegido(self):
        """Passar senha pra PDF não protegido não deve falhar."""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        texto = extrair_texto_pdf(str(_PDF_NUBANK), senha="qualquer")
        assert len(texto) > 100

    def test_corrompido_levanta(self, tmp_path):
        from views.cartoes.importar_fatura_pdf_model import (
            PDFCorrompidoError, extrair_texto_pdf,
        )
        bad = tmp_path / "lixo.pdf"
        bad.write_bytes(b"%PDF-fake-1.4\nnao eh um PDF valido")
        with pytest.raises(PDFCorrompidoError):
            extrair_texto_pdf(str(bad))


# ---------------------------------------------------------------------------
# Etapa 1 — Classes de erro expostas no módulo
# ---------------------------------------------------------------------------

class TestClassesDeErro:
    def test_erros_existem_e_sao_exception(self):
        from views.cartoes.importar_fatura_pdf_model import (
            PDFCamposIncompletosError,
            PDFCorrompidoError,
            PDFLayoutDesconhecidoError,
            PDFSenhaIncorretaError,
        )
        for cls in (PDFSenhaIncorretaError, PDFCorrompidoError,
                    PDFLayoutDesconhecidoError, PDFCamposIncompletosError):
            assert issubclass(cls, Exception)
            inst = cls("mensagem teste")
            assert "mensagem teste" in str(inst)


# ---------------------------------------------------------------------------
# Etapa 2 — Parser base, registry e GenericoParser
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_pdfparser_e_abstrato(self):
        from views.cartoes.pdf_parsers.base import PDFParser
        with pytest.raises(TypeError):
            PDFParser()  # ABC não pode ser instanciado direto

    def test_generico_registrado_por_padrao(self):
        from views.cartoes.pdf_parsers import todos_parsers
        nomes = [p.nome_layout for p in todos_parsers()]
        assert "generico" in nomes

    def test_generico_e_ultimo_da_fila(self):
        from views.cartoes.pdf_parsers import todos_parsers
        parsers = todos_parsers()
        assert parsers[-1].nome_layout == "generico"

    def test_registrar_parser_insere_antes_do_generico(self):
        from views.cartoes.pdf_parsers import registrar, todos_parsers, _PARSERS
        from views.cartoes.pdf_parsers.base import PDFParser

        class FakeParser(PDFParser):
            nome_layout = "fake_test_only"
            def reconhece(self, texto): return False
            def extrair(self, texto):   return []

        try:
            registrar(FakeParser())
            parsers = todos_parsers()
            nomes = [p.nome_layout for p in parsers]
            assert nomes.index("fake_test_only") < nomes.index("generico")
        finally:
            # Limpa o estado
            _PARSERS[:] = [p for p in _PARSERS
                           if p.nome_layout != "fake_test_only"]

    def test_re_registrar_substitui_anterior(self):
        """Registrar 2x o mesmo nome_layout não deve duplicar."""
        from views.cartoes.pdf_parsers import registrar, todos_parsers, _PARSERS
        from views.cartoes.pdf_parsers.base import PDFParser

        class FakeV1(PDFParser):
            nome_layout = "fake_dup"
            def reconhece(self, texto): return False
            def extrair(self, texto):   return []

        class FakeV2(PDFParser):
            nome_layout = "fake_dup"
            def reconhece(self, texto): return True
            def extrair(self, texto):   return [{"a": 1}]

        try:
            registrar(FakeV1())
            registrar(FakeV2())
            parsers = todos_parsers()
            duplicados = [p for p in parsers if p.nome_layout == "fake_dup"]
            assert len(duplicados) == 1
        finally:
            _PARSERS[:] = [p for p in _PARSERS if p.nome_layout != "fake_dup"]


class TestDetectarLayout:
    def test_texto_qualquer_cai_em_generico(self):
        from views.cartoes.pdf_parsers import detectar_layout
        parser = detectar_layout("texto qualquer sem layout específico")
        assert parser.nome_layout == "generico"

    def test_detectar_em_texto_vazio_cai_em_generico(self):
        from views.cartoes.pdf_parsers import detectar_layout
        parser = detectar_layout("")
        assert parser.nome_layout == "generico"


class TestGenericoParser:
    def test_extrai_linha_data_descricao_valor_br(self):
        from views.cartoes.pdf_parsers.generico import GenericoParser
        texto = "01/05  PADARIA DO BAIRRO        45,80\n"
        itens = GenericoParser().extrair(texto)
        assert len(itens) == 1
        assert itens[0]["descricao"] == "PADARIA DO BAIRRO"
        assert itens[0]["valor"] == 45.80

    def test_extrai_com_simbolo_real(self):
        from views.cartoes.pdf_parsers.generico import GenericoParser
        texto = "12/03  AMAZON BR        R$ 199,90"
        itens = GenericoParser().extrair(texto)
        assert len(itens) == 1
        assert itens[0]["valor"] == 199.90

    def test_extrai_valor_com_milhar(self):
        from views.cartoes.pdf_parsers.generico import GenericoParser
        texto = "05/04  GELADEIRA INOX     2.499,00"
        itens = GenericoParser().extrair(texto)
        assert len(itens) == 1
        assert itens[0]["valor"] == 2499.00

    def test_ignora_linhas_sem_padrao(self):
        from views.cartoes.pdf_parsers.generico import GenericoParser
        itens = GenericoParser().extrair("Texto qualquer sem data nem valor")
        assert itens == []

    def test_schema_de_saida_completo(self):
        from views.cartoes.pdf_parsers.generico import GenericoParser
        itens = GenericoParser().extrair("01/05 LOJA TESTE 100,00")
        assert len(itens) == 1
        assert set(itens[0].keys()) == {
            "descricao", "estabelecimento", "categoria", "parcela", "valor",
        }

    def test_extrai_multiplas_linhas(self):
        from views.cartoes.pdf_parsers.generico import GenericoParser
        texto = (
            "01/05  PADARIA DO BAIRRO       45,80\n"
            "02/05  POSTO SHELL            120,00\n"
            "03/05  NETFLIX                 39,90\n"
        )
        itens = GenericoParser().extrair(texto)
        assert len(itens) == 3
        valores = sorted(i["valor"] for i in itens)
        assert valores == [39.90, 45.80, 120.00]

    def test_generico_em_pdf_real_extrai_algo(self):
        """Sanity: rodar o genérico no PDF do Nubank deve achar pelo menos
        algumas linhas (mesmo que não seja o parser ideal pra esse layout)."""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.generico import GenericoParser
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        itens = GenericoParser().extrair(texto)
        # Não exigimos N específico (será refinado em parsers concretos),
        # mas o genérico não pode retornar 0 num PDF real de fatura.
        assert len(itens) > 0
