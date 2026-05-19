"""
importar_fatura_pdf_model.py — Pipeline de importação de fatura via PDF.

Etapa 1: classes de erro, detecção de senha, extração de texto base.
Etapas seguintes: parsers por layout, pipeline completo, OCR fallback.

Usa pypdf (já presente nas dependências) tanto para detecção de senha
quanto para descriptografia e extração de texto. pdfplumber pode ser
adicionado depois para extração de tabelas em parsers específicos.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Erros explícitos do módulo
# ---------------------------------------------------------------------------

class PDFSenhaIncorretaError(Exception):
    """PDF protegido por senha e a senha fornecida não funcionou (ou ausente)."""


class PDFCorrompidoError(Exception):
    """Arquivo inexistente, ilegível, sem header PDF válido ou ilegível pelo pypdf."""


class PDFLayoutDesconhecidoError(Exception):
    """Nenhum parser concreto reconheceu o layout do PDF (usado em etapas 2+)."""


class PDFCamposIncompletosError(Exception):
    """Parser identificou o layout mas faltam campos obrigatórios (usado em etapas 3+)."""


# ---------------------------------------------------------------------------
# Detecção de senha
# ---------------------------------------------------------------------------

def pdf_tem_senha(caminho: str) -> bool:
    """Retorna True se o PDF estiver protegido por senha.

    Levanta PDFCorrompidoError se o arquivo não puder ser aberto como PDF.
    """
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as e:  # pragma: no cover — pypdf é dependência base
        raise RuntimeError(
            "Biblioteca pypdf não está disponível. Reinstale as dependências."
        ) from e

    try:
        reader = PdfReader(str(p))
        tem = bool(reader.is_encrypted)
        log.info("pdf_tem_senha(%s) = %s", p.name, tem)
        return tem
    except PdfReadError as e:
        log.warning("pdf_tem_senha: PDF corrompido %s: %s", p.name, e)
        raise PDFCorrompidoError(
            f"Arquivo {p.name!r} não é um PDF válido: {e}"
        ) from e
    except Exception as e:
        log.warning("pdf_tem_senha: erro inesperado em %s: %s", p.name, e)
        raise PDFCorrompidoError(
            f"Falha ao abrir {p.name!r}: {e}"
        ) from e


# ---------------------------------------------------------------------------
# Extração de texto
# ---------------------------------------------------------------------------

def extrair_texto_pdf(caminho: str, senha: Optional[str] = None) -> str:
    """Extrai todo o texto do PDF.

    - Se o PDF estiver protegido e a senha for None ou incorreta, levanta
      PDFSenhaIncorretaError.
    - Se a senha for fornecida para um PDF não protegido, é ignorada.
    - Levanta PDFCorrompidoError se o arquivo for inválido.

    Retorna string com o texto concatenado de todas as páginas.
    """
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(p))
    except PdfReadError as e:
        raise PDFCorrompidoError(
            f"Arquivo {p.name!r} não é um PDF válido: {e}"
        ) from e
    except Exception as e:
        raise PDFCorrompidoError(
            f"Falha ao abrir {p.name!r}: {e}"
        ) from e

    if reader.is_encrypted:
        if not senha:
            log.info("extrair_texto_pdf(%s): protegido, senha ausente", p.name)
            raise PDFSenhaIncorretaError(
                f"{p.name} é protegido por senha. Forneça a senha."
            )
        try:
            # pypdf.decrypt retorna PasswordType (0 = falhou, 1 = user, 2 = owner)
            resultado = reader.decrypt(senha)
            if not resultado:
                raise PDFSenhaIncorretaError(
                    f"Senha incorreta para {p.name}."
                )
        except PDFSenhaIncorretaError:
            raise
        except Exception as e:
            log.warning("extrair_texto_pdf: erro descriptografando %s: %s", p.name, e)
            raise PDFSenhaIncorretaError(
                f"Falha ao descriptografar {p.name}: {e}"
            ) from e

    try:
        partes: list[str] = []
        for pag in reader.pages:
            try:
                partes.append(pag.extract_text() or "")
            except Exception as e:  # pragma: no cover — falha por página
                log.warning("extract_text de página falhou em %s: %s", p.name, e)
        texto = "\n".join(partes).strip()
    except Exception as e:
        raise PDFCorrompidoError(
            f"Falha ao extrair texto de {p.name!r}: {e}"
        ) from e

    if not texto:
        log.warning("extrair_texto_pdf(%s): texto vazio (PDF escaneado?)", p.name)
    else:
        log.info("extrair_texto_pdf(%s): %d caracteres", p.name, len(texto))
    return texto
