"""Testes de app/output e app/cli com um ResultadoPeriodo de TESTE (tests/dados_teste_resultado.py)."""
from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from app import cli
from app.core.config import RAIZ, cenario as ler_cenario
from app.core.models import Cenario, Plano, Recurso
from app.output import escrever_saidas, render_json, render_markdown
from app.output.mapa import LEAFLET_JS, render_mapa
from tests.dados_teste_resultado import regiao_teste, resultado_teste

CENARIO = Cenario(regiao="tocantins", periodo="2026-10-24", simulado=True,
                  recursos=[Recurso(id="r-terra-1", base_id="osm_teste_2", tipo="terrestre")])


# ----------------------------------------------------------------------------- render

def test_markdown_ordem_das_secoes_e_conteudo():
    md = render_markdown(resultado_teste(), regiao_teste(), CENARIO, modo="offline",
                         arquivo_cenario="cenarios/x.yaml", pasta_saida=Path("/tmp/fococerto-teste/out/t/p"))
    assert "RECURSOS SIMULADOS" in md and "cenarios/x.yaml" in md
    # o mais importante vem primeiro: escalações antes da ordem de recursos, que vem antes das prioridades
    i_esc, i_ordem, i_prio = (md.index("## Escalações"), md.index("## Ordem de recursos"),
                              md.index("## Lista de prioridades"))
    assert i_esc < i_ordem < i_prio
    assert "**ESCALADA** `cel_-110_-462`" in md
    assert "| 1 | `r-terra-1` (terrestre, Base Teste Mateiros) | `cel_-102_-465` (Mateiros, 8.4 km)" in md
    assert "`pop:Mateiros:2300`" in md and "(nenhuma evidência citada)" in md
    assert "provável queima agrícola ou de manejo** (confiança: **média**)" in md
    assert "substitui m1" in md
    assert "Rodadas do ciclo Planejador/Crítico: 2" in md
    assert "veredicto do Crítico `rejeita`; 1 violações (eta_acima_limite)" in md
    assert "veredicto do Crítico `escala`" in md
    assert "## Limitações" in md and "Detecção de satélite não confirma incêndio" in md
    assert "[Log completo da execução](../../../logs/exec-teste.jsonl)" in md
    assert "offline (agentes determinísticos, sem LLM)" in md
    # "|" dentro do texto não quebra a tabela; o resumo fica fora de tabela
    assert "Plano de teste: duas ocorrências com população exposta atendidas | uma escalada." in md


def test_markdown_em_ingles_e_sem_aviso_quando_nao_simulado():
    cen = CENARIO.model_copy(update={"simulado": False})
    md = render_markdown(resultado_teste(), regiao_teste("en"), cen)
    assert "## Resource order" in md and "## Escalations" in md and "## Limitations" in md
    assert "SIMULATED RESOURCES" not in md
    assert "likely agricultural or management burn** (confidence: **medium**)" in md


def test_idioma_desconhecido_cai_no_portugues():
    md = render_markdown(resultado_teste(), regiao_teste("xx"), CENARIO)
    assert "## Ordem de recursos" in md


def test_json_round_trip_do_plano():
    dados = json.loads(render_json(resultado_teste(), regiao_teste(), CENARIO, modo="offline"))
    assert dados["meta"]["simulado"] is True and dados["meta"]["aprovacao_humana"] == "pendente"
    plano = Plano(**dados["plano"])
    assert [d.recurso_id for d in plano.designacoes] == ["r-terra-1", "r-aereo-1"]
    assert dados["historico"][0]["veredicto"]["decisao"] == "rejeita"
    assert dados["escalacoes"][0]["ocorrencia_id"] == "cel_-110_-462"


def test_mapa_autocontido():
    h = render_mapa(resultado_teste(), regiao_teste(), CENARIO, arquivo_cenario="cenarios/x.yaml")
    assert LEAFLET_JS in h and "leaflet/1.9.4/" in h
    i = h.index('<script id="dados" type="application/json">') + len('<script id="dados" type="application/json">')
    bruto = h[i:h.index("</script>", i)]
    assert "<" not in bruto  # "Dianópolis <teste>" foi escapado e não fecha o <script>
    d = json.loads(bruto)
    assert len(d["ocorrencias"]) == 5 and len(d["bases"]) == 2 and len(d["linhas"]) == 2
    por_id = {o["id"]: o for o in d["ocorrencias"]}
    assert por_id["cel_-110_-462"]["escalada"] is True
    assert por_id["cel_-102_-465"]["faixa"] == "alta" and por_id["cel_-95_-476"]["faixa"] == "baixa"
    assert por_id["cel_-102_-465"]["designacoes"][0]["justificativa"].startswith("Mateiros")
    assert d["aviso"] and "RECURSOS SIMULADOS" in d["aviso"]


def test_escrever_saidas(tmp_path):
    c = escrever_saidas(resultado_teste(), regiao_teste(), CENARIO, tmp_path / "out", modo="offline")
    assert {p.name for p in c.values()} == {"plano.json", "plano.md", "mapa.html"}
    assert all(p.stat().st_size > 0 for p in c.values())


def test_cenarios_da_demo_sao_validos_e_simulados():
    arquivos = sorted((RAIZ / "cenarios").glob("tocantins-*.yaml"))
    assert len(arquivos) >= 3
    for a in arquivos:
        c = ler_cenario(a)
        assert c.simulado is True and c.regiao == "tocantins" and c.recursos
        # toda base de recurso existe no cache (OSM) ou foi declarada no cenário
        ids_cache = {l.split(",")[0] for l in (RAIZ / "data/cache/tocantins/bases.csv").read_text().splitlines()[1:]}
        ids_declarados = {b.id for b in c.bases}
        assert all(b.simulada for b in c.bases)
        assert all(r.base_id in ids_cache | ids_declarados for r in c.recursos)


# ----------------------------------------------------------------------------- CLI

def test_cli_help():
    r = subprocess.run([sys.executable, "-m", "app.cli", "--help"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0
    for sub in ("run", "nota", "aprovar", "avaliar"):
        assert sub in r.stdout
    r = subprocess.run([sys.executable, "-m", "app.cli", "run", "--help"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0 and "--sample" in r.stdout and "--recursos" in r.stdout


def test_cli_modulo_faltando_da_mensagem_clara(monkeypatch, capsys, tmp_path):
    monkeypatch.setitem(sys.modules, "app.agents.grafo", None)  # simula o módulo ausente
    rc = cli.main(["run", "--sample", "--saida", str(tmp_path), "--pasta-logs", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "app.agents.grafo ainda não existe (dono: agentes-llm)" in err
    assert "Traceback" not in err


def test_cli_nome_faltando_no_modulo(monkeypatch):
    monkeypatch.setitem(sys.modules, "app.agents.grafo", types.ModuleType("app.agents.grafo"))
    with pytest.raises(cli.ErroDependencia, match="ainda não define executar_periodo"):
        cli.importar("app.agents.grafo", "executar_periodo")


def _stubs(monkeypatch, chamadas):
    """Módulos falsos com a assinatura dos contratos (seções 3, 10 e 11), só para o teste."""
    grafo = types.ModuleType("app.agents.grafo")

    def executar_periodo(regiao, cenario, repo, memoria, log, modo="llm", usar_critico_llm=True, usar_memoria=True):
        chamadas["executar"] = {"modo": modo, "repo": type(repo).__name__, "memoria": type(memoria).__name__}
        log.evento("planejador", "proposta", {"rodada": 1})
        return resultado_teste().model_copy(update={"log_path": ""})

    grafo.executar_periodo = executar_periodo

    repo_mod = types.ModuleType("app.data.repositorio")

    class RepositorioCache:
        def salvar_decisoes(self, plano, aprovado_por):
            chamadas["decisoes"] = (plano, aprovado_por)

        def salvar_nota(self, regiao, periodo, texto, autor):
            chamadas["nota_repo"] = (regiao, periodo, texto, autor)

    repo_mod.RepositorioCache = RepositorioCache
    mem_mod = types.ModuleType("app.memory_client")

    class MemoriaLocal:
        def __init__(self, caminho=None):
            chamadas["memoria_caminho"] = caminho

        def gravar(self, regiao, texto, tipo, fonte, confianca=1.0, supersedes=None):
            chamadas["nota_mem"] = (regiao, texto, tipo, fonte)
            return types.SimpleNamespace(id="m-teste", supersedes=None)

    mem_mod.MemoriaLocal = MemoriaLocal
    monkeypatch.setitem(sys.modules, "app.agents.grafo", grafo)
    monkeypatch.setitem(sys.modules, "app.data.repositorio", repo_mod)
    monkeypatch.setitem(sys.modules, "app.memory_client", mem_mod)
    monkeypatch.setattr(cli.config, "regiao", lambda nome: regiao_teste())


def test_cli_run_aprovar_nota_com_stubs(monkeypatch, tmp_path, capsys):
    chamadas: dict = {}
    _stubs(monkeypatch, chamadas)
    comum = ["--sample", "--saida", str(tmp_path / "out"), "--pasta-logs", str(tmp_path / "logs")]
    rc = cli.main(["run", "--regiao", "tocantins", "--recursos", str(RAIZ / "cenarios/tocantins-escasso.yaml"), *comum])
    assert rc == 0, capsys.readouterr().err
    assert chamadas["executar"] == {"modo": "offline", "repo": "RepositorioCache", "memoria": "MemoriaLocal"}
    periodo = ler_cenario(RAIZ / "cenarios/tocantins-escasso.yaml").periodo
    pasta = tmp_path / "out" / "tocantins" / periodo
    assert {p.name for p in pasta.iterdir()} == {"plano.json", "plano.md", "mapa.html"}
    md = (pasta / "plano.md").read_text()
    assert "RECURSOS SIMULADOS" in md and "tocantins-escasso.yaml" in md and "](../../../logs/" in md
    logs = list((tmp_path / "logs").glob("*.jsonl"))
    assert len(logs) == 1
    eventos = [json.loads(l)["evento"] for l in logs[0].read_text().splitlines()]
    assert eventos[0] == "inicio" and eventos[-1] == "fim" and "proposta" in eventos
    assert "planejador: proposta" in capsys.readouterr().err  # progresso no terminal

    rc = cli.main(["aprovar", "--regiao", "tocantins", "--periodo", periodo, "--autor", "coord", *comum])
    assert rc == 0
    plano, autor = chamadas["decisoes"]
    assert autor == "coord" and len(plano.designacoes) == 2

    rc = cli.main(["nota", "--regiao", "tocantins", "--periodo", "2026-10-25", "--autor", "coord", *comum,
                   "estrada para Mateiros alagada"])
    assert rc == 0
    assert chamadas["nota_repo"] == ("tocantins", "2026-10-25", "estrada para Mateiros alagada", "coord")
    assert chamadas["nota_mem"] == ("tocantins", "estrada para Mateiros alagada", "nota", "coordenador:coord")


def test_cli_aprovar_sem_plano(tmp_path, capsys):
    rc = cli.main(["aprovar", "--regiao", "tocantins", "--periodo", "2000-01-01", "--saida", str(tmp_path)])
    assert rc == 2 and "Não há plano salvo" in capsys.readouterr().err
