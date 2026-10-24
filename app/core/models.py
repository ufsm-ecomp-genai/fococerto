"""Tipos compartilhados entre módulos. Fonte da verdade: docs/CONTRATOS.md, seção 2."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Ocorrencia(BaseModel):
    id: str  # "cel_<lat10>_<lon10>"
    lat: float
    lon: float
    n_focos: int
    frp_soma: float
    frp_max: float
    primeiro: datetime
    ultimo: datetime
    periodos_seguidos: int = 1
    status: Literal["nova", "crescendo", "estavel", "diminuindo"] | None = None
    pop_raio: int = 0
    dist_ti_uc_km: float | None = None
    vpd_kpa: float | None = None
    vento_kmh: float | None = None
    prioridade: float = 0.0
    componentes: dict[str, float] = Field(default_factory=dict)
    localidades: list[dict] = Field(default_factory=list)  # [{nome, pop, dist_km}]


class Base(BaseModel):
    id: str
    nome: str
    lat: float
    lon: float


class Recurso(BaseModel):
    id: str
    base_id: str
    tipo: Literal["terrestre", "aereo"]
    capacidade: int = 1
    disponivel: bool = True


class Designacao(BaseModel):
    recurso_id: str
    ocorrencia_id: str
    ordem: int
    eta_h: float
    justificativa: str
    evidencias: list[str] = Field(default_factory=list)


class Plano(BaseModel):
    periodo: str
    regiao: str
    designacoes: list[Designacao] = Field(default_factory=list)
    reserva: list[str] = Field(default_factory=list)
    nao_atendidas: list[str] = Field(default_factory=list)
    resumo: str = ""
    rodada: int = 0


class Violacao(BaseModel):
    regra: str
    ocorrencia_id: str | None = None
    recurso_id: str | None = None
    evidencia: dict = Field(default_factory=dict)
    sugestao: str = ""
    rigida: bool = True


class ParecerAnalista(BaseModel):
    ocorrencia_id: str
    pergunta: str
    conclusao: Literal["queima_agricola_provavel", "incendio_vegetacao_provavel", "indeterminado"]
    confianca: Literal["baixa", "media", "alta"]
    evidencias: list[str] = Field(default_factory=list)
    consultas: list[str] = Field(default_factory=list)


class VeredictoCritico(BaseModel):
    decisao: Literal["aprova", "rejeita", "escala"]
    motivos: list[str] = Field(default_factory=list)
    contra_proposta: Plano | None = None
    pedir_analista: list[str] = Field(default_factory=list)


class Memoria(BaseModel):
    id: str
    regiao: str
    texto: str
    tipo: Literal["derivada", "nota"]
    fonte: str
    confianca: float = 1.0
    supersedes: str | None = None
    criada_em: datetime


class RegiaoCfg(BaseModel):
    nome: str
    bbox: tuple[float, float, float, float]  # lat_min, lat_max, lon_min, lon_max
    idioma: str = "pt-BR"
    velocidade_kmh: float = 40.0
    velocidade_aereo_kmh: float = 180.0  # suposição declarada: linha reta
    fator_tortuosidade: float = 1.4
    raio_exposicao_km: float = 15.0
    eta_max_h: float = 6.0


class Cenario(BaseModel):
    regiao: str
    periodo: str
    recursos: list[Recurso]
    reserva: int = 0
    notas: list[str] = Field(default_factory=list)
    simulado: bool = True


class ResultadoPeriodo(BaseModel):
    """Saída de app.agents.grafo.executar_periodo (docs/CONTRATOS.md, seção 10)."""
    plano: Plano
    status: Literal["aprova", "escala"] | None = None
    ocorrencias: list[Ocorrencia]
    bases: list[Base]
    recursos: list[Recurso]
    escalacoes: list[dict] = Field(default_factory=list)  # {ocorrencia_id, motivo}
    pareceres: list[ParecerAnalista] = Field(default_factory=list)
    memorias_usadas: list[Memoria] = Field(default_factory=list)
    historico: list[dict] = Field(default_factory=list)  # por rodada: {rodada, plano, violacoes, veredicto}
    rodadas: int = 0
    log_path: str = ""
