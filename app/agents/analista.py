"""Analista: chamado pelo Crítico. "Queima agrícola/de manejo recorrente ou incêndio em vegetação nativa?"

Faz várias consultas (histórico de 7 dias, dia/noite, FRP, persistência, TI/UC, tempo, exposição) e devolve
uma conclusão com grau de incerteza (ParecerAnalista).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.base import (CONFIANCA_MIN_MEMORIA, Contexto, SaidaInvalida, chamar_json, registrar_fallback,
                             resumo_memoria, resumo_ocorrencia)
from app.core.logging import LogExecucao
from app.core.mensagens import msg, rotulo
from app.core.models import Memoria, ParecerAnalista
from app.tools.texto import contem_termo, norm
from app.llm.client import LLMIndisponivel
from app.tools.consultar import CONSULTAS, Consultor

PAPEL = "analista"
PERGUNTA = msg("an_pergunta", "pt-BR")   # compatibilidade; no idioma da execução: pergunta_padrao(idioma)


def pergunta_padrao(idioma: str | None = None) -> str:
    """A pergunta padrão do Analista no idioma da execução (app/core/mensagens.py)."""
    return msg("an_pergunta", idioma)

# Limiares heurísticos declarados (não calibrados com verdade de campo).
FRP_POR_FOCO_BAIXO = 20.0   # MW por foco
FRP_ALTO = 50.0             # MW (máximo de um foco) ou por foco >= 40
FRAC_NOITE_BAIXA = 0.10
FRAC_NOITE_ALTA = 0.25
TI_UC_PERTO_KM = 5.0
TI_UC_LONGE_KM = 10.0


def coletar(c: Consultor, oid: str, dias: int = 7) -> dict:
    """As consultas padrão do Analista (cada uma vira um evento ``consulta`` no log)."""
    hist = c.historico_celula(oid, dias)
    return {
        "historico": hist,
        "dia_noite": c.padrao_dia_noite(oid, dias),
        "frp": c.padrao_frp(oid, dias),
        "persistencia": c.persistencia(oid, dias),
        "ti_uc": c.proximidade_ti_uc(oid),
        "tempo": c.tempo(oid),
        "exposicao": c.exposicao(oid),
    }


def memorias_da_ocorrencia(ctx: Contexto, oid: str) -> tuple[list[Memoria], Memoria | None]:
    """Memórias (H-MEM + notas) que citam a ocorrência, e a de reforço (reignição/cresceu) lida pela ferramenta."""
    reforco = ctx.leitura().reforcos.get(oid)
    citam = [m for m in ctx.memorias if contem_termo(norm(m.texto), oid)]
    if reforco is not None and reforco not in citam:
        citam.append(reforco)
    return citam, reforco


def avaliar(ev: dict, reforco: Memoria | None = None, idioma: str | None = None) -> tuple[str, str, list[str], float]:
    """Pontua sinais de queima agrícola vs vegetação. Devolve (conclusao, confianca, evidencias, escore).

    ``reforco``: memória que diz que o fogo desta célula já reacendeu/cresceu (ou que foi despriorizado e cresceu).
    É um sinal contra "manejo controlado" que o histórico de 7 dias sozinho não mostra. ``idioma``: das frases
    de evidência (pt-BR padrão, ou en)."""
    dn, frp, per, ti, tempo = ev["dia_noite"], ev["frp"], ev["persistencia"], ev["ti_uc"], ev["tempo"]
    agri, veg, evid = 0.0, 0.0, []
    if reforco is not None and reforco.confianca >= CONFIANCA_MIN_MEMORIA:
        veg += 1
        evid.append(msg("an_memoria", idioma, mid=reforco.id, conf=reforco.confianca, texto=reforco.texto[:160]))
    total = (dn["n_dia"] or 0) + (dn["n_noite"] or 0)
    fn = dn["frac_noite"]
    if fn is not None and total >= 2:
        if fn <= FRAC_NOITE_BAIXA:
            agri += 1
            evid.append(msg("an_noite_baixa", idioma, total=total, fn=fn))
        elif fn >= FRAC_NOITE_ALTA:
            veg += 1
            evid.append(msg("an_noite_alta", idioma, fn=fn))
    if per["dias_com_foco"] >= 3 and per["max_focos_dia"] <= 5:
        agri += 1
        evid.append(msg("an_recorrente", idioma, dias=per["dias_com_foco"], maxf=per["max_focos_dia"]))
    if per["max_focos_dia"] >= 10:
        veg += 0.5
        evid.append(msg("an_pico", idioma, maxf=per["max_focos_dia"]))
    fpf = frp["frp_por_foco_hist"] if frp["frp_por_foco_hist"] is not None else frp["frp_por_foco_atual"]
    if fpf is not None:
        if fpf < FRP_POR_FOCO_BAIXO:
            agri += 1
            evid.append(msg("an_frp_baixo", idioma, fpf=fpf))
        elif fpf >= 40:
            veg += 1
            evid.append(msg("an_frp_alto", idioma, fpf=fpf))
    if (frp["frp_max_atual"] or 0) >= FRP_ALTO and not (fpf is not None and fpf >= 40):
        veg += 1
        evid.append(msg("an_frp_max", idioma, frp=frp["frp_max_atual"]))
    if per["status"] == "crescendo":
        veg += 1
        evid.append(msg("an_crescendo", idioma))
    elif per["status"] in ("estavel", "diminuindo"):
        agri += 0.5
        evid.append(msg("an_estavel", idioma, status=rotulo("status_ocorrencia", per["status"], idioma)))
    d = ti["dist_ti_uc_km"]
    if d is not None and d <= TI_UC_PERTO_KM:
        veg += 1
        evid.append(msg("an_ti_perto", idioma, d=d))
    elif d is None or d > TI_UC_LONGE_KM:
        agri += 0.5
        evid.append(msg("an_ti_longe", idioma) + (msg("an_ti_longe_km", idioma, d=d) if d is not None
                                                  else msg("an_ti_longe_sem", idioma)))
    if (tempo["vpd_kpa"] or 0) >= 2.0 and (tempo["vento_kmh"] or 0) >= 20:
        veg += 0.5
        evid.append(msg("an_tempo", idioma, vpd=tempo["vpd_kpa"], vento=tempo["vento_kmh"]))
    escore = agri - veg
    if escore >= 1.5:
        conclusao = "queima_agricola_provavel"
    elif escore <= -1.5:
        conclusao = "incendio_vegetacao_provavel"
    else:
        conclusao = "indeterminado"
    poucos_dados = per["dias_com_foco"] < 2
    if conclusao == "indeterminado" or poucos_dados:
        confianca = "baixa"
    elif abs(escore) >= 3 and per["dias_com_foco"] >= 3:
        confianca = "alta"
    else:
        confianca = "media"
    if poucos_dados:
        evid.append(msg("an_poucos_dados", idioma, dias=per["dias_com_foco"]))
    evid.append(msg("an_escore", idioma, escore=escore))
    return conclusao, confianca, evid, escore


def decidir_offline(ctx: Contexto, oid: str, consultor: Consultor, pergunta: str | None = None) -> ParecerAnalista:
    """Heurística determinística de persistência, dia/noite, FRP e proximidade de TI/UC (sample mode)."""
    idioma = ctx.regiao.idioma
    pergunta = pergunta or pergunta_padrao(idioma)
    ev = coletar(consultor, oid)
    _, reforco = memorias_da_ocorrencia(ctx, oid)
    conclusao, confianca, evid, _ = avaliar(ev, reforco, idioma)
    return ParecerAnalista(ocorrencia_id=oid, pergunta=pergunta, conclusao=conclusao, confianca=confianca,
                           evidencias=evid, consultas=list(consultor.consultas))


class SaidaAnalista(BaseModel):
    conclusao: Literal["queima_agricola_provavel", "incendio_vegetacao_provavel", "indeterminado"]
    confianca: Literal["baixa", "media", "alta"]
    evidencias: list[str]
    mais_consultas: list[str] = Field(default_factory=list,
                                      description="opcional: ex. 'historico_celula:14' para pedir 14 dias")


def _extra(c: Consultor, oid: str, pedidos: list[str]) -> dict:
    out = {}
    for p in pedidos[:3]:
        nome, _, arg = p.partition(":")
        nome = nome.strip()
        if nome not in CONSULTAS:
            continue
        if nome in ("historico_celula", "padrao_dia_noite", "padrao_frp", "persistencia"):
            dias = int(arg) if arg.strip().isdigit() else 7
            out[f"{nome}:{min(max(dias, 1), 30)}"] = getattr(c, nome)(oid, min(max(dias, 1), 30))
        else:
            out[nome] = getattr(c, nome)(oid)
    return out


def decidir(ctx: Contexto, oid: str, consultor: Consultor, log: LogExecucao | None,
            pergunta: str | None = None) -> ParecerAnalista:
    """O LLM interpreta as consultas; pode pedir até uma rodada de consultas extras (``mais_consultas``)."""
    idioma = ctx.regiao.idioma
    pergunta = pergunta or pergunta_padrao(idioma)
    ev = coletar(consultor, oid)
    citam, reforco = memorias_da_ocorrencia(ctx, oid)
    sinal = avaliar(ev, reforco, idioma)
    dados = {"pergunta": pergunta, "ocorrencia": resumo_ocorrencia(ctx.occ[oid]),
             "consultas": {k: v for k, v in ev.items()},
             "memorias_sobre_a_ocorrencia": [resumo_memoria(m) for m in citam],
             "sinais_heuristicos": {"conclusao": sinal[0], "confianca": sinal[1], "evidencias": sinal[2]},
             "consultas_disponiveis": list(CONSULTAS)}
    try:
        saida = chamar_json(PAPEL, "analista", dados, SaidaAnalista, log, idioma=idioma)
        if saida.mais_consultas:
            dados["consultas_extras"] = _extra(consultor, oid, saida.mais_consultas)
            dados["instrucao"] = "Estas são as consultas extras que você pediu. Agora conclua (mais_consultas vazio)."
            saida = chamar_json(PAPEL, "analista", dados, SaidaAnalista, log, idioma=idioma)
        return ParecerAnalista(ocorrencia_id=oid, pergunta=pergunta, conclusao=saida.conclusao,
                               confianca=saida.confianca, evidencias=saida.evidencias,
                               consultas=list(consultor.consultas))
    except (SaidaInvalida, LLMIndisponivel) as e:
        registrar_fallback(log, PAPEL, e)
        conclusao, confianca, evid, _ = sinal
        return ParecerAnalista(ocorrencia_id=oid, pergunta=pergunta, conclusao=conclusao, confianca=confianca,
                               evidencias=evid, consultas=list(consultor.consultas))
