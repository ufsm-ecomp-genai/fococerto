"""Execução de um período: Planejador ⇄ (checar_regras + checar_citacoes) ⇄ Crítico ⇄ Analista (LangGraph).

Interface: docs/CONTRATOS.md, seção 10. No máximo 3 rodadas Planejador→Crítico. Escalação obrigatória quando há
população exposta sem recurso viável (regra rígida insolúvel) ou impasse após 3 rodadas; o Crítico também pode
escalar em zona cinzenta. Guarda-corpo final (decisão do time): toda ocorrência com população exposta sem recurso
no plano final vira escalação ("solicitar apoio externo"), mesmo com aprovação do Crítico. O Analista é chamado
pelo Crítico (no máximo uma vez por rodada).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents import analista, critico, planejador
from app.agents.base import Contexto, reescrever_citacoes, resumo_memoria, resumo_plano
from app.data.bases import fundir_bases_com_apelidos
from app.core.config import RAIZ
from app.core.logging import LogExecucao
from app.core.mensagens import msg, normalizar_idioma, prefixos_escalacao, rotulo
from app.core.models import (Base, Cenario, Memoria, Ocorrencia, ParecerAnalista, Plano, RegiaoCfg,
                             ResultadoPeriodo, VeredictoCritico, Violacao)
from app.tools.alocador import alocador_simples
from app.tools.citacoes import checar_citacoes
from app.tools.consultar import Consultor
from app.tools.geo import exposta
from app.tools.memorias import REFORCO, interpretar_memorias, tokens_distintivos
from app.tools.texto import contem_termo, norm, sem_sufixo_simulada, tokens_nome
from app.tools.monitor import monitor
from app.tools.regras import INSOLUVEIS, checar_regras

MAX_RODADAS = 3
TOP = 15
TOP_ANTERIOR = 5000  # sem corte relevante: o monitor precisa do par de cada célula de ontem (dia típico: ~200)
MAX_PUXADAS = 5      # ocorrências fora do top 15 que uma memória derivada de reforço traz para a lista


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
    violacoes: list[Violacao]            # todas as da rodada (inclui citacao_incorreta já corrigida)
    violacoes_critico: list[Violacao]    # as do plano depois da correção de citações (o que o Crítico julga)
    citacoes_corrigidas: list[Violacao]
    divergencia: dict
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


PALAVRAS_MEMORIA = ["estrada", "rota", "reserva", "cresceu", "reignição"]
RE_PALAVRAS_MEMORIA = re.compile(r"estrada|rota\b|reserva|cresc|reign|reacend|alagad|bloquead|interditad|liberad"
                                 r"|ponte|despriorizad")


def _ids_substituidos(memoria: ClienteMemoria, todas: list[Memoria]) -> set[str]:
    """Memórias que outra substituiu: as apontadas por ``supersedes`` e as que o serviço marca com
    ``substituida_por`` (inclui conflito resolvido pelo engine, que não preenche ``supersedes`` na vencedora)."""
    ids = {m.supersedes for m in todas if m.supersedes}
    por = getattr(memoria, "substituida_por", None)
    if callable(por):
        ids |= {m.id for m in todas if por(m.id)}
    return ids


def _motivo_listar(texto: str, ocorrencias: list[Ocorrencia], bases: list[Base],
                   distintivos: dict[str, list[str]]) -> str | None:
    """Por que uma memória da região interessa a este período (None se não interessa)."""
    t = norm(texto)
    for o in ocorrencias:
        if contem_termo(t, o.id):
            return f"celula:{o.id}"
    for b in bases:
        nome = sem_sufixo_simulada(b.nome)
        if contem_termo(t, b.id) or (len(nome) >= 4 and contem_termo(t, nome)) or \
                any(contem_termo(t, tk) for tk in distintivos.get(b.id, [])):
            return f"base:{b.id}"
    for o in ocorrencias:
        for l in o.localidades:
            nome = l.get("nome") or ""
            if len(norm(nome)) >= 4 and contem_termo(t, nome):
                return f"localidade:{nome}"
    m = RE_PALAVRAS_MEMORIA.search(t)
    return f"palavra:{m.group(0)}" if m else None


def _ler_memorias(memoria: ClienteMemoria, regiao: str, bases: list[Base], ocorrencias: list[Ocorrencia]
                  ) -> tuple[list[Memoria], list[Memoria], dict[str, str]]:
    """Memórias ativas que interessam ao período, por duas vias (registradas em ``vias``):

    1. ``recall`` do H-MEM, uma consulta por termo (o recall compara palavras: consulta longa dilui a similaridade);
    2. ``listar(regiao)`` (o escopo por região é pequeno, CONTRATOS §5): entram as ativas que citam célula do
       período, base, localidade ou palavra-chave (as derivadas, só por célula ou localidade). Sem isso, uma memória longa (ex.: derivada de reignição) não
       passa do limiar 0,35 do recall contra um termo curto, nem pelo id da célula.
    Substituídas (``supersedes``/``substituida_por``) nunca entram como ativas."""
    nomes_base = [p.strip() for b in bases for p in re.sub(r"\(.*?\)", "", b.nome).split("/")]
    termos = PALAVRAS_MEMORIA + nomes_base + \
        [l.get("nome", "") for o in ocorrencias for l in o.localidades[:2]] + [o.id for o in ocorrencias]
    ativas: dict[str, Memoria] = {}
    subst: dict[str, Memoria] = {}
    vias: dict[str, str] = {}
    for termo in dict.fromkeys(t for t in termos if t and len(t) >= 3):
        a, sb = memoria.recall(regiao, termo, k=5)
        for m in a:
            ativas.setdefault(m.id, m)
            vias.setdefault(m.id, f"recall:{termo}")
        subst.update({m.id: m for m in sb})
    todas = [m for m in memoria.listar(regiao) if m.regiao == regiao]
    ids_subst = _ids_substituidos(memoria, todas) | set(subst)
    distintivos = tokens_distintivos(bases, set(tokens_nome(regiao.replace("_", " "))))
    for m in todas:
        if m.id in ativas or m.id in ids_subst:
            continue
        motivo = _motivo_listar(m.texto, ocorrencias, bases, distintivos)
        if motivo and m.tipo == "derivada" and not motivo.startswith(("celula:", "localidade:")):
            # derivada fala de uma célula: só interessa se a célula (ou a localidade) está no período. Pela base
            # ou por palavra-chave, toda derivada antiga voltaria em todo período (ex.: localidade = nome da base).
            continue
        if motivo:
            ativas[m.id] = m
            vias[m.id] = f"listar:{motivo}"
    usadas = [m for m in ativas.values() if m.regiao == regiao and m.id not in ids_subst]
    return usadas, list(subst.values()), {m.id: vias[m.id] for m in usadas}


def _puxar_por_memoria(memoria: ClienteMemoria, regiao: str, repo: Repositorio, periodo: str,
                       atuais: list[Ocorrencia]) -> list[tuple[Ocorrencia, Memoria]]:
    """Ocorrências do período fora do top 15 citadas **pelo id** numa memória derivada ativa de reforço
    ("cresceu", "persistiu forte", reignição). Sem isso, a célula que ficou sem recurso e cresceu continua fora
    da lista (o top 15 é dominado pela prioridade do dia) e a memória não tem efeito nenhum."""
    todas = [m for m in memoria.listar(regiao) if m.regiao == regiao]
    subst = _ids_substituidos(memoria, todas)
    no_top = {o.id for o in atuais}
    por_cel: dict[str, Memoria] = {}
    for m in sorted(todas, key=lambda x: x.criada_em):
        if m.tipo != "derivada" or m.id in subst or not REFORCO.search(norm(m.texto)):
            continue
        for cel in _ids_cel([m.texto]):
            cel = cel.rstrip("._")
            if cel not in no_top:
                por_cel[cel] = m
    if not por_cel:
        return []
    candidatas = [o for o in repo.ocorrencias(regiao, periodo, top=TOP_ANTERIOR) if o.id in por_cel]
    candidatas.sort(key=lambda o: -o.prioridade)
    return [(o, por_cel[o.id]) for o in candidatas[:MAX_PUXADAS]]


SUGESTAO_APOIO_EXTERNO = msg("sugestao_apoio_externo", "pt-BR")   # em inglês: "request external support"


def escalar_expostas_sem_recurso(plano: Plano, ocorrencias: list[Ocorrencia], esc: list[dict],
                                 idioma: str | None = None) -> tuple[list[dict], list[dict]]:
    """Escalação obrigatória determinística: cada ocorrência com ``pop_raio > 0`` sem designação no plano final
    ganha uma escalação com motivo e ``sugestao`` "solicitar apoio externo" (no idioma da execução). As escalações
    já existentes ficam (a da mesma ocorrência só ganha a ``sugestao``). Devolve (todas, novas)."""
    sugestao = msg("sugestao_apoio_externo", idioma)
    designadas = {d.ocorrencia_id for d in plano.designacoes}
    saida = [dict(e) for e in esc]
    novas = []
    for o in ocorrencias:
        if not exposta(o) or o.id in designadas:
            continue
        existentes = [e for e in saida if e.get("ocorrencia_id") == o.id]
        for e in existentes:
            e.setdefault("sugestao", sugestao)
        if not existentes:
            nova = {"ocorrencia_id": o.id, "motivo": msg("esc_guarda_corpo", idioma, pop=o.pop_raio, sug=sugestao),
                    "sugestao": sugestao}
            saida.append(nova)
            novas.append(nova)
    return saida, novas


def caminho_log(caminho) -> str:
    """Caminho do log relativo à raiz do repositório quando está dentro dela (não vaza o caminho da máquina);
    absoluto quando está fora (ex.: /tmp)."""
    p = Path(caminho).resolve()
    try:
        return p.relative_to(RAIZ).as_posix()
    except ValueError:
        return str(p)


def executar_periodo(regiao: RegiaoCfg, cenario: Cenario, repo: Repositorio, memoria: ClienteMemoria,
                     log: LogExecucao, modo: Literal["llm", "offline"] = "llm",
                     usar_critico_llm: bool = True, usar_memoria: bool = True,
                     idioma: str | None = None) -> ResultadoPeriodo:
    """``idioma`` (pt-BR ou en; "en-US", "pt"... são normalizados): idioma de todo o texto que o sistema e os agentes
    escrevem no plano. None = ``regiao.idioma`` (idioma não suportado cai no pt-BR). CONTRATOS, seções 10 e 19."""
    idioma = normalizar_idioma(idioma) or normalizar_idioma(regiao.idioma) or "pt-BR"
    regiao = regiao.model_copy(update={"idioma": idioma})  # ferramentas e agentes leem o idioma de regiao_cfg
    periodo = cenario.periodo
    rotulo_modo = "llm" if modo == "llm" else "offline_deterministico"
    log.evento("sistema", "inicio", {"regiao": regiao.nome, "periodo": periodo, "modo": rotulo_modo,
                                     "usar_critico_llm": usar_critico_llm, "usar_memoria": usar_memoria,
                                     "cenario_simulado": cenario.simulado, "max_rodadas": MAX_RODADAS,
                                     "idioma": idioma})

    # ------------------------------------------------------------ preparação (ferramentas, sem LLM)
    # O período anterior é consultado ANTES do atual: o RepositorioCache/Zetaris usa o último período consultado
    # como fim do historico_celula, e o Analista precisa ver o dia do período (bug 4 da ablação).
    # Sem corte relevante no anterior: com top 100, uma célula que já existia ficava "nova" (bug 5).
    anteriores: list[Ocorrencia] = []
    ant = _periodo_anterior(periodo)
    if ant:
        try:
            anteriores = repo.ocorrencias(regiao.nome, ant, top=TOP_ANTERIOR)
        except Exception as e:  # noqa: BLE001 - sem período anterior, tudo vira "nova"
            log.evento("ferramenta", "consulta", {"consulta": f"ocorrencias({ant})", "erro": str(e)})
    atuais = repo.ocorrencias(regiao.nome, periodo, top=TOP)[:TOP]
    if usar_memoria:
        try:
            puxadas = _puxar_por_memoria(memoria, regiao.nome, repo, periodo, atuais)
        except Exception as e:  # noqa: BLE001 - H-MEM fora do ar não derruba o período
            puxadas = []
            log.evento("sistema", "memoria_lida", {"erro": f"{type(e).__name__}: {e}", "puxadas_por_memoria": []})
        if puxadas:
            atuais = atuais + [o for o, _ in puxadas]
            log.evento("sistema", "memoria_lida", {
                "puxadas_por_memoria": [{"ocorrencia_id": o.id, "memoria_id": m.id, "texto": m.texto,
                                         "n_focos": o.n_focos, "prioridade": round(o.prioridade, 4)}
                                        for o, m in puxadas],
                "obs": f"fora do top {TOP}, entram na lista do período por memória derivada de reforço"})
    ocorrencias = monitor(atuais, anteriores)
    log.evento("ferramenta", "consulta", {"consulta": "monitor", "anterior": ant, "n_atuais": len(ocorrencias),
                                          "status": {o.id: o.status for o in ocorrencias}})
    # bases em camadas (CONTRATOS §16): as declaradas no cenário vencem; a menos de 3 km de outra base, são fundidas
    # e os recursos passam a apontar para a base mantida
    bases, apelidos = fundir_bases_com_apelidos(repo.bases(regiao.nome), cenario.bases)
    if cenario.bases:
        log.evento("sistema", "inicio", {"bases_declaradas_no_cenario": [
            {"id": b.id, "nome": b.nome, "simulada": b.simulada} for b in cenario.bases], "fundidas": apelidos})
    recursos = [r.model_copy(update={"base_id": apelidos.get(r.base_id, r.base_id)}) for r in cenario.recursos]
    ids_bases = {b.id for b in bases}
    sem_base = [r.id for r in recursos if r.base_id not in ids_bases]
    if sem_base:
        log.evento("sistema", "inicio", {"aviso": "recursos com base_id que não existe no repositório: ETA "
                                                   "infinito, nunca serão designados", "recursos": sem_base})

    memorias: list[Memoria] = []
    if usar_memoria:
        try:
            memorias, substituidas, vias = _ler_memorias(memoria, regiao.nome, bases, ocorrencias)
            log.evento("sistema", "memoria_lida", {
                "ativas": [resumo_memoria(m) for m in memorias],
                "substituidas": [resumo_memoria(m) for m in substituidas],
                "vias": vias})
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
    leitura = interpretar_memorias(ctx.memorias, bases, ocorrencias, regiao=regiao.nome)
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

    def checar(plano: Plano) -> list[Violacao]:
        vs = checar_regras(plano, ocorrencias, recursos, bases, regiao, ctx.memorias, reserva_minima=cenario.reserva)
        return vs + checar_citacoes(plano, ocorrencias, bases, recursos=recursos, regiao_cfg=regiao)

    def no_checar(s: Estado) -> dict:
        """Regras + citações. Citação errada é corrigida aqui, de forma determinística, ANTES do Crítico: a
        justificativa é reescrita a partir dos dados (a alocação não muda) e o evento ``citacao_corrigida``
        registra o que o agente errou e o valor real. As violações ``citacao_incorreta`` continuam no estado e no
        histórico (métrica da ablação), mas o Crítico só recebe as restantes: citação nunca causa rejeição."""
        plano, rodada = s["plano"], s["rodada"]
        vs = checar(plano)
        for v in vs:
            log.evento("ferramenta", "violacao", {"rodada": rodada, **v.model_dump()})
        cit = [v for v in vs if v.regra == "citacao_incorreta"]
        if not cit:
            return {"violacoes": vs, "violacoes_critico": vs, "citacoes_corrigidas": []}
        corrigido = reescrever_citacoes(ctx, plano, cit)
        antes = {(d.recurso_id, d.ocorrencia_id): d for d in plano.designacoes}
        depois = {(d.recurso_id, d.ocorrencia_id): d for d in corrigido.designacoes}
        restantes = checar(corrigido)
        log.evento("ferramenta", "citacao_corrigida", {
            "rodada": rodada, "agente_que_errou": "planejador",
            "obs": "o agente citou fato que não confere com os dados; o sistema reescreveu a justificativa a partir "
                   "dos dados antes do Crítico (a alocação não muda)",
            "correcoes": [{"recurso_id": v.recurso_id, "ocorrencia_id": v.ocorrencia_id,
                           "campo": v.evidencia.get("campo"), "citado": v.evidencia.get("citado"),
                           "real": v.evidencia.get("real"),
                           "justificativa_antes": antes[(v.recurso_id, v.ocorrencia_id)].justificativa
                           if (v.recurso_id, v.ocorrencia_id) in antes else None,
                           "justificativa_depois": depois[(v.recurso_id, v.ocorrencia_id)].justificativa
                           if (v.recurso_id, v.ocorrencia_id) in depois else None} for v in cit],
            "citacoes_restantes": sum(v.regra == "citacao_incorreta" for v in restantes)})
        # o histórico guarda TODAS as violações da rodada (inclusive as citações corrigidas); o Crítico, as do
        # plano corrigido
        return {"plano": corrigido, "violacoes": vs, "violacoes_critico": restantes, "citacoes_corrigidas": cit}

    def no_criticar(s: Estado) -> dict:
        plano, rodada = s["plano"], s["rodada"]
        vs = s.get("violacoes_critico", s["violacoes"])
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
                msg("sis_aprovacao_recusada", idioma, regras=", ".join(sorted({x.regra for x in rig})))]})
        insol = [x for x in vs if x.regra in INSOLUVEIS]
        if v.decisao == "aprova" and insol:
            v = v.model_copy(update={"decisao": "escala", "motivos": v.motivos + [
                msg("sis_escalacao_obrigatoria", idioma, oid=x.ocorrencia_id) for x in insol]})
        evento = "consulta" if v.pedir_analista else v.decisao
        log.evento("critico", evento, {"rodada": rodada, "origem": origem, "decisao": v.decisao,
                                       "motivos": v.motivos, "pedir_analista": v.pedir_analista,
                                       "contra_proposta": resumo_plano(v.contra_proposta) if v.contra_proposta else None})
        if not v.pedir_analista:
            s["historico"].append({"rodada": rodada, "plano": plano.model_dump(mode="json"),
                                   "violacoes": [x.model_dump() for x in s["violacoes"]],
                                   "citacoes_corrigidas": [x.model_dump() for x in s.get("citacoes_corrigidas", [])],
                                   "veredicto": v.model_dump(mode="json"), "origem_critico": origem})
        return {"veredicto": v, "historico": s["historico"]}

    def no_analisar(s: Estado) -> dict:
        v = s["veredicto"]
        for oid in v.pedir_analista:
            if oid in pareceres or oid not in ctx.occ:
                continue
            log.evento("analista", "inicio", {"ocorrencia_id": oid, "pergunta": analista.pergunta_padrao(idioma),
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
        vs_final = s.get("violacoes_critico", s.get("violacoes", []))
        rig_abertas = [x for x in vs_final if x.rigida and x.regra not in INSOLUVEIS]
        impasse = v is not None and v.decisao == "rejeita" and bool(rig_abertas)
        divergencia = None
        if v is not None and v.decisao == "rejeita" and not rig_abertas:
            # Última rodada rejeitada só por zona cinzenta (trade-off, exceção não rígida): não é impasse. Fica o
            # melhor plano disponível (contra-proposta do Crítico, se não violar regra rígida; senão a última
            # proposta) e os motivos do Crítico vão visíveis ao coordenador. Escalação só pelo guarda-corpo.
            escolhido = "ultima_proposta"
            cp = v.contra_proposta
            if cp is not None:
                rig_cp = [x for x in checar(cp) if x.rigida and x.regra not in INSOLUVEIS
                          and x.regra != "citacao_incorreta"]   # citação: corrigida abaixo, pelo guarda-corpo
                if not rig_cp:
                    plano, escolhido = cp.model_copy(update={"rodada": rodada}), "contra_proposta_critico"
            status = "aprova"
            divergencia = {"motivo": "divergencia_zona_cinzenta", "plano_escolhido": escolhido,
                           "motivos_critico": list(v.motivos)}
            plano = plano.model_copy(update={"resumo": msg(
                "resumo_divergencia", idioma, n=rodada,
                plano=msg("plano_cp_critico" if escolhido == "contra_proposta_critico" else "plano_ultima", idioma),
                motivos=" | ".join(v.motivos)[:800], resumo=plano.resumo)})
            for oid in sorted({x.ocorrencia_id for x in checar(plano) if x.regra in INSOLUVEIS}):
                esc.append({"ocorrencia_id": oid, "motivo": msg("esc_insoluvel", idioma)})
            log.evento("sistema", "aprova", {"rodada": rodada, **divergencia,
                                             "obs": "rejeição do Crítico sem violação rígida aberta na última "
                                                    "rodada: não é impasse"})
        elif impasse:
            status = "escala"
            esc.append({"ocorrencia_id": None, "motivo": msg(
                "esc_impasse", idioma, n=MAX_RODADAS, regras=", ".join(sorted({x.regra for x in rig_abertas})),
                parecer=" | ".join(v.motivos)[:600])})
        elif status == "escala":
            if v is not None and v.contra_proposta is not None:
                plano = v.contra_proposta
            insol = {x.ocorrencia_id for x in s["violacoes"] if x.regra in INSOLUVEIS}
            for oid in sorted(insol):
                esc.append({"ocorrencia_id": oid, "motivo": msg("esc_insoluvel", idioma)})
            outros = [m for m in (v.motivos if v else []) if m.startswith(prefixos_escalacao())]
            ids = [i for i in _ids_cel(outros) if i not in insol] or ([None] if outros else [])
            for oid in ids:
                esc.append({"ocorrencia_id": oid, "motivo": " ".join(m for m in outros if oid is None or oid in m)[:600]})
            if not esc:
                esc.append({"ocorrencia_id": None, "motivo": " ".join(v.motivos if v else [])[:600]})
        if impasse:
            log.evento("sistema", "escala", {"rodada": rodada, "motivo": "impasse", "escalacoes": esc})
        # guarda-corpo (decisão do time, 25/10): toda ocorrência com população exposta que termina sem recurso no
        # plano final vira escalação com sugestão de apoio externo, mesmo que o Crítico (LLM ou não) tenha aprovado.
        esc, novas = escalar_expostas_sem_recurso(plano, ocorrencias, esc, idioma)
        if novas:
            log.evento("sistema", "escala", {"rodada": rodada, "motivo": "exposta_sem_recurso_no_plano_final",
                                             "decisao_critico": v.decisao if v else None, "escalacoes": novas})
        if esc:
            status = "escala"
        # guarda-corpo: o plano que vai ao coordenador nunca leva citação que não confere com os dados
        cit = [x for x in checar_citacoes(plano, ocorrencias, bases, recursos=recursos, regiao_cfg=regiao)
               if x.regra == "citacao_incorreta"]
        if cit:
            plano = reescrever_citacoes(ctx, plano, cit)
            log.evento("sistema", "violacao", {"rodada": rodada, "acao": "justificativa_reescrita_no_plano_final",
                                               "violacoes": [x.model_dump() for x in cit]})
        return {"status": status, "escalacoes": esc, "plano": plano, "divergencia": divergencia}

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
    prefixo = rotulo("prefixo_status", final["status"], idioma)
    plano = plano.model_copy(update={"resumo": f"{prefixo} {plano.resumo}"})
    log.evento("sistema", "fim", {"status": final["status"], "rodadas": final["rodada"],
                                  "designacoes": len(plano.designacoes), "escalacoes": final["escalacoes"],
                                  "pareceres": sorted(pareceres), "modo": rotulo_modo,
                                  "divergencia": final.get("divergencia")})
    return ResultadoPeriodo(plano=plano, status=final["status"], ocorrencias=ocorrencias, bases=bases, recursos=recursos,
                            escalacoes=final["escalacoes"], pareceres=list(pareceres.values()),
                            memorias_usadas=memorias, historico=final["historico"], rodadas=final["rodada"],
                            log_path=caminho_log(log.caminho))
