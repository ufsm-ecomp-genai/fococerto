"""Regressões da ablação LLM (25/10): falsos positivos do checar_citacoes que travavam o ciclo em impasse e a
memória de reignição gerada pelos dados. Dados SIMULADOS de teste (fakes), salvo o teste com o cache real."""
import pytest

from app.agents.aprendizado import aprender_entre_periodos, detectar_reignicao
from app.core.logging import LogExecucao
from app.core.models import Base, Designacao, Plano
from app.memory_client import MemoriaLocal
from app.tools.citacoes import checar_citacoes
from app.tools.memorias import interpretar_memorias
from tests.fakes import RepositorioFake, oc, rec, regiao_teste

CFG = regiao_teste()
BN = Base(id="bn", nome="Base Norte", lat=-10.0, lon=-47.0)
DIV = [{"nome": "Divinópolis do Tocantins", "pop": 7297, "dist_km": 9.5}]


def _cit(just, evid=(), occs=None, bases=(BN,), recurso="t1", base_id="bn", eta=None):
    occs = occs or [oc("a", -10.1, -47.0, 0.9, pop=7297, localidades=DIV)]
    recs = [rec(recurso, base_id)]
    from app.tools.geo import eta_recurso
    b = {x.id: x for x in bases}[base_id]
    e = eta if eta is not None else round(eta_recurso(recs[0], b, occs[0], CFG), 2)
    d = Designacao(recurso_id=recurso, ocorrencia_id="a", ordem=1, eta_h=e, justificativa=just,
                   evidencias=list(evid))
    return checar_citacoes(Plano(periodo="p", regiao="teste", designacoes=[d]), occs, list(bases), recursos=recs,
                           regiao_cfg=CFG)


# ------------------------------------------------------------------ localidade abreviada (prefixo)
def test_localidade_por_prefixo_inequivoco_sem_acento():
    assert _cit("Divinopolis a 9,5 km", ["loc:Divinopolis", "dist:Divinopolis:9.5"]) == []


def test_prefixo_ambiguo_entre_duas_localidades_da_ocorrencia_e_erro():
    locs = DIV + [{"nome": "Divinópolis de Goiás", "pop": 100, "dist_km": 12.0}]
    occs = [oc("a", -10.1, -47.0, 0.9, pop=7397, localidades=locs)]
    v = _cit("perto", ["loc:Divinopolis"], occs=occs)
    assert [x.evidencia["campo"] for x in v] == ["localidade"]


def test_localidade_inexistente_continua_errada():
    v = _cit("perto", ["loc:Gurupi"])
    assert [x.evidencia["campo"] for x in v] == ["localidade"]


def test_nome_curto_de_outra_ocorrencia_dentro_do_nome_completo_nao_e_erro():
    occs = [oc("a", -10.1, -47.0, 0.9, pop=7297, localidades=DIV),
            oc("b", -11.0, -47.0, 0.5, localidades=[{"nome": "Divinópolis", "pop": 50, "dist_km": 3.0}])]
    assert _cit("7.297 habitantes em Divinópolis do Tocantins", occs=occs) == []


# ------------------------------------------------------------------ "ETA ≤ 6 h" é o limite, não o ETA
@pytest.mark.parametrize("texto", ["único recurso terrestre com ETA ≤ 6 h", "NENHUM recurso chega em ≤6h",
                                   "conceicao chega excedendo o ETA máximo 6 h", "ETA dentro do limite de 6 h"])
def test_limite_de_eta_citado_nao_e_citacao_errada(texto):
    assert [x for x in _cit(texto) if x.evidencia["campo"] == "eta_texto"] == []


def test_eta_errado_com_comparador_continua_errado():
    v = _cit("ETA ≤ 4 h")  # 4 não é o limite (6): é um ETA citado e está errado
    assert [x.evidencia["campo"] for x in v] == ["eta_texto"]


def test_base_de_saida_citada_como_lugar_nas_evidencias():
    base = Base(id="sp", nome="Paranã (simulada)", lat=-10.0, lon=-47.0, simulada=True)
    occs = [oc("a", -10.1, -47.0, 0.4)]
    assert _cit("x", ["loc:Paranã"], occs=occs, bases=(base,), base_id="sp") == []
    v = _cit("x", ["dist:Paranã:80"], occs=occs, bases=(base,), base_id="sp")
    assert [x.evidencia["campo"] for x in v] == ["dist"]


# ------------------------------------------------------------------ memória de reignição
def _h(*ns, fim="2026-10-20"):
    from datetime import date, timedelta
    f = date.fromisoformat(fim)
    return [{"dia": (f - timedelta(days=len(ns) - 1 - i)).isoformat(), "n_focos": n} for i, n in enumerate(ns)]


def test_detectar_reignicao():
    a = detectar_reignicao(_h(0, 0, 0, 0, 6, 5, 0, 14), "2026-10-20")
    assert a and a["n_antes"] == 11 and a["n_depois"] == 14 and a["dias_sem_foco"] == 1
    assert detectar_reignicao(_h(0, 0, 0, 1, 10, 1, 3), "2026-10-20") is None      # sem intervalo
    assert detectar_reignicao(_h(0, 0, 0, 0, 1, 0, 0, 16), "2026-10-20") is None   # 1 foco isolado antes
    assert detectar_reignicao(_h(0, 0, 0, 0, 0, 0, 0, 9), "2026-10-20") is None    # nunca queimou antes
    assert detectar_reignicao(_h(5, 0, 2, 2, 2, 2), "2026-10-20") is None          # queima atual é antiga
    assert detectar_reignicao(_h(6, 0, 0, 0), "2026-10-20") is None                # não queima em P


def test_aprendizado_grava_reignicao_sem_depender_do_plano_anterior(tmp_path):
    p0, p1 = "2026-10-19", "2026-10-20"
    cel = "cel_-120_-470"
    repo = RepositorioFake({p0: [oc("cel_x", -10.2, -47.1, 0.5)],
                            p1: [oc(cel, -12.0, -47.0, 0.4, n_focos=14,
                                    localidades=[{"nome": "Lugarejo", "pop": 0, "dist_km": 20}])]},
                           [BN], {cel: _h(0, 0, 0, 0, 6, 5, 0, 14, fim=p1)})
    plano = Plano(periodo=p0, regiao="teste", designacoes=[], nao_atendidas=[], resumo="", rodada=1)
    mem, log = MemoriaLocal(), LogExecucao("teste", p1, pasta=tmp_path)
    g = aprender_entre_periodos("teste", p1, plano, repo, mem, log)
    assert len(g) == 1 and cel in g[0].texto and "Lugarejo" in g[0].texto and "reignição" in g[0].texto
    assert g[0].tipo == "derivada" and g[0].fonte == f"aprendizado:{p0}->{p1}"
    # vira reforço para a célula (o grafo sobe a prioridade e puxa a célula)
    leitura = interpretar_memorias(g, [BN], repo.ocorrencias("teste", p1), regiao="teste")
    assert cel in leitura.reforcos
    # idempotente
    assert aprender_entre_periodos("teste", p1, plano, repo, mem) == []
    assert len(mem.listar("teste")) == 1


def test_reignicao_com_dados_reais_do_cache(tmp_path):
    from app.data.repositorio import RepositorioCache
    try:
        repo = RepositorioCache()
        repo.ocorrencias("tocantins", "2026-10-19", top=5)
    except FileNotFoundError:
        pytest.skip("sem cache do Tocantins")
    plano = Plano(periodo="2026-10-19", regiao="tocantins", designacoes=[], nao_atendidas=[], resumo="", rodada=1)
    g = aprender_entre_periodos("tocantins", "2026-10-20", plano, repo, MemoriaLocal())
    textos = [m.texto for m in g]
    assert any("cel_-120_-470" in t and "reignição" in t for t in textos), textos
