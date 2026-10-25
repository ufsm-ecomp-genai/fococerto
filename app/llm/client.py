"""Cliente LLM do FocoCerto (docs/CONTRATOS.md, seção 4).

Providers (variável LLM_PROVIDER):
- ``nightshift``: Meterless Nightshift, compatível com OpenAI (POST {METERLESS_BASE_URL}/chat/completions),
  com o token METERLESS_RUNTIME_TOKEN e o modelo METERLESS_MODEL (padrão ``meterless/auto``).
  **NÃO TESTADO contra um Nightshift real** (não havia Nightshift nesta máquina no desenvolvimento).
  O formato exato do *receipt* não está documentado; ``_extrair_meta`` procura ``routed_model`` e o
  receipt de forma tolerante no corpo e nos cabeçalhos da resposta.
- ``offline``: não chama LLM nenhum. ``chat`` levanta ``LLMIndisponivel`` e os agentes usam o próprio
  ``decidir_offline()``.

Toda chamada (sucesso ou falha) vira uma linha ``llm_call`` no log, com modelo, routed_model, receipt,
tokens e latência. Nunca chamamos a NVIDIA direto: tudo passa pelo Nightshift.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import env
from app.core.logging import LogExecucao


@dataclass
class LLMResult:
    texto: str
    modelo: str
    json: dict | None = None
    routed_model: str | None = None
    receipt: str | None = None
    tokens: int | None = None
    latencia_s: float = 0.0


class LLMIndisponivel(RuntimeError):
    """O provider é offline, ou o Nightshift não respondeu depois dos retries."""


RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def provider() -> str:
    return (env("LLM_PROVIDER", "offline") or "offline").strip().lower()


def _cfg() -> dict[str, Any]:
    return {
        "base_url": (env("METERLESS_BASE_URL") or "").rstrip("/"),
        "token": env("METERLESS_RUNTIME_TOKEN") or "",
        "modelo": env("METERLESS_MODEL", "meterless/auto") or "meterless/auto",
        "app": env("METERLESS_APP", "fococerto") or "fococerto",
        "scope": env("METERLESS_SCOPE", "user") or "user",
        "timeout_s": float(env("LLM_TIMEOUT_S", "180") or 180),
        "retries": int(env("LLM_RETRIES", "3") or 3),
        "backoff_s": float(env("LLM_BACKOFF_S", "2") or 2),
        "max_tokens": int(env("LLM_MAX_TOKENS", "4096") or 4096),
        "temperatura": float(env("LLM_TEMPERATURE", "0.2") or 0.2),
        # Desliga o raciocínio do Nemotron. Medido no Nightshift real (25/10): só "/no_think" não basta com prompts
        # grandes (o Planejador gastou os 4096 tokens raciocinando e não escreveu o JSON);
        # chat_template_kwargs.enable_thinking=false funciona (65 tokens e 1,3 s contra 225 e 5,1 s num teste curto).
        # Desligue com LLM_NO_THINK=0.
        "no_think": (env("LLM_NO_THINK", "1") or "1") not in ("0", "false", "no"),
    }


def _post(url: str, headers: dict, corpo: dict, timeout_s: float) -> httpx.Response:
    """Ponto único de I/O de rede (os testes substituem esta função).

    O timeout do httpx vale entre pacotes, não para a chamada inteira: com resposta chunked, um servidor que manda
    bytes de vez em quando nunca estoura. Aconteceu no Nightshift real (ablação presa 14 h numa chamada). Por isso
    há um prazo TOTAL: passou dele, a chamada é abortada com ReadTimeout e entra no retry normal."""
    limite = time.monotonic() + timeout_s
    with httpx.Client(timeout=httpx.Timeout(timeout_s, connect=15)) as c:
        with c.stream("POST", url, headers=headers, json=corpo) as r:
            partes = []
            for pedaco in r.iter_bytes():
                partes.append(pedaco)
                if time.monotonic() > limite:
                    raise httpx.ReadTimeout(f"prazo total de {timeout_s:.0f} s excedido", request=r.request)
            cabecalhos = {k: v for k, v in r.headers.items()
                          if k.lower() not in ("content-encoding", "transfer-encoding", "content-length")}
            return httpx.Response(r.status_code, headers=cabecalhos, content=b"".join(partes), request=r.request)


# ---------------------------------------------------------------- receipt / routed_model
def _procurar(obj: Any, chaves: tuple[str, ...], prof: int = 0) -> Any:
    if prof > 5:
        return None
    if isinstance(obj, dict):
        for k in chaves:
            if k in obj and obj[k] not in (None, ""):
                return obj[k]
        for v in obj.values():
            achado = _procurar(v, chaves, prof + 1)
            if achado is not None:
                return achado
    elif isinstance(obj, list):
        for v in obj:
            achado = _procurar(v, chaves, prof + 1)
            if achado is not None:
                return achado
    return None


def _receipt_str(r: Any) -> str | None:
    if r is None:
        return None
    if isinstance(r, dict):
        rid = r.get("id") or r.get("receipt_id") or r.get("request_id")
        return str(rid) if rid else json.dumps(r, ensure_ascii=False, sort_keys=True)[:4000]
    return str(r)[:4000]


def _extrair_meta(corpo: dict, headers: dict | httpx.Headers) -> tuple[str | None, str | None]:
    """Devolve (routed_model, receipt). Tolerante: o formato do receipt do Nightshift não está documentado."""
    receipt_obj = None
    for chave in ("meterless_receipt", "receipt", "meterless"):
        if chave in corpo:
            receipt_obj = corpo[chave]
            break
    routed = _procurar(receipt_obj, ("routed_model",)) if receipt_obj is not None else None
    routed = routed or _procurar(corpo, ("routed_model",))
    receipt = None
    if receipt_obj is not None:
        interno = receipt_obj.get("receipt") if isinstance(receipt_obj, dict) and "receipt" in receipt_obj else receipt_obj
        receipt = _receipt_str(interno)
    hdrs = {k.lower(): v for k, v in dict(headers).items()}
    for k, v in hdrs.items():
        if receipt is None and "receipt" in k:
            receipt = str(v)[:4000]
        if routed is None and "routed" in k and "model" in k:
            routed = v
    return (str(routed) if routed else None), receipt


# ---------------------------------------------------------------- JSON
def limpar_raciocinio(texto: str) -> str:
    """Remove o raciocínio do modelo. O Nemotron via Nightshift devolve o raciocínio grudado antes da resposta,
    às vezes só com a tag de fechamento ("...pensamento.</think>resposta"); vale o que vem depois do último </think>."""
    t = re.sub(r"<think>.*?</think>", "", texto or "", flags=re.S)
    if "</think>" in t:
        t = t.rsplit("</think>", 1)[1]
    return t.strip()


def extrair_json(texto: str) -> dict | None:
    """Extrai o primeiro objeto JSON do texto (aceita cercas ```json e texto em volta)."""
    if not texto:
        return None
    t = limpar_raciocinio(texto)
    cerca = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, flags=re.S)
    candidatos = [cerca.group(1)] if cerca else []
    ini = t.find("{")
    if ini >= 0:
        prof, em_str, esc = 0, False, False
        for i in range(ini, len(t)):
            ch = t[i]
            if em_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    em_str = False
            elif ch == '"':
                em_str = True
            elif ch == "{":
                prof += 1
            elif ch == "}":
                prof -= 1
                if prof == 0:
                    candidatos.append(t[ini : i + 1])
                    break
    for c in candidatos:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


# ---------------------------------------------------------------- chat
def chat(messages: list[dict], papel: str, json_schema: dict | None = None,
         log: LogExecucao | None = None) -> LLMResult:
    """Uma chamada ao LLM (contrato seção 4). ``log`` é opcional (extensão do contrato) e registra ``llm_call``.

    Com ``json_schema``, o schema vai numa mensagem de sistema e a resposta é parseada para ``LLMResult.json``
    (a *validação* pydantic fica com quem chama, ver ``app.agents.base.chamar_json``).
    """
    prov = provider()
    if prov == "offline":
        raise LLMIndisponivel("LLM_PROVIDER=offline: os agentes devem usar decidir_offline()")
    if prov != "nightshift":
        raise LLMIndisponivel(f"LLM_PROVIDER desconhecido: {prov!r} (use nightshift|offline)")
    cfg = _cfg()
    if not cfg["base_url"] or not cfg["token"]:
        raise LLMIndisponivel("METERLESS_BASE_URL/METERLESS_RUNTIME_TOKEN não configurados")

    msgs: list[dict] = []
    if cfg["no_think"]:
        msgs.append({"role": "system", "content": "/no_think"})
    msgs.extend(messages)
    if json_schema is not None:
        msgs.append({"role": "system", "content": "Responda SOMENTE com um objeto JSON válido que siga este JSON Schema, "
                     "sem texto antes ou depois:\n" + json.dumps(json_schema, ensure_ascii=False)})
    corpo = {"model": cfg["modelo"], "messages": msgs, "max_tokens": cfg["max_tokens"],
             "temperature": cfg["temperatura"]}
    if cfg["no_think"]:
        corpo["chat_template_kwargs"] = {"enable_thinking": False}
    headers = {"Authorization": f"Bearer {cfg['token']}", "meterless-app": cfg["app"],
               "meterless-scope": cfg["scope"], "Content-Type": "application/json"}
    url = cfg["base_url"] + "/chat/completions"

    t0 = time.monotonic()
    ultimo_erro = ""
    for tentativa in range(cfg["retries"] + 1):
        try:
            resp = _post(url, headers, corpo, cfg["timeout_s"])
            if resp.status_code in RETRY_STATUS:
                ultimo_erro = f"HTTP {resp.status_code}: {resp.text[:200]}"
            elif resp.status_code >= 400:
                ultimo_erro = f"HTTP {resp.status_code}: {resp.text[:200]}"
                break  # erro do cliente: não adianta repetir
            else:
                dados = resp.json()
                texto = limpar_raciocinio(dados["choices"][0]["message"].get("content") or "")
                routed, receipt = _extrair_meta(dados, resp.headers)
                uso = dados.get("usage") or {}
                res = LLMResult(
                    texto=texto,
                    json=extrair_json(texto) if json_schema is not None else None,
                    modelo=str(dados.get("model") or cfg["modelo"]),
                    routed_model=routed, receipt=receipt,
                    tokens=uso.get("total_tokens"),
                    latencia_s=round(time.monotonic() - t0, 3),
                )
                if log:
                    log.evento(papel, "llm_call", {"status": "ok", "tentativas": tentativa + 1,
                                                   "json_ok": res.json is not None if json_schema else None},
                               modelo=res.modelo, routed_model=res.routed_model, receipt=res.receipt,
                               tokens=res.tokens, latencia_s=res.latencia_s)
                return res
        except (httpx.TimeoutException, httpx.TransportError) as e:
            ultimo_erro = f"{type(e).__name__}: {e}"
        except (ValueError, KeyError, IndexError, TypeError) as e:
            ultimo_erro = f"resposta inesperada: {type(e).__name__}: {e}"
        if tentativa < cfg["retries"]:
            time.sleep(cfg["backoff_s"] * (2 ** tentativa))
    lat = round(time.monotonic() - t0, 3)
    if log:
        log.evento(papel, "llm_call", {"status": "erro", "erro": ultimo_erro}, modelo=cfg["modelo"], latencia_s=lat)
    raise LLMIndisponivel(f"Nightshift falhou após {cfg['retries'] + 1} tentativas: {ultimo_erro}")
