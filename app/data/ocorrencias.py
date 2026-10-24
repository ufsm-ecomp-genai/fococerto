"""Ocorrências, contexto e prioridade em Python (seção 5 da especificação).

É a implementação de referência das views do Zetaris (`sql/zetaris_views.sql`):
- `agrupar`               ~ view `ocorrencias`           (células de 0,1°, por dia UTC)
- `aplicar_contexto`      ~ view `ocorrencias_contexto`  (pop. num raio, tempo do ponto da grade)
- `aplicar_prioridade`    ~ view `ocorrencias_prioridade` (fórmula ponderada)
O RepositorioCache usa sempre este módulo; o RepositorioZetaris usa como fallback.

Período: data UTC "AAAA-MM-DD" (um período operacional = um dia UTC de aquisição do VIIRS).

Normalizações (suposições declaradas, ajustáveis aqui):
- exposição    = log10(1 + pop_raio) / log10(1 + POP_REF)  (cortado em 1); se houver distância a TI/UC,
                 soma PESO_TI_UC · max(0, 1 − dist/raio) (cortado em 1)
- intensidade  = log(1 + frp_soma) / log(1 + maior frp_soma da região no período)
- tempo        = HDW simplificado = VPD(hPa) × vento(m/s) / HDW_REF   (cortado em 1)
- persistência = (períodos_seguidos − 1) / (PERSIST_REF − 1)          (cortado em 1)
- crescimento  = max(0, (focos_hoje − focos_ontem) / max(focos_hoje, focos_ontem))  (nova = 1)
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.core.models import Ocorrencia, RegiaoCfg
from app.data.geo import dentro_bbox, haversine_km, id_celula

PESOS = {"exposicao": 0.35, "intensidade": 0.25, "tempo": 0.20, "persistencia": 0.10, "crescimento": 0.10}
POP_REF = 100_000      # uma cidade de 100 mil hab. no raio satura a exposição
PESO_TI_UC = 0.3
HDW_REF = 400.0        # hPa·m/s. Tocantins, 17–24/10/2026 (792 pontos×dia): p50 146, p90 241, máx. 479
PERSIST_REF = 4        # 4 dias seguidos ou mais satura a persistência
MAX_LOCALIDADES = 5    # localidades listadas por ocorrência (as mais próximas dentro do raio)


def normalizar_periodo(periodo: str) -> str:
    return date.fromisoformat(str(periodo)[:10]).isoformat()


def dia_anterior(dia: str, n: int = 1) -> str:
    return (date.fromisoformat(dia) - timedelta(days=n)).isoformat()


# --------------------------------------------------------------------------- 1. ocorrencias
def indexar_por_celula_dia(focos: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """{cel_id: {dia: [focos]}}."""
    idx: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for f in focos:
        idx[id_celula(f["lat"], f["lon"])][f["dia"]].append(f)
    return idx


def periodos_seguidos(dias_com_foco: set[str], dia: str) -> int:
    """Quantos dias consecutivos, terminando em `dia`, a célula teve foco (0 se não teve em `dia`)."""
    n = 0
    d = dia
    while d in dias_com_foco:
        n += 1
        d = dia_anterior(d)
    return n


def agrupar(focos: list[dict], periodo: str) -> list[dict]:
    """Agrupa os focos do período em células de 0,1°. Usa os dias anteriores para persistência e crescimento."""
    periodo = normalizar_periodo(periodo)
    idx = indexar_por_celula_dia(focos)
    ontem = dia_anterior(periodo)
    out = []
    for cel, por_dia in idx.items():
        hoje = por_dia.get(periodo)
        if not hoje:
            continue
        frps = [f["frp"] for f in hoje]
        horas = [f["data_hora_utc"] for f in hoje]
        out.append({
            "id": cel,
            "dia": periodo,
            "lat": round(sum(f["lat"] for f in hoje) / len(hoje), 5),
            "lon": round(sum(f["lon"] for f in hoje) / len(hoje), 5),
            "n_focos": len(hoje),
            "frp_soma": round(sum(frps), 2),
            "frp_max": round(max(frps), 2),
            "primeiro": min(horas),
            "ultimo": max(horas),
            "periodos_seguidos": periodos_seguidos({d for d, fs in por_dia.items() if fs}, periodo),
            "n_focos_ontem": len(por_dia.get(ontem, [])),
            "focos_ids": sorted(f["id"] for f in hoje),
        })
    return out


# --------------------------------------------------------------------------- 2. contexto
def localidades_no_raio(lat: float, lon: float, localidades: list[dict], raio_km: float) -> list[dict]:
    """Localidades do cities1000 a até `raio_km`, da mais próxima para a mais distante."""
    # pré-filtro barato por caixa (1° de latitude ≈ 111 km)
    dlat = raio_km / 111.0 + 0.01
    dlon = raio_km / (111.0 * max(0.1, math.cos(math.radians(lat)))) + 0.01
    perto = []
    for l in localidades:
        if abs(l["lat"] - lat) > dlat or abs(l["lon"] - lon) > dlon:
            continue
        d = haversine_km(lat, lon, l["lat"], l["lon"])
        if d <= raio_km:
            perto.append({"nome": l["nome"], "pop": int(l["pop"]), "dist_km": round(d, 1)})
    perto.sort(key=lambda x: x["dist_km"])
    return perto


def clima_mais_proximo(lat: float, lon: float, dia: str, clima: list[dict]) -> dict | None:
    """Linha de tempo do ponto da grade mais próximo, no dia pedido (None se não houver)."""
    do_dia = [c for c in clima if c["dia"] == dia]
    if not do_dia:
        return None
    return min(do_dia, key=lambda c: haversine_km(lat, lon, c["lat"], c["lon"]))


def ponto_grade(lat: float, lon: float, passo: float) -> tuple[float, float]:
    """Ponto da grade por arredondamento ao passo (a mesma regra da view ocorrencias_contexto)."""
    return round(_arred(lat / passo) * passo, 4), round(_arred(lon / passo) * passo, 4)


def _arred(x: float) -> int:
    """Arredonda metade para longe do zero (ROUND do Spark SQL), não o arredondamento bancário do Python."""
    return int(math.floor(abs(x) + 0.5)) * (1 if x >= 0 else -1)


def aplicar_contexto(grupos: list[dict], localidades: list[dict], clima: list[dict],
                     raio_km: float, ti_uc: list[dict] | None = None,
                     passo_clima: float | None = None) -> list[dict]:
    """Junta população no raio, localidades próximas, tempo da grade e (se houver) distância a TI/UC.

    Com `passo_clima`, o ponto da grade é achado por arredondamento (igual ao SQL); sem ele, pelo mais próximo.
    """
    clima_dia: dict[str, list[dict]] = defaultdict(list)
    clima_idx: dict[tuple, dict] = {}
    for c in clima:
        clima_dia[c["dia"]].append(c)
        clima_idx[(c["dia"], round(c["lat"], 4), round(c["lon"], 4))] = c
    for g in grupos:
        locs = localidades_no_raio(g["lat"], g["lon"], localidades, raio_km)
        g["pop_raio"] = sum(l["pop"] for l in locs)
        g["n_localidades_raio"] = len(locs)
        g["localidades"] = locs[:MAX_LOCALIDADES]
        if passo_clima:
            c = clima_idx.get((g["dia"], *ponto_grade(g["lat"], g["lon"], passo_clima)))
        else:
            c = clima_mais_proximo(g["lat"], g["lon"], g["dia"], clima_dia.get(g["dia"], []))
        g["vpd_kpa"] = c["vpd_kpa_max"] if c else None
        g["vento_kmh"] = c["vento_kmh_max"] if c else None
        g["clima_ponto"] = (c["lat"], c["lon"]) if c else None
        if ti_uc:
            g["dist_ti_uc_km"] = round(min(haversine_km(g["lat"], g["lon"], t["lat"], t["lon"]) for t in ti_uc), 1)
        else:
            g["dist_ti_uc_km"] = None  # camada TI/UC ainda não ingerida
    return grupos


def distancias_bases(lat: float, lon: float, bases: list[dict]) -> list[dict]:
    """Distância em linha reta até cada base, da mais próxima para a mais distante."""
    return sorted(({"base_id": b["id"], "dist_km": round(haversine_km(lat, lon, b["lat"], b["lon"]), 1)}
                   for b in bases), key=lambda x: x["dist_km"])


# --------------------------------------------------------------------------- 3. prioridade
def _corta(x: float) -> float:
    return max(0.0, min(1.0, x))


def componente_exposicao(pop_raio: int, dist_ti_uc_km: float | None, raio_km: float) -> float:
    pop = _corta(math.log10(1 + max(0, pop_raio)) / math.log10(1 + POP_REF))
    if dist_ti_uc_km is None:
        return round(pop, 4)
    ti = _corta(1 - dist_ti_uc_km / raio_km)
    return round(_corta(pop + PESO_TI_UC * ti), 4)


def componente_intensidade(frp_soma: float, frp_soma_max_regiao: float) -> float:
    if frp_soma_max_regiao <= 0:
        return 0.0
    return round(_corta(math.log1p(max(0.0, frp_soma)) / math.log1p(frp_soma_max_regiao)), 4)


def componente_tempo(vpd_kpa: float | None, vento_kmh: float | None) -> float:
    if vpd_kpa is None or vento_kmh is None:
        return 0.0
    hdw = (vpd_kpa * 10.0) * (vento_kmh / 3.6)
    return round(_corta(hdw / HDW_REF), 4)


def componente_persistencia(periodos: int) -> float:
    return round(_corta((periodos - 1) / (PERSIST_REF - 1)), 4)


def componente_crescimento(focos_hoje: int, focos_ontem: int) -> float:
    maior = max(focos_hoje, focos_ontem)
    if maior == 0:
        return 0.0
    return round(_corta((focos_hoje - focos_ontem) / maior), 4)


def calcular_prioridade(componentes: dict[str, float], pesos: dict[str, float] = PESOS) -> float:
    return round(sum(pesos[k] * componentes.get(k, 0.0) for k in pesos), 4)


def aplicar_prioridade(grupos: list[dict], raio_km: float) -> list[dict]:
    frp_max = max((g["frp_soma"] for g in grupos), default=0.0)
    for g in grupos:
        comp = {
            "exposicao": componente_exposicao(g.get("pop_raio", 0), g.get("dist_ti_uc_km"), raio_km),
            "intensidade": componente_intensidade(g["frp_soma"], frp_max),
            "tempo": componente_tempo(g.get("vpd_kpa"), g.get("vento_kmh")),
            "persistencia": componente_persistencia(g["periodos_seguidos"]),
            "crescimento": componente_crescimento(g["n_focos"], g.get("n_focos_ontem", 0)),
        }
        g["componentes"] = comp
        g["prioridade"] = calcular_prioridade(comp)
    grupos.sort(key=lambda g: (-g["prioridade"], -g["frp_soma"], g["id"]))
    return grupos


# --------------------------------------------------------------------------- montagem
def para_ocorrencia(g: dict) -> Ocorrencia:
    return Ocorrencia(
        id=g["id"], lat=g["lat"], lon=g["lon"], n_focos=g["n_focos"], frp_soma=g["frp_soma"],
        frp_max=g["frp_max"], primeiro=datetime.fromisoformat(g["primeiro"]),
        ultimo=datetime.fromisoformat(g["ultimo"]), periodos_seguidos=g["periodos_seguidos"],
        status=None,  # preenchido pela ferramenta monitor (app/tools)
        pop_raio=g.get("pop_raio", 0), dist_ti_uc_km=g.get("dist_ti_uc_km"),
        vpd_kpa=g.get("vpd_kpa"), vento_kmh=g.get("vento_kmh"), prioridade=g["prioridade"],
        componentes=g["componentes"], localidades=g.get("localidades", []),
    )


def montar_ocorrencias(focos: list[dict], localidades: list[dict], clima: list[dict],
                       regiao: RegiaoCfg, periodo: str, top: int | None = 15,
                       ti_uc: list[dict] | None = None, passo_clima: float | None = None) -> list[Ocorrencia]:
    """Pipeline completo: focos crus → ocorrências priorizadas da região no período (top N)."""
    focos_reg = [f for f in focos if dentro_bbox(f["lat"], f["lon"], regiao.bbox)]
    grupos = agrupar(focos_reg, periodo)
    aplicar_contexto(grupos, localidades, clima, regiao.raio_exposicao_km, ti_uc, passo_clima)
    aplicar_prioridade(grupos, regiao.raio_exposicao_km)
    if top is not None:
        grupos = grupos[:top]
    return [para_ocorrencia(g) for g in grupos]


def historico(focos: list[dict], cel_id: str, ate_dia: str, dias: int = 7) -> list[dict]:
    """Série diária de uma célula: [{dia, n_focos, frp_soma, frp_max, dia_noite: {D, N}}], do mais antigo ao atual."""
    ate_dia = normalizar_periodo(ate_dia)
    da_cel = [f for f in focos if id_celula(f["lat"], f["lon"]) == cel_id]
    out = []
    for k in range(dias - 1, -1, -1):
        d = dia_anterior(ate_dia, k)
        fs = [f for f in da_cel if f["dia"] == d]
        out.append({
            "dia": d,
            "n_focos": len(fs),
            "frp_soma": round(sum((f["frp"] for f in fs), 0.0), 2),
            "frp_max": round(max((f["frp"] for f in fs), default=0.0), 2),
            "dia_noite": {"D": sum(1 for f in fs if f["dia_noite"] == "D"),
                          "N": sum(1 for f in fs if f["dia_noite"] == "N")},
        })
    return out
