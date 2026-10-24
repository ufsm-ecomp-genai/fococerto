"""Utilidades dos scripts de dados: raiz do repo no sys.path, região e DSN do Postgres."""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.core.config import carregar_env, regiao  # noqa: E402

RAW = RAIZ / "data" / "raw"
CACHE = RAIZ / "data" / "cache"


def bbox_da_regiao(nome: str):
    return regiao(nome).bbox


def dsn_postgres() -> str | None:
    carregar_env()
    return os.environ.get("POSTGRES_DSN")
