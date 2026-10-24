"""Leitura determinística das memórias (H-MEM) e notas: o que elas dizem sobre bases, rotas, reserva e reforço.

É uma ferramenta: extrai *fatos candidatos* por palavras-chave. Quem decide se a exceção vale é o Crítico.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.models import Base, Memoria, Ocorrencia
from app.tools.texto import contem_termo, norm, tokens_nome

BLOQUEIO = re.compile(r"alagad|bloquead|interditad|intransitavel|inacessivel|fechad|sem acesso|ponte caiu|atolad")
LIBERACAO = re.compile(r"liberad|reabert|desbloquead|normalizad|(?<!in)transitavel|desimpedid")
REFORCO = re.compile(r"cresceu|cresce|reign|reacend|subestimad|despriorizad.*(cresc|aument|volt)|aumentou|voltou a queimar")
NUMEROS = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5}


@dataclass
class LeituraMemorias:
    bases_bloqueadas: dict[str, Memoria] = field(default_factory=dict)        # base_id -> memória
    ocorrencias_bloqueadas: dict[str, Memoria] = field(default_factory=dict)  # rota terrestre p/ a ocorrência
    reforcos: dict[str, Memoria] = field(default_factory=dict)                # ocorrencia_id -> memória
    reserva_minima: int = 0
    memoria_reserva: Memoria | None = None
    aplicadas: list[str] = field(default_factory=list)                        # ids de memórias que casaram


def _bases_citadas(t: str, bases: list[Base]) -> list[Base]:
    achadas = []
    for b in bases:
        if contem_termo(t, b.id) or contem_termo(t, b.nome) or any(contem_termo(t, tk) for tk in tokens_nome(b.nome)):
            achadas.append(b)
    return achadas


def _ocorrencias_citadas(t: str, ocorrencias: list[Ocorrencia]) -> list[Ocorrencia]:
    achadas = []
    for o in ocorrencias:
        if contem_termo(t, o.id) or any(len(norm(loc.get("nome", ""))) >= 4 and contem_termo(t, loc.get("nome", ""))
                                        for loc in o.localidades):
            achadas.append(o)
    return achadas


def _reserva(t: str) -> int | None:
    if "reserva" not in t:
        return None
    if re.search(r"sem reserva|nao (precisa|e necessari\w*|manter)\w* .*reserva", t):
        return 0
    m = re.search(r"(\d+|zero|uma?|dois|duas|tres|quatro|cinco)\s+(?:\w+\s+){0,3}(?:de |em |na |como )?reserva", t) \
        or re.search(r"reserva\s+(?:de|com|minima de|minima)?\s*(\d+|uma?|dois|duas|tres|quatro|cinco)", t)
    if not m:
        return 1  # "manter reserva" sem número: ao menos um recurso
    v = m.group(1)
    return int(v) if v.isdigit() else NUMEROS.get(v, 1)


def interpretar_memorias(memorias: list[Memoria], bases: list[Base], ocorrencias: list[Ocorrencia]) -> LeituraMemorias:
    """Processa em ordem cronológica: uma liberação posterior anula um bloqueio anterior do mesmo lugar."""
    out = LeituraMemorias()
    for m in sorted(memorias, key=lambda x: x.criada_em):
        t = norm(m.texto)
        casou = False
        libera, bloqueia = bool(LIBERACAO.search(t)), bool(BLOQUEIO.search(t))
        if libera or bloqueia:
            for b in _bases_citadas(t, bases):
                casou = True
                if libera:
                    out.bases_bloqueadas.pop(b.id, None)
                else:
                    out.bases_bloqueadas[b.id] = m
            for o in _ocorrencias_citadas(t, ocorrencias):
                casou = True
                if libera:
                    out.ocorrencias_bloqueadas.pop(o.id, None)
                else:
                    out.ocorrencias_bloqueadas[o.id] = m
        if REFORCO.search(t):
            for o in _ocorrencias_citadas(t, ocorrencias):
                out.reforcos[o.id] = m
                casou = True
        n = _reserva(t)
        if n is not None:
            out.reserva_minima, out.memoria_reserva = n, m
            casou = True
        if casou:
            out.aplicadas.append(m.id)
    return out
