"""Distância e ETA (docs/CONTRATOS.md, seção 6)."""
from __future__ import annotations

import math

from app.core.models import Base, Ocorrencia, Recurso, RegiaoCfg

RAIO_TERRA_KM = 6371.0088
# Suposição declarada (não está no YAML de região): aeronave voa em linha reta a esta velocidade média,
# incluindo decolagem. Pedido de contrato: campo `velocidade_aereo_kmh` em RegiaoCfg.
VELOCIDADE_AEREO_KMH_PADRAO = 180.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAIO_TERRA_KM * math.asin(math.sqrt(a))


def eta_h(lat1: float, lon1: float, lat2: float, lon2: float, regiao_cfg: RegiaoCfg,
          tipo: str = "terrestre") -> float:
    """ETA em horas: haversine × tortuosidade ÷ velocidade (terrestre); linha reta ÷ velocidade aérea (aereo)."""
    d = haversine_km(lat1, lon1, lat2, lon2)
    if tipo == "aereo":
        v = getattr(regiao_cfg, "velocidade_aereo_kmh", None) or VELOCIDADE_AEREO_KMH_PADRAO
        return d / v
    return d * regiao_cfg.fator_tortuosidade / regiao_cfg.velocidade_kmh


def eta_recurso(recurso: Recurso, base: Base | None, oc: Ocorrencia, regiao_cfg: RegiaoCfg) -> float:
    if base is None:
        return math.inf
    return eta_h(base.lat, base.lon, oc.lat, oc.lon, regiao_cfg, recurso.tipo)


def etas_disponiveis(oc: Ocorrencia, recursos: list[Recurso], por_base: dict[str, Base],
                     regiao_cfg: RegiaoCfg) -> dict[str, float]:
    """{recurso_id: ETA até ``oc``} dos recursos disponíveis (sem arredondar)."""
    return {r.id: eta_recurso(r, por_base.get(r.base_id), oc, regiao_cfg) for r in recursos if r.disponivel}


def viaveis(etas: dict[str, float], regiao_cfg: RegiaoCfg) -> list[tuple[float, str]]:
    """(ETA, recurso_id) dos que chegam dentro de ``regiao_cfg.eta_max_h``, do mais rápido ao mais lento."""
    return sorted((e, rid) for rid, e in etas.items() if e <= regiao_cfg.eta_max_h)


def matriz_eta(recursos: list[Recurso], bases: list[Base], ocorrencias: list[Ocorrencia],
               regiao_cfg: RegiaoCfg) -> dict[str, dict[str, float]]:
    """{recurso_id: {ocorrencia_id: eta_h}} para os recursos disponíveis."""
    por_id = {b.id: b for b in bases}
    return {r.id: {o.id: round(eta_recurso(r, por_id.get(r.base_id), o, regiao_cfg), 2) for o in ocorrencias}
            for r in recursos if r.disponivel}


def exposta(oc: Ocorrencia) -> bool:
    """População exposta no raio (critério da regra 'prioridade da vida')."""
    return oc.pop_raio > 0
