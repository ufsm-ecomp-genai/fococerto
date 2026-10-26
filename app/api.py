"""API HTTP do FocoCerto para o front-end (contrato em web/README.md).

    uvicorn app.api:app --port 8000

Só lê e escreve o que a CLI já lê e escreve: reaproveita as funções de ``app/cli.py`` (``cmd_run``,
``cmd_nota``, ``cmd_aprovar``, ``carregar_cenario``) e lê as saídas em ``out/<regiao>/<periodo>/plano.json``.
Nada é inventado aqui: um plano que não existe é 404, e o ``POST /api/run`` roda o mesmo ciclo da CLI.

Configuração por variáveis de ambiente (as mesmas da CLI, mais estas):
- ``FOCOCERTO_SAIDA``: pasta das saídas (padrão ``out/``), a mesma do ``--saida`` da CLI;
- ``FOCOCERTO_CORS_ORIGENS``: regex extra de origens permitidas (padrão: só localhost e 127.0.0.1, qualquer porta);
- ``FOCOCERTO_CENARIOS_DIR``: onde o ``POST /api/cenarios`` grava os cenários montados na tela (padrão
  ``data/estado/cenarios/``, fora do git). Os cenários do repositório (``cenarios/``) nunca são sobrescritos.
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
from app.core.mensagens import IDIOMAS, normalizar_idioma
from app.core.models import Base, Cenario

RE_REGIAO = re.compile(r"^[a-z0-9_-]{1,64}$")
RE_PERIODO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_NOME = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
RE_NOME_CENARIO = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MARGEM_BBOX_GRAUS = 1.0   # base declarada pode ficar até 1° fora da bbox da região (mesma margem das bases do Zetaris)
TTL_BASES_S = 300         # bases conhecidas ficam em memória por 5 min (no Zetaris, cada consulta leva segundos)
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
    recursos: str | None = Field(None, description="caminho do cenário, relativo à raiz (lista em GET /api/cenarios); "
                                                   "use este OU cenario")
    cenario: Cenario | None = Field(None, description="o cenário inteiro (formato de cenarios/*.yaml), montado na "
                                                      "tela; use este OU recursos")
    sample: bool = Field(False, description="igual ao --sample da CLI: cache local, MemoriaLocal, agentes offline")
    idioma: str | None = Field(None, description="idioma do plano inteiro: pt-BR ou en (aceita pt, en-US...); "
                                                 "padrão: FOCOCERTO_IDIOMA ou o idioma da região")


class PedidoSalvarCenario(BaseModel):
    nome: str = Field(..., description="só letras, números, _ e - (vira <nome>.yaml)")
    cenario: Cenario
    sample: bool = Field(False, description="valida as bases contra o cache local (como o --sample)")


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


def _erro(loc: list, msg: str) -> dict:
    """Um erro no mesmo formato dos 422 do FastAPI (lista de {loc, msg, type}): a tela trata os dois igual."""
    return {"loc": ["body", *loc], "msg": msg, "type": "value_error"}


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
            "modo": meta.get("modo"), "idioma": meta.get("idioma"), "simulado": meta.get("simulado"),
            "gerado_em": meta.get("gerado_em"),
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

    def criar(self, pedido: PedidoRun, arq: Path | None, saida: Path, pasta_logs: Path,
              cenario: Cenario | None = None, origem: str | None = None) -> dict:
        jid = uuid.uuid4().hex[:12]
        job = {"id": jid, "status": "na_fila", "pedido": pedido.model_dump(), "criado_em": _agora(),
               "iniciado_em": None, "terminado_em": None, "progresso": [], "erro": None, "resultado": None}
        with self._dados:
            self._jobs[jid] = job
        threading.Thread(target=self._rodar, args=(jid, pedido, arq, saida, pasta_logs, cenario, origem), daemon=True,
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

    def _rodar(self, jid: str, pedido: PedidoRun, arq: Path | None, saida: Path, pasta_logs: Path,
               cenario: Cenario | None = None, origem: str | None = None) -> None:
        with self._trava:
            self._atualizar(jid, status="rodando", iniciado_em=_agora())
            args = argparse.Namespace(comando="run", regiao=pedido.regiao, periodo=pedido.periodo,
                                      recursos=str(arq) if arq else None,
                                      sample=pedido.sample, saida=str(saida), pasta_logs=str(pasta_logs),
                                      idioma=pedido.idioma)
            original = cli.progresso
            llm_provider = os.environ.get("LLM_PROVIDER")
            thread_job = threading.current_thread()

            def progresso(msg: str) -> None:
                # só as mensagens desta execução vão para o job (GET /api/bases pode chamar a CLI ao mesmo tempo)
                if threading.current_thread() is thread_job:
                    self._anotar(jid, msg)
                original(msg)

            t0 = time.monotonic()
            cli.progresso = progresso  # a CLI escreve o progresso por esta função (inclusive o LogComProgresso)
            try:
                if cenario is not None:
                    cli.rodar_cenario(args, cenario, origem)
                    periodo = pedido.periodo or cenario.periodo
                else:
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


def _base_json(b: Base, regiao: str) -> dict:
    """Base com a procedência à vista. Para as da lista oficial, junta órgão, URL e data da fonte do CSV da região."""
    d = {"id": b.id, "nome": b.nome, "lat": b.lat, "lon": b.lon, "confianca": b.confianca, "fonte": b.fonte,
         "simulada": b.simulada}
    extra = _oficiais_por_id(regiao).get(b.id)
    if extra and b.confianca == "oficial":
        d.update({"orgao": extra.get("orgao") or None, "fonte_url": extra.get("fonte") or None,
                  "data_fonte": extra.get("data_fonte") or None, "coordenada": extra.get("coordenada") or None})
    return d


def _oficiais_por_id(regiao: str) -> dict[str, dict]:
    from app.data import fontes
    from app.data.bases import caminho_oficiais
    arq = caminho_oficiais(regiao)
    return {r["id"].strip(): r for r in fontes.ler_csv(arq)} if arq.exists() else {}


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
              repositorio_cache=None, cenarios_dir: str | Path | None = None) -> FastAPI:
    """Fábrica da aplicação. Os parâmetros existem para os testes; em produção vêm do ambiente.

    O ``.env`` (mesmas variáveis da CLI: LLM_PROVIDER, ZETARIS_API_KEY, HMEM_URL...) é lido quando o servidor
    sobe (lifespan), não no import: importar este módulo não muda o ambiente do processo."""
    cfg_api = ler_config_api()
    pastas_cenarios = list(cfg_api["pastas_cenarios"])
    saida = Path(saida or os.environ.get("FOCOCERTO_SAIDA") or RAIZ / "out")
    exemplos = Path(exemplos or RAIZ / (cfg_api.get("exemplos") or "exemplos"))
    pasta_logs = Path(pasta_logs or RAIZ / "logs")
    web_dist = Path(web_dist or RAIZ / "web" / "dist")
    cenarios_dir = Path(cenarios_dir or os.environ.get("FOCOCERTO_CENARIOS_DIR") or "data/estado/cenarios")
    if not cenarios_dir.is_absolute():
        cenarios_dir = RAIZ / cenarios_dir
    jobs = Jobs()
    _repo: dict[str, Any] = {"cache": repositorio_cache}
    _bases: dict[tuple[str, bool], tuple[float, dict]] = {}   # (regiao, sample) -> (instante, resposta)
    _trava_bases = threading.Lock()

    def repo_cache():
        if _repo["cache"] is None:
            from app.data.repositorio import RepositorioCache
            _repo["cache"] = RepositorioCache()
        return _repo["cache"]

    # ------------------------------------------------------------------ bases conhecidas e validação do cenário
    def _regiao_configurada(regiao: str) -> None:
        _validar_regiao(regiao)
        if not (RAIZ / "config" / "regioes" / f"{regiao}.yaml").exists():
            raise HTTPException(404, f"Região '{regiao}' não configurada (config/regioes/{regiao}.yaml). "
                                     f"Veja GET /api/regioes.")

    def bases_conhecidas(regiao: str, sample: bool) -> dict:
        """Camadas 2–4 (oficial, OSM, estimada) do mesmo repositório que o ``run`` usaria (``cli.criar_repositorio``:
        cache local no sample mode ou sem ZETARIS_API_KEY; senão Zetaris), mais os dias disponíveis se o repositório
        souber dizer. Fica em memória por TTL_BASES_S."""
        _regiao_configurada(regiao)
        chave = (regiao, bool(sample))
        with _trava_bases:
            em_memoria = _bases.get(chave)
        if em_memoria and time.monotonic() - em_memoria[0] < TTL_BASES_S:
            return em_memoria[1]
        try:
            repo = cli.criar_repositorio(argparse.Namespace(sample=sample, regiao=regiao))
            bases = repo.bases(regiao)
            periodos = repo.periodos_disponiveis(regiao) if hasattr(repo, "periodos_disponiveis") else None
        except FileNotFoundError as e:
            raise HTTPException(404, f"Sem dados para a região '{regiao}': {e}") from e
        except cli.ErroCLI as e:
            raise HTTPException(503, str(e)) from e
        except Exception as e:  # noqa: BLE001 - Zetaris fora do ar, por exemplo
            raise HTTPException(503, f"Não consegui ler as bases de '{regiao}' ({type(e).__name__}: {e}). "
                                     f"Sem Zetaris, use sample=true.") from e
        resp = {"regiao": regiao, "repositorio": type(repo).__name__, "bases": [_base_json(b, regiao) for b in bases],
                "periodos": periodos}
        with _trava_bases:
            _bases[chave] = (time.monotonic(), resp)
        return resp

    def validar_cenario(c: Cenario, sample: bool, regiao_pedido: str | None = None,
                        periodo_pedido: str | None = None) -> Cenario:
        """Regras que o pydantic não pega. Erros juntos, num 422 no formato do FastAPI. Devolve o cenário com as
        bases declaradas marcadas ``confianca="declarada"`` (CONTRATOS §16: a base declarada é a do coordenador)."""
        erros: list[dict] = []
        _regiao_configurada(c.regiao)
        if regiao_pedido and regiao_pedido != c.regiao:
            erros.append(_erro(["cenario", "regiao"], f"O cenário é da região '{c.regiao}', mas o pedido é para "
                                                      f"'{regiao_pedido}'."))
        if not RE_PERIODO.match(c.periodo or ""):
            erros.append(_erro(["cenario", "periodo"], f"Período inválido: {c.periodo!r} (formato AAAA-MM-DD)."))
        conhecidas = bases_conhecidas(c.regiao, sample)
        periodo = periodo_pedido or c.periodo
        disponiveis = conhecidas.get("periodos")
        if disponiveis is not None and RE_PERIODO.match(periodo or "") and periodo not in disponiveis:
            onde = ["periodo"] if periodo_pedido else ["cenario", "periodo"]
            faixa = f"{disponiveis[0]} a {disponiveis[-1]}" if disponiveis else "nenhum"
            erros.append(_erro(onde, f"Não há dados de {periodo} para '{c.regiao}' (dias disponíveis: {faixa}; "
                                     f"lista em GET /api/periodos?regiao={c.regiao})."))
        bbox = config.regiao(c.regiao).bbox
        vistos: set[str] = set()
        for i, b in enumerate(c.bases):
            if not b.id.strip() or not b.nome.strip():
                erros.append(_erro(["cenario", "bases", i], "Base declarada sem id ou sem nome."))
            if b.id in vistos:
                erros.append(_erro(["cenario", "bases", i, "id"], f"Id de base repetido: '{b.id}'."))
            vistos.add(b.id)
            lat_min, lat_max, lon_min, lon_max = bbox
            m = MARGEM_BBOX_GRAUS
            if not (lat_min - m <= b.lat <= lat_max + m and lon_min - m <= b.lon <= lon_max + m):
                erros.append(_erro(["cenario", "bases", i], f"A base '{b.id}' ({b.lat}, {b.lon}) está fora da "
                                                            f"região '{c.regiao}' (bbox {list(bbox)})."))
        ids_bases = {b["id"] for b in conhecidas["bases"]} | vistos
        ids_rec: set[str] = set()
        for i, r in enumerate(c.recursos):
            if not r.id.strip():
                erros.append(_erro(["cenario", "recursos", i, "id"], "Recurso sem id."))
            if r.id in ids_rec:
                erros.append(_erro(["cenario", "recursos", i, "id"], f"Id de recurso repetido: '{r.id}'."))
            ids_rec.add(r.id)
            if r.base_id not in ids_bases:
                erros.append(_erro(["cenario", "recursos", i, "base_id"],
                                   f"A base '{r.base_id}' do recurso '{r.id}' não existe: não está nas bases conhecidas "
                                   f"de '{c.regiao}' (GET /api/bases?regiao={c.regiao}) nem nas declaradas no cenário."))
            if r.capacidade < 1:
                erros.append(_erro(["cenario", "recursos", i, "capacidade"],
                                   f"Capacidade do recurso '{r.id}' deve ser pelo menos 1."))
        if c.reserva < 0:
            erros.append(_erro(["cenario", "reserva"], "A reserva não pode ser negativa."))
        if erros:
            raise HTTPException(422, erros)
        declaradas = [b.model_copy(update={"confianca": "declarada"}) for b in c.bases]
        return c.model_copy(update={"bases": declaradas, "notas": [n for n in c.notas if n.strip()]})

    # ------------------------------------------------------------------ cenários do repositório e salvos
    def cenarios_repositorio() -> list[tuple[str, Path]]:
        """(caminho relativo, arquivo) das duas primeiras pastas de web/api.yaml."""
        return [(f"{pasta}/{arq.name}", arq) for pasta in pastas_cenarios[:2]
                for arq in sorted((RAIZ / pasta).glob("*.yaml"))]

    def _resumo_cenario(d: dict) -> dict:
        return {"regiao": d.get("regiao"), "periodo": str(d.get("periodo")) if d.get("periodo") else None,
                "simulado": d.get("simulado"), "recursos": len(d.get("recursos") or []),
                "bases_declaradas": len(d.get("bases") or []), "reserva": d.get("reserva"),
                "notas": d.get("notas") or []}

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

    @api.get("/api/bases")
    def bases(regiao: str = Query(..., description="nome da região"),
              sample: bool = Query(False, description="força o cache local (como o --sample)")) -> dict:
        """Bases conhecidas da região (oficial, OSM, estimada), já fundidas, com a procedência."""
        return bases_conhecidas(regiao, sample)

    @api.get("/api/cenarios")
    def cenarios() -> list[dict]:
        """Cenários do repositório (as duas primeiras pastas de web/api.yaml; aceitos por caminho no POST /api/run)
        e os salvos pela tela (POST /api/cenarios; carregue com GET /api/cenarios/{nome})."""
        out = []
        for caminho, arq in cenarios_repositorio():
            try:
                d = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError) as e:
                out.append({"caminho": caminho, "nome": arq.stem, "origem": "repositorio", "erro": str(e)})
                continue
            out.append({"caminho": caminho, "nome": arq.stem, "origem": "repositorio", **_resumo_cenario(d)})
        for arq in sorted(cenarios_dir.glob("*.yaml")):
            try:
                d = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError) as e:
                out.append({"caminho": None, "nome": arq.stem, "origem": "salvo", "erro": str(e)})
                continue
            out.append({"caminho": None, "nome": arq.stem, "origem": "salvo", **_resumo_cenario(d),
                        "salvo_em": datetime.fromtimestamp(arq.stat().st_mtime, timezone.utc).isoformat(
                            timespec="seconds")})
        return out

    @api.get("/api/cenarios/{nome}")
    def cenario_por_nome(nome: str) -> dict:
        """O cenário inteiro (formato Cenario), pronto para editar na tela e mandar em POST /api/run."""
        if not RE_NOME_CENARIO.match(nome):
            raise HTTPException(400, f"Nome de cenário inválido: {nome!r} (use letras, números, _ ou -).")
        candidatos = [(caminho, arq, "repositorio") for caminho, arq in cenarios_repositorio() if arq.stem == nome]
        candidatos.append((None, cenarios_dir / f"{nome}.yaml", "salvo"))
        for caminho, arq, origem in candidatos:
            if arq.exists():
                try:
                    c = cli.carregar_cenario(arq)
                except cli.ErroCLI as e:
                    raise HTTPException(500, str(e)) from e
                return {"nome": nome, "origem": origem, "caminho": caminho, "cenario": c.model_dump()}
        raise HTTPException(404, f"Cenário '{nome}' não existe. Veja GET /api/cenarios.")

    @api.post("/api/cenarios", status_code=201)
    def salvar_cenario(pedido: PedidoSalvarCenario) -> dict:
        """Grava o cenário montado na tela em FOCOCERTO_CENARIOS_DIR/<nome>.yaml, depois de validar. Não
        sobrescreve cenário do repositório; um salvo com o mesmo nome é substituído."""
        nome = pedido.nome
        if not RE_NOME_CENARIO.match(nome or ""):
            raise HTTPException(400, f"Nome de cenário inválido: {nome!r} (use só letras, números, _ ou -; até 64).")
        do_repo = [caminho for caminho, arq in cenarios_repositorio() if arq.stem == nome]
        if do_repo:
            raise HTTPException(409, f"'{nome}' é um cenário do repositório ({do_repo[0]}) e não pode ser "
                                     f"sobrescrito. Escolha outro nome.")
        c = validar_cenario(pedido.cenario, pedido.sample)
        arq = cenarios_dir / f"{nome}.yaml"
        substituido = arq.exists()
        cenarios_dir.mkdir(parents=True, exist_ok=True)
        cabecalho = (f"# Cenário salvo pela tela (POST /api/cenarios) em {_agora()}.\n"
                     f"# simulado: {str(c.simulado).lower()}; bases declaradas = informadas pelo coordenador.\n")
        arq.write_text(cabecalho + yaml.safe_dump(c.model_dump(), allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        return {"ok": True, "nome": nome, "origem": "salvo", "substituido": substituido,
                "url": f"/api/cenarios/{nome}"}

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
        if pedido.idioma and not normalizar_idioma(pedido.idioma):
            raise HTTPException(400, f"Idioma não suportado: {pedido.idioma!r}. Use um de {', '.join(IDIOMAS)} "
                                     f"(ex.: en, en-US, pt, pt-BR).")
        if (pedido.recursos is None) == (pedido.cenario is None):
            raise HTTPException(422, [_erro(["recursos"], "Mande o caminho do cenário em 'recursos' OU o cenário "
                                                          "inteiro em 'cenario' (um dos dois).")])
        if pedido.cenario is not None:
            cenario = validar_cenario(pedido.cenario, pedido.sample, pedido.regiao, pedido.periodo)
            job = jobs.criar(pedido, None, saida, pasta_logs, cenario=cenario,
                             origem="cenário da tela (POST /api/run)")
            return {"job_id": job["id"], "status": job["status"], "url": f"/api/jobs/{job['id']}"}
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
