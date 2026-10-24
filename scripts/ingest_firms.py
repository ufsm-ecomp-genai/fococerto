"""Ingestão do NASA FIRMS (VIIRS Suomi-NPP) no Postgres. Idempotente (INSERT … ON CONFLICT DO NOTHING).

Uso:
  python scripts/ingest_firms.py --regiao tocantins --janela 7d
  python scripts/ingest_firms.py --regiao tocantins --arquivo data/raw/firms_7d.csv --saida-csv data/raw/tocantins/focos.csv
  python scripts/ingest_firms.py --aplicar-schema            # só cria as tabelas (sql/postgres.sql)
DSN: --dsn ou a variável POSTGRES_DSN (ex.: postgresql://postgres:dev@localhost:55432/postgres).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ingest_comum import RAIZ, RAW, bbox_da_regiao, dsn_postgres

from app.data.fontes import COLUNAS_FOCOS, FIRMS_URL, JANELAS_FIRMS, baixar, escrever_csv, ler_firms


def aplicar_schema(conn) -> None:
    sql = (RAIZ / "sql" / "postgres.sql").read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def gravar_postgres(focos: list[dict], dsn: str) -> tuple[int, int]:
    """Grava os focos. Devolve (inseridos, já existentes)."""
    import psycopg

    with psycopg.connect(dsn) as conn:
        aplicar_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM focos")
            antes = cur.fetchone()[0]
            cur.executemany(
                "INSERT INTO focos (id, lat, lon, data_hora_utc, satelite, confianca, frp, dia_noite, dia) "
                "VALUES (%(id)s, %(lat)s, %(lon)s, %(data_hora_utc)s, %(satelite)s, %(confianca)s, %(frp)s, "
                "%(dia_noite)s, %(dia)s) ON CONFLICT (id) DO NOTHING",
                focos,
            )
            cur.execute("SELECT count(*) FROM focos")
            depois = cur.fetchone()[0]
        conn.commit()
    return depois - antes, len(focos) - (depois - antes)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--regiao", help="nome de config/regioes/<regiao>.yaml (recorta pela bbox)")
    p.add_argument("--janela", choices=JANELAS_FIRMS, default="24h")
    p.add_argument("--arquivo", type=Path, help="CSV do FIRMS já baixado (não baixa de novo)")
    p.add_argument("--dsn", help="DSN do Postgres (padrão: POSTGRES_DSN)")
    p.add_argument("--saida-csv", type=Path, help="também grava o recorte neste CSV")
    p.add_argument("--sem-postgres", action="store_true", help="não grava no Postgres")
    p.add_argument("--aplicar-schema", action="store_true", help="só cria as tabelas e sai")
    a = p.parse_args(argv)

    dsn = a.dsn or dsn_postgres()
    if a.aplicar_schema:
        import psycopg
        if not dsn:
            sys.exit("Defina POSTGRES_DSN ou passe --dsn")
        with psycopg.connect(dsn) as conn:
            aplicar_schema(conn)
        print("schema aplicado")
        return 0

    arquivo = a.arquivo
    if arquivo is None:
        arquivo = RAW / f"firms_{a.janela}.csv"
        print(f"baixando {FIRMS_URL.format(janela=a.janela)} -> {arquivo}")
        baixar(FIRMS_URL.format(janela=a.janela), arquivo)
    bbox = bbox_da_regiao(a.regiao) if a.regiao else None
    focos = ler_firms(arquivo, bbox)
    dias = sorted({f["dia"] for f in focos})
    print(f"focos lidos (recorte {a.regiao or 'global'}, deduplicados): {len(focos)}; dias: {dias[0] if dias else '-'} a {dias[-1] if dias else '-'}")
    if a.saida_csv:
        n = escrever_csv(a.saida_csv, focos, COLUNAS_FOCOS)
        print(f"csv: {a.saida_csv} ({n} linhas)")
    if not a.sem_postgres:
        if not dsn:
            sys.exit("Defina POSTGRES_DSN ou passe --dsn (ou use --sem-postgres)")
        novos, repetidos = gravar_postgres(focos, dsn)
        print(f"postgres: {novos} inseridos, {repetidos} já existiam")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
