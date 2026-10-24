"""Valida sql/zetaris_views.sql num Spark SQL local (o motor sob o Zetaris) contra a lógica em Python.

NÃO substitui o teste num Zetaris real: confere a SINTAXE Spark SQL e a SEMÂNTICA (mesmos números), usando
os dados reais do cache e uma resposta real do Open-Meteo (achatada pela mesma view REST do setup).
Diferenças de dialeto do Zetaris (SCHEMASTORE VIEW, LIGHTNING) são trocadas por equivalentes Spark.

Uso (precisa de pyspark 4 + Java 17/21; fora do venv do projeto para não pesar):
  /tmp/spark-venv/bin/python sql/validar_views_spark.py --regiao tocantins
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "scripts")]

from app.core.config import regiao as carregar_regiao  # noqa: E402
from app.data import fontes  # noqa: E402
from app.data.geo import grade  # noqa: E402
from app.data.ocorrencias import montar_ocorrencias  # noqa: E402
import setup_zetaris as sz  # noqa: E402


def para_spark(sql: str) -> str:
    return re.sub(r"CREATE SCHEMASTORE VIEW (\w+) WITH CONTAINER (\w+) AS",
                  r"CREATE OR REPLACE VIEW \2.\1 AS", sql)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--regiao", default="tocantins")
    p.add_argument("--tmp", type=Path, default=Path("/tmp/fococerto-spark"))
    a = p.parse_args()
    r = a.regiao
    cfg = carregar_regiao(r)
    pasta = RAIZ / "data" / "cache" / r
    passo = fontes.passo_clima(r)

    # dados reais: cache + resposta REST real do Open-Meteo (a mesma URL registrada no Zetaris)
    shutil.rmtree(a.tmp, ignore_errors=True)
    a.tmp.mkdir(parents=True)
    import httpx
    pontos = grade(cfg.bbox, passo)
    resp = httpx.get(fontes.url_open_meteo(pontos, past_days=7), timeout=120).json()
    (a.tmp / "clima_raw.json").write_text(json.dumps(resp))
    clima_py = fontes.clima_de_resposta(pontos, resp)
    focos = fontes.focos_de_csv_cache(fontes.ler_csv(pasta / "focos.csv"))
    locs = fontes.localidades_de_csv(fontes.ler_csv(pasta / "localidades.csv"))
    sz_csv = sz.preparar_csvs([r], a.tmp)
    print("csvs:", sz_csv)

    from pyspark.sql import SparkSession
    spark = (SparkSession.builder.master("local[2]").appName("fococerto-views")
             .config("spark.sql.warehouse.dir", str(a.tmp / "wh"))
             .config("spark.sql.session.timeZone", "UTC")
             .config("spark.ui.enabled", "false").getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    for db in ("fococerto_pg", "fococerto_arq", "fococerto_rest", "fococerto"):
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {db}")
    # Postgres -> tipos como no JDBC (DATE e TIMESTAMP)
    (spark.read.option("header", True).csv(str(pasta / "focos.csv"))
     .selectExpr("id", "CAST(lat AS DOUBLE) lat", "CAST(lon AS DOUBLE) lon",
                 "CAST(data_hora_utc AS TIMESTAMP) data_hora_utc", "satelite", "confianca",
                 "CAST(frp AS DOUBLE) frp", "dia_noite", "CAST(dia AS DATE) dia")
     .write.saveAsTable("fococerto_pg.focos"))
    for t in ("regioes", "localidades", "bases"):  # file store CSV com inferSchema, como no Zetaris
        (spark.read.option("header", True).option("inferSchema", True).csv(str(a.tmp / f"{t}.csv"))
         .write.saveAsTable(f"fococerto_arq.{t}"))
    spark.read.option("multiLine", True).json(str(a.tmp / "clima_raw.json")).write.saveAsTable(f"fococerto_rest.clima_{r}_raw")

    cmds = [(f"view clima_{r}", sz.sql_clima_regiao(r)), ("view clima", sz.sql_clima_uniao([r]))] + sz.views_do_arquivo()
    for desc, sql in cmds:
        spark.sql(para_spark(sql))
        print("ok", desc)
    n_clima = spark.sql("SELECT COUNT(*) FROM fococerto.clima").first()[0]
    print(f"clima (REST achatado): {n_clima} linhas; Python: {len(clima_py)}")

    dias = sorted({f["dia"] for f in focos})
    total = difs = 0
    campos = ["n_focos", "frp_soma", "frp_max", "periodos_seguidos", "pop_raio", "vpd_kpa", "vento_kmh", "prioridade"]
    for dia in dias:
        py = {o.id: o for o in montar_ocorrencias(focos, locs, clima_py, cfg, dia, top=None, passo_clima=passo)}
        sq = {row["id"]: row.asDict() for row in spark.sql(
            f"SELECT * FROM fococerto.ocorrencias_prioridade WHERE regiao = '{r}' AND dia = DATE '{dia}'").collect()}
        if set(py) != set(sq):
            print(f"{dia}: ids diferentes: só py {sorted(set(py) - set(sq))[:5]}, só sql {sorted(set(sq) - set(py))[:5]}")
            difs += 1
        for cid in set(py) & set(sq):
            o, s = py[cid], sq[cid]
            total += 1
            erros = []
            for c in campos:
                vp, vs = getattr(o, c), s[c]
                if (vp is None) != (vs is None) or (vp is not None and abs(float(vp) - float(vs)) > 1e-3):
                    erros.append(f"{c}: py={vp} sql={vs}")
            for k, v in o.componentes.items():
                if abs(v - float(s[f"c_{k}"])) > 1e-3:
                    erros.append(f"c_{k}: py={v} sql={s[f'c_{k}']}")
            if abs(o.lat - s["lat"]) > 1e-4 or abs(o.lon - s["lon"]) > 1e-4:
                erros.append("lat/lon")
            if erros:
                difs += 1
                if difs <= 10:
                    print(f"{dia} {cid}: {erros}")
        top_py = [o.id for o in sorted(py.values(), key=lambda o: (-o.prioridade, -o.frp_soma, o.id))[:15]]
        top_sq = [row["id"] for row in spark.sql(
            f"SELECT id FROM fococerto.ocorrencias_prioridade WHERE regiao = '{r}' AND dia = DATE '{dia}' "
            "ORDER BY prioridade DESC, frp_soma DESC, id LIMIT 15").collect()]
        print(f"{dia}: py {len(py)} ocorrências, sql {len(sq)}; top 15 igual: {top_py == top_sq}")
    print(f"comparadas {total} ocorrências; com diferença: {difs}")
    spark.stop()
    return 0 if difs == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
