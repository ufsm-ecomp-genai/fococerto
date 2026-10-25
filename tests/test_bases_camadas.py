"""Bases em camadas com procedência (docs/CONTRATOS.md, seção 16). Dono: dados-zetaris."""
from __future__ import annotations

import csv
import json

from app.core.config import RAIZ, cenario as ler_cenario
from app.core.models import Base, Cenario, Recurso
from app.data.bases import (RAIO_FUSAO_KM, bases_em_camadas, bases_estimadas, fundir_bases,
                            fundir_bases_com_apelidos, fundir_com_apelidos, ler_bases_oficiais, precisa_estimadas)
from app.data.repositorio import RepositorioCache
from app.output import render_markdown
from app.output.mapa import render_mapa
from tests.dados_teste_resultado import regiao_teste, resultado_teste

BBOX_TO = (-13.0, -8.0, -49.5, -45.5)


def _b(id, lat, lon, conf="osm", nome=None, fonte="f"):
    return Base(id=id, nome=nome or id, lat=lat, lon=lon, fonte=fonte, confianca=conf)


# ----------------------------------------------------------------------------- fusão
def test_fusao_por_distancia_mantem_maior_confianca_e_registra_fundidas():
    of = _b("of_a", -10.0, -48.0, "oficial", fonte="Diário Oficial 2024")
    osm = _b("osm_a", -10.01, -48.01, "osm", fonte="OpenStreetMap node/1")   # ~1,5 km
    longe = _b("osm_b", -10.2, -48.0, "osm")                                 # ~22 km
    bases, apelidos = fundir_com_apelidos([osm, longe], [of])  # ordem de entrada não importa: vale a confiança
    assert [b.id for b in bases] == ["of_a", "osm_b"]
    assert bases[0].confianca == "oficial" and bases[0].lat == -10.0
    assert "Diário Oficial 2024" in bases[0].fonte and "fundida com osm_a" in bases[0].fonte
    assert "OpenStreetMap node/1" in bases[0].fonte
    assert apelidos == {"osm_a": "of_a"}


def test_fusao_respeita_o_raio():
    a = _b("a", -10.0, -48.0, "oficial")
    perto = _b("b", -10.0 + (RAIO_FUSAO_KM - 0.5) / 111.2, -48.0)
    fora = _b("c", -10.0 + (RAIO_FUSAO_KM + 0.5) / 111.2, -48.0)
    assert [b.id for b in fundir_com_apelidos([a, perto])[0]] == ["a"]
    assert [b.id for b in fundir_com_apelidos([a, fora])[0]] == ["a", "c"]


def test_mesmo_id_funde_mesmo_longe():
    bases, apelidos = fundir_com_apelidos([_b("x", -10, -48, "osm")], [_b("x", -11, -49, "oficial")])
    assert len(bases) == 1 and bases[0].confianca == "oficial" and bases[0].lat == -11 and apelidos == {}


def test_fundir_bases_declarada_vence_e_vira_declarada():
    repo = [_b("cbmto_x", -10.0, -48.0, "oficial"), _b("osm_y", -12.0, -47.0, "osm")]
    decl = [Base(id="sim_x", nome="X (simulada)", lat=-10.005, lon=-48.0, simulada=True)]  # confianca default "osm"
    bases = fundir_bases(repo, decl)
    assert [b.id for b in bases] == ["sim_x", "osm_y"]
    assert bases[0].confianca == "declarada" and "fundida com cbmto_x" in bases[0].fonte
    _, apelidos = fundir_bases_com_apelidos(repo, decl)
    assert apelidos == {"cbmto_x": "sim_x"}


def test_estimadas_so_quando_nada_cobre_a_regiao():
    locs = [{"geonameid": "1", "nome": "Cidade Grande", "lat": -10.0, "lon": -48.0, "pop": 50000},
            {"geonameid": "2", "nome": "Vila", "lat": -11.0, "lon": -47.0, "pop": 1500}]
    est = bases_estimadas(locs, BBOX_TO, pop_min=20000)
    assert [(b.id, b.confianca) for b in est] == [("est_1", "estimada")]
    assert "NÃO verificada" in est[0].fonte
    fora = [_b("osm_fora", -20.0, -40.0)]
    assert precisa_estimadas("auto", fora, BBOX_TO) is True
    assert precisa_estimadas("auto", fora + [_b("osm_dentro", -10.5, -48.0)], BBOX_TO) is False
    assert precisa_estimadas("sempre", [_b("osm_dentro", -10.5, -48.0)], BBOX_TO) is True
    assert precisa_estimadas("nunca", [], BBOX_TO) is False
    # região sem lista oficial e sem OSM dentro da bbox: entram as estimadas
    bases = bases_em_camadas("regiao_inexistente", BBOX_TO, fora, locs, oficiais=[])
    assert {b.confianca for b in bases} == {"osm", "estimada"}
    # com lista oficial cobrindo: não entram
    bases = bases_em_camadas("regiao_inexistente", BBOX_TO, fora, locs, oficiais=[_b("of", -9.0, -48.0, "oficial")])
    assert "estimada" not in {b.confianca for b in bases}


# ----------------------------------------------------------------------------- dados reais do Tocantins
def test_csv_oficial_tocantins_tem_fonte_e_data():
    caminho = RAIZ / "config" / "regioes" / "tocantins_bases_oficiais.csv"
    linhas = list(csv.DictReader(caminho.open(encoding="utf-8")))
    assert len(linhas) == 12
    for l in linhas:
        assert l["fonte"].startswith("https://") and l["data_fonte"].isdigit() and l["orgao"] and l["coordenada"]
        assert -13.0 <= float(l["lat"]) <= -7.5 and -49.5 <= float(l["lon"]) <= -45.5
    assert "mateiros" not in caminho.read_text(encoding="utf-8").lower()
    assert all(b.confianca == "oficial" for b in ler_bases_oficiais("tocantins"))


def test_repositorio_cache_funde_palmas_oficial_com_osm():
    bases = RepositorioCache().bases("tocantins")
    por_id = {b.id: b for b in bases}
    assert len(bases) == len(por_id)  # sem duplicata
    palmas = por_id["osm_n5067657890"]
    assert palmas.confianca == "oficial" and palmas.nome == "CBMTO 1º BBM Palmas"
    assert "fundida com osm_n5067657890" in palmas.fonte and "OpenStreetMap node/5067657890" in palmas.fonte
    assert por_id["osm_w1022455273"].confianca == "osm"  # SCI do aeroporto de Palmas: ~10 km, outra unidade
    assert {"prevfogo_sao_felix", "icmbio_rio_conceicao", "cbmto_colinas"} <= set(por_id)
    assert not any(b.confianca == "estimada" for b in bases)  # a região já é coberta
    assert not any(b.id.startswith("sim_") for b in bases)


def test_cenarios_usam_so_bases_com_fonte():
    bases = {b.id: b for b in RepositorioCache().bases("tocantins")}
    tamanhos = {}
    for nome in ("escasso", "medio", "folgado"):
        c = ler_cenario(RAIZ / "cenarios" / f"tocantins-{nome}.yaml")
        tamanhos[nome] = (len(c.recursos), c.reserva)
        assert c.simulado is True and c.bases == []
        for r in c.recursos:
            assert r.base_id in bases and bases[r.base_id].confianca in ("oficial", "osm")
            assert "mateiros" not in r.id and not r.base_id.startswith("sim_")
    assert tamanhos == {"escasso": (6, 0), "medio": (10, 1), "folgado": (16, 2)}


# ----------------------------------------------------------------------------- saída
def _resultado_com_procedencias():
    r = resultado_teste()
    bases = [r.bases[0].model_copy(update={"confianca": "oficial", "fonte": "CBMTO — https://exemplo.org/a (2023)"}),
             r.bases[1]]
    return r.model_copy(update={"bases": bases})


def test_markdown_mostra_procedencia_e_aviso_de_bases_reais():
    cen = Cenario(regiao="tocantins", periodo="2026-10-24", simulado=True,
                  recursos=[Recurso(id="r-terra-1", base_id="osm_teste_2", tipo="terrestre")])
    md = render_markdown(_resultado_com_procedencias(), regiao_teste(), cen)
    assert "Bases: localização real com fonte; quantidade de equipes simulada (cenário)." in md
    assert "(aereo, Base Teste Palmas, base oficial)" in md
    assert "## Bases e procedência" in md and "https://exemplo.org/a" in md
    assert "**oficial**: lista oficial da região" in md and "**OSM**: OpenStreetMap" in md


def test_markdown_avisa_base_declarada():
    r = _resultado_com_procedencias()
    decl = Base(id="osm_teste_2", nome="Base Teste Mateiros", lat=-10.55, lon=-46.42, simulada=True)
    cen = Cenario(regiao="tocantins", periodo="2026-10-24", simulado=True, bases=[decl],
                  recursos=[Recurso(id="r-terra-1", base_id="osm_teste_2", tipo="terrestre")])
    md = render_markdown(r, regiao_teste(), cen)
    assert "1 declarada(s) ou estimada(s) sem verificação (osm_teste_2)" in md
    assert "base declarada" in md


def test_mapa_estilo_e_legenda_por_procedencia():
    cen = Cenario(regiao="tocantins", periodo="2026-10-24", simulado=True,
                  recursos=[Recurso(id="r-terra-1", base_id="osm_teste_2", tipo="terrestre")])
    h = render_mapa(_resultado_com_procedencias(), regiao_teste(), cen)
    assert "server.arcgisonline.com" in h  # fundo Esri mantido
    i = h.index('<script id="dados" type="application/json">') + len('<script id="dados" type="application/json">')
    d = json.loads(h[i:h.index("</script>", i)])
    assert {b["id"]: b["procedencia"] for b in d["bases"]} == {"osm_teste_1": "oficial", "osm_teste_2": "osm"}
    assert d["procedencias_presentes"] == ["oficial", "osm"]
    assert d["estilo_base"]["oficial"]["cor"] != d["estilo_base"]["osm"]["cor"]
    assert d["aviso_bases"].startswith("Bases: localização real com fonte")
    assert "D.procedencias_presentes.map" in h  # legenda por procedência


def test_link_do_log_relativo_a_raiz_do_repo():
    from app.output.render import _link_log
    pasta = RAIZ / "out" / "tocantins" / "2026-10-23"
    assert _link_log("logs/x.jsonl", pasta) == "../../../logs/x.jsonl"
    assert _link_log(str(RAIZ / "logs" / "x.jsonl"), pasta) == "../../../logs/x.jsonl"
    assert _link_log("output_examples/a/trace.jsonl", RAIZ / "output_examples" / "a") == "trace.jsonl"
    assert _link_log("", pasta) == "" and _link_log("logs/x.jsonl", None) == "logs/x.jsonl"
