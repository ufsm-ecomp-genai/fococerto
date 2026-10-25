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
                    web_dist=tmp_path / "sem_dist")
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
