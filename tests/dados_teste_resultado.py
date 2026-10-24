"""DADO DE TESTE construído à mão. NÃO é saída do sistema nem dado real do FIRMS.

Serve só para testar a renderização (app/output) e a CLI enquanto app.agents.grafo não existe.
Coordenadas aproximadas do Tocantins; números inventados para o teste.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.models import (Base, Designacao, Memoria, Ocorrencia, ParecerAnalista, Plano, RegiaoCfg, Recurso,
                             ResultadoPeriodo, VeredictoCritico, Violacao)

T0 = datetime(2026, 10, 24, 3, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 10, 24, 17, 0, tzinfo=timezone.utc)


def regiao_teste(idioma: str = "pt-BR") -> RegiaoCfg:
    return RegiaoCfg(nome="tocantins", bbox=(-11.5, -9.0, -48.5, -45.5), idioma=idioma)


def _oc(oid, lat, lon, prio, n, pop, loc=None, status="nova"):
    return Ocorrencia(id=oid, lat=lat, lon=lon, n_focos=n, frp_soma=n * 10.0, frp_max=n * 4.0,
                      primeiro=T0, ultimo=T1, status=status, pop_raio=pop, prioridade=prio,
                      componentes={"exposicao": prio / 2, "intensidade": prio / 2},
                      localidades=[loc] if loc else [])


def resultado_teste() -> ResultadoPeriodo:
    ocorrencias = [
        _oc("cel_-102_-465", -10.2, -46.5, 0.91, 9, 2300, {"nome": "Mateiros", "pop": 2300, "dist_km": 8.4}, "crescendo"),
        _oc("cel_-105_-474", -10.5, -47.4, 0.74, 5, 1200, {"nome": "Ponte Alta do Tocantins", "pop": 7000, "dist_km": 13.1}),
        _oc("cel_-98_-470", -9.8, -47.0, 0.55, 3, 0),
        _oc("cel_-110_-462", -11.0, -46.2, 0.42, 4, 900, {"nome": "Dianópolis <teste>", "pop": 19000, "dist_km": 14.9}),
        _oc("cel_-95_-476", -9.5, -47.6, 0.20, 1, 0, status="diminuindo"),
    ]
    bases = [
        Base(id="osm_teste_1", nome="Base Teste Palmas", lat=-10.18, lon=-48.33),
        Base(id="osm_teste_2", nome="Base Teste Mateiros", lat=-10.55, lon=-46.42),
    ]
    recursos = [
        Recurso(id="r-terra-1", base_id="osm_teste_2", tipo="terrestre"),
        Recurso(id="r-aereo-1", base_id="osm_teste_1", tipo="aereo"),
        Recurso(id="r-terra-2", base_id="osm_teste_1", tipo="terrestre"),
    ]
    plano = Plano(
        periodo="2026-10-24", regiao="tocantins", rodada=2, reserva=["r-terra-2"],
        nao_atendidas=["cel_-98_-470", "cel_-110_-462", "cel_-95_-476"],
        resumo="Plano de teste: duas ocorrências com população exposta atendidas | uma escalada.",
        designacoes=[
            Designacao(recurso_id="r-terra-1", ocorrencia_id="cel_-102_-465", ordem=1, eta_h=1.2,
                       justificativa="Mateiros a 8,4 km, ocorrência crescendo.",
                       evidencias=["pop:Mateiros:2300", "eta:1.2h"]),
            Designacao(recurso_id="r-aereo-1", ocorrencia_id="cel_-105_-474", ordem=2, eta_h=0.6,
                       justificativa="Única aeronave; Ponte Alta a 13,1 km.", evidencias=[]),
        ],
    )
    pareceres = [ParecerAnalista(ocorrencia_id="cel_-98_-470", pergunta="Queima agrícola recorrente?",
                                 conclusao="queima_agricola_provavel", confianca="media",
                                 evidencias=["hist7d:5_de_7_dias"], consultas=["historico_celula(7)"])]
    memorias = [Memoria(id="m2", regiao="tocantins", texto="estrada para Mateiros liberada", tipo="nota",
                        fonte="coordenador:teste", confianca=1.0, supersedes="m1", criada_em=T1)]
    historico = [
        {"rodada": 1, "plano": plano.model_copy(update={"rodada": 1}),
         "violacoes": [Violacao(regra="eta_acima_limite", recurso_id="r-terra-2", ocorrencia_id="cel_-110_-462")],
         "veredicto": VeredictoCritico(decisao="rejeita", motivos=["ETA acima do limite"])},
        {"rodada": 2, "plano": plano, "violacoes": [],
         "veredicto": {"decisao": "escala", "motivos": ["Dianópolis exposta sem recurso viável"]}},
    ]
    return ResultadoPeriodo(
        plano=plano, ocorrencias=ocorrencias, bases=bases, recursos=recursos,
        escalacoes=[{"ocorrencia_id": "cel_-110_-462", "motivo": "população exposta sem recurso viável"}],
        pareceres=pareceres, memorias_usadas=memorias, historico=historico, rodadas=2,
        log_path="/tmp/fococerto-teste/logs/exec-teste.jsonl",
    )
