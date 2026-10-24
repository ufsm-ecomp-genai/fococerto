"""Testes do RepositorioCache (sobre um cache mínimo em tmp_path), das fontes e do parser do Zetaris."""
import json
import os
import sys
from pathlib import Path

import pytest

from app.core.models import Designacao, Plano
from app.data import fontes
from app.data.repositorio import (Repositorio, RepositorioCache, linhas_da_resposta, linhas_decisao)

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def cache(tmp_path):
    """Cache mínimo da região 'tocantins' (usa config/regioes/tocantins.yaml)."""
    pasta = tmp_path / "cache" / "tocantins"
    focos = [
        {"id": "f1", "lat": -10.21, "lon": -48.31, "data_hora_utc": "2026-10-23T17:00:00", "satelite": "N",
         "confianca": "nominal", "frp": 12.5, "dia_noite": "D", "dia": "2026-10-23"},
        {"id": "f2", "lat": -10.22, "lon": -48.32, "data_hora_utc": "2026-10-22T05:00:00", "satelite": "N",
         "confianca": "nominal", "frp": 3.0, "dia_noite": "N", "dia": "2026-10-22"},
        {"id": "f3", "lat": -12.51, "lon": -46.51, "data_hora_utc": "2026-10-23T16:00:00", "satelite": "N",
         "confianca": "high", "frp": 80.0, "dia_noite": "D", "dia": "2026-10-23"},
    ]
    fontes.escrever_csv(pasta / "focos.csv", focos, fontes.COLUNAS_FOCOS)
    fontes.escrever_csv(pasta / "localidades.csv",
                        [{"geonameid": "1", "nome": "Palmas", "lat": -10.18, "lon": -48.33, "pop": 200000, "pais": "BR"}],
                        fontes.COLUNAS_LOCALIDADES)
    fontes.escrever_csv(pasta / "bases.csv",
                        [{"id": "osm_n1", "nome": "1º BBM", "lat": -10.2, "lon": -48.34, "fonte": "OpenStreetMap"}],
                        fontes.COLUNAS_BASES)
    fontes.escrever_csv(pasta / "clima.csv",
                        [{"lat": -10.0, "lon": -48.5, "dia": "2026-10-23", "vpd_kpa_max": 4.0, "vento_kmh_max": 18,
                          "umidade_min_pct": 30, "chuva_mm": 0}], fontes.COLUNAS_CLIMA)
    (pasta / "meta.json").write_text(json.dumps({"passo_clima": 0.5}))
    return RepositorioCache(tmp_path / "cache", tmp_path / "estado")


def test_cache_implementa_protocol(cache):
    assert isinstance(cache, Repositorio)


def test_cache_ocorrencias(cache):
    ocs = cache.ocorrencias("tocantins", "2026-10-23", top=15)
    assert [o.id for o in ocs] == ["cel_-103_-484", "cel_-126_-466"]
    palmas = ocs[0]
    assert palmas.pop_raio == 200000 and palmas.periodos_seguidos == 2
    assert palmas.vpd_kpa == 4.0 and palmas.vento_kmh == 18.0
    assert ocs[1].vpd_kpa is None  # sem ponto da grade nesse lugar no cache mínimo
    assert cache.periodos_disponiveis("tocantins") == ["2026-10-22", "2026-10-23"]


def test_cache_bases_e_historico(cache):
    assert [b.id for b in cache.bases("tocantins")] == ["osm_n1"]
    cache.ocorrencias("tocantins", "2026-10-23")
    h = cache.historico_celula("cel_-103_-484", dias=2)
    assert [(x["dia"], x["n_focos"]) for x in h] == [("2026-10-22", 1), ("2026-10-23", 1)]


def test_cache_salva_decisoes_e_notas(cache, tmp_path):
    plano = Plano(periodo="2026-10-23", regiao="tocantins", rodada=1, reserva=["r9"], nao_atendidas=["cel_-126_-466"],
                  designacoes=[Designacao(recurso_id="r1", ocorrencia_id="cel_-103_-484", ordem=1, eta_h=0.5,
                                          justificativa="pop. 200 mil a 4 km", evidencias=["f1", "pop:200000"])])
    cache.salvar_decisoes(plano, aprovado_por="coordenador")
    cache.salvar_nota("tocantins", "2026-10-23", "manter 1 equipe em Palmas", "coordenador")
    dec = cache.decisoes_salvas("tocantins")
    assert [d["acao"] for d in dec] == ["designar", "reserva", "nao_atendida"]
    assert json.loads(dec[0]["evidencias"]) == ["f1", "pop:200000"]
    assert cache.notas_salvas("tocantins")[0]["texto"] == "manter 1 equipe em Palmas"
    assert (tmp_path / "estado" / "tocantins" / "decisoes.jsonl").exists()


def test_cache_regiao_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        RepositorioCache(tmp_path).ocorrencias("tocantins", "2026-10-23")


def test_cache_real_tocantins_existe_e_e_pequeno():
    pasta = RAIZ / "data" / "cache" / "tocantins"
    if not pasta.exists():
        pytest.skip("cache real não gerado")
    assert sum(p.stat().st_size for p in pasta.iterdir()) < 1_000_000
    ocs = RepositorioCache().ocorrencias("tocantins", "2026-10-23", top=15)
    assert len(ocs) == 15 and ocs == sorted(ocs, key=lambda o: -o.prioridade)


def test_ler_firms_recorta_e_deduplica(tmp_path):
    csv = tmp_path / "firms.csv"
    csv.write_text(
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight\n"
        "-10.2,-48.3,330,0.4,0.4,2026-10-23,1705,N,nominal,2.0NRT,290,12.5,D\n"
        "-10.2,-48.3,330,0.4,0.4,2026-10-23,1705,N,nominal,2.0NRT,290,12.5,D\n"
        "-3.7,-54.6,320,0.4,0.6,2026-10-23,555,N,nominal,2.0NRT,290,28.0,N\n")
    fs = fontes.ler_firms(csv, (-13, -8, -49.5, -45.5))
    assert len(fs) == 1
    assert fs[0]["data_hora_utc"] == "2026-10-23T17:05:00" and fs[0]["frp"] == 12.5
    assert len(fontes.ler_firms(csv)) == 2


def test_clima_de_resposta_usa_ponto_pedido():
    resp = [{"latitude": -10.0176, "longitude": -47.99, "daily": {
        "time": ["2026-10-22", "2026-10-23"], "vapour_pressure_deficit_max": [3.0, 3.5],
        "wind_speed_10m_max": [10, 12], "relative_humidity_2m_min": [40, 35], "precipitation_sum": [0, 0]}}]
    linhas = fontes.clima_de_resposta([(-10.0, -48.0)], resp)
    assert linhas[1] == {"lat": -10.0, "lon": -48.0, "dia": "2026-10-23", "vpd_kpa_max": 3.5,
                         "vento_kmh_max": 12, "umidade_min_pct": 35, "chuva_mm": 0}
    with pytest.raises(ValueError):
        fontes.clima_de_resposta([(-10.0, -48.0), (-10.5, -48.0)], resp)


def test_bases_de_overpass_nomeia_sem_inventar_posicao():
    dados = {"elements": [{"type": "node", "id": 1, "lat": -12.15, "lon": -45.0, "tags": {"amenity": "fire_station"}},
                          {"type": "way", "id": 2, "center": {"lat": -10.2, "lon": -48.34}, "tags": {"name": "1º BBM"}}]}
    locs = [{"nome": "Barreiras", "lat": -12.1528, "lon": -44.99, "pop": 158000}]
    b = fontes.bases_de_overpass(dados, locs)
    assert b[0]["id"] == "osm_n1" and b[0]["nome"].startswith("Bombeiros (perto de Barreiras")
    assert (b[0]["lat"], b[0]["lon"]) == (-12.15, -45.0)
    assert b[1]["nome"] == "1º BBM"


def test_linhas_decisao():
    plano = Plano(periodo="p", regiao="r", designacoes=[], reserva=["a"], nao_atendidas=[])
    assert linhas_decisao(plano, "x")[0]["acao"] == "reserva"


@pytest.mark.parametrize("resp", [
    {"data": [{"n": "3"}]},
    {"data": {"columns": ["n"], "rows": [["3"]]}},
    {"data": {"schema": [{"name": "n"}], "rows": [["3"]]}},
])
def test_linhas_da_resposta_zetaris(resp):
    assert linhas_da_resposta(resp) == [{"n": "3"}]


def test_setup_zetaris_gera_comandos_sem_ponto_e_virgula():
    sys.path.insert(0, str(RAIZ / "scripts"))
    import setup_zetaris as sz
    cmds = sz.comandos(["tocantins", "iberia"], "postgresql://u:p@localhost:55432/db", "host.docker.internal", "/x")
    nomes = [d for d, _ in cmds]
    assert "view ocorrencias_prioridade" in nomes and "CACHE clima tocantins" in nomes
    assert all(not s.rstrip().endswith(";") for _, s in cmds)
    pg = dict(cmds)["datasource Postgres"]
    assert "jdbc:postgresql://host.docker.internal:55432/db" in pg


@pytest.mark.skipif(not os.environ.get("POSTGRES_DSN_TESTE"), reason="defina POSTGRES_DSN_TESTE para testar a escrita")
def test_escrita_postgres():
    import psycopg
    from app.data.repositorio import EscritaPostgres
    dsn = os.environ["POSTGRES_DSN_TESTE"]
    with psycopg.connect(dsn) as conn:
        conn.execute((RAIZ / "sql" / "postgres.sql").read_text())
        antes = conn.execute("SELECT count(*) FROM decisoes").fetchone()[0]
    plano = Plano(periodo="2026-10-23", regiao="tocantins", reserva=["r9"],
                  designacoes=[Designacao(recurso_id="r1", ocorrencia_id="cel_1_1", ordem=1, eta_h=1.0,
                                          justificativa="teste", evidencias=["f1"])])
    e = EscritaPostgres(dsn)
    e.salvar_decisoes(plano, "pytest")
    e.salvar_nota("tocantins", "2026-10-23", "nota de teste", "pytest")
    with psycopg.connect(dsn) as conn:
        assert conn.execute("SELECT count(*) FROM decisoes").fetchone()[0] == antes + 2
        assert conn.execute("SELECT texto FROM notas ORDER BY seq DESC LIMIT 1").fetchone()[0] == "nota de teste"
