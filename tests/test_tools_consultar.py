import pytest

from app.core.logging import LogExecucao
from app.tools.consultar import Consultor, consultar
from tests.fakes import RepositorioFake, hist_agricola, hist_vegetacao, oc


def _repo():
    return RepositorioFake({}, [], {"agri": hist_agricola(), "veg": hist_vegetacao()})


def test_consultas_derivadas_do_historico(tmp_path):
    log = LogExecucao("teste", "p", pasta=tmp_path)
    c = Consultor(_repo(), [oc("agri", -10, -47, 0.5, dist_ti=None), oc("veg", -10, -47, 0.5, dist_ti=2.0)], log)
    dn = c.padrao_dia_noite("agri")
    assert dn["frac_noite"] == 0.0 and dn["n_dia"] == 8
    per = c.persistencia("agri")
    assert per["dias_com_foco"] == 4 and per["intermitente"] and per["maior_sequencia_dias"] == 1
    assert c.padrao_frp("agri")["frp_por_foco_hist"] == 5.0
    assert c.padrao_dia_noite("veg")["frac_noite"] > 0.3
    assert c.proximidade_ti_uc("veg") == {"dist_ti_uc_km": 2.0}
    assert len(c.consultas) == 5
    linhas = log.caminho.read_text().strip().splitlines()
    assert len(linhas) == 5 and all('"evento": "consulta"' in l for l in linhas)


def test_formatos_alternativos_de_dia_noite():
    repo = RepositorioFake({}, [], {"x": [{"n_focos": 4, "frp": 1, "n_noite": 1},
                                          {"n_focos": 2, "frp": 1, "dia_noite": "N"},
                                          {"n_focos": 2, "frp": 1, "dia_noite": 0.5}]})
    dn = Consultor(repo, []).padrao_dia_noite("x")
    assert dn["n_noite"] == 4 and dn["n_dia"] == 4


def test_wrapper_consultar_so_aceita_consultas_parametrizadas():
    assert consultar(_repo(), "historico_celula", "agri", dias=3) == hist_agricola()[-3:]
    with pytest.raises(ValueError):
        consultar(_repo(), "DROP TABLE focos", "agri")
