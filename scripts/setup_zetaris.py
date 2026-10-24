"""Registra no Zetaris, POR SCRIPT (nunca à mão), todas as fontes e views do FocoCerto.

** NÃO TESTADO contra um Zetaris real ** (não havia Zetaris rodando no desenvolvimento). A sintaxe segue
01-zetaris/getting-started (guia de comandos Lightning SQL e receitas REST) e as dicas confirmadas nos chats:
- CSV: copiar para o file store do container (docker cp) e CREATE LIGHTNING FILESTORE TABLE … FORMAT CSV.
- Dentro do SQL do Zetaris, serviços do host ficam em host.docker.internal.
- Pela REST: um comando por requisição, sem ponto e vírgula; valores voltam como string.
- Tabelas REST precisam de CACHE TABLE, refeito depois de reiniciar (use --so-cache).

Passos:
  1. Postgres:   CREATE DATASOURCE fococerto_pg (JDBC) + REGISTER DATASOURCE TABLES
  2. Arquivos:   regioes.csv, localidades.csv, bases.csv -> docker cp -> CREATE LIGHTNING FILESTORE TABLE
  3. REST:       uma tabela Open-Meteo por região (grade fixa) + CACHE TABLE
  4. Views:      fococerto.clima_<regiao>, fococerto.clima, e sql/zetaris_views.sql
  5. Conferência: SELECT COUNT(*) em cada objeto

Uso:
  python scripts/setup_zetaris.py --dry-run                 # só imprime os comandos (não precisa de Zetaris)
  python scripts/setup_zetaris.py --regioes tocantins,iberia
  python scripts/setup_zetaris.py --so-cache                # refaz CACHE TABLE (depois de reiniciar o Zetaris)
Variáveis (.env): ZETARIS_REST_URL, ZETARIS_API_KEY, ZETARIS_ORG_ID, POSTGRES_DSN,
  ZETARIS_PG_HOST (padrão host.docker.internal), ZETARIS_DRIVER_CONTAINER (padrão zetaris-driver-1),
  ZETARIS_FILESTORE_DIR (padrão /home/zetaris/customer-data/shared/fococerto).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from ingest_comum import CACHE, RAIZ, RAW

from app.core.config import carregar_env, regiao as carregar_regiao
from app.data import fontes
from app.data.geo import grade

PG = "fococerto_pg"
ARQ = "fococerto_arq"
REST = "fococerto_rest"
CONTAINER = "fococerto"
TABELAS_PG = ["focos", "recursos_periodo", "decisoes", "notas"]
VIEWS = ["ocorrencias", "ocorrencias_localidades", "ocorrencias_contexto", "ocorrencias_prioridade"]


# --------------------------------------------------------------------------- comandos SQL
def sql_datasource_pg(dsn: str, host: str) -> list[tuple[str, str]]:
    u = urlparse(dsn)
    jdbc = f"jdbc:postgresql://{host}:{u.port or 5432}{u.path or '/postgres'}"
    lista = ", ".join(f"'{t}'" for t in TABELAS_PG)
    return [
        ("datasource Postgres",
         f'CREATE DATASOURCE {PG} DESCRIBE BY "FocoCerto Postgres (focos, decisoes, notas)" OPTIONS ('
         f'jdbcdriver "org.postgresql.Driver", jdbcurl "{jdbc}", username "{u.username or "postgres"}", '
         f'password "{u.password or ""}", fetchsize "1000")'),
        ("tabelas do Postgres", f"REGISTER DATASOURCE TABLES ({lista}) FROM {PG}"),
    ]


def sql_filestore(dir_container: str) -> list[tuple[str, str]]:
    cmds = [("database de arquivos", f'CREATE LIGHTNING DATABASE {ARQ.upper()} DESCRIBE BY "FocoCerto CSV (GeoNames, OSM, regioes)"')]
    for t in ("regioes", "localidades", "bases"):
        cmds.append((f"file store {t}",
                     f"CREATE LIGHTNING FILESTORE TABLE {t} FROM {ARQ.upper()} FORMAT CSV OPTIONS ("
                     f'PATH "{dir_container}/{t}.csv", header "true", inferSchema "true")'))
    return cmds


def sql_rest(regioes: list[str]) -> list[tuple[str, str]]:
    cmds = [("database REST", f'CREATE LIGHTNING DATABASE {REST.upper()} DESCRIBE BY "FocoCerto Open-Meteo (grade fixa)"')]
    for r in regioes:
        url = fontes.url_open_meteo(grade(carregar_regiao(r).bbox, fontes.passo_clima(r)), past_days=7)
        cmds.append((f"REST clima {r}",
                     f"CREATE LIGHTNING REST TABLE clima_{r}_raw FROM {REST.upper()} REQUEST("
                     f'endpoint "{url}", method "get", response_type "json", http_encoding "URLENCODED"'
                     ") HEADER () BODY ()"))
    return cmds


def sql_cache(regioes: list[str]) -> list[tuple[str, str]]:
    return [(f"CACHE clima {r}", f"CACHE TABLE {REST}.clima_{r}_raw") for r in regioes]


def sql_clima_regiao(r: str) -> str:
    """View achatada de uma tabela REST do Open-Meteo: uma linha por ponto da grade e dia.

    A resposta traz a célula do modelo (levemente deslocada); arredondar ao passo devolve o ponto pedido.
    """
    p = fontes.passo_clima(r)
    return (f"CREATE SCHEMASTORE VIEW clima_{r} WITH CONTAINER {CONTAINER} AS\n"
            f"SELECT '{r}' AS regiao,\n"
            f"       ROUND(ROUND(latitude / {p}) * {p}, 4) AS lat,\n"
            f"       ROUND(ROUND(longitude / {p}) * {p}, 4) AS lon,\n"
            "       CAST(t.dia AS DATE) AS dia,\n"
            "       CAST(daily.vapour_pressure_deficit_max[t.i] AS DOUBLE) AS vpd_kpa_max,\n"
            "       CAST(daily.wind_speed_10m_max[t.i] AS DOUBLE) AS vento_kmh_max,\n"
            "       CAST(daily.relative_humidity_2m_min[t.i] AS DOUBLE) AS umidade_min_pct,\n"
            "       CAST(daily.precipitation_sum[t.i] AS DOUBLE) AS chuva_mm\n"
            f"FROM {REST}.clima_{r}_raw\n"
            "LATERAL VIEW posexplode(daily.time) t AS i, dia")


def sql_clima_uniao(regioes: list[str]) -> str:
    partes = "\nUNION ALL\n".join(f"SELECT * FROM {CONTAINER}.clima_{r}" for r in regioes)
    return f"CREATE SCHEMASTORE VIEW clima WITH CONTAINER {CONTAINER} AS\n{partes}"


def views_do_arquivo(caminho: Path = RAIZ / "sql" / "zetaris_views.sql") -> list[tuple[str, str]]:
    """Divide o arquivo em comandos (";" no fim da linha), sem comentários e sem o ponto e vírgula."""
    texto = "\n".join(l for l in caminho.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--"))
    cmds = [c.strip() for c in re.split(r";\s*$", texto, flags=re.M) if c.strip()]
    out = []
    for c in cmds:
        m = re.match(r"CREATE SCHEMASTORE VIEW (\w+)", c)
        out.append((f"view {m.group(1) if m else '?'}", c))
    return out


def comandos(regioes: list[str], dsn: str, pg_host: str, dir_container: str) -> list[tuple[str, str]]:
    cmds = sql_datasource_pg(dsn, pg_host) + sql_filestore(dir_container) + sql_rest(regioes) + sql_cache(regioes)
    cmds.append(("container", f"CREATE SCHEMASTORE CONTAINER {CONTAINER}"))
    cmds += [(f"view clima_{r}", sql_clima_regiao(r)) for r in regioes]
    cmds.append(("view clima", sql_clima_uniao(regioes)))
    cmds += views_do_arquivo()
    return cmds


def conferencias(regioes: list[str]) -> list[tuple[str, str]]:
    objs = [f"{PG}.focos", f"{ARQ}.regioes", f"{ARQ}.localidades", f"{ARQ}.bases", f"{CONTAINER}.clima"]
    objs += [f"{CONTAINER}.{v}" for v in VIEWS]
    return [(f"conta {o}", f"SELECT COUNT(*) AS n FROM {o}") for o in objs]


# --------------------------------------------------------------------------- CSVs do file store
def preparar_csvs(regioes: list[str], destino: Path) -> dict[str, int]:
    """Junta regiões, localidades e bases de todas as regiões (do cache, ou das fontes se não houver cache)."""
    regs, locs, bases = [], [], []
    cities = RAW / "cities1000.zip"
    for r in regioes:
        cfg = carregar_regiao(r)
        lat_min, lat_max, lon_min, lon_max = cfg.bbox
        regs.append({"regiao": r, "lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max,
                     "raio_km": cfg.raio_exposicao_km, "passo_clima": fontes.passo_clima(r)})
        pasta = CACHE / r
        if (pasta / "localidades.csv").exists():
            ls = fontes.ler_csv(pasta / "localidades.csv")
        else:
            if not cities.exists():
                fontes.baixar(fontes.GEONAMES_URL, cities)
            ls = fontes.ler_geonames(cities, cfg.bbox, 0.2)
        if (pasta / "bases.csv").exists():
            bs = fontes.ler_csv(pasta / "bases.csv")
        else:
            dados = fontes.baixar_overpass(cfg.bbox, 1.0, RAW / r / "overpass.json")
            bs = fontes.bases_de_overpass(dados, fontes.ler_geonames(cities, cfg.bbox, 1.5) if cities.exists() else None)
        locs += [{**l, "regiao": r} for l in ls]
        bases += [{**b, "regiao": r} for b in bs]
    return {
        "regioes": fontes.escrever_csv(destino / "regioes.csv", regs,
                                       ["regiao", "lat_min", "lat_max", "lon_min", "lon_max", "raio_km", "passo_clima"]),
        "localidades": fontes.escrever_csv(destino / "localidades.csv", locs, ["regiao"] + fontes.COLUNAS_LOCALIDADES),
        "bases": fontes.escrever_csv(destino / "bases.csv", bases, ["regiao"] + fontes.COLUNAS_BASES),
    }


def copiar_para_container(origem: Path, container: str, dir_container: str, dry: bool) -> None:
    cmds = [["docker", "exec", container, "mkdir", "-p", dir_container]]
    cmds += [["docker", "cp", str(origem / f"{t}.csv"), f"{container}:{dir_container}/{t}.csv"]
             for t in ("regioes", "localidades", "bases")]
    for c in cmds:
        print("$ " + " ".join(c))
        if not dry:
            subprocess.run(c, check=True)


# --------------------------------------------------------------------------- execução
def executar(cmds: list[tuple[str, str]], repo, ignorar_existente: bool) -> int:
    falhas = 0
    for desc, sql in cmds:
        try:
            linhas = repo.sql(sql)
            print(f"ok   {desc}" + (f" -> {linhas[:1]}" if linhas else ""))
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if ignorar_existente and re.search(r"already exist|já existe|exists", msg, re.I):
                print(f"já existe  {desc}")
                continue
            falhas += 1
            print(f"FALHOU {desc}: {msg[:300]}")
    return falhas


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--regioes", default="tocantins,iberia")
    p.add_argument("--dry-run", action="store_true", help="só imprime os comandos")
    p.add_argument("--so-cache", action="store_true", help="só refaz CACHE TABLE das tabelas REST")
    p.add_argument("--sem-copiar", action="store_true", help="não faz docker cp dos CSVs")
    p.add_argument("--ignorar-existente", action="store_true", default=True)
    a = p.parse_args(argv)
    carregar_env()
    regioes = [r.strip() for r in a.regioes.split(",") if r.strip()]
    dsn = os.environ.get("POSTGRES_DSN", "postgresql://postgres:SENHA@localhost:5432/postgres")
    pg_host = os.environ.get("ZETARIS_PG_HOST", "host.docker.internal")
    container = os.environ.get("ZETARIS_DRIVER_CONTAINER", "zetaris-driver-1")
    dir_container = os.environ.get("ZETARIS_FILESTORE_DIR", "/home/zetaris/customer-data/shared/fococerto")

    cmds = sql_cache(regioes) if a.so_cache else comandos(regioes, dsn, pg_host, dir_container)
    if a.dry_run:
        for desc, sql in cmds + ([] if a.so_cache else conferencias(regioes)):
            print(f"-- {desc}\n{re.sub(r'password \"[^\"]*\"', 'password \"***\"', sql)}\n")
        if not a.so_cache:
            n = preparar_csvs(regioes, RAW / "zetaris")
            print(f"-- CSVs para o file store em {RAW / 'zetaris'}: {n}")
            copiar_para_container(RAW / "zetaris", container, dir_container, dry=True)
        return 0

    from app.data.repositorio import RepositorioZetaris
    repo = RepositorioZetaris(dsn=dsn)
    if not a.so_cache:
        n = preparar_csvs(regioes, RAW / "zetaris")
        print(f"CSVs: {n}")
        if not a.sem_copiar:
            copiar_para_container(RAW / "zetaris", container, dir_container, dry=False)
    falhas = executar(cmds, repo, a.ignorar_existente)
    if not a.so_cache:
        falhas += executar(conferencias(regioes), repo, False)
    print(f"falhas: {falhas}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
