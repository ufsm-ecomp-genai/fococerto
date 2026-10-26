"""Integração de ponta a ponta (dono: qa-integracao).

Roda a CLI de verdade (subprocesso) numa CÓPIA da árvore do projeto em tmp_path: app/, config/,
cenarios/ e data/cache/. A cópia tem o seu próprio data/estado/ e nenhum .env, então nada aqui
toca o estado do repositório de trabalho e o teste reproduz um juiz com `.env` vazio.

Motivo da cópia: a CLI grava a memória em RAIZ/data/estado (RAIZ = pasta acima de app/) e não
aceita outro diretório de estado por opção ou variável de ambiente.
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
CENARIOS = sorted((RAIZ / "cenarios").glob("tocantins-*.yaml"))
CAMPOS_LOG = {"t", "execucao", "regiao", "periodo", "agente", "evento", "dados",
              "modelo", "routed_model", "receipt", "tokens", "latencia_s"}
AGENTES = {"planejador", "critico", "analista", "ferramenta", "sistema"}
EVENTOS = {"inicio", "proposta", "violacao", "rejeita", "aprova", "escala", "consulta",
           "memoria_lida", "memoria_gravada", "llm_call", "fim"}
VARS_EXTERNAS = ("ZETARIS_API_KEY", "ZETARIS_REST_URL", "HMEM_URL", "METERLESS_BASE_URL",
                 "METERLESS_RUNTIME_TOKEN", "LLM_PROVIDER", "POSTGRES_DSN")


# ----------------------------------------------------------------------------- infraestrutura

@pytest.fixture(scope="module")
def arvore(tmp_path_factory) -> Path:
    """Cópia mínima e isolada do projeto (sem .env, sem data/estado)."""
    dest = tmp_path_factory.mktemp("arvore") / "fococerto"
    ignorar = shutil.ignore_patterns("__pycache__", "*.pyc")
    for pasta in ("app", "config", "cenarios"):
        shutil.copytree(RAIZ / pasta, dest / pasta, ignore=ignorar)
    shutil.copytree(RAIZ / "data" / "cache", dest / "data" / "cache", ignore=ignorar)
    return dest


def cli(arvore: Path, *args: str, ok: bool = True) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in VARS_EXTERNAS}
    p = subprocess.run([sys.executable, "-m", "app.cli", *args], cwd=arvore, env=env,
                       capture_output=True, text=True, timeout=120)
    if ok:
        assert p.returncode == 0, f"rc={p.returncode}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr[-3000:]}"
    return p


def rodar(arvore: Path, cenario: Path, saida: Path, *extra: str) -> dict:
    """`run --sample` gravando em `saida`; devolve plano.json, o log e os caminhos."""
    cli(arvore, "run", "--sample", "--regiao", "tocantins", "--recursos", str(cenario),
        "--saida", str(saida / "out"), "--pasta-logs", str(saida / "logs"), *extra)
    jsons = list((saida / "out").rglob("plano.json"))
    assert len(jsons) == 1, jsons
    logs = list((saida / "logs").glob("*.jsonl"))
    assert len(logs) == 1, logs
    linhas = [json.loads(l) for l in logs[0].read_text(encoding="utf-8").splitlines() if l.strip()]
    return {"plano_json": json.loads(jsons[0].read_text(encoding="utf-8")), "pasta": jsons[0].parent,
            "log": linhas, "log_path": logs[0]}


def escrever_cenario(arvore: Path, base: Path, nome: str, **mudancas) -> Path:
    dados = yaml.safe_load(base.read_text(encoding="utf-8"))
    for chave, valor in mudancas.items():
        dados[chave] = valor(dados[chave]) if callable(valor) else valor
    caminho = arvore / "cenarios" / f"qa-{nome}.yaml"
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return caminho


def ids_designados(r: dict) -> list[str]:
    return [d["recurso_id"] for d in r["plano_json"]["plano"]["designacoes"]]


def pares(r: dict) -> set[tuple[str, str]]:
    return {(d["recurso_id"], d["ocorrencia_id"]) for d in r["plano_json"]["plano"]["designacoes"]}


def checar_coerencia(r: dict, cenario: dict) -> None:
    """Invariantes que valem para qualquer entrada: o plano só usa o que existe na entrada."""
    plano = r["plano_json"]["plano"]
    disponiveis = {x["id"] for x in cenario["recursos"] if x["disponivel"]}
    ocorrencias = {o["id"] for o in r["plano_json"]["ocorrencias"]}
    usados = ids_designados(r)
    assert set(usados) <= disponiveis, f"designou recurso indisponível/inexistente: {set(usados) - disponiveis}"
    assert len(usados) == len(set(usados)), "recurso com capacidade 1 designado duas vezes"
    assert {d["ocorrencia_id"] for d in plano["designacoes"]} <= ocorrencias
    assert set(plano["reserva"]) <= disponiveis
    assert not set(plano["reserva"]) & set(usados), "recurso ao mesmo tempo na reserva e designado"
    assert plano["periodo"] == cenario["periodo"] and plano["regiao"] == cenario["regiao"]
    for d in plano["designacoes"]:
        assert d["justificativa"].strip() and d["evidencias"], d


# ----------------------------------------------------------------------------- run --sample de ponta a ponta

@pytest.fixture(scope="module")
def execucoes(arvore, tmp_path_factory) -> dict[str, dict]:
    """Uma execução de cada cenário real (reaproveitada pelos testes)."""
    return {c.stem: rodar(arvore, arvore / "cenarios" / c.name, tmp_path_factory.mktemp(c.stem)) for c in CENARIOS}


def test_ha_tres_cenarios_reais():
    assert len(CENARIOS) >= 3, CENARIOS


@pytest.mark.parametrize("nome", [c.stem for c in CENARIOS])
def test_run_sample_gera_saidas(execucoes, nome):
    r = execucoes[nome]
    cen = yaml.safe_load((RAIZ / "cenarios" / f"{nome}.yaml").read_text(encoding="utf-8"))
    pasta = r["pasta"]
    assert pasta.parts[-2:] == ("tocantins", cen["periodo"])
    for arq in ("plano.json", "plano.md", "mapa.html"):
        assert (pasta / arq).stat().st_size > 200, arq

    d = r["plano_json"]
    assert d["meta"]["regiao"] == "tocantins" and d["meta"]["periodo"] == cen["periodo"]
    assert d["meta"]["modo"] == "offline"
    assert d["log_path"] == str(r["log_path"])
    from app.core.models import Plano, ResultadoPeriodo
    Plano(**d["plano"])  # o `aprovar` lê exatamente isto
    ResultadoPeriodo(**{k: v for k, v in d.items() if k != "meta"})
    checar_coerencia(r, cen)
    assert d["plano"]["designacoes"], "nenhuma designação num período com 179 ocorrências"

    md = (pasta / "plano.md").read_text(encoding="utf-8")
    for rec in ids_designados(r):
        assert rec in md, f"{rec} não aparece no plano.md"
    html = (pasta / "mapa.html").read_text(encoding="utf-8")
    assert "<html" in html.lower() and "leaflet" in html.lower()
    assert d["plano"]["designacoes"][0]["ocorrencia_id"] in html


def test_status_do_resultado_preenchido(execucoes):
    for nome, r in execucoes.items():
        d = r["plano_json"]
        esperado = "escala" if d["escalacoes"] else "aprova"
        assert d["status"] == esperado, (nome, d["status"])


@pytest.mark.parametrize("nome", [c.stem for c in CENARIOS])
def test_log_jsonl_segue_secao_7(execucoes, nome):
    r = execucoes[nome]
    log = r["log"]
    assert len(log) >= 5
    execucao = log[0]["execucao"]
    assert r["log_path"].stem == execucao
    for i, linha in enumerate(log):
        assert set(linha) == CAMPOS_LOG, f"linha {i}: campos {sorted(set(linha) ^ CAMPOS_LOG)}"
        assert linha["execucao"] == execucao and linha["regiao"] == "tocantins"
        assert linha["periodo"] == r["plano_json"]["meta"]["periodo"]
        assert linha["agente"] in AGENTES, linha["agente"]
        assert linha["evento"] in EVENTOS, linha["evento"]
        assert isinstance(linha["dados"], dict)
        assert re.match(r"\d{4}-\d\d-\d\dT", linha["t"])
    assert log[0]["evento"] == "inicio" and log[-1]["evento"] == "fim"
    # sample mode: nenhuma chamada de LLM e nenhum modelo registrado
    assert not [l for l in log if l["evento"] == "llm_call" or l["modelo"]]
    # as decisões dos agentes aparecem no log
    eventos = {(l["agente"], l["evento"]) for l in log}
    assert ("planejador", "proposta") in eventos
    assert any(a == "critico" and e in ("aprova", "rejeita", "escala") for a, e in eventos)


def test_mesma_entrada_mesmo_plano(arvore, execucoes, tmp_path):
    """Sample mode é determinístico: repetir a entrada repete o plano."""
    nome = CENARIOS[0].stem
    r = rodar(arvore, arvore / "cenarios" / CENARIOS[0].name, tmp_path)
    assert pares(r) == pares(execucoes[nome])


# ----------------------------------------------------------------------------- anti-trapaça: a saída segue a entrada

def test_tres_cenarios_geram_planos_diferentes(execucoes):
    planos = {n: frozenset(pares(r)) for n, r in execucoes.items()}
    assert len(set(planos.values())) == len(planos), planos
    n = {k: len(v) for k, v in planos.items()}
    # mais recursos -> pelo menos tantas designações quanto o cenário mais escasso
    assert n["tocantins-folgado"] >= n["tocantins-escasso"], n
    reservas = {k: len(r["plano_json"]["plano"]["reserva"]) for k, r in execucoes.items()}
    for k, r in execucoes.items():
        cen = yaml.safe_load((RAIZ / "cenarios" / f"{k}.yaml").read_text(encoding="utf-8"))
        assert reservas[k] >= cen["reserva"] or r["plano_json"]["escalacoes"], (k, reservas)


def test_recurso_indisponivel_sai_do_plano(arvore, execucoes, tmp_path):
    base = arvore / "cenarios" / "tocantins-escasso.yaml"
    antes = execucoes["tocantins-escasso"]
    alvo = ids_designados(antes)[0]
    cam = escrever_cenario(arvore, base, "sem-" + alvo, recursos=lambda rs: [
        {**x, "disponivel": False} if x["id"] == alvo else x for x in rs])
    depois = rodar(arvore, cam, tmp_path)
    assert alvo not in ids_designados(depois)
    assert pares(depois) != pares(antes)
    checar_coerencia(depois, yaml.safe_load(cam.read_text(encoding="utf-8")))


def test_reserva_maior_segura_recursos(arvore, execucoes, tmp_path):
    base = arvore / "cenarios" / "tocantins-folgado.yaml"
    antes = execucoes["tocantins-folgado"]
    cen = yaml.safe_load(base.read_text(encoding="utf-8"))
    nova = cen["reserva"] + 3
    cam = escrever_cenario(arvore, base, "reserva-maior", reserva=nova)
    depois = rodar(arvore, cam, tmp_path)
    assert len(depois["plano_json"]["plano"]["reserva"]) >= nova
    assert len(ids_designados(depois)) < len(ids_designados(antes))
    checar_coerencia(depois, yaml.safe_load(cam.read_text(encoding="utf-8")))


def test_um_unico_recurso_gera_no_maximo_uma_designacao(arvore, tmp_path):
    base = arvore / "cenarios" / "tocantins-medio.yaml"
    cam = escrever_cenario(arvore, base, "um-recurso", reserva=0,
                           recursos=lambda rs: [x for x in rs if x["tipo"] == "aereo"][:1])
    r = rodar(arvore, cam, tmp_path)
    assert len(ids_designados(r)) <= 1
    checar_coerencia(r, yaml.safe_load(cam.read_text(encoding="utf-8")))


def test_outro_periodo_usa_outras_ocorrencias(arvore, execucoes, tmp_path):
    """--periodo diferente lê outro dia do cache: ocorrências e plano mudam."""
    antes = execucoes["tocantins-medio"]
    r = rodar(arvore, arvore / "cenarios" / "tocantins-medio.yaml", tmp_path, "--periodo", "2026-10-22")
    assert r["pasta"].name == "2026-10-22"
    assert r["plano_json"]["plano"]["periodo"] == "2026-10-22"
    ids_antes = {o["id"] for o in antes["plano_json"]["ocorrencias"]}
    ids_depois = {o["id"] for o in r["plano_json"]["ocorrencias"]}
    assert ids_antes != ids_depois
    assert pares(r) != pares(antes)
    from app.data.repositorio import RepositorioCache
    do_dia = {o.id for o in RepositorioCache(raiz=arvore / "data" / "cache").ocorrencias("tocantins", "2026-10-22", top=1000)}
    assert ids_depois <= do_dia


def test_base_movida_muda_eta(arvore, execucoes, tmp_path):
    """Mudar a posição de uma base da lista oficial (config/regioes/<regiao>_bases_oficiais.csv) muda o ETA
    calculado (não é texto pronto). A cópia do CSV na árvore é restaurada no fim."""
    import csv as _csv
    base = arvore / "cenarios" / "tocantins-escasso.yaml"
    antes = execucoes["tocantins-escasso"]
    cen = yaml.safe_load(base.read_text(encoding="utf-8"))
    por_rec = {x["id"]: x["base_id"] for x in cen["recursos"]}
    arq = arvore / "config" / "regioes" / "tocantins_bases_oficiais.csv"
    original = arq.read_text(encoding="utf-8")
    linhas = list(_csv.DictReader(original.splitlines()))
    ids_oficiais = {l["id"] for l in linhas if l["id"] != "osm_n5067657890"}  # Palmas também está no OSM
    d0 = next(d for d in antes["plano_json"]["plano"]["designacoes"] if por_rec[d["recurso_id"]] in ids_oficiais)
    base_id = por_rec[d0["recurso_id"]]
    try:
        with arq.open("w", encoding="utf-8", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=list(linhas[0]))
            w.writeheader()
            for l in linhas:
                if l["id"] == base_id:
                    l = {**l, "lat": float(l["lat"]) + 0.5, "lon": float(l["lon"]) + 0.5}
                w.writerow(l)
        depois = rodar(arvore, base, tmp_path)
    finally:
        arq.write_text(original, encoding="utf-8")
    eta = {(d["recurso_id"], d["ocorrencia_id"]): d["eta_h"] for d in depois["plano_json"]["plano"]["designacoes"]}
    chave = (d0["recurso_id"], d0["ocorrencia_id"])
    assert chave not in eta or eta[chave] != d0["eta_h"], (chave, d0["eta_h"])


# ----------------------------------------------------------------------------- nota (memória) e aprovar

@pytest.fixture(scope="module")
def com_nota(arvore, tmp_path_factory) -> dict:
    """`nota` em --sample bloqueando a base de um recurso que o plano usa, e depois um novo `run`."""
    cen = arvore / "cenarios" / "tocantins-escasso.yaml"
    antes = rodar(arvore, cen, tmp_path_factory.mktemp("antes-nota"))
    texto = "base de São Félix alagada, sem acesso por terra"
    p = cli(arvore, "nota", "--sample", "--regiao", "tocantins", "--periodo", "2026-10-23", "--autor", "qa",
            "--pasta-logs", str(tmp_path_factory.mktemp("logs-nota")), texto)
    depois = rodar(arvore, cen, tmp_path_factory.mktemp("depois-nota"))
    return {"antes": antes, "depois": depois, "texto": texto, "saida_nota": p.stdout}


def test_nota_persiste_em_disco(arvore, com_nota):
    assert "Nota registrada" in com_nota["saida_nota"]
    mem = arvore / "data" / "estado" / "memoria_tocantins.json"
    assert com_nota["texto"] in mem.read_text(encoding="utf-8")
    notas = arvore / "data" / "estado" / "tocantins" / "notas.jsonl"
    assert com_nota["texto"] in notas.read_text(encoding="utf-8")
    from app.memory_client import MemoriaLocal
    textos = [m.texto for m in MemoriaLocal(caminho=mem).listar("tocantins")]
    assert com_nota["texto"] in textos


def test_nota_aparece_no_run_seguinte(com_nota):
    depois = com_nota["depois"]
    lidas = [l["dados"] for l in depois["log"] if l["evento"] == "memoria_lida"]
    ativas = [m for d in lidas for m in d.get("ativas", [])]
    assert any(com_nota["texto"] in json.dumps(m, ensure_ascii=False) for m in ativas), lidas
    assert any(com_nota["texto"] == m["texto"] for m in depois["plano_json"]["memorias_usadas"])
    # a nota bloqueia a base de São Félix (Prevfogo): o recurso de lá não sai por terra
    assert "saofelix-t1" not in ids_designados(depois)
    # regressão: a escalação pela memória não pode esconder as ocorrências expostas sem recurso
    designadas = {d["ocorrencia_id"] for d in depois["plano_json"]["plano"]["designacoes"]}
    escaladas = {e["ocorrencia_id"] for e in depois["plano_json"]["escalacoes"]}
    expostas_sem_recurso = {o["id"] for o in depois["plano_json"]["ocorrencias"]
                            if o["pop_raio"] > 0 and o["id"] not in designadas}
    assert expostas_sem_recurso <= escaladas, expostas_sem_recurso - escaladas


def test_aprovar_grava_decisoes(arvore, tmp_path):
    saida = tmp_path / "s"
    r = rodar(arvore, arvore / "cenarios" / "tocantins-medio.yaml", saida)
    p = cli(arvore, "aprovar", "--sample", "--regiao", "tocantins", "--periodo", "2026-10-23", "--autor", "qa",
            "--saida", str(saida / "out"), "--pasta-logs", str(tmp_path / "logs-aprovar"))
    assert "aprovado por qa" in p.stdout
    linhas = [json.loads(l) for l in (arvore / "data" / "estado" / "tocantins" / "decisoes.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
    gravadas = {(l.get("recurso_id"), l.get("ocorrencia_id")) for l in linhas if l.get("aprovado_por") == "qa"}
    assert pares(r) <= gravadas, (pares(r), gravadas)
    log = [json.loads(l) for f in (tmp_path / "logs-aprovar").glob("*.jsonl") for l in f.read_text().splitlines()]
    assert [l for l in log if l["evento"] == "aprova" and set(l) == CAMPOS_LOG]


def test_aprovar_sem_plano_falha_com_mensagem(arvore, tmp_path):
    p = cli(arvore, "aprovar", "--sample", "--regiao", "tocantins", "--periodo", "2026-10-19",
            "--saida", str(tmp_path / "vazio"), ok=False)
    assert p.returncode == 2 and "Não há plano salvo" in p.stderr


# ----------------------------------------------------------------------------- anti-trapaça: código

def _literais_de_codigo(arq: Path) -> list[tuple[int, str]]:
    """Strings do código (exceto docstrings e comentários)."""
    arvore = ast.parse(arq.read_text(encoding="utf-8"))
    docstrings = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and no.body:
            primeiro = no.body[0]
            if isinstance(primeiro, ast.Expr) and isinstance(primeiro.value, ast.Constant):
                docstrings.add(id(primeiro.value))
    return [(no.lineno, no.value) for no in ast.walk(arvore)
            if isinstance(no, ast.Constant) and isinstance(no.value, str) and id(no) not in docstrings]


PROIBIDOS_EM_LITERAIS = {
    "id de célula fixo": re.compile(r"cel_-?\d+_-?\d+"),
    "nome de cenário": re.compile(r"escasso|folgado|\bmedio\b|tocantins-|iberia-"),
    "data fixa": re.compile(r"\b20\d\d-\d\d-\d\d\b"),
    "saída pronta": re.compile(r"output_examples|input_examples"),
}


def test_codigo_sem_literais_de_demo():
    achados = []
    for arq in sorted((RAIZ / "app").rglob("*.py")):
        for linha, s in _literais_de_codigo(arq):
            for motivo, rx in PROIBIDOS_EM_LITERAIS.items():
                if rx.search(s):
                    achados.append(f"{arq.relative_to(RAIZ)}:{linha} [{motivo}] {s[:80]!r}")
    assert not achados, "\n".join(achados)


def test_codigo_sem_comparacao_com_cenario_ou_celula():
    """Procura `if x == "<constante>"` em que a constante parece cenário, período ou célula."""
    rx = re.compile(r"""(==|!=|\bin\b)\s*[\(\[{]?\s*["'](cel_|tocantins|iberia|20\d\d-)""")
    achados = []
    for arq in sorted((RAIZ / "app").rglob("*.py")):
        for i, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
            if rx.search(linha.split("#")[0]):
                achados.append(f"{arq.relative_to(RAIZ)}:{i}: {linha.strip()}")
    assert not achados, "\n".join(achados)


def test_sem_chamada_direta_a_nvidia_ou_outro_provedor():
    rx = re.compile(r"integrate\.api\.nvidia\.com|build\.nvidia\.com|nvapi-|api\.openai\.com|"
                    r"api\.anthropic\.com|generativelanguage\.googleapis|^\s*(import|from)\s+(openai|anthropic)\b",
                    re.I | re.M)
    achados = [f"{a.relative_to(RAIZ)}: {m.group(0)}" for a in sorted((RAIZ / "app").rglob("*.py"))
               for m in rx.finditer(a.read_text(encoding="utf-8"))]
    assert not achados, achados


def test_so_o_cliente_llm_faz_http_para_llm():
    """Só app/llm/client.py monta chamadas /chat/completions."""
    fora = [str(a.relative_to(RAIZ)) for a in (RAIZ / "app").rglob("*.py")
            if "chat/completions" in a.read_text(encoding="utf-8") and a != RAIZ / "app" / "llm" / "client.py"]
    assert not fora, fora


# ----------------------------------------------------------------------------- contratos (docs/CONTRATOS.md)

def _params(f) -> list[tuple[str, object]]:
    return [(p.name, p.default) for p in inspect.signature(f).parameters.values() if p.name != "self"]


VAZIO = inspect.Parameter.empty


def test_contrato_executar_periodo():
    from app.agents.grafo import executar_periodo
    assert _params(executar_periodo) == [
        ("regiao", VAZIO), ("cenario", VAZIO), ("repo", VAZIO), ("memoria", VAZIO), ("log", VAZIO),
        ("modo", "llm"), ("usar_critico_llm", True), ("usar_memoria", True), ("idioma", None)]  # §10/§19


def test_contrato_chat_e_llmresult():
    from app.llm.client import LLMResult, chat
    ps = _params(chat)
    assert ps[:3] == [("messages", VAZIO), ("papel", VAZIO), ("json_schema", None)]
    assert all(d is not VAZIO for _, d in ps[3:]), "parâmetros extras de chat() precisam ter padrão"
    assert set(LLMResult.__dataclass_fields__) == {"texto", "json", "modelo", "routed_model", "receipt",
                                                   "tokens", "latencia_s"}


REPOSITORIO = {
    "ocorrencias": [("regiao", VAZIO), ("periodo", VAZIO), ("top", 15)],
    "bases": [("regiao", VAZIO)],
    "historico_celula": [("ocorrencia_id", VAZIO), ("dias", 7)],
    "salvar_decisoes": [("plano", VAZIO), ("aprovado_por", VAZIO)],
    "salvar_nota": [("regiao", VAZIO), ("periodo", VAZIO), ("texto", VAZIO), ("autor", VAZIO)],
}
MEMORIA = {
    "gravar": [("regiao", VAZIO), ("texto", VAZIO), ("tipo", VAZIO), ("fonte", VAZIO),
               ("confianca", 1.0), ("supersedes", None)],
    "recall": [("regiao", VAZIO), ("consulta", VAZIO), ("k", 5)],
    "listar": [("regiao", VAZIO)],
}


@pytest.mark.parametrize("classe", ["Repositorio", "RepositorioCache", "RepositorioZetaris"])
def test_contrato_repositorio(classe):
    from app.data import repositorio
    cls = getattr(repositorio, classe)
    for metodo, esperado in REPOSITORIO.items():
        assert _params(getattr(cls, metodo)) == esperado, f"{classe}.{metodo}"


@pytest.mark.parametrize("classe", ["ClienteMemoria", "MemoriaLocal", "ClienteHMEM"])
def test_contrato_cliente_memoria(classe):
    from app import memory_client
    cls = getattr(memory_client, classe)
    for metodo, esperado in MEMORIA.items():
        assert _params(getattr(cls, metodo)) == esperado, f"{classe}.{metodo}"


def test_protocolos_locais_do_grafo_batem_com_os_oficiais():
    from app.agents import grafo
    for metodo in ("ocorrencias", "bases", "historico_celula"):
        assert _params(getattr(grafo.Repositorio, metodo)) == REPOSITORIO[metodo]
    for metodo, esperado in MEMORIA.items():
        assert _params(getattr(grafo.ClienteMemoria, metodo)) == esperado


def test_construtores_usados_pela_cli():
    from app.data.repositorio import RepositorioCache, RepositorioZetaris
    from app.memory_client import ClienteHMEM, MemoriaLocal
    RepositorioCache()
    # sem ZETARIS_REST_URL/API_KEY o construtor recusa (a CLI cai no cache); com eles, não conecta ainda
    RepositorioZetaris(rest_url="http://zetaris.invalid", api_key="placeholder", dsn="postgresql://x@invalid/x")
    MemoriaLocal()
    ClienteHMEM("http://127.0.0.1:7070").close()


CAMPOS_MODELOS = {
    "Ocorrencia": {"id", "lat", "lon", "n_focos", "frp_soma", "frp_max", "primeiro", "ultimo", "periodos_seguidos",
                   "status", "pop_raio", "dist_ti_uc_km", "vpd_kpa", "vento_kmh", "prioridade", "componentes",
                   "localidades"},
    "Base": {"id", "nome", "lat", "lon"},
    "Recurso": {"id", "base_id", "tipo", "capacidade", "disponivel"},
    "Designacao": {"recurso_id", "ocorrencia_id", "ordem", "eta_h", "justificativa", "evidencias"},
    "Plano": {"periodo", "regiao", "designacoes", "reserva", "nao_atendidas", "resumo", "rodada"},
    "Violacao": {"regra", "ocorrencia_id", "recurso_id", "evidencia", "sugestao", "rigida"},
    "ParecerAnalista": {"ocorrencia_id", "pergunta", "conclusao", "confianca", "evidencias", "consultas"},
    "VeredictoCritico": {"decisao", "motivos", "contra_proposta", "pedir_analista"},
    "Memoria": {"id", "regiao", "texto", "tipo", "fonte", "confianca", "supersedes", "criada_em"},
    "Cenario": {"regiao", "periodo", "recursos", "bases", "reserva", "notas", "simulado"},
    "ResultadoPeriodo": {"plano", "log_path"},
}


@pytest.mark.parametrize("nome", sorted(CAMPOS_MODELOS))
def test_contrato_modelos_tem_os_campos(nome):
    from app.core import models
    campos = set(getattr(models, nome).model_fields)
    assert CAMPOS_MODELOS[nome] <= campos, CAMPOS_MODELOS[nome] - campos
