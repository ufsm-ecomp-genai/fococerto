"""checar_regras: regras rígidas da seção 6 da especificação, mais fatos de memória para o Crítico julgar.

Regras (``Violacao.regra``):
- ``ocorrencia_inexistente``, ``recurso_inexistente``, ``recurso_indisponivel``   rígidas (consistência)
- ``capacidade_excedida``: recurso em mais ocorrências que a capacidade (cap. 1 = "em duas ocorrências")  rígida
- ``recurso_duplicado``: o mesmo par recurso/ocorrência repetido                                          rígida
- ``eta_acima_limite``: ETA recalculado > eta_max_h da região                                            rígida
- ``exposta_sem_recurso``: ocorrência com população sem recurso enquanto outra sem exposição recebeu    rígida
- ``reserva_nao_mantida``: reserva pedida (cenário ou memória do coordenador) não mantida                rígida
- ``exposicao_sem_recurso_viavel``: população exposta e nenhum recurso disponível com ETA viável.
   Rígida e **insolúvel pelo plano**: obriga escalação.
- ``exposta_nao_atendida``: população sem recurso, mas os viáveis estão todos em ocorrências com exposição.
   Não rígida (zona cinzenta: o Crítico decide se escala).
- ``restricao_memoria``: designação terrestre que usa base/rota que uma memória diz estar bloqueada.
   Não rígida (exceção: o Crítico decide se vale).
"""
from __future__ import annotations

from collections import Counter

from app.core.models import Base, Memoria, Ocorrencia, Plano, Recurso, RegiaoCfg, Violacao
from app.tools.geo import eta_recurso, exposta
from app.tools.memorias import interpretar_memorias

INSOLUVEIS = {"exposicao_sem_recurso_viavel"}


def checar_regras(plano: Plano, ocorrencias: list[Ocorrencia], recursos: list[Recurso], bases: list[Base],
                  regiao_cfg: RegiaoCfg, memorias: list[Memoria], reserva_minima: int = 0) -> list[Violacao]:
    occ = {o.id: o for o in ocorrencias}
    rec = {r.id: r for r in recursos}
    por_base = {b.id: b for b in bases}
    leitura = interpretar_memorias(memorias, bases, ocorrencias)
    vs: list[Violacao] = []

    pares = Counter((d.recurso_id, d.ocorrencia_id) for d in plano.designacoes)
    for (rid, oid), n in pares.items():
        if n > 1:
            vs.append(Violacao(regra="recurso_duplicado", recurso_id=rid, ocorrencia_id=oid,
                               evidencia={"vezes": n}, sugestao="remover a designação repetida"))

    por_recurso = Counter(d.recurso_id for d in plano.designacoes)
    for d in plano.designacoes:
        o, r = occ.get(d.ocorrencia_id), rec.get(d.recurso_id)
        if o is None:
            vs.append(Violacao(regra="ocorrencia_inexistente", ocorrencia_id=d.ocorrencia_id, recurso_id=d.recurso_id,
                               evidencia={}, sugestao="usar só ocorrências do top do período"))
            continue
        if r is None:
            vs.append(Violacao(regra="recurso_inexistente", ocorrencia_id=o.id, recurso_id=d.recurso_id,
                               evidencia={}, sugestao="usar só recursos do cenário"))
            continue
        if not r.disponivel:
            vs.append(Violacao(regra="recurso_indisponivel", ocorrencia_id=o.id, recurso_id=r.id,
                               evidencia={"disponivel": False}, sugestao="trocar por um recurso disponível"))
        eta = eta_recurso(r, por_base.get(r.base_id), o, regiao_cfg)
        if eta > regiao_cfg.eta_max_h:
            vs.append(Violacao(regra="eta_acima_limite", ocorrencia_id=o.id, recurso_id=r.id,
                               evidencia={"eta_h": round(eta, 2), "eta_max_h": regiao_cfg.eta_max_h,
                                          "base": r.base_id},
                               sugestao="usar um recurso de base mais próxima ou aéreo"))
        if r.tipo == "terrestre":
            m = leitura.bases_bloqueadas.get(r.base_id) or leitura.ocorrencias_bloqueadas.get(o.id)
            if m is not None:
                vs.append(Violacao(regra="restricao_memoria", ocorrencia_id=o.id, recurso_id=r.id, rigida=False,
                                   evidencia={"memoria_id": m.id, "texto": m.texto, "fonte": m.fonte,
                                              "confianca": m.confianca, "base": r.base_id},
                                   sugestao="avaliar se a rota está mesmo bloqueada; usar outra base ou aéreo"))
    for rid, n in por_recurso.items():
        r = rec.get(rid)
        if r is not None and n > max(r.capacidade, 1):
            vs.append(Violacao(regra="capacidade_excedida", recurso_id=rid,
                               evidencia={"designacoes": n, "capacidade": r.capacidade},
                               sugestao="liberar o recurso de alguma ocorrência"))

    # reserva
    pedida = max(reserva_minima, leitura.reserva_minima)
    usados = set(por_recurso)
    livres = [r.id for r in recursos if r.disponivel and r.id not in usados]
    if pedida > 0 and len(livres) < pedida:
        ev = {"pedida": pedida, "mantida": len(livres), "livres": livres}
        if leitura.memoria_reserva is not None and leitura.reserva_minima == pedida:
            ev.update(memoria_id=leitura.memoria_reserva.id, texto=leitura.memoria_reserva.texto)
        vs.append(Violacao(regra="reserva_nao_mantida", evidencia=ev,
                           sugestao=f"manter {pedida} recurso(s) sem designação"))

    # prioridade da vida e escalação
    designadas = {d.ocorrencia_id for d in plano.designacoes if d.ocorrencia_id in occ}
    sem_exposicao_atendidas = [oid for oid in designadas if not exposta(occ[oid])]
    disp = [r for r in recursos if r.disponivel]
    for o in ocorrencias:
        if not exposta(o) or o.id in designadas:
            continue
        etas = {r.id: eta_recurso(r, por_base.get(r.base_id), o, regiao_cfg) for r in disp}
        viaveis = sorted((e, rid) for rid, e in etas.items() if e <= regiao_cfg.eta_max_h)
        if not viaveis:
            vs.append(Violacao(regra="exposicao_sem_recurso_viavel", ocorrencia_id=o.id,
                               evidencia={"pop_raio": o.pop_raio,
                                          "eta_min_h": round(min(etas.values()), 2) if etas else None,
                                          "eta_max_h": regiao_cfg.eta_max_h},
                               sugestao="escalar: nenhum recurso chega dentro do limite"))
        elif sem_exposicao_atendidas:
            vs.append(Violacao(regra="exposta_sem_recurso", ocorrencia_id=o.id,
                               evidencia={"pop_raio": o.pop_raio, "sem_exposicao_atendidas": sem_exposicao_atendidas,
                                          "viaveis": [rid for _, rid in viaveis]},
                               sugestao="realocar um recurso de ocorrência sem exposição para esta"))
        else:
            vs.append(Violacao(regra="exposta_nao_atendida", ocorrencia_id=o.id, rigida=False,
                               evidencia={"pop_raio": o.pop_raio, "viaveis": [rid for _, rid in viaveis]},
                               sugestao="os recursos viáveis estão em ocorrências com exposição ou na reserva: avaliar escalação"))
    return vs
