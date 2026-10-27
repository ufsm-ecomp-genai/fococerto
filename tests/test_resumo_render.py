"""Divisão do plano.resumo em resumo / desvios / respostas ao Crítico, só na renderização."""
from __future__ import annotations

import pytest

from app.agents.base import texto_respostas
from app.core.mensagens import msg
from app.output import render_markdown
from app.output.comum import dividir_resumo, partes_resposta
from tests.dados_teste_resultado import regiao_teste, resultado_teste


def _resumo(idioma, texto="Plano X.", desvios=(), respostas=()):
    # mesma montagem de base.plano_de_saida
    r = texto + ((msg("sufixo_desvios", idioma) + " | ".join(desvios)) if desvios else "")
    resp = texto_respostas(list(respostas))
    return r + (msg("sufixo_respostas", idioma) + resp if resp else "")


@pytest.mark.parametrize("idioma", ["pt-BR", "en"])
def test_divide_as_tres_partes(idioma):
    r = _resumo(idioma, desvios=["a1 movida (ganho 0,6 h)", "t1 movida"],
                respostas=["p1 -> adotado (motivo (com parênteses))", "p2 -> rejeitado"])
    p = dividir_resumo(r)
    assert p.texto == "Plano X."
    assert p.desvios == ["a1 movida (ganho 0,6 h)", "t1 movida"]
    assert p.respostas == ["p1 -> adotado (motivo (com parênteses))", "p2 -> rejeitado"]


@pytest.mark.parametrize("idioma", ["pt-BR", "en"])
def test_partes_ausentes(idioma):
    assert dividir_resumo(_resumo(idioma, desvios=["d"])) == ("Plano X.", ["d"], [])
    assert dividir_resumo(_resumo(idioma, respostas=["p -> adotado"])) == ("Plano X.", [], ["p -> adotado"])
    assert dividir_resumo(_resumo(idioma, texto="", desvios=["d"])) == ("", ["d"], [])


def test_sem_marca_e_vazio():
    assert dividir_resumo("Só texto | com barra.") == ("Só texto | com barra.", [], [])
    assert dividir_resumo("") == ("", [], [])
    assert dividir_resumo(None) == ("", [], [])


def test_partes_resposta():
    assert partes_resposta("Violação x: a -> b. -> adotado (Realocada (pop 2).)") == \
        ("Violação x: a -> b.", "adotado", "Realocada (pop 2).")
    assert partes_resposta("ponto -> adotado (motivo (pop 2))") == ("ponto", "adotado", "motivo (pop 2)")
    assert partes_resposta("ponto -> rejeitado") == ("ponto", "rejeitado", None)
    assert partes_resposta("resposta livre") == ("resposta livre", None, None)


@pytest.mark.parametrize("idioma,rot_d,rot_r", [("pt-BR", "Desvios do baseline", "Respostas ao Crítico"),
                                                ("en", "Deviations from the baseline", "Replies to the Critic")])
def test_markdown_renderiza_listas(idioma, rot_d, rot_r):
    res = resultado_teste()
    res.plano.resumo = _resumo(idioma, desvios=["d1", "d2"], respostas=["p1 -> adotado (m1)"])
    md = render_markdown(res, regiao_teste(idioma))
    assert f"**{rot_d}:**\n\n- d1\n- d2\n" in md
    assert f"**{rot_r}:**\n\n- p1 → **adotado**: m1\n" in md
    assert "p1 -> adotado" not in md and " | " not in md.split(rot_d)[1].split("\n## ")[0]
