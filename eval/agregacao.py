"""Agregação e tabela da ablação (sem dependência do código dos agentes): usada por run_ablacao.py e
recalcular.py. Definições das métricas em eval/README.md."""
from __future__ import annotations

from collections import Counter, defaultdict

from eval.checagem import desvio, metricas_escalacao, resumo_execucao

VARIANTES = {
    "A": "alocador_simples sozinho",
    "B": "Planejador + checador (usar_critico_llm=False)",
    "C": "completo (Crítico + Analista + H-MEM)",
    "D": "C sem H-MEM (usar_memoria=False)",
}


def metricas_completas(meta: dict, gab: dict, chks: list[dict], rd: dict, cfg) -> dict:
    """Métricas de uma execução: as de ``resumo_execucao`` mais as de sobre-escalação."""
    m = resumo_execucao(chks, rd, cfg.eta_max_h)
    m.update(metricas_escalacao(meta, gab, rd, cfg))
    return m


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
        passou_rep = {r: sum(m["passou"] for m in v) for r, v in sorted(reps.items())}
        aplic_rep = {r: sum(m["aplicaveis"] for m in v) for r, v in sorted(reps.items())}
        ssum = lambda k: sum(m.get(k) or 0 for m in ms)  # noqa: E731
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
            # por execução única (uma repetição de todos os cenários): "x/27" em vez de "x/81"
            "acerto_por_repeticao": {f"r{r}": f"{passou_rep[r]}/{aplic_rep[r]}" for r in passou_rep},
            "acerto_por_execucao_media": _media(list(passou_rep.values())),
            "acerto_por_execucao_aplicaveis": sorted(set(aplic_rep.values())),
            "acerto_por_execucao_desvio": desvio(list(passou_rep.values())),
            "acerto_por_execucao_min_max": [min(passou_rep.values()), max(passou_rep.values())],
            # sobre-escalação (somas sobre as execuções; definição em eval/README.md)
            "escaladas": ssum("escaladas"),
            "sobre_escaladas": ssum("sobre_escaladas"),
            "escaladas_sem_exposicao": ssum("escaladas_sem_exposicao"),
            "escaladas_com_recurso_livre": ssum("escaladas_com_recurso_livre"),
            "escaladas_com_troca": ssum("escaladas_com_troca"),
            "escaladas_so_com_reserva": ssum("escaladas_so_com_reserva"),
            "escaladas_e_atendidas": ssum("escaladas_e_atendidas"),
            "escalacoes_sem_alvo": ssum("escalacoes_sem_alvo"),
            "escalacoes_impasse": ssum("escalacoes_impasse"),
            "credito_escalacao": ssum("credito_escalacao"),
            "execucoes_com_sobre_escalacao": sum(1 for m in ms if (m.get("sobre_escaladas") or 0) > 0),
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
    linhas += ["", "Por execução única (uma repetição dos cenários; o total acima soma as repetições):", "",
               "| Variante | Média por execução | r1 / r2 / r3 | Mín–máx | Desvio (checagens) |", "|---|---|---|---|---|"]
    for var, v in vs.items():
        apl = "/".join(str(x) for x in v.get("acerto_por_execucao_aplicaveis") or [])
        mm = v.get("acerto_por_execucao_min_max") or ["", ""]
        linhas.append(f"| **{var}** | {v.get('acerto_por_execucao_media')}/{apl} | "
                      f"{' / '.join((v.get('acerto_por_repeticao') or {}).values())} | {mm[0]}–{mm[1]} | "
                      f"{v.get('acerto_por_execucao_desvio')} |")
    linhas += ["", "Escalação (somas sobre as execuções; definições em eval/README.md, \"Sobre-escalação\"):", "",
               "| Variante | Ocorrências escaladas | Sobre-escaladas | Sem exposição | Com recurso livre viável | "
               "Só quebrando a reserva (info) | Com troca possível (info) | Citadas no motivo mas atendidas | Escalações sem alvo | Por impasse | "
               "Checagens que passaram só por escalar | Execuções com sobre-escalação |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for var, v in vs.items():
        linhas.append(f"| **{var}** | {v.get('escaladas')} | {v.get('sobre_escaladas')} | "
                      f"{v.get('escaladas_sem_exposicao')} | {v.get('escaladas_com_recurso_livre')} | "
                      f"{v.get('escaladas_so_com_reserva')} | {v.get('escaladas_com_troca')} | "
                      f"{v.get('escaladas_e_atendidas')} | "
                      f"{v.get('escalacoes_sem_alvo')} | {v.get('escalacoes_impasse')} | "
                      f"{v.get('credito_escalacao')} | {v.get('execucoes_com_sobre_escalacao')}/{v['execucoes']} |")
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
