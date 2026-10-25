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


REAIS = ("oficial", "osm")  # procedências com localização real verificável por fonte (docs/CONTRATOS.md, seção 16)


def procedencia_base(base: Any, cenario: Any = None) -> str:
    """Confiança efetiva da base: 'declarada' se veio do cenário (id em Cenario.bases ou simulada=True);
    senão o campo ``confianca`` (padrão 'osm', o default do contrato)."""
    ids_cenario = {campo(b, "id") for b in (campo(cenario, "bases", []) or [])}
    if campo(base, "id") in ids_cenario or campo(base, "simulada", False):
        return "declarada"
    return campo(base, "confianca", "osm") or "osm"


def bases_usadas(resultado: ResultadoPeriodo) -> list:
    """Bases que têm ao menos um recurso do cenário, na ordem do repositório."""
    ids = {r.base_id for r in resultado.recursos}
    return [b for b in resultado.bases if b.id in ids]


def aviso_bases(resultado: ResultadoPeriodo, cenario: Any, T: dict) -> str | None:
    """Aviso de procedência para o topo do plano e do mapa (só quando o cenário é simulado)."""
    if cenario is None or not campo(cenario, "simulado", False):
        return None
    usadas = bases_usadas(resultado)
    outras = [b for b in usadas if procedencia_base(b, cenario) not in REAIS]
    if not usadas:
        return None
    if not outras:
        return T["aviso_bases_reais"]
    return T["aviso_bases_mistas"].format(n_reais=len(usadas) - len(outras), n_outras=len(outras),
                                          ids=", ".join(b.id for b in outras))
