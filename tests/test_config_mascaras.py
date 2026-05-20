"""
test_config_mascaras.py — Testes dos helpers de máscara e validação
em config.py (CPF, telefone, CEP, e-mail).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Stub de entry pra testar as máscaras sem precisar de Tk root
# ---------------------------------------------------------------------------

class _StubEntry:
    """Mimica a API mínima de CTkEntry que mascara_* usa: get/delete/insert."""

    def __init__(self, valor: str = ""):
        self._v = valor

    def get(self) -> str:
        return self._v

    def delete(self, start, end) -> None:
        # Apenas zera (padrão é (0, "end"))
        self._v = ""

    def insert(self, pos, texto: str) -> None:
        self._v = texto


# ---------------------------------------------------------------------------
# CPF
# ---------------------------------------------------------------------------

class TestMascaraCPF:
    def test_vazio_fica_vazio(self):
        from config import mascara_cpf
        e = _StubEntry("")
        mascara_cpf(e)
        assert e.get() == ""

    def test_3_digitos(self):
        from config import mascara_cpf
        e = _StubEntry("123")
        mascara_cpf(e)
        assert e.get() == "123"

    def test_6_digitos(self):
        from config import mascara_cpf
        e = _StubEntry("123456")
        mascara_cpf(e)
        assert e.get() == "123.456"

    def test_9_digitos(self):
        from config import mascara_cpf
        e = _StubEntry("123456789")
        mascara_cpf(e)
        assert e.get() == "123.456.789"

    def test_11_digitos(self):
        from config import mascara_cpf
        e = _StubEntry("12345678901")
        mascara_cpf(e)
        assert e.get() == "123.456.789-01"

    def test_ignora_nao_digitos(self):
        from config import mascara_cpf
        e = _StubEntry("abc123.456-78901")
        mascara_cpf(e)
        assert e.get() == "123.456.789-01"

    def test_excesso_truncado_em_11(self):
        """CPF tem 11 dígitos — excesso é descartado."""
        from config import mascara_cpf
        e = _StubEntry("12345678901234")
        mascara_cpf(e)
        assert e.get() == "123.456.789-01"


# ---------------------------------------------------------------------------
# Telefone (10 ou 11 dígitos)
# ---------------------------------------------------------------------------

class TestMascaraTelefone:
    def test_vazio(self):
        from config import mascara_telefone
        e = _StubEntry("")
        mascara_telefone(e)
        assert e.get() == ""

    def test_2_digitos(self):
        from config import mascara_telefone
        e = _StubEntry("31")
        mascara_telefone(e)
        assert e.get() == "(31"

    def test_3_digitos(self):
        """DDD completo, começa o número."""
        from config import mascara_telefone
        e = _StubEntry("319")
        mascara_telefone(e)
        assert e.get() == "(31) 9"

    def test_10_digitos_telefone_fixo(self):
        from config import mascara_telefone
        e = _StubEntry("3133334444")
        mascara_telefone(e)
        assert e.get() == "(31) 3333-4444"

    def test_11_digitos_celular(self):
        from config import mascara_telefone
        e = _StubEntry("31999990000")
        mascara_telefone(e)
        assert e.get() == "(31) 99999-0000"

    def test_ignora_nao_digitos(self):
        from config import mascara_telefone
        e = _StubEntry("+55 (31) 99999-0000")
        mascara_telefone(e)
        # 55 + 31 + 99999 + 0000 → 13 dígitos, trunca em 11 (DDD+9)
        assert e.get() == "(55) 31999-9900"

    def test_excesso_truncado_em_11(self):
        from config import mascara_telefone
        e = _StubEntry("319999900001234")
        mascara_telefone(e)
        assert e.get() == "(31) 99999-0000"


# ---------------------------------------------------------------------------
# CEP
# ---------------------------------------------------------------------------

class TestMascaraCEP:
    def test_vazio(self):
        from config import mascara_cep
        e = _StubEntry("")
        mascara_cep(e)
        assert e.get() == ""

    def test_5_digitos(self):
        from config import mascara_cep
        e = _StubEntry("35430")
        mascara_cep(e)
        assert e.get() == "35430"

    def test_8_digitos(self):
        from config import mascara_cep
        e = _StubEntry("35430191")
        mascara_cep(e)
        assert e.get() == "35430-191"

    def test_ignora_nao_digitos(self):
        from config import mascara_cep
        e = _StubEntry("CEP: 35.430-191!")
        mascara_cep(e)
        assert e.get() == "35430-191"

    def test_excesso_truncado(self):
        from config import mascara_cep
        e = _StubEntry("354301919999")
        mascara_cep(e)
        assert e.get() == "35430-191"


# ---------------------------------------------------------------------------
# E-mail
# ---------------------------------------------------------------------------

class TestValidarEmail:
    @pytest.mark.parametrize("email", [
        "joao@exemplo.com",
        "ana.silva@empresa.com.br",
        "user+tag@dominio.io",
        "x@y.zz",
        "FELIPE@gmail.com",
    ])
    def test_validos(self, email):
        from config import validar_email
        assert validar_email(email) is True

    @pytest.mark.parametrize("email", [
        "",
        "   ",
        "semarroba.com",
        "@semuser.com",
        "user@",
        "user@@dominio.com",
        "user@dominio",   # sem TLD
        "user @com.br",   # espaço
        "user@.com",      # ponto colado
        "user@dom..com",  # ponto duplo
    ])
    def test_invalidos(self, email):
        from config import validar_email
        assert validar_email(email) is False

    def test_none_e_falso(self):
        from config import validar_email
        assert validar_email(None) is False
