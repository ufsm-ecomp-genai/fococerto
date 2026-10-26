"""Ids inventados e coberturas falsas no texto livre do plano (CONTRATOS §20), em pt-BR e en.

Regressão da execução real com Nemotron em inglês (25/10): o Planejador citou ``gurupi-t1`` (base ``cbmto_gurupi``),
que não existe no cenário tocantins-escasso, e o resumo afirmou que ``cel_-117_-491`` estava "covered by gurupi-t1",
quando no plano final ela ficou sem recurso. Ocorrências, recursos e bases daqui são dados SIMULADOS de teste
(fakes), com ids na forma dos reais."""
import json

import pytest

from app.agents import critico, planejador
from app.agents.base import Contexto, reescrever_citacoes
from app.agents.grafo import executar_periodo
from app.core.logging import LogExecucao
from app.core.models import Base, Cenario, Designacao, Plano, VeredictoCritico
from app.tools.citacoes import checar_citacoes, checar_resumo, coberturas_falsas
from tests.fakes import MemoriaFake, RepositorioFake, oc, rec, regiao_teste

PN = Base(id="cbmto_porto_nacional", nome="CBMTO Porto Nacional", lat=-10.70, lon=-48.41)
PAL = Base(id="osm_n5067657890", nome="Quartel Palmas", lat=-10.18, lon=-48.33)
BASES = [PN, PAL]
RECS = [rec("portonac-t1", PN.id), rec("palmas-a1", PAL.id, tipo="aereo"), rec("paraiso-t1", PAL.id)]
OCCS = [oc("cel_-107_-483", -10.7, -48.3, 0.59, pop=53316),
        oc("cel_-117_-491", -11.7, -49.1, 0.70, pop=87545),
        oc("cel_-103_-478", -10.3, -47.8, 0.60, pop=2463)]
# plano final real (recorte): portonac-t1 foi para cel_-107_-483 e cel_-117_-491 ficou sem recurso
DESIG = [("portonac-t1", "cel_-107_-483"), ("palmas-a1", "cel_-103_-478")]


def _cfg(idioma):
    return regiao_teste(idioma=idioma)


def _plano(resumo="", justificativas=None):
    ds = [Designacao(recurso_id=r, ocorrencia_id=o, ordem=i + 1, eta_h=1.0,
                     justificativa=(justificativas or {}).get(r, "ok"), evidencias=[])
          for i, (r, o) in enumerate(DESIG)]
    return Plano(periodo="2026-10-23", regiao="teste", designacoes=ds, resumo=resumo,
                 nao_atendidas=["cel_-117_-491"], reserva=["paraiso-t1"])


def _resumo_vs(resumo, idioma="pt-BR"):
    return [(v.evidencia["campo"], v.evidencia["citado"])
            for v in checar_resumo(_plano(resumo), OCCS, BASES, RECS, idioma)]


def _jus_vs(texto, idioma="pt-BR"):
    vs = checar_citacoes(_plano(justificativas={"palmas-a1": texto}), OCCS, BASES, recursos=RECS,
                         regiao_cfg=_cfg(idioma))
    return [(v.evidencia["campo"], v.evidencia["citado"]) for v in vs if v.evidencia["campo"] == "id_inexistente"]


# ------------------------------------------------------------------ id inexistente na justificativa
@pytest.mark.parametrize("idioma,texto", [
    ("pt-BR", "Troca obrigatória: gurupi-t1 (base cbmto_gurupi) atenderia cel_-117_-491 em 0,31 h."),
    ("en", "Mandatory swap: gurupi-t1 (base cbmto_gurupi) could serve cel_-117_-491 in 0.31 h."),
])
def test_id_inexistente_na_justificativa(idioma, texto):
    assert sorted(_jus_vs(texto, idioma)) == [("id_inexistente", "cbmto_gurupi"), ("id_inexistente", "gurupi-t1")]


@pytest.mark.parametrize("idioma,texto", [
    ("pt-BR", "Paraíso-t1 está livre; Palmas-a1 sai do osm_n5067657890 para cel_-103_-478."),
    ("en", "Paraíso-t1 is free; Palmas-a1 leaves osm_n5067657890 for cel_-103_-478."),
])
def test_ids_existentes_na_justificativa_sem_alarme(idioma, texto):
    assert _jus_vs(texto, idioma) == []


def test_celula_inexistente_na_justificativa_e_mensagem_no_idioma():
    vs = checar_citacoes(_plano(justificativas={"palmas-a1": "libera cel_-999_-999"}), OCCS, BASES, recursos=RECS,
                         regiao_cfg=_cfg("en"))
    v = [x for x in vs if x.evidencia["campo"] == "id_inexistente"]
    assert [x.evidencia["citado"] for x in v] == ["cel_-999_-999"] and "does not exist" in v[0].sugestao


def test_ids_extras_contam_como_existentes():
    p = _plano(justificativas={"palmas-a1": "memória sobre cel_-50_-480"})
    assert not [v for v in checar_citacoes(p, OCCS, BASES, recursos=RECS, ids_extras={"cel_-50_-480"})
                if v.evidencia["campo"] == "id_inexistente"]


# ------------------------------------------------------------------ resumo: id inexistente e cobertura falsa
@pytest.mark.parametrize("idioma,resumo", [
    ("pt-BR", "Seis recursos designados; a base sim_gurupi tem reserva."),
    ("en", "Six crews assigned; base sim_gurupi holds the reserve."),
])
def test_id_inexistente_no_resumo(idioma, resumo):
    assert _resumo_vs(resumo, idioma) == [("id_inexistente", "sim_gurupi")]


@pytest.mark.parametrize("idioma,resumo", [
    ("pt-BR", "cel_-117_-491 (87.545 habitantes) atendida por portonac-t1."),
    ("pt-BR", "Trocas: portonac-t1 → cel_-117_-491 (ETA 4,4 h)."),
    ("pt-BR", "cel_-117_-491 coberta pelo recurso paraiso-t1; reserva vazia."),
    ("en", "cel_-117_-491 (87,545 people, covered by portonac-t1)."),
    ("en", "Swaps applied: portonac-t1 assigned to cel_-117_-491."),
    ("en", "Swaps applied: paraiso-t1 to cel_-117_-491 (ETA 4.4 h)."),
])
def test_cobertura_falsa_no_resumo(idioma, resumo):
    vs = _resumo_vs(resumo, idioma)
    assert [c for c, _ in vs] == ["cobertura_falsa"] and vs[0][1].endswith("→cel_-117_-491")


@pytest.mark.parametrize("idioma,resumo", [
    ("pt-BR", "cel_-117_-491 (87.545 habitantes) sem recurso viável: escalada."),
    ("pt-BR", "cel_-117_-491 não é atendida por portonac-t1, que foi para cel_-107_-483."),
    ("pt-BR", "Desvios do baseline: removido portonac-t1→cel_-117_-491, incluído portonac-t1→cel_-107_-483."),
    ("pt-BR", "O Crítico propôs paraiso-t1 → cel_-117_-491, mas o ETA passa do limite."),
    ("en", "cel_-117_-491 (87,545 people) is not covered by any crew and must be escalated."),
    ("en", "cel_-117_-491 left uncovered; portonac-t1 would be assigned to cel_-117_-491 only with a 4.4 h ETA."),
    ("en", "Instead of portonac-t1 → cel_-117_-491, portonac-t1 → cel_-107_-483."),
    ("en", "Done. Replies to the Critic: portonac-t1 assigned to cel_-117_-491 (round 1) -> adotado"),
])
def test_frase_negativa_ou_citacao_do_critico_sem_alarme(idioma, resumo):
    assert _resumo_vs(resumo, idioma) == []


@pytest.mark.parametrize("idioma,resumo", [
    ("pt-BR", "portonac-t1 → cel_-107_-483 (53.316 hab.); cel_-103_-478 atendida por palmas-a1; paraiso-t1 em "
              "reserva; cel_-117_-491 sem recurso."),
    ("en", "portonac-t1 assigned to cel_-107_-483; cel_-103_-478 covered by Palmas-a1; Paraíso-t1 held in reserve; "
           "cel_-117_-491 without a crew."),
])
def test_resumo_correto_sem_alarme(idioma, resumo):
    assert _resumo_vs(resumo, idioma) == []


# ------------------------------------------------------------------ caso real (25/10, Nemotron, en)
RESUMO_REAL = (
    "Six resources assigned to six incidents with exposed population, all ETA ≤ 6 h limit. Mandatory swaps applied: "
    "palmas-a1 to cel_-103_-478 (2463 people, ETA 0.37 h). Six incidents remain without viable resource and must be "
    "escalated: cel_-117_-491 (87545 people, covered by gurupi-t1). Deviations from the baseline: portonac-t1 moved "
    "from cel_-117_-491 to cel_-107_-483 (troca_recurso_local: gurupi-t1 available for cel_-117_-491 at 0.31 h, "
    "portonac-t1 serves 53316 people at 0.49 h)")
JUS_REAL = ("Mandatory swap: gurupi-t1 (base cbmto_gurupi) can serve cel_-117_-491 (pop 87545) in 0.31 h, which is "
            "faster than portonac-t1's 4.4 h.")


@pytest.mark.parametrize("idioma,aviso", [("en", "Summary rewritten by the system"),
                                          ("pt-BR", "Resumo reescrito pelo sistema")])
def test_caso_real_gurupi_t1(idioma, aviso):
    plano = _plano(RESUMO_REAL, {"portonac-t1": JUS_REAL})
    cfg = _cfg(idioma)
    vs = [v for v in checar_citacoes(plano, OCCS, BASES, recursos=RECS, regiao_cfg=cfg)
          if v.regra == "citacao_incorreta"]
    achados = {(v.evidencia["campo"], v.evidencia.get("onde"), str(v.evidencia["citado"])) for v in vs}
    assert ("id_inexistente", None, "gurupi-t1") in achados          # justificativa
    assert ("id_inexistente", None, "cbmto_gurupi") in achados
    assert ("id_inexistente", "resumo", "gurupi-t1") in achados      # resumo
    assert ("cobertura_falsa", "resumo", "gurupi-t1→cel_-117_-491") in achados
    cob = [v for v in vs if v.evidencia["campo"] == "cobertura_falsa"][0]
    assert cob.ocorrencia_id == "cel_-117_-491" and cob.evidencia["real"] == []

    ctx = Contexto(regiao=cfg, periodo="2026-10-23", ocorrencias=OCCS, recursos=RECS, bases=BASES, reserva=0)
    novo = reescrever_citacoes(ctx, plano, vs)
    assert "gurupi" not in novo.resumo and aviso in novo.resumo
    assert "portonac-t1→cel_-107_-483" in novo.resumo and "cel_-117_-491" in novo.resumo
    assert {(d.recurso_id, d.ocorrencia_id) for d in novo.designacoes} == set(DESIG)   # alocação não muda
    assert "gurupi" not in novo.designacoes[0].justificativa
    assert [v for v in checar_citacoes(novo, OCCS, BASES, recursos=RECS, regiao_cfg=cfg)
            if v.regra == "citacao_incorreta"] == []


def test_coberturas_falsas_ignora_motivos_do_critico_na_divergencia():
    t = ("Divergência do Crítico em zona cinzenta após 3 rodada(s) (não bloqueia; plano adotado: x). Motivos do "
         "Crítico: paraiso-t1 → cel_-117_-491 ganharia 1 h || portonac-t1 → cel_-107_-483.")
    assert coberturas_falsas(t, set(DESIG)) == []


# ------------------------------------------------------------------ grafo (offline, com fakes)
P = "2026-10-24"
BN = Base(id="osm_n1", nome="Base Norte", lat=-10.0, lon=-47.0)
G_OCCS = [oc("cel_-101_-470", -10.1, -47.0, 0.8, pop=500), oc("cel_-102_-470", -10.2, -47.0, 0.7, pop=300)]


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "offline")


def _rodar(tmp_path, idioma):
    repo = RepositorioFake({P: G_OCCS}, [BN])
    log = LogExecucao("teste", P, pasta=tmp_path)
    cen = Cenario(regiao="teste", periodo=P, recursos=[rec("norte-t1", "osm_n1")], reserva=0)
    res = executar_periodo(regiao_teste(), cen, repo, MemoriaFake(), log, modo="offline", idioma=idioma)
    return res, [json.loads(l) for l in log.caminho.read_text().splitlines()]


@pytest.mark.parametrize("idioma,falso,aviso", [
    ("pt-BR", "cel_-102_-470 atendida por gurupi-t1.", "Resumo reescrito pelo sistema"),
    ("en", "cel_-102_-470 covered by gurupi-t1.", "Summary rewritten by the system")])
def test_grafo_reescreve_resumo_do_planejador_antes_do_critico(tmp_path, monkeypatch, offline, idioma, falso, aviso):
    original = planejador.decidir_offline
    vistos = []

    def com_resumo_falso(ctx, rodada, *a, **k):
        p = original(ctx, rodada, *a, **k)
        return p.model_copy(update={"resumo": falso})

    def crit(ctx, plano, vs, rodada):
        vistos.append(plano.resumo)
        return VeredictoCritico(decisao="aprova", motivos=["ok"])

    monkeypatch.setattr(planejador, "decidir_offline", com_resumo_falso)
    monkeypatch.setattr(critico, "decidir_offline", crit)
    res, ev = _rodar(tmp_path, idioma)
    assert "gurupi" not in vistos[0] and aviso in vistos[0]                  # o Crítico já recebe o resumo certo
    assert "gurupi" not in res.plano.resumo and "norte-t1→cel_-101_-470" in res.plano.resumo
    cc = [e for e in ev if e["evento"] == "citacao_corrigida"]
    campos = [c for e in cc for c in e["dados"]["correcoes"] if c["campo"] == "resumo"]
    assert {c["motivo"] for c in campos} == {"id_inexistente", "cobertura_falsa"}
    assert campos[0]["resumo_antes"] == falso and aviso in campos[0]["resumo_depois"]


@pytest.mark.parametrize("idioma", ["pt-BR", "en"])
def test_no_final_tira_do_resumo_motivo_do_critico_com_id_inventado(tmp_path, monkeypatch, offline, idioma):
    """Divergência em zona cinzenta: os motivos do Crítico vão para o resumo; o que cita id inventado sai."""
    monkeypatch.setattr(critico, "decidir_offline", lambda *a, **k: VeredictoCritico(
        decisao="rejeita", motivos=["cel_-102_-470 covered by gurupi-t1 in 0.3 h", "trade-off discutível"]))
    res, ev = _rodar(tmp_path, idioma)
    assert res.rodadas == 3
    assert "gurupi" not in res.plano.resumo and "trade-off discutível" in res.plano.resumo
    assert "norte-t1→cel_-101_-470" in res.plano.resumo
    fim = [e for e in ev if e["evento"] == "citacao_corrigida" and e["dados"].get("no_plano_final")]
    assert fim and any(c["campo"] == "resumo" for c in fim[0]["dados"]["correcoes"])
    # o plano publicado é coerente com as designações finais
    assert checar_resumo(res.plano, res.ocorrencias, res.bases, res.recursos) == []
