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


PALAVRAS_VAZIAS = {"base", "de", "do", "da", "dos", "das", "e", "posto", "brigada", "sede"}


def tokens_nome(nome: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", norm(nome)) if len(t) >= 4 and t not in PALAVRAS_VAZIAS]
