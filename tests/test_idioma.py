"""Idioma por execução (docs/CONTRATOS.md, seção 19): o plano inteiro sai em pt-BR ou en, não só os rótulos.

- normalização e precedência (--idioma > pedido da API > FOCOCERTO_IDIOMA > RegiaoCfg.idioma);
- catálogo de conteúdo (app/core/mensagens.py) com as mesmas chaves nos dois idiomas;
- checar_citacoes em inglês: fato errado é pego, fato certo não gera alarme falso, evidências estruturadas iguais;
- prompts do LLM pedem o idioma;
- ponta a ponta: `run --sample --idioma en` nos cenários reais sem português no plano.md/plano.json (fora nomes de
  lugares, fontes das bases e ids), e o análogo em pt-BR sem inglês de interface.
Dados de teste SIMULADOS (fakes), salvo as execuções com o cache real.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import cli
from app.agents import base as agentes_base
from app.agents import planejador
from app.agents.base import Contexto
from app.core import config
from app.core.config import RAIZ
from app.core.mensagens import MENSAGENS, msg, normalizar_idioma, resolver_idioma
from app.core.models import Base, Designacao, Plano
from app.llm import client
from app.llm.client import LLMResult
from app.tools.alocador import justificar
from app.tools.citacoes import checar_citacoes
from app.tools.geo import eta_recurso
from app.tools.regras import checar_regras
from tests.fakes import oc, rec, regiao_teste

CFG_PT = regiao_teste()
CFG_EN = regiao_teste(idioma="en")
BN = Base(id="bn", nome="Base Norte", lat=-10.0, lon=-47.0)
DIV = [{"nome": "Divinópolis do Tocantins", "pop": 7297, "dist_km": 9.5}]


# ------------------------------------------------------------------ normalização, precedência, catálogo
@pytest.mark.parametrize("valor,esperado", [("en", "en"), ("en-US", "en"), ("EN_gb", "en"), ("pt", "pt-BR"),
                                            ("pt-BR", "pt-BR"), ("pt_PT", "pt-BR"), ("es-ES", None), ("", None),
                                            (None, None)])
def test_normalizar_idioma(valor, esperado):
    assert normalizar_idioma(valor) == esperado


def test_resolver_idioma_precedencia_e_fallback():
    assert resolver_idioma("en", "pt-BR", "pt-BR") == "en"
    assert resolver_idioma(None, "en-US", "pt-BR") == "en"
    assert resolver_idioma(None, None, "pt-BR") == "pt-BR"
    assert resolver_idioma(None, "xx", "es-ES") == "pt-BR"   # nada suportado: pt-BR


def test_catalogo_tem_as_mesmas_chaves_nos_dois_idiomas():
    assert set(MENSAGENS["pt-BR"]) == set(MENSAGENS["en"])
    for chave, v in MENSAGENS["pt-BR"].items():
        if isinstance(v, dict):
            assert set(v) == set(MENSAGENS["en"][chave]), chave


def test_textos_pt_identicos_aos_de_antes():
    """O catálogo não muda os textos em português (exemplos e testes antigos continuam valendo)."""
    assert msg("esc_guarda_corpo", "pt-BR", pop=300, sug=msg("sugestao_apoio_externo", "pt-BR")) == \
        "Obrigatória: 300 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo."
    assert msg("jus_pop", "pt-BR", pop=1200) == "1200 habitantes no raio"
    assert msg("jus_pop", "en", pop=1200) == "1200 inhabitants in the radius"


# ------------------------------------------------------------------ checar_citacoes em inglês
def _cit(just, evid=(), cfg=CFG_EN, eta=None):
    occs = [oc("a", -10.1, -47.0, 0.9, pop=7297, localidades=DIV,
               n_focos=4, frp_soma=40.0)]
    recs = [rec("t1", "bn")]
    e = eta if eta is not None else round(eta_recurso(recs[0], BN, occs[0], cfg), 2)
    d = Designacao(recurso_id="t1", ocorrencia_id="a", ordem=1, eta_h=e, justificativa=just, evidencias=list(evid))
    return checar_citacoes(Plano(periodo="p", regiao="teste", designacoes=[d]), occs, [BN], recursos=recs,
                           regiao_cfg=cfg)


def _eta_real(cfg=CFG_EN) -> float:
    return eta_recurso(rec("t1", "bn"), BN, oc("a", -10.1, -47.0, 0.9), cfg)


def test_justificativa_inglesa_correta_nao_gera_alarme():
    eta = _eta_real()
    texto = (f"7,297 inhabitants exposed; Divinópolis do Tocantins at 9.5 km; t1 arrives in {eta:.1f} h from "
             f"Base Norte, within the 6 h limit (ETA {eta:.1f} h, limit 6 h). About 7297 people and residents nearby.")
    assert _cit(texto, ["pop:7297", f"eta:{eta:.2f}", "dist:Divinópolis do Tocantins:9.5", "base:bn"]) == []


@pytest.mark.parametrize("texto,campo", [
    ("About 25,000 inhabitants exposed.", "pop_texto"),
    ("Roughly 900 people live nearby.", "pop_texto"),
    ("5000 residents in the radius.", "pop_texto"),
    ("The crew arrives in 4.5 h.", "eta_texto"),
    ("ETA 3 h from Base Norte.", "eta_texto"),
    ("Divinópolis do Tocantins is 30 km away.", "dist_texto"),
])
def test_justificativa_inglesa_com_fato_errado_e_pega(texto, campo):
    assert campo in [v.evidencia["campo"] for v in _cit(texto)]


def test_limite_em_ingles_nao_e_eta_citado():
    for texto in ("no crew arrives within the 6 h limit", "ETA under 6 h", "ETA limit 6 h", "arrives in up to 6 h"):
        assert [v for v in _cit(texto) if v.evidencia["campo"] == "eta_texto"] == [], texto


def test_localidade_de_outra_ocorrencia_citada_em_ingles_e_pega():
    occs = [oc("a", -10.1, -47.0, 0.9, pop=7297, localidades=DIV),
            oc("b", -11.5, -47.0, 0.5, pop=900, localidades=[{"nome": "Gurupi", "pop": 900, "dist_km": 3.0}])]
    recs = [rec("t1", "bn")]
    d = Designacao(recurso_id="t1", ocorrencia_id="a", ordem=1, eta_h=round(eta_recurso(recs[0], BN, occs[0], CFG_EN), 2),
                   justificativa="Protects the town of Gurupi.", evidencias=[])
    vs = checar_citacoes(Plano(periodo="p", regiao="teste", designacoes=[d]), occs, [BN], recursos=recs,
                         regiao_cfg=CFG_EN)
    assert [v.evidencia["campo"] for v in vs] == ["localidade"]


def test_evidencias_estruturadas_independem_do_idioma():
    evid_ok = ["pop:7297", "dist:Divinópolis do Tocantins:9.5", "base:bn", "focos:4", "frp:40"]
    evid_erro = ["pop:9999", "dist:Divinópolis do Tocantins:30", "focos:9", "frp:999", "eta:9.9", "base:nao_existe"]
    for cfg in (CFG_PT, CFG_EN):
        assert _cit("-", evid_ok, cfg=cfg) == []
        campos = sorted(v.evidencia["campo"] for v in _cit("-", evid_erro, cfg=cfg))
        assert campos == ["base", "dist", "eta", "focos", "frp", "pop"]
    sug_pt = {v.evidencia["campo"]: v.sugestao for v in _cit("-", evid_erro, cfg=CFG_PT)}
    sug_en = {v.evidencia["campo"]: v.sugestao for v in _cit("-", evid_erro, cfg=CFG_EN)}
    assert sug_pt["pop"] == "população no raio = 7297" and sug_en["pop"] == "population in the radius = 7297"


@pytest.mark.parametrize("cfg", [CFG_PT, CFG_EN], ids=["pt-BR", "en"])
def test_justificativa_do_alocador_passa_no_checador_nos_dois_idiomas(cfg):
    o = oc("a", -10.1, -47.0, 0.9, pop=7297, localidades=DIV)
    r = rec("t1", "bn")
    eta = eta_recurso(r, BN, o, cfg)
    texto, ev = justificar(o, r, BN, eta, idioma=cfg.idioma)
    assert ("inhabitants" in texto) == (cfg.idioma == "en") and ("habitantes" in texto) == (cfg.idioma == "pt-BR")
    d = Designacao(recurso_id="t1", ocorrencia_id="a", ordem=1, eta_h=round(eta, 2), justificativa=texto,
                   evidencias=ev)
    assert checar_citacoes(Plano(periodo="p", regiao="teste", designacoes=[d]), [o], [BN], recursos=[r],
                           regiao_cfg=cfg) == []


def test_sugestoes_das_regras_no_idioma():
    o = oc("a", -10.1, -47.0, 0.9, pop=500)
    p = Plano(periodo="p", regiao="teste", designacoes=[])
    for cfg, trecho in ((CFG_PT, "escalar"), (CFG_EN, "escalate")):
        vs = checar_regras(p, [o], [rec("t1", "longe")], [BN], cfg, [])
        assert vs and all(trecho in v.sugestao for v in vs if v.regra == "exposicao_sem_recurso_viavel")


# ------------------------------------------------------------------ prompts do LLM pedem o idioma
def test_prompt_do_llm_pede_o_idioma(monkeypatch):
    capturado = {}

    def chat_falso(messages, papel, json_schema=None, log=None):
        capturado["msgs"] = messages
        return LLMResult(texto="{}", json={"designacoes": [], "resumo": "ok"}, modelo="falso", routed_model=None,
                         receipt=None, tokens=None, latencia_s=0.0)

    monkeypatch.setattr(client, "chat", chat_falso)
    o = oc("a", -10.1, -47.0, 0.9, pop=10)
    for cfg, esperado in ((CFG_EN, "English"), (CFG_PT, "português do Brasil")):
        ctx = Contexto(regiao=cfg, periodo="p", ocorrencias=[o], recursos=[rec("t1", "bn")], bases=[BN], reserva=0)
        planejador.decidir(ctx, 1, None)
        sistema, usuario = capturado["msgs"][0]["content"], capturado["msgs"][1]["content"]
        assert esperado in sistema
        dados = json.loads(usuario.split("\n", 1)[1])
        assert dados["idioma_saida"] == cfg.idioma
    # os três prompts mencionam o campo idioma_saida
    for nome in ("planejador", "critico", "analista"):
        assert "idioma_saida" in agentes_base.carregar_prompt(nome)


# ------------------------------------------------------------------ ponta a ponta (cache real, sample mode)
CENARIOS = ["cenarios/tocantins-escasso.yaml", "cenarios/tocantins-medio.yaml", "cenarios/tocantins-folgado.yaml",
            "input_examples/tocantins-parana-analista.yaml"]   # o último chama o Analista
PORTUGUES = ["habitantes", "escalação", "obrigatória", "sugestão", "recurso", "ocorrência", " não ", "população",
             "prioridade", "saindo de", "chega em", "crítico", "analista", "designaç", "rodada", "queima", "focos"]
INGLES = ["inhabitants", "escalation", "mandatory", "suggest", "priority", " the ", "resource", "incident",
          "detections", "arrives", "critic", "analyst", "planner", "round ", "justification", " crew"]
CHAVES_DADO = {"fonte", "nome", "texto", "citado", "real", "arquivo_cenario", "log_path", "consultas", "evidencias",
               "regra", "campo", "localidades"}


@pytest.fixture
def rodar_cli(tmp_path, monkeypatch):
    """`python -m app.cli run --sample ...` no mesmo processo, com estado, saídas e logs em tmp_path."""
    from app.data.repositorio import RepositorioCache
    from app.memory_client import MemoriaLocal
    monkeypatch.setattr(config, "carregar_env", lambda *a, **k: None)   # não lê o .env do repositório
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.delenv("FOCOCERTO_IDIOMA", raising=False)

    def rodar(cenario: str, *extra: str, nome: str = "x") -> dict:
        estado = tmp_path / nome / "estado"
        monkeypatch.setattr(cli, "criar_repositorio", lambda args: RepositorioCache(estado=estado))
        monkeypatch.setattr(cli, "criar_memoria", lambda args: MemoriaLocal(caminho=estado / "memoria.json"))
        saida = tmp_path / nome / "out"
        rc = cli.main(["run", "--sample", "--regiao", "tocantins", "--recursos", str(RAIZ / cenario),
                       "--saida", str(saida), "--pasta-logs", str(tmp_path / nome / "logs"), *extra])
        assert rc == 0
        pasta = next(saida.rglob("plano.json")).parent
        return {"json": json.loads((pasta / "plano.json").read_text(encoding="utf-8")),
                "md": (pasta / "plano.md").read_text(encoding="utf-8"),
                "mapa": (pasta / "mapa.html").read_text(encoding="utf-8"), "rc": rc}
    return rodar


def _valores_livres(obj, chave=None):
    """Strings de texto livre do plano.json (fora as chaves que guardam dado de entrada, nome ou id)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in CHAVES_DADO or k.endswith("_id") or k == "id":
                continue
            yield from _valores_livres(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _valores_livres(v, chave)
    elif isinstance(obj, str):
        yield obj


def _limpar(texto: str, d: dict) -> str:
    """Tira o que não é idioma de interface: código entre crases, ids com _ ou :, nomes de lugares e bases, fontes."""
    nomes = {b["nome"] for b in d["bases"]} | {b["fonte"] for b in d["bases"] if b.get("fonte")}
    nomes |= {l["nome"] for o in d["ocorrencias"] for l in o["localidades"] if l.get("nome")}
    for n in sorted(nomes, key=len, reverse=True):
        texto = texto.replace(n, " ")
    texto = re.sub(r"`[^`]*`", " ", texto)
    texto = re.sub(r"\S*[_/]\S*|\b\w+:\S+", " ", texto)   # ids, caminhos e tokens de evidência (pop:1200)
    return " " + texto.lower() + " "


def _sobras(r: dict, palavras: list[str]) -> dict[str, list[str]]:
    d = r["json"]
    md = _limpar(r["md"], d)
    js = _limpar("\n".join(_valores_livres(d)), d)
    achados = {}
    for onde, texto in (("plano.md", md), ("plano.json", js)):
        for p in palavras:
            for m in re.finditer(re.escape(p), texto):
                achados.setdefault(onde, []).append(texto[max(0, m.start() - 50):m.end() + 50].replace("\n", " "))
    return achados


@pytest.mark.parametrize("cenario", CENARIOS)
def test_plano_em_ingles_sem_portugues(rodar_cli, cenario):
    r = rodar_cli(cenario, "--idioma", "en-US", nome="en")
    assert r["json"]["meta"]["idioma"] == "en"
    assert r["json"]["plano"]["resumo"].startswith(("[approved]", "[escalated]"))
    assert '<html lang="en">' in r["mapa"]
    sobras = _sobras(r, PORTUGUES)
    assert not sobras, json.dumps(sobras, ensure_ascii=False, indent=1)[:3000]


@pytest.mark.parametrize("cenario", CENARIOS)
def test_plano_em_portugues_sem_ingles(rodar_cli, cenario):
    r = rodar_cli(cenario, "--idioma", "pt", nome="pt")
    assert r["json"]["meta"]["idioma"] == "pt-BR"
    assert r["json"]["plano"]["resumo"].startswith(("[aprova]", "[escala]"))
    sobras = _sobras(r, INGLES)
    assert not sobras, json.dumps(sobras, ensure_ascii=False, indent=1)[:3000]


def test_mesma_alocacao_nos_dois_idiomas(rodar_cli):
    """O idioma muda o texto, não a decisão."""
    pt = rodar_cli(CENARIOS[0], nome="pt")
    en = rodar_cli(CENARIOS[0], "--idioma", "en", nome="en")
    pares = lambda r: [(d["recurso_id"], d["ocorrencia_id"], d["evidencias"]) for d in r["json"]["plano"]["designacoes"]]
    assert pares(pt) == pares(en)
    assert [e["ocorrencia_id"] for e in pt["json"]["escalacoes"]] == [e["ocorrencia_id"] for e in en["json"]["escalacoes"]]


def test_precedencia_flag_sobre_variavel_de_ambiente(rodar_cli, monkeypatch):
    monkeypatch.setenv("FOCOCERTO_IDIOMA", "en")
    assert rodar_cli(CENARIOS[2], nome="env")["json"]["meta"]["idioma"] == "en"
    assert rodar_cli(CENARIOS[2], "--idioma", "pt-BR", nome="flag")["json"]["meta"]["idioma"] == "pt-BR"
    monkeypatch.delenv("FOCOCERTO_IDIOMA")
    assert rodar_cli(CENARIOS[2], nome="regiao")["json"]["meta"]["idioma"] == "pt-BR"   # tocantins.yaml


def test_idioma_nao_suportado_e_erro_claro(rodar_cli, capsys):
    with pytest.raises(AssertionError):
        rodar_cli(CENARIOS[2], "--idioma", "fr", nome="fr")
    assert "Idioma não suportado" in capsys.readouterr().err


# ------------------------------------------------------------------ API
def test_api_run_aceita_idioma(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from app.api import criar_app
    from app.data.repositorio import RepositorioCache
    from app.memory_client import MemoriaLocal
    from tests.test_api import esperar
    estado = tmp_path / "estado"
    monkeypatch.setattr(cli, "criar_repositorio", lambda args: RepositorioCache(estado=estado))
    monkeypatch.setattr(cli, "criar_memoria", lambda args: MemoriaLocal(caminho=estado / "memoria.json"))
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("FOCOCERTO_IDIOMA", raising=False)
    c = TestClient(criar_app(saida=tmp_path / "out", exemplos=tmp_path / "ex", pasta_logs=tmp_path / "logs",
                             web_dist=tmp_path / "sem_dist"))
    ruim = c.post("/api/run", json={"regiao": "tocantins", "recursos": "cenarios/tocantins-folgado.yaml",
                                    "sample": True, "idioma": "klingon"})
    assert ruim.status_code == 400 and "Idioma não suportado" in ruim.json()["detail"]
    r = c.post("/api/run", json={"regiao": "tocantins", "recursos": "cenarios/tocantins-folgado.yaml",
                                 "sample": True, "idioma": "en"})
    j = esperar(c, r.json()["job_id"])
    assert j["status"] == "concluido", j.get("erro")
    assert j["resultado"]["idioma"] == "en" and j["pedido"]["idioma"] == "en"
    plano = c.get(j["resultado"]["plano_url"]).json()
    assert plano["meta"]["idioma"] == "en"
    assert all("inhabitants" in d["justificativa"] or "no population" in d["justificativa"]
               for d in plano["plano"]["designacoes"])
