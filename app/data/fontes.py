"""Leitura e download das fontes públicas (FIRMS, GeoNames, OSM/Overpass, Open-Meteo).

Os arquivos baixados são DADOS: só são lidos como CSV/JSON, nunca executados nem interpretados
como instruções. Usado pelos scripts de ingestão, pelo congelar_cache.py e pelo setup do Zetaris.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.data.geo import dentro_bbox, grade, haversine_km

USER_AGENT = "FocoCerto/0.1 (Open Agent Hackathon 2026, time UFSM)"

FIRMS_URL = ("https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/"
             "SUOMI_VIIRS_C2_Global_{janela}.csv")
JANELAS_FIRMS = ("24h", "48h", "7d")
GEONAMES_URL = "https://download.geonames.org/export/dump/cities1000.zip"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_ESPELHOS = ["https://overpass.kumi.systems/api/interpreter"]
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
VARS_DIARIAS = "vapour_pressure_deficit_max,wind_speed_10m_max,relative_humidity_2m_min,precipitation_sum"

# Passo da grade fixa do Open-Meteo por região (graus). Ibéria usa 1° para caber numa URL (~135 pontos).
PASSO_CLIMA = {"iberia": 1.0}
PASSO_CLIMA_PADRAO = 0.5


def passo_clima(regiao: str) -> float:
    return PASSO_CLIMA.get(regiao, PASSO_CLIMA_PADRAO)


COLUNAS_FOCOS = ["id", "lat", "lon", "data_hora_utc", "satelite", "confianca", "frp", "dia_noite", "dia"]
COLUNAS_LOCALIDADES = ["geonameid", "nome", "lat", "lon", "pop", "pais"]
COLUNAS_BASES = ["id", "nome", "lat", "lon", "fonte"]
COLUNAS_CLIMA = ["lat", "lon", "dia", "vpd_kpa_max", "vento_kmh_max", "umidade_min_pct", "chuva_mm"]


# --------------------------------------------------------------------------- utilidades
def baixar(url: str, destino: Path, timeout: float = 600.0) -> Path:
    """Download em streaming para arquivo (o FIRMS de 7 dias tem ~40 MB)."""
    import httpx

    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True,
                      headers={"User-Agent": USER_AGENT}) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for bloco in r.iter_bytes(1 << 20):
                f.write(bloco)
    tmp.replace(destino)
    return destino


def escrever_csv(caminho: Path, linhas: Iterable[dict], colunas: list[str]) -> int:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
        w.writeheader()
        for linha in linhas:
            w.writerow(linha)
            n += 1
    return n


def ler_csv(caminho: Path) -> list[dict]:
    with caminho.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- FIRMS
def id_foco(lat: float, lon: float, data: str, hora: str, satelite: str) -> str:
    chave = f"{lat:.5f}|{lon:.5f}|{data}|{hora}|{satelite}"
    return hashlib.sha1(chave.encode()).hexdigest()[:16]


def ler_firms(caminho: Path, bbox=None) -> list[dict]:
    """Lê o CSV do FIRMS (VIIRS), recorta pela bbox e deduplica pelo id.

    Devolve dicts com as colunas de COLUNAS_FOCOS (lat/lon/frp como float, data_hora_utc ISO).
    """
    vistos: set[str] = set()
    focos = []
    with caminho.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                lat, lon = float(r["latitude"]), float(r["longitude"])
            except (KeyError, ValueError):
                continue
            if bbox is not None and not dentro_bbox(lat, lon, bbox):
                continue
            data, hora = r["acq_date"], r["acq_time"].zfill(4)
            fid = id_foco(lat, lon, data, hora, r.get("satellite", ""))
            if fid in vistos:
                continue
            vistos.add(fid)
            try:
                frp = float(r.get("frp") or 0.0)
            except ValueError:
                frp = 0.0
            dh = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H%M")
            focos.append({
                "id": fid, "lat": lat, "lon": lon, "data_hora_utc": dh.isoformat(),
                "satelite": r.get("satellite", ""), "confianca": r.get("confidence", ""),
                "frp": frp, "dia_noite": r.get("daynight", ""), "dia": data,
            })
    return focos


def focos_de_csv_cache(linhas: list[dict]) -> list[dict]:
    """Converte linhas lidas de focos.csv (strings) para os tipos usados pelo motor."""
    out = []
    for r in linhas:
        out.append({**r, "lat": float(r["lat"]), "lon": float(r["lon"]), "frp": float(r["frp"] or 0.0)})
    return out


# --------------------------------------------------------------------------- GeoNames
def ler_geonames(caminho: Path, bbox=None, margem: float = 0.0, paises: set[str] | None = None) -> list[dict]:
    """Lê cities1000 (.zip ou .txt, separado por TAB). Colunas: 0 id, 1 nome, 4 lat, 5 lon, 8 país, 14 pop."""
    if caminho.suffix == ".zip":
        with zipfile.ZipFile(caminho) as z:
            texto = io.TextIOWrapper(z.open("cities1000.txt"), encoding="utf-8")
            return _filtrar_geonames(texto, bbox, margem, paises)
    with caminho.open(encoding="utf-8") as f:
        return _filtrar_geonames(f, bbox, margem, paises)


def _filtrar_geonames(linhas, bbox, margem, paises) -> list[dict]:
    out = []
    for linha in linhas:
        c = linha.rstrip("\n").split("\t")
        if len(c) < 15:
            continue
        try:
            lat, lon, pop = float(c[4]), float(c[5]), int(c[14] or 0)
        except ValueError:
            continue
        if bbox is not None and not dentro_bbox(lat, lon, bbox, margem):
            continue
        if paises and c[8] not in paises:
            continue
        out.append({"geonameid": c[0], "nome": c[1], "lat": lat, "lon": lon, "pop": pop, "pais": c[8]})
    return out


def localidades_de_csv(linhas: list[dict]) -> list[dict]:
    return [{**r, "lat": float(r["lat"]), "lon": float(r["lon"]), "pop": int(r["pop"])} for r in linhas]


# --------------------------------------------------------------------------- OSM / Overpass
def consulta_overpass(bbox, margem: float = 0.0) -> str:
    lat_min, lat_max, lon_min, lon_max = bbox
    b = f"{lat_min - margem},{lon_min - margem},{lat_max + margem},{lon_max + margem}"  # S,W,N,E
    return ("[out:json][timeout:180];("
            f'nwr["amenity"="fire_station"]({b});'
            ");out center tags;")


def baixar_overpass(bbox, margem: float, destino_json: Path, max_idade_h: float = 24 * 7,
                    forcar: bool = False) -> dict:
    """Consulta o Overpass com cache em arquivo (só refaz se o arquivo for mais velho que max_idade_h)."""
    import httpx

    if destino_json.exists() and not forcar:
        idade_h = (time.time() - destino_json.stat().st_mtime) / 3600
        if idade_h < max_idade_h:
            return json.loads(destino_json.read_text(encoding="utf-8"))
    q = consulta_overpass(bbox, margem)
    ultimo_erro: Exception | None = None
    dados = None
    for tentativa, url in enumerate([OVERPASS_URL, OVERPASS_URL, *OVERPASS_ESPELHOS]):
        try:
            r = httpx.post(url, data={"data": q}, timeout=240, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            dados = r.json()
            break
        except (httpx.HTTPError, ValueError) as e:  # 429/502/504 são comuns no Overpass público
            ultimo_erro = e
            time.sleep(min(30, 5 * (tentativa + 1)))
    if dados is None:
        raise RuntimeError(f"Overpass falhou em todas as tentativas: {ultimo_erro}")
    destino_json.parent.mkdir(parents=True, exist_ok=True)
    destino_json.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def bases_de_overpass(dados: dict, localidades: list[dict] | None = None) -> list[dict]:
    """Converte elementos do Overpass em bases {id, nome, lat, lon, fonte}.

    Quando a base não tem nome no OSM, o nome é derivado da localidade mais próxima do GeoNames
    (ex.: "Bombeiros (perto de Barreiras, 3 km)"). Nada é inventado: a posição é sempre a do OSM.
    """
    bases = []
    for e in dados.get("elements", []):
        lat = e.get("lat", (e.get("center") or {}).get("lat"))
        lon = e.get("lon", (e.get("center") or {}).get("lon"))
        if lat is None or lon is None:
            continue
        tags = e.get("tags", {})
        nome = tags.get("name") or tags.get("official_name") or tags.get("operator")
        if not nome:
            nome = "Bombeiros (sem nome no OSM)"
            if localidades:
                perto = min(localidades, key=lambda l: haversine_km(lat, lon, l["lat"], l["lon"]))
                d = haversine_km(lat, lon, perto["lat"], perto["lon"])
                nome = f"Bombeiros (perto de {perto['nome']}, {d:.0f} km)"
        elif localidades and len(nome) <= 4:  # nomes curtos e ambíguos, ex.: "SCI"
            perto = min(localidades, key=lambda l: haversine_km(lat, lon, l["lat"], l["lon"]))
            nome = f"{nome} ({perto['nome']})"
        bases.append({"id": f"osm_{e['type'][0]}{e['id']}", "nome": nome, "lat": round(lat, 6),
                      "lon": round(lon, 6), "fonte": f"OpenStreetMap {e['type']}/{e['id']}"})
    bases.sort(key=lambda b: b["id"])
    return bases


def bases_de_csv(linhas: list[dict]) -> list[dict]:
    return [{**r, "lat": float(r["lat"]), "lon": float(r["lon"])} for r in linhas]


# --------------------------------------------------------------------------- Open-Meteo
def url_open_meteo(pontos: list[tuple[float, float]], past_days: int = 7, forecast_days: int = 1) -> str:
    lats = ",".join(f"{p[0]:g}" for p in pontos)
    lons = ",".join(f"{p[1]:g}" for p in pontos)
    return (f"{OPEN_METEO_URL}?latitude={lats}&longitude={lons}&daily={VARS_DIARIAS}"
            f"&past_days={past_days}&forecast_days={forecast_days}&timezone=UTC")


def baixar_clima_grade(bbox, passo: float = 0.5, past_days: int = 7, lote: int = 100) -> list[dict]:
    """Tempo diário (máx. VPD, máx. vento, mín. umidade, chuva) numa grade fixa sobre a região.

    Guarda a coordenada PEDIDA da grade (o Open-Meteo devolve a célula do modelo, levemente deslocada).
    """
    import httpx

    pontos = grade(bbox, passo)
    linhas: list[dict] = []
    for k in range(0, len(pontos), lote):
        bloco = pontos[k:k + lote]
        r = httpx.get(url_open_meteo(bloco, past_days), timeout=120, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        linhas += clima_de_resposta(bloco, r.json())
    return linhas


def clima_de_resposta(pontos: list[tuple[float, float]], resp) -> list[dict]:
    """Resposta do Open-Meteo (lista na mesma ordem dos pontos pedidos) -> linhas por ponto da grade e dia."""
    if isinstance(resp, dict):
        resp = [resp]
    if len(resp) != len(pontos):
        raise ValueError(f"Open-Meteo devolveu {len(resp)} locais para {len(pontos)} pontos pedidos")
    linhas = []
    for (lat, lon), item in zip(pontos, resp):
        d = item["daily"]
        for i, dia in enumerate(d["time"]):
            linhas.append({
                "lat": lat, "lon": lon, "dia": dia,
                "vpd_kpa_max": d["vapour_pressure_deficit_max"][i],
                "vento_kmh_max": d["wind_speed_10m_max"][i],
                "umidade_min_pct": d["relative_humidity_2m_min"][i],
                "chuva_mm": d["precipitation_sum"][i],
            })
    return linhas


def clima_de_csv(linhas: list[dict]) -> list[dict]:
    def f(v):
        return None if v in ("", None, "None") else float(v)
    return [{"lat": float(r["lat"]), "lon": float(r["lon"]), "dia": r["dia"],
             "vpd_kpa_max": f(r["vpd_kpa_max"]), "vento_kmh_max": f(r["vento_kmh_max"]),
             "umidade_min_pct": f(r.get("umidade_min_pct")), "chuva_mm": f(r.get("chuva_mm"))}
            for r in linhas]
