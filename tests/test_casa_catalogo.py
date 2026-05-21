"""
test_casa_catalogo.py — Testes do parser/catalogo de Compras de Casa.

Lê `docs/Lista de itens de compras.txt` (~500 itens em 15 categorias)
e oferece duas APIs:
- listar_itens_sugeridos() -> list[dict] com nome, categoria, marcas
- listar_marcas_sugeridas(item_nome) -> list[str]
- _todas_marcas_do_catalogo() -> set[str] (para seed inicial)
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestParserCatalogo:
    def test_listar_itens_sugeridos_retorna_lista(self):
        from views.compras_casa.catalogo import listar_itens_sugeridos
        itens = listar_itens_sugeridos()
        assert isinstance(itens, list)
        assert len(itens) > 100, f"esperava muitos itens, achou {len(itens)}"

    def test_item_tem_nome_e_categoria(self):
        from views.compras_casa.catalogo import listar_itens_sugeridos
        itens = listar_itens_sugeridos()
        for it in itens:
            assert it["nome"], f"item sem nome: {it}"
            assert it["categoria"], f"item sem categoria: {it['nome']}"

    def test_arroz_existe_com_marcas(self):
        """Sanity: 'Arroz branco tipo 1' do .txt tem marcas Camil/Tio João/Prato Fino."""
        from views.compras_casa.catalogo import listar_itens_sugeridos
        itens = listar_itens_sugeridos()
        arroz = next(
            (i for i in itens if "arroz branco tipo 1" in i["nome"].lower()),
            None,
        )
        assert arroz is not None
        marcas = [m.lower() for m in arroz["marcas"]]
        assert "camil" in marcas
        assert "tio joão" in marcas
        assert "prato fino" in marcas

    def test_item_sem_marca_hortifruti(self):
        """Itens hortifruti não têm marcas — devem aparecer com lista vazia."""
        from views.compras_casa.catalogo import listar_itens_sugeridos
        itens = listar_itens_sugeridos()
        tomate = next(
            (i for i in itens if i["nome"].lower() == "tomate"),
            None,
        )
        assert tomate is not None
        assert tomate["marcas"] == []
        assert "hortifruti" in tomate["categoria"].lower()

    def test_categorias_extraidas(self):
        """As 15 categorias do .txt devem aparecer nos itens."""
        from views.compras_casa.catalogo import listar_itens_sugeridos
        itens = listar_itens_sugeridos()
        cats = {i["categoria"] for i in itens}
        # Pelo menos 10 categorias distintas (algumas podem se fundir)
        assert len(cats) >= 10, f"poucas categorias: {cats}"


class TestMarcasSugeridas:
    def test_listar_marcas_sugeridas_por_item(self):
        from views.compras_casa.catalogo import listar_marcas_sugeridas
        marcas = listar_marcas_sugeridas("Arroz branco tipo 1")
        assert "Camil" in marcas
        assert "Tio João" in marcas

    def test_item_inexistente_retorna_vazio(self):
        from views.compras_casa.catalogo import listar_marcas_sugeridas
        assert listar_marcas_sugeridas("XYZ-NAO-EXISTE-123") == []

    def test_case_insensitive(self):
        from views.compras_casa.catalogo import listar_marcas_sugeridas
        m1 = listar_marcas_sugeridas("Arroz Branco Tipo 1")
        m2 = listar_marcas_sugeridas("arroz branco tipo 1")
        assert m1 == m2

    def test_todas_marcas_deduplicadas(self):
        """A função interna que devolve todas as marcas do catálogo
        deve trazer um set sem duplicatas e bem grande (>100)."""
        from views.compras_casa.catalogo import _todas_marcas_do_catalogo
        marcas = _todas_marcas_do_catalogo()
        assert isinstance(marcas, set)
        assert len(marcas) > 100
        # Marcas famosas devem estar lá
        nomes = {m.lower() for m in marcas}
        for esperada in ["camil", "omo", "nestlé", "knorr"]:
            assert esperada in nomes


class TestSeedMarcas:
    def test_popular_marcas_do_catalogo(self, banco):
        """Popular a tabela `marcas` na 1ª execução com o catálogo do .txt.

        Obs: o `inicializar_banco` agora também popula via
        `_popular_marcas_padrao` — então o teste limpa antes pra validar
        a função `popular_marcas_iniciais` em isolamento."""
        from database import conectar
        from views.compras_casa.catalogo import (
            _todas_marcas_do_catalogo, popular_marcas_iniciais,
        )

        with conectar() as conn:
            conn.execute("DELETE FROM marcas")

        n_inseridas = popular_marcas_iniciais()
        assert n_inseridas > 100

        # Depois: tem todas as marcas do catálogo
        with conectar() as conn:
            n_depois = conn.execute("SELECT COUNT(*) FROM marcas").fetchone()[0]
        assert n_depois == len(_todas_marcas_do_catalogo())

    def test_popular_marcas_e_idempotente(self, banco):
        """Rodar 2x não duplica nem falha."""
        from database import conectar
        from views.compras_casa.catalogo import popular_marcas_iniciais

        popular_marcas_iniciais()
        with conectar() as conn:
            n1 = conn.execute("SELECT COUNT(*) FROM marcas").fetchone()[0]
        popular_marcas_iniciais()
        with conectar() as conn:
            n2 = conn.execute("SELECT COUNT(*) FROM marcas").fetchone()[0]
        assert n1 == n2
