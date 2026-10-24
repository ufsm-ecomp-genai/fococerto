"""Bases de bombeiros do OpenStreetMap (Overpass, por bbox) -> CSV. Cache em arquivo JSON.

Uso:
  python scripts/ingest_osm.py --regiao tocantins               # -> data/raw/tocantins/bases.csv
  python scripts/ingest_osm.py --regiao tocantins --forcar      # ignora o cache
A margem (padrão 1°) inclui bases fora da bbox que podem despachar para dentro dela.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ingest_comum import RAW, bbox_da_regiao

from app.data.fontes import (COLUNAS_BASES, baixar_overpass, bases_de_overpass, escrever_csv,
                             ler_geonames)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--regiao", required=True)
    p.add_argument("--margem", type=float, default=1.0)
    p.add_argument("--forcar", action="store_true")
    p.add_argument("--max-idade-h", type=float, default=24 * 7)
    p.add_argument("--saida", type=Path)
    a = p.parse_args(argv)
    bbox = bbox_da_regiao(a.regiao)
    pasta = RAW / a.regiao
    dados = baixar_overpass(bbox, a.margem, pasta / "overpass.json", a.max_idade_h, a.forcar)
    cities = RAW / "cities1000.zip"
    locs = ler_geonames(cities, bbox, a.margem + 0.5) if cities.exists() else None
    bases = bases_de_overpass(dados, locs)
    saida = a.saida or pasta / "bases.csv"
    n = escrever_csv(saida, bases, COLUNAS_BASES)
    print(f"bases: {n} -> {saida}")
    for b in bases:
        print(f"  {b['id']}: {b['nome']} ({b['lat']:.4f}, {b['lon']:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
