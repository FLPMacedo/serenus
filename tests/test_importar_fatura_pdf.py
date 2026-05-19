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
