"""Logger JSONL: uma linha por evento em logs/<execucao>.jsonl (docs/CONTRATOS.md, seção 7)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import RAIZ

CAMPOS_LLM = ("modelo", "routed_model", "receipt", "tokens", "latencia_s")


class LogExecucao:
    def __init__(self, regiao: str, periodo: str, execucao: str | None = None, pasta: Path = RAIZ / "logs"):
        self.execucao = execucao or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self.regiao = regiao
        self.periodo = periodo
        pasta.mkdir(parents=True, exist_ok=True)
        self.caminho = pasta / f"{self.execucao}.jsonl"

    def evento(self, agente: str, evento: str, dados: dict | None = None, **llm) -> dict:
        linha = {
            "t": datetime.now(timezone.utc).isoformat(),
            "execucao": self.execucao,
            "regiao": self.regiao,
            "periodo": self.periodo,
            "agente": agente,
            "evento": evento,
            "dados": dados or {},
        }
        for campo in CAMPOS_LLM:
            linha[campo] = llm.get(campo)
        with self.caminho.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False, default=str) + "\n")
        return linha
