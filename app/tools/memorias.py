"""Leitura determinística das memórias (H-MEM) e notas: o que elas dizem sobre bases, rotas, reserva e reforço.

É uma ferramenta: extrai *fatos candidatos* por palavras-chave. Quem decide se a exceção vale é o Crítico.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.models import Base, Memoria, Ocorrencia
from app.tools.texto import contem_termo, norm, sem_sufixo_simulada, tokens_nome

BLOQUEIO = re.compile(r"alagad|bloquead|interditad|intransitavel|inacessivel|fechad|sem acesso|ponte caiu|atolad")
LIBERACAO = re.compile(r"liberad|reabert|desbloquead|normalizad|(?<!in)transitavel|desimpedid")
REFORCO = re.compile(r"cresceu|cresce|persistiu forte|reign|reacend|subestimad|despriorizad.*(cresc|aument|volt)|aumentou|voltou a queimar")
NUMEROS = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5}


@dataclass
class LeituraMemorias:
    bases_bloqueadas: dict[str, Memoria] = field(default_factory=dict)        # base_id -> memória
    ocorrencias_bloqueadas: dict[str, Memoria] = field(default_factory=dict)  # rota terrestre p/ a ocorrência
    reforcos: dict[str, Memoria] = field(default_factory=dict)                # ocorrencia_id -> memória
    reserva_minima: int = 0
    memoria_reserva: Memoria | None = None
    aplicadas: list[str] = field(default_factory=list)                        # ids de memórias que casaram


def tokens_distintivos(bases: list[Base], ignorar: set[str]) -> dict[str, list[str]]:
    """Por base, as palavras do nome que só ela tem (sem '(simulada)', nome da região e palavras vazias).

    Ex.: com a região 'tocantins', 'Paraíso do Tocantins (simulada)' -> ['paraiso']; uma palavra que aparece no
    nome de duas bases ('porto' em 'Porto Nacional' e 'Porto Alegre') não identifica nenhuma das duas."""
    por_base = {b.id: set(tokens_nome(b.nome, ignorar)) for b in bases}
    contagem: dict[str, int] = {}
    for tks in por_base.values():
        for tk in tks:
            contagem[tk] = contagem.get(tk, 0) + 1
    return {bid: sorted(tk for tk in tks if contagem[tk] == 1) for bid, tks in por_base.items()}


def _bases_citadas(t: str, bases: list[Base], distintivos: dict[str, list[str]]) -> list[Base]:
    achadas = []
    for b in bases:
        nome = sem_sufixo_simulada(b.nome)
        if (contem_termo(t, b.id) or (len(nome) >= 4 and contem_termo(t, nome))
                or any(contem_termo(t, tk) for tk in distintivos.get(b.id, []))):
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


def interpretar_memorias(memorias: list[Memoria], bases: list[Base], ocorrencias: list[Ocorrencia],
                         regiao: str | None = None) -> LeituraMemorias:
    """Processa em ordem cronológica: uma liberação posterior anula um bloqueio anterior do mesmo lugar.

    Base citada = id, nome completo (sem '(simulada)') ou palavra distintiva do nome. O nome da região
    (``regiao`` e ``Memoria.regiao``) não conta: 'no Tocantins' não cita 'Paraíso do Tocantins'."""
    out = LeituraMemorias()
    ignorar = {tk for r in {regiao, *(m.regiao for m in memorias)} if r for tk in tokens_nome(r.replace("_", " "))}
    distintivos = tokens_distintivos(bases, ignorar)
    for m in sorted(memorias, key=lambda x: x.criada_em):
        t = norm(m.texto)
        casou = False
        libera, bloqueia = bool(LIBERACAO.search(t)), bool(BLOQUEIO.search(t))
        if libera or bloqueia:
            for b in _bases_citadas(t, bases, distintivos):
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
