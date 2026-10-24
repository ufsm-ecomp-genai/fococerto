"""Crítico: julga o que as ferramentas deixam em zona cinzenta (especificação, seção 6).

(1) trade-offs, (2) exceções vindas da memória, (3) quando escalar sem regra rígida obrigando; escreve a
contra-proposta e chama o Analista quando a decisão depende de uma pergunta em aberto.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.base import (Contexto, SaidaInvalida, SaidaPlano, chamar_json, dados_comuns, pares, plano_de_saida,
                             realocar, registrar_fallback, resumo_plano, validar_ids)
from app.core.logging import LogExecucao
from app.core.models import Plano, VeredictoCritico, Violacao
from app.llm.client import LLMIndisponivel
from app.tools.geo import exposta
from app.tools.regras import INSOLUVEIS

PAPEL = "critico"
CONFIANCA_MIN_MEMORIA = 0.5   # memória abaixo disso não justifica exceção
FRACAO_ETA_TRADEOFF = 0.5     # exposta com ETA acima de 50% do limite é candidata a troca
GANHO_ETA_TRADEOFF_H = 1.0    # troca só se outro recurso chega ≥ 1 h antes
MAX_ANALISTA = 3


def decidir_regras(ctx: Contexto, plano: Plano, violacoes: list[Violacao], rodada: int) -> VeredictoCritico:
    """Variante B da ablação (``usar_critico_llm=False``): só o checador realimentando o Planejador.
    Rejeita se houver violação rígida solúvel; não julga exceções nem trade-offs; não chama o Analista."""
    rig = [v for v in violacoes if v.rigida and v.regra not in INSOLUVEIS]
    if rig:
        return VeredictoCritico(decisao="rejeita", motivos=[f"{v.regra}: {v.sugestao}" for v in rig])
    return VeredictoCritico(decisao="aprova", motivos=["checador: nenhuma violação rígida solúvel"])


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
            motivos.append(f"Exceção aceita: memória {v.evidencia.get('memoria_id')} (\"{v.evidencia.get('texto')}\", "
                           f"confiança {conf:.2f}) vale sobre a regra da base mais próxima; {v.recurso_id} não deve "
                           f"ir por terra a {v.ocorrencia_id}.")
        else:
            motivos.append(f"Memória {v.evidencia.get('memoria_id')} tem confiança {conf:.2f} < "
                           f"{CONFIANCA_MIN_MEMORIA}: designação {v.recurso_id}→{v.ocorrencia_id} mantida.")

    # regras rígidas solúveis
    rigidas = [v for v in violacoes if v.rigida and v.regra not in INSOLUVEIS]
    for v in rigidas:
        motivos.append(f"Regra rígida {v.regra} ({v.ocorrencia_id or ''} {v.recurso_id or ''}): {v.sugestao}.")
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
                motivos=motivos + [f"Pergunta em aberto: {', '.join(candidatas)} recebe(m) recurso sem população exposta "
                                   f"enquanto {len(nao_atendidas)} ocorrência(s) ficam sem; é queima agrícola recorrente?"])
        # pareceres: rebaixar queima agrícola provável sem exposição e longe de TI/UC
        for oid in designadas:
            par, o = ctx.pareceres.get(oid), occ[oid]
            if par is None or exposta(o):
                continue
            longe = o.dist_ti_uc_km is None or o.dist_ti_uc_km > 5.0
            if par.conclusao == "queima_agricola_provavel" and par.confianca in ("media", "alta") and longe:
                rebaixar.add(oid)
                motivos.append(f"Analista: {oid} é queima agrícola provável (confiança {par.confianca}); o recurso "
                               f"rende mais em ocorrência não atendida.")
            elif par.conclusao == "incendio_vegetacao_provavel":
                motivos.append(f"Analista: {oid} é incêndio em vegetação provável (confiança {par.confianca}); "
                               f"designação mantida.")
            else:
                motivos.append(f"Analista inconclusivo sobre {oid} ({par.conclusao}, {par.confianca}): designação "
                               f"mantida por precaução.")

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
                motivos.append(f"Trade-off: {o.id} ({o.pop_raio} hab.) espera {d.eta_h:.1f} h por {d.recurso_id}, "
                               f"mas {d2.recurso_id} (em {o2.id}, sem exposição) chegaria em {eta_alt:.1f} h.")
                break

    # ocorrências expostas sem recurso: entram em TODA escalação, para o coordenador não perdê-las de vista
    esc_expostas: list[str] = []
    for v in violacoes:
        if v.regra == "exposta_nao_atendida":
            esc_expostas.append(f"Escalação: {v.ocorrencia_id} tem {v.evidencia.get('pop_raio')} hab. expostos e os "
                                f"recursos viáveis estão em outras ocorrências com população ou na reserva.")
        elif v.regra in INSOLUVEIS:
            esc_expostas.append(f"Escalação obrigatória: {v.ocorrencia_id} tem {v.evidencia.get('pop_raio')} hab. "
                                f"expostos e nenhum recurso chega em até {v.evidencia.get('eta_max_h')} h.")

    if proibidos or rebaixar or rigidas or tradeoff:
        cp = realocar(ctx, rodada, proibidos=proibidos, bases_bloqueadas=bb, rotas_bloqueadas=rb, rebaixar=rebaixar,
                      resumo_prefixo="Contra-proposta do Crítico (offline).")
        expostas_perdidas = [oid for oid in designadas if exposta(occ[oid]) and oid in cp.nao_atendidas]
        if excecoes and expostas_perdidas:
            return VeredictoCritico(decisao="escala", contra_proposta=cp, motivos=motivos + [
                f"Escalação: respeitar a memória deixa {', '.join(expostas_perdidas)} (com população) sem recurso "
                f"viável; decisão humana sobre usar a rota."] + esc_expostas)
        if pares(cp) != pares(plano):
            return VeredictoCritico(decisao="rejeita", contra_proposta=cp, motivos=motivos)
        if rigidas:
            return VeredictoCritico(decisao="escala", motivos=motivos + [
                "Escalação: não encontrei plano alternativo que resolva as regras rígidas."] + esc_expostas)
        motivos.append("Revisão não muda o plano.")

    # (3) escalação em zona cinzenta e obrigatória
    if esc_expostas:
        return VeredictoCritico(decisao="escala", motivos=motivos + esc_expostas)
    return VeredictoCritico(decisao="aprova", motivos=motivos or ["Sem violações nem zona cinzenta relevante."])


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
        s = chamar_json(PAPEL, "critico", dados, SaidaCritico, log, validar=validar)
        cp = plano_de_saida(s.contra_proposta, ctx, rodada) if s.contra_proposta else None
        return VeredictoCritico(decisao=s.decisao, motivos=s.motivos, contra_proposta=cp,
                                pedir_analista=[i for i in s.pedir_analista if i not in ctx.pareceres])
    except (SaidaInvalida, LLMIndisponivel) as e:
        registrar_fallback(log, PAPEL, e)
        return decidir_offline(ctx, plano, violacoes, rodada)
