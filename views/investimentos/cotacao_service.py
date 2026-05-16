"""
cotacao_service.py — Serviço de cotação de ativos.

CotacaoService      : adaptador base (manual — retorna None).
CotacaoAPIService   : busca via brapi.dev (B3 + cripto, sem chave de API).
"""
from __future__ import annotations
import urllib.request
import json


class CotacaoService:
    """Adaptador base — cotação manual. Usuário informa via interface."""

    def obter_preco(self, codigo: str, tipo: str) -> float | None:
        return None

    def disponivel(self) -> bool:
        return False

    def nome(self) -> str:
        return "Manual"


class CotacaoAPIService(CotacaoService):
    """
    Busca cotações em tempo real via brapi.dev.
    Suporte: ações/ETFs/FIIs da B3 (código puro, ex: 'PETR4') e
    criptomoedas com sufixo '-USD' (ex: 'BTC-USD').
    Degrada silenciosamente para None em caso de erro ou código inválido.
    """

    _BASE = "https://brapi.dev/api/quote/{ticker}?fundamental=false"
    _TIMEOUT = 5  # segundos

    def disponivel(self) -> bool:
        return True

    def nome(self) -> str:
        return "brapi.dev"

    def obter_preco(self, codigo: str, tipo: str) -> float | None:
        ticker = self._resolver_ticker(codigo, tipo)
        if not ticker:
            return None
        try:
            url = self._BASE.format(ticker=ticker)
            req = urllib.request.Request(url, headers={"User-Agent": "Serenus/1.0"})
            with urllib.request.urlopen(req, timeout=self._TIMEOUT) as resp:
                data = json.loads(resp.read())
            results = data.get("results", [])
            if not results:
                return None
            preco = results[0].get("regularMarketPrice")
            return float(preco) if preco is not None else None
        except Exception:
            return None

    @staticmethod
    def _resolver_ticker(codigo: str, tipo: str) -> str | None:
        codigo = codigo.strip().upper()
        if not codigo:
            return None
        if tipo == "cripto":
            # brapi aceita BTC-USD, ETH-USD etc.
            if "-" not in codigo:
                return f"{codigo}-USD"
            return codigo
        # Para B3 (ação, ETF, FII, tesouro) usa o código direto
        return codigo


# Instância padrão usada pelo sistema.
cotacao_service = CotacaoService()

