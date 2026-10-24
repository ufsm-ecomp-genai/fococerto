"""Execução de um período: Planejador ⇄ (checar_regras + checar_citacoes) ⇄ Crítico ⇄ Analista (LangGraph).

Interface: docs/CONTRATOS.md, seção 10. No máximo 3 rodadas Planejador→Crítico. Escalação obrigatória quando há
população exposta sem recurso viável (regra rígida insolúvel) ou impasse após 3 rodadas; o Crítico também pode
escalar em zona cinzenta. O Analista é chamado pelo Crítico (no máximo uma vez por rodada).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents import analista, critico, planejador
from app.agents.base import Contexto, resumo_memoria, resumo_plano
from app.core.logging import LogExecucao
from app.core.models import (Base, Cenario, Memoria, Ocorrencia, ParecerAnalista, Plano, RegiaoCfg,
                             ResultadoPeriodo, VeredictoCritico, Violacao)
from app.tools.alocador import alocador_simples
from app.tools.citacoes import checar_citacoes
from app.tools.consultar import Consultor
from app.tools.memorias import interpretar_memorias
from app.tools.monitor import monitor
from app.tools.regras import INSOLUVEIS, checar_regras

MAX_RODADAS = 3
TOP = 15


class Repositorio(Protocol):  # docs/CONTRATOS.md, seção 3 (só o que o grafo usa)
    def ocorrencias(self, regiao: str, periodo: str, top: int = 15) -> list[Ocorrencia]: ...
    def bases(self, regiao: str) -> list[Base]: ...
    def historico_celula(self, ocorrencia_id: str, dias: int = 7) -> list[dict]: ...


class ClienteMemoria(Protocol):  # docs/CONTRATOS.md, seção 11
    def gravar(self, regiao: str, texto: str, tipo: str, fonte: str, confianca: float = 1.0,
               supersedes: str | None = None) -> Memoria: ...
    def recall(self, regiao: str, consulta: str, k: int = 5) -> tuple[list[Memoria], list[Memoria]]: ...
    def listar(self, regiao: str) -> list[Memoria]: ...


class Estado(TypedDict, total=False):
    rodada: int
    plano: Plano
    violacoes: list[Violacao]
    veredicto: VeredictoCritico | None
    analista_na_rodada: bool
    status: str
    escalacoes: list[dict]
    historico: list[dict]


def _periodo_anterior(periodo: str) -> str | None:
    try:
        return (date.fromisoformat(periodo[:10]) - timedelta(days=1)).isoformat()
    except ValueError:
        return None


def _ids_cel(textos: list[str]) -> list[str]:
    return sorted({m for t in textos for m in re.findall(r"cel_[-\d_.]+", t)})


def executar_periodo(regiao: RegiaoCfg, cenario: Cenario, repo: Repositorio, memoria: ClienteMemoria,
                     log: LogExecucao, modo: Literal["llm", "offline"] = "llm",
                     usar_critico_llm: bool = True, usar_memoria: bool = True) -> ResultadoPeriodo:
    periodo = cenario.periodo
    rotulo_modo = "llm" if modo == "llm" else "offline_deterministico"
    log.evento("sistema", "inicio", {"regiao": regiao.nome, "periodo": periodo, "modo": rotulo_modo,
                                     "usar_critico_llm": usar_critico_llm, "usar_memoria": usar_memoria,
                                     "cenario_simulado": cenario.simulado, "max_rodadas": MAX_RODADAS})

    # ------------------------------------------------------------ preparação (ferramentas, sem LLM)
    atuais = repo.ocorrencias(regiao.nome, periodo, top=TOP)[:TOP]
    anteriores: list[Ocorrencia] = []
    ant = _periodo_anterior(periodo)
    if ant:
        try:
            anteriores = repo.ocorrencias(regiao.nome, ant, top=100)
        except Exception as e:  # noqa: BLE001 - sem período anterior, tudo vira "nova"
            log.evento("ferramenta", "consulta", {"consulta": f"ocorrencias({ant})", "erro": str(e)})
    ocorrencias = monitor(atuais, anteriores)
    log.evento("ferramenta", "consulta", {"consulta": "monitor", "anterior": ant, "n_atuais": len(ocorrencias),
                                          "status": {o.id: o.status for o in ocorrencias}})
    bases = repo.bases(regiao.nome)
    ids_repo = {b.id for b in bases}
    declaradas = [b for b in cenario.bases if b.id not in ids_repo]
    if declaradas:
        bases = bases + declaradas
        log.evento("sistema", "inicio", {"bases_declaradas_no_cenario": [
            {"id": b.id, "nome": b.nome, "simulada": b.simulada} for b in declaradas]})
    recursos = list(cenario.recursos)
    ids_bases = {b.id for b in bases}
    sem_base = [r.id for r in recursos if r.base_id not in ids_bases]
    if sem_base:
        log.evento("sistema", "inicio", {"aviso": "recursos com base_id que não existe no repositório: ETA "
                                                   "infinito, nunca serão designados", "recursos": sem_base})

    memorias: list[Memoria] = []
    if usar_memoria:
        termos = ["estrada", "rota", "base", "reserva", "cresceu", "reignição"] + [b.nome for b in bases] + \
                 [l.get("nome", "") for o in ocorrencias for l in o.localidades[:2]] + [o.id for o in ocorrencias]
        try:
            ativas, substituidas = memoria.recall(regiao.nome, " ".join(t for t in termos if t), k=10)
            memorias = [m for m in ativas if m.regiao == regiao.nome]
            log.evento("sistema", "memoria_lida", {
                "ativas": [resumo_memoria(m) for m in memorias],
                "substituidas": [resumo_memoria(m) for m in substituidas]})
        except Exception as e:  # noqa: BLE001 - H-MEM fora do ar não derruba o período
            log.evento("sistema", "memoria_lida", {"erro": f"{type(e).__name__}: {e}", "ativas": []})
    agora = datetime.now(timezone.utc)
    notas = [Memoria(id=f"nota_periodo_{i + 1}", regiao=regiao.nome, texto=t, tipo="nota",
                     fonte=f"cenario:{periodo}", confianca=1.0, criada_em=agora)
             for i, t in enumerate(cenario.notas)]
    if notas:
        log.evento("sistema", "memoria_lida", {"notas_do_periodo": [n.texto for n in notas],
                                               "obs": "notas do cenário (entrada do período, não vêm do H-MEM)"})

    baseline = alocador_simples(ocorrencias, recursos, bases, regiao, cenario.reserva, periodo=periodo,
                                regiao=regiao.nome)
    log.evento("ferramenta", "proposta", {"origem": "alocador_simples", "plano": resumo_plano(baseline)})
    ctx = Contexto(regiao=regiao, periodo=periodo, ocorrencias=ocorrencias, recursos=recursos, bases=bases,
                   reserva=cenario.reserva, memorias=memorias + notas, baseline=baseline)
    leitura = interpretar_memorias(ctx.memorias, bases, ocorrencias)
    if leitura.aplicadas:
        log.evento("sistema", "memoria_lida", {
            "interpretacao": {"bases_bloqueadas": {k: v.id for k, v in leitura.bases_bloqueadas.items()},
                              "rotas_bloqueadas": {k: v.id for k, v in leitura.ocorrencias_bloqueadas.items()},
                              "reforcos": {k: v.id for k, v in leitura.reforcos.items()},
                              "reserva_minima": leitura.reserva_minima}})
    pareceres: dict[str, ParecerAnalista] = ctx.pareceres
    consultor = Consultor(repo, ocorrencias, log, agente="analista")

    # ------------------------------------------------------------ nós
    def no_planejar(s: Estado) -> dict:
        rodada = s.get("rodada", 0) + 1
        veredicto, violacoes = s.get("veredicto"), s.get("violacoes")
        if modo == "llm":
            plano = planejador.decidir(ctx, rodada, log, veredicto, violacoes, s.get("plano"))
        else:
            plano = planejador.decidir_offline(ctx, rodada, veredicto, violacoes)
        log.evento("planejador", "proposta", {"rodada": rodada, "modo": rotulo_modo, "plano": resumo_plano(plano)})
        return {"rodada": rodada, "plano": plano, "veredicto": None, "analista_na_rodada": False}

    def no_checar(s: Estado) -> dict:
        plano = s["plano"]
        vs = checar_regras(plano, ocorrencias, recursos, bases, regiao, ctx.memorias, reserva_minima=cenario.reserva)
        vs += checar_citacoes(plano, ocorrencias, bases, recursos=recursos, regiao_cfg=regiao)
        for v in vs:
            log.evento("ferramenta", "violacao", {"rodada": s["rodada"], **v.model_dump()})
        return {"violacoes": vs}

    def no_criticar(s: Estado) -> dict:
        plano, vs, rodada = s["plano"], s["violacoes"], s["rodada"]
        if not usar_critico_llm:
            v = critico.decidir_regras(ctx, plano, vs, rodada)
            origem = "checador"
        elif modo == "llm":
            v = critico.decidir(ctx, plano, vs, rodada, log)
            origem = "llm"
        else:
            v = critico.decidir_offline(ctx, plano, vs, rodada)
            origem = "offline_deterministico"
        if s.get("analista_na_rodada") and v.pedir_analista:
            v = v.model_copy(update={"pedir_analista": []})  # no máximo um Analista por rodada
        # guarda-corpo: regra rígida solúvel não pode ser aprovada
        rig = [x for x in vs if x.rigida and x.regra not in INSOLUVEIS]
        if v.decisao == "aprova" and rig:
            v = v.model_copy(update={"decisao": "rejeita", "motivos": v.motivos + [
                "Sistema: aprovação recusada, há regra rígida violada: " + ", ".join(sorted({x.regra for x in rig}))]})
        insol = [x for x in vs if x.regra in INSOLUVEIS]
        if v.decisao == "aprova" and insol:
            v = v.model_copy(update={"decisao": "escala", "motivos": v.motivos + [
                f"Sistema: escalação obrigatória, {x.ocorrencia_id} com população exposta sem recurso viável."
                for x in insol]})
        evento = "consulta" if v.pedir_analista else v.decisao
        log.evento("critico", evento, {"rodada": rodada, "origem": origem, "decisao": v.decisao,
                                       "motivos": v.motivos, "pedir_analista": v.pedir_analista,
                                       "contra_proposta": resumo_plano(v.contra_proposta) if v.contra_proposta else None})
        if not v.pedir_analista:
            s["historico"].append({"rodada": rodada, "plano": plano.model_dump(mode="json"),
                                   "violacoes": [x.model_dump() for x in vs],
                                   "veredicto": v.model_dump(mode="json"), "origem_critico": origem})
        return {"veredicto": v, "historico": s["historico"]}

    def no_analisar(s: Estado) -> dict:
        v = s["veredicto"]
        for oid in v.pedir_analista:
            if oid in pareceres or oid not in ctx.occ:
                continue
            log.evento("analista", "inicio", {"ocorrencia_id": oid, "pergunta": analista.PERGUNTA,
                                              "pedido_por": "critico", "rodada": s["rodada"]})
            antes = len(consultor.consultas)
            if modo == "llm":
                p = analista.decidir(ctx, oid, consultor, log)
            else:
                p = analista.decidir_offline(ctx, oid, consultor)
            p = p.model_copy(update={"consultas": consultor.consultas[antes:]})
            pareceres[oid] = p
            log.evento("analista", "fim", {"modo": rotulo_modo, **p.model_dump()})
        return {"analista_na_rodada": True}

    def no_finalizar(s: Estado) -> dict:
        v, rodada, plano = s.get("veredicto"), s["rodada"], s["plano"]
        esc = list(s.get("escalacoes", []))
        status = v.decisao if v else "escala"
        if v is not None and v.decisao == "rejeita":  # só chega aqui por impasse
            status = "escala"
            esc.append({"ocorrencia_id": None, "motivo": f"Impasse: {MAX_RODADAS} rodadas sem aprovação. "
                                                         f"Último parecer: {' | '.join(v.motivos)[:600]}"})
        elif status == "escala":
            if v is not None and v.contra_proposta is not None:
                plano = v.contra_proposta
            insol = {x.ocorrencia_id for x in s["violacoes"] if x.regra in INSOLUVEIS}
            for oid in sorted(insol):
                esc.append({"ocorrencia_id": oid, "motivo": "Obrigatória: população exposta sem recurso viável "
                                                            "dentro do ETA máximo."})
            outros = [m for m in (v.motivos if v else []) if m.startswith("Escalação:")]
            ids = [i for i in _ids_cel(outros) if i not in insol] or ([None] if outros else [])
            for oid in ids:
                esc.append({"ocorrencia_id": oid, "motivo": " ".join(m for m in outros if oid is None or oid in m)[:600]})
            if not esc:
                esc.append({"ocorrencia_id": None, "motivo": " ".join(v.motivos if v else [])[:600]})
        if v is not None and v.decisao == "rejeita":
            log.evento("sistema", "escala", {"rodada": rodada, "motivo": "impasse", "escalacoes": esc})
        return {"status": status, "escalacoes": esc, "plano": plano}

    # ------------------------------------------------------------ arestas
    def depois_critico(s: Estado) -> str:
        v = s["veredicto"]
        if v.pedir_analista and not s.get("analista_na_rodada"):
            return "analisar"
        if v.decisao == "rejeita" and s["rodada"] < MAX_RODADAS:
            return "planejar"
        return "finalizar"

    g = StateGraph(Estado)
    g.add_node("planejar", no_planejar)
    g.add_node("checar", no_checar)
    g.add_node("criticar", no_criticar)
    g.add_node("analisar", no_analisar)
    g.add_node("finalizar", no_finalizar)
    g.add_edge(START, "planejar")
    g.add_edge("planejar", "checar")
    g.add_edge("checar", "criticar")
    g.add_conditional_edges("criticar", depois_critico, {"analisar": "analisar", "planejar": "planejar",
                                                         "finalizar": "finalizar"})
    g.add_edge("analisar", "criticar")
    g.add_edge("finalizar", END)
    final: dict[str, Any] = g.compile().invoke({"rodada": 0, "historico": [], "escalacoes": []},
                                               {"recursion_limit": 60})

    plano: Plano = final["plano"]
    plano = plano.model_copy(update={"resumo": f"[{final['status']}] {plano.resumo}"})
    log.evento("sistema", "fim", {"status": final["status"], "rodadas": final["rodada"],
                                  "designacoes": len(plano.designacoes), "escalacoes": final["escalacoes"],
                                  "pareceres": sorted(pareceres), "modo": rotulo_modo})
    return ResultadoPeriodo(plano=plano, ocorrencias=ocorrencias, bases=bases, recursos=recursos,
                            escalacoes=final["escalacoes"], pareceres=list(pareceres.values()),
                            memorias_usadas=memorias, historico=final["historico"], rodadas=final["rodada"],
                            log_path=str(log.caminho))
