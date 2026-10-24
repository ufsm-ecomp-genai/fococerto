"""Memória derivada entre períodos (app/agents/aprendizado.py) e o efeito dela no período seguinte.

Dados SIMULADOS de teste (fakes), ids de célula no formato real (cel_<lat10>_<lon10>)."""
import json

import pytest

from app.agents.aprendizado import aprender_entre_periodos, plano_anterior
from app.agents.grafo import TOP, executar_periodo
from app.core.logging import LogExecucao
from app.core.models import Base, Cenario, Designacao, Plano
from app.data.repositorio import RepositorioCache
from app.memory_client import MemoriaLocal
from tests.fakes import RepositorioFake, oc, rec, regiao_teste

CFG = regiao_teste()
BN = Base(id="bn", nome="Base Norte", lat=-10.0, lon=-47.0)
P0, P1 = "2026-10-22", "2026-10-23"
A, B = "cel_-101_-470", "cel_-102_-471"
LOC_A = [{"nome": "Lizarda", "pop": 300, "dist_km": 30}]  # fora do raio de exposição: não é "exposta"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "offline")


def _plano(designadas=(), sem=()):
    ds = [Designacao(recurso_id=f"t{i}", ocorrencia_id=o, ordem=i + 1, eta_h=1.0, justificativa="x")
          for i, o in enumerate(designadas)]
    return Plano(periodo=P0, regiao="teste", designacoes=ds, nao_atendidas=list(sem), resumo="", rodada=1)


def _repo(n_a0, n_a1, n_b1=4, extras1=()):
    return RepositorioFake({
        P0: [oc(A, -10.1, -47.0, 0.4, n_focos=n_a0, localidades=LOC_A), oc(B, -10.2, -47.1, 0.5, n_focos=5)],
        P1: [oc(A, -10.1, -47.0, 0.4, n_focos=n_a1, localidades=LOC_A),
             oc(B, -10.2, -47.1, 0.5, n_focos=n_b1), *extras1],
    }, [BN])


def _eventos(log):
    return [json.loads(l) for l in log.caminho.read_text().splitlines()]


def test_grava_quando_cresce_sem_recurso(tmp_path):
    mem, log = MemoriaLocal(), LogExecucao("teste", P1, pasta=tmp_path)
    gravadas = aprender_entre_periodos("teste", P1, _plano(sem=[A]), _repo(3, 9), mem, log)
    assert len(gravadas) == 1
    m = gravadas[0]
    assert m.tipo == "derivada" and m.fonte == f"aprendizado:{P0}->{P1}"
    assert A in m.texto and "Lizarda" in m.texto and "cresceu de 3 para 9" in m.texto
    ev = [e for e in _eventos(log) if e["evento"] == "memoria_gravada"]
    assert ev and ev[0]["dados"]["memoria_id"] == m.id and ev[0]["dados"]["celula"] == A
    assert ev[0]["dados"]["n_focos_antes"] == 3 and ev[0]["dados"]["n_focos_depois"] == 9


def test_grava_quando_persiste_forte_e_ignora_quando_some(tmp_path):
    mem = MemoriaLocal()
    g = aprender_entre_periodos("teste", P1, _plano(sem=[A]), _repo(8, 7), mem)
    assert len(g) == 1 and "persistiu forte" in g[0].texto
    mem2 = MemoriaLocal()
    assert aprender_entre_periodos("teste", P1, _plano(sem=[A]), _repo(3, 0), mem2) == []
    assert aprender_entre_periodos("teste", P1, _plano(sem=[A]), _repo(3, 2), mem2) == []


def test_nao_grava_reforco_quando_foi_atendida(tmp_path):
    mem = MemoriaLocal()
    assert aprender_entre_periodos("teste", P1, _plano(designadas=[A]), _repo(3, 9), mem) == []
    # atendida e diminuiu: memória informativa, sem palavra de reforço
    g = aprender_entre_periodos("teste", P1, _plano(designadas=[A]), _repo(6, 1), MemoriaLocal())
    assert len(g) == 1 and "recebeu recurso" in g[0].texto and "cresceu" not in g[0].texto
    assert g[0].confianca < 0.8


def test_idempotente(tmp_path):
    mem = MemoriaLocal(caminho=tmp_path / "mem.json")
    repo = _repo(3, 9)
    assert len(aprender_entre_periodos("teste", P1, _plano(sem=[A]), repo, mem)) == 1
    assert aprender_entre_periodos("teste", P1, _plano(sem=[A]), repo, mem) == []
    assert aprender_entre_periodos("teste", P1, _plano(sem=[A]),
                                   repo, MemoriaLocal(caminho=tmp_path / "mem.json")) == []
    assert len(mem.listar("teste")) == 1


def _rodar(tmp_path, repo, memoria, usar_memoria=True):
    log = LogExecucao("teste", P1, pasta=tmp_path)
    cen = Cenario(regiao="teste", periodo=P1, recursos=[rec("t1", "bn")], reserva=0)
    return executar_periodo(CFG, cen, repo, memoria, log, modo="offline", usar_memoria=usar_memoria), _eventos(log)


def test_memoria_derivada_muda_a_decisao_no_periodo_seguinte(tmp_path):
    """Um recurso, duas ocorrências sem exposição: sem memória vai para B (prioridade maior); depois do
    aprendizado (A ficou sem recurso e cresceu), A ganha o reforço e o recurso."""
    repo = _repo(3, 9)
    sem, _ = _rodar(tmp_path, repo, MemoriaLocal(), usar_memoria=False)
    assert {d.ocorrencia_id for d in sem.plano.designacoes} == {B}

    mem = MemoriaLocal()
    aprender_entre_periodos("teste", P1, _plano(designadas=[B], sem=[A]), repo, mem)
    com, ev = _rodar(tmp_path, repo, mem)
    assert {d.ocorrencia_id for d in com.plano.designacoes} == {A}
    interp = [e["dados"]["interpretacao"] for e in ev if "interpretacao" in e["dados"]]
    assert interp and A in interp[0]["reforcos"]
    assert any(m.tipo == "derivada" and A in m.texto for m in com.memorias_usadas)


def test_memoria_derivada_puxa_celula_fora_do_top(tmp_path):
    """A célula que ficou sem recurso e cresceu está fora do top 15 de P: a memória a traz para a lista."""
    outras = [oc(f"cel_-{110 + i}_-460", -11.0 - i / 10, -46.0, 0.9 - i / 100, n_focos=2) for i in range(TOP)]
    repo = _repo(3, 9, extras1=outras)
    sem, _ = _rodar(tmp_path, repo, MemoriaLocal())
    assert A not in {o.id for o in sem.ocorrencias}
    mem = MemoriaLocal()
    aprender_entre_periodos("teste", P1, _plano(sem=[A]), repo, mem)
    com, ev = _rodar(tmp_path, repo, mem)
    assert A in {o.id for o in com.ocorrencias}
    puxadas = [e["dados"]["puxadas_por_memoria"] for e in ev if e["dados"].get("puxadas_por_memoria")]
    assert puxadas and puxadas[0][0]["ocorrencia_id"] == A


def test_plano_anterior_do_plano_json_e_das_decisoes_aprovadas(tmp_path):
    plano = _plano(designadas=[B], sem=[A])
    pasta = tmp_path / "out" / "teste" / P0
    pasta.mkdir(parents=True)
    (pasta / "plano.json").write_text(json.dumps({"meta": {}, "plano": plano.model_dump(mode="json")}))
    repo = RepositorioCache(estado=tmp_path / "estado")
    p, origem = plano_anterior("teste", P1, repo, tmp_path / "out")
    assert p is not None and p.nao_atendidas == [A] and origem.endswith("plano.json")

    aprovado = _plano(designadas=[A], sem=[B])
    repo.salvar_decisoes(aprovado, aprovado_por="coord")
    p, origem = plano_anterior("teste", P1, repo, tmp_path / "out")
    assert origem == "decisoes_aprovadas"
    assert [d.ocorrencia_id for d in p.designacoes] == [A] and p.nao_atendidas == [B]
    assert plano_anterior("teste", P0, repo, tmp_path / "out") == (None, None)
