"""Congela em data/cache/<regiao>/ um recorte pequeno e real para o sample mode (--sample).

Arquivos gerados:
  focos.csv        detecções FIRMS VIIRS da bbox (janela 7d por padrão)
  localidades.csv  GeoNames cities1000 na bbox + margem
  bases.csv        bombeiros do OSM (Overpass, bbox + 1°)
  clima.csv        Open-Meteo diário numa grade fixa (0,5°), últimos 7 dias + hoje
  meta.json        fontes, data do download e contagens

Uso:
  python scripts/congelar_cache.py --regiao tocantins [--firms data/raw/firms_7d.csv] [--passo-clima 0.5]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ingest_comum import CACHE, RAW, bbox_da_regiao

from app.data.fontes import (COLUNAS_BASES, COLUNAS_CLIMA, COLUNAS_FOCOS, COLUNAS_LOCALIDADES,
                             FIRMS_URL, GEONAMES_URL, OPEN_METEO_URL, OVERPASS_URL, baixar,
                             baixar_clima_grade, baixar_overpass, bases_de_overpass, escrever_csv,
                             ler_firms, ler_geonames, passo_clima)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--regiao", required=True)
    p.add_argument("--firms", type=Path, help="CSV do FIRMS já baixado (padrão: data/raw/firms_7d.csv, baixa se faltar)")
    p.add_argument("--passo-clima", type=float, help="graus (padrão: fontes.PASSO_CLIMA da região)")
    p.add_argument("--margem-localidades", type=float, default=0.2)
    p.add_argument("--margem-bases", type=float, default=1.0)
    a = p.parse_args(argv)

    bbox = bbox_da_regiao(a.regiao)
    a.passo_clima = a.passo_clima or passo_clima(a.regiao)
    destino = CACHE / a.regiao
    firms = a.firms or RAW / "firms_7d.csv"
    if not firms.exists():
        baixar(FIRMS_URL.format(janela="7d"), firms)
    cities = RAW / "cities1000.zip"
    if not cities.exists():
        baixar(GEONAMES_URL, cities)

    focos = ler_firms(firms, bbox)
    locs = ler_geonames(cities, bbox, a.margem_localidades)
    dados_osm = baixar_overpass(bbox, a.margem_bases, RAW / a.regiao / "overpass.json")
    bases = bases_de_overpass(dados_osm, ler_geonames(cities, bbox, a.margem_bases + 0.5))
    clima = baixar_clima_grade(bbox, a.passo_clima, past_days=7)

    cont = {
        "focos": escrever_csv(destino / "focos.csv", focos, COLUNAS_FOCOS),
        "localidades": escrever_csv(destino / "localidades.csv", locs, COLUNAS_LOCALIDADES),
        "bases": escrever_csv(destino / "bases.csv", bases, COLUNAS_BASES),
        "clima": escrever_csv(destino / "clima.csv", clima, COLUNAS_CLIMA),
    }
    dias = sorted({f["dia"] for f in focos})
    meta = {
        "regiao": a.regiao,
        "bbox": list(bbox),
        "passo_clima": a.passo_clima,
        "congelado_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dias_focos": dias,
        "contagens": cont,
        "fontes": {
            "focos": FIRMS_URL.format(janela="7d") + f" (arquivo local: {firms.name})",
            "localidades": GEONAMES_URL + f" (bbox + {a.margem_localidades}°)",
            "bases": OVERPASS_URL + f' amenity=fire_station (bbox + {a.margem_bases}°)',
            "clima": OPEN_METEO_URL + f" diário, grade {a.passo_clima}°, past_days=7",
        },
        "simulado": False,
        "observacao": "Dados reais congelados. TI/UC ainda não incluídos (dist_ti_uc_km = null).",
    }
    (destino / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    total = 0
    for arq in sorted(destino.iterdir()):
        total += arq.stat().st_size
        print(f"{arq.relative_to(CACHE.parent.parent)}: {arq.stat().st_size / 1024:.1f} KB")
    print(f"contagens: {cont}; dias: {dias[0]}..{dias[-1]}; total {total / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
