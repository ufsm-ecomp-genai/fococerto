"""Funções geográficas puras (sem I/O)."""
from __future__ import annotations

import math

RAIO_TERRA_KM = 6371.0088  # raio médio (IUGG)
PASSO_CELULA = 0.1         # graus: células de ~11 km (seção 5, view `ocorrencias`)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta (grande círculo) em km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAIO_TERRA_KM * math.asin(min(1.0, math.sqrt(a)))


def indice_celula(lat: float, lon: float, passo: float = PASSO_CELULA) -> tuple[int, int]:
    """Índices inteiros da célula (canto sudoeste). floor, para o mesmo resultado em Python e SQL.

    O round(…, 9) evita que 0.3/0.1 = 2.9999999 caia na célula errada.
    """
    return math.floor(round(lat / passo, 9)), math.floor(round(lon / passo, 9))


def id_celula(lat: float, lon: float) -> str:
    """Id da ocorrência no formato do contrato: "cel_<lat10>_<lon10>" (ex.: cel_-103_-484)."""
    i, j = indice_celula(lat, lon)
    return f"cel_{i}_{j}"


def centro_celula(cel_id: str, passo: float = PASSO_CELULA) -> tuple[float, float]:
    """Centro geométrico da célula a partir do id."""
    _, i, j = cel_id.split("_")
    return (int(i) + 0.5) * passo, (int(j) + 0.5) * passo


def dentro_bbox(lat: float, lon: float, bbox, margem: float = 0.0) -> bool:
    lat_min, lat_max, lon_min, lon_max = bbox
    return (lat_min - margem) <= lat <= (lat_max + margem) and (lon_min - margem) <= lon <= (lon_max + margem)


def grade(bbox, passo: float) -> list[tuple[float, float]]:
    """Pontos de uma grade regular que cobre a bbox (inclui as bordas)."""
    lat_min, lat_max, lon_min, lon_max = bbox
    n_lat = int(round((lat_max - lat_min) / passo)) + 1
    n_lon = int(round((lon_max - lon_min) / passo)) + 1
    return [(round(lat_min + a * passo, 4), round(lon_min + b * passo, 4))
            for a in range(n_lat) for b in range(n_lon)]
