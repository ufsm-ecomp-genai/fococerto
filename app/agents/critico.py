"""Crítico: julga o que as ferramentas deixam em zona cinzenta (especificação, seção 6).

(1) trade-offs, (2) exceções vindas da memória, (3) quando escalar sem regra rígida obrigando; escreve a
contra-proposta e chama o Analista quando a decisão depende de uma pergunta em aberto.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.base import (CONFIANCA_MIN_MEMORIA, Contexto, SaidaInvalida, SaidaPlano, chamar_json, dados_comuns,
                             pares, plano_de_saida, prioridades_ajustadas, realocar, reescrever_citacoes,
                             registrar_fallback, resumo_plano, validar_ids)
from app.core.logging import LogExecucao
from app.core.mensagens import msg, rotulo
from app.core.models import Plano, VeredictoCritico, Violacao
from app.llm.client import LLMIndisponivel
from app.tools.alocador import completar_plano, justificar
from app.tools.geo import eta_recurso, exposta
from app.tools.regras import INSOLUVEIS

PAPEL = "critico"
FRACAO_ETA_TRADEOFF = 0.5     # exposta com ETA acima de 50% do limite é candidata a troca
GANHO_ETA_TRADEOFF_H = 1.0    # troca só se outro recurso chega ≥ 1 h antes
MAX_ANALISTA = 3


def _escolher_trocas(violacoes: list[Violacao]) -> list[dict]:
    """Trocas ``troca_recurso_local`` compatíveis entre si (cada recurso, origem e destino uma vez só), na ordem do
    maior ganho de ETA."""
    cands = []
    for v in violacoes:
        if v.regra == "troca_recurso_local":
            cands += [{**c, "para": v.ocorrencia_id, "pop_para": v.evidencia.get("pop_raio")}
                      for c in v.evidencia.get("candidatos") or [v.evidencia]]
    usados_r, usados_o, escolhidas = set(), set(), []
    for c in sorted(cands, key=lambda c: (-c["ganho_eta_h"], c["pop_de"], c["recurso_id"], c["para"])):
        if c["recurso_id"] in usados_r or c["de_ocorrencia"] in usados_o or c["para"] in usados_o:
            continue
        usados_r.add(c["recurso_id"])
        usados_o |= {c["de_ocorrencia"], c["para"]}
        escolhidas.append(c)
    return escolhidas


def _aplicar_trocas(ctx: Contexto, plano: Plano, trocas: list[dict], rodada: int) -> Plano:
    """Plano com cada recurso das ``trocas`` movido da ocorrência de origem para a exposta sem recurso. O resto do
    plano fica igual; ETA e justificativa vêm dos dados (template verificável do alocador)."""
    mover = {(t["recurso_id"], t["de_ocorrencia"]): t["para"] for t in trocas}
    idioma = ctx.regiao.idioma
    pri, extras, _ = prioridades_ajustadas(ctx)
    ds = []
    for d in plano.designacoes:
        para = mover.get((d.recurso_id, d.ocorrencia_id))
        if para is not None:
            r, o = ctx.rec[d.recurso_id], ctx.occ[para]
            b = ctx.base_por_id.get(r.base_id)
            eta = eta_recurso(r, b, o, ctx.regiao)
            texto, ev = justificar(o, r, b, eta, pri.get(o.id), extras.get(o.id, ""), idioma=idioma)
            d = d.model_copy(update={"ocorrencia_id": para, "eta_h": round(eta, 2), "evidencias": ev,
                                     "justificativa": texto + msg("cr_nota_troca", idioma)})
        ds.append(d)
    p = plano.model_copy(update={"designacoes": ds, "rodada": rodada, "resumo": (
        msg("cr_cp_troca", idioma) + plano.resumo).strip()})
    return completar_plano(p, ctx.ocorrencias, ctx.recursos)


def decidir_regras(ctx: Contexto, plano: Plano, violacoes: list[Violacao], rodada: int) -> VeredictoCritico:
    """Variante B da ablação (``usar_critico_llm=False``): só o checador realimentando o Planejador.
    Rejeita se houver violação rígida solúvel; não julga exceções nem trade-offs; não chama o Analista."""
    rig = [v for v in violacoes if v.rigida and v.regra not in INSOLUVEIS]
    if rig:
        return VeredictoCritico(decisao="rejeita", motivos=[f"{v.regra}: {v.sugestao}" for v in rig])
    return VeredictoCritico(decisao="aprova", motivos=[msg("cr_checador_ok", ctx.regiao.idioma)])


def decidir_offline(ctx: Contexto, plano: Plano, violacoes: list[Violacao], rodada: int) -> VeredictoCritico:
    """Crítico determinístico (sample mode): checador + regras de exceção, trade-off e escalação."""
    motivos: list[str] = []
    proibidos: set[tuple[str, str]] = set()
    bb: set[str] = set()
    rb: set[str] = set()
    rebaixar: set[str] = set()
    tradeoff = False
    leitura = ctx.leitura()
    occ = ctx.occ
    idioma = ctx.regiao.idioma

    def conf_txt(c: str) -> str:
        return rotulo("confiancas", c, idioma)

    # (2) exceções vindas da memória
    excecoes = []
    for v in violacoes:
        if v.regra != "restricao_memoria":
            continue
        conf = float(v.evidencia.get("confianca", 1.0))
        if conf >= CONFIANCA_MIN_MEMORIA:
            proibidos.add((v.recurso_id, v.ocorrencia_id))
            if v.evidencia.get("base") in leitura.bases_bloqueadas:
                bb.add(v.evidencia["base"])
            if v.ocorrencia_id in leitura.ocorrencias_bloqueadas:
                rb.add(v.ocorrencia_id)
            excecoes.append(v)
            motivos.append(msg("cr_excecao_aceita", idioma, mid=v.evidencia.get("memoria_id"),
                               texto=v.evidencia.get("texto"), conf=conf, rid=v.recurso_id, oid=v.ocorrencia_id))
        else:
            motivos.append(msg("cr_memoria_fraca", idioma, mid=v.evidencia.get("memoria_id"), conf=conf,
                               minimo=CONFIANCA_MIN_MEMORIA, rid=v.recurso_id, oid=v.ocorrencia_id))

    # regras rígidas solúveis. Citação incorreta não muda a alocação: o texto é reescrito a partir dos dados
    # (mais abaixo) e nunca, sozinha, força escalação.
    rigidas = [v for v in violacoes if v.rigida and v.regra not in INSOLUVEIS]
    citacoes = [v for v in rigidas if v.regra == "citacao_incorreta"]
    rig_alocacao = [v for v in rigidas if v.regra != "citacao_incorreta"]
    for v in rigidas:
        motivos.append(msg("cr_regra_rigida", idioma, regra=v.regra, oid=v.ocorrencia_id or "",
                           rid=v.recurso_id or "", sugestao=v.sugestao))
        if v.recurso_id and v.ocorrencia_id and v.regra in ("eta_acima_limite", "recurso_indisponivel",
                                                             "recurso_inexistente", "ocorrencia_inexistente"):
            proibidos.add((v.recurso_id, v.ocorrencia_id))

    designadas = [d.ocorrencia_id for d in plano.designacoes if d.ocorrencia_id in occ]
    nao_atendidas = [o.id for o in ctx.ocorrencias if o.id not in set(designadas)]

    # pergunta em aberto → Analista: recurso gasto em ocorrência sem exposição enquanto outra fica sem recurso
    if nao_atendidas:
        candidatas = sorted((oid for oid in designadas if not exposta(occ[oid]) and oid not in ctx.pareceres),
                            key=lambda oid: occ[oid].prioridade)[:MAX_ANALISTA]
        if candidatas:
            return VeredictoCritico(
                decisao="rejeita", pedir_analista=candidatas,
                motivos=motivos + [msg("cr_pergunta_analista", idioma, ids=", ".join(candidatas),
                                       n=len(nao_atendidas))])
        # pareceres: rebaixar queima agrícola provável sem exposição e longe de TI/UC
        for oid in designadas:
            par, o = ctx.pareceres.get(oid), occ[oid]
            if par is None or exposta(o):
                continue
            longe = o.dist_ti_uc_km is None or o.dist_ti_uc_km > 5.0
            mem = leitura.reforcos.get(oid)
            if (par.conclusao == "queima_agricola_provavel" and mem is not None
                    and mem.confianca >= CONFIANCA_MIN_MEMORIA):
                motivos.append(msg("cr_analista_memoria_contra", idioma, oid=oid, conf=conf_txt(par.confianca),
                                   mid=mem.id, texto=mem.texto[:160], mconf=mem.confianca))
            elif par.conclusao == "queima_agricola_provavel" and par.confianca in ("media", "alta") and longe:
                rebaixar.add(oid)
                motivos.append(msg("cr_analista_rebaixa", idioma, oid=oid, conf=conf_txt(par.confianca)))
            elif par.conclusao == "incendio_vegetacao_provavel":
                motivos.append(msg("cr_analista_vegetacao", idioma, oid=oid, conf=conf_txt(par.confianca)))
            else:
                motivos.append(msg("cr_analista_inconclusivo", idioma, oid=oid,
                                   conclusao=rotulo("conclusoes", par.conclusao, idioma),
                                   conf=conf_txt(par.confianca)))

    # (1) trade-off: exposta atendida de longe enquanto um recurso mais perto está em ocorrência sem exposição
    for d in plano.designacoes:
        o = occ.get(d.ocorrencia_id)
        if o is None or not exposta(o) or d.eta_h <= FRACAO_ETA_TRADEOFF * ctx.regiao.eta_max_h:
            continue
        for d2 in plano.designacoes:
            o2 = occ.get(d2.ocorrencia_id)
            if o2 is None or exposta(o2):
                continue
            eta_alt = ctx.etas.get(d2.recurso_id, {}).get(o.id)
            if eta_alt is not None and eta_alt + GANHO_ETA_TRADEOFF_H <= d.eta_h:
                tradeoff = True
                motivos.append(msg("cr_tradeoff", idioma, oid=o.id, pop=o.pop_raio, eta=d.eta_h, rid=d.recurso_id,
                                   rid2=d2.recurso_id, oid2=o2.id, eta_alt=eta_alt))
                break

    # (1b) troca de recurso local ocioso (regra troca_recurso_local, documentada em app/tools/regras.py)
    trocas = _escolher_trocas(violacoes)
    for t in trocas:
        motivos.append(msg("cr_troca", idioma, rid=t["recurso_id"], para=t["para"], pop_para=t["pop_para"],
                           eta_para=t["eta_para_exposta_h"], de=t["de_ocorrencia"], pop_de=t["pop_de"],
                           eta_atual=t["eta_atual_h"]))

    # ocorrências expostas sem recurso: entram em TODA escalação, para o coordenador não perdê-las de vista
    esc_expostas: list[str] = []
    for v in violacoes:
        if v.regra == "exposta_nao_atendida":
            esc_expostas.append(msg("cr_esc_exposta_nao_atendida", idioma, oid=v.ocorrencia_id,
                                    pop=v.evidencia.get("pop_raio")))
        elif v.regra in INSOLUVEIS:
            esc_expostas.append(msg("cr_esc_obrigatoria", idioma, oid=v.ocorrencia_id,
                                    pop=v.evidencia.get("pop_raio"), eta_max=v.evidencia.get("eta_max_h")))

    if proibidos or rebaixar or rig_alocacao or tradeoff:
        cp = realocar(ctx, rodada, proibidos=proibidos, bases_bloqueadas=bb, rotas_bloqueadas=rb, rebaixar=rebaixar,
                      resumo_prefixo=msg("cr_cp_offline", idioma))
        expostas_perdidas = [oid for oid in designadas if exposta(occ[oid]) and oid in cp.nao_atendidas]
        if excecoes and expostas_perdidas:
            return VeredictoCritico(decisao="escala", contra_proposta=cp, motivos=motivos + [
                msg("cr_esc_memoria", idioma, ids=", ".join(expostas_perdidas))] + esc_expostas)
        if pares(cp) != pares(plano):
            return VeredictoCritico(decisao="rejeita", contra_proposta=cp, motivos=motivos)
        if rig_alocacao:
            return VeredictoCritico(decisao="escala", contra_proposta=reescrever_citacoes(ctx, plano, citacoes),
                                    motivos=motivos + [msg("cr_esc_sem_alternativa", idioma)] + esc_expostas)
        motivos.append(msg("cr_revisao_igual", idioma))

    if trocas:
        cp = _aplicar_trocas(ctx, reescrever_citacoes(ctx, plano, citacoes), trocas, rodada)
        return VeredictoCritico(decisao="rejeita", contra_proposta=cp, motivos=motivos)

    if citacoes:  # mesma alocação, justificativas reescritas a partir dos dados; volta ao Planejador
        cp = reescrever_citacoes(ctx, plano, citacoes)
        alvo = sorted({f"{v.recurso_id}→{v.ocorrencia_id}" for v in citacoes})
        return VeredictoCritico(decisao="rejeita", contra_proposta=cp.model_copy(update={
            "rodada": rodada, "resumo": (msg("cr_cp_citacoes", idioma) + plano.resumo).strip()}),
            motivos=motivos + [msg("cr_citacao", idioma, alvo=", ".join(alvo))])

    # (3) escalação em zona cinzenta e obrigatória
    if esc_expostas:
        return VeredictoCritico(decisao="escala", motivos=motivos + esc_expostas)
    return VeredictoCritico(decisao="aprova", motivos=motivos or [msg("cr_sem_violacoes", idioma)])


class SaidaCritico(BaseModel):
    decisao: Literal["aprova", "rejeita", "escala"]
    motivos: list[str]
    pedir_analista: list[str] = Field(default_factory=list)
    contra_proposta: SaidaPlano | None = None


def decidir(ctx: Contexto, plano: Plano, violacoes: list[Violacao], rodada: int,
            log: LogExecucao | None) -> VeredictoCritico:
    dados = dados_comuns(ctx)
    dados.update(rodada=rodada, max_rodadas=3, plano=resumo_plano(plano),
                 violacoes=[v.model_dump() for v in violacoes],
                 ja_analisadas=sorted(ctx.pareceres))

    def validar(s: SaidaCritico) -> list[str]:
        erros = validar_ids(s.contra_proposta, ctx)
        erros += [f"pedir_analista com id fora do top: {i}" for i in s.pedir_analista if i not in ctx.occ]
        return erros

    try:
        s = chamar_json(PAPEL, "critico", dados, SaidaCritico, log, validar=validar, idioma=ctx.regiao.idioma)
        cp = plano_de_saida(s.contra_proposta, ctx, rodada) if s.contra_proposta else None
        return VeredictoCritico(decisao=s.decisao, motivos=s.motivos, contra_proposta=cp,
                                pedir_analista=[i for i in s.pedir_analista if i not in ctx.pareceres])
    except (SaidaInvalida, LLMIndisponivel) as e:
        registrar_fallback(log, PAPEL, e)
        return decidir_offline(ctx, plano, violacoes, rodada)
