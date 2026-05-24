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
# Os PDFs Itaú VISA/MASTERCARD originais (nominais separados, ambos com
# senha 10544) foram substituídos por um Fatura_ItauUniclass.pdf SEM
# senha. Os apontadores ficam aqui pra quando os PDFs originais voltarem,
# mas os testes que dependem das características antigas (presença de
# senha, contagem ≥9 itens, presença de Spotify) ficam @skipif. Esses
# testes voltam a rodar automaticamente quando os PDFs forem repostos.
_PDF_VISA      = _FATURAS_DIR / "Fatura_ItauUniclass.pdf"
_PDF_MASTER    = _FATURAS_DIR / "Fatura_ItauUniclass.pdf"
# PDF "desconhecido" (não-Itaú/Nubank) — usado pra testar o fallback do
# detectar_layout. Magalu serve esse propósito porque o ItauParser não
# casa com ele.
_PDF_DESCONHEC = _FATURAS_DIR / "Fatura_Magazine_Luiza.pdf"
_SENHA_ITAU    = "10544"


# Detecta dinamicamente se o PDF VISA/Itaú atualmente disponível é o
# original (com senha) ou o substituto Fatura_ItauUniclass.pdf (sem senha).
# Usado pra @skipif nos testes que assumem características do original.
def _pdf_visa_e_o_original() -> bool:
    """True se o PDF VISA tem senha (= é o original VISA/MASTERCARD).
    False se for o substituto ItauUniclass (sem senha, 4 itens só)."""
    try:
        from views.cartoes.importar_fatura_pdf_model import pdf_tem_senha
        return pdf_tem_senha(str(_PDF_VISA))
    except Exception:
        return False


_VISA_ORIGINAL = _pdf_visa_e_o_original()
_SKIP_MSG = (
    "PDF VISA/MASTERCARD original substituído por Fatura_ItauUniclass.pdf "
    "(sem senha, 4 itens). Teste volta a rodar quando o original retornar."
)

# Lista de PDFs novos disponíveis para a revisão de parsers que o usuário
# vai pedir em momento oportuno. Mantidos aqui pra referência rápida.
# A coluna XLSX indica se já existe saída anterior do pipeline PDF→XLSX
# em faturas_modelos/ (= parser já foi rodado contra este PDF antes;
# pode ser uma das 2 saídas com valores acima do total que o usuário
# mencionou).
#
#   PDF                              | XLSX prévio | Status
#   ---------------------------------+-------------+----------------------
#   Fatura_Credicard.pdf             | não         | não avaliado
#   Fatura_Digio.pdf                 | sim         | avaliado, conferir
#   Fatura_ItauUniclass.pdf          | sim         | avaliado, conferir
#   Fatura_Magazine_Luiza.pdf        | sim         | avaliado, conferir
#   Fatura_Will.pdf                  | sim         | avaliado, conferir
#   _Fatura Telefone Vivo.pdf        | não         | não avaliado
#   _Fatura_Mercado_Livre.pdf        | sim         | avaliado, conferir
#   Nubank_2026-05-16.pdf            | sim         | avaliado, conferir


# ---------------------------------------------------------------------------
# Etapa 1 — Detecção de senha
# ---------------------------------------------------------------------------

class TestPdfTemSenha:
    def test_nubank_sem_senha(self):
        from views.cartoes.importar_fatura_pdf_model import pdf_tem_senha
        assert pdf_tem_senha(str(_PDF_NUBANK)) is False

    @pytest.mark.skipif(not _VISA_ORIGINAL, reason=_SKIP_MSG)
    def test_visa_tem_senha(self):
        from views.cartoes.importar_fatura_pdf_model import pdf_tem_senha
        assert pdf_tem_senha(str(_PDF_VISA)) is True

    @pytest.mark.skipif(not _VISA_ORIGINAL, reason=_SKIP_MSG)
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

    @pytest.mark.skipif(not _VISA_ORIGINAL, reason=_SKIP_MSG)
    def test_visa_senha_errada_levanta(self):
        from views.cartoes.importar_fatura_pdf_model import (
            PDFSenhaIncorretaError, extrair_texto_pdf,
        )
        with pytest.raises(PDFSenhaIncorretaError):
            extrair_texto_pdf(str(_PDF_VISA), senha="senha_errada")

    @pytest.mark.skipif(not _VISA_ORIGINAL, reason=_SKIP_MSG)
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


# ---------------------------------------------------------------------------
# Etapa 3 — Parser Nubank
# ---------------------------------------------------------------------------

class TestNubankParser:
    def test_reconhece_pdf_nubank_real(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.nubank import NubankParser
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        assert NubankParser().reconhece(texto) is True

    def test_nao_reconhece_texto_aleatorio(self):
        from views.cartoes.pdf_parsers.nubank import NubankParser
        assert NubankParser().reconhece("texto qualquer sem indicio") is False

    def test_nao_reconhece_fatura_itau(self):
        """Garante que o parser Nubank não dá falso positivo em PDF Itaú."""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.nubank import NubankParser
        texto = extrair_texto_pdf(str(_PDF_VISA), senha=_SENHA_ITAU)
        assert NubankParser().reconhece(texto) is False

    def test_extrai_itens_do_pdf_real(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.nubank import NubankParser
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        itens = NubankParser().extrair(texto)
        # Pelo menos 5 transações positivas (a fatura tem ~26)
        assert len(itens) >= 5, f"esperava >=5 itens, achou {len(itens)}"

    def test_extrai_netflix(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.nubank import NubankParser
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        itens = NubankParser().extrair(texto)
        netflix = [i for i in itens if "netflix" in i["descricao"].lower()]
        assert len(netflix) >= 1
        assert netflix[0]["valor"] == pytest.approx(44.90)

    def test_captura_parcela_multilinha(self):
        """Transações parceladas vêm em multi-linha: data → descrição
        com 'Parcela N/M' → linha de detalhes → valor isolado."""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.nubank import NubankParser
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        itens = NubankParser().extrair(texto)
        parceladas = [i for i in itens if i.get("parcela", "")]
        assert len(parceladas) >= 1, "nenhuma transação parcelada capturada"
        # Pelo menos uma das parcelas deve ter formato N/M
        formatos = [i["parcela"] for i in parceladas]
        import re
        assert any(re.match(r"^\d+/\d+$", p) for p in formatos), \
            f"nenhum no formato N/M: {formatos}"

    def test_ignora_pagamentos_negativos(self):
        """Linhas '−R$ X' (U+2212) são pagamentos/créditos — pular."""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.nubank import NubankParser
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        itens = NubankParser().extrair(texto)
        for i in itens:
            assert i["valor"] > 0, f"valor não positivo: {i}"
        descs = " | ".join(i["descricao"].lower() for i in itens)
        assert "pagamento em" not in descs

    def test_schema_completo_em_todos_itens(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.nubank import NubankParser
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        itens = NubankParser().extrair(texto)
        chaves = {"descricao", "estabelecimento", "categoria", "parcela", "valor"}
        for i in itens:
            assert set(i.keys()) == chaves

    def test_detectado_pelo_registry(self):
        """Após o parser ser registrado, detectar_layout deve devolvê-lo
        pra um PDF Nubank (não cair no genérico)."""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers import detectar_layout
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        parser = detectar_layout(texto)
        assert parser.nome_layout == "nubank"


# ---------------------------------------------------------------------------
# Etapa 4 — Parser Itaú (VISA + MASTERCARD)
# ---------------------------------------------------------------------------

class TestItauParser:
    def test_reconhece_visa(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        texto = extrair_texto_pdf(str(_PDF_VISA), senha=_SENHA_ITAU)
        assert ItauParser().reconhece(texto) is True

    def test_reconhece_mastercard(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        texto = extrair_texto_pdf(str(_PDF_MASTER), senha=_SENHA_ITAU)
        assert ItauParser().reconhece(texto) is True

    def test_nao_reconhece_nubank(self):
        """Garante que o parser Itaú não dá falso positivo em PDF Nubank,
        mesmo com 'ITAU UNIBANCO' aparecendo como estabelecimento."""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        texto = extrair_texto_pdf(str(_PDF_NUBANK))
        assert ItauParser().reconhece(texto) is False

    def test_extrai_itens_visa(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        texto = extrair_texto_pdf(str(_PDF_VISA), senha=_SENHA_ITAU)
        itens = ItauParser().extrair(texto)
        # VISA tem 4 lançamentos em "produtos e serviços"
        assert len(itens) >= 4, f"esperava >=4 itens, achou {len(itens)}"

    @pytest.mark.skipif(not _VISA_ORIGINAL, reason=_SKIP_MSG)
    def test_extrai_itens_mastercard(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        texto = extrair_texto_pdf(str(_PDF_MASTER), senha=_SENHA_ITAU)
        itens = ItauParser().extrair(texto)
        # MASTERCARD tem 5 (compras+saques) + 4 (produtos+serviços) = 9
        assert len(itens) >= 9, f"esperava >=9 itens, achou {len(itens)}"

    @pytest.mark.skipif(not _VISA_ORIGINAL, reason=_SKIP_MSG)
    def test_extrai_spotify_mastercard(self):
        """13/03 DM*SpotifySAO PAULOBRA 12,90"""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        texto = extrair_texto_pdf(str(_PDF_MASTER), senha=_SENHA_ITAU)
        itens = ItauParser().extrair(texto)
        sp = [i for i in itens if "spotify" in i["descricao"].lower()]
        assert len(sp) >= 1
        assert sp[0]["valor"] == pytest.approx(12.90)

    def test_extrai_parcela_visa(self):
        """VISA tem parcelas no formato '05/12', '05/11', '03/04', '02/04'."""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        texto = extrair_texto_pdf(str(_PDF_VISA), senha=_SENHA_ITAU)
        itens = ItauParser().extrair(texto)
        parc = [i for i in itens if i["parcela"]]
        assert len(parc) >= 4, "VISA deve ter pelo menos 4 parceladas"

    def test_ignora_pagamentos_negativos(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        for pdf in (_PDF_VISA, _PDF_MASTER):
            texto = extrair_texto_pdf(str(pdf), senha=_SENHA_ITAU)
            itens = ItauParser().extrair(texto)
            for i in itens:
                assert i["valor"] > 0, f"valor não positivo em {pdf.name}: {i}"
            descs = " | ".join(i["descricao"].lower() for i in itens)
            assert "pagamento" not in descs

    def test_nao_inclui_proximas_faturas(self):
        """Linhas em 'Compras parceladas - próximas faturas' devem ser puladas
        (são projeções, não lançamentos da fatura atual)."""
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        texto = extrair_texto_pdf(str(_PDF_VISA), senha=_SENHA_ITAU)
        itens = ItauParser().extrair(texto)
        # VISA: 4 produtos atuais + 4 próximos = não pode ter 8+
        # Parser deve trazer só os 4 atuais
        assert len(itens) <= 6, \
            f"parser está incluindo próximas faturas (len={len(itens)})"

    def test_schema_completo(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers.itau import ItauParser
        texto = extrair_texto_pdf(str(_PDF_MASTER), senha=_SENHA_ITAU)
        itens = ItauParser().extrair(texto)
        chaves = {"descricao", "estabelecimento", "categoria", "parcela", "valor"}
        for i in itens:
            assert set(i.keys()) == chaves

    def test_detectado_pelo_registry_visa(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers import detectar_layout
        texto = extrair_texto_pdf(str(_PDF_VISA), senha=_SENHA_ITAU)
        parser = detectar_layout(texto)
        assert parser.nome_layout == "itau"

    def test_detectado_pelo_registry_mastercard(self):
        from views.cartoes.importar_fatura_pdf_model import extrair_texto_pdf
        from views.cartoes.pdf_parsers import detectar_layout
        texto = extrair_texto_pdf(str(_PDF_MASTER), senha=_SENHA_ITAU)
        parser = detectar_layout(texto)
        assert parser.nome_layout == "itau"

    def test_d_filipe_hardcoded_removido(self):
        """Bug D: o regex _LINHA_AUXILIAR não deve conter o nome próprio
        'FILIPE' (hardcoded pelo dev). Deve filtrar headers de titular por
        padrão genérico ou simplesmente não filtrar (a regex de transação
        já descarta linhas sem data)."""
        import re
        from views.cartoes.pdf_parsers import itau as itau_mod
        # Garante que não bate em nomes arbitrários
        texto_filipe = itau_mod._LINHA_AUXILIAR.pattern
        assert "FILIPE" not in texto_filipe.upper(), \
            "regex hardcoded com 'FILIPE' — remover"

    def test_e_descricao_vazia_e_rejeitada(self):
        """Bug E: linha tipo '14/11  05/12 168,73' (sem nome de
        estabelecimento) não pode virar item com descricao='' silenciosamente."""
        from views.cartoes.pdf_parsers.itau import ItauParser
        # Simula um texto Itaú mínimo com uma linha sem descrição
        texto = (
            "Lançamentos: produtos e serviços\n"
            "DATA PRODUTOS/SERVIÇOS VALOR EM R$\n"
            "14/11  05/12 168,73\n"  # sem descrição entre data e parcela
            "Total dos lançamentos atuais 168,73\n"
        )
        itens = ItauParser().extrair(texto)
        # Item sem descrição NÃO deve ser incluído
        for i in itens:
            assert i["descricao"], f"item com descrição vazia foi aceito: {i}"


# ---------------------------------------------------------------------------
# Etapa 8 — OCR fallback (graceful degradation)
# ---------------------------------------------------------------------------

class TestOcrFallback:
    def test_ocr_disponivel_retorna_bool(self):
        """Função utilitária reporta se as libs de OCR estão instaladas."""
        from views.cartoes.importar_fatura_pdf_model import ocr_disponivel
        assert isinstance(ocr_disponivel(), bool)

    def test_pdf_escaneado_sem_ocr_levanta_mensagem_clara(self, tmp_path, monkeypatch):
        """Simula PDF escaneado (texto vazio) com OCR indisponível —
        deve levantar erro claro ('escaneado' / 'OCR' / 'Tesseract' na msg)."""
        import views.cartoes.importar_fatura_pdf_model as mod
        from views.cartoes.importar_fatura_pdf_model import (
            PDFCamposIncompletosError, pdf_para_linhas,
        )

        # Mock: simula texto vazio (como se fosse um PDF puramente imagem)
        monkeypatch.setattr(mod, "extrair_texto_pdf",
                            lambda caminho, senha=None: "")
        # Força OCR indisponível
        monkeypatch.setattr(mod, "ocr_disponivel", lambda: False)
        # Mock pdf_tem_senha pra não tentar abrir um arquivo real
        monkeypatch.setattr(mod, "pdf_tem_senha", lambda caminho: False)

        with pytest.raises(PDFCamposIncompletosError) as excinfo:
            pdf_para_linhas("fake.pdf")
        msg = str(excinfo.value).lower()
        assert ("ocr" in msg) or ("escane" in msg) or ("tesseract" in msg)


# ---------------------------------------------------------------------------
# Etapa 5 — Pipeline pdf_para_linhas + salvar_como_xlsx + equivalência
# ---------------------------------------------------------------------------

class TestPdfParaLinhas:
    def test_nubank_pipeline_completo(self):
        from views.cartoes.importar_fatura_pdf_model import pdf_para_linhas
        linhas, meta = pdf_para_linhas(str(_PDF_NUBANK))
        assert len(linhas) >= 5
        assert meta["layout"] == "nubank"
        assert meta["tinha_senha"] is False
        assert meta["n_itens"] == len(linhas)
        assert meta["total"] > 0

    @pytest.mark.skipif(not _VISA_ORIGINAL, reason=_SKIP_MSG)
    def test_visa_pipeline_com_senha(self):
        from views.cartoes.importar_fatura_pdf_model import pdf_para_linhas
        linhas, meta = pdf_para_linhas(str(_PDF_VISA), senha=_SENHA_ITAU)
        assert len(linhas) >= 4
        assert meta["layout"] == "itau"
        assert meta["tinha_senha"] is True
        # VISA total deve bater com R$ 1.048,87
        assert meta["total"] == pytest.approx(1048.87, abs=0.01)

    @pytest.mark.skipif(not _VISA_ORIGINAL, reason=_SKIP_MSG)
    def test_mastercard_pipeline_com_senha(self):
        from views.cartoes.importar_fatura_pdf_model import pdf_para_linhas
        linhas, meta = pdf_para_linhas(str(_PDF_MASTER), senha=_SENHA_ITAU)
        assert len(linhas) >= 9
        assert meta["layout"] == "itau"
        assert meta["total"] == pytest.approx(1148.60, abs=0.01)

    @pytest.mark.skipif(not _VISA_ORIGINAL, reason=_SKIP_MSG)
    def test_pipeline_senha_errada_levanta(self):
        from views.cartoes.importar_fatura_pdf_model import (
            PDFSenhaIncorretaError, pdf_para_linhas,
        )
        with pytest.raises(PDFSenhaIncorretaError):
            pdf_para_linhas(str(_PDF_VISA), senha="errada")

    def test_pipeline_meta_inclui_ocr_usado(self):
        """O metadata deve indicar se OCR foi usado (False por padrão até Etapa 8)."""
        from views.cartoes.importar_fatura_pdf_model import pdf_para_linhas
        _, meta = pdf_para_linhas(str(_PDF_NUBANK))
        assert "ocr_usado" in meta
        assert meta["ocr_usado"] is False


class TestSalvarComoXlsx:
    def test_gera_arquivo_xlsx(self, tmp_path):
        from views.cartoes.importar_fatura_pdf_model import (
            pdf_para_linhas, salvar_como_xlsx,
        )
        linhas, _ = pdf_para_linhas(str(_PDF_NUBANK))
        destino = tmp_path / "saida.xlsx"
        salvar_como_xlsx(linhas, str(destino))
        assert destino.exists()
        assert destino.stat().st_size > 0

    def test_xlsx_gerado_e_lido_de_volta_por_excel_pipeline(self, tmp_path):
        """Saída do salvar_como_xlsx é lida pelo ler_arquivo_fatura do Excel
        e produz lista equivalente (mesmo schema, mesmos valores)."""
        from views.cartoes.importar_fatura_model import ler_arquivo_fatura
        from views.cartoes.importar_fatura_pdf_model import (
            pdf_para_linhas, salvar_como_xlsx,
        )
        linhas_pdf, _ = pdf_para_linhas(str(_PDF_NUBANK))
        destino = tmp_path / "intermediario.xlsx"
        salvar_como_xlsx(linhas_pdf, str(destino))

        linhas_excel = ler_arquivo_fatura(str(destino))

        # Mesmo nº de itens
        assert len(linhas_excel) == len(linhas_pdf)
        # Mesmos valores totais (round pra evitar artefato float)
        soma_pdf = round(sum(i["valor"] for i in linhas_pdf), 2)
        soma_xls = round(sum(i["valor"] for i in linhas_excel), 2)
        assert soma_pdf == soma_xls
        # Mesmo schema
        for i in linhas_excel:
            assert {"descricao", "estabelecimento", "categoria",
                    "parcela", "valor"} <= set(i.keys())

    def test_pdfs_normais_nao_usam_ocr(self):
        """PDFs com texto extraível NÃO devem disparar OCR (otimização)."""
        from views.cartoes.importar_fatura_pdf_model import pdf_para_linhas
        for pdf, senha in [
            (_PDF_NUBANK,  None),
            (_PDF_VISA,    _SENHA_ITAU),
            (_PDF_MASTER,  _SENHA_ITAU),
        ]:
            _, meta = pdf_para_linhas(str(pdf), senha=senha)
            assert meta["ocr_usado"] is False, f"OCR rodou desnecessariamente em {pdf.name}"

    def test_xlsx_passa_na_validacao_da_pipeline_excel(self, tmp_path):
        """Saída do PDF, lida via Excel, passa pela validar_linhas_fatura
        sem erros — fluxo PDF é compatível com pipeline existente."""
        from views.cartoes.importar_fatura_model import (
            ler_arquivo_fatura, validar_linhas_fatura,
        )
        from views.cartoes.importar_fatura_pdf_model import (
            pdf_para_linhas, salvar_como_xlsx,
        )
        linhas_pdf, _ = pdf_para_linhas(str(_PDF_VISA), senha=_SENHA_ITAU)
        destino = tmp_path / "v.xlsx"
        salvar_como_xlsx(linhas_pdf, str(destino))

        linhas_excel = ler_arquivo_fatura(str(destino))
        erros = validar_linhas_fatura(linhas_excel)
        assert erros == [], f"erros inesperados: {erros}"
