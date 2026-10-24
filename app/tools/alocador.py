"""alocador_simples (baseline guloso) e o alocador com restrições usado pelos agentes offline."""
from __future__ import annotations

import math
from collections.abc import Iterable

from app.core.models import Base, Designacao, Ocorrencia, Plano, Recurso, RegiaoCfg
from app.tools.geo import eta_recurso, exposta, haversine_km


def justificar(oc: Ocorrencia, rec: Recurso, base: Base | None, eta: float, prioridade: float | None = None,
               extra: str = "") -> tuple[str, list[str]]:
    """Justificativa por template, com fatos verificáveis pelo checar_citacoes."""
    p = oc.prioridade if prioridade is None else prioridade
    partes = [f"Prioridade {p:.2f}"]
    ev = [f"focos:{oc.n_focos}", f"eta:{eta:.2f}"]
    if oc.pop_raio > 0:
        partes.append(f"{oc.pop_raio} habitantes no raio")
        ev.append(f"pop:{oc.pop_raio}")
        if oc.localidades:
            loc = min(oc.localidades, key=lambda l: l.get("dist_km", math.inf))
            if loc.get("nome") and loc.get("dist_km") is not None:
                partes.append(f"{loc['nome']} a {float(loc['dist_km']):.1f} km")
                ev.append(f"dist:{loc['nome']}:{float(loc['dist_km']):.1f}")
    else:
        partes.append("sem população no raio")
    partes.append(f"{oc.n_focos} focos, FRP somado {oc.frp_soma:.0f} MW")
    if base is not None:
        partes.append(f"{rec.id} ({rec.tipo}) chega em ETA {eta:.1f} h saindo de {base.nome}")
        ev.append(f"base:{base.id}")
    if extra:
        partes.append(extra)
    return "; ".join(partes) + ".", ev


def alocar(ocorrencias: list[Ocorrencia], recursos: list[Recurso], bases: list[Base], regiao_cfg: RegiaoCfg,
           reserva: int, *, periodo: str = "", regiao: str | None = None,
           prioridades: dict[str, float] | None = None, exposicao_primeiro: bool = False,
           proibidos: Iterable[tuple[str, str]] = (), bases_bloqueadas: Iterable[str] = (),
           rotas_bloqueadas: Iterable[str] = (), extras: dict[str, str] | None = None) -> Plano:
    """Guloso: em ordem de prioridade, cada ocorrência recebe o recurso viável (ETA ≤ eta_max_h) mais próximo.

    - ``reserva``: quantos recursos disponíveis ficam guardados (o alocador para quando sobrar só a reserva).
    - ``prioridades``: prioridade ajustada por ocorrência (padrão: ``oc.prioridade``).
    - ``exposicao_primeiro``: ocorrências com população exposta vêm antes (heurística de prioridade da vida).
    - ``proibidos``: pares (recurso_id, ocorrencia_id) vetados; ``bases_bloqueadas``/``rotas_bloqueadas``
      vetam recursos *terrestres* saindo daquela base / indo àquela ocorrência.
    """
    pri = {o.id: (prioridades or {}).get(o.id, o.prioridade) for o in ocorrencias}
    ordem = sorted(ocorrencias, key=lambda o: ((not exposta(o)) if exposicao_primeiro else False, -pri[o.id], o.id))
    por_base = {b.id: b for b in bases}
    disp = [r for r in recursos if r.disponivel]
    uso = {r.id: 0 for r in disp}
    proib, bb, rb = set(proibidos), set(bases_bloqueadas), set(rotas_bloqueadas)
    designacoes: list[Designacao] = []
    nao_atendidas: list[str] = []
    for o in ordem:
        livres = sum(1 for r in disp if uso[r.id] == 0)
        candidatos = []
        for r in disp:
            if uso[r.id] >= max(r.capacidade, 1) or (r.id, o.id) in proib:
                continue
            if r.tipo == "terrestre" and (r.base_id in bb or o.id in rb):
                continue
            if uso[r.id] == 0 and livres <= reserva:
                continue  # pegar um recurso novo quebraria a reserva
            eta = eta_recurso(r, por_base.get(r.base_id), o, regiao_cfg)
            if eta <= regiao_cfg.eta_max_h:
                candidatos.append((eta, r.id, r))
        if not candidatos:
            nao_atendidas.append(o.id)
            continue
        eta, _, r = min(candidatos)
        uso[r.id] += 1
        texto, ev = justificar(o, r, por_base.get(r.base_id), eta, pri[o.id], (extras or {}).get(o.id, ""))
        designacoes.append(Designacao(recurso_id=r.id, ocorrencia_id=o.id, ordem=len(designacoes) + 1,
                                      eta_h=round(eta, 2), justificativa=texto, evidencias=ev))
    reserva_ids = [r.id for r in disp if uso[r.id] == 0]
    resumo = (f"{len(designacoes)} designações, {len(nao_atendidas)} ocorrências sem recurso, "
              f"{len(reserva_ids)} recursos em reserva.")
    return Plano(periodo=periodo, regiao=regiao or regiao_cfg.nome, designacoes=designacoes,
                 reserva=reserva_ids, nao_atendidas=nao_atendidas, resumo=resumo)


def alocador_simples(ocorrencias: list[Ocorrencia], recursos: list[Recurso], bases: list[Base],
                     regiao_cfg: RegiaoCfg, reserva: int, periodo: str = "", regiao: str | None = None) -> Plano:
    """Baseline (variante A): maior prioridade recebe o recurso viável mais próximo. Sem heurística nenhuma."""
    return alocar(ocorrencias, recursos, bases, regiao_cfg, reserva, periodo=periodo, regiao=regiao)


def completar_plano(plano: Plano, ocorrencias: list[Ocorrencia], recursos: list[Recurso]) -> Plano:
    """Recalcula ``ordem``, ``reserva`` e ``nao_atendidas`` a partir das designações (fonte da verdade)."""
    designadas = {d.ocorrencia_id for d in plano.designacoes}
    usados = {d.recurso_id for d in plano.designacoes}
    ds = [d.model_copy(update={"ordem": i + 1}) for i, d in enumerate(plano.designacoes)]
    return plano.model_copy(update={
        "designacoes": ds,
        "reserva": [r.id for r in recursos if r.disponivel and r.id not in usados],
        "nao_atendidas": [o.id for o in ocorrencias if o.id not in designadas],
    })


def distancia_km(oc: Ocorrencia, base: Base) -> float:
    return haversine_km(base.lat, base.lon, oc.lat, oc.lon)
