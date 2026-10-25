"""API HTTP do FocoCerto para o front-end (contrato em web/README.md).

    uvicorn app.api:app --port 8000

Só lê e escreve o que a CLI já lê e escreve: reaproveita as funções de ``app/cli.py`` (``cmd_run``,
``cmd_nota``, ``cmd_aprovar``, ``carregar_cenario``) e lê as saídas em ``out/<regiao>/<periodo>/plano.json``.
Nada é inventado aqui: um plano que não existe é 404, e o ``POST /api/run`` roda o mesmo ciclo da CLI.

Configuração por variáveis de ambiente (as mesmas da CLI, mais estas):
- ``FOCOCERTO_SAIDA``: pasta das saídas (padrão ``out/``), a mesma do ``--saida`` da CLI;
- ``FOCOCERTO_CORS_ORIGENS``: regex extra de origens permitidas (padrão: só localhost e 127.0.0.1, qualquer porta).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import cli
from app.core import config
from app.core.config import RAIZ

RE_REGIAO = re.compile(r"^[a-z0-9_-]{1,64}$")
RE_PERIODO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_NOME = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
CORS_PADRAO = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
CONFIG_API = RAIZ / "web" / "api.yaml"


def ler_config_api(caminho: Path = CONFIG_API) -> dict:
    """Pasta dos exemplos e pastas de cenários aceitas (web/api.yaml; variáveis de ambiente sobrescrevem).
    Ficam em configuração, não no código: o servidor só sabe onde procurar, não o que tem lá."""
    cfg = yaml.safe_load(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    cfg = cfg or {}
    if os.environ.get("FOCOCERTO_EXEMPLOS"):
        cfg["exemplos"] = os.environ["FOCOCERTO_EXEMPLOS"]
    if os.environ.get("FOCOCERTO_PASTAS_CENARIOS"):
        cfg["pastas_cenarios"] = [x.strip() for x in os.environ["FOCOCERTO_PASTAS_CENARIOS"].split(",") if x.strip()]
    cfg.setdefault("pastas_cenarios", ["cenarios"])
    return cfg


# ----------------------------------------------------------------------------- corpos das requisições
class PedidoRun(BaseModel):
    regiao: str
    periodo: str | None = Field(None, description="AAAA-MM-DD; padrão: o período do cenário")
    recursos: str = Field(..., description="caminho do cenário, relativo à raiz (lista em GET /api/cenarios)")
    sample: bool = Field(False, description="igual ao --sample da CLI: cache local, MemoriaLocal, agentes offline")


class PedidoNota(BaseModel):
    regiao: str
    periodo: str | None = None
    texto: str
    autor: str
    sample: bool = False


class PedidoAprovar(BaseModel):
    regiao: str
    periodo: str
    autor: str
    sample: bool = False


# ----------------------------------------------------------------------------- utilidades
def _validar_regiao(regiao: str) -> str:
    if not RE_REGIAO.match(regiao or ""):
        raise HTTPException(400, f"Região inválida: {regiao!r} (use letras minúsculas, números, _ ou -).")
    return regiao


def _validar_periodo(periodo: str | None, obrigatorio: bool = True) -> str | None:
    if periodo is None and not obrigatorio:
        return None
    if not RE_PERIODO.match(periodo or ""):
        raise HTTPException(400, f"Período inválido: {periodo!r} (formato AAAA-MM-DD).")
    return periodo


def _ler_json(arq: Path) -> Any:
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise HTTPException(500, f"Não consegui ler {arq.name}: {type(e).__name__}: {e}") from e


def _resumo_plano(d: dict) -> dict:
    """Cabeçalho de um plano.json (para listas)."""
    meta = d.get("meta") or {}
    plano = d.get("plano") or {}
    return {"regiao": meta.get("regiao") or plano.get("regiao"), "periodo": meta.get("periodo") or plano.get("periodo"),
            "modo": meta.get("modo"), "simulado": meta.get("simulado"), "gerado_em": meta.get("gerado_em"),
            "aprovacao_humana": meta.get("aprovacao_humana"), "status": d.get("status"),
            "designacoes": len(plano.get("designacoes") or []), "escalacoes": len(d.get("escalacoes") or []),
            "ocorrencias": len(d.get("ocorrencias") or []), "rodadas": d.get("rodadas")}


def _resolver_cenario(caminho: str, pastas: list[str]) -> Path:
    """Caminho do cenário, relativo à raiz, dentro de uma das pastas permitidas (web/api.yaml)."""
    p = Path(caminho)
    arq = (p if p.is_absolute() else RAIZ / p).resolve()
    permitidas = [(RAIZ / d).resolve() for d in pastas]
    if arq.suffix not in (".yaml", ".yml") or not any(arq.is_relative_to(d) for d in permitidas):
        raise HTTPException(400, f"recursos deve ser um .yaml em {', '.join(pastas)} (recebido {caminho!r}).")
    if not arq.exists():
        raise HTTPException(404, f"Cenário não encontrado: {caminho}")
    return arq


# ----------------------------------------------------------------------------- jobs (POST /api/run)
class Jobs:
    """Fila de execuções em threads. Uma execução por vez (``_trava``): a CLI muda ``os.environ`` no sample
    mode e escreve o progresso por uma função global, então duas execuções simultâneas se misturariam."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._trava = threading.Lock()   # serializa as execuções
        self.trava_stdout = threading.Lock()  # nota/aprovar capturam o stdout da CLI por um instante
        self._dados = threading.Lock()   # protege o dicionário de jobs

    def criar(self, pedido: PedidoRun, arq: Path, saida: Path, pasta_logs: Path) -> dict:
        jid = uuid.uuid4().hex[:12]
        job = {"id": jid, "status": "na_fila", "pedido": pedido.model_dump(), "criado_em": _agora(),
               "iniciado_em": None, "terminado_em": None, "progresso": [], "erro": None, "resultado": None}
        with self._dados:
            self._jobs[jid] = job
        threading.Thread(target=self._rodar, args=(jid, pedido, arq, saida, pasta_logs), daemon=True,
                         name=f"fococerto-job-{jid}").start()
        return self.ver(jid)

    def ver(self, jid: str) -> dict | None:
        with self._dados:
            j = self._jobs.get(jid)
            return None if j is None else json.loads(json.dumps(j))  # cópia

    def listar(self) -> list[dict]:
        with self._dados:
            return [{k: j[k] for k in ("id", "status", "criado_em", "terminado_em", "erro")} | {"pedido": j["pedido"]}
                    for j in sorted(self._jobs.values(), key=lambda x: x["criado_em"], reverse=True)]

    def _atualizar(self, jid: str, **campos) -> None:
        with self._dados:
            self._jobs[jid].update(campos)

    def _anotar(self, jid: str, msg: str) -> None:
        with self._dados:
            self._jobs[jid]["progresso"].append({"t": _agora(), "msg": msg})

    def _rodar(self, jid: str, pedido: PedidoRun, arq: Path, saida: Path, pasta_logs: Path) -> None:
        with self._trava:
            self._atualizar(jid, status="rodando", iniciado_em=_agora())
            args = argparse.Namespace(comando="run", regiao=pedido.regiao, periodo=pedido.periodo, recursos=str(arq),
                                      sample=pedido.sample, saida=str(saida), pasta_logs=str(pasta_logs))
            original = cli.progresso
            llm_provider = os.environ.get("LLM_PROVIDER")

            def progresso(msg: str) -> None:
                self._anotar(jid, msg)
                original(msg)

            t0 = time.monotonic()
            cli.progresso = progresso  # a CLI escreve o progresso por esta função (inclusive o LogComProgresso)
            try:
                cli.cmd_run(args)
                periodo = pedido.periodo or cli.carregar_cenario(arq).periodo
                arq_plano = saida / pedido.regiao / periodo / "plano.json"
                d = json.loads(arq_plano.read_text(encoding="utf-8"))
                self._atualizar(jid, status="concluido", resultado={
                    **_resumo_plano(d), "plano_url": f"/api/plano/{pedido.regiao}/{periodo}",
                    "duracao_s": round(time.monotonic() - t0, 2)})
            except cli.ErroCLI as e:
                self._atualizar(jid, status="erro", erro=str(e))
            except Exception as e:  # noqa: BLE001 - o erro vai para o job, não derruba o servidor
                self._atualizar(jid, status="erro", erro=f"{type(e).__name__}: {e}",
                                traceback=traceback.format_exc(limit=8))
            finally:
                cli.progresso = original
                # o sample mode da CLI fixa LLM_PROVIDER=offline no processo; o servidor volta ao valor anterior
                if llm_provider is None:
                    os.environ.pop("LLM_PROVIDER", None)
                else:
                    os.environ["LLM_PROVIDER"] = llm_provider
                self._atualizar(jid, terminado_em=_agora())


def _relativo(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(RAIZ))
    except ValueError:
        return str(p)


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------------------- app
def criar_app(saida: str | Path | None = None, exemplos: str | Path | None = None,
              pasta_logs: str | Path | None = None, web_dist: str | Path | None = None,
              repositorio_cache=None) -> FastAPI:
    """Fábrica da aplicação. Os parâmetros existem para os testes; em produção vêm do ambiente.

    O ``.env`` (mesmas variáveis da CLI: LLM_PROVIDER, ZETARIS_API_KEY, HMEM_URL...) é lido quando o servidor
    sobe (lifespan), não no import: importar este módulo não muda o ambiente do processo."""
    cfg_api = ler_config_api()
    pastas_cenarios = list(cfg_api["pastas_cenarios"])
    saida = Path(saida or os.environ.get("FOCOCERTO_SAIDA") or RAIZ / "out")
    exemplos = Path(exemplos or RAIZ / (cfg_api.get("exemplos") or "exemplos"))
    pasta_logs = Path(pasta_logs or RAIZ / "logs")
    web_dist = Path(web_dist or RAIZ / "web" / "dist")
    jobs = Jobs()
    _repo: dict[str, Any] = {"cache": repositorio_cache}

    def repo_cache():
        if _repo["cache"] is None:
            from app.data.repositorio import RepositorioCache
            _repo["cache"] = RepositorioCache()
        return _repo["cache"]

    @contextlib.asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI):
        config.carregar_env()  # sem sobrescrever o ambiente, igual à CLI
        yield

    api = FastAPI(title="FocoCerto API", version="1", lifespan=ciclo_de_vida,
                  description="Planos de prioridade e ordem de recursos entre incêndios simultâneos. "
                              "Contrato para o front-end em web/README.md.")
    origens = CORS_PADRAO
    if os.environ.get("FOCOCERTO_CORS_ORIGENS"):
        origens = f"(?:{CORS_PADRAO})|(?:{os.environ['FOCOCERTO_CORS_ORIGENS']})"
    api.add_middleware(CORSMiddleware, allow_origin_regex=origens, allow_methods=["GET", "POST", "OPTIONS"],
                       allow_headers=["*"])

    @api.get("/api/saude")
    def saude() -> dict:
        return {"ok": True, "saida": str(saida), "exemplos": exemplos.exists(), "web_dist": web_dist.exists()}

    # ------------------------------------------------------------------ regiões e períodos
    @api.get("/api/regioes")
    def regioes() -> list[dict]:
        out = []
        for arq in sorted((RAIZ / "config" / "regioes").glob("*.yaml")):
            try:
                cfg = config.regiao(arq.stem)
            except Exception as e:  # noqa: BLE001 - uma região quebrada não esconde as outras
                out.append({"nome": arq.stem, "erro": f"{type(e).__name__}: {e}"})
                continue
            out.append({"nome": cfg.nome, "idioma": cfg.idioma, "bbox": cfg.bbox, "eta_max_h": cfg.eta_max_h,
                        "raio_exposicao_km": cfg.raio_exposicao_km,
                        "tem_cache": (RAIZ / "data" / "cache" / cfg.nome / "focos.csv").exists(),
                        "planos_salvos": len(list((saida / cfg.nome).glob("*/plano.json")))})
        return out

    @api.get("/api/periodos")
    def periodos(regiao: str = Query(..., description="nome da região")) -> dict:
        _validar_regiao(regiao)
        if not (RAIZ / "config" / "regioes" / f"{regiao}.yaml").exists():
            raise HTTPException(404, f"Região '{regiao}' não configurada (config/regioes/{regiao}.yaml).")
        try:
            cache = repo_cache().periodos_disponiveis(regiao)
            erro_cache = None
        except FileNotFoundError as e:
            cache, erro_cache = [], str(e)
        com_plano = sorted(p.parent.name for p in (saida / regiao).glob("*/plano.json"))
        return {"regiao": regiao, "periodos_cache": cache, "periodos_com_plano": com_plano, "erro_cache": erro_cache}

    @api.get("/api/cenarios")
    def cenarios() -> list[dict]:
        """Arquivos de recursos que o POST /api/run aceita (as duas primeiras pastas de web/api.yaml)."""
        out = []
        for pasta in pastas_cenarios[:2]:
            for arq in sorted((RAIZ / pasta).glob("*.yaml")):
                try:
                    d = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
                except (OSError, yaml.YAMLError) as e:
                    out.append({"caminho": f"{pasta}/{arq.name}", "erro": str(e)})
                    continue
                out.append({"caminho": f"{pasta}/{arq.name}", "nome": arq.stem, "regiao": d.get("regiao"),
                            "periodo": str(d.get("periodo")) if d.get("periodo") else None,
                            "simulado": d.get("simulado"), "recursos": len(d.get("recursos") or []),
                            "reserva": d.get("reserva"), "notas": d.get("notas") or []})
        return out

    # ------------------------------------------------------------------ planos
    @api.get("/api/plano/{regiao}/{periodo}")
    def plano(regiao: str, periodo: str) -> dict:
        _validar_regiao(regiao)
        _validar_periodo(periodo)
        arq = saida / regiao / periodo / "plano.json"
        if not arq.exists():
            raise HTTPException(404, f"Não há plano para {regiao}/{periodo} (esperado em {_relativo(arq)}). "
                                     f"Rode POST /api/run ou: python -m app.cli run --regiao {regiao} "
                                     f"--periodo {periodo} --recursos cenarios/<cenario>.yaml")
        return _ler_json(arq)

    @api.get("/api/exemplos")
    def exemplos_lista() -> list[dict]:
        out = []
        for arq in sorted(exemplos.glob("*/plano.json")):
            out.append({"nome": arq.parent.name, **_resumo_plano(_ler_json(arq)),
                        "tem_trace": (arq.parent / "trace.jsonl").exists()})
        return out

    @api.get("/api/exemplos/{nome}")
    def exemplo(nome: str) -> dict:
        if not RE_NOME.match(nome):
            raise HTTPException(400, f"Nome inválido: {nome!r}")
        arq = exemplos / nome / "plano.json"
        if not arq.exists():
            raise HTTPException(404, f"Exemplo '{nome}' não existe. Veja GET /api/exemplos.")
        return _ler_json(arq)

    @api.get("/api/exemplos/{nome}/trace")
    def exemplo_trace(nome: str, limite: int = Query(500, ge=1, le=5000)) -> list[dict]:
        """Eventos do log JSONL do exemplo (procedência: quem decidiu o quê, com qual modelo)."""
        if not RE_NOME.match(nome):
            raise HTTPException(400, f"Nome inválido: {nome!r}")
        arq = exemplos / nome / "trace.jsonl"
        if not arq.exists():
            raise HTTPException(404, f"Exemplo '{nome}' não tem trace.jsonl.")
        linhas = arq.read_text(encoding="utf-8").splitlines()[:limite]
        return [json.loads(l) for l in linhas if l.strip()]

    # ------------------------------------------------------------------ execução
    @api.post("/api/run", status_code=202)
    def run(pedido: PedidoRun) -> dict:
        _validar_regiao(pedido.regiao)
        _validar_periodo(pedido.periodo, obrigatorio=False)
        arq = _resolver_cenario(pedido.recursos, pastas_cenarios)
        job = jobs.criar(pedido, arq, saida, pasta_logs)
        return {"job_id": job["id"], "status": job["status"], "url": f"/api/jobs/{job['id']}"}

    @api.get("/api/jobs")
    def jobs_lista() -> list[dict]:
        return jobs.listar()

    @api.get("/api/jobs/{jid}")
    def job(jid: str) -> dict:
        j = jobs.ver(jid)
        if j is None:
            raise HTTPException(404, f"Job '{jid}' não existe (os jobs ficam só na memória do servidor).")
        return j

    # ------------------------------------------------------------------ nota e aprovação
    def _chamar_cli(funcao, **campos) -> list[str]:
        """Chama um subcomando da CLI e devolve o que ele imprimiu. Erros da CLI viram 400/404."""
        args = argparse.Namespace(saida=str(saida), pasta_logs=str(pasta_logs), **campos)
        try:
            # não espera a execução em andamento (que pode levar minutos no modo LLM); só serializa a captura
            with jobs.trava_stdout, contextlib.redirect_stdout(io.StringIO()) as buf:
                funcao(args)
        except cli.ErroCLI as e:
            msg = str(e)
            raise HTTPException(404 if msg.startswith("Não há plano") else 400, msg) from e
        return buf.getvalue().splitlines()

    @api.post("/api/nota")
    def nota(pedido: PedidoNota) -> dict:
        _validar_regiao(pedido.regiao)
        _validar_periodo(pedido.periodo, obrigatorio=False)
        if not pedido.texto.strip():
            raise HTTPException(400, "A nota está vazia.")
        if not pedido.autor.strip():
            raise HTTPException(400, "Informe o autor da nota.")
        msgs = _chamar_cli(cli.cmd_nota, regiao=pedido.regiao, periodo=pedido.periodo, autor=pedido.autor,
                           texto=[pedido.texto], sample=pedido.sample)
        mem = next((m.group(1) for l in msgs if (m := re.search(r"com memória (\S+?)\.?$", l))), None)
        return {"ok": True, "regiao": pedido.regiao, "periodo": pedido.periodo, "memoria_id": mem, "mensagens": msgs}

    @api.post("/api/aprovar")
    def aprovar(pedido: PedidoAprovar) -> dict:
        _validar_regiao(pedido.regiao)
        _validar_periodo(pedido.periodo)
        if not pedido.autor.strip():
            raise HTTPException(400, "Informe quem aprova.")
        msgs = _chamar_cli(cli.cmd_aprovar, regiao=pedido.regiao, periodo=pedido.periodo, autor=pedido.autor,
                           sample=pedido.sample)
        return {"ok": True, "regiao": pedido.regiao, "periodo": pedido.periodo, "aprovado_por": pedido.autor,
                "mensagens": msgs}

    # ------------------------------------------------------------------ front-end compilado
    if web_dist.is_dir():
        api.mount("/", StaticFiles(directory=str(web_dist), html=True), name="web")

    api.state.jobs = jobs
    return api


app = criar_app()
