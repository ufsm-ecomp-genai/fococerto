"""Memória derivada dos dados (H-MEM, especificação seção 7): o que o plano do período anterior deixou sem
recurso e o que os dados novos do FIRMS mostraram depois.

Quem chama: a CLI ``run``, antes de ``executar_periodo`` do período P (a assinatura do contrato, seção 10, não
muda). Passos:

1. ``plano_anterior(...)`` acha o plano do período P-1: primeiro as decisões **aprovadas** (``aprovar``, quando o
   repositório consegue lê-las, como o ``RepositorioCache``), senão o ``plano.json`` salvo pela CLI em
   ``<saida>/<regiao>/<P-1>/``. O ``plano.json`` existe com qualquer repositório (cache ou Zetaris).
2. ``aprender_entre_periodos(...)`` compara cada ocorrência de P-1 com a mesma célula em P (dados do repositório):
   - sem recurso em P-1 (``nao_atendidas``, inclui as escaladas) e cresceu ou continuou forte em P: grava
     ``tipo="derivada"`` com "cresceu"/"persistiu forte", o id da célula e a localidade (o recall do H-MEM compara
     palavras). O ``interpretar_memorias`` lê isso como reforço (+0,15 de prioridade) e o grafo puxa a célula
     para a lista do período mesmo fora do top 15;
   - com recurso em P-1 e diminuiu ou sumiu em P: grava uma derivada informativa (confiança menor, sem reforço).
   - reignição (independe do plano de P-1): para as ocorrências de P (top 15 + as citadas pelo id numa derivada
     ativa de reforço, as que o grafo puxa), ``historico_celula`` mostra focos em P depois de pelo menos um dia
     sem foco, e a célula já tinha queimado nos 7 dias anteriores (pelo menos ``REIGNICAO_MIN_FOCOS_ANTES``
     focos). Grava derivada de reforço com "reignição", o id da célula e a localidade.
   Idempotente: não grava de novo a mesma célula com a mesma ``fonte`` (``aprendizado:<P-1>-><P>``).

Os limiares são declarados aqui (não dependem de cenário nem de célula).
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app.core.models import Designacao, Memoria, Ocorrencia, Plano
from app.tools.memorias import REFORCO
from app.tools.texto import contem_termo, norm

TOP_TODAS = 5000          # todas as ocorrências do dia (dia típico do Tocantins: ~200)
CRESCEU_MIN_FOCOS = 3     # cresceu = mais focos que em P-1 e pelo menos 3 em P
FORTE_MIN_FOCOS = 5       # persistiu forte = pelo menos 5 focos em P e não caiu mais de 30%
FORTE_FRACAO = 0.7
CONFIANCA_REFORCO = 0.8   # dado observado (FIRMS), mas a causa (falta de recurso) é inferida
CONFIANCA_ATENDIDA = 0.6
TOP_PERIODO = 15                # o que o grafo põe na lista do período (grafo.TOP)
JANELA_REIGNICAO_DIAS = 7       # dias antes de P olhados no historico_celula
REIGNICAO_MIN_FOCOS_ANTES = 3   # foco isolado não é "fogo que voltou"
REIGNICAO_MAX_DIAS_ATIVA = 2    # a queima atual começou há no máximo 2 dias (P-1 ou P), depois do intervalo


def periodo_anterior(periodo: str) -> str | None:
    try:
        return (date.fromisoformat(periodo[:10]) - timedelta(days=1)).isoformat()
    except ValueError:
        return None


# ---------------------------------------------------------------- onde está o plano de P-1
def _plano_das_decisoes(linhas: list[dict], regiao: str, periodo: str) -> Plano | None:
    """Última aprovação do período (as linhas de uma aprovação têm o mesmo ``criado_em``)."""
    do_periodo = [l for l in linhas if l.get("periodo") == periodo and l.get("regiao", regiao) == regiao]
    if not do_periodo:
        return None
    ultima = max(str(l.get("criado_em", "")) for l in do_periodo)
    lote = [l for l in do_periodo if str(l.get("criado_em", "")) == ultima]
    ds = []
    for l in lote:
        if l.get("acao") != "designar":
            continue
        try:
            ev = json.loads(l.get("evidencias") or "[]")
        except (TypeError, ValueError):
            ev = []
        ds.append(Designacao(recurso_id=l["recurso_id"], ocorrencia_id=l["ocorrencia_id"],
                             ordem=int(l.get("ordem") or len(ds) + 1), eta_h=float(l.get("eta_h") or 0.0),
                             justificativa=l.get("motivo") or "", evidencias=ev))
    return Plano(periodo=periodo, regiao=regiao, designacoes=ds,
                 reserva=[l["recurso_id"] for l in lote if l.get("acao") == "reserva" and l.get("recurso_id")],
                 nao_atendidas=[l["ocorrencia_id"] for l in lote
                                if l.get("acao") == "nao_atendida" and l.get("ocorrencia_id")],
                 resumo="decisões aprovadas", rodada=int(lote[0].get("rodada") or 1))


def plano_anterior(regiao: str, periodo: str, repo: Any, pasta_saida: str | Path | None = None
                   ) -> tuple[Plano | None, str | None]:
    """(plano de P-1, origem) ou (None, None). Origem: ``decisoes_aprovadas`` ou o caminho do ``plano.json``."""
    ant = periodo_anterior(periodo)
    if not ant:
        return None, None
    ler = getattr(repo, "decisoes_salvas", None)
    if callable(ler):
        try:
            p = _plano_das_decisoes(ler(regiao), regiao, ant)
            if p is not None:
                return p, "decisoes_aprovadas"
        except Exception:  # noqa: BLE001 - estado local ilegível: tenta o plano.json
            pass
    if pasta_saida is not None:
        arq = Path(pasta_saida) / regiao / ant / "plano.json"
        if arq.exists():
            dados = json.loads(arq.read_text(encoding="utf-8"))
            return Plano(**dados["plano"]), str(arq)
    return None, None


# ---------------------------------------------------------------- comparação e gravação
def _localidade(o: Ocorrencia | None) -> str:
    if o is None or not o.localidades:
        return "sem localidade próxima"
    loc = min(o.localidades, key=lambda l: l.get("dist_km") if l.get("dist_km") is not None else 1e9)
    return loc.get("nome") or "sem localidade próxima"


def _textos_da_fonte(memoria: Any, regiao: str, fonte: str) -> list[str]:
    """Textos (normalizados) das derivadas já gravadas com esta ``fonte`` (idempotência)."""
    return [norm(m.texto) for m in memoria.listar(regiao) if m.tipo == "derivada" and m.fonte == fonte]


def comparar(plano: Plano, ant: dict[str, Ocorrencia], atu: dict[str, Ocorrencia]) -> list[dict]:
    """Achados (sem gravar): uma entrada por célula de P-1 que vale lembrar."""
    designadas = {d.ocorrencia_id for d in plano.designacoes}
    sem = list(dict.fromkeys(plano.nao_atendidas)) or [oid for oid in ant if oid not in designadas]
    achados = []
    for oid in sem:
        if oid in designadas:
            continue
        n0 = ant[oid].n_focos if oid in ant else 0
        n1 = atu[oid].n_focos if oid in atu else 0
        if n1 > n0 and n1 >= CRESCEU_MIN_FOCOS:
            achados.append({"celula": oid, "tipo": "cresceu", "n_antes": n0, "n_depois": n1})
        elif n1 >= FORTE_MIN_FOCOS and n1 >= FORTE_FRACAO * n0:
            achados.append({"celula": oid, "tipo": "persistiu", "n_antes": n0, "n_depois": n1})
    for oid in dict.fromkeys(d.ocorrencia_id for d in plano.designacoes):
        n0 = ant[oid].n_focos if oid in ant else 0
        n1 = atu[oid].n_focos if oid in atu else 0
        if n0 > 0 and n1 < n0:
            achados.append({"celula": oid, "tipo": "atendida_diminuiu", "n_antes": n0, "n_depois": n1})
    return achados


def detectar_reignicao(hist: list[dict], periodo: str) -> dict | None:
    """Série diária (do mais antigo a P) -> achado de reignição ou None.

    Reignição: a queima atual (dias seguidos com foco terminando em P, no máximo ``REIGNICAO_MAX_DIAS_ATIVA``)
    vem depois de pelo menos um dia sem foco, e antes desse intervalo a célula teve pelo menos
    ``REIGNICAO_MIN_FOCOS_ANTES`` focos na janela."""
    if not hist or hist[-1].get("dia") != periodo[:10] or not hist[-1].get("n_focos"):
        return None
    i = len(hist) - 1
    while i >= 0 and hist[i].get("n_focos", 0) > 0:
        i -= 1
    ativa = hist[i + 1:]
    if i < 0 or len(ativa) > REIGNICAO_MAX_DIAS_ATIVA:
        return None
    j = i
    while j >= 0 and hist[j].get("n_focos", 0) == 0:
        j -= 1
    antes = [h for h in hist[:j + 1] if h.get("n_focos", 0) > 0]
    n_antes = sum(h["n_focos"] for h in antes)
    if not antes or n_antes < REIGNICAO_MIN_FOCOS_ANTES:
        return None
    return {"tipo": "reignicao", "n_antes": n_antes, "n_depois": int(hist[-1]["n_focos"]),
            "dias_antes": [h["dia"] for h in antes], "dias_sem_foco": i - j,
            "n_atual": sum(h["n_focos"] for h in ativa)}


def _celulas_reforco(memoria: Any, regiao: str) -> set[str]:
    """Células citadas pelo id numa derivada de reforço ainda ativa (as que o grafo puxa para a lista)."""
    import re
    todas = [m for m in memoria.listar(regiao) if m.regiao == regiao]
    por = getattr(memoria, "substituida_por", None)
    subst = {m.supersedes for m in todas if m.supersedes} | (
        {m.id for m in todas if por(m.id)} if callable(por) else set())
    return {c.rstrip("._") for m in todas if m.tipo == "derivada" and m.id not in subst
            and REFORCO.search(norm(m.texto)) for c in re.findall(r"cel_[-\d_.]+", m.texto)}


def reignicoes(regiao: str, periodo: str, atu: dict[str, Ocorrencia], repo: Any, memoria: Any) -> list[dict]:
    """Achados de reignição nas ocorrências de P (top 15 + puxadas por memória). O repositório precisa ter
    consultado P por último (fim do ``historico_celula``)."""
    top = sorted(atu.values(), key=lambda o: -o.prioridade)[:TOP_PERIODO]
    ids = list(dict.fromkeys([o.id for o in top] + sorted(c for c in _celulas_reforco(memoria, regiao) if c in atu)))
    achados = []
    for oid in ids:
        try:
            hist = repo.historico_celula(oid, JANELA_REIGNICAO_DIAS + 1)
        except Exception:  # noqa: BLE001 - sem histórico, sem achado
            continue
        a = detectar_reignicao(hist, periodo)
        if a is not None:
            achados.append({"celula": oid, **a})
    return achados


def texto_memoria(a: dict, localidade: str, p_ant: str, p_atu: str) -> str:
    cel, n0, n1 = a["celula"], a["n_antes"], a["n_depois"]
    if a["tipo"] == "reignicao":
        dias = ", ".join(d[8:10] + "/" + d[5:7] for d in a["dias_antes"])
        return (f"{cel} ({localidade}) teve reignição em {p_atu}: voltou a queimar com {n1} focos depois de "
                f"{a['dias_sem_foco']} dia(s) sem foco; antes tinha {n0} focos ({dias}). O fogo anterior não foi "
                f"extinto: tratar como reignição, não como foco novo")
    if a["tipo"] == "cresceu":
        return f"{cel} ({localidade}) ficou sem recurso em {p_ant} e cresceu de {n0} para {n1} focos em {p_atu}"
    if a["tipo"] == "persistiu":
        return (f"{cel} ({localidade}) ficou sem recurso em {p_ant} e persistiu forte em {p_atu}: "
                f"{n0} para {n1} focos")
    return f"{cel} ({localidade}) recebeu recurso em {p_ant} e diminuiu de {n0} para {n1} focos em {p_atu}"


def aprender_entre_periodos(regiao: str, periodo: str, plano: Plano, repo: Any, memoria: Any,
                            log: Any = None) -> list[Memoria]:
    """Grava as memórias derivadas da transição ``plano.periodo`` -> ``periodo``. Devolve as gravadas agora."""
    p_ant = plano.periodo
    fonte = f"aprendizado:{p_ant}->{periodo}"
    # P-1 antes de P: o repositório usa o último período consultado como fim do historico_celula.
    ant = {o.id: o for o in repo.ocorrencias(regiao, p_ant, top=TOP_TODAS)}
    atu = {o.id: o for o in repo.ocorrencias(regiao, periodo, top=TOP_TODAS)}
    achados = comparar(plano, ant, atu)
    vistos = {a["celula"] for a in achados}
    achados += [a for a in reignicoes(regiao, periodo, atu, repo, memoria) if a["celula"] not in vistos]
    ja = _textos_da_fonte(memoria, regiao, fonte)
    gravadas, puladas = [], []
    for a in achados:
        if any(contem_termo(t, a["celula"]) for t in ja):
            puladas.append(a["celula"])
            continue
        loc = _localidade(atu.get(a["celula"]) or ant.get(a["celula"]))
        texto = texto_memoria(a, loc, p_ant, periodo)
        conf = CONFIANCA_ATENDIDA if a["tipo"] == "atendida_diminuiu" else CONFIANCA_REFORCO
        m = memoria.gravar(regiao, texto, tipo="derivada", fonte=fonte, confianca=conf)
        gravadas.append(m)
        if log is not None:
            por = getattr(memoria, "substituida_por", None)
            log.evento("sistema", "memoria_gravada", {
                "memoria_id": m.id, "texto": texto, "tipo": "derivada", "fonte": fonte, "confianca": conf,
                "achado": a["tipo"], "celula": a["celula"], "localidade": loc,
                "n_focos_antes": a["n_antes"], "n_focos_depois": a["n_depois"],
                "conflitos": list(getattr(memoria, "ultimos_conflitos", []) or []),
                "substituida_por": por(m.id) if callable(por) else None})
    if log is not None:
        log.evento("sistema", "consulta", {
            "consulta": "aprendizado_entre_periodos", "de": p_ant, "para": periodo, "fonte": fonte,
            "sem_recurso_em_p_anterior": len(plano.nao_atendidas), "designadas_em_p_anterior":
                len(plano.designacoes), "achados": len(achados), "gravadas": [m.id for m in gravadas],
            "ja_existiam": puladas})
    return gravadas
