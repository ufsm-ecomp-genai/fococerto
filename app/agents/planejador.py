"""Planejador: parte do alocador_simples e desvia com justificativa (especificação, seção 6)."""
from __future__ import annotations

from app.agents.base import (Contexto, SaidaInvalida, SaidaPlano, chamar_json, dados_comuns, pares, plano_de_saida,
                             prioridades_ajustadas, realocar, registrar_fallback, resumo_plano, validar_ids)
from app.core.logging import LogExecucao
from app.core.models import Plano, VeredictoCritico, Violacao
from app.llm.client import LLMIndisponivel
from app.tools.alocador import completar_plano

PAPEL = "planejador"
# Violações rígidas cujo par (recurso, ocorrência) o Planejador simplesmente veta na revisão.
VETAR_PAR = {"eta_acima_limite", "recurso_indisponivel", "recurso_inexistente", "ocorrencia_inexistente"}


def _descrever_desvios(base: Plano | None, novo: Plano) -> list[str]:
    if base is None:
        return []
    b, n = pares(base), pares(novo)
    saiu, entrou = sorted(b - n), sorted(n - b)
    out = [f"removido {r}→{o}" for r, o in saiu] + [f"incluído {r}→{o}" for r, o in entrou]
    return out


def decidir_offline(ctx: Contexto, rodada: int, veredicto: VeredictoCritico | None = None,
                    violacoes: list[Violacao] | None = None) -> Plano:
    """Determinístico (sample mode). Heurísticas:
    1. se o Crítico mandou contra-proposta, adota-a (é o papel do Crítico escrevê-la);
    2. senão, guloso com população exposta primeiro, prioridade ajustada por memórias derivadas e pareceres,
       reserva pedida pelo coordenador (cenário ou memória) e veto dos pares que violaram regra rígida."""
    if veredicto is not None and veredicto.contra_proposta is not None:
        cp = completar_plano(veredicto.contra_proposta, ctx.ocorrencias, ctx.recursos)
        resumo = "Adota a contra-proposta do Crítico. " + (cp.resumo or "")
        return cp.model_copy(update={"rodada": rodada, "periodo": ctx.periodo, "regiao": ctx.regiao.nome,
                                     "resumo": resumo.strip()})
    proibidos = {(v.recurso_id, v.ocorrencia_id) for v in (violacoes or [])
                 if v.rigida and v.regra in VETAR_PAR and v.recurso_id and v.ocorrencia_id}
    plano = realocar(ctx, rodada, proibidos=proibidos)
    desvios = _descrever_desvios(ctx.baseline, plano)
    _, _, ajustes = prioridades_ajustadas(ctx)
    partes = ["Planejador offline (determinístico): população exposta primeiro"]
    if ctx.reserva_pedida() > ctx.reserva:
        partes.append(f"reserva {ctx.reserva_pedida()} pedida em memória")
    if ajustes:
        partes.append(f"{len(ajustes)} ajuste(s) de prioridade por memória/parecer")
    if desvios:
        partes.append("desvios do baseline: " + ", ".join(desvios))
    else:
        partes.append("igual ao baseline")
    return plano.model_copy(update={"resumo": "; ".join(partes) + ". " + plano.resumo})


def decidir(ctx: Contexto, rodada: int, log: LogExecucao | None, veredicto: VeredictoCritico | None = None,
            violacoes: list[Violacao] | None = None, plano_anterior: Plano | None = None) -> Plano:
    dados = dados_comuns(ctx)
    dados["rodada"] = rodada
    dados["proposta_baseline"] = resumo_plano(ctx.baseline) if ctx.baseline else None
    if plano_anterior is not None:
        dados["plano_anterior"] = resumo_plano(plano_anterior)
    if veredicto is not None:
        dados["veredicto_critico"] = {
            "decisao": veredicto.decisao, "motivos": veredicto.motivos,
            "contra_proposta": resumo_plano(veredicto.contra_proposta) if veredicto.contra_proposta else None}
    if violacoes:
        dados["violacoes"] = [v.model_dump() for v in violacoes]
    try:
        saida = chamar_json(PAPEL, "planejador", dados, SaidaPlano, log, validar=lambda s: validar_ids(s, ctx))
        return plano_de_saida(saida, ctx, rodada)
    except (SaidaInvalida, LLMIndisponivel) as e:
        registrar_fallback(log, PAPEL, e)
        return decidir_offline(ctx, rodada, veredicto, violacoes)
