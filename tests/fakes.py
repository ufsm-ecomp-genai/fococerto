"""Fakes para testes (dados SIMULADOS, só para teste). Seguem os Protocols de docs/CONTRATOS.md, seções 3 e 11.

Não substituem ``app/data/repositorio.py`` (dono: dados-zetaris) nem ``app/memory_client.py`` (dono: hmem-engine).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.models import Base, Memoria, Ocorrencia, Plano, Recurso, RegiaoCfg

T0 = datetime(2026, 10, 24, 15, 0, tzinfo=timezone.utc)


def regiao_teste(**kw) -> RegiaoCfg:
    dados = dict(nome="teste", bbox=(-13.0, -8.0, -49.5, -45.5), velocidade_kmh=40.0, fator_tortuosidade=1.4,
                 raio_exposicao_km=15.0, eta_max_h=6.0)
    dados.update(kw)
    return RegiaoCfg(**dados)


def oc(id: str, lat: float, lon: float, prioridade: float, pop: int = 0, localidades: list[dict] | None = None,
       n_focos: int = 4, frp_soma: float = 40.0, frp_max: float = 15.0, dist_ti: float | None = None,
       periodos_seguidos: int = 1, vpd: float | None = None, vento: float | None = None) -> Ocorrencia:
    return Ocorrencia(id=id, lat=lat, lon=lon, n_focos=n_focos, frp_soma=frp_soma, frp_max=frp_max,
                      primeiro=T0 - timedelta(hours=6), ultimo=T0, periodos_seguidos=periodos_seguidos,
                      pop_raio=pop, dist_ti_uc_km=dist_ti, vpd_kpa=vpd, vento_kmh=vento, prioridade=prioridade,
                      componentes={"exposicao": 1.0 if pop else 0.0}, localidades=localidades or [])


def rec(id: str, base_id: str, tipo: str = "terrestre", capacidade: int = 1, disponivel: bool = True) -> Recurso:
    return Recurso(id=id, base_id=base_id, tipo=tipo, capacidade=capacidade, disponivel=disponivel)


class RepositorioFake:
    def __init__(self, ocorrencias: dict[str, list[Ocorrencia]], bases: list[Base],
                 historicos: dict[str, list[dict]] | None = None):
        self._occ = ocorrencias
        self._bases = bases
        self._hist = historicos or {}
        self.consultas_historico: list[tuple[str, int]] = []
        self.decisoes: list[tuple[Plano, str]] = []
        self.notas: list[tuple[str, str, str, str]] = []

    def ocorrencias(self, regiao: str, periodo: str, top: int = 15) -> list[Ocorrencia]:
        return sorted(self._occ.get(periodo, []), key=lambda o: -o.prioridade)[:top]

    def bases(self, regiao: str) -> list[Base]:
        return list(self._bases)

    def historico_celula(self, ocorrencia_id: str, dias: int = 7) -> list[dict]:
        self.consultas_historico.append((ocorrencia_id, dias))
        return list(self._hist.get(ocorrencia_id, []))[-dias:]

    def salvar_decisoes(self, plano: Plano, aprovado_por: str) -> None:
        self.decisoes.append((plano, aprovado_por))

    def salvar_nota(self, regiao: str, periodo: str, texto: str, autor: str) -> None:
        self.notas.append((regiao, periodo, texto, autor))


class MemoriaFake:
    """Memória em lista. ``recall`` devolve todas as ativas da região (sem ranking semântico)."""

    def __init__(self):
        self._m: list[Memoria] = []
        self.chamadas_recall = 0

    def gravar(self, regiao: str, texto: str, tipo: str, fonte: str, confianca: float = 1.0,
               supersedes: str | None = None) -> Memoria:
        m = Memoria(id=f"mem_{len(self._m) + 1}", regiao=regiao, texto=texto, tipo=tipo, fonte=fonte,
                    confianca=confianca, supersedes=supersedes, criada_em=T0 + timedelta(minutes=len(self._m)))
        self._m.append(m)
        return m

    def recall(self, regiao: str, consulta: str, k: int = 5) -> tuple[list[Memoria], list[Memoria]]:
        self.chamadas_recall += 1
        sub = {m.supersedes for m in self._m if m.supersedes}
        da_regiao = [m for m in self._m if m.regiao == regiao]
        return [m for m in da_regiao if m.id not in sub][:k], [m for m in da_regiao if m.id in sub]

    def listar(self, regiao: str) -> list[Memoria]:
        return [m for m in self._m if m.regiao == regiao]


# ---------------------------------------------------------------- históricos simulados
def hist_agricola(dias: int = 7) -> list[dict]:
    """Dias alternados, poucos focos diurnos e FRP baixo (padrão de queima de manejo)."""
    return [{"dia": f"2026-10-{17 + i:02d}", "n_focos": 2 if i % 2 == 0 else 0, "frp": 10.0 if i % 2 == 0 else 0.0,
             "dia_noite": "D"} for i in range(dias)]


def hist_vegetacao(dias: int = 7) -> list[dict]:
    """Contínuo, crescente, com detecções noturnas e FRP alto."""
    return [{"dia": f"2026-10-{17 + i:02d}", "n_focos": 3 + 2 * i, "frp": 60.0 * (3 + 2 * i),
             "dia_noite": {"D": 2 + i, "N": 1 + i}} for i in range(dias)]
