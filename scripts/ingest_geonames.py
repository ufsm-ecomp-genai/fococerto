"""GeoNames cities1000 -> CSV filtrado por bbox da região (com margem) e/ou países.

Uso:
  python scripts/ingest_geonames.py --regiao tocantins            # -> data/raw/tocantins/localidades.csv
  python scripts/ingest_geonames.py --paises ES,PT --saida x.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ingest_comum import RAW, bbox_da_regiao

from app.data.fontes import COLUNAS_LOCALIDADES, GEONAMES_URL, baixar, escrever_csv, ler_geonames


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--regiao")
    p.add_argument("--margem", type=float, default=0.2, help="graus além da bbox (localidades perto da borda)")
    p.add_argument("--paises", help="códigos ISO separados por vírgula (ex.: BR ou ES,PT)")
    p.add_argument("--arquivo", type=Path, default=RAW / "cities1000.zip")
    p.add_argument("--saida", type=Path)
    a = p.parse_args(argv)
    if not a.regiao and not a.paises:
        p.error("informe --regiao e/ou --paises")
    if not a.arquivo.exists():
        print(f"baixando {GEONAMES_URL}")
        baixar(GEONAMES_URL, a.arquivo)
    bbox = bbox_da_regiao(a.regiao) if a.regiao else None
    paises = set(a.paises.split(",")) if a.paises else None
    locs = ler_geonames(a.arquivo, bbox, a.margem, paises)
    saida = a.saida or RAW / (a.regiao or "paises") / "localidades.csv"
    n = escrever_csv(saida, locs, COLUNAS_LOCALIDADES)
    print(f"localidades: {n} -> {saida} (pop. somada {sum(l['pop'] for l in locs):,})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
