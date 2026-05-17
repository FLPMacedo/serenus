"""
test_modo_ajuda.py — Testes do helper `modo_ajuda_ativo()`.

A renderização real do banner/tooltip exige um root Tk (não testamos UI),
mas a lógica de leitura da configuração é coberta aqui — é o que decide se
o banner aparece ou some.
"""
from __future__ import annotations

from database import salvar_configuracao


class TestModoAjudaConfig:
    def test_padrao_eh_ligado(self, banco):
        from views.widgets.ajuda import modo_ajuda_ativo
        # Configuração nunca gravada → padrão = ligado
        assert modo_ajuda_ativo() is True

    def test_desligar_persiste(self, banco):
        from views.widgets.ajuda import modo_ajuda_ativo
        salvar_configuracao("modo_ajuda", "0")
        assert modo_ajuda_ativo() is False

    def test_religar(self, banco):
        from views.widgets.ajuda import modo_ajuda_ativo
        salvar_configuracao("modo_ajuda", "0")
        assert modo_ajuda_ativo() is False
        salvar_configuracao("modo_ajuda", "1")
        assert modo_ajuda_ativo() is True

    def test_valor_invalido_trata_como_desligado(self, banco):
        from views.widgets.ajuda import modo_ajuda_ativo
        salvar_configuracao("modo_ajuda", "talvez")
        # Apenas "1" liga; qualquer outro valor desliga
        assert modo_ajuda_ativo() is False
