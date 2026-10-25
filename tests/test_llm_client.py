"""Cliente LLM com transporte falso (nenhuma rede). NÃO substitui um teste contra o Nightshift real."""
import json

import httpx
import pytest

from app.core.logging import LogExecucao
from app.llm import client


@pytest.fixture
def nightshift(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nightshift")
    monkeypatch.setenv("METERLESS_BASE_URL", "http://nightshift.fake/v1")
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "tok-teste")
    monkeypatch.setenv("LLM_BACKOFF_S", "0")
    monkeypatch.setenv("LLM_RETRIES", "2")


def _resp(status=200, conteudo="ok", extra=None, headers=None):
    corpo = {"model": "meterless/auto", "choices": [{"message": {"content": conteudo}}],
             "usage": {"total_tokens": 42}}
    corpo.update(extra or {})
    return httpx.Response(status, json=corpo, headers=headers or {},
                          request=httpx.Request("POST", "http://nightshift.fake/v1/chat/completions"))


def test_offline_nao_chama_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    with pytest.raises(client.LLMIndisponivel):
        client.chat([{"role": "user", "content": "oi"}], "planejador")


def test_chat_extrai_receipt_routed_model_e_loga(nightshift, monkeypatch, tmp_path):
    vistos = {}

    def post(url, headers, corpo, timeout_s):
        vistos.update(url=url, headers=headers, corpo=corpo)
        return _resp(conteudo='```json\n{"a": 1}\n```',
                     extra={"meterless": {"receipt": {"id": "rcpt_123", "routed_model": "nvidia/nemotron-x"}}})

    monkeypatch.setattr(client, "_post", post)
    log = LogExecucao("teste", "p", pasta=tmp_path)
    r = client.chat([{"role": "user", "content": "oi"}], "critico", json_schema={"type": "object"}, log=log)
    assert r.json == {"a": 1} and r.tokens == 42
    assert r.routed_model == "nvidia/nemotron-x" and r.receipt == "rcpt_123"
    assert vistos["url"].endswith("/chat/completions")
    assert vistos["headers"]["Authorization"] == "Bearer tok-teste" and vistos["headers"]["meterless-app"]
    linha = json.loads(log.caminho.read_text().splitlines()[0])
    assert linha["evento"] == "llm_call" and linha["agente"] == "critico"
    assert linha["routed_model"] == "nvidia/nemotron-x" and linha["receipt"] == "rcpt_123"
    assert linha["latencia_s"] is not None


def test_formato_real_do_nightshift(nightshift, monkeypatch, tmp_path):
    """Fixture com uma resposta REAL do Nightshift (Nemotron 3 Ultra): routed_model, recibo e raciocínio grudado."""
    from pathlib import Path
    real = json.loads((Path(__file__).parent / "fixtures" / "nightshift_resposta_real.json").read_text())
    assert client._extrair_meta(real, {}) == ("nvidia/nemotron-3-ultra-550b-a55b", "rcpt_req_79nabedm")
    real["choices"][0]["message"]["content"] = 'Vou pensar no plano {rascunho}.</think>{"decisao": "aprova"}'
    monkeypatch.setattr(client, "_post", lambda *a, **k: httpx.Response(
        200, json=real, request=httpx.Request("POST", "http://nightshift.fake/v1/chat/completions")))
    r = client.chat([{"role": "user", "content": "oi"}], "critico", json_schema={"type": "object"},
                    log=LogExecucao("teste", "p", pasta=tmp_path))
    assert r.texto == '{"decisao": "aprova"}' and r.json == {"decisao": "aprova"}
    assert r.routed_model == "nvidia/nemotron-3-ultra-550b-a55b" and r.receipt == "rcpt_req_79nabedm"


def test_limpar_raciocinio():
    assert client.limpar_raciocinio('The user wants "ok".</think>ok') == "ok"
    assert client.limpar_raciocinio("<think>a</think>resposta") == "resposta"
    assert client.limpar_raciocinio("sem raciocínio") == "sem raciocínio"


def test_receipt_em_cabecalho():
    routed, receipt = client._extrair_meta({"model": "x"}, {"X-Meterless-Receipt": "r9",
                                                            "X-Meterless-Routed-Model": "nvidia/n"})
    assert (routed, receipt) == ("nvidia/n", "r9")


def test_retry_com_backoff_em_502_e_timeout(nightshift, monkeypatch):
    seq = [_resp(502), httpx.ReadTimeout("lento"), _resp(conteudo="feito")]

    def post(*a, **k):
        x = seq.pop(0)
        if isinstance(x, Exception):
            raise x
        return x

    monkeypatch.setattr(client, "_post", post)
    assert client.chat([{"role": "user", "content": "oi"}], "planejador").texto == "feito"


def test_desiste_depois_dos_retries(nightshift, monkeypatch, tmp_path):
    monkeypatch.setattr(client, "_post", lambda *a, **k: _resp(503))
    log = LogExecucao("teste", "p", pasta=tmp_path)
    with pytest.raises(client.LLMIndisponivel):
        client.chat([{"role": "user", "content": "oi"}], "planejador", log=log)
    assert '"status": "erro"' in log.caminho.read_text()


def test_extrair_json_tolerante():
    assert client.extrair_json('Claro! {"x": {"y": "}"}} fim') == {"x": {"y": "}"}}
    assert client.extrair_json("<think>{nada}</think>{\"ok\": true}") == {"ok": True}
    assert client.extrair_json("sem json") is None
