"""decidir() com JSON inválido cai no decidir_offline (e loga); decidir_offline sem LLM."""
import json

import httpx
import pytest

from app.agents import analista, planejador
from app.agents.base import Contexto
from app.core.logging import LogExecucao
from app.core.models import Base
from app.llm import client
from app.tools.consultar import Consultor
from tests.fakes import RepositorioFake, hist_agricola, oc, rec, regiao_teste

CFG = regiao_teste()
BN = Base(id="bn", nome="Base Norte", lat=-10.0, lon=-47.0)


@pytest.fixture
def llm_falso(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nightshift")
    monkeypatch.setenv("METERLESS_BASE_URL", "http://nightshift.fake/v1")
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "tok")
    monkeypatch.setenv("LLM_BACKOFF_S", "0")
    respostas: list[str] = []

    def post(url, headers, corpo, timeout_s):
        return httpx.Response(200, request=httpx.Request("POST", url),
                              json={"model": "m", "choices": [{"message": {"content": respostas.pop(0)}}]})

    monkeypatch.setattr(client, "_post", post)
    return respostas


def _ctx():
    occs = [oc("cel_b", -10.1, -47.0, 0.9, n_focos=2, frp_soma=10)]
    return Contexto(regiao=CFG, periodo="p", ocorrencias=occs, recursos=[rec("t1", "bn")], bases=[BN], reserva=0)


def test_analista_json_invalido_duas_vezes_cai_no_offline(llm_falso, tmp_path):
    llm_falso += ["nada de json", json.dumps({"conclusao": "talvez", "confianca": "alta", "evidencias": []})]
    log = LogExecucao("t", "p", pasta=tmp_path)
    ctx = _ctx()
    p = analista.decidir(ctx, "cel_b", Consultor(RepositorioFake({}, [], {"cel_b": hist_agricola()}), ctx.ocorrencias),
                         log)
    assert p.conclusao == "queima_agricola_provavel" and p.consultas
    st = [json.loads(l)["dados"]["status"] for l in log.caminho.read_text().splitlines()
          if json.loads(l)["evento"] == "llm_call"]
    assert st == ["ok", "json_invalido", "ok", "json_invalido", "fallback_offline"]


def test_analista_llm_pede_consulta_extra(llm_falso, tmp_path):
    llm_falso += [json.dumps({"conclusao": "indeterminado", "confianca": "baixa", "evidencias": ["x"],
                              "mais_consultas": ["historico_celula:14"]}),
                  json.dumps({"conclusao": "queima_agricola_provavel", "confianca": "media", "evidencias": ["y"]})]
    repo = RepositorioFake({}, [], {"cel_b": hist_agricola(14)})
    ctx = _ctx()
    p = analista.decidir(ctx, "cel_b", Consultor(repo, ctx.ocorrencias), LogExecucao("t", "p", pasta=tmp_path))
    assert p.conclusao == "queima_agricola_provavel" and p.confianca == "media"
    assert ("cel_b", 14) in repo.consultas_historico and "historico_celula(cel_b, dias=14)" in p.consultas


def test_planejador_rejeita_id_inventado_e_cai_no_offline(llm_falso, tmp_path):
    inventado = json.dumps({"designacoes": [{"recurso_id": "helicoptero_x", "ocorrencia_id": "cel_b",
                                             "justificativa": "j"}], "resumo": "r"})
    llm_falso += [inventado, inventado]
    plano = planejador.decidir(_ctx(), 1, LogExecucao("t", "p", pasta=tmp_path))
    assert [(d.recurso_id, d.ocorrencia_id) for d in plano.designacoes] == [("t1", "cel_b")]
    assert "offline" in plano.resumo
