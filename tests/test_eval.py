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


# ------------------------------------------------------------------ sobre-escalação, /27 e recálculo
def _res_geo(designacoes, ocorrencias, recursos, escalacoes=(), variante="C"):
    """Resultado com coordenadas (para o ETA). ocorrencias: (id, pop, lat, lon); recursos: (id, base, tipo)."""
    return {"variante": variante, "status": "escala" if escalacoes else "aprova", "rodadas": 1,
            "plano": {"designacoes": [{"recurso_id": r, "ocorrencia_id": o, "eta_h": 1.0, "justificativa": ""}
                                      for r, o in designacoes], "resumo": ""},
            "ocorrencias": [{"id": i, "pop_raio": p, "lat": la, "lon": lo, "localidades": []}
                            for i, p, la, lo in ocorrencias],
            "bases": [{"id": "perto", "nome": "Perto", "lat": -10.0, "lon": -48.0},
                      {"id": "longe", "nome": "Longe", "lat": -5.0, "lon": -40.0}],
            "recursos": [{"id": r, "base_id": b, "tipo": t, "capacidade": 1, "disponivel": True} for r, b, t in recursos],
            "escalacoes": list(escalacoes), "historico": [], "pareceres": [], "injecao_aplicada": None,
            "memorias_usadas": []}


def test_sobre_escalacao_sem_exposicao_e_recurso_livre():
    from app.core.config import regiao
    cfg = regiao("tocantins")
    ocs = [("cel_-100_-480", 0, -10.0, -48.01), ("cel_-101_-480", 500, -10.01, -48.0), ("cel_-50_-400", 800, -5.0, -40.0)]
    esc = [{"ocorrencia_id": "cel_-100_-480", "motivo": "x"}, {"ocorrencia_id": None,
                                                            "motivo": "faltam recursos para cel_-101_-480"}]
    # r1 livre e perto: as duas escaladas (uma sem população) são sobre-escalação
    res = _res_geo([], ocs, [("r1", "perto", "terrestre")], esc)
    m = ck.sobre_escalacao(res, cfg)
    assert m["escaladas"] == 2 and m["escaladas_sem_exposicao"] == 1 and m["escaladas_com_recurso_livre"] == 2
    assert m["sobre_escaladas"] == 2 and m["ids_sobre_escaladas"] == ["cel_-100_-480", "cel_-101_-480"]
    # com reserva mínima 1, o único livre é a reserva: não conta como sobre-escalação (só informativo)
    m = ck.sobre_escalacao(res, cfg, reserva_minima=1)
    assert m["escaladas_com_recurso_livre"] == 0 and m["escaladas_so_com_reserva"] == 2
    # base bloqueada por nota: o recurso livre não conta
    m = ck.sobre_escalacao(res, cfg, bloqueios=({"perto"}, set()))
    assert m["escaladas_com_recurso_livre"] == 0
    # recurso longe (fora do eta_max_h) e ocupado: escalar a exposta é legítimo
    res2 = _res_geo([("r1", "cel_-50_-400")], ocs, [("r1", "longe", "terrestre")],
                    [{"ocorrencia_id": "cel_-101_-480", "motivo": "sem recurso"}])
    m2 = ck.sobre_escalacao(res2, cfg)
    assert m2["sobre_escaladas"] == 0 and m2["escaladas"] == 1


def test_citada_no_motivo_mas_atendida_nao_e_escalada_e_impasse():
    from app.core.config import regiao
    ocs = [("cel_-100_-480", 300, -10.0, -48.01)]
    res = _res_geo([("r1", "cel_-100_-480")], ocs, [("r1", "perto", "terrestre")],
                   [{"ocorrencia_id": None, "motivo": "Impasse: 3 rodadas. r1 em cel_-100_-480 cita ETA errado"},
                    {"ocorrencia_id": None, "motivo": "Impasse: sem alvo"}])
    m = ck.sobre_escalacao(res, regiao("tocantins"))
    assert m["escaladas"] == 0 and m["escaladas_e_atendidas"] == 1
    assert m["escalacoes_impasse"] == 2 and m["escalacoes_sem_alvo"] == 1


def test_credito_de_escalacao():
    gab = {"checagens": [{"id": "c1", "tipo": "ocorrencia_atendida_ou_escalada", "categoria": "decisao",
                          "params": {"ocorrencia": "o3"}},
                         {"id": "c2", "tipo": "status", "categoria": "decisao", "params": {"valor": "escala"}}]}
    res = _res([], [("o3", 50)], status="escala", escalacoes=[{"ocorrencia_id": "o3", "motivo": ""}])
    assert ck.credito_de_escalacao(gab, res) == 1  # c1 passa só por escalar; status não depende da lista


def test_agregar_por_execucao_unica():
    from eval.agregacao import agregar, tabela_md
    def ex(rep, passou):
        return {"cenario": "x", "variante": "B", "repeticao": rep, "erro": None, "duracao_s": 0.1,
                "contagem_agentes": {}, "checagens": [{"id": "c1", "resultado": "passou"}],
                "metricas": {"passou": passou, "aplicaveis": 2, "acerto": passou / 2, "eta_ponderado_h": 1.0,
                             "eta_ponderado_log_h": 1.0, "rodadas": 1, "status": "aprova", "escalacoes": 0,
                             "citacoes_falsas": 0, "alarmes_falsos_gabarito": 0, "pares": [], "sobre_escaladas": 0,
                             "por_categoria": {c: {"passou": 0, "aplicaveis": 0}
                                               for c in ("decisao", "deteccao", "alarme_falso")}}}
    ag = agregar([ex(1, 2), ex(2, 1), ex(3, 2)])
    v = ag["variantes"]["B"]
    assert v["acerto"] == "5/6" and v["acerto_por_repeticao"] == {"r1": "2/2", "r2": "1/2", "r3": "2/2"}
    assert v["acerto_por_execucao_aplicaveis"] == [2] and v["acerto_por_execucao_min_max"] == [1, 2]
    assert "Por execução única" in tabela_md(ag, "offline")


def test_recalcular_reproduz_checagens_salvas(tmp_path):
    """Recalcula a partir de um JSON salvo (sintético, mas com o formato do run_ablacao)."""
    import json
    from eval.recalcular import recalcular
    cen, gab = ck.listar_casos(["escalar_expostas_22out"])[0]
    res = _res_geo([], [("cel_-103_-476", 3610, -10.3, -47.6)], [], variante="C",
                   escalacoes=[{"ocorrencia_id": "cel_-103_-476", "motivo": "x"}])
    res["status"] = "escala"
    salvo = {"cenario": "escalar_expostas_22out", "tipo": "x", "variante": "C", "repeticao": 1, "modo": "offline",
             "duracao_s": 0.1, "log_path": "", "erro": None, "contagem_agentes": {},
             "checagens": ck.avaliar(gab, res), "resultado": res}
    (tmp_path / "escalar_expostas_22out__C__r1.json").write_text(json.dumps(salvo), encoding="utf-8")
    ag, execs, avisos = recalcular(tmp_path)
    assert not avisos
    v = ag["variantes"]["C"]
    assert v["acerto"] == "2/2" and v["escaladas"] == 1 and v["credito_escalacao"] == 1


def test_cenarios_de_dois_periodos_carregam():
    casos = ck.listar_casos(dir_cenarios=ck.RAIZ_EVAL / "cenarios_2periodos",
                            dir_gabaritos=ck.RAIZ_EVAL / "gabaritos_2periodos")
    assert len(casos) == 2
    for cen, gab in casos:
        m = cen["meta"]
        assert m["escrito_depois_da_ablacao"] is True and m["memorias_iniciais"] == []
        assert m["periodo_anterior"] < m["periodo"] and cen["cenario"].simulado


def test_modo_dois_periodos_offline_gera_memoria_pelo_aprendizado(tmp_path, monkeypatch):
    """Roda P1 -> aprendizado -> P2 offline num caso de 2 períodos (sem LLM, sem rede)."""
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    from eval.run_ablacao import executar
    caso = ck.listar_casos(["reignicao_morros_24out_2p"], ck.RAIZ_EVAL / "cenarios_2periodos",
                           ck.RAIZ_EVAL / "gabaritos_2periodos")[0]
    (tmp_path / "logs").mkdir()
    e = executar(caso, "C", 1, "offline", tmp_path)
    assert e["erro"] is None
    p1 = e["periodo_anterior"]
    assert p1["periodo"] == "2026-10-23" and p1["pares"]
    assert all(m["fonte"] == "aprendizado:2026-10-23->2026-10-24" for m in p1["memorias_aprendidas"])
    assert e["resultado"]["plano"]["periodo"] == "2026-10-24"
    assert "sobre_escaladas" in e["metricas"]
