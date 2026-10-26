"""Guarda-corpo de escalação (app/agents/grafo.py, escalar_expostas_sem_recurso): o motivo diz quais recursos
chegariam a tempo à ocorrência exposta e onde cada um ficou no plano final (designado a outra ocorrência, em
reserva ou sem designação), ou que nenhum chega dentro do ETA máximo. pt-BR e en. A forma do dict não muda.
Dados de teste SIMULADOS (fakes)."""
from __future__ import annotations

import re

import pytest

from app.agents.grafo import escalar_expostas_sem_recurso
from app.core.mensagens import msg
from app.core.models import Base, Designacao, Plano
from app.tools.geo import eta_recurso
from tests.fakes import oc, rec, regiao_teste

CFG = regiao_teste()
BN = Base(id="bn", nome="Base Norte", lat=-10.0, lon=-47.0)
LONGE = Base(id="longe", nome="Base Longe", lat=-5.0, lon=-40.0)
X = oc("cel_-101_-470", -10.1, -47.0, 0.9, pop=29357)
Y = oc("cel_-102_-471", -10.2, -47.1, 0.5, pop=2463,
       localidades=[{"nome": "Santa Tereza do Tocantins", "pop": 2463, "dist_km": 3.0},
                    {"nome": "Outra", "pop": 100, "dist_km": 9.0}])
A1, T1, T9 = rec("a1", "bn", "aereo"), rec("t1", "bn"), rec("t9", "longe")


def _plano(designacoes=(), reserva=()) -> Plano:
    return Plano(periodo="2026-10-23", regiao="teste", designacoes=list(designacoes), reserva=list(reserva))


def _d(rid: str, o) -> Designacao:
    return Designacao(recurso_id=rid, ocorrencia_id=o.id, ordem=1, eta_h=1.0, justificativa="x")


def _escalar(plano, recursos, idioma):
    todas, novas = escalar_expostas_sem_recurso(plano, [X, Y], [], idioma, recursos=recursos, bases=[BN, LONGE],
                                                regiao=CFG)
    assert todas == novas and [e["ocorrencia_id"] for e in novas] == [X.id]
    e = novas[0]
    assert set(e) == {"ocorrencia_id", "motivo", "sugestao", "alcance"}  # campos antigos + alcance (CONTRATOS §22)
    assert e["sugestao"] == msg("sugestao_apoio_externo", idioma)
    return e["motivo"]


@pytest.mark.parametrize("idioma,esperado", [
    ("en", "Mandatory: 29357 people exposed and no crew/aircraft assigned in the final plan. Could reach it within "
           "the 6 h limit: a1 ({ea:.1f} h; assigned to the incident near Santa Tereza do Tocantins (2463 people)), "
           "t1 ({et:.1f} h; in reserve). Suggested action: request external support."),
    ("pt-BR", "Obrigatória: 29357 hab. expostos e nenhum recurso designado no plano final. Chegariam dentro do "
              "limite de 6 h: a1 ({ea:.1f} h; designado à ocorrência perto de Santa Tereza do Tocantins (2463 hab.)), "
              "t1 ({et:.1f} h; em reserva). Sugestão: solicitar apoio externo."),
])
def test_viavel_usado_em_outra_e_em_reserva(idioma, esperado):
    motivo = _escalar(_plano([_d("a1", Y)], reserva=["t1"]), [A1, T1, T9], idioma)
    ea, et = eta_recurso(A1, BN, X, CFG), eta_recurso(T1, BN, X, CFG)
    assert ea < et <= CFG.eta_max_h
    assert motivo == esperado.format(ea=ea, et=et)
    assert "t9" not in motivo                        # base longe: fora do ETA máximo, não é listado
    # sem id de outra célula no texto (o avaliador conta como escalada toda célula citada no motivo)
    assert re.findall(r"cel_-?\d+_-?\d+", motivo) == []


@pytest.mark.parametrize("idioma,trecho", [("en", "t1 ({et:.1f} h; unassigned)"),
                                           ("pt-BR", "t1 ({et:.1f} h; sem designação)")])
def test_viavel_sem_designacao(idioma, trecho):
    motivo = _escalar(_plano([_d("a1", Y)]), [A1, T1], idioma)
    assert trecho.format(et=eta_recurso(T1, BN, X, CFG)) in motivo


@pytest.mark.parametrize("idioma,esperado", [
    ("en", "Mandatory: 29357 people exposed and no crew/aircraft assigned in the final plan. No available "
           "crew/aircraft can reach it within the 6 h limit. Suggested action: request external support."),
    ("pt-BR", "Obrigatória: 29357 hab. expostos e nenhum recurso designado no plano final. Nenhum recurso "
              "disponível chega dentro do limite de 6 h. Sugestão: solicitar apoio externo."),
])
def test_nenhum_viavel(idioma, esperado):
    indisponivel = rec("a2", "bn", "aereo", disponivel=False)       # perto, mas indisponível: não conta
    assert _escalar(_plano([_d("t9", Y)]), [T9, indisponivel], idioma) == esperado


def test_sem_dados_de_recursos_mantem_texto_antigo():
    _, novas = escalar_expostas_sem_recurso(_plano(), [X], [], "pt-BR")
    assert novas[0]["motivo"] == msg("esc_guarda_corpo", "pt-BR", pop=29357, sug=msg("sugestao_apoio_externo", "pt-BR"))


def test_alcance_estruturado_e_escalacao_existente():
    """O campo ``alcance`` traz a mesma informação do motivo, estruturada; uma escalação que já existia (ex.: do
    Crítico) ganha o campo sem mudar o motivo."""
    plano = _plano([_d("a1", Y)], reserva=["t1"])
    todas, novas = escalar_expostas_sem_recurso(plano, [X, Y], [], "en", recursos=[A1, T1, T9],
                                                bases=[BN, LONGE], regiao=CFG)
    alc = {a["recurso_id"]: a for a in novas[0]["alcance"]}
    assert set(alc) == {"a1", "t1"}                                    # t9 está longe demais
    assert alc["a1"]["situacao"] == "designado" and alc["a1"]["destinos"] == [
        {"ocorrencia_id": Y.id, "localidade": "Santa Tereza do Tocantins", "pop_raio": 2463}]
    assert alc["t1"]["situacao"] == "reserva" and alc["t1"]["destinos"] == []
    etas = [a["eta_h"] for a in novas[0]["alcance"]]
    assert etas == sorted(etas)

    critico = {"ocorrencia_id": X.id, "motivo": "do Crítico"}
    todas, novas = escalar_expostas_sem_recurso(plano, [X, Y], [critico], "en", recursos=[A1, T1, T9],
                                                bases=[BN, LONGE], regiao=CFG)
    assert novas == [] and todas[0]["motivo"] == "do Crítico" and len(todas[0]["alcance"]) == 2
    assert critico == {"ocorrencia_id": X.id, "motivo": "do Crítico"}   # a entrada não é alterada


def test_sem_dados_de_recurso_nao_tem_alcance():
    _, novas = escalar_expostas_sem_recurso(_plano(), [X, Y], [], "en")
    assert "alcance" not in novas[0]
