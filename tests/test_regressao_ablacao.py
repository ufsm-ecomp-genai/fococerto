"""Regressão dos 7 bugs achados pela ablação offline (eval/RELATORIO.md, "Bugs encontrados").

Dados SIMULADOS (fakes) exceto onde indicado (cache real do Tocantins em ``data/cache``).
"""
import json
from pathlib import Path

import pytest

from app.agents import critico, planejador
from app.agents.base import Contexto
from app.agents.grafo import executar_periodo
from app.core.config import cenario as carregar_cenario
from app.core.config import regiao as carregar_regiao
from app.core.logging import LogExecucao
from app.core.models import Base, Cenario, Designacao, Plano
from app.memory_client import MemoriaLocal
from app.tools.alocador import alocador_simples
from app.tools.citacoes import checar_citacoes
from app.tools.memorias import interpretar_memorias
from app.tools.monitor import monitor
from app.tools.regras import checar_regras
from tests.fakes import MemoriaFake, RepositorioFake, T0, hist_agricola, oc, rec, regiao_teste

RAIZ = Path(__file__).resolve().parents[1]
CFG = regiao_teste()
BN = Base(id="bn", nome="Base Norte", lat=-10.0, lon=-47.0)
BS = Base(id="bs", nome="Base Sul", lat=-10.8, lon=-47.0)
P = "2026-10-24"
TEXTO_DERIVADA = ("Derivada dos dados FIRMS (19/10): a célula {cel} teve 6 focos em 17/10 e 5 em 18/10 e nenhum em "
                  "19/10. Se voltar a ter focos, é reignição do mesmo fogo, não foco novo.")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "offline")


def _rodar(tmp_path, occs, recursos, memoria=None, historicos=None, anteriores=None, reserva=0, **kw):
    dados = {P: occs}
    if anteriores is not None:
        dados["2026-10-23"] = anteriores
    repo = RepositorioFake(dados, [BN, BS], historicos)
    log = LogExecucao("teste", P, pasta=tmp_path)
    cen = Cenario(regiao="teste", periodo=P, recursos=recursos, reserva=reserva)
    res = executar_periodo(CFG, cen, repo, memoria or MemoriaFake(), log, modo="offline", **kw)
    eventos = [json.loads(l) for l in log.caminho.read_text().splitlines()]
    return res, eventos


def _pares(res):
    return {(d.recurso_id, d.ocorrencia_id) for d in res.plano.designacoes}


# ------------------------------------------------------------------ bug 1: memória derivada não voltava
def test_bug1_recall_por_termo_nao_traz_a_memoria_longa():
    """Documenta a causa (limiar 0,35 do recall); a correção é no grafo, via listar()."""
    m = MemoriaLocal()
    m.gravar("teste", TEXTO_DERIVADA.format(cel="cel_-120_-470"), "derivada", "dados:firms", 0.9)
    assert m.recall("teste", "cel_-120_-470", k=5)[0] == []


def test_bug1_memoria_derivada_chega_aos_agentes_pelo_listar(tmp_path):
    mem = MemoriaLocal()
    gravada = mem.gravar("teste", TEXTO_DERIVADA.format(cel="cel_b"), "derivada", "dados:firms", 0.9)
    mem.gravar("outra", TEXTO_DERIVADA.format(cel="cel_b"), "derivada", "dados:firms", 0.9)  # outra região
    occs = [oc("cel_a", -10.1, -47.0, 0.8), oc("cel_b", -10.7, -47.0, 0.7)]
    res, ev = _rodar(tmp_path, occs, [rec("t1", "bn"), rec("t2", "bs")], memoria=mem)
    assert [m.id for m in res.memorias_usadas] == [gravada.id]
    lida = next(e for e in ev if e["evento"] == "memoria_lida" and "ativas" in e["dados"])
    assert lida["dados"]["vias"][gravada.id].startswith("listar:")


def test_bug1_memoria_substituida_fica_de_fora_no_listar(tmp_path):
    mem = MemoriaLocal()
    antiga = mem.gravar("teste", TEXTO_DERIVADA.format(cel="cel_b"), "derivada", "dados:firms", 0.9)
    nova = mem.gravar("teste", "Correção: a célula cel_b não queimou em 17/10; o fogo foi outro.", "derivada",
                      "dados:firms", 0.9, supersedes=antiga.id)
    occs = [oc("cel_a", -10.1, -47.0, 0.8), oc("cel_b", -10.7, -47.0, 0.7)]
    res, _ = _rodar(tmp_path, occs, [rec("t1", "bn"), rec("t2", "bs")], memoria=mem)
    assert [m.id for m in res.memorias_usadas] == [nova.id]


def _cenario_reignicao():
    occs = [oc("cel_a", -10.1, -47.0, 0.7, pop=500, localidades=[{"nome": "Vila Alegre", "pop": 500, "dist_km": 4}]),
            oc("cel_b", -10.75, -47.0, 0.9, n_focos=2, frp_soma=10, frp_max=6),
            oc("cel_c", -10.7, -47.05, 0.6, n_focos=15, frp_soma=900, frp_max=120, dist_ti=3.0)]
    return occs, [rec("t1", "bn"), rec("t2", "bs")], {"cel_b": hist_agricola()}


def test_bug1_memoria_de_reignicao_pesa_contra_o_rebaixamento(tmp_path):
    occs, recs, hist = _cenario_reignicao()
    sem, _ = _rodar(tmp_path, occs, recs, historicos=hist)
    assert "cel_b" in sem.plano.nao_atendidas  # sem memória: queima agrícola, rebaixada (comportamento esperado)
    mem = MemoriaLocal()
    m = mem.gravar("teste", TEXTO_DERIVADA.format(cel="cel_b"), "derivada", "dados:firms", 0.9)
    res, ev = _rodar(tmp_path, occs, recs, memoria=mem, historicos=hist)
    assert ("t2", "cel_b") in _pares(res)
    par = {p.ocorrencia_id: p for p in res.pareceres}
    assert any(m.id in e for e in par["cel_b"].evidencias)  # o Analista leu a memória
    motivos = [x for h in res.historico for x in h["veredicto"]["motivos"]]
    assert any(m.id in x and "cel_b" in x for x in motivos)  # e o Crítico pesou a memória


# ------------------------------------------------------------------ bug 2: localidades homônimas
def test_bug2_citacao_aceita_qualquer_localidade_homonima():
    locs = [{"nome": "Santa Maria do Tocantins", "pop": 3000, "dist_km": 10.4},
            {"nome": "Santa Maria do Tocantins", "pop": 3000, "dist_km": 14.3}]
    occs = [oc("cel_a", -10.1, -47.0, 0.9, pop=3000, localidades=locs)]
    recs = [rec("t1", "bn")]
    p = alocador_simples(occs, recs, [BN], CFG, reserva=0)
    assert any(e.startswith("dist:Santa Maria do Tocantins:10.4") for e in p.designacoes[0].evidencias)
    assert checar_citacoes(p, occs, [BN], recursos=recs, regiao_cfg=CFG) == []
    errado = p.model_copy(update={"designacoes": [p.designacoes[0].model_copy(update={
        "evidencias": ["dist:Santa Maria do Tocantins:30.0"]})]})
    assert [v.evidencia["campo"] for v in checar_citacoes(errado, occs, [BN], recursos=recs, regiao_cfg=CFG)] == ["dist"]


# ------------------------------------------------------------------ bug 3: Crítico escalava com texto falso
FALSO = " Cerca de 25.000 habitantes expostos."


def test_bug3_critico_reescreve_justificativa_falsa_em_vez_de_escalar():
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500, localidades=[{"nome": "Vila Alegre", "pop": 500, "dist_km": 4}])]
    recs = [rec("t1", "bn")]
    ctx = Contexto(regiao=CFG, periodo=P, ocorrencias=occs, recursos=recs, bases=[BN], reserva=0)
    p = alocador_simples(occs, recs, [BN], CFG, reserva=0)
    d = p.designacoes[0]
    p = p.model_copy(update={"designacoes": [d.model_copy(update={"justificativa": d.justificativa + FALSO})]})
    vs = checar_citacoes(p, occs, [BN], recursos=recs, regiao_cfg=CFG)
    assert [v.regra for v in vs] == ["citacao_incorreta"]
    v = critico.decidir_offline(ctx, p, vs, 1)
    assert v.decisao == "rejeita" and v.contra_proposta is not None
    assert "25.000" not in v.contra_proposta.designacoes[0].justificativa
    assert checar_citacoes(v.contra_proposta, occs, [BN], recursos=recs, regiao_cfg=CFG) == []


def test_bug3_plano_final_nunca_tem_citacao_falsa(tmp_path, monkeypatch):
    original = planejador.decidir_offline

    def com_fato_errado(ctx, rodada, veredicto=None, violacoes=None):
        p = original(ctx, rodada, veredicto, violacoes)
        if rodada == 1:
            ds = [d.model_copy(update={"justificativa": d.justificativa + FALSO}) if d.ocorrencia_id == "cel_a" else d
                  for d in p.designacoes]
            p = p.model_copy(update={"designacoes": ds})
        return p

    monkeypatch.setattr(planejador, "decidir_offline", com_fato_errado)
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500, localidades=[{"nome": "Vila Alegre", "pop": 500, "dist_km": 4}]),
            oc("cel_longe", -12.9, -49.4, 0.9, pop=1000)]  # sem recurso viável: escalação obrigatória
    recs = [rec("t1", "bn")]
    res, _ = _rodar(tmp_path, occs, recs)
    assert res.status == "escala" and ("t1", "cel_a") in _pares(res)
    assert all("25.000" not in d.justificativa for d in res.plano.designacoes)
    assert checar_citacoes(res.plano, occs, [BN, BS], recursos=recs, regiao_cfg=CFG) == []
    assert [e["ocorrencia_id"] for e in res.escalacoes] == ["cel_longe"]


# ------------------------------------------------------------------ bug 4: histórico sem o dia do período (cache real)
def test_bug4_historico_do_analista_inclui_o_dia_do_periodo(tmp_path):
    from app.data.repositorio import RepositorioCache
    repo = RepositorioCache(raiz=RAIZ / "data" / "cache", estado=tmp_path / "estado")
    cen = carregar_cenario(RAIZ / "cenarios" / "tocantins-escasso.yaml")
    log = LogExecucao(cen.regiao, cen.periodo, pasta=tmp_path)
    res = executar_periodo(carregar_regiao(cen.regiao), cen, repo, MemoriaLocal(), log, modo="offline")
    oid = res.ocorrencias[0].id
    assert repo.historico_celula(oid)[-1]["dia"] == cen.periodo


# ------------------------------------------------------------------ bug 5: monitor e o corte top 100
def test_bug5_celula_com_periodos_seguidos_nao_e_nova_sem_par():
    o = oc("cel_x", -10.1, -47.0, 0.5, periodos_seguidos=5)
    assert monitor([o], [])[0].status != "nova"
    assert monitor([oc("cel_y", -10.1, -47.0, 0.5, periodos_seguidos=1)], [])[0].status == "nova"


def test_bug5_grafo_compara_com_todas_as_anteriores(tmp_path):
    anteriores = [oc(f"cel_{i}", -10.0, -47.0, 0.9 - i * 0.001) for i in range(150)]
    anteriores.append(oc("cel_alvo", -10.1, -47.0, 0.01, n_focos=4, frp_soma=40))  # fora do top 100 de ontem
    atual = oc("cel_alvo", -10.1, -47.0, 0.8, n_focos=4, frp_soma=40)
    res, _ = _rodar(tmp_path, [atual], [rec("t1", "bn")], anteriores=anteriores)
    assert res.ocorrencias[0].status == "estavel"


# ------------------------------------------------------------------ bug 6: base casada por palavra genérica
BASES_SIM = [Base(id="sim_paraiso", nome="Paraíso do Tocantins (simulada)", lat=-10.2, lon=-48.9, simulada=True),
             Base(id="sim_porto", nome="Porto Nacional (simulada)", lat=-10.7, lon=-48.4, simulada=True),
             Base(id="sim_gurupi", nome="Gurupi (simulada)", lat=-11.7, lon=-49.1, simulada=True),
             Base(id="osm_1", nome="1º Batalhão de Bombeiros Militar", lat=-10.2, lon=-48.3),
             Base(id="osm_2", nome="Corpo de Bombeiros Militar", lat=-13.3, lon=-50.2)]


def _nota(texto, i=0):
    return MemoriaFake().gravar("tocantins", texto, "nota", "coordenador").model_copy(
        update={"id": f"n{i}", "criada_em": T0})


@pytest.mark.parametrize("texto,esperado", [
    ("Estrada alagada perto de Porto Nacional, no Tocantins", {"sim_porto"}),
    ("A base simulada de Gurupi está com a estrada bloqueada", {"sim_gurupi"}),
    ("Saída da base de Paraíso interditada", {"sim_paraiso"}),
    ("Paraíso do Tocantins: ponte caiu", {"sim_paraiso"}),
    ("Estrada dos bombeiros militares de Palmas alagada", set()),
])
def test_bug6_base_so_casa_pelo_nome_distintivo(texto, esperado):
    leitura = interpretar_memorias([_nota(texto)], BASES_SIM, [])
    assert set(leitura.bases_bloqueadas) == esperado


# ------------------------------------------------------------------ bug 7: exposta_sem_recurso sem recurso liberável
def test_bug7_exposta_sem_recurso_so_e_rigida_se_o_recurso_chega_a_exposta():
    BF = Base(id="bf", nome="Base Longe", lat=-12.9, lon=-49.4)
    occs = [oc("vida", -10.1, -47.0, 0.5, pop=300), oc("outra", -10.2, -47.0, 0.9, pop=100),
            oc("mato", -12.8, -49.4, 0.9)]
    recs = [rec("t1", "bf"), rec("t2", "bn")]
    plano = Plano(periodo=P, regiao="teste", designacoes=[
        Designacao(recurso_id="t1", ocorrencia_id="mato", ordem=1, eta_h=0.4, justificativa="x"),
        Designacao(recurso_id="t2", ocorrencia_id="outra", ordem=2, eta_h=0.4, justificativa="x")])
    v = {x.ocorrencia_id: x for x in checar_regras(plano, occs, recs, [BN, BF], CFG, [])}
    assert v["vida"].regra == "exposta_nao_atendida" and not v["vida"].rigida
    # controle: se o recurso da ocorrência sem exposição chega à exposta, continua rígida
    recs2 = [rec("t1", "bn"), rec("t2", "bn")]
    v2 = {x.ocorrencia_id: x for x in checar_regras(plano.model_copy(update={"designacoes": [
        Designacao(recurso_id="t1", ocorrencia_id="mato", ordem=1, eta_h=0.4, justificativa="x")]}),
        [occs[0], occs[2]], recs2[:1], [BN], CFG, [])}
    assert v2["vida"].regra == "exposta_sem_recurso" and v2["vida"].rigida
    assert v2["vida"].evidencia["liberaveis"] == ["t1"]


def test_bug1_cliente_http_exclui_substituida_por_conflito_resolvido(tmp_path):
    """Conflito resolvido pelo engine marca só ``substituida_por`` na perdedora (sem ``supersedes`` na vencedora)."""
    import httpx

    from app.memory_client import ClienteHMEM

    def mem(i, texto, substituida_por=None):
        return {"id": f"teste:mem-{i}", "regiao": "teste", "texto": texto, "tipo": "derivada", "fonte": "dados:firms",
                "confianca": 0.9, "supersedes": None, "substituida_por": substituida_por,
                "criada_em": "2026-10-24T12:00:00+00:00"}

    lista = [mem(1, TEXTO_DERIVADA.format(cel="cel_b"), substituida_por="teste:mem-2"),
             mem(2, "A célula cel_b foi checada em campo: era queima de pasto, apagada.")]

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/recall":
            return httpx.Response(200, json={"memorias": [], "substituidas": [], "trace": {}})
        return httpx.Response(200, json=lista)

    cli = ClienteHMEM("http://hmem", client=httpx.Client(base_url="http://hmem", transport=httpx.MockTransport(handler)))
    occs = [oc("cel_a", -10.1, -47.0, 0.8), oc("cel_b", -10.7, -47.0, 0.7)]
    res, _ = _rodar(tmp_path, occs, [rec("t1", "bn"), rec("t2", "bs")], memoria=cli)
    assert [m.id for m in res.memorias_usadas] == ["teste:mem-2"]
    assert cli.substituida_por("teste:mem-1") == "teste:mem-2"
