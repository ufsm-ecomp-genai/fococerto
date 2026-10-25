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
from eval.checagem import RAIZ_EVAL, avaliar, desvio, listar_casos, resumo_execucao

VARIANTES = {
    "A": "alocador_simples sozinho",
    "B": "Planejador + checador (usar_critico_llm=False)",
    "C": "completo (Crítico + Analista + H-MEM)",
    "D": "C sem H-MEM (usar_memoria=False)",
}


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
    try:
        if variante == "A":
            res = rodar_A(cfg, cen, repo, log, inj, registro)
        else:
            memoria = carregar_memorias(meta, cen.regiao)
            with injecao_no_planejador(inj, registro):
                res = grafo.executar_periodo(cfg, cen, repo, memoria, log, modo=modo,
                                             usar_critico_llm=(variante != "B"), usar_memoria=(variante != "D"))
    except Exception as e:  # noqa: BLE001 - uma execução que quebra vira linha de erro, não derruba a ablação
        erro = f"{type(e).__name__}: {e}"
        res = None
    dur = round(time.perf_counter() - t0, 3)
    saida = {"cenario": meta["id"], "tipo": meta["tipo"], "variante": variante, "repeticao": rep, "modo": modo,
             "duracao_s": dur, "log_path": str(log.caminho), "erro": erro}
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
        saida.update(checagens=chks, metricas=resumo_execucao(chks, rd, cfg.eta_max_h),
                     contagem_agentes=contar_agentes(log.caminho), memorias_usadas=[m["id"] for m in rd["memorias_usadas"]],
                     injecao_aplicada=registro or None, resultado=rd)
    (pasta / f"{meta['id']}__{variante}__r{rep}.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return saida


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


# ------------------------------------------------------------------ agregação
def agregar(execs: list[dict]) -> dict:
    por = defaultdict(list)
    for e in execs:
        por[(e["cenario"], e["variante"])].append(e)
    linhas = {}
    for (cid, var), es in sorted(por.items()):
        ok = [e for e in es if not e["erro"]]
        ms = [e["metricas"] for e in ok]
        linhas[f"{cid}|{var}"] = {
            "cenario": cid, "variante": var, "n": len(es), "erros": len(es) - len(ok),
            "acerto_medio": _media([m["acerto"] for m in ms]), "acerto_desvio": desvio([m["acerto"] for m in ms]),
            "eta_pond_medio": _media([m["eta_ponderado_h"] for m in ms]),
            "eta_pond_desvio": desvio([m["eta_ponderado_h"] for m in ms]),
            "planos_identicos": len({tuple(m["pares"]) for m in ms}) <= 1,
            "checagens": {c["id"]: [x["resultado"] for e in ok for x in e["checagens"] if x["id"] == c["id"]]
                          for c in (ok[0]["checagens"] if ok else [])},
        }
    variantes = {}
    for var in VARIANTES:
        es = [e for e in execs if e["variante"] == var and not e["erro"]]
        if not es:
            continue
        ms = [e["metricas"] for e in es]
        soma = lambda cat, k: sum(m["por_categoria"][cat][k] for m in ms)  # noqa: E731
        reps = defaultdict(list)
        for e in es:
            reps[e["repeticao"]].append(e["metricas"])
        acerto_por_rep = [sum(m["passou"] for m in v) / max(1, sum(m["aplicaveis"] for m in v)) for v in reps.values()]
        variantes[var] = {
            "descricao": VARIANTES[var], "execucoes": len(es),
            "erros": sum(1 for e in execs if e["variante"] == var and e["erro"]),
            "acerto": f"{sum(m['passou'] for m in ms)}/{sum(m['aplicaveis'] for m in ms)}",
            "acerto_pct": round(100 * sum(m["passou"] for m in ms) / max(1, sum(m["aplicaveis"] for m in ms)), 1),
            "decisao": f"{soma('decisao', 'passou')}/{soma('decisao', 'aplicaveis')}",
            "deteccao": f"{soma('deteccao', 'passou')}/{soma('deteccao', 'aplicaveis')}",
            "alarmes_falsos_gabarito": sum(m["alarmes_falsos_gabarito"] for m in ms),
            "alarme_falso_aplicaveis": soma("alarme_falso", "aplicaveis"),
            "citacoes_falsas": sum(m["citacoes_falsas"] for m in ms),
            "eta_pond_medio_h": _media([m["eta_ponderado_h"] for m in ms]),
            "eta_pond_log_medio_h": _media([m["eta_ponderado_log_h"] for m in ms]),
            "rodadas_media": _media([m["rodadas"] for m in ms]),
            "status_escala": sum(1 for m in ms if m["status"] == "escala"),
            "escalacoes_media": _media([m["escalacoes"] for m in ms]),
            "desvio_acerto_entre_repeticoes": desvio(acerto_por_rep),
            "cenarios_com_planos_diferentes_entre_repeticoes": sum(
                1 for k, l in linhas.items() if l["variante"] == var and not l["planos_identicos"]),
            "agentes": dict(sum((Counter(e["contagem_agentes"]) for e in es), Counter())),
            "duracao_total_s": round(sum(e["duracao_s"] for e in es), 2),
        }
    return {"variantes": variantes, "por_cenario": linhas}


def _media(xs):
    v = [x for x in xs if x is not None]
    return round(sum(v) / len(v), 3) if v else None


# ------------------------------------------------------------------ estimativa do modo LLM
def estimar(agregado: dict, n_cenarios: int, repeticoes: int, latencia_s: float) -> dict:
    """A partir dos pontos de decisão observados no offline (planejador, crítico, analista por execução)."""
    out = {"latencia_s_suposta": latencia_s, "repeticoes": repeticoes, "por_variante": {}}
    tot_min = tot_max = 0.0
    for var, v in agregado["variantes"].items():
        ag, n = v["agentes"], v["execucoes"]
        if var == "A":
            continue
        plan = ag.get("planejador", 0) / n
        crit = ag.get("critico", 0) / n if var != "B" else 0.0  # B não chama o Crítico LLM
        anal = ag.get("analista", 0) / n
        base = plan + crit + anal  # 1 chamada por ponto de decisão, sem retry
        pior = 2 * (plan + crit) + 4 * anal  # retry de JSON em tudo; Analista pede mais_consultas (2 chamadas)
        out["por_variante"][var] = {"chamadas_por_execucao_min": round(base, 2), "chamadas_por_execucao_max": round(pior, 2),
                                    "planejador": round(plan, 2), "critico": round(crit, 2), "analista": round(anal, 2)}
        tot_min += base * n_cenarios * repeticoes
        tot_max += pior * n_cenarios * repeticoes
    out["chamadas_total_min"], out["chamadas_total_max"] = round(tot_min), round(tot_max)
    out["horas_min"], out["horas_max"] = round(tot_min * latencia_s / 3600, 2), round(tot_max * latencia_s / 3600, 2)
    out["teto_teorico_por_execucao"] = "3 rodadas × (1 Planejador + 2 Crítico + 3 Analistas × 2) × 2 retries = 54"
    out["obs"] = ("Estimativa a partir da trajetória OFFLINE: no modo LLM o número de rodadas e de pareceres pode ser "
                  "outro. A variante A não chama LLM; a B só chama o Planejador.")
    return out


# ------------------------------------------------------------------ tabela
def tabela_md(agregado: dict, modo: str) -> str:
    vs = agregado["variantes"]
    linhas = [f"Modo: **{modo}**" + (" (agentes offline determinísticos: validação do pipeline, não o resultado final)"
                                     if modo == "offline" else ""), "",
              "| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | "
              "ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | "
              "Cenários com planos ≠ entre rep. |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for var, v in vs.items():
        linhas.append(f"| **{var}** | {v['acerto']} ({v['acerto_pct']}%) | {v['decisao']} | {v['deteccao']} | "
                      f"{v['alarmes_falsos_gabarito']}/{v['alarme_falso_aplicaveis']} | {v['citacoes_falsas']} | "
                      f"{v['eta_pond_medio_h']} | {v['eta_pond_log_medio_h']} | {v['rodadas_media']} | "
                      f"{v['status_escala']}/{v['execucoes']} | {v['escalacoes_media']} | "
                      f"{v['desvio_acerto_entre_repeticoes']} | {v['cenarios_com_planos_diferentes_entre_repeticoes']} |")
    linhas += ["", "Por cenário (checagens; P = passou, F = falhou, – = não se aplica, ! = inválido; "
                   "uma letra por repetição quando diferem):", "",
               "| Cenário | " + " | ".join(vs) + " |", "|---|" + "---|" * len(vs)]
    sigla = {"passou": "P", "falhou": "F", "nao_se_aplica": "–", "invalido": "!"}
    cenarios = sorted({l["cenario"] for l in agregado["por_cenario"].values()})
    for cid in cenarios:
        cel = []
        for var in vs:
            l = agregado["por_cenario"].get(f"{cid}|{var}")
            if l is None:
                cel.append("")
                continue
            partes = []
            for chk, rs in l["checagens"].items():
                s = {sigla[r] for r in rs}
                partes.append(f"{chk}:{''.join(sigla[r] for r in rs) if len(s) > 1 else next(iter(s), '?')}")
            cel.append(" ".join(partes) + (f" (ETA {l['eta_pond_medio']})" if l["eta_pond_medio"] is not None else ""))
        linhas.append(f"| {cid} | " + " | ".join(cel) + " |")
    return "\n".join(linhas) + "\n"


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
    casos = listar_casos(a.cenarios)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pasta = Path(a.saida) / f"{ts}_{modo}{'_estimativa' if a.estimar else ''}"
    (pasta / "logs").mkdir(parents=True, exist_ok=True)
    print(f"{len(casos)} cenários × {len(a.variantes)} variantes × {reps} repetições, modo {modo} → {pasta}")
    execs = []
    for caso in casos:
        for var in a.variantes:
            for r in range(1, reps + 1):
                e = executar(caso, var, r, modo, pasta)
                execs.append(e)
                m = e.get("metricas") or {}
                print(f"  {e['cenario']:38s} {var} r{r}: " + (f"ERRO {e['erro']}" if e["erro"] else
                      f"{m['passou']}/{m['aplicaveis']} checagens, ETA pond. {m['eta_ponderado_h']} h, "
                      f"status {m['status']}, rodadas {m['rodadas']} ({e['duracao_s']} s)"))
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
