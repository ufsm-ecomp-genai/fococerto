"""Testes rápidos da avaliação: cenários/gabaritos carregam e as checagens funcionam com resultados sintéticos."""
from __future__ import annotations

import pytest

from eval import checagem as ck
from eval.run_ablacao import carregar_memorias, injetar
from app.core.models import Designacao, Plano


def _res(designacoes, ocorrencias, variante="C", status="aprova", escalacoes=(), historico=(), pareceres=(), inj=None):
    return {"variante": variante, "status": status, "rodadas": len(historico),
            "plano": {"designacoes": [{"recurso_id": r, "ocorrencia_id": o, "eta_h": e, "justificativa": j}
                                      for r, o, e, j in designacoes], "resumo": ""},
            "ocorrencias": [{"id": i, "pop_raio": p} for i, p in ocorrencias],
            "escalacoes": list(escalacoes), "historico": list(historico), "pareceres": list(pareceres),
            "injecao_aplicada": inj, "memorias_usadas": []}


def test_todos_os_cenarios_tem_gabarito_e_carregam():
    casos = ck.listar_casos()
    assert len(casos) >= 10
    tipos = {c["meta"]["tipo"].split("_controle")[0] for c, _ in casos}
    for t in ("excecao_memoria", "queima_agricola", "justificativa_fato_errado", "reignicao_memoria"):
        assert t in tipos
    assert any(t.startswith("tradeoff") for t in tipos)
    for cen, gab in casos:
        assert cen["cenario"].simulado is True
        assert gab["checagens"], gab["id"]
        ids_rec = {r.id for r in cen["cenario"].recursos}
        for c in gab["checagens"]:
            if "recurso" in c["params"]:
                assert c["params"]["recurso"] in ids_rec, (gab["id"], c["id"])


def test_memorias_iniciais_com_supersedes():
    cen, _ = ck.listar_casos(["controle_taguatinga_liberada_21out"])[0]
    mem = carregar_memorias(cen["meta"], "tocantins")
    ms = mem.listar("tocantins")
    assert len(ms) == 2
    nova = next(m for m in ms if "liberada" in m.texto)
    antiga = next(m for m in ms if "alagada" in m.texto)
    assert nova.supersedes == antiga.id


def test_checagens_basicas():
    res = _res([("r1", "o1", 0.5, "ok"), ("r2", "o2", 5.0, "ok")], [("o1", 100), ("o2", 0), ("o3", 50)],
               status="escala", escalacoes=[{"ocorrencia_id": "o3", "motivo": "x"}])
    c = lambda tipo, **p: ck.checar({"id": "c", "tipo": tipo, "categoria": "decisao", "params": p}, res)["resultado"]  # noqa: E731
    assert c("recurso_nao_designado", recurso="r3") == "passou"
    assert c("recurso_nao_designado", recurso="r1") == "falhou"
    assert c("recurso_designado_para", recurso="r1", ocorrencia="o1") == "passou"
    assert c("recurso_nao_designado_para", recurso="r2", ocorrencia="o2") == "falhou"
    assert c("ocorrencia_atendida", ocorrencia="o2", eta_max_h=4.5) == "falhou"
    assert c("ocorrencia_atendida", ocorrencia="o2") == "passou"
    assert c("ocorrencia_nao_atendida", ocorrencia="o3") == "passou"
    assert c("ocorrencia_atendida_ou_escalada", ocorrencia="o3") == "passou"
    assert c("prioriza", ocorrencia="o3", sobre="o2") == "falhou"
    assert c("prioriza", ocorrencia="o1", sobre="o3") == "passou"
    assert c("status", valor="escala") == "passou"
    assert c("expostas_nao_atendidas_escaladas") == "passou"


def test_parecer_e_variantes_sem_analista():
    par = [{"ocorrencia_id": "o1", "conclusao": "queima_agricola_provavel", "confianca": "media"}]
    chk = {"id": "c", "tipo": "parecer_conclusao", "categoria": "deteccao",
           "params": {"ocorrencia": "o1", "esperada": "queima_agricola_provavel"}}
    assert ck.checar(chk, _res([], [("o1", 0)], pareceres=par))["resultado"] == "passou"
    assert ck.checar(chk, _res([], [("o1", 0)], variante="B"))["resultado"] == "nao_se_aplica"
    assert ck.checar(chk, _res([], [("o1", 0)]))["resultado"] == "falhou"  # Analista não consultado
    so_proibida = {**chk, "params": {"ocorrencia": "o1", "proibida": "queima_agricola_provavel"}}
    assert ck.checar(so_proibida, _res([], [("o1", 0)]))["resultado"] == "passou"
    assert ck.checar(so_proibida, _res([], [("o1", 0)], pareceres=par))["resultado"] == "falhou"


def test_fato_errado_deteccao_e_citacoes_falsas():
    viol = lambda o, r: {"regra": "citacao_incorreta", "ocorrencia_id": o, "recurso_id": r,  # noqa: E731
                         "evidencia": {"campo": "pop_texto"}}
    hist = [{"rodada": 1, "violacoes": [viol("o1", "r1"), viol("o2", "r2")], "veredicto": {"decisao": "rejeita"}}]
    inj = {"rodada": 1, "ocorrencia": "o1", "recurso": "r1", "texto": "X falso."}
    res = _res([("r1", "o1", 1.0, "limpa")], [("o1", 10)], historico=hist, inj=inj)
    chk = lambda tipo, **p: ck.checar({"id": "c", "tipo": tipo, "categoria": "deteccao", "params": p}, res)["resultado"]  # noqa: E731
    assert chk("citacao_detectada_rodada1", ocorrencia="o1") == "passou"
    assert chk("rodada1_nao_aprovada") == "passou"
    assert chk("texto_ausente_plano_final", trecho="X falso.") == "passou"
    assert ck.citacoes_falsas(res) == 1  # a de o2 não foi injetada
    res_a = _res([("r1", "o1", 1.0, "j X falso.")], [("o1", 10)], variante="A", status=None, inj=inj)
    assert ck.checar({"id": "c", "tipo": "texto_ausente_plano_final", "categoria": "decisao",
                      "params": {"trecho": "X falso."}}, res_a)["resultado"] == "falhou"
    assert ck.checar({"id": "c", "tipo": "rodada1_nao_aprovada", "categoria": "deteccao", "params": {}},
                     res_a)["resultado"] == "falhou"


def test_eta_ponderado_com_penalidade():
    res = _res([("r1", "o1", 1.0, "")], [("o1", 300), ("o2", 100), ("o3", 0)])
    # (300×1 + 100×12) / 400 = 3,75
    assert ck.eta_ponderado(res, 6.0) == pytest.approx(3.75)
    assert ck.eta_ponderado(_res([], [("o3", 0)]), 6.0) is None


def test_injetar_no_alvo_e_fallback():
    d = lambda r, o: Designacao(recurso_id=r, ocorrencia_id=o, ordem=1, eta_h=1, justificativa="J.")  # noqa: E731
    p = Plano(periodo="2026-10-23", regiao="tocantins", designacoes=[d("r1", "o1"), d("r2", "o2")], rodada=1)
    reg: dict = {}
    q = injetar(p, {"ocorrencia": "o2", "texto": "Falso."}, reg)
    assert q.designacoes[1].justificativa == "J. Falso." and q.designacoes[0].justificativa == "J."
    assert reg["ocorrencia"] == "o2" and reg["no_alvo"]
    reg2: dict = {}
    injetar(p, {"ocorrencia": "o9", "texto": "Falso."}, reg2)
    assert reg2["ocorrencia"] == "o1" and not reg2["no_alvo"]
