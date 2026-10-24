"""Peças comuns aos agentes: contexto do período, chamada LLM com JSON validado e conversão de planos."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, Field, ValidationError

from app.core.logging import LogExecucao
from app.core.models import (Base, Designacao, Memoria, Ocorrencia, ParecerAnalista, Plano, Recurso, RegiaoCfg)
from app.llm import client
from app.tools.alocador import alocar, completar_plano
from app.tools.geo import eta_recurso, exposta, matriz_eta
from app.tools.memorias import LeituraMemorias, interpretar_memorias

PROMPTS = Path(__file__).parent / "prompts"
T = TypeVar("T", bound=BaseModel)


class SaidaInvalida(RuntimeError):
    """O LLM não devolveu JSON válido no schema, nem depois do retry."""


# ---------------------------------------------------------------- contexto do período
@dataclass
class Contexto:
    regiao: RegiaoCfg
    periodo: str
    ocorrencias: list[Ocorrencia]          # top 15, já com status do monitor
    recursos: list[Recurso]
    bases: list[Base]
    reserva: int                           # reserva pedida no cenário
    memorias: list[Memoria] = field(default_factory=list)  # H-MEM (se usar_memoria) + notas do período
    pareceres: dict[str, ParecerAnalista] = field(default_factory=dict)
    baseline: Plano | None = None

    @cached_property
    def occ(self) -> dict[str, Ocorrencia]:
        return {o.id: o for o in self.ocorrencias}

    @cached_property
    def rec(self) -> dict[str, Recurso]:
        return {r.id: r for r in self.recursos}

    @cached_property
    def base_por_id(self) -> dict[str, Base]:
        return {b.id: b for b in self.bases}

    @cached_property
    def etas(self) -> dict[str, dict[str, float]]:
        return matriz_eta(self.recursos, self.bases, self.ocorrencias, self.regiao)

    def leitura(self) -> LeituraMemorias:
        return interpretar_memorias(self.memorias, self.bases, self.ocorrencias)

    def reserva_pedida(self) -> int:
        return max(self.reserva, self.leitura().reserva_minima)


# ---------------------------------------------------------------- heurísticas compartilhadas (offline)
def prioridades_ajustadas(ctx: Contexto) -> tuple[dict[str, float], dict[str, str], list[dict]]:
    """Prioridade ajustada por memória derivada (reforço) e pelos pareceres do Analista.

    Devolve (prioridades, texto extra por ocorrência para a justificativa, lista de ajustes para o log)."""
    leitura = ctx.leitura()
    pri, extras, ajustes = {}, {}, []
    for o in ctx.ocorrencias:
        p, notas = o.prioridade, []
        m = leitura.reforcos.get(o.id)
        if m is not None:
            p += 0.15
            notas.append(f"memória {m.id} indica que este padrão já cresceu antes (+0,15)")
            ajustes.append({"ocorrencia_id": o.id, "memoria_id": m.id, "delta": 0.15, "texto": m.texto})
        par = ctx.pareceres.get(o.id)
        if par is not None:
            if par.conclusao == "queima_agricola_provavel" and par.confianca in ("media", "alta") and not exposta(o):
                p *= 0.5
                notas.append(f"Analista: queima agrícola provável (confiança {par.confianca}), prioridade ×0,5")
                ajustes.append({"ocorrencia_id": o.id, "parecer": par.conclusao, "fator": 0.5})
            elif par.conclusao == "incendio_vegetacao_provavel":
                p += 0.1
                notas.append(f"Analista: incêndio em vegetação provável (confiança {par.confianca}), +0,1")
                ajustes.append({"ocorrencia_id": o.id, "parecer": par.conclusao, "delta": 0.1})
        pri[o.id] = round(p, 4)
        if notas:
            extras[o.id] = "; ".join(notas)
    return pri, extras, ajustes


def realocar(ctx: Contexto, rodada: int, *, proibidos=(), bases_bloqueadas=(), rotas_bloqueadas=(),
             rebaixar=(), resumo_prefixo: str = "") -> Plano:
    pri, extras, _ = prioridades_ajustadas(ctx)
    for oid in rebaixar:
        if oid in pri:
            pri[oid] = round(pri[oid] * 0.3, 4)
    p = alocar(ctx.ocorrencias, ctx.recursos, ctx.bases, ctx.regiao, ctx.reserva_pedida(), periodo=ctx.periodo,
               regiao=ctx.regiao.nome, prioridades=pri, exposicao_primeiro=True, proibidos=proibidos,
               bases_bloqueadas=bases_bloqueadas, rotas_bloqueadas=rotas_bloqueadas, extras=extras)
    return p.model_copy(update={"rodada": rodada, "resumo": (resumo_prefixo + " " + p.resumo).strip()})


def pares(plano: Plano | None) -> set[tuple[str, str]]:
    return {(d.recurso_id, d.ocorrencia_id) for d in plano.designacoes} if plano else set()


# ---------------------------------------------------------------- resumos para o LLM (nunca linhas cruas)
def resumo_ocorrencia(o: Ocorrencia) -> dict:
    return {
        "id": o.id, "lat": round(o.lat, 3), "lon": round(o.lon, 3), "n_focos": o.n_focos,
        "frp_soma": round(o.frp_soma, 1), "frp_max": round(o.frp_max, 1), "status": o.status,
        "periodos_seguidos": o.periodos_seguidos, "pop_raio": o.pop_raio,
        "localidades": [{"nome": l.get("nome"), "pop": l.get("pop"), "dist_km": l.get("dist_km")}
                        for l in sorted(o.localidades, key=lambda l: l.get("dist_km") or 1e9)[:3]],
        "dist_ti_uc_km": o.dist_ti_uc_km, "vpd_kpa": o.vpd_kpa, "vento_kmh": o.vento_kmh,
        "prioridade": round(o.prioridade, 3), "componentes": {k: round(v, 3) for k, v in o.componentes.items()},
    }


def resumo_plano(p: Plano) -> dict:
    return {"rodada": p.rodada, "resumo": p.resumo, "reserva": p.reserva, "nao_atendidas": p.nao_atendidas,
            "designacoes": [{"ordem": d.ordem, "recurso_id": d.recurso_id, "ocorrencia_id": d.ocorrencia_id,
                             "eta_h": d.eta_h, "justificativa": d.justificativa} for d in p.designacoes]}


def resumo_memoria(m: Memoria) -> dict:
    return {"id": m.id, "texto": m.texto, "tipo": m.tipo, "fonte": m.fonte, "confianca": m.confianca,
            "criada_em": m.criada_em.isoformat(), "supersedes": m.supersedes}


def dados_comuns(ctx: Contexto) -> dict:
    return {
        "regiao": {"nome": ctx.regiao.nome, "eta_max_h": ctx.regiao.eta_max_h,
                   "raio_exposicao_km": ctx.regiao.raio_exposicao_km},
        "periodo": ctx.periodo,
        "ocorrencias_top": [resumo_ocorrencia(o) for o in ctx.ocorrencias],
        "recursos": [r.model_dump() for r in ctx.recursos],
        "bases": [b.model_dump() for b in ctx.bases],
        "eta_h_por_recurso": ctx.etas,
        "reserva_pedida": ctx.reserva_pedida(),
        "memorias": [resumo_memoria(m) for m in ctx.memorias],
        "pareceres_analista": [p.model_dump() for p in ctx.pareceres.values()],
    }


# ---------------------------------------------------------------- saída LLM -> Plano
class DesignacaoLLM(BaseModel):
    recurso_id: str
    ocorrencia_id: str
    justificativa: str
    evidencias: list[str] = Field(default_factory=list)


class SaidaPlano(BaseModel):
    designacoes: list[DesignacaoLLM]
    resumo: str
    desvios: list[str] = Field(default_factory=list)


def validar_ids(saida: SaidaPlano | None, ctx: Contexto) -> list[str]:
    if saida is None:
        return []
    erros = []
    for d in saida.designacoes:
        if d.recurso_id not in ctx.rec:
            erros.append(f"recurso_id inexistente: {d.recurso_id}")
        if d.ocorrencia_id not in ctx.occ:
            erros.append(f"ocorrencia_id fora do top: {d.ocorrencia_id}")
    return erros


def plano_de_saida(saida: SaidaPlano, ctx: Contexto, rodada: int) -> Plano:
    """ETA vem da ferramenta (o LLM não calcula números); ordem, reserva e não atendidas são derivadas."""
    ds = []
    for d in saida.designacoes:
        r = ctx.rec[d.recurso_id]
        ev = list(d.evidencias)
        if not any(e.startswith("base:") for e in ev):
            ev.append(f"base:{r.base_id}")
        ds.append(Designacao(recurso_id=d.recurso_id, ocorrencia_id=d.ocorrencia_id, ordem=len(ds) + 1,
                             eta_h=round(eta_recurso(r, ctx.base_por_id.get(r.base_id), ctx.occ[d.ocorrencia_id],
                                                     ctx.regiao), 2),
                             justificativa=d.justificativa, evidencias=ev))
    resumo = saida.resumo + ((" Desvios do baseline: " + " | ".join(saida.desvios)) if saida.desvios else "")
    p = Plano(periodo=ctx.periodo, regiao=ctx.regiao.nome, designacoes=ds, resumo=resumo, rodada=rodada)
    return completar_plano(p, ctx.ocorrencias, ctx.recursos)


# ---------------------------------------------------------------- chamada LLM com JSON validado
def carregar_prompt(nome: str) -> str:
    return (PROMPTS / f"{nome}.md").read_text(encoding="utf-8")


def chamar_json(papel: str, prompt: str, dados: dict, modelo: type[T], log: LogExecucao | None,
                validar: Callable[[T], list[str]] | None = None, tentativas: int = 2) -> T:
    """Chama o LLM, extrai o JSON e valida com pydantic (+ ``validar``). Se falhar, pede a correção uma vez.

    Levanta ``SaidaInvalida`` ou ``client.LLMIndisponivel``; quem chama decide o fallback."""
    schema = modelo.model_json_schema()
    msgs = [{"role": "system", "content": carregar_prompt(prompt)},
            {"role": "user", "content": "DADOS (JSON):\n" + json.dumps(dados, ensure_ascii=False, default=str)}]
    erro = ""
    for i in range(tentativas):
        res = client.chat(msgs, papel, json_schema=schema, log=log)
        try:
            if res.json is None:
                raise ValueError("a resposta não contém um objeto JSON")
            obj = modelo.model_validate(res.json)
            problemas = validar(obj) if validar else []
            if problemas:
                raise ValueError("; ".join(problemas))
            return obj
        except (ValidationError, ValueError) as e:
            erro = str(e)[:1500]
            if log:
                log.evento(papel, "llm_call", {"status": "json_invalido", "tentativa": i + 1, "erro": erro},
                           modelo=res.modelo, routed_model=res.routed_model, receipt=res.receipt)
            msgs = msgs + [{"role": "assistant", "content": res.texto[:4000]},
                           {"role": "user", "content": f"Resposta inválida: {erro}. Responda de novo SOMENTE com o "
                                                       f"objeto JSON corrigido, no schema pedido."}]
    raise SaidaInvalida(erro)


def registrar_fallback(log: LogExecucao | None, papel: str, erro: Exception) -> None:
    if log:
        log.evento(papel, "llm_call", {"status": "fallback_offline", "motivo": f"{type(erro).__name__}: {erro}",
                                       "modo": "offline_deterministico"})
