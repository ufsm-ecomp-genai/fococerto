"""Regressão das correções da revisão do juiz (docs/ESTADO.md, fila itens 1, 2, 6 e 12). Dados SIMULADOS de teste."""
import json
import os

import pytest

from app import cli
from app.agents import critico
from app.agents.base import Contexto
from app.agents.grafo import executar_periodo
from app.core.config import RAIZ
from app.core.logging import LogExecucao
from app.core.models import Base, Cenario, Designacao, Plano, VeredictoCritico
from app.tools.regras import checar_regras
from tests.fakes import MemoriaFake, RepositorioFake, oc, rec, regiao_teste

CFG = regiao_teste()
BN = Base(id="bn", nome="Base Norte", lat=-10.0, lon=-47.0)
BS = Base(id="bs", nome="Base Sul", lat=-10.8, lon=-47.0)
P = "2026-10-24"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.delenv("SAMPLE_MODE", raising=False)


def _rodar(tmp_path, occs, recursos, pasta_log=None, **kw):
    repo = RepositorioFake({P: occs}, [BN, BS])
    log = LogExecucao("teste", P, pasta=pasta_log or tmp_path)
    cen = Cenario(regiao="teste", periodo=P, recursos=recursos, reserva=0)
    return executar_periodo(CFG, cen, repo, MemoriaFake(), log, modo="offline", **kw)


def _plano(*pares):
    return Plano(periodo=P, regiao="teste", designacoes=[
        Designacao(recurso_id=r, ocorrencia_id=o, ordem=i + 1, eta_h=e, justificativa="x")
        for i, (r, o, e) in enumerate(pares)])


# ------------------------------------------------------------------ 1. escalação obrigatória
def _duas_expostas():
    # um recurso só, duas expostas; a segunda fica sem recurso (exposta_nao_atendida, não rígida)
    return [oc("cel_a", -10.1, -47.0, 0.8, pop=500), oc("cel_b", -10.2, -47.0, 0.7, pop=300)], [rec("t1", "bn")]


def test_exposta_sem_recurso_vira_escalacao_mesmo_com_critico_aprovando(tmp_path, monkeypatch):
    monkeypatch.setattr(critico, "decidir_offline",
                        lambda ctx, plano, vs, rodada: VeredictoCritico(decisao="aprova", motivos=["LLM: ok"]))
    occs, recs = _duas_expostas()
    res = _rodar(tmp_path, occs, recs)
    assert res.status == "escala"
    esc = {e["ocorrencia_id"]: e for e in res.escalacoes}
    assert "cel_b" in esc and "cel_a" not in esc
    assert esc["cel_b"]["sugestao"] == "solicitar apoio externo"
    assert "300" in esc["cel_b"]["motivo"] and "apoio externo" in esc["cel_b"]["motivo"]
    assert res.plano.resumo.startswith("[escala]")


def test_escalacoes_existentes_nao_somem_nem_duplicam(tmp_path):
    occs, recs = _duas_expostas()
    occs.append(oc("cel_longe", -12.9, -49.4, 0.9, pop=50))  # sem recurso viável: escalação obrigatória já existente
    res = _rodar(tmp_path, occs, recs)
    ids = [e["ocorrencia_id"] for e in res.escalacoes]
    assert res.status == "escala"
    assert {"cel_b", "cel_longe"} <= set(ids)
    assert len([i for i in ids if i is not None]) == len({i for i in ids if i is not None})  # sem duplicata
    assert all(e.get("sugestao") == "solicitar apoio externo" for e in res.escalacoes if e["ocorrencia_id"])


def test_sem_populacao_sem_recurso_nao_escala(tmp_path):
    occs = [oc("cel_a", -10.1, -47.0, 0.8, pop=500), oc("cel_mato", -10.2, -47.0, 0.7)]
    res = _rodar(tmp_path, occs, [rec("t1", "bn")])
    assert res.status == "aprova" and res.escalacoes == []


# ------------------------------------------------------------------ 2. troca de recurso local ocioso
def _caso_troca():
    # cel_longe (500 hab.) vem antes no guloso e leva t1 (Base Norte, ~3,5 h); cel_perto (5000 hab.) fica a ~0,2 h
    # da mesma base e fica sem recurso (padrão de output_examples/tocantins-folgado, sem ids fixos).
    return [oc("cel_longe", -10.9, -47.0, 0.9, pop=500), oc("cel_perto", -10.05, -47.0, 0.5, pop=5000)], \
        [rec("t1", "bn")]


def test_checar_regras_propoe_troca_recurso_local():
    occs, recs = _caso_troca()
    v = checar_regras(_plano(("t1", "cel_longe", 3.5)), occs, recs, [BN, BS], CFG, [])
    troca = [x for x in v if x.regra == "troca_recurso_local"]
    assert len(troca) == 1 and not troca[0].rigida
    t = troca[0]
    assert t.ocorrencia_id == "cel_perto" and t.recurso_id == "t1"
    assert t.evidencia["de_ocorrencia"] == "cel_longe" and t.evidencia["eta_para_exposta_h"] < 0.5
    assert "t1" in t.sugestao and "cel_longe" in t.sugestao
    # continua informando a exposta sem recurso (não esconde a zona cinzenta)
    assert any(x.regra == "exposta_nao_atendida" and x.ocorrencia_id == "cel_perto" for x in v)


def test_sem_troca_quando_a_atendida_tem_mais_exposicao_ou_o_ganho_e_pequeno():
    # a atendida tem muito mais gente: não troca
    occs = [oc("cel_longe", -10.9, -47.0, 0.9, pop=50000), oc("cel_perto", -10.05, -47.0, 0.5, pop=5000)]
    v = checar_regras(_plano(("t1", "cel_longe", 3.5)), occs, [rec("t1", "bn")], [BN, BS], CFG, [])
    assert not any(x.regra == "troca_recurso_local" for x in v)
    # o recurso já está mais perto da que atende: não troca
    occs = [oc("cel_a", -10.1, -47.0, 0.9, pop=500), oc("cel_b", -10.2, -47.0, 0.7, pop=5000)]
    v = checar_regras(_plano(("t1", "cel_a", 0.39)), occs, [rec("t1", "bn")], [BN, BS], CFG, [])
    assert not any(x.regra == "troca_recurso_local" for x in v)


def test_critico_offline_aplica_a_troca(tmp_path):
    occs, recs = _caso_troca()
    res = _rodar(tmp_path, occs, recs)
    pares = {(d.recurso_id, d.ocorrencia_id) for d in res.plano.designacoes}
    assert ("t1", "cel_perto") in pares  # o recurso local vai para a exposta perto da base
    assert res.historico[0]["veredicto"]["decisao"] == "rejeita"
    assert any("Troca" in m for m in res.historico[0]["veredicto"]["motivos"])
    # quem perdeu o recurso continua visível como escalação
    assert any(e["ocorrencia_id"] == "cel_longe" for e in res.escalacoes)


def test_critico_offline_unitario_troca():
    occs, recs = _caso_troca()
    ctx = Contexto(regiao=CFG, periodo=P, ocorrencias=occs, recursos=recs, bases=[BN, BS], reserva=0)
    plano = _plano(("t1", "cel_longe", 3.5))
    v = critico.decidir_offline(ctx, plano, checar_regras(plano, occs, recs, [BN, BS], CFG, []), 1)
    assert v.decisao == "rejeita" and v.contra_proposta is not None
    assert [(d.recurso_id, d.ocorrencia_id) for d in v.contra_proposta.designacoes] == [("t1", "cel_perto")]
    assert "cel_longe" in v.contra_proposta.nao_atendidas


# ------------------------------------------------------------------ 3. SAMPLE_MODE=true
@pytest.mark.parametrize("valor,esperado", [("true", True), ("1", True), ("TRUE", True), ("false", False),
                                            ("", False)])
def test_sample_mode_por_variavel_de_ambiente(monkeypatch, valor, esperado):
    monkeypatch.setenv("SAMPLE_MODE", valor)
    args = cli.montar_parser().parse_args(["run", "--regiao", "tocantins"])
    assert cli.modo_sample(args) is esperado


def test_sample_mode_env_roda_sem_regiao_e_forca_offline(monkeypatch):
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "nightshift")
    chamados = {}

    def falso_run(args):
        chamados["regiao"] = args.regiao
        chamados["modo"] = cli.escolher_modo(args)
        return 0

    monkeypatch.setattr(cli, "cmd_run", falso_run)  # montar_parser lê cmd_run na hora
    assert cli.main(["run"]) == 0
    assert chamados == {"regiao": "tocantins", "modo": "offline"}
    assert os.environ["LLM_PROVIDER"] == "offline"


# ------------------------------------------------------------------ 4. avaliar
def test_cli_avaliar_chama_a_ablacao_por_import(tmp_path, capsys):
    rc = cli.main(["avaliar", "--modo", "offline", "--repeticoes", "1", "--cenarios",
                   "controle_taguatinga_liberada_21out", "--saida", str(tmp_path)])
    assert rc == 0
    pastas = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(pastas) == 1 and pastas[0].name.endswith("_offline")
    assert len(list(pastas[0].glob("controle_taguatinga_liberada_21out__*__r1.json"))) == 4  # variantes A-D


def test_cli_avaliar_sample_equivale_a_modo_offline(monkeypatch):
    recebido = {}
    import eval.run_ablacao as ab
    monkeypatch.setattr(ab, "main", lambda argv: recebido.setdefault("argv", argv) and 0)
    assert cli.main(["avaliar", "--sample", "--repeticoes", "2", "--cenarios", "a", "b"]) == 0
    argv = recebido["argv"]
    assert argv[argv.index("--modo") + 1] == "offline"
    assert argv[argv.index("--repeticoes") + 1] == "2"
    assert argv[argv.index("--cenarios") + 1:argv.index("--cenarios") + 3] == ["a", "b"]


# ------------------------------------------------------------------ 5. log_path relativo
def test_log_path_relativo_a_raiz_quando_dentro_do_repo(tmp_path):
    occs, recs = _duas_expostas()
    pasta = RAIZ / "logs" / "_teste_log_path"
    try:
        res = _rodar(tmp_path, occs, recs, pasta_log=pasta)
        assert not os.path.isabs(res.log_path)
        assert res.log_path.startswith("logs/_teste_log_path/") and (RAIZ / res.log_path).exists()
    finally:
        for f in pasta.glob("*"):
            f.unlink()
        pasta.rmdir()


def test_log_path_absoluto_quando_fora_do_repo(tmp_path):
    occs, recs = _duas_expostas()
    res = _rodar(tmp_path, occs, recs)
    assert os.path.isabs(res.log_path) and json.loads(open(res.log_path).readline())["evento"] == "inicio"
