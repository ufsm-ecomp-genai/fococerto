"""Planejador: parte do alocador_simples e desvia com justificativa (especificação, seção 6)."""
from __future__ import annotations

from app.agents.base import (Contexto, SaidaInvalida, SaidaPlano, chamar_json, dados_comuns, pares, plano_de_saida,
                             prioridades_ajustadas, realocar, registrar_fallback, resumo_plano, validar_ids)
from app.core.logging import LogExecucao
from app.core.mensagens import msg
from app.core.models import Plano, VeredictoCritico, Violacao
from app.llm.client import LLMIndisponivel
from app.tools.alocador import completar_plano

PAPEL = "planejador"
# Violações rígidas cujo par (recurso, ocorrência) o Planejador simplesmente veta na revisão.
VETAR_PAR = {"eta_acima_limite", "recurso_indisponivel", "recurso_inexistente", "ocorrencia_inexistente"}


def _descrever_desvios(base: Plano | None, novo: Plano, idioma: str | None = None) -> list[str]:
    if base is None:
        return []
    b, n = pares(base), pares(novo)
    saiu, entrou = sorted(b - n), sorted(n - b)
    out = ([msg("pl_removido", idioma, r=r, o=o) for r, o in saiu]
           + [msg("pl_incluido", idioma, r=r, o=o) for r, o in entrou])
    return out


def decidir_offline(ctx: Contexto, rodada: int, veredicto: VeredictoCritico | None = None,
                    violacoes: list[Violacao] | None = None) -> Plano:
    """Determinístico (sample mode). Heurísticas:
    1. se o Crítico mandou contra-proposta, adota-a (é o papel do Crítico escrevê-la);
    2. senão, guloso com população exposta primeiro, prioridade ajustada por memórias derivadas e pareceres,
       reserva pedida pelo coordenador (cenário ou memória) e veto dos pares que violaram regra rígida."""
    idioma = ctx.regiao.idioma
    if veredicto is not None and veredicto.contra_proposta is not None:
        cp = completar_plano(veredicto.contra_proposta, ctx.ocorrencias, ctx.recursos)
        resumo = msg("pl_adota_cp", idioma) + (cp.resumo or "")
        return cp.model_copy(update={"rodada": rodada, "periodo": ctx.periodo, "regiao": ctx.regiao.nome,
                                     "resumo": resumo.strip()})
    proibidos = {(v.recurso_id, v.ocorrencia_id) for v in (violacoes or [])
                 if v.rigida and v.regra in VETAR_PAR and v.recurso_id and v.ocorrencia_id}
    plano = realocar(ctx, rodada, proibidos=proibidos)
    desvios = _descrever_desvios(ctx.baseline, plano, idioma)
    _, _, ajustes = prioridades_ajustadas(ctx)
    partes = [msg("pl_offline", idioma)]
    if ctx.reserva_pedida() > ctx.reserva:
        partes.append(msg("pl_reserva_memoria", idioma, n=ctx.reserva_pedida()))
    if ajustes:
        partes.append(msg("pl_ajustes", idioma, n=len(ajustes)))
    if desvios:
        partes.append(msg("pl_desvios", idioma, lista=", ".join(desvios)))
    else:
        partes.append(msg("pl_igual", idioma))
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
        # rodada >= 2: cada ponto do Crítico tem de ser adotado ou recusado com motivo (respostas_ao_critico)
        dados["pontos_do_critico_a_responder"] = [m for m in veredicto.motivos if m and m.strip()]
        if veredicto.contra_proposta is not None:
            dados["pares_da_contra_proposta"] = [f"{d.recurso_id}->{d.ocorrencia_id}"
                                                 for d in veredicto.contra_proposta.designacoes]
    if violacoes:
        dados["violacoes"] = [v.model_dump() for v in violacoes]
    try:
        saida = chamar_json(PAPEL, "planejador", dados, SaidaPlano, log, validar=lambda s: validar_ids(s, ctx),
                            idioma=ctx.regiao.idioma)
        return plano_de_saida(saida, ctx, rodada)
    except (SaidaInvalida, LLMIndisponivel) as e:
        registrar_fallback(log, PAPEL, e)
        return decidir_offline(ctx, rodada, veredicto, violacoes)
