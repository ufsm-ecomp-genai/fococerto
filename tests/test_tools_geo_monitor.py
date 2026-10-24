import math

from app.tools.geo import eta_h, haversine_km
from app.tools.monitor import monitor
from tests.fakes import oc, regiao_teste


def test_haversine_um_grau_de_latitude():
    assert math.isclose(haversine_km(-10, -47, -11, -47), 111.2, rel_tol=0.01)


def test_eta_terrestre_usa_tortuosidade_e_velocidade():
    cfg = regiao_teste()
    d = haversine_km(-10, -47, -11, -47)
    assert math.isclose(eta_h(-10, -47, -11, -47, cfg), d * 1.4 / 40, rel_tol=1e-9)


def test_eta_aereo_e_menor_que_terrestre():
    cfg = regiao_teste()
    assert eta_h(-10, -47, -11, -47, cfg, "aereo") < eta_h(-10, -47, -11, -47, cfg)


def test_monitor_status():
    ant = [oc("a", -10, -47, 0.5, n_focos=4, frp_soma=40), oc("b", -10, -47, 0.5, n_focos=4, frp_soma=40),
           oc("c", -10, -47, 0.5, n_focos=4, frp_soma=40, periodos_seguidos=3)]
    atu = [oc("a", -10, -47, 0.5, n_focos=8, frp_soma=40), oc("b", -10, -47, 0.5, n_focos=2, frp_soma=20),
           oc("c", -10, -47, 0.5, n_focos=4, frp_soma=42), oc("d", -10, -47, 0.5)]
    st = {o.id: o for o in monitor(atu, ant)}
    assert st["a"].status == "crescendo"
    assert st["b"].status == "diminuindo"
    assert st["c"].status == "estavel" and st["c"].periodos_seguidos == 4
    assert st["d"].status == "nova"
    assert atu[0].status is None  # não altera a entrada
