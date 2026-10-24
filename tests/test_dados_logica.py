"""Testes da lógica de dados (app/data/geo.py e app/data/ocorrencias.py) com dados pequenos e conhecidos."""
import math

import pytest

from app.core.models import Ocorrencia, RegiaoCfg
from app.data import geo
from app.data import ocorrencias as oc

REG = RegiaoCfg(nome="teste", bbox=(-11.0, -9.0, -49.0, -47.0), raio_exposicao_km=15)


def foco(fid, lat, lon, dia, hora="1700", frp=10.0, dn="D"):
    return {"id": fid, "lat": lat, "lon": lon, "dia": dia, "frp": frp, "dia_noite": dn,
            "data_hora_utc": f"{dia}T{hora[:2]}:{hora[2:]}:00", "satelite": "N", "confianca": "nominal"}


# ------------------------------------------------------------------ haversine e células
def test_haversine_um_grau_de_latitude():
    assert geo.haversine_km(0, 0, 1, 0) == pytest.approx(111.195, abs=0.01)


def test_haversine_longitude_encolhe_com_latitude():
    assert geo.haversine_km(60, 0, 60, 1) == pytest.approx(111.195 * math.cos(math.radians(60)), rel=1e-3)


def test_haversine_palmas_gurupi():
    # Palmas (-10.1844, -48.3336) a Gurupi (-11.7292, -49.0686): ~187 km em linha reta
    assert geo.haversine_km(-10.1844, -48.3336, -11.7292, -49.0686) == pytest.approx(187, abs=3)


def test_haversine_simetrica_e_zero():
    assert geo.haversine_km(-10, -48, -10, -48) == 0
    assert geo.haversine_km(-10, -48, -9, -47) == pytest.approx(geo.haversine_km(-9, -47, -10, -48))


def test_id_celula_usa_floor():
    assert geo.id_celula(-10.23, -48.37) == "cel_-103_-484"
    assert geo.id_celula(10.23, 48.37) == "cel_102_483"
    assert geo.id_celula(-10.0, -48.0) == "cel_-100_-480"
    assert geo.id_celula(0.3, 0.7) == "cel_3_7"  # 0.3/0.1 = 2.9999999 sem o round


def test_centro_celula():
    assert geo.centro_celula("cel_-103_-484") == pytest.approx((-10.25, -48.35))


def test_grade_cobre_bbox():
    g = geo.grade((-13, -8, -49.5, -45.5), 0.5)
    assert len(g) == 11 * 9
    assert (-13.0, -49.5) in g and (-8.0, -45.5) in g


# ------------------------------------------------------------------ agrupamento
def test_agrupar_por_celula_e_dia():
    focos = [
        foco("a", -10.21, -48.31, "2026-10-23", frp=5),
        foco("b", -10.29, -48.39, "2026-10-23", frp=15, hora="0500"),
        foco("c", -10.51, -48.31, "2026-10-23", frp=1),     # outra célula
        foco("d", -10.21, -48.31, "2026-10-22", frp=99),    # mesmo lugar, dia anterior
    ]
    g = {x["id"]: x for x in oc.agrupar(focos, "2026-10-23")}
    assert set(g) == {"cel_-103_-484", "cel_-106_-484"}
    a = g["cel_-103_-484"]
    assert a["n_focos"] == 2 and a["frp_soma"] == 20 and a["frp_max"] == 15
    assert a["lat"] == pytest.approx(-10.25) and a["lon"] == pytest.approx(-48.35)
    assert a["primeiro"] == "2026-10-23T05:00:00" and a["ultimo"] == "2026-10-23T17:00:00"
    assert a["periodos_seguidos"] == 2 and a["n_focos_ontem"] == 1
    assert g["cel_-106_-484"]["periodos_seguidos"] == 1 and g["cel_-106_-484"]["n_focos_ontem"] == 0


def test_periodos_seguidos_para_no_buraco():
    dias = {"2026-10-23", "2026-10-22", "2026-10-20", "2026-10-19"}
    assert oc.periodos_seguidos(dias, "2026-10-23") == 2
    assert oc.periodos_seguidos(dias, "2026-10-20") == 2
    assert oc.periodos_seguidos(dias, "2026-10-21") == 0


def test_agrupar_periodo_sem_focos():
    assert oc.agrupar([foco("a", -10.2, -48.3, "2026-10-22")], "2026-10-23") == []


# ------------------------------------------------------------------ contexto
def test_localidades_no_raio_ordenadas():
    locs = [{"nome": "Perto", "lat": -10.25, "lon": -48.30, "pop": 2000},
            {"nome": "Longe", "lat": -10.25, "lon": -48.10, "pop": 50000},   # ~27 km
            {"nome": "Meio", "lat": -10.35, "lon": -48.35, "pop": 1000}]
    r = oc.localidades_no_raio(-10.25, -48.35, locs, 15)
    assert [l["nome"] for l in r] == ["Perto", "Meio"]
    assert r[0]["dist_km"] == pytest.approx(5.5, abs=0.1)


def test_clima_por_grade_e_mais_proximo():
    clima = [{"lat": -10.0, "lon": -48.5, "dia": "2026-10-23", "vpd_kpa_max": 3.0, "vento_kmh_max": 10.0},
             {"lat": -10.5, "lon": -48.5, "dia": "2026-10-23", "vpd_kpa_max": 5.0, "vento_kmh_max": 20.0}]
    g = [{"id": "x", "dia": "2026-10-23", "lat": -10.30, "lon": -48.40}]
    oc.aplicar_contexto(g, [], clima, 15)
    assert g[0]["vpd_kpa"] == 5.0
    oc.aplicar_contexto(g, [], clima, 15, passo_clima=0.5)
    assert g[0]["vpd_kpa"] == 5.0 and g[0]["vento_kmh"] == 20.0


def test_ponto_grade_arredonda_como_spark():
    assert oc.ponto_grade(-10.25, -48.75, 0.5) == (-10.5, -49.0)  # metade para longe do zero
    assert oc.ponto_grade(-10.24, -48.74, 0.5) == (-10.0, -48.5)


# ------------------------------------------------------------------ fórmula
def test_pesos_somam_um():
    assert sum(oc.PESOS.values()) == pytest.approx(1.0)


def test_prioridade_extremos():
    assert oc.calcular_prioridade({k: 1.0 for k in oc.PESOS}) == pytest.approx(1.0)
    assert oc.calcular_prioridade({k: 0.0 for k in oc.PESOS}) == 0.0
    assert oc.calcular_prioridade({"exposicao": 1.0}) == pytest.approx(0.35)


def test_componente_exposicao():
    assert oc.componente_exposicao(0, None, 15) == 0.0
    assert oc.componente_exposicao(100_000, None, 15) == 1.0
    assert oc.componente_exposicao(1000, None, 15) == pytest.approx(math.log10(1001) / math.log10(100001), abs=1e-4)
    # TI/UC a 0 km soma 0,3
    assert oc.componente_exposicao(0, 0.0, 15) == pytest.approx(0.3)
    assert oc.componente_exposicao(0, 30.0, 15) == 0.0


def test_componente_intensidade():
    assert oc.componente_intensidade(50, 50) == 1.0
    assert oc.componente_intensidade(0, 50) == 0.0
    assert 0 < oc.componente_intensidade(5, 50) < 1
    assert oc.componente_intensidade(5, 0) == 0.0


def test_componente_tempo():
    # VPD 4 kPa = 40 hPa; vento 36 km/h = 10 m/s -> HDW 400 = referência
    assert oc.componente_tempo(4.0, 36.0) == pytest.approx(1.0)
    assert oc.componente_tempo(2.0, 36.0) == pytest.approx(0.5)
    assert oc.componente_tempo(None, 10.0) == 0.0


def test_componente_persistencia_e_crescimento():
    assert oc.componente_persistencia(1) == 0.0
    assert oc.componente_persistencia(4) == 1.0
    assert oc.componente_persistencia(10) == 1.0
    assert oc.componente_crescimento(5, 0) == 1.0     # nova
    assert oc.componente_crescimento(5, 5) == 0.0
    assert oc.componente_crescimento(2, 8) == 0.0     # diminuindo não pontua
    assert oc.componente_crescimento(8, 2) == pytest.approx(0.75)


# ------------------------------------------------------------------ pipeline
def test_montar_ocorrencias_ordena_por_prioridade():
    focos = [
        foco("a", -10.21, -48.31, "2026-10-23", frp=5),       # perto de cidade
        foco("b", -9.51, -47.51, "2026-10-23", frp=200),      # forte, isolado
        foco("c", -9.51, -47.51, "2026-10-22", frp=200),
        foco("fora", -5.0, -40.0, "2026-10-23", frp=999),     # fora da bbox
    ]
    locs = [{"nome": "Cidade", "lat": -10.22, "lon": -48.33, "pop": 50000}]
    clima = [{"lat": -10.0, "lon": -48.5, "dia": "2026-10-23", "vpd_kpa_max": 4.0, "vento_kmh_max": 18.0}]
    ocs = oc.montar_ocorrencias(focos, locs, clima, REG, "2026-10-23", top=None)
    assert all(isinstance(o, Ocorrencia) for o in ocs)
    assert [o.id for o in ocs] == ["cel_-103_-484", "cel_-96_-476"]
    a, b = ocs
    assert a.pop_raio == 50000 and a.localidades[0]["nome"] == "Cidade"
    assert b.pop_raio == 0 and b.periodos_seguidos == 2 and b.componentes["intensidade"] == 1.0
    assert b.componentes["crescimento"] == 0.0
    assert a.prioridade == pytest.approx(sum(oc.PESOS[k] * v for k, v in a.componentes.items()), abs=1e-3)
    assert a.status is None
    assert len(oc.montar_ocorrencias(focos, locs, clima, REG, "2026-10-23", top=1)) == 1


def test_historico_preenche_dias_sem_foco():
    focos = [foco("a", -10.21, -48.31, "2026-10-23", dn="N", frp=3), foco("b", -10.22, -48.32, "2026-10-21", frp=7)]
    h = oc.historico(focos, "cel_-103_-484", "2026-10-23", dias=3)
    assert [x["dia"] for x in h] == ["2026-10-21", "2026-10-22", "2026-10-23"]
    assert [x["n_focos"] for x in h] == [1, 0, 1]
    assert h[2]["dia_noite"] == {"D": 0, "N": 1} and h[0]["frp_soma"] == 7.0
