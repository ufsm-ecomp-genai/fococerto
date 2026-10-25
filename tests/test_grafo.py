"""executar_periodo em modo offline com fakes (dados SIMULADOS de teste)."""
import json

import httpx
import pytest

from app.agents import critico
from app.agents.grafo import executar_periodo
from app.core.logging import LogExecucao
from app.core.models import Base, Cenario, VeredictoCritico
from app.llm import client
from tests.fakes import MemoriaFake, RepositorioFake, hist_agricola, hist_vegetacao, oc, rec, regiao_teste

CFG = regiao_teste()
BN = Base(id="bn", nome="Base Norte", lat=-10.0, lon=-47.0)
BS = Base(id="bs", nome="Base Sul", lat=-10.8, lon=-47.0)
P = "2026-10-24"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "offline")


def _rodar(tmp_path, occs, recursos, memoria=None, historicos=None, reserva=0, notas=(), **kw):
    repo = RepositorioFake({P: occs}, [BN, BS], historicos)
    memoria = memoria or MemoriaFake()
    log = LogExecucao("teste", P, pasta=tmp_path)
    cen = Cenario(regiao="teste", periodo=P, recursos=recursos, reserva=reserva, notas=list(notas))
    res = executar_periodo(CFG, cen, repo, memoria, log, modo=kw.pop("modo", "offline"), **kw)
    eventos = [json.loads(l) for l in log.caminho.read_text().splitlines()]
    return res, eventos, repo, memoria


def _pares(res):
    return {(d.recurso_id, d.ocorrencia_id) for d in res.plano.designacoes}


def _decisoes(eventos):
    return [e["evento"] for e in eventos if e["agente"] == "critico"]


def _cenario_analista():
    occs = [oc("cel_a", -10.1, -47.0, 0.7, pop=500, localidades=[{"nome": "Vila Alegre", "pop": 500, "dist_km": 4}]),
            oc("cel_b", -10.75, -47.0, 0.9, n_focos=2, frp_soma=10, frp_max=6),
            oc("cel_c", -10.7, -47.05, 0.6, n_focos=15, frp_soma=900, frp_max=120, dist_ti=3.0)]
    hist = {"cel_b": hist_agricola(), "cel_c": hist_vegetacao()}
    return occs, [rec("t1", "bn"), rec("t2", "bs")], hist


def _cenario_memoria():
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500, localidades=[{"nome": "Vila Alegre", "pop": 500, "dist_km": 4}])]
    mem = MemoriaFake()
    mem.gravar("teste", "Estrada que sai da Base Norte está alagada", "nota", "coordenador", confianca=0.9)
    mem.gravar("outra_regiao", "Base Sul alagada", "nota", "coordenador")  # não pode vazar de região
    return occs, [rec("t1", "bn"), rec("t2", "bs")], mem


# --------------------------------------------------------------------------------------------- casos
def test_aprova_direto(tmp_path):
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500), oc("cel_b", -10.7, -47.0, 0.7, pop=300)]
    res, ev, _, _ = _rodar(tmp_path, occs, [rec("t1", "bn"), rec("t2", "bs")])
    assert res.rodadas == 1 and res.escalacoes == [] and res.pareceres == []
    assert _pares(res) == {("t1", "cel_a"), ("t2", "cel_b")}
    assert _decisoes(ev) == ["aprova"]
    assert ev[0]["evento"] == "inicio" and ev[-1]["evento"] == "fim"
    assert all(set(e) >= {"t", "execucao", "regiao", "periodo", "agente", "evento", "dados", "modelo",
                          "routed_model", "receipt", "tokens", "latencia_s"} for e in ev)
    assert res.plano.resumo.startswith("[aprova]") and res.log_path


def test_rejeita_e_revisa_por_excecao_da_memoria(tmp_path):
    occs, recs, mem = _cenario_memoria()
    res, ev, _, _ = _rodar(tmp_path, occs, recs, memoria=mem)
    assert res.rodadas == 2 and res.escalacoes == []
    assert _pares(res) == {("t2", "cel_a")}  # evita a base com estrada alagada
    assert res.historico[0]["veredicto"]["decisao"] == "rejeita"
    assert res.historico[0]["veredicto"]["contra_proposta"] is not None
    assert any("Exceção aceita" in m for m in res.historico[0]["veredicto"]["motivos"])
    assert _decisoes(ev) == ["rejeita", "aprova"]
    assert [m.texto for m in res.memorias_usadas] == ["Estrada que sai da Base Norte está alagada"]
    assert any(e["evento"] == "violacao" and e["dados"]["regra"] == "restricao_memoria" for e in ev)


def test_memoria_substituida_nao_vale(tmp_path):
    occs, recs, mem = _cenario_memoria()
    antiga = mem.listar("teste")[0]
    mem.gravar("teste", "Estrada da Base Norte liberada", "nota", "coordenador", supersedes=antiga.id)
    res, ev, _, _ = _rodar(tmp_path, occs, recs, memoria=mem)
    assert res.rodadas == 1 and _pares(res) == {("t1", "cel_a")}
    lida = next(e for e in ev if e["evento"] == "memoria_lida")
    assert [m["id"] for m in lida["dados"]["substituidas"]] == [antiga.id]


def test_escala_exposicao_sem_recurso_viavel(tmp_path):
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500), oc("cel_longe", -12.9, -49.4, 0.9, pop=1000)]
    res, ev, _, _ = _rodar(tmp_path, occs, [rec("t1", "bn")])
    assert res.rodadas == 1
    assert [e["ocorrencia_id"] for e in res.escalacoes] == ["cel_longe"]
    assert "Obrigatória" in res.escalacoes[0]["motivo"]
    assert _pares(res) == {("t1", "cel_a")}
    assert "escala" in _decisoes(ev)


def test_analista_chamado_e_muda_o_plano(tmp_path):
    occs, recs, hist = _cenario_analista()
    res, ev, repo, _ = _rodar(tmp_path, occs, recs, historicos=hist)
    par = {p.ocorrencia_id: p for p in res.pareceres}
    assert par["cel_b"].conclusao == "queima_agricola_provavel" and par["cel_b"].confianca in ("media", "alta")
    assert par["cel_c"].conclusao == "incendio_vegetacao_provavel"
    assert len(par["cel_b"].consultas) >= 5 and ("cel_b", 7) in repo.consultas_historico
    assert ("t1", "cel_a") in _pares(res) and any(o == "cel_c" for _, o in _pares(res))
    assert "cel_b" in res.plano.nao_atendidas
    assert res.rodadas == 2 and res.escalacoes == []
    assert sum(1 for e in ev if e["agente"] == "analista" and e["evento"] == "consulta") >= 10
    pedidos = [e for e in ev if e["agente"] == "critico" and e["dados"].get("pedir_analista")]
    assert [p["dados"]["pedir_analista"] for p in pedidos] == [["cel_b"], ["cel_c"]]


def test_variante_b_sem_critico_llm(tmp_path):
    occs, recs, hist = _cenario_analista()
    res, ev, repo, _ = _rodar(tmp_path, occs, recs, historicos=hist, usar_critico_llm=False)
    assert res.pareceres == [] and repo.consultas_historico == []  # sem Analista
    assert ("t2", "cel_b") in _pares(res) and res.rodadas == 1
    assert all(e["dados"].get("origem") in (None, "checador") for e in ev if e["agente"] == "critico")
    # e também não julga a exceção da memória (é não rígida)
    occs, recs, mem = _cenario_memoria()
    res2, _, _, _ = _rodar(tmp_path, occs, recs, memoria=mem, usar_critico_llm=False)
    assert _pares(res2) == {("t1", "cel_a")}


def test_variante_d_sem_memoria(tmp_path):
    occs, recs, mem = _cenario_memoria()
    res, ev, _, mem = _rodar(tmp_path, occs, recs, memoria=mem, usar_memoria=False)
    assert mem.chamadas_recall == 0 and res.memorias_usadas == []
    assert _pares(res) == {("t1", "cel_a")} and res.rodadas == 1
    assert not any(e["evento"] == "memoria_lida" for e in ev)


def test_nota_do_periodo_vale_mesmo_sem_hmem(tmp_path):
    occs, recs, _ = _cenario_memoria()
    res, _, _, _ = _rodar(tmp_path, occs, recs, usar_memoria=False, notas=["estrada da Base Norte alagada"])
    assert _pares(res) == {("t2", "cel_a")}


def test_reserva_pedida_em_memoria(tmp_path):
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500), oc("cel_b", -10.7, -47.0, 0.7)]
    mem = MemoriaFake()
    mem.gravar("teste", "Coordenador prefere manter 1 equipe de reserva", "nota", "coordenador")
    res, _, _, _ = _rodar(tmp_path, occs, [rec("t1", "bn"), rec("t2", "bs")], memoria=mem)
    assert len(res.plano.reserva) == 1 and ("t1", "cel_a") in _pares(res)


def test_rejeicao_so_zona_cinzenta_na_ultima_rodada_nao_e_impasse(tmp_path, monkeypatch):
    """3 rejeições sem violação rígida: fica a contra-proposta do Crítico, motivo divergencia_zona_cinzenta, os
    motivos do Crítico no resumo; sem escalação genérica de impasse (a exposta está atendida)."""
    def rejeita(ctx, plano, vs, rodada):
        return VeredictoCritico(decisao="rejeita", motivos=["discordo do trade-off"],
                                contra_proposta=plano.model_copy(update={"resumo": "cp do crítico"}))
    monkeypatch.setattr(critico, "decidir_offline", rejeita)
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500)]
    res, ev, _, _ = _rodar(tmp_path, occs, [rec("t1", "bn")])
    assert res.rodadas == 3 and len(res.historico) == 3
    assert res.status == "aprova" and res.escalacoes == []
    assert not any((e.get("motivo") or "").startswith("Impasse") for e in res.escalacoes)
    assert "discordo do trade-off" in res.plano.resumo and "cp do crítico" in res.plano.resumo
    div = [e for e in ev if e["agente"] == "sistema" and e["dados"].get("motivo") == "divergencia_zona_cinzenta"]
    assert div and div[0]["dados"]["plano_escolhido"] == "contra_proposta_critico"
    assert not any(e["dados"].get("motivo") == "impasse" for e in ev if e["agente"] == "sistema")
    assert sum(1 for e in ev if e["agente"] == "planejador" and e["evento"] == "proposta") == 3


def test_divergencia_mantem_guarda_corpo_das_expostas(tmp_path, monkeypatch):
    monkeypatch.setattr(critico, "decidir_offline",
                        lambda *a, **k: VeredictoCritico(decisao="rejeita", motivos=["discordo"]))
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500), oc("cel_b", -10.15, -47.0, 0.7, pop=300)]
    res, _, _, _ = _rodar(tmp_path, occs, [rec("t1", "bn")])
    assert res.status == "escala"
    assert [e["ocorrencia_id"] for e in res.escalacoes] == ["cel_b"]
    assert res.escalacoes[0]["sugestao"] == "solicitar apoio externo"


def test_impasse_so_com_violacao_rigida_aberta(tmp_path, monkeypatch):
    from app.agents import grafo
    from app.core.models import Violacao
    rig = Violacao(regra="capacidade_excedida", ocorrencia_id="cel_a", recurso_id="t1", evidencia={},
                   sugestao="x", rigida=True)
    monkeypatch.setattr(grafo, "checar_regras", lambda *a, **k: [rig])
    monkeypatch.setattr(critico, "decidir_offline",
                        lambda *a, **k: VeredictoCritico(decisao="rejeita", motivos=["discordo"]))
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500)]
    res, ev, _, _ = _rodar(tmp_path, occs, [rec("t1", "bn")])
    assert res.rodadas == 3 and res.status == "escala"
    assert res.escalacoes[0]["ocorrencia_id"] is None and "Impasse" in res.escalacoes[0]["motivo"]
    assert "capacidade_excedida" in res.escalacoes[0]["motivo"]
    assert any(e["dados"].get("motivo") == "impasse" for e in ev if e["agente"] == "sistema")


def test_modo_llm_sem_nightshift_cai_no_offline_e_loga(tmp_path):
    occs, recs, hist = _cenario_analista()
    off, _, _, _ = _rodar(tmp_path, occs, recs, historicos=hist)
    res, ev, _, _ = _rodar(tmp_path, occs, recs, historicos=hist, modo="llm")
    assert _pares(res) == _pares(off) and res.rodadas == off.rodadas
    fb = [e for e in ev if e["evento"] == "llm_call" and e["dados"]["status"] == "fallback_offline"]
    assert {e["agente"] for e in fb} == {"planejador", "critico", "analista"}


# ------------------------------------------------- modo llm com transporte falso (não é o Nightshift real)
def test_modo_llm_ciclo_com_citacao_errada_corrigida(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nightshift")
    monkeypatch.setenv("METERLESS_BASE_URL", "http://nightshift.fake/v1")
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "tok")
    monkeypatch.setenv("LLM_BACKOFF_S", "0")
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500, localidades=[{"nome": "Vila Alegre", "pop": 500, "dist_km": 4}])]
    plano_errado = {"designacoes": [{"recurso_id": "t1", "ocorrencia_id": "cel_a",
                                     "justificativa": "Vila Alegre com 5000 habitantes", "evidencias": ["pop:5000"]}],
                    "resumo": "r", "desvios": []}
    plano_certo = {"designacoes": [{"recurso_id": "t1", "ocorrencia_id": "cel_a",
                                    "justificativa": "Vila Alegre com 500 habitantes", "evidencias": ["pop:500"]}],
                   "resumo": "r2", "desvios": []}
    respostas = {
        "planejador": [json.dumps(plano_errado), json.dumps(plano_certo)],
        "critico": ["isto não é json", json.dumps({"decisao": "rejeita", "motivos": ["população citada errada"],
                                                   "pedir_analista": [], "contra_proposta": None}),
                    json.dumps({"decisao": "aprova", "motivos": ["ok"], "pedir_analista": []})],
    }

    pedidos_planejador = []

    def post(url, headers, corpo, timeout_s):
        sistema = " ".join(m["content"] for m in corpo["messages"] if m["role"] == "system")
        papel = "planejador" if "Você é o **Planejador**" in sistema else "critico"
        if papel == "planejador":
            pedidos_planejador.append(" ".join(m["content"] for m in corpo["messages"] if m["role"] == "user"))
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "model": "meterless/auto", "choices": [{"message": {"content": respostas[papel].pop(0)}}],
            "usage": {"total_tokens": 10}, "meterless": {"receipt": {"id": f"r-{papel}", "routed_model": "nvidia/fake"}}})

    monkeypatch.setattr(client, "_post", post)
    res, ev, _, _ = _rodar(tmp_path, occs, [rec("t1", "bn")], modo="llm")
    assert res.rodadas == 2 and res.escalacoes == []
    assert res.historico[0]["veredicto"]["decisao"] == "rejeita"
    # a citação errada continua no histórico (métrica), mas foi corrigida antes do Crítico
    assert any(v["regra"] == "citacao_incorreta" for v in res.historico[0]["violacoes"])
    assert res.historico[0]["citacoes_corrigidas"] and "5000" not in res.historico[0]["plano"]["designacoes"][0][
        "justificativa"]
    cc = [e for e in ev if e["evento"] == "citacao_corrigida"]
    assert cc and cc[0]["agente"] == "ferramenta" and cc[0]["dados"]["correcoes"][0]["citado"] in ("5000", 5000.0)
    assert cc[0]["dados"]["correcoes"][0]["real"] == 500
    assert res.historico[1]["violacoes"] == []
    # rodada 2: o Planejador recebeu os pontos do Crítico para responder
    assert "pontos_do_critico_a_responder" in pedidos_planejador[1] and "população citada errada" in \
        pedidos_planejador[1]
    chamadas = [e for e in ev if e["evento"] == "llm_call"]
    assert any(e["dados"]["status"] == "json_invalido" for e in chamadas)  # retry de JSON do Crítico
    assert all(e["routed_model"] == "nvidia/fake" for e in chamadas if e["dados"]["status"] == "ok")
    assert respostas == {"planejador": [], "critico": []}
