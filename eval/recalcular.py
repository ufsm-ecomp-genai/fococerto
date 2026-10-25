"""Recalcula checagens, métricas, resumo e tabela a partir dos JSONs já salvos de uma ablação, sem rodar
nenhum agente nem o LLM.

    .venv/bin/python -m eval.recalcular eval/resultados/20261025T015525Z_llm
    .venv/bin/python -m eval.recalcular eval/resultados/20261024T222738Z_offline --saida /tmp/x

Para cada ``<cenario>__<variante>__r<n>.json`` da pasta, lê o ``resultado`` salvo (o ``ResultadoPeriodo`` da
execução), confere de novo contra o gabarito atual e recalcula as métricas, incluindo as de sobre-escalação
(eval/README.md). Avisa se alguma checagem recalculada difere da que foi salva na execução original.

Escreve ``resumo_recalculado.json`` e ``tabela_recalculada.md`` (na própria pasta, ou em ``--saida``). Não
altera ``resumo.json`` nem ``tabela.md`` da execução original.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from app.core.config import regiao as carregar_regiao
from eval.checagem import DIR_CENARIOS, DIR_GABARITOS, RAIZ_EVAL, avaliar, listar_casos
from eval.agregacao import VARIANTES, agregar, metricas_completas, tabela_md

NOME = re.compile(r"^(?P<cen>.+)__(?P<var>[A-D])__r(?P<rep>\d+)\.json$")
PARES_DIRS = [(DIR_CENARIOS, DIR_GABARITOS),
              (RAIZ_EVAL / "cenarios_2periodos", RAIZ_EVAL / "gabaritos_2periodos")]


def casos_conhecidos() -> dict[str, tuple[dict, dict]]:
    out: dict[str, tuple[dict, dict]] = {}
    for dc, dg in PARES_DIRS:
        if dc.exists():
            for cen, gab in listar_casos(dir_cenarios=dc, dir_gabaritos=dg):
                out[cen["meta"]["id"]] = (cen, gab)
    return out


def recalcular(pasta: Path) -> tuple[dict, list[dict], list[str]]:
    """(agregado, execuções recalculadas, avisos)."""
    casos = casos_conhecidos()
    execs, avisos, modos = [], [], set()
    cfgs: dict[str, object] = {}
    for arq in sorted(pasta.glob("*__*__r*.json")):
        m = NOME.match(arq.name)
        if not m:
            continue
        e = json.loads(arq.read_text(encoding="utf-8"))
        modos.add(e.get("modo"))
        if e.get("erro") or not e.get("resultado"):
            execs.append(e)
            continue
        if e["cenario"] not in casos:
            avisos.append(f"{arq.name}: cenário {e['cenario']} sem gabarito conhecido; ignorado")
            continue
        cen, gab = casos[e["cenario"]]
        rd = e["resultado"]
        reg = cen["cenario"].regiao
        cfg = cfgs.setdefault(reg, carregar_regiao(reg))
        chks = avaliar(gab, rd)
        antes = {c["id"]: c["resultado"] for c in e.get("checagens") or []}
        depois = {c["id"]: c["resultado"] for c in chks}
        if antes and antes != depois:
            dif = {k: (antes.get(k), depois.get(k)) for k in depois if antes.get(k) != depois.get(k)}
            avisos.append(f"{arq.name}: checagens diferentes da execução original: {dif}")
        e = {**e, "checagens": chks, "metricas": metricas_completas(cen["meta"], gab, chks, rd, cfg)}
        execs.append(e)
    if not execs:
        raise SystemExit(f"Nenhum <cenario>__<variante>__r<n>.json em {pasta}")
    if len(modos) > 1:
        avisos.append(f"modos misturados na pasta: {sorted(map(str, modos))}")
    return agregar(execs), execs, avisos


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", help="pasta de resultados (eval/resultados/<timestamp>_<modo>)")
    ap.add_argument("--saida", help="onde gravar resumo_recalculado.json e tabela_recalculada.md (padrão: a pasta)")
    a = ap.parse_args(argv)
    pasta = Path(a.pasta)
    ag, execs, avisos = recalcular(pasta)
    modo = next((e.get("modo") for e in execs if e.get("modo")), "?")
    saida = Path(a.saida) if a.saida else pasta
    saida.mkdir(parents=True, exist_ok=True)
    resumo = {"origem": str(pasta), "modo": modo, "recalculado_por": "eval/recalcular.py", "variantes": VARIANTES,
              "execucoes": len(execs), "avisos": avisos, "agregado": ag}
    (saida / "resumo_recalculado.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1, default=str),
                                                   encoding="utf-8")
    tab = tabela_md(ag, modo)
    (saida / "tabela_recalculada.md").write_text(tab, encoding="utf-8")
    print(tab)
    for av in avisos:
        print("AVISO:", av, file=sys.stderr)
    print(f"{len(execs)} execuções; gravado em {saida}/resumo_recalculado.json e tabela_recalculada.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
