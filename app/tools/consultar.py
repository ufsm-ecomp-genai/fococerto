"""consultar: consultas parametrizadas sobre o Repositorio (que lê do Zetaris ou do cache).

Cada consulta é registrada (lista ``consultas`` e evento ``consulta`` no log). As consultas derivadas
(dia/noite, FRP, persistência) são calculadas sobre ``historico_celula``, que é a única consulta histórica do
contrato do Repositorio (seção 3).

Formato aceito para cada dia de ``historico_celula`` (o contrato diz só "n_focos, frp, dia_noite"):
- ``n_focos`` (int), ``frp`` ou ``frp_soma`` (MW), ``dia`` (data, opcional);
- dia/noite em qualquer uma destas formas: ``n_dia``/``n_noite``; ``dia_noite`` como dict ``{"D": n, "N": n}``;
  ``dia_noite`` como string FIRMS ``"D"``/``"N"`` (ou "dia"/"noite"/"misto"); ou fração de noite em [0, 1].
"""
from __future__ import annotations

from typing import Any, Protocol

from app.core.logging import LogExecucao
from app.core.models import Ocorrencia


class RepoHistorico(Protocol):
    def historico_celula(self, ocorrencia_id: str, dias: int = 7) -> list[dict]: ...


def _dia_noite(d: dict) -> tuple[float, float]:
    n = float(d.get("n_focos", 0) or 0)
    if "n_noite" in d or "n_dia" in d:
        noite = float(d.get("n_noite", 0) or 0)
        return float(d.get("n_dia", n - noite) or 0), noite
    dn = d.get("dia_noite")
    if isinstance(dn, dict):
        return float(dn.get("D", dn.get("dia", 0)) or 0), float(dn.get("N", dn.get("noite", 0)) or 0)
    if isinstance(dn, (int, float)) and not isinstance(dn, bool) and 0 <= dn <= 1:
        return n * (1 - dn), n * dn
    if isinstance(dn, str):
        s = dn.strip().lower()
        if s in ("n", "noite", "night"):
            return 0.0, n
        if s in ("d", "dia", "day"):
            return n, 0.0
        if s in ("dn", "nd", "misto", "ambos", "both"):
            return n / 2, n / 2
    return n, 0.0  # sem informação: conta como dia (não inventa sinal noturno)


class Consultor:
    def __init__(self, repo: RepoHistorico, ocorrencias: list[Ocorrencia], log: LogExecucao | None = None,
                 agente: str = "analista"):
        self.repo = repo
        self.occ = {o.id: o for o in ocorrencias}
        self.log = log
        self.agente = agente
        self.consultas: list[str] = []
        self._cache: dict[tuple[str, int], list[dict]] = {}

    def _registrar(self, nome: str, resultado: Any) -> None:
        self.consultas.append(nome)
        if self.log:
            self.log.evento(self.agente, "consulta", {"consulta": nome, "resultado": resultado})

    def _hist(self, oid: str, dias: int) -> list[dict]:
        if (oid, dias) not in self._cache:
            try:
                self._cache[(oid, dias)] = list(self.repo.historico_celula(oid, dias) or [])
            except Exception as e:  # noqa: BLE001 - consulta falha não derruba o agente
                if self.log:
                    self.log.evento(self.agente, "consulta", {"consulta": f"historico_celula({oid}, dias={dias})",
                                                              "erro": f"{type(e).__name__}: {e}"})
                self._cache[(oid, dias)] = []
        return self._cache[(oid, dias)]

    def historico_celula(self, oid: str, dias: int = 7) -> list[dict]:
        h = self._hist(oid, dias)
        self._registrar(f"historico_celula({oid}, dias={dias})", h)
        return h

    def padrao_dia_noite(self, oid: str, dias: int = 7) -> dict:
        h = self._hist(oid, dias)
        n_dia = sum(_dia_noite(d)[0] for d in h)
        n_noite = sum(_dia_noite(d)[1] for d in h)
        tot = n_dia + n_noite
        r = {"n_dia": n_dia, "n_noite": n_noite, "frac_noite": round(n_noite / tot, 3) if tot else None}
        self._registrar(f"padrao_dia_noite({oid}, dias={dias})", r)
        return r

    def padrao_frp(self, oid: str, dias: int = 7) -> dict:
        h = self._hist(oid, dias)
        focos = sum(float(d.get("n_focos", 0) or 0) for d in h)
        frps = [float(d.get("frp", d.get("frp_soma", 0)) or 0) for d in h]
        o = self.occ.get(oid)
        r = {
            "frp_por_foco_hist": round(sum(frps) / focos, 2) if focos else None,
            "frp_max_foco_hist": max((float(d.get("frp_max", 0) or 0) for d in h), default=None),
            "frp_soma_atual": o.frp_soma if o else None,
            "frp_max_atual": o.frp_max if o else None,
            "frp_por_foco_atual": round(o.frp_soma / o.n_focos, 2) if o and o.n_focos else None,
        }
        self._registrar(f"padrao_frp({oid}, dias={dias})", r)
        return r

    def persistencia(self, oid: str, dias: int = 7) -> dict:
        h = self._hist(oid, dias)
        serie = [float(d.get("n_focos", 0) or 0) for d in h]
        com = [n > 0 for n in serie]
        run = best = 0
        for c in com:
            run = run + 1 if c else 0
            best = max(best, run)
        o = self.occ.get(oid)
        r = {
            "dias_no_historico": len(serie),
            "dias_com_foco": sum(com),
            "maior_sequencia_dias": best,
            "max_focos_dia": max(serie) if serie else 0,
            "intermitente": sum(com) >= 2 and best < sum(com),
            "periodos_seguidos": o.periodos_seguidos if o else None,
            "status": o.status if o else None,
        }
        self._registrar(f"persistencia({oid}, dias={dias})", r)
        return r

    def proximidade_ti_uc(self, oid: str) -> dict:
        o = self.occ.get(oid)
        r = {"dist_ti_uc_km": o.dist_ti_uc_km if o else None}
        self._registrar(f"proximidade_ti_uc({oid})", r)
        return r

    def tempo(self, oid: str) -> dict:
        o = self.occ.get(oid)
        r = {"vpd_kpa": o.vpd_kpa if o else None, "vento_kmh": o.vento_kmh if o else None}
        self._registrar(f"tempo({oid})", r)
        return r

    def exposicao(self, oid: str) -> dict:
        o = self.occ.get(oid)
        r = {"pop_raio": o.pop_raio if o else None, "localidades": o.localidades if o else []}
        self._registrar(f"exposicao({oid})", r)
        return r


CONSULTAS = ("historico_celula", "padrao_dia_noite", "padrao_frp", "persistencia", "proximidade_ti_uc", "tempo",
             "exposicao")


def consultar(repo: RepoHistorico, consulta: str, ocorrencia_id: str, ocorrencias: list[Ocorrencia] | None = None,
              log: LogExecucao | None = None, **params) -> Any:
    """Wrapper de uma consulta só. ``consulta`` precisa estar em ``CONSULTAS`` (consultas parametrizadas, sem SQL livre)."""
    if consulta not in CONSULTAS:
        raise ValueError(f"consulta desconhecida: {consulta!r}; use uma de {CONSULTAS}")
    c = Consultor(repo, ocorrencias or [], log)
    return getattr(c, consulta)(ocorrencia_id, **params)
