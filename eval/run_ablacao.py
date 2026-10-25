"""Ablação do FocoCerto: variantes A/B/C/D × cenários × repetições, conferidas contra os gabaritos.

    .venv/bin/python -m eval.run_ablacao --modo offline --repeticoes 3
    .venv/bin/python -m eval.run_ablacao --modo llm --repeticoes 3        # LLM_PROVIDER=nightshift
    .venv/bin/python -m eval.run_ablacao --estimar                        # chamadas LLM e tempo, sem rodar LLM

Método e definições: eval/README.md. Saída: eval/resultados/<timestamp>_<modo>/.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.agents import grafo, planejador
from app.agents.base import resumo_plano
from app.core.config import regiao as carregar_regiao
from app.core.logging import LogExecucao
from app.core.models import Plano, ResultadoPeriodo
from app.data.repositorio import RepositorioCache
from app.memory_client import MemoriaLocal
from app.tools.alocador import alocador_simples
from app.tools.monitor import monitor
from eval.agregacao import VARIANTES, agregar, estimar, metricas_completas, tabela_md  # noqa: F401
from eval.checagem import RAIZ_EVAL, avaliar, listar_casos



# ------------------------------------------------------------------ memória e injeção
def carregar_memorias(meta: dict, regiao: str) -> MemoriaLocal:
    mem = MemoriaLocal()
    ids: dict[str, str] = {}
    for m in meta.get("memorias_iniciais") or []:
        sup = ids.get(m["supersedes_ref"]) if m.get("supersedes_ref") else None
        if m.get("supersedes_ref") and sup is None:
            raise ValueError(f"supersedes_ref {m['supersedes_ref']!r} não aponta para memória anterior")
        gravada = mem.gravar(regiao, m["texto"], m["tipo"], m["fonte"], float(m.get("confianca", 1.0)), sup)
        if m.get("ref"):
            ids[m["ref"]] = gravada.id
    return mem


def injetar(plano: Plano, inj: dict, registro: dict) -> Plano:
    """Acrescenta inj['texto'] à justificativa da designação de inj['ocorrencia'] (ou da primeira)."""
    if not plano.designacoes:
        registro.update(rodada=plano.rodada, ocorrencia=None, recurso=None, texto=inj["texto"], obs="plano vazio")
        return plano
    alvo = next((d for d in plano.designacoes if d.ocorrencia_id == inj["ocorrencia"]), plano.designacoes[0])
    ds = [d.model_copy(update={"justificativa": d.justificativa.rstrip() + " " + inj["texto"]}) if d is alvo else d
          for d in plano.designacoes]
    registro.update(rodada=plano.rodada, ocorrencia=alvo.ocorrencia_id, recurso=alvo.recurso_id, texto=inj["texto"],
                    no_alvo=alvo.ocorrencia_id == inj["ocorrencia"])
    return plano.model_copy(update={"designacoes": ds})


@contextlib.contextmanager
def injecao_no_planejador(inj: dict | None, registro: dict):
    """Monkeypatch de planejador.decidir/decidir_offline só durante uma execução (rodada inj['rodada'])."""
    if not inj:
        yield
        return
    orig_llm, orig_off = planejador.decidir, planejador.decidir_offline
    rodada_alvo = int(inj.get("rodada", 1))

    def envolver(f):
        def g(ctx, rodada, *a, **kw):
            p = f(ctx, rodada, *a, **kw)
            return injetar(p, inj, registro) if rodada == rodada_alvo else p
        return g

    planejador.decidir, planejador.decidir_offline = envolver(orig_llm), envolver(orig_off)
    try:
        yield
    finally:
        planejador.decidir, planejador.decidir_offline = orig_llm, orig_off


# ------------------------------------------------------------------ execução de uma variante
def rodar_A(cfg, cen, repo, log: LogExecucao, inj: dict | None, registro: dict) -> ResultadoPeriodo:
    """Mesma preparação do grafo (top 15, monitor, bases do cenário) e só o alocador_simples."""
    log.evento("sistema", "inicio", {"variante": "A", "periodo": cen.periodo, "modo": "sem_llm"})
    atuais = repo.ocorrencias(cfg.nome, cen.periodo, top=grafo.TOP)[:grafo.TOP]
    ant = (date.fromisoformat(cen.periodo) - timedelta(days=1)).isoformat()
    try:
        anteriores = repo.ocorrencias(cfg.nome, ant, top=100)
    except Exception:  # noqa: BLE001 - igual ao grafo: sem período anterior, tudo é "nova"
        anteriores = []
    ocorrencias = monitor(atuais, anteriores)
    bases = repo.bases(cfg.nome)
    ids = {b.id for b in bases}
    bases = bases + [b for b in cen.bases if b.id not in ids]
    plano = alocador_simples(ocorrencias, cen.recursos, bases, cfg, cen.reserva, periodo=cen.periodo, regiao=cfg.nome)
    plano = plano.model_copy(update={"rodada": 1})
    if inj:
        plano = injetar(plano, inj, registro)
    log.evento("ferramenta", "proposta", {"origem": "alocador_simples", "plano": resumo_plano(plano)})
    log.evento("sistema", "fim", {"variante": "A", "designacoes": len(plano.designacoes)})
    return ResultadoPeriodo(plano=plano, status=None, ocorrencias=ocorrencias, bases=bases, recursos=cen.recursos,
                            rodadas=0, log_path=str(log.caminho))


def executar(caso: tuple[dict, dict], variante: str, rep: int, modo: str, pasta: Path) -> dict:
    cen_info, gab = caso
    meta, cen = cen_info["meta"], cen_info["cenario"]
    cfg = carregar_regiao(cen.regiao)
    repo = RepositorioCache()
    log = LogExecucao(cen.regiao, cen.periodo, execucao=f"{meta['id']}__{variante}__r{rep}", pasta=pasta / "logs")
    registro: dict = {}
    inj = meta.get("injecao")
    t0 = time.perf_counter()
    erro = None
    p1: dict | None = None
    try:
        memoria = carregar_memorias(meta, cen.regiao)
        if meta.get("periodo_anterior"):
            p1 = rodar_periodo_anterior(meta, cfg, cen, variante, rep, modo, pasta, memoria, repo, log)
        if variante == "A":
            res = rodar_A(cfg, cen, repo, log, inj, registro)
        else:
            with injecao_no_planejador(inj, registro):
                res = grafo.executar_periodo(cfg, cen, repo, memoria, log, modo=modo,
                                             usar_critico_llm=(variante != "B"), usar_memoria=(variante != "D"))
    except Exception as e:  # noqa: BLE001 - uma execução que quebra vira linha de erro, não derruba a ablação
        erro = f"{type(e).__name__}: {e}"
        res = None
    dur = round(time.perf_counter() - t0, 3)
    saida = {"cenario": meta["id"], "tipo": meta["tipo"], "variante": variante, "repeticao": rep, "modo": modo,
             "duracao_s": dur, "log_path": str(log.caminho), "erro": erro}
    if p1 is not None:
        saida["periodo_anterior"] = p1
    if res is not None:
        rd = res.model_dump(mode="json")
        rd["variante"] = variante
        rd["injecao_aplicada"] = registro or None
        if rd.get("status") is None and variante != "A":
            # o grafo não preenche ResultadoPeriodo.status (bug relatado); o status sai no prefixo do resumo
            pref = rd["plano"]["resumo"].split("]", 1)[0].lstrip("[")
            if pref in ("aprova", "escala"):
                rd["status"], rd["status_lido_do_resumo"] = pref, True
        chks = avaliar(gab, rd)
        saida.update(checagens=chks, metricas=metricas_completas(meta, gab, chks, rd, cfg),
                     contagem_agentes=contar_agentes(log.caminho), memorias_usadas=[m["id"] for m in rd["memorias_usadas"]],
                     injecao_aplicada=registro or None, resultado=rd)
    (pasta / f"{meta['id']}__{variante}__r{rep}.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return saida


def rodar_periodo_anterior(meta: dict, cfg, cen, variante: str, rep: int, modo: str, pasta: Path, memoria,
                           repo, log: LogExecucao) -> dict:
    """Modo de 2 períodos (``periodo_anterior`` no cenário): roda P1 com a mesma variante e os mesmos recursos,
    depois ``aprendizado.aprender_entre_periodos(P1 -> P2)`` grava as derivadas na ``memoria`` que P2 vai usar.
    Igual à CLI ``run`` (CONTRATOS, seção 15), mas com o plano de P1 vindo direto do resultado, sem disco.
    Na variante A (sem memória) e na D (``usar_memoria=False``) a memória é gerada mas não é lida em P2."""
    from app.agents.aprendizado import aprender_entre_periodos
    cen1 = cen.model_copy(update={"periodo": meta["periodo_anterior"]})
    log1 = LogExecucao(cen.regiao, cen1.periodo, execucao=f"{meta['id']}__{variante}__r{rep}__p1", pasta=pasta / "logs")
    repo1 = RepositorioCache()
    if variante == "A":
        res1 = rodar_A(cfg, cen1, repo1, log1, None, {})
    else:
        res1 = grafo.executar_periodo(cfg, cen1, repo1, memoria, log1, modo=modo,
                                      usar_critico_llm=(variante != "B"), usar_memoria=(variante != "D"))
    gravadas = aprender_entre_periodos(cen.regiao, cen.periodo, res1.plano, repo, memoria, log)
    return {"periodo": cen1.periodo, "log_path": str(log1.caminho), "status": res1.status,
            "pares": sorted(f"{d.recurso_id}->{d.ocorrencia_id}" for d in res1.plano.designacoes),
            "nao_atendidas": list(res1.plano.nao_atendidas),
            "memorias_aprendidas": [{"id": m.id, "texto": m.texto, "fonte": m.fonte, "confianca": m.confianca}
                                    for m in gravadas]}


def contar_agentes(caminho: Path) -> dict:
    """Pontos de decisão de agente no log (proxy do nº de chamadas LLM) e chamadas LLM reais."""
    c = Counter()
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        e = json.loads(linha)
        a, ev, d = e["agente"], e["evento"], e.get("dados") or {}
        if a == "planejador" and ev == "proposta":
            c["planejador"] += 1
        elif a == "critico" and ev in ("aprova", "rejeita", "escala", "consulta") and d.get("origem") != "checador":
            c["critico"] += 1
        elif a == "analista" and ev == "fim":
            c["analista"] += 1
        if ev == "llm_call" and d.get("status") not in ("fallback_offline", "json_invalido"):
            c["llm_calls"] += 1
    return dict(c)


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    from app.core.config import carregar_env
    carregar_env()  # mesmo .env da CLI (sem sobrescrever o ambiente)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modo", choices=["offline", "llm"], default="offline")
    ap.add_argument("--repeticoes", type=int, default=3)
    ap.add_argument("--variantes", default="ABCD")
    ap.add_argument("--cenarios", nargs="*", help="ids (padrão: todos)")
    ap.add_argument("--saida", default=str(RAIZ_EVAL / "resultados"))
    ap.add_argument("--dois-periodos", action="store_true",
                    help="usa eval/cenarios_2periodos/ (reignição em 2 períodos: a memória derivada vem do "
                         "aprendizado.py rodando o período anterior, não do cenário)")
    ap.add_argument("--retomar", help="pasta de uma execução interrompida: reaproveita as execuções já salvas "
                                      "e roda só as que faltam")
    ap.add_argument("--estimar", action="store_true",
                    help="roda 1 repetição offline e estima chamadas LLM e tempo do modo llm (não chama LLM)")
    ap.add_argument("--latencia-s", type=float, default=float(os.environ.get("EVAL_LATENCIA_S", "30")),
                    help="latência média suposta por chamada LLM, para a estimativa (padrão 30 s)")
    a = ap.parse_args(argv)

    modo = "offline" if a.estimar else a.modo
    if modo == "offline":
        os.environ["LLM_PROVIDER"] = "offline"  # garante que nenhuma chamada LLM sai daqui
    elif (os.environ.get("LLM_PROVIDER") or "").lower() != "nightshift":
        print("Modo llm exige LLM_PROVIDER=nightshift (e METERLESS_BASE_URL/METERLESS_RUNTIME_TOKEN).", file=sys.stderr)
        return 2
    reps = 1 if a.estimar else a.repeticoes
    if a.dois_periodos:
        casos = listar_casos(a.cenarios, RAIZ_EVAL / "cenarios_2periodos", RAIZ_EVAL / "gabaritos_2periodos")
    else:
        casos = listar_casos(a.cenarios)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pasta = Path(a.retomar) if a.retomar else Path(a.saida) / f"{ts}_{modo}{'_2periodos' if a.dois_periodos else ''}{'_estimativa' if a.estimar else ''}"
    (pasta / "logs").mkdir(parents=True, exist_ok=True)
    print(f"{len(casos)} cenários × {len(a.variantes)} variantes × {reps} repetições, modo {modo} → {pasta}")
    execs = []
    for caso in casos:
        for var in a.variantes:
            for r in range(1, reps + 1):
                nome = f"{caso[0]['meta']['id']}__{var}__r{r}"
                salvo = pasta / f"{nome}.json"
                if a.retomar and salvo.exists():
                    e = json.loads(salvo.read_text(encoding="utf-8"))
                else:
                    (pasta / "logs" / f"{nome}.jsonl").unlink(missing_ok=True)  # log parcial de uma execução cortada
                    e = executar(caso, var, r, modo, pasta)
                execs.append(e)
                m = e.get("metricas") or {}
                print(f"  {e['cenario']:38s} {var} r{r}: " + (f"ERRO {e['erro']}" if e["erro"] else
                      f"{m['passou']}/{m['aplicaveis']} checagens, ETA pond. {m['eta_ponderado_h']} h, "
                      f"status {m['status']}, rodadas {m['rodadas']} ({e['duracao_s']} s)"))
                if e.get("periodo_anterior"):
                    p1 = e["periodo_anterior"]
                    print(f"      P1 {p1['periodo']}: {len(p1['pares'])} designações, "
                          f"{len(p1['memorias_aprendidas'])} memória(s) aprendida(s): "
                          + "; ".join(x["texto"] for x in p1["memorias_aprendidas"]))
    ag = agregar(execs)
    resumo = {"modo": modo, "timestamp_utc": ts, "repeticoes": reps, "cenarios": [c[0]["meta"]["id"] for c in casos],
              "variantes": VARIANTES, "agregado": ag,
              "estimativa_llm": estimar(ag, len(casos), a.repeticoes if not a.estimar else 3, a.latencia_s)}
    (pasta / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (pasta / "tabela.md").write_text(tabela_md(ag, modo), encoding="utf-8")
    print(tabela_md(ag, modo))
    print("Estimativa do modo llm:", json.dumps(resumo["estimativa_llm"], ensure_ascii=False, indent=1))
    print(f"Resultados em {pasta}")
    return 0 if not any(e["erro"] for e in execs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
