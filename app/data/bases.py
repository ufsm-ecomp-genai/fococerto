"""Bases em camadas, com procedência (docs/CONTRATOS.md, seção 16). Funções puras, sem rede.

Camadas, da maior para a menor confiança:
  1. ``declarada``: no cenário (``Cenario.bases``), informada pelo coordenador. O grafo soma essas.
  2. ``oficial``:   ``config/regioes/<regiao>_bases_oficiais.csv`` (id,nome,orgao,lat,lon,fonte,data_fonte[,coordenada]).
  3. ``osm``:       ``amenity=fire_station`` do OpenStreetMap (data/cache/<regiao>/bases.csv ou tabela do Zetaris).
  4. ``estimada``:  sede de município do GeoNames (unidade NÃO verificada). Só entra se nenhuma outra camada tem
                    base dentro da bbox da região, ou se o YAML da região pedir (``bases_estimadas: sempre``).

Fusão: duas bases a menos de ``RAIO_FUSAO_KM`` (ou com o mesmo id) são a mesma unidade. Fica o registro da camada
de maior confiança; as outras entram no texto de ``fonte`` ("fundida com ...") e no mapa de apelidos (id perdido ->
id mantido), para quem tiver recursos apontando para o id perdido.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.core.config import RAIZ
from app.core.models import Base
from app.data import fontes
from app.data.geo import dentro_bbox, haversine_km

PASTA_REGIOES = RAIZ / "config" / "regioes"
ORDEM_CONFIANCA = {"declarada": 0, "oficial": 1, "osm": 2, "estimada": 3}
RAIO_FUSAO_KM = 3.0
POP_MIN_ESTIMADA = 20000  # sede de município com pelo menos isto de habitantes (GeoNames) vira base estimada
ROTULO = {"declarada": "declarada pelo coordenador", "oficial": "lista oficial", "osm": "OpenStreetMap",
          "estimada": "estimada (sede de município)"}


# --------------------------------------------------------------------------- leitura das camadas
def caminho_oficiais(regiao: str, pasta: Path = PASTA_REGIOES) -> Path:
    return Path(pasta) / f"{regiao}_bases_oficiais.csv"


def bases_oficiais_de_linhas(linhas: list[dict]) -> list[Base]:
    """Linhas do CSV oficial -> Base(confianca="oficial"). A fonte fica legível: órgão, URL e ano."""
    out = []
    for r in linhas:
        partes = [p for p in (r.get("orgao"), r.get("fonte")) if p]
        fonte = " — ".join(partes)
        if r.get("data_fonte"):
            fonte += f" ({r['data_fonte']})"
        if r.get("coordenada"):
            fonte += f"; coordenada: {r['coordenada']}"
        out.append(Base(id=r["id"].strip(), nome=r["nome"].strip(), lat=float(r["lat"]), lon=float(r["lon"]),
                        fonte=fonte, confianca="oficial"))
    return out


def ler_bases_oficiais(regiao: str, pasta: Path = PASTA_REGIOES) -> list[Base]:
    """Camada 2. Opcional: sem o arquivo, devolve []."""
    p = caminho_oficiais(regiao, pasta)
    return bases_oficiais_de_linhas(fontes.ler_csv(p)) if p.exists() else []


def bases_osm_de_linhas(linhas: list[dict]) -> list[Base]:
    """Camada 3 (CSV do cache ou linhas do Zetaris; valores podem vir como string)."""
    return [Base(id=str(b["id"]), nome=str(b["nome"]), lat=float(b["lat"]), lon=float(b["lon"]),
                 fonte=str(b.get("fonte") or "OpenStreetMap amenity=fire_station"), confianca="osm")
            for b in linhas]


def bases_estimadas(localidades: list[dict], bbox, pop_min: int = POP_MIN_ESTIMADA) -> list[Base]:
    """Camada 4: sedes de município (GeoNames) dentro da bbox com pop >= pop_min. Unidade não verificada."""
    out = []
    for l in sorted(localidades, key=lambda x: -int(float(x.get("pop") or 0))):
        lat, lon, pop = float(l["lat"]), float(l["lon"]), int(float(l.get("pop") or 0))
        if pop < pop_min or not dentro_bbox(lat, lon, bbox):
            continue
        gid = l.get("geonameid") or f"{lat:.3f}_{lon:.3f}"
        out.append(Base(id=f"est_{gid}", nome=f"{l['nome']} (estimada)", lat=lat, lon=lon,
                        fonte=f"GeoNames {gid}: sede de município, {pop} hab.; unidade de combate NÃO verificada",
                        confianca="estimada"))
    return out


def politica_estimadas(regiao: str, pasta: Path = PASTA_REGIOES) -> tuple[str, int]:
    """Do YAML da região: ``bases_estimadas: auto|sempre|nunca`` (padrão auto) e ``bases_estimadas_pop_min``."""
    p = Path(pasta) / f"{regiao}.yaml"
    dados = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    dados = dados or {}
    modo = str(dados.get("bases_estimadas", "auto")).lower()
    if modo in ("true", "sim", "yes"):
        modo = "sempre"
    elif modo in ("false", "nao", "não", "no"):
        modo = "nunca"
    return modo, int(dados.get("bases_estimadas_pop_min", POP_MIN_ESTIMADA))


def precisa_estimadas(modo: str, bases: list[Base], bbox) -> bool:
    if modo == "sempre":
        return True
    if modo == "nunca":
        return False
    return not any(dentro_bbox(b.lat, b.lon, bbox) for b in bases)


# --------------------------------------------------------------------------- fusão
def _rotulo_curto(b: Base) -> str:
    return f"{b.id} ({ROTULO.get(b.confianca, b.confianca)}{': ' + b.fonte if b.fonte else ''})"


def fundir_com_apelidos(*camadas: list[Base], raio_km: float = RAIO_FUSAO_KM) -> tuple[list[Base], dict[str, str]]:
    """Funde camadas de bases. Devolve (bases, apelidos) com apelidos = {id descartado: id mantido}.

    Ordem de prioridade pela ``confianca`` de cada base (declarada > oficial > osm > estimada); no empate, a
    ordem de entrada. Mesma unidade = mesmo id ou distância < raio_km."""
    todas = [b for c in camadas for b in c]
    ordenadas = sorted(enumerate(todas), key=lambda ib: (ORDEM_CONFIANCA.get(ib[1].confianca, 9), ib[0]))
    mantidas: list[Base] = []
    fundidas: dict[str, list[Base]] = {}
    apelidos: dict[str, str] = {}
    for _, b in ordenadas:
        alvo = next((m for m in mantidas if m.id == b.id), None) or \
            next((m for m in mantidas if haversine_km(m.lat, m.lon, b.lat, b.lon) < raio_km), None)
        if alvo is None:
            mantidas.append(b)
            continue
        fundidas.setdefault(alvo.id, []).append(b)
        if b.id != alvo.id:
            apelidos[b.id] = alvo.id
    out = []
    for m in mantidas:
        extra = fundidas.get(m.id)
        if extra:
            m = m.model_copy(update={"fonte": (m.fonte + "; " if m.fonte else "") +
                                     "fundida com " + ", ".join(_rotulo_curto(x) for x in extra)})
        out.append(m)
    return out, apelidos


def fundir_bases(repo_bases: list[Base], declaradas: list[Base], raio_km: float = RAIO_FUSAO_KM) -> list[Base]:
    """Para o grafo: soma as bases do cenário (camada 1, marcadas ``declarada``) às do repositório (camadas 2–4,
    já fundidas), removendo duplicatas por distância. A declarada vence a do repositório no mesmo lugar.

    Atenção: se uma declarada absorve uma base do repositório de id diferente, recursos com o id antigo ficam
    sem base. Use ``fundir_bases_com_apelidos`` para remapear ``Recurso.base_id``."""
    return fundir_bases_com_apelidos(repo_bases, declaradas, raio_km)[0]


def fundir_bases_com_apelidos(repo_bases: list[Base], declaradas: list[Base], raio_km: float = RAIO_FUSAO_KM
                              ) -> tuple[list[Base], dict[str, str]]:
    decl = [b.model_copy(update={"confianca": "declarada"}) for b in declaradas]
    return fundir_com_apelidos(decl, repo_bases, raio_km=raio_km)


def bases_em_camadas(regiao: str, bbox, osm: list[Base], localidades: list[dict] | None,
                     oficiais: list[Base] | None = None, pasta: Path = PASTA_REGIOES) -> list[Base]:
    """Camadas 2–4 fundidas (o que o Repositorio.bases devolve)."""
    oficiais = ler_bases_oficiais(regiao, pasta) if oficiais is None else oficiais
    camadas = [oficiais, osm]
    modo, pop_min = politica_estimadas(regiao, pasta)
    if localidades and precisa_estimadas(modo, oficiais + osm, bbox):
        camadas.append(bases_estimadas(localidades, bbox, pop_min))
    return fundir_com_apelidos(*camadas)[0]
