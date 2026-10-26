"""API do front-end (app/api.py) com TestClient, em sample mode: sem rede, sem Zetaris, sem Nightshift.

O estado (memória, decisões, notas, saídas e logs) vai para tmp_path: os construtores da CLI são trocados por
versões que gravam lá, para o teste não tocar em data/estado/ nem em out/ do repositório."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app import cli  # noqa: E402
from app.api import criar_app  # noqa: E402
from app.core.config import RAIZ  # noqa: E402

CENARIO = "cenarios/tocantins-medio.yaml"


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    from app.data.repositorio import RepositorioCache
    from app.memory_client import MemoriaLocal
    estado = tmp_path / "estado"
    monkeypatch.setattr(cli, "criar_repositorio", lambda args: RepositorioCache(estado=estado))
    monkeypatch.setattr(cli, "criar_memoria",
                        lambda args: MemoriaLocal(caminho=estado / f"memoria_{args.regiao}.json"))
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    exemplos = tmp_path / "exemplos"
    shutil.copytree(RAIZ / "output_examples" / "tocantins-medio", exemplos / "tocantins-medio")
    app = criar_app(saida=tmp_path / "out", exemplos=exemplos, pasta_logs=tmp_path / "logs",
                    web_dist=tmp_path / "sem_dist", cenarios_dir=tmp_path / "cenarios_salvos")
    c = TestClient(app)
    c.tmp = tmp_path
    return c


def esperar(c: TestClient, jid: str, limite_s: float = 120) -> dict:
    t0 = time.monotonic()
    while time.monotonic() - t0 < limite_s:
        j = c.get(f"/api/jobs/{jid}").json()
        if j["status"] in ("concluido", "erro"):
            return j
        time.sleep(0.2)
    raise AssertionError(f"job {jid} não terminou em {limite_s}s")


def test_regioes_periodos_e_cenarios(cliente):
    rs = {r["nome"]: r for r in cliente.get("/api/regioes").json()}
    assert rs["tocantins"]["tem_cache"] is True and rs["tocantins"]["idioma"] == "pt-BR"
    p = cliente.get("/api/periodos", params={"regiao": "tocantins"}).json()
    assert "2026-10-23" in p["periodos_cache"] and p["periodos_com_plano"] == []
    assert cliente.get("/api/periodos", params={"regiao": "naoexiste"}).status_code == 404
    assert cliente.get("/api/periodos", params={"regiao": "../x"}).status_code == 400
    cens = {c["caminho"]: c for c in cliente.get("/api/cenarios").json()}
    assert cens[CENARIO]["simulado"] is True and cens[CENARIO]["recursos"] > 0


def test_exemplos(cliente):
    lista = cliente.get("/api/exemplos").json()
    assert [e["nome"] for e in lista] == ["tocantins-medio"] and lista[0]["tem_trace"]
    d = cliente.get("/api/exemplos/tocantins-medio").json()
    original = json.loads((RAIZ / "output_examples" / "tocantins-medio" / "plano.json").read_text(encoding="utf-8"))
    assert d == original
    assert cliente.get("/api/exemplos/nao-existe").status_code == 404
    tr = cliente.get("/api/exemplos/tocantins-medio/trace", params={"limite": 3}).json()
    assert len(tr) == 3 and {"agente", "evento"} <= set(tr[0])


def test_plano_inexistente_404_claro(cliente):
    r = cliente.get("/api/plano/tocantins/2026-10-23")
    assert r.status_code == 404 and "Não há plano" in r.json()["detail"]
    assert cliente.get("/api/plano/tocantins/23-10-2026").status_code == 400


def test_run_sample_job_plano_nota_e_aprovar(cliente):
    r = cliente.post("/api/run", json={"regiao": "tocantins", "recursos": CENARIO, "sample": True})
    assert r.status_code == 202
    j = esperar(cliente, r.json()["job_id"])
    assert j["status"] == "concluido", j.get("erro")
    assert j["progresso"] and any("Rodando o ciclo" in p["msg"] for p in j["progresso"])
    res = j["resultado"]
    assert res["plano_url"] == "/api/plano/tocantins/2026-10-23" and res["modo"] == "offline"
    plano = cliente.get(res["plano_url"]).json()
    assert plano["meta"]["simulado"] is True and plano["plano"]["designacoes"]
    assert len(plano["plano"]["designacoes"]) == res["designacoes"]
    assert (cliente.tmp / "out" / "tocantins" / "2026-10-23" / "mapa.html").exists()
    assert cliente.get("/api/periodos", params={"regiao": "tocantins"}).json()["periodos_com_plano"] == ["2026-10-23"]
    # o sample mode da CLI fixa LLM_PROVIDER=offline; o servidor restaura o ambiente depois do job
    import os
    assert "LLM_PROVIDER" not in os.environ

    n = cliente.post("/api/nota", json={"regiao": "tocantins", "periodo": "2026-10-23", "autor": "qa",
                                        "texto": "estrada para São Félix alagada", "sample": True})
    assert n.status_code == 200 and n.json()["memoria_id"]
    assert (cliente.tmp / "estado" / "tocantins" / "notas.jsonl").exists()

    a = cliente.post("/api/aprovar", json={"regiao": "tocantins", "periodo": "2026-10-23", "autor": "qa",
                                           "sample": True})
    assert a.status_code == 200 and a.json()["aprovado_por"] == "qa"
    linhas = (cliente.tmp / "estado" / "tocantins" / "decisoes.jsonl").read_text(encoding="utf-8").splitlines()
    assert linhas


def test_aprovar_sem_plano_e_validacoes(cliente):
    r = cliente.post("/api/aprovar", json={"regiao": "tocantins", "periodo": "2026-10-19", "autor": "qa",
                                           "sample": True})
    assert r.status_code == 404 and "Não há plano" in r.json()["detail"]
    assert cliente.post("/api/nota", json={"regiao": "tocantins", "texto": "  ", "autor": "qa"}).status_code == 400
    assert cliente.post("/api/run", json={"regiao": "tocantins", "recursos": "/etc/passwd"}).status_code == 400
    assert cliente.post("/api/run", json={"regiao": "tocantins", "recursos": "cenarios/nao.yaml"}).status_code == 404
    assert cliente.get("/api/jobs/naoexiste").status_code == 404


def test_run_com_erro_vira_job_com_erro(cliente):
    """Cenário de outra região: a CLI recusa, e o erro aparece no job (o servidor não cai)."""
    r = cliente.post("/api/run", json={"regiao": "iberia", "recursos": CENARIO, "sample": True})
    j = esperar(cliente, r.json()["job_id"])
    assert j["status"] == "erro" and "região" in j["erro"]


def test_cors_localhost(cliente):
    r = cliente.options("/api/regioes", headers={"Origin": "http://localhost:5173",
                                                 "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = cliente.get("/api/regioes", headers={"Origin": "https://exemplo.com"})
    assert "access-control-allow-origin" not in r.headers


def test_serve_web_dist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>FocoCerto</title>", encoding="utf-8")
    c = TestClient(criar_app(saida=tmp_path / "out", exemplos=tmp_path / "ex", web_dist=dist))
    assert "FocoCerto" in c.get("/").text
    assert c.get("/api/saude").json()["ok"] is True


# ----------------------------------------------------------------------------- tela "Recursos do dia" (CONTRATOS §21)
def cenario_tela() -> dict:
    """Cenário como a tela monta: equipes em bases conhecidas e numa base nova, declarada clicando no mapa."""
    return {"regiao": "tocantins", "periodo": "2026-10-23", "simulado": True, "reserva": 1,
            "notas": ["ponte do rio Sono interditada"],
            "bases": [{"id": "decl_novo_acordo", "nome": "Brigada municipal de Novo Acordo", "lat": -9.97,
                       "lon": -47.68, "fonte": "coordenador (tela)"}],
            "recursos": [
                {"id": "palmas-t1", "base_id": "osm_n5067657890", "tipo": "terrestre", "capacidade": 1, "disponivel": True},
                {"id": "palmas-a1", "base_id": "osm_n5067657890", "tipo": "aereo", "capacidade": 1, "disponivel": True},
                {"id": "gurupi-t1", "base_id": "cbmto_gurupi", "tipo": "terrestre", "capacidade": 1, "disponivel": True},
                {"id": "novoacordo-t1", "base_id": "decl_novo_acordo", "tipo": "terrestre", "capacidade": 1,
                 "disponivel": True}]}


def test_bases_da_regiao(cliente):
    r = cliente.get("/api/bases", params={"regiao": "tocantins", "sample": True})
    assert r.status_code == 200
    d = r.json()
    assert d["repositorio"] == "RepositorioCache" and "2026-10-23" in d["periodos"]
    por_id = {b["id"]: b for b in d["bases"]}
    palmas = por_id["osm_n5067657890"]
    assert palmas["confianca"] == "oficial" and palmas["orgao"] == "CBMTO" and palmas["data_fonte"]
    assert palmas["fonte"] and palmas["fonte_url"].startswith("http")
    assert all({"id", "nome", "lat", "lon", "confianca", "fonte"} <= set(b) for b in d["bases"])
    assert any(b["confianca"] == "osm" for b in d["bases"])
    r = cliente.get("/api/bases", params={"regiao": "naoexiste"})
    assert r.status_code == 404 and "naoexiste" in r.json()["detail"]
    assert cliente.get("/api/bases", params={"regiao": "../x"}).status_code == 400


def test_run_com_cenario_da_tela_em_ingles(cliente):
    antes = sorted(p.name for p in (RAIZ / "cenarios").iterdir())
    r = cliente.post("/api/run", json={"regiao": "tocantins", "cenario": cenario_tela(), "sample": True,
                                       "idioma": "en"})
    assert r.status_code == 202, r.text
    j = esperar(cliente, r.json()["job_id"])
    assert j["status"] == "concluido", j.get("erro")
    assert j["resultado"]["idioma"] == "en" and j["resultado"]["designacoes"] > 0
    assert any("4 recursos" in p["msg"] for p in j["progresso"])
    plano = cliente.get(j["resultado"]["plano_url"]).json()
    assert plano["meta"]["idioma"] == "en" and plano["meta"]["simulado"] is True
    assert "POST /api/run" in plano["meta"]["arquivo_cenario"]
    decl = [b for b in plano["bases"] if b["id"] == "decl_novo_acordo"]
    assert decl and decl[0]["confianca"] == "declarada"
    assert {r["id"] for r in plano["recursos"]} == {"palmas-t1", "palmas-a1", "gurupi-t1", "novoacordo-t1"}
    # o cenário da tela não vira arquivo em cenarios/ do repositório
    assert sorted(p.name for p in (RAIZ / "cenarios").iterdir()) == antes


def test_run_cenario_invalido_422(cliente):
    c = cenario_tela()
    c["recursos"][1]["id"] = "palmas-t1"           # id duplicado
    c["recursos"][2]["base_id"] = "cbmto_nao_existe"  # base inexistente
    r = cliente.post("/api/run", json={"regiao": "tocantins", "cenario": c, "sample": True})
    assert r.status_code == 422
    msgs = [e["msg"] for e in r.json()["detail"]]
    assert any("repetido: 'palmas-t1'" in m for m in msgs)
    assert any("'cbmto_nao_existe'" in m and "não existe" in m for m in msgs)
    locs = [e["loc"] for e in r.json()["detail"]]
    assert ["body", "cenario", "recursos", 2, "base_id"] in locs

    c = cenario_tela()
    c["recursos"][0]["tipo"] = "helicoptero"
    assert cliente.post("/api/run", json={"regiao": "tocantins", "cenario": c, "sample": True}).status_code == 422
    c = cenario_tela()
    c["periodo"] = "2026-09-01"
    r = cliente.post("/api/run", json={"regiao": "tocantins", "cenario": c, "sample": True})
    assert r.status_code == 422 and "dias disponíveis" in r.json()["detail"][0]["msg"]
    # nem recursos nem cenario / os dois
    assert cliente.post("/api/run", json={"regiao": "tocantins", "sample": True}).status_code == 422
    assert cliente.post("/api/run", json={"regiao": "tocantins", "recursos": CENARIO, "cenario": cenario_tela(),
                                          "sample": True}).status_code == 422
    assert cliente.get("/api/jobs").json() == []


def test_salvar_listar_e_carregar_cenario(cliente):
    r = cliente.post("/api/cenarios", json={"nome": "meu-dia_23", "cenario": cenario_tela(), "sample": True})
    assert r.status_code == 201 and r.json()["substituido"] is False
    assert (cliente.tmp / "cenarios_salvos" / "meu-dia_23.yaml").exists()
    lista = cliente.get("/api/cenarios").json()
    salvo = next(c for c in lista if c["nome"] == "meu-dia_23")
    assert salvo["origem"] == "salvo" and salvo["recursos"] == 4 and salvo["bases_declaradas"] == 1
    assert next(c for c in lista if c["caminho"] == CENARIO)["origem"] == "repositorio"
    d = cliente.get("/api/cenarios/meu-dia_23").json()
    assert d["origem"] == "salvo" and d["cenario"]["bases"][0]["confianca"] == "declarada"
    assert d["cenario"]["periodo"] == "2026-10-23" and len(d["cenario"]["recursos"]) == 4
    # o objeto carregado roda de novo sem mudança
    r = cliente.post("/api/run", json={"regiao": "tocantins", "cenario": d["cenario"], "sample": True})
    assert esperar(cliente, r.json()["job_id"])["status"] == "concluido"
    # salvar de novo substitui o salvo
    assert cliente.post("/api/cenarios", json={"nome": "meu-dia_23", "cenario": cenario_tela(),
                                               "sample": True}).json()["substituido"] is True
    rep = cliente.get("/api/cenarios/tocantins-medio").json()
    assert rep["origem"] == "repositorio" and rep["caminho"] == CENARIO
    assert cliente.get("/api/cenarios/nao-existe").status_code == 404


def test_cenario_nome_invalido_e_repositorio_protegido(cliente):
    for nome in ("../x", "com espaço", "a.yaml", ""):
        r = cliente.post("/api/cenarios", json={"nome": nome, "cenario": cenario_tela(), "sample": True})
        assert r.status_code == 400, nome
    antes = (RAIZ / CENARIO).read_text(encoding="utf-8")
    r = cliente.post("/api/cenarios", json={"nome": "tocantins-medio", "cenario": cenario_tela(), "sample": True})
    assert r.status_code == 409 and "repositório" in r.json()["detail"]
    assert (RAIZ / CENARIO).read_text(encoding="utf-8") == antes
    assert not (cliente.tmp / "cenarios_salvos" / "tocantins-medio.yaml").exists()
    c = cenario_tela()
    c["recursos"][0]["base_id"] = "nao_existe"
    r = cliente.post("/api/cenarios", json={"nome": "ok", "cenario": c, "sample": True})
    assert r.status_code == 422 and not (cliente.tmp / "cenarios_salvos" / "ok.yaml").exists()
