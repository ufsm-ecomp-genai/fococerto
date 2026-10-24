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
from app.core.models import Memoria, ParecerAnalista
from app.tools.texto import contem_termo, norm
from app.llm.client import LLMIndisponivel
from app.tools.consultar import CONSULTAS, Consultor

PAPEL = "analista"
PERGUNTA = ("Esta ocorrência é provavelmente queima agrícola ou de manejo recorrente, "
            "ou incêndio em vegetação nativa?")

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


def avaliar(ev: dict, reforco: Memoria | None = None) -> tuple[str, str, list[str], float]:
    """Pontua sinais de queima agrícola vs vegetação. Devolve (conclusao, confianca, evidencias, escore).

    ``reforco``: memória que diz que o fogo desta célula já reacendeu/cresceu (ou que foi despriorizado e cresceu).
    É um sinal contra "manejo controlado" que o histórico de 7 dias sozinho não mostra."""
    dn, frp, per, ti, tempo = ev["dia_noite"], ev["frp"], ev["persistencia"], ev["ti_uc"], ev["tempo"]
    agri, veg, evid = 0.0, 0.0, []
    if reforco is not None and reforco.confianca >= CONFIANCA_MIN_MEMORIA:
        veg += 1
        evid.append(f"vegetação: memória {reforco.id} (confiança {reforco.confianca:.2f}) diz que este fogo já "
                    f"reacendeu/cresceu: \"{reforco.texto[:160]}\"")
    total = (dn["n_dia"] or 0) + (dn["n_noite"] or 0)
    fn = dn["frac_noite"]
    if fn is not None and total >= 2:
        if fn <= FRAC_NOITE_BAIXA:
            agri += 1
            evid.append(f"agrícola: {total:.0f} focos em 7 dias, {fn:.0%} à noite (queima de manejo costuma ser diurna)")
        elif fn >= FRAC_NOITE_ALTA:
            veg += 1
            evid.append(f"vegetação: {fn:.0%} dos focos à noite (fogo que segue queimando sem manejo)")
    if per["dias_com_foco"] >= 3 and per["max_focos_dia"] <= 5:
        agri += 1
        evid.append(f"agrícola: recorrente e pequeno ({per['dias_com_foco']} dias com foco, máx. "
                    f"{per['max_focos_dia']:.0f} focos/dia)")
    if per["max_focos_dia"] >= 10:
        veg += 0.5
        evid.append(f"vegetação: pico de {per['max_focos_dia']:.0f} focos num dia")
    fpf = frp["frp_por_foco_hist"] if frp["frp_por_foco_hist"] is not None else frp["frp_por_foco_atual"]
    if fpf is not None:
        if fpf < FRP_POR_FOCO_BAIXO:
            agri += 1
            evid.append(f"agrícola: FRP baixo ({fpf:.1f} MW por foco)")
        elif fpf >= 40:
            veg += 1
            evid.append(f"vegetação: FRP alto ({fpf:.1f} MW por foco)")
    if (frp["frp_max_atual"] or 0) >= FRP_ALTO and not (fpf is not None and fpf >= 40):
        veg += 1
        evid.append(f"vegetação: foco com FRP máximo {frp['frp_max_atual']:.0f} MW")
    if per["status"] == "crescendo":
        veg += 1
        evid.append("vegetação: ocorrência crescendo em relação ao período anterior")
    elif per["status"] in ("estavel", "diminuindo"):
        agri += 0.5
        evid.append(f"agrícola: ocorrência {per['status']}")
    d = ti["dist_ti_uc_km"]
    if d is not None and d <= TI_UC_PERTO_KM:
        veg += 1
        evid.append(f"vegetação: a {d:.1f} km de TI/UC")
    elif d is None or d > TI_UC_LONGE_KM:
        agri += 0.5
        evid.append("agrícola: longe de TI/UC" + (f" ({d:.1f} km)" if d is not None else " (sem TI/UC no raio)"))
    if (tempo["vpd_kpa"] or 0) >= 2.0 and (tempo["vento_kmh"] or 0) >= 20:
        veg += 0.5
        evid.append(f"vegetação: tempo propício a espalhar (VPD {tempo['vpd_kpa']} kPa, vento {tempo['vento_kmh']} km/h)")
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
        evid.append(f"incerteza: só {per['dias_com_foco']} dia(s) com foco no histórico")
    evid.append(f"escore agrícola−vegetação = {escore:+.1f} (limiar ±1,5; heurística não calibrada)")
    return conclusao, confianca, evid, escore


def decidir_offline(ctx: Contexto, oid: str, consultor: Consultor, pergunta: str = PERGUNTA) -> ParecerAnalista:
    """Heurística determinística de persistência, dia/noite, FRP e proximidade de TI/UC (sample mode)."""
    ev = coletar(consultor, oid)
    _, reforco = memorias_da_ocorrencia(ctx, oid)
    conclusao, confianca, evid, _ = avaliar(ev, reforco)
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
            pergunta: str = PERGUNTA) -> ParecerAnalista:
    """O LLM interpreta as consultas; pode pedir até uma rodada de consultas extras (``mais_consultas``)."""
    ev = coletar(consultor, oid)
    citam, reforco = memorias_da_ocorrencia(ctx, oid)
    sinal = avaliar(ev, reforco)
    dados = {"pergunta": pergunta, "ocorrencia": resumo_ocorrencia(ctx.occ[oid]),
             "consultas": {k: v for k, v in ev.items()},
             "memorias_sobre_a_ocorrencia": [resumo_memoria(m) for m in citam],
             "sinais_heuristicos": {"conclusao": sinal[0], "confianca": sinal[1], "evidencias": sinal[2]},
             "consultas_disponiveis": list(CONSULTAS)}
    try:
        saida = chamar_json(PAPEL, "analista", dados, SaidaAnalista, log)
        if saida.mais_consultas:
            dados["consultas_extras"] = _extra(consultor, oid, saida.mais_consultas)
            dados["instrucao"] = "Estas são as consultas extras que você pediu. Agora conclua (mais_consultas vazio)."
            saida = chamar_json(PAPEL, "analista", dados, SaidaAnalista, log)
        return ParecerAnalista(ocorrencia_id=oid, pergunta=pergunta, conclusao=saida.conclusao,
                               confianca=saida.confianca, evidencias=saida.evidencias,
                               consultas=list(consultor.consultas))
    except (SaidaInvalida, LLMIndisponivel) as e:
        registrar_fallback(log, PAPEL, e)
        conclusao, confianca, evid, _ = sinal
        return ParecerAnalista(ocorrencia_id=oid, pergunta=pergunta, conclusao=conclusao, confianca=confianca,
                               evidencias=evid, consultas=list(consultor.consultas))
