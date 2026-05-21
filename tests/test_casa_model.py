"""
test_casa_model.py — Testes do módulo Compras de Casa.

Cobertura por etapa:
  C1 — Schema itens_estoque
  C2 — CRUD + listar_lista_compras (estoque <= mínimo)
  C3/C4 — UI (smoke import)
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# C1 — Schema: itens_estoque
# ---------------------------------------------------------------------------

class TestTabelaItensEstoque:
    def test_tabela_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "itens_estoque" in tabelas

    def test_colunas(self, banco):
        from database import conectar
        with conectar() as conn:
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(itens_estoque)"
            ).fetchall()}
        esperadas = {
            "id", "nome", "categoria", "unidade",
            "estoque_atual", "estoque_minimo",
            "observacao", "ativo", "criado_em",
        }
        assert esperadas <= cols

    def test_nome_obrigatorio(self, banco):
        import sqlite3
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO itens_estoque (categoria, criado_em)"
                    " VALUES (?, ?)",
                    ("Mercearia", agora),
                )

    def test_insere_item_minimo(self, banco):
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            cur = conn.execute(
                "INSERT INTO itens_estoque (nome, criado_em) VALUES (?, ?)",
                ("Arroz", agora),
            )
            iid = cur.lastrowid
            row = conn.execute(
                "SELECT estoque_atual, estoque_minimo, ativo"
                " FROM itens_estoque WHERE id=?", (iid,),
            ).fetchone()
        # Defaults razoáveis
        assert iid > 0
        assert row["estoque_atual"] == 0
        assert row["estoque_minimo"] == 0
        assert row["ativo"] == 1


class TestSchemaMarcas:
    """D1: nova coluna `marca` em itens_estoque + tabela `marcas`."""

    def test_coluna_marca_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(itens_estoque)"
            ).fetchall()}
        assert "marca" in cols

    def test_tabela_marcas_existe(self, banco):
        from database import conectar
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "marcas" in tabelas

    def test_marcas_colunas(self, banco):
        from database import conectar
        with conectar() as conn:
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(marcas)"
            ).fetchall()}
        assert {"id", "nome", "criado_em"} <= cols

    def test_marca_nome_unique(self, banco):
        """marcas.nome deve ter UNIQUE — evita duplicatas no catálogo."""
        import sqlite3
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Usa nome único que não exista no catálogo seed
        nome_unico = "MarcaTesteUniqueXYZ"
        with conectar() as conn:
            conn.execute(
                "INSERT INTO marcas (nome, criado_em) VALUES (?, ?)",
                (nome_unico, agora),
            )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO marcas (nome, criado_em) VALUES (?, ?)",
                    (nome_unico, agora),
                )

    def test_marca_default_vazia_em_item(self, banco):
        """Item sem marca cadastrada deve ter marca='' (default)."""
        from datetime import datetime
        from database import conectar
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            cur = conn.execute(
                "INSERT INTO itens_estoque (nome, criado_em)"
                " VALUES (?, ?)", ("Item Sem Marca", agora),
            )
            row = conn.execute(
                "SELECT marca FROM itens_estoque WHERE id=?",
                (cur.lastrowid,),
            ).fetchone()
        assert row["marca"] == ""


class TestZerarDadosInclueItensEstoque:
    def test_zerar_dados_remove_itens_estoque(self, banco):
        from datetime import datetime
        from database import conectar, zerar_dados
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conectar() as conn:
            conn.execute(
                "INSERT INTO itens_estoque (nome, criado_em) VALUES (?,?)",
                ("Apagar", agora),
            )
        zerar_dados()
        with conectar() as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM itens_estoque"
            ).fetchone()[0]
        assert n == 0


# ---------------------------------------------------------------------------
# C2 — CRUD do model + lista de compras + ajuste de estoque
# ---------------------------------------------------------------------------

def _dados_item(nome: str = "Arroz", **extras) -> dict:
    base = {
        "nome":           nome,
        "categoria":      "Mercearia",
        "unidade":        "kg",
        "estoque_atual":  5.0,
        "estoque_minimo": 2.0,
        "observacao":     "",
    }
    base.update(extras)
    return base


class TestCRUDItens:
    def test_salvar_retorna_id(self, banco):
        from views.compras_casa.casa_model import salvar_item
        iid = salvar_item(_dados_item())
        assert isinstance(iid, int) and iid > 0

    def test_obter_devolve_campos(self, banco):
        from views.compras_casa.casa_model import obter_item, salvar_item
        iid = salvar_item(_dados_item("Feijão", estoque_atual=3.0))
        it = obter_item(iid)
        assert it is not None
        assert it.nome == "Feijão"
        assert it.estoque_atual == pytest.approx(3.0)
        assert it.estoque_minimo == pytest.approx(2.0)
        assert it.categoria == "Mercearia"

    def test_obter_inexistente_retorna_none(self, banco):
        from views.compras_casa.casa_model import obter_item
        assert obter_item(9999) is None

    def test_listar_so_ativos_por_padrao(self, banco):
        from views.compras_casa.casa_model import listar_itens, salvar_item
        salvar_item(_dados_item("A"))
        b = salvar_item(_dados_item("B"))
        from database import conectar
        with conectar() as conn:
            conn.execute("UPDATE itens_estoque SET ativo=0 WHERE id=?", (b,))
        nomes = sorted(i.nome for i in listar_itens())
        assert nomes == ["A"]
        # Incluir inativos quando pedido
        nomes_full = sorted(i.nome for i in listar_itens(incluir_inativos=True))
        assert nomes_full == ["A", "B"]

    def test_listar_ordena_alfabeticamente(self, banco):
        from views.compras_casa.casa_model import listar_itens, salvar_item
        salvar_item(_dados_item("Zarcao"))
        salvar_item(_dados_item("Abacate"))
        salvar_item(_dados_item("Manga"))
        nomes = [i.nome for i in listar_itens()]
        assert nomes == ["Abacate", "Manga", "Zarcao"]

    def test_atualizar_item(self, banco):
        from views.compras_casa.casa_model import obter_item, salvar_item
        iid = salvar_item(_dados_item("Antes"))
        salvar_item({**_dados_item("Depois"), "estoque_minimo": 10.0}, id=iid)
        it = obter_item(iid)
        assert it.nome == "Depois"
        assert it.estoque_minimo == pytest.approx(10.0)

    def test_excluir_item(self, banco):
        from views.compras_casa.casa_model import (
            excluir_item, listar_itens, salvar_item,
        )
        iid = salvar_item(_dados_item())
        ok, _ = excluir_item(iid)
        assert ok is True
        assert listar_itens() == []

    def test_nome_vazio_recusa(self, banco):
        from views.compras_casa.casa_model import salvar_item
        with pytest.raises(ValueError):
            salvar_item({**_dados_item(), "nome": "   "})


class TestAjustarEstoque:
    def test_ajustar_set_define_valor(self, banco):
        from views.compras_casa.casa_model import (
            ajustar_estoque, obter_item, salvar_item,
        )
        iid = salvar_item(_dados_item("X", estoque_atual=5.0))
        ajustar_estoque(iid, novo_valor=10.0)
        assert obter_item(iid).estoque_atual == pytest.approx(10.0)

    def test_ajustar_delta_soma(self, banco):
        from views.compras_casa.casa_model import (
            ajustar_estoque, obter_item, salvar_item,
        )
        iid = salvar_item(_dados_item("Y", estoque_atual=5.0))
        ajustar_estoque(iid, delta=3.0)  # +3
        assert obter_item(iid).estoque_atual == pytest.approx(8.0)
        ajustar_estoque(iid, delta=-2.0)  # -2
        assert obter_item(iid).estoque_atual == pytest.approx(6.0)

    def test_ajustar_delta_nao_negativa(self, banco):
        """Estoque não pode ficar negativo (clampa em 0)."""
        from views.compras_casa.casa_model import (
            ajustar_estoque, obter_item, salvar_item,
        )
        iid = salvar_item(_dados_item("Z", estoque_atual=2.0))
        ajustar_estoque(iid, delta=-10.0)
        assert obter_item(iid).estoque_atual == pytest.approx(0.0)

    def test_ajustar_set_negativo_recusa(self, banco):
        from views.compras_casa.casa_model import ajustar_estoque, salvar_item
        iid = salvar_item(_dados_item("W"))
        with pytest.raises(ValueError):
            ajustar_estoque(iid, novo_valor=-5.0)


class TestListaCompras:
    def test_lista_compras_vazia(self, banco):
        from views.compras_casa.casa_model import listar_lista_compras
        assert listar_lista_compras() == []

    def test_inclui_itens_abaixo_do_minimo(self, banco):
        from views.compras_casa.casa_model import (
            listar_lista_compras, salvar_item,
        )
        salvar_item(_dados_item("Acima", estoque_atual=10.0, estoque_minimo=5.0))
        salvar_item(_dados_item("Igual", estoque_atual=2.0, estoque_minimo=2.0))
        salvar_item(_dados_item("Abaixo", estoque_atual=1.0, estoque_minimo=5.0))

        lista = listar_lista_compras()
        nomes = sorted(i.nome for i in lista)
        # Iguala e abaixo entram (atual <= mínimo); acima não
        assert nomes == ["Abaixo", "Igual"]

    def test_lista_ignora_itens_com_minimo_zero(self, banco):
        """Item com minimo=0 nunca deveria aparecer na lista
        (provavelmente é item sem controle de estoque)."""
        from views.compras_casa.casa_model import (
            listar_lista_compras, salvar_item,
        )
        salvar_item(_dados_item("SemControle",
                                 estoque_atual=0.0, estoque_minimo=0.0))
        salvar_item(_dados_item("Falta",
                                 estoque_atual=0.0, estoque_minimo=1.0))
        nomes = sorted(i.nome for i in listar_lista_compras())
        assert nomes == ["Falta"]

    def test_lista_ignora_inativos(self, banco):
        from database import conectar
        from views.compras_casa.casa_model import (
            listar_lista_compras, salvar_item,
        )
        salvar_item(_dados_item("Ativo", estoque_atual=0.0, estoque_minimo=5.0))
        bid = salvar_item(_dados_item("Inativo",
                                       estoque_atual=0.0, estoque_minimo=5.0))
        with conectar() as conn:
            conn.execute("UPDATE itens_estoque SET ativo=0 WHERE id=?", (bid,))
        nomes = sorted(i.nome for i in listar_lista_compras())
        assert nomes == ["Ativo"]

    def test_item_tem_propriedade_quantidade_a_comprar(self, banco):
        """quantidade_a_comprar = estoque_minimo - estoque_atual (>=0)."""
        from views.compras_casa.casa_model import (
            listar_lista_compras, salvar_item,
        )
        salvar_item(_dados_item("X", estoque_atual=2.0, estoque_minimo=10.0))
        lista = listar_lista_compras()
        assert len(lista) == 1
        assert lista[0].quantidade_a_comprar == pytest.approx(8.0)


# ---------------------------------------------------------------------------
# D3 — Marca no item + CRUD de marcas (find or create)
# ---------------------------------------------------------------------------

class TestMarcaNoItem:
    def test_salvar_item_aceita_marca(self, banco):
        from views.compras_casa.casa_model import obter_item, salvar_item
        iid = salvar_item({**_dados_item("Arroz"), "marca": "Camil"})
        it = obter_item(iid)
        assert it.marca == "Camil"

    def test_item_sem_marca_fica_vazio(self, banco):
        from views.compras_casa.casa_model import obter_item, salvar_item
        iid = salvar_item(_dados_item("X"))
        assert obter_item(iid).marca == ""

    def test_salvar_item_com_marca_nova_cria_em_marcas(self, banco):
        """Se a marca passada não existe em `marcas`, o sistema cria
        automaticamente (find-or-create) — assim o catálogo cresce."""
        from views.compras_casa.casa_model import listar_marcas, salvar_item
        salvar_item({**_dados_item("Y"), "marca": "MarcaTesteUnica"})
        nomes = {m.nome for m in listar_marcas()}
        assert "MarcaTesteUnica" in nomes

    def test_salvar_item_com_marca_existente_nao_duplica(self, banco):
        from views.compras_casa.casa_model import (
            listar_marcas, salvar_item, salvar_marca,
        )
        salvar_marca("Existente")
        n_antes = len(listar_marcas())
        salvar_item({**_dados_item("A"), "marca": "Existente"})
        salvar_item({**_dados_item("B"), "marca": "Existente"})
        n_depois = len(listar_marcas())
        assert n_depois == n_antes  # não duplicou

    def test_marca_vazia_nao_cria_registro(self, banco):
        from views.compras_casa.casa_model import listar_marcas, salvar_item
        n_antes = len(listar_marcas())
        salvar_item(_dados_item("Z"))  # sem marca
        salvar_item({**_dados_item("W"), "marca": ""})
        assert len(listar_marcas()) == n_antes


class TestCRUDMarcas:
    def test_salvar_marca_retorna_id(self, banco):
        from views.compras_casa.casa_model import salvar_marca
        mid = salvar_marca("Camil")
        assert isinstance(mid, int) and mid > 0

    def test_salvar_marca_idempotente(self, banco):
        """Re-salvar mesma marca retorna o mesmo id (find-or-create)."""
        from views.compras_casa.casa_model import salvar_marca
        m1 = salvar_marca("Tirolez")
        m2 = salvar_marca("Tirolez")
        assert m1 == m2

    def test_salvar_marca_case_preservada(self, banco):
        """Casing original é preservado, mas re-salvar com casing diferente
        ainda devolve o mesmo registro (case-insensitive match)."""
        from views.compras_casa.casa_model import (
            listar_marcas, salvar_marca,
        )
        m1 = salvar_marca("Camil")
        m2 = salvar_marca("CAMIL")
        assert m1 == m2
        # Não criou duplicata
        nomes = [m.nome for m in listar_marcas() if m.nome.lower() == "camil"]
        assert len(nomes) == 1

    def test_salvar_marca_vazia_retorna_zero(self, banco):
        from views.compras_casa.casa_model import salvar_marca
        assert salvar_marca("") == 0
        assert salvar_marca("   ") == 0

    def test_listar_marcas_ordenado_alfabeticamente(self, banco):
        from views.compras_casa.casa_model import listar_marcas, salvar_marca
        salvar_marca("Zé Bom")
        salvar_marca("Adorada")
        salvar_marca("Médio")
        nomes = [m.nome for m in listar_marcas()]
        assert nomes == sorted(nomes, key=str.lower)

    def test_buscar_marcas_por_prefixo(self, banco):
        """Busca por prefixo. Usa um prefixo único que não exista no catálogo
        seed do init (que popula ~500 marcas)."""
        from views.compras_casa.casa_model import buscar_marcas, salvar_marca
        # Prefixo único pra evitar marcas do catálogo seed
        salvar_marca("ZzTesteUmaMarca")
        salvar_marca("ZzTesteOutraMarca")
        salvar_marca("Outro")
        resultados = sorted(m.nome for m in buscar_marcas("zztest"))
        assert resultados == ["ZzTesteOutraMarca", "ZzTesteUmaMarca"]
