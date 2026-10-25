"""Acesso a dados do FocoCerto (docs/CONTRATOS.md, seção 3).

- RepositorioCache:   lê data/cache/<regiao>/ (sample mode). Lógica real (app/data/ocorrencias.py) sobre
                      dados reais congelados. Decisões e notas vão para data/estado/ (JSONL local).
- RepositorioZetaris: lê pelas views do Zetaris (REST /sql-editor/sqls/run); se as views falharem, busca as
                      tabelas cruas PELO ZETARIS e calcula em Python. Decisões e notas vão direto ao Postgres.
                      ** NÃO TESTADO contra um Zetaris real ** (não havia Zetaris rodando no desenvolvimento).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.core.config import RAIZ, carregar_env
from app.core.config import regiao as carregar_regiao
from app.core.models import Base, Ocorrencia, Plano
from app.data import fontes
from app.data.bases import PASTA_REGIOES, bases_em_camadas, politica_estimadas, bases_osm_de_linhas, bases_oficiais_de_linhas, ler_bases_oficiais
from app.data.geo import centro_celula, dentro_bbox
from app.data.ocorrencias import (dia_anterior, historico, montar_ocorrencias, normalizar_periodo)

CACHE_PADRAO = RAIZ / "data" / "cache"
ESTADO_PADRAO = RAIZ / "data" / "estado"
DIAS_CONTEXTO = 7  # dias anteriores carregados para persistência e crescimento


@runtime_checkable
class Repositorio(Protocol):
    def ocorrencias(self, regiao: str, periodo: str, top: int = 15) -> list[Ocorrencia]: ...
    def bases(self, regiao: str) -> list[Base]: ...
    def historico_celula(self, ocorrencia_id: str, dias: int = 7) -> list[dict]: ...
    def salvar_decisoes(self, plano: Plano, aprovado_por: str) -> None: ...
    def salvar_nota(self, regiao: str, periodo: str, texto: str, autor: str) -> None: ...


def linhas_decisao(plano: Plano, aprovado_por: str) -> list[dict]:
    """Plano -> linhas da tabela `decisoes` (designar / reserva / nao_atendida)."""
    linhas = []
    base = {"regiao": plano.regiao, "periodo": plano.periodo, "aprovado_por": aprovado_por, "rodada": plano.rodada}
    for d in plano.designacoes:
        linhas.append({**base, "ocorrencia_id": d.ocorrencia_id, "recurso_id": d.recurso_id, "acao": "designar",
                       "ordem": d.ordem, "eta_h": d.eta_h, "motivo": d.justificativa,
                       "evidencias": json.dumps(d.evidencias, ensure_ascii=False)})
    for r in plano.reserva:
        linhas.append({**base, "ocorrencia_id": None, "recurso_id": r, "acao": "reserva", "ordem": None,
                       "eta_h": None, "motivo": "mantido em reserva", "evidencias": "[]"})
    for o in plano.nao_atendidas:
        linhas.append({**base, "ocorrencia_id": o, "recurso_id": None, "acao": "nao_atendida", "ordem": None,
                       "eta_h": None, "motivo": "sem recurso disponível neste período", "evidencias": "[]"})
    return linhas


# =========================================================================== cache (sample mode)
class RepositorioCache:
    """Lê os CSVs congelados por scripts/congelar_cache.py. Sem rede, sem Zetaris, sem Postgres."""

    def __init__(self, raiz: Path | str = CACHE_PADRAO, estado: Path | str = ESTADO_PADRAO,
                 pasta_regioes: Path | str = PASTA_REGIOES):
        self.raiz = Path(raiz)
        self.estado = Path(estado)
        self.pasta_regioes = Path(pasta_regioes)  # onde ficam <regiao>_bases_oficiais.csv (camada 2)
        self._dados: dict[str, dict] = {}
        self._ultimo_periodo: dict[str, str] = {}

    # ----------------------------------------------------------------- carga
    def _carregar(self, regiao: str) -> dict:
        if regiao not in self._dados:
            pasta = self.raiz / regiao
            if not (pasta / "focos.csv").exists():
                raise FileNotFoundError(f"Sem cache para a região '{regiao}' em {pasta}. "
                                        f"Rode: python scripts/congelar_cache.py --regiao {regiao}")
            ler = lambda nome: fontes.ler_csv(pasta / nome) if (pasta / nome).exists() else []  # noqa: E731
            self._dados[regiao] = {
                "cfg": carregar_regiao(regiao),
                "focos": fontes.focos_de_csv_cache(ler("focos.csv")),
                "localidades": fontes.localidades_de_csv(ler("localidades.csv")),
                "bases": fontes.bases_de_csv(ler("bases.csv")),
                "clima": fontes.clima_de_csv(ler("clima.csv")),
                "passo_clima": self._passo(pasta, regiao),
            }
        return self._dados[regiao]

    def periodos_disponiveis(self, regiao: str) -> list[str]:
        """Dias (UTC) com focos no cache. Útil para escolher o --periodo do sample mode."""
        return sorted({f["dia"] for f in self._carregar(regiao)["focos"]})

    # ----------------------------------------------------------------- contrato
    def ocorrencias(self, regiao: str, periodo: str, top: int = 15) -> list[Ocorrencia]:
        d = self._carregar(regiao)
        periodo = normalizar_periodo(periodo)
        self._ultimo_periodo[regiao] = periodo
        return montar_ocorrencias(d["focos"], d["localidades"], d["clima"], d["cfg"], periodo, top,
                                  passo_clima=d["passo_clima"])

    def bases(self, regiao: str) -> list[Base]:
        """Camadas 2–4 fundidas (app/data/bases.py): lista oficial da região, OSM e, se nada cobrir a região,
        sedes de município estimadas. As declaradas no cenário (camada 1) o grafo soma."""
        d = self._carregar(regiao)
        return bases_em_camadas(regiao, d["cfg"].bbox, bases_osm_de_linhas(d["bases"]), d["localidades"],
                                pasta=self.pasta_regioes)

    def historico_celula(self, ocorrencia_id: str, dias: int = 7) -> list[dict]:
        regiao = self._regiao_da_celula(ocorrencia_id)
        d = self._carregar(regiao)
        ate = self._ultimo_periodo.get(regiao) or max(f["dia"] for f in d["focos"])
        return historico(d["focos"], ocorrencia_id, ate, dias)

    def salvar_decisoes(self, plano: Plano, aprovado_por: str) -> None:
        agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._anexar(plano.regiao, "decisoes.jsonl",
                     [{**l, "criado_em": agora} for l in linhas_decisao(plano, aprovado_por)])

    def salvar_nota(self, regiao: str, periodo: str, texto: str, autor: str) -> None:
        agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._anexar(regiao, "notas.jsonl",
                     [{"regiao": regiao, "periodo": periodo, "texto": texto, "autor": autor, "criado_em": agora}])

    # ----------------------------------------------------------------- leitura do estado local
    def decisoes_salvas(self, regiao: str) -> list[dict]:
        return self._ler_jsonl(regiao, "decisoes.jsonl")

    def notas_salvas(self, regiao: str) -> list[dict]:
        return self._ler_jsonl(regiao, "notas.jsonl")

    # ----------------------------------------------------------------- internos
    @staticmethod
    def _passo(pasta: Path, regiao: str) -> float:
        meta = pasta / "meta.json"
        if meta.exists():
            passo = json.loads(meta.read_text(encoding="utf-8")).get("passo_clima")
            if passo:
                return float(passo)
        return fontes.passo_clima(regiao)

    def _regiao_da_celula(self, cel_id: str) -> str:
        lat, lon = centro_celula(cel_id)
        candidatas = sorted(p.name for p in self.raiz.iterdir() if (p / "focos.csv").exists())
        for r in candidatas:
            if dentro_bbox(lat, lon, carregar_regiao(r).bbox):
                return r
        raise KeyError(f"Célula {cel_id} fora das regiões em cache: {candidatas}")

    def _anexar(self, regiao: str, nome: str, linhas: list[dict]) -> None:
        pasta = self.estado / regiao
        pasta.mkdir(parents=True, exist_ok=True)
        with (pasta / nome).open("a", encoding="utf-8") as f:
            for l in linhas:
                f.write(json.dumps(l, ensure_ascii=False) + "\n")

    def _ler_jsonl(self, regiao: str, nome: str) -> list[dict]:
        p = self.estado / regiao / nome
        if not p.exists():
            return []
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# =========================================================================== Postgres (escrita)
class EscritaPostgres:
    """Escrita direta no Postgres (o Zetaris é só leitura). Testado contra Postgres 16 local."""

    def __init__(self, dsn: str):
        self.dsn = dsn

    def salvar_decisoes(self, plano: Plano, aprovado_por: str) -> None:
        import psycopg

        linhas = linhas_decisao(plano, aprovado_por)
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO decisoes (regiao, periodo, ocorrencia_id, recurso_id, acao, ordem, eta_h, "
                "aprovado_por, motivo, evidencias, rodada) VALUES (%(regiao)s, %(periodo)s, %(ocorrencia_id)s, "
                "%(recurso_id)s, %(acao)s, %(ordem)s, %(eta_h)s, %(aprovado_por)s, %(motivo)s, %(evidencias)s, "
                "%(rodada)s)", linhas)

    def salvar_nota(self, regiao: str, periodo: str, texto: str, autor: str) -> None:
        import psycopg

        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO notas (regiao, periodo, texto, autor) VALUES (%s, %s, %s, %s)",
                        (regiao, periodo, texto, autor))


# =========================================================================== Zetaris
class ErroZetaris(RuntimeError):
    pass


def linhas_da_resposta(resp) -> list[dict]:
    """Normaliza a resposta do /sql-editor/sqls/run para lista de dicts.

    NÃO TESTADO contra Zetaris real: aceita {"data": [ {col: val} ]}, {"data": {"columns": [...], "rows": [[...]]}}
    e variações com "schema"/"fields". Valores chegam como string (dica confirmada nos chats).
    """
    data = resp.get("data", resp) if isinstance(resp, dict) else resp
    if data is None:
        return []
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        cols = data.get("columns") or data.get("schema") or data.get("fields") or []
        cols = [c.get("name") if isinstance(c, dict) else c for c in cols]
        rows = data.get("rows") or data.get("data") or data.get("records") or []
        out = []
        for r in rows:
            out.append(dict(zip(cols, r)) if isinstance(r, list) else r)
        return out
    raise ErroZetaris(f"Formato de resposta inesperado: {str(resp)[:200]}")


def _f(v) -> float | None:
    return None if v in (None, "", "null", "None", "NaN") else float(v)


def _dt(v) -> datetime:
    return datetime.fromisoformat(str(v).replace(" ", "T").replace("Z", ""))


class RepositorioZetaris:
    """Lê pelo Zetaris (REST) e escreve no Postgres. NÃO TESTADO contra Zetaris real.

    Nomes registrados por scripts/setup_zetaris.py:
      fococerto_pg.focos                  (Postgres, datasource JDBC)
      fococerto_arq.localidades / .bases  (file store CSV)
      fococerto.clima                     (view sobre as tabelas REST do Open-Meteo, com CACHE TABLE)
      fococerto.ocorrencias, .ocorrencias_contexto, .ocorrencias_prioridade, .ocorrencias_localidades
    """

    def __init__(self, rest_url: str | None = None, api_key: str | None = None, org_id: str | None = None,
                 dsn: str | None = None, usar_views: bool = True, timeout: float = 180.0):
        carregar_env()
        self.rest_url = (rest_url or os.environ.get("ZETARIS_REST_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("ZETARIS_API_KEY", "")
        self.org_id = org_id or os.environ.get("ZETARIS_ORG_ID", "1")
        self.escrita = EscritaPostgres(dsn or os.environ.get("POSTGRES_DSN", ""))
        self.usar_views = usar_views
        self.timeout = timeout
        self.consultas: list[str] = []      # SQL enviado (para log/auditoria)
        self.modo_usado: str | None = None  # "views" | "python" (fallback)
        self._ultimo_periodo: str | None = None
        if not self.rest_url or not self.api_key:
            raise ErroZetaris("Defina ZETARIS_REST_URL e ZETARIS_API_KEY (ou use --sample)")

    # ----------------------------------------------------------------- REST
    def sql(self, comando: str, limit: int = 10000) -> list[dict]:
        """Um comando por requisição, sem ponto e vírgula (dica confirmada nos chats)."""
        import httpx

        comando = comando.strip().rstrip(";")
        self.consultas.append(comando)
        r = httpx.post(
            self.rest_url + "/sql-editor/sqls/run",
            json={"queryId": str(uuid.uuid4()), "sql": comando, "source": "SqlEditor", "limit": limit},
            headers={"Authorization": f"Bearer {self.api_key}", "X-Org-ID": self.org_id,
                     "X-Request-ID": str(uuid.uuid4()), "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        if r.status_code >= 400:
            raise ErroZetaris(f"HTTP {r.status_code}: {r.text[:300]}")
        return linhas_da_resposta(r.json() if r.content else None)

    def aquecer_cache(self, regioes: list[str]) -> None:
        """CACHE TABLE nas tabelas REST do Open-Meteo. Rodar no início de cada execução: o cache do Spark
        se perde quando o Zetaris reinicia (dica confirmada nos chats)."""
        for r in regioes:
            self.sql(f"CACHE TABLE fococerto_rest.clima_{r}_raw")

    # ----------------------------------------------------------------- contrato
    def ocorrencias(self, regiao: str, periodo: str, top: int = 15) -> list[Ocorrencia]:
        cfg = carregar_regiao(regiao)
        periodo = normalizar_periodo(periodo)
        self._ultimo_periodo = periodo
        if self.usar_views:
            try:
                ocs = self._ocorrencias_views(regiao, periodo, top)
                self.modo_usado = "views"
                return ocs
            except (ErroZetaris, KeyError, ValueError) as e:  # cai para o cálculo em Python
                self.erro_views = str(e)
        self.modo_usado = "python"
        lat_min, lat_max, lon_min, lon_max = cfg.bbox
        inicio = dia_anterior(periodo, DIAS_CONTEXTO)
        focos = self.sql(
            "SELECT id, lat, lon, data_hora_utc, satelite, confianca, frp, dia_noite, dia FROM fococerto_pg.focos "
            f"WHERE dia BETWEEN '{inicio}' AND '{periodo}' AND lat BETWEEN {lat_min} AND {lat_max} "
            f"AND lon BETWEEN {lon_min} AND {lon_max}", limit=200000)
        focos = [{**f, "lat": float(f["lat"]), "lon": float(f["lon"]), "frp": _f(f["frp"]) or 0.0,
                  "dia": str(f["dia"])[:10], "data_hora_utc": _dt(f["data_hora_utc"]).isoformat()} for f in focos]
        m = 0.3
        locs = self.sql("SELECT nome, lat, lon, pop FROM fococerto_arq.localidades "
                        f"WHERE lat BETWEEN {lat_min - m} AND {lat_max + m} AND lon BETWEEN {lon_min - m} AND {lon_max + m}",
                        limit=200000)
        locs = [{"nome": l["nome"], "lat": float(l["lat"]), "lon": float(l["lon"]), "pop": int(float(l["pop"]))}
                for l in locs]
        clima = self.sql("SELECT lat, lon, dia, vpd_kpa_max, vento_kmh_max FROM fococerto.clima "
                         f"WHERE regiao = '{regiao}' AND dia = '{periodo}'")
        clima = [{"lat": float(c["lat"]), "lon": float(c["lon"]), "dia": str(c["dia"])[:10],
                  "vpd_kpa_max": _f(c["vpd_kpa_max"]), "vento_kmh_max": _f(c["vento_kmh_max"])} for c in clima]
        return montar_ocorrencias(focos, locs, clima, cfg, periodo, top, passo_clima=fontes.passo_clima(regiao))

    def _ocorrencias_views(self, regiao: str, periodo: str, top: int) -> list[Ocorrencia]:
        linhas = self.sql(
            "SELECT * FROM fococerto.ocorrencias_prioridade "
            f"WHERE regiao = '{regiao}' AND dia = '{periodo}' ORDER BY prioridade DESC, frp_soma DESC, id LIMIT {int(top)}")
        if not linhas:
            return []
        ids = ", ".join(f"'{l['id']}'" for l in linhas)
        locs = self.sql(
            "SELECT id, nome, pop, dist_km FROM fococerto.ocorrencias_localidades "
            f"WHERE dia = '{periodo}' AND id IN ({ids}) ORDER BY id, dist_km")
        por_id: dict[str, list[dict]] = {}
        for l in locs:
            por_id.setdefault(l["id"], []).append(
                {"nome": l["nome"], "pop": int(float(l["pop"])), "dist_km": round(float(l["dist_km"]), 1)})
        out = []
        for l in linhas:
            comp = {k: float(l[f"c_{k}"]) for k in ("exposicao", "intensidade", "tempo", "persistencia", "crescimento")}
            out.append(Ocorrencia(
                id=l["id"], lat=float(l["lat"]), lon=float(l["lon"]), n_focos=int(float(l["n_focos"])),
                frp_soma=float(l["frp_soma"]), frp_max=float(l["frp_max"]), primeiro=_dt(l["primeiro"]),
                ultimo=_dt(l["ultimo"]), periodos_seguidos=int(float(l["periodos_seguidos"])),
                pop_raio=int(float(l["pop_raio"] or 0)), dist_ti_uc_km=_f(l.get("dist_ti_uc_km")),
                vpd_kpa=_f(l.get("vpd_kpa")), vento_kmh=_f(l.get("vento_kmh")),
                prioridade=float(l["prioridade"]), componentes=comp, localidades=por_id.get(l["id"], [])[:5]))
        return out

    def bases(self, regiao: str) -> list[Base]:
        lat_min, lat_max, lon_min, lon_max = carregar_regiao(regiao).bbox
        m = 1.0
        filtro = f"lat BETWEEN {lat_min - m} AND {lat_max + m} AND lon BETWEEN {lon_min - m} AND {lon_max + m}"
        linhas = self.sql(f"SELECT id, nome, lat, lon, fonte FROM fococerto_arq.bases WHERE {filtro}")
        # camada 2: lista oficial registrada no Zetaris por scripts/setup_zetaris.py; se a tabela não existir
        # (setup antigo), lê o CSV local de config/regioes/ (fallback registrado em self.erro_bases_oficiais)
        try:
            oficiais = bases_oficiais_de_linhas(self.sql(
                "SELECT id, nome, orgao, lat, lon, fonte, data_fonte, coordenada FROM fococerto_arq.bases_oficiais "
                f"WHERE regiao = '{regiao}'"))
        except ErroZetaris as e:
            self.erro_bases_oficiais = str(e)
            oficiais = ler_bases_oficiais(regiao)
        locs = None
        modo, pop_min = politica_estimadas(regiao)
        if modo == "sempre" or (modo == "auto" and not oficiais and not linhas):
            locs = self.sql(f"SELECT geonameid, nome, lat, lon, pop FROM fococerto_arq.localidades WHERE {filtro} "
                            f"AND pop >= {int(pop_min)}")
        return bases_em_camadas(regiao, (lat_min, lat_max, lon_min, lon_max), bases_osm_de_linhas(linhas), locs,
                                oficiais=oficiais)

    def historico_celula(self, ocorrencia_id: str, dias: int = 7) -> list[dict]:
        _, i, j = ocorrencia_id.split("_")
        i, j = int(i), int(j)
        ate = self._ultimo_periodo or datetime.now(timezone.utc).date().isoformat()
        inicio = dia_anterior(ate, dias - 1)
        focos = self.sql(
            "SELECT id, lat, lon, frp, dia_noite, dia FROM fococerto_pg.focos "
            f"WHERE dia BETWEEN '{inicio}' AND '{ate}' "
            f"AND lat >= {i / 10 - 0.001} AND lat < {(i + 1) / 10 + 0.001} "
            f"AND lon >= {j / 10 - 0.001} AND lon < {(j + 1) / 10 + 0.001}")
        focos = [{"id": f["id"], "lat": float(f["lat"]), "lon": float(f["lon"]), "frp": _f(f["frp"]) or 0.0,
                  "dia_noite": f["dia_noite"], "dia": str(f["dia"])[:10]} for f in focos]
        return historico(focos, ocorrencia_id, ate, dias)

    def salvar_decisoes(self, plano: Plano, aprovado_por: str) -> None:
        self.escrita.salvar_decisoes(plano, aprovado_por)

    def salvar_nota(self, regiao: str, periodo: str, texto: str, autor: str) -> None:
        self.escrita.salvar_nota(regiao, periodo, texto, autor)


def criar_repositorio(sample: bool) -> Repositorio:
    """--sample -> RepositorioCache; senão RepositorioZetaris (exige .env)."""
    return RepositorioCache() if sample else RepositorioZetaris()
