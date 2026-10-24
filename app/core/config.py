"""Configuração: variáveis de ambiente (.env) e YAML de região/cenário."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

from app.core.models import Cenario, RegiaoCfg

RAIZ = Path(__file__).resolve().parents[2]


def carregar_env(caminho: Path = RAIZ / ".env") -> None:
    """Carrega KEY=VALUE do .env sem sobrescrever o ambiente já definido."""
    if not caminho.exists():
        return
    for linha in caminho.read_text().splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


def env(chave: str, padrao: str | None = None) -> str | None:
    return os.environ.get(chave, padrao)


def regiao(nome: str) -> RegiaoCfg:
    dados = yaml.safe_load((RAIZ / "config" / "regioes" / f"{nome}.yaml").read_text())
    return RegiaoCfg(nome=nome, **dados)


def cenario(caminho: str | Path) -> Cenario:
    return Cenario(**yaml.safe_load(Path(caminho).read_text()))
