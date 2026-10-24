"""Funções compartilhadas pelos renderizadores (Markdown, JSON e mapa)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.core.models import ResultadoPeriodo


def campo(obj: Any, nome: str, padrao: Any = None) -> Any:
    """Lê `nome` de um modelo pydantic ou de um dict (o histórico pode vir em qualquer forma)."""
    if obj is None:
        return padrao
    if isinstance(obj, dict):
        return obj.get(nome, padrao)
    return getattr(obj, nome, padrao)


def para_dict(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: para_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [para_dict(v) for v in obj]
    return obj


def faixas_prioridade(resultado: ResultadoPeriodo) -> dict[str, str]:
    """Faixa relativa (alta/media/baixa) por ocorrência: tercis do ranking de prioridade do período."""
    ordenadas = sorted(resultado.ocorrencias, key=lambda o: o.prioridade, reverse=True)
    n = len(ordenadas)
    faixas: dict[str, str] = {}
    for i, o in enumerate(ordenadas):
        frac = i / n if n else 0
        faixas[o.id] = "alta" if frac < 1 / 3 else ("media" if frac < 2 / 3 else "baixa")
    return faixas


def ids_escalados(resultado: ResultadoPeriodo) -> dict[str, str]:
    """ocorrencia_id -> motivo. Escalações sem ocorrência ficam com a chave ""."""
    saida: dict[str, str] = {}
    for e in resultado.escalacoes:
        oid = campo(e, "ocorrencia_id") or ""
        motivo = str(campo(e, "motivo", "") or "")
        saida[oid] = f"{saida[oid]}; {motivo}" if oid in saida and motivo else (motivo or saida.get(oid, ""))
    return saida


def localidade_proxima(localidades: list[dict]) -> dict | None:
    if not localidades:
        return None
    return min(localidades, key=lambda l: l.get("dist_km", float("inf")) if l.get("dist_km") is not None else float("inf"))
