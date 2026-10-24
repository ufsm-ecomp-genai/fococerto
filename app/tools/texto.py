"""Normalização de texto (acentos/caixa) para casar nomes em memórias e justificativas."""
from __future__ import annotations

import re
import unicodedata


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def contem_termo(texto_norm: str, termo: str) -> bool:
    t = norm(termo).strip()
    return bool(t) and re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", texto_norm) is not None


PALAVRAS_VAZIAS = {"base", "bases", "de", "do", "da", "dos", "das", "e", "posto", "brigada", "sede",
                   # genéricas de nome de unidade: não distinguem uma base de outra
                   "simulada", "simulado", "perto", "bombeiro", "bombeiros", "militar", "batalhao", "corpo",
                   "unidade", "quartel", "grupamento", "cidade", "estado", "regiao"}
RE_SIMULADA = re.compile(r"\(\s*simulad[ao]\s*\)")


def sem_sufixo_simulada(nome: str) -> str:
    """'Paraíso do Tocantins (simulada)' -> 'Paraíso do Tocantins' (o sufixo só marca dado simulado)."""
    return RE_SIMULADA.sub(" ", norm(nome)).strip()


def tokens_nome(nome: str, ignorar: set[str] | frozenset[str] = frozenset()) -> list[str]:
    """Palavras do nome que podem identificá-lo: ≥ 4 letras, fora das palavras vazias, sem o sufixo
    '(simulada)' e fora de ``ignorar`` (ex.: o nome da região, que aparece em muitos nomes de cidade)."""
    return [t for t in re.findall(r"[a-z0-9]+", sem_sufixo_simulada(nome))
            if len(t) >= 4 and t not in PALAVRAS_VAZIAS and t not in ignorar]
