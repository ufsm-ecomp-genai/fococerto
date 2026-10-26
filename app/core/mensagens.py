"""Catálogo das frases de CONTEÚDO geradas pelo sistema, por idioma (docs/CONTRATOS.md, seção 19).

Os rótulos de interface (títulos, colunas, legendas) ficam em ``app/output/textos.py``. Aqui ficam as frases que
os agentes offline, as ferramentas e o grafo escrevem dentro do plano: justificativa do alocador, sugestões das
regras e do checador de citações, motivos do Crítico offline, escalações, pareceres offline do Analista e resumos
do Planejador offline. O texto pt-BR é o mesmo que o sistema já escrevia antes do catálogo.

Uso: ``msg("jus_pop", idioma, pop=1200)``. Chave ausente num idioma cai no pt-BR. Idiomas suportados: pt-BR e en
(``normalizar_idioma`` aceita "pt", "pt-BR", "pt_PT", "en", "en-US", "EN_gb"...). Para acrescentar um idioma,
copie o bloco "en" e registre a chave em ``IDIOMAS``.
"""
from __future__ import annotations

IDIOMA_PADRAO = "pt-BR"
IDIOMAS = ("pt-BR", "en")


def normalizar_idioma(valor: str | None) -> str | None:
    """'en', 'en-US', 'en_GB' -> 'en'; 'pt', 'pt-BR', 'pt_PT' -> 'pt-BR'. Vazio ou não suportado -> None."""
    if not valor or not str(valor).strip():
        return None
    prefixo = str(valor).strip().replace("_", "-").split("-")[0].lower()
    return {"pt": "pt-BR", "en": "en"}.get(prefixo)


def resolver_idioma(*candidatos: str | None) -> str:
    """Primeiro candidato suportado, na ordem de precedência dada (ex.: --idioma, pedido da API,
    FOCOCERTO_IDIOMA, RegiaoCfg.idioma). Nenhum suportado -> pt-BR."""
    for c in candidatos:
        n = normalizar_idioma(c)
        if n:
            return n
    return IDIOMA_PADRAO


MENSAGENS: dict[str, dict] = {
    "pt-BR": {
        # ------------------------------------------------ rótulos usados dentro de frases (pt: o valor cru)
        "tipos_recurso": {"terrestre": "terrestre", "aereo": "aereo"},
        "confiancas": {"baixa": "baixa", "media": "media", "alta": "alta"},
        "conclusoes": {"queima_agricola_provavel": "queima_agricola_provavel",
                       "incendio_vegetacao_provavel": "incendio_vegetacao_provavel",
                       "indeterminado": "indeterminado"},
        "status_ocorrencia": {"nova": "nova", "crescendo": "crescendo", "estavel": "estavel",
                              "diminuindo": "diminuindo"},
        "ou": " ou ",
        # ------------------------------------------------ justificativa do alocador (app/tools/alocador.py)
        "jus_prioridade": "Prioridade {p:.2f}",
        "jus_pop": "{pop} habitantes no raio",
        "jus_localidade": "{nome} a {km:.1f} km",
        "jus_sem_pop": "sem população no raio",
        "jus_focos": "{n} focos, FRP somado {frp:.0f} MW",
        "jus_chegada": "{recurso} ({tipo}) chega em ETA {eta:.1f} h saindo de {base}",
        "resumo_alocador": "{n_desig} designações, {n_sem} ocorrências sem recurso, {n_res} recursos em reserva.",
        # ------------------------------------------------ ajustes de prioridade (app/agents/base.py)
        "extra_memoria_reforco": "memória {mid} indica que este padrão já cresceu antes (+0,15)",
        "extra_analista_mantida": ("Analista: queima agrícola provável, mas a memória {mid} (reignição/crescimento) "
                                   "pesa contra rebaixar: prioridade mantida"),
        "extra_analista_agricola": "Analista: queima agrícola provável (confiança {conf}), prioridade ×0,5",
        "extra_analista_vegetacao": "Analista: incêndio em vegetação provável (confiança {conf}), +0,1",
        "nota_reescrita": (" (Justificativa reescrita a partir dos dados: a anterior citava fato "
                           "que não confere.)"),
        "sufixo_desvios": " Desvios do baseline: ",
        "sufixo_respostas": " Respostas ao Crítico: ",
        # ------------------------------------------------ sugestões de checar_regras (app/tools/regras.py)
        "sug_duplicado": "remover a designação repetida",
        "sug_ocorrencia_inexistente": "usar só ocorrências do top do período",
        "sug_recurso_inexistente": "usar só recursos do cenário",
        "sug_indisponivel": "trocar por um recurso disponível",
        "sug_eta": "usar um recurso de base mais próxima ou aéreo",
        "sug_memoria": "avaliar se a rota está mesmo bloqueada; usar outra base ou aéreo",
        "sug_capacidade": "liberar o recurso de alguma ocorrência",
        "sug_reserva": "manter {n} recurso(s) sem designação",
        "sug_sem_viavel": "escalar: nenhum recurso chega dentro do limite",
        "sug_exposta_sem_recurso": "realocar para esta um recurso que está em ocorrência sem exposição: {ids}",
        "sug_troca": ("trocar: {rid} sai de {de} ({pop_de} hab., ETA {eta_de} h) e vai para {para} ({pop_para} hab., "
                      "ETA {eta_para} h); {de} fica sem recurso e deve ser escalada"),
        "sug_exposta_nao_atendida": ("os recursos viáveis estão em ocorrências com exposição ou na reserva (os que "
                                     "estão em ocorrências sem exposição não chegam aqui no ETA máximo): avaliar "
                                     "escalação"),
        # ------------------------------------------------ sugestões de checar_citacoes (app/tools/citacoes.py)
        "cit_base_inexistente": "citar uma base existente",
        "cit_base_errada": "o recurso sai da base {bid}",
        "cit_eta_h": "ETA correto ≈ {eta:.1f} h",
        "cit_pop": "população no raio = {pop}",
        "cit_eta": "ETA ≈ {eta:.1f} h",
        "cit_focos": "focos = {n}",
        "cit_frp": "FRP somado = {frp:.0f} MW",
        "cit_ti_uc": "conferir a distância até TI/UC",
        "cit_dist_base": "a base {nome} fica a {km:.1f} km em linha reta",
        "cit_localidade_fora": "citar só localidades no raio desta ocorrência",
        "cit_dist": "{nome} fica a {kms} km",
        "cit_mal_formatada": "evidência mal formatada",
        "cit_localidade_texto": "{nome} não está no raio desta ocorrência",
        "cit_dist_texto": "conferir a distância citada",
        "cit_id_inexistente": "{id} não existe nos dados desta execução: cite só ids de recursos, bases e ocorrências dos DADOS",
        "cit_cobertura_falsa": "no plano, {oid} é atendida por: {reais}",
        "cit_sem_recurso": "nenhum recurso",
        "resumo_sistema": ("{n} designação(ões): {lista}. Sem recurso: {sem}. Reserva: {res}."),
        "resumo_nenhuma": "nenhuma",
        "resumo_nenhum": "nenhum",
        "nota_resumo_reescrito": (" (Resumo reescrito pelo sistema a partir das designações finais: o resumo do "
                                  "agente citava id inexistente ou atendimento que não confere com o plano.)"),
        # ------------------------------------------------ Crítico offline (app/agents/critico.py)
        "cr_checador_ok": "checador: nenhuma violação rígida solúvel",
        "cr_excecao_aceita": ("Exceção aceita: memória {mid} (\"{texto}\", confiança {conf:.2f}) vale sobre a regra da "
                              "base mais próxima; {rid} não deve ir por terra a {oid}."),
        "cr_memoria_fraca": "Memória {mid} tem confiança {conf:.2f} < {minimo}: designação {rid}→{oid} mantida.",
        "cr_regra_rigida": "Regra rígida {regra} ({oid} {rid}): {sugestao}.",
        "cr_pergunta_analista": ("Pergunta em aberto: {ids} recebe(m) recurso sem população exposta enquanto {n} "
                                 "ocorrência(s) ficam sem; é queima agrícola recorrente?"),
        "cr_analista_memoria_contra": ("Analista: {oid} parece queima agrícola ({conf}), mas a memória {mid} "
                                       "(\"{texto}\", confiança {mconf:.2f}) diz que este fogo já reacendeu/cresceu: "
                                       "não rebaixo, designação mantida."),
        "cr_analista_rebaixa": ("Analista: {oid} é queima agrícola provável (confiança {conf}); o recurso rende mais "
                                "em ocorrência não atendida."),
        "cr_analista_vegetacao": "Analista: {oid} é incêndio em vegetação provável (confiança {conf}); designação mantida.",
        "cr_analista_inconclusivo": ("Analista inconclusivo sobre {oid} ({conclusao}, {conf}): designação mantida por "
                                     "precaução."),
        "cr_tradeoff": ("Trade-off: {oid} ({pop} hab.) espera {eta:.1f} h por {rid}, mas {rid2} (em {oid2}, sem "
                        "exposição) chegaria em {eta_alt:.1f} h."),
        "cr_troca": ("Troca de recurso local: {rid} chega a {para} ({pop_para} hab.) em {eta_para} h, mas foi para "
                     "{de} ({pop_de} hab.) a {eta_atual} h; troco e {de} fica sem recurso (escalação)."),
        "cr_esc_exposta_nao_atendida": ("Escalação: {oid} tem {pop} hab. expostos e os recursos viáveis estão em "
                                        "outras ocorrências com população ou na reserva."),
        "cr_esc_obrigatoria": ("Escalação obrigatória: {oid} tem {pop} hab. expostos e nenhum recurso chega em até "
                               "{eta_max} h."),
        "cr_esc_memoria": ("Escalação: respeitar a memória deixa {ids} (com população) sem recurso viável; decisão "
                           "humana sobre usar a rota."),
        "cr_esc_sem_alternativa": "Escalação: não encontrei plano alternativo que resolva as regras rígidas.",
        "cr_revisao_igual": "Revisão não muda o plano.",
        "cr_citacao": ("Citação incorreta em {alvo}: reescrevo a justificativa a partir dos dados; a alocação fica "
                       "igual."),
        "cr_sem_violacoes": "Sem violações nem zona cinzenta relevante.",
        "cr_cp_offline": "Contra-proposta do Crítico (offline).",
        "cr_cp_troca": "Contra-proposta do Crítico (offline): troca de recurso local. ",
        "cr_cp_citacoes": "Contra-proposta do Crítico (offline): justificativas reescritas a partir dos dados. ",
        "cr_nota_troca": " (Troca de recurso local proposta pelo Crítico.)",
        # ------------------------------------------------ Planejador offline (app/agents/planejador.py)
        "pl_adota_cp": "Adota a contra-proposta do Crítico. ",
        "pl_offline": "Planejador offline (determinístico): população exposta primeiro",
        "pl_reserva_memoria": "reserva {n} pedida em memória",
        "pl_ajustes": "{n} ajuste(s) de prioridade por memória/parecer",
        "pl_desvios": "desvios do baseline: {lista}",
        "pl_igual": "igual ao baseline",
        "pl_removido": "removido {r}→{o}",
        "pl_incluido": "incluído {r}→{o}",
        # ------------------------------------------------ grafo (app/agents/grafo.py)
        "sugestao_apoio_externo": "solicitar apoio externo",
        "esc_guarda_corpo": ("Obrigatória: {pop} hab. expostos e nenhum recurso designado no plano final. "
                             "Sugestão: {sug}."),
        "esc_guarda_corpo_alcance": ("Obrigatória: {pop} hab. expostos e nenhum recurso designado no plano final. "
                                     "{alcance} Sugestão: {sug}."),
        "esc_alcance": "Chegariam dentro do limite de {eta_max} h: {lista}.",
        "esc_alcance_item": "{rid} ({eta:.1f} h; {destino})",
        "esc_alcance_mais": "e mais {n}",
        "esc_destino_designado": "designado {alvos}",
        "esc_destino_reserva": "em reserva",
        "esc_alvo_loc": "à ocorrência perto de {loc} ({pop} hab.)",
        "esc_alvo_sem_loc": "a outra ocorrência ({pop} hab.)",
        "esc_destino_livre": "sem designação",
        "esc_sem_alcance": "Nenhum recurso disponível chega dentro do limite de {eta_max} h.",
        "esc_insoluvel": "Obrigatória: população exposta sem recurso viável dentro do ETA máximo.",
        "esc_impasse": ("Impasse: {n} rodadas sem aprovação, com regra rígida aberta ({regras}). "
                        "Último parecer: {parecer}"),
        "resumo_divergencia": ("Divergência do Crítico em zona cinzenta após {n} rodada(s) (não bloqueia; plano "
                               "adotado: {plano}). Motivos do Crítico: {motivos} || {resumo}"),
        "plano_cp_critico": "contra-proposta do Crítico",
        "plano_ultima": "última proposta do Planejador",
        "sis_aprovacao_recusada": "Sistema: aprovação recusada, há regra rígida violada: {regras}",
        "sis_escalacao_obrigatoria": "Sistema: escalação obrigatória, {oid} com população exposta sem recurso viável.",
        "prefixo_status": {"aprova": "[aprova]", "escala": "[escala]"},
        # ------------------------------------------------ Analista (app/agents/analista.py)
        "an_pergunta": ("Esta ocorrência é provavelmente queima agrícola ou de manejo recorrente, "
                        "ou incêndio em vegetação nativa?"),
        "an_memoria": ("vegetação: memória {mid} (confiança {conf:.2f}) diz que este fogo já reacendeu/cresceu: "
                       "\"{texto}\""),
        "an_noite_baixa": ("agrícola: {total:.0f} focos em 7 dias, {fn:.0%} à noite (queima de manejo costuma ser "
                           "diurna)"),
        "an_noite_alta": "vegetação: {fn:.0%} dos focos à noite (fogo que segue queimando sem manejo)",
        "an_recorrente": "agrícola: recorrente e pequeno ({dias} dias com foco, máx. {maxf:.0f} focos/dia)",
        "an_pico": "vegetação: pico de {maxf:.0f} focos num dia",
        "an_frp_baixo": "agrícola: FRP baixo ({fpf:.1f} MW por foco)",
        "an_frp_alto": "vegetação: FRP alto ({fpf:.1f} MW por foco)",
        "an_frp_max": "vegetação: foco com FRP máximo {frp:.0f} MW",
        "an_crescendo": "vegetação: ocorrência crescendo em relação ao período anterior",
        "an_estavel": "agrícola: ocorrência {status}",
        "an_ti_perto": "vegetação: a {d:.1f} km de TI/UC",
        "an_ti_longe": "agrícola: longe de TI/UC",
        "an_ti_longe_km": " ({d:.1f} km)",
        "an_ti_longe_sem": " (sem TI/UC no raio)",
        "an_tempo": "vegetação: tempo propício a espalhar (VPD {vpd} kPa, vento {vento} km/h)",
        "an_poucos_dados": "incerteza: só {dias} dia(s) com foco no histórico",
        "an_escore": "escore agrícola−vegetação = {escore:+.1f} (limiar ±1,5; heurística não calibrada)",
        # ------------------------------------------------ instrução de idioma para o LLM (app/agents/base.py)
        "llm_idioma": ("## Idioma da saída\nEscreva todo o texto livre (justificativas, motivos, resumo, desvios, "
                       "respostas ao Crítico, evidências do parecer) em **português do Brasil**. Mantenha nomes de "
                       "lugares, bases, recursos e ids exatamente como estão nos DADOS. As chaves do JSON e os valores "
                       "enumerados (ex.: aprova/rejeita/escala, baixa/media/alta) não mudam."),
    },
    "en": {
        "tipos_recurso": {"terrestre": "ground", "aereo": "air"},
        "confiancas": {"baixa": "low", "media": "medium", "alta": "high"},
        "conclusoes": {"queima_agricola_provavel": "likely agricultural burn",
                       "incendio_vegetacao_provavel": "likely vegetation fire",
                       "indeterminado": "undetermined"},
        "status_ocorrencia": {"nova": "new", "crescendo": "growing", "estavel": "stable", "diminuindo": "shrinking"},
        "ou": " or ",
        "jus_prioridade": "Priority {p:.2f}",
        "jus_pop": "{pop} inhabitants in the radius",
        "jus_localidade": "{nome} at {km:.1f} km",
        "jus_sem_pop": "no population in the radius",
        "jus_focos": "{n} detections, total FRP {frp:.0f} MW",
        "jus_chegada": "{recurso} ({tipo}) arrives in ETA {eta:.1f} h from {base}",
        "resumo_alocador": "{n_desig} assignments, {n_sem} incidents without a crew, {n_res} crews/aircraft held in reserve.",
        "extra_memoria_reforco": "memory {mid} indicates this pattern has grown before (+0.15)",
        "extra_analista_mantida": ("Analyst: likely agricultural burn, but memory {mid} (reignition/growth) weighs "
                                   "against downgrading: priority kept"),
        "extra_analista_agricola": "Analyst: likely agricultural burn (confidence {conf}), priority ×0.5",
        "extra_analista_vegetacao": "Analyst: likely vegetation fire (confidence {conf}), +0.1",
        "nota_reescrita": " (Justification rewritten from the data: the previous one cited a fact that does not match.)",
        "sufixo_desvios": " Deviations from the baseline: ",
        "sufixo_respostas": " Replies to the Critic: ",
        "sug_duplicado": "remove the repeated assignment",
        "sug_ocorrencia_inexistente": "use only incidents from the period's top list",
        "sug_recurso_inexistente": "use only crews/aircraft from the scenario",
        "sug_indisponivel": "swap for an available crew/aircraft",
        "sug_eta": "use a crew from a closer base or an aircraft",
        "sug_memoria": "check whether the route is really blocked; use another base or an aircraft",
        "sug_capacidade": "free the crew/aircraft from one of its incidents",
        "sug_reserva": "keep {n} crew(s)/aircraft unassigned",
        "sug_sem_viavel": "escalate: no crew/aircraft arrives within the limit",
        "sug_exposta_sem_recurso": "reassign here a crew/aircraft that is at an incident with no exposure: {ids}",
        "sug_troca": ("swap: {rid} leaves {de} ({pop_de} people, ETA {eta_de} h) and goes to {para} ({pop_para} "
                      "people, ETA {eta_para} h); {de} is left uncovered and must be escalated"),
        "sug_exposta_nao_atendida": ("the viable crews/aircraft are at incidents with exposure or in reserve (those at "
                                     "incidents with no exposure cannot get here within the maximum ETA): consider "
                                     "escalating"),
        "cit_base_inexistente": "cite an existing base",
        "cit_base_errada": "the crew/aircraft leaves from base {bid}",
        "cit_eta_h": "correct ETA ≈ {eta:.1f} h",
        "cit_pop": "population in the radius = {pop}",
        "cit_eta": "ETA ≈ {eta:.1f} h",
        "cit_focos": "detections = {n}",
        "cit_frp": "total FRP = {frp:.0f} MW",
        "cit_ti_uc": "check the distance to the indigenous land/protected area",
        "cit_dist_base": "base {nome} is {km:.1f} km away in a straight line",
        "cit_localidade_fora": "cite only places within this incident's radius",
        "cit_dist": "{nome} is {kms} km away",
        "cit_mal_formatada": "malformed evidence",
        "cit_localidade_texto": "{nome} is outside this incident's radius",
        "cit_dist_texto": "check the cited distance",
        "cit_id_inexistente": "{id} does not exist in this run's data: cite only crew/aircraft, base and incident ids from the DATA",
        "cit_cobertura_falsa": "in the plan, {oid} is served by: {reais}",
        "cit_sem_recurso": "no crew/aircraft",
        "resumo_sistema": ("{n} assignment(s): {lista}. Without a crew: {sem}. Reserve: {res}."),
        "resumo_nenhuma": "none",
        "resumo_nenhum": "none",
        "nota_resumo_reescrito": (" (Summary rewritten by the system from the final assignments: the agent's summary "
                                  "cited a nonexistent id or a coverage that does not match the plan.)"),
        "cr_checador_ok": "checker: no solvable hard violation",
        "cr_excecao_aceita": ("Exception accepted: memory {mid} (\"{texto}\", confidence {conf:.2f}) overrides the "
                              "nearest-base rule; {rid} should not go by road to {oid}."),
        "cr_memoria_fraca": "Memory {mid} has confidence {conf:.2f} < {minimo}: assignment {rid}→{oid} kept.",
        "cr_regra_rigida": "Hard rule {regra} ({oid} {rid}): {sugestao}.",
        "cr_pergunta_analista": ("Open question: {ids} get(s) a crew with no exposed population while {n} "
                                 "incident(s) go without; is it a recurring agricultural burn?"),
        "cr_analista_memoria_contra": ("Analyst: {oid} looks like an agricultural burn ({conf}), but memory {mid} "
                                       "(\"{texto}\", confidence {mconf:.2f}) says this fire has already "
                                       "reignited/grown: not downgrading, assignment kept."),
        "cr_analista_rebaixa": ("Analyst: {oid} is a likely agricultural burn (confidence {conf}); the crew does more "
                                "good at an uncovered incident."),
        "cr_analista_vegetacao": "Analyst: {oid} is a likely vegetation fire (confidence {conf}); assignment kept.",
        "cr_analista_inconclusivo": "Analyst inconclusive about {oid} ({conclusao}, {conf}): assignment kept as a precaution.",
        "cr_tradeoff": ("Trade-off: {oid} ({pop} people) waits {eta:.1f} h for {rid}, but {rid2} (at {oid2}, no "
                        "exposure) would arrive in {eta_alt:.1f} h."),
        "cr_troca": ("Local crew swap: {rid} reaches {para} ({pop_para} people) in {eta_para} h, but was sent to {de} "
                     "({pop_de} people) at {eta_atual} h; I swap it and {de} is left uncovered (escalation)."),
        "cr_esc_exposta_nao_atendida": ("Escalation: {oid} has {pop} people exposed and the viable crews/aircraft are "
                                        "at other incidents with population or in reserve."),
        "cr_esc_obrigatoria": ("Mandatory escalation: {oid} has {pop} people exposed and no crew/aircraft arrives "
                               "within {eta_max} h."),
        "cr_esc_memoria": ("Escalation: honoring the memory leaves {ids} (with population) with no viable crew; human "
                           "decision on using the route."),
        "cr_esc_sem_alternativa": "Escalation: I found no alternative plan that resolves the hard rules.",
        "cr_revisao_igual": "The review does not change the plan.",
        "cr_citacao": ("Incorrect citation in {alvo}: I rewrite the justification from the data; the allocation stays "
                       "the same."),
        "cr_sem_violacoes": "No violations and no relevant grey zone.",
        "cr_cp_offline": "Critic counter-proposal (offline).",
        "cr_cp_troca": "Critic counter-proposal (offline): local crew swap. ",
        "cr_cp_citacoes": "Critic counter-proposal (offline): justifications rewritten from the data. ",
        "cr_nota_troca": " (Local crew swap proposed by the Critic.)",
        "pl_adota_cp": "Adopts the Critic's counter-proposal. ",
        "pl_offline": "Offline Planner (deterministic): exposed population first",
        "pl_reserva_memoria": "reserve of {n} requested in memory",
        "pl_ajustes": "{n} priority adjustment(s) from memory/opinion",
        "pl_desvios": "deviations from the baseline: {lista}",
        "pl_igual": "same as the baseline",
        "pl_removido": "removed {r}→{o}",
        "pl_incluido": "added {r}→{o}",
        "sugestao_apoio_externo": "request external support",
        "esc_guarda_corpo": ("Mandatory: {pop} people exposed and no crew/aircraft assigned in the final plan. "
                             "Suggested action: {sug}."),
        "esc_guarda_corpo_alcance": ("Mandatory: {pop} people exposed and no crew/aircraft assigned in the final "
                                     "plan. {alcance} Suggested action: {sug}."),
        "esc_alcance": "Could reach it within the {eta_max} h limit: {lista}.",
        "esc_alcance_item": "{rid} ({eta:.1f} h; {destino})",
        "esc_alcance_mais": "and {n} more",
        "esc_destino_designado": "assigned to {alvos}",
        "esc_destino_reserva": "in reserve",
        "esc_alvo_loc": "the incident near {loc} ({pop} people)",
        "esc_alvo_sem_loc": "another incident ({pop} people)",
        "esc_destino_livre": "unassigned",
        "esc_sem_alcance": "No available crew/aircraft can reach it within the {eta_max} h limit.",
        "esc_insoluvel": "Mandatory: exposed population with no viable crew/aircraft within the maximum ETA.",
        "esc_impasse": ("Deadlock: {n} rounds without approval, with a hard rule still open ({regras}). "
                        "Last opinion: {parecer}"),
        "resumo_divergencia": ("Critic disagreement in a grey zone after {n} round(s) (not blocking; plan adopted: "
                               "{plano}). Critic's reasons: {motivos} || {resumo}"),
        "plano_cp_critico": "the Critic's counter-proposal",
        "plano_ultima": "the Planner's last proposal",
        "sis_aprovacao_recusada": "System: approval refused, a hard rule is violated: {regras}",
        "sis_escalacao_obrigatoria": "System: mandatory escalation, {oid} has exposed population and no viable crew/aircraft.",
        "prefixo_status": {"aprova": "[approved]", "escala": "[escalated]"},
        "an_pergunta": ("Is this incident probably a recurring agricultural or management burn, "
                        "or a wildfire in native vegetation?"),
        "an_memoria": ("vegetation: memory {mid} (confidence {conf:.2f}) says this fire has already reignited/grown: "
                       "\"{texto}\""),
        "an_noite_baixa": ("agricultural: {total:.0f} detections in 7 days, {fn:.0%} at night (management burns are "
                           "usually daytime)"),
        "an_noite_alta": "vegetation: {fn:.0%} of detections at night (fire that keeps burning unmanaged)",
        "an_recorrente": "agricultural: recurring and small ({dias} days with detections, max {maxf:.0f} detections/day)",
        "an_pico": "vegetation: peak of {maxf:.0f} detections in one day",
        "an_frp_baixo": "agricultural: low FRP ({fpf:.1f} MW per detection)",
        "an_frp_alto": "vegetation: high FRP ({fpf:.1f} MW per detection)",
        "an_frp_max": "vegetation: detection with max FRP {frp:.0f} MW",
        "an_crescendo": "vegetation: incident growing compared to the previous period",
        "an_estavel": "agricultural: incident {status}",
        "an_ti_perto": "vegetation: {d:.1f} km from an indigenous land/protected area",
        "an_ti_longe": "agricultural: far from indigenous lands/protected areas",
        "an_ti_longe_km": " ({d:.1f} km)",
        "an_ti_longe_sem": " (none in the radius)",
        "an_tempo": "vegetation: weather favors spread (VPD {vpd} kPa, wind {vento} km/h)",
        "an_poucos_dados": "uncertainty: only {dias} day(s) with detections in the history",
        "an_escore": "agricultural−vegetation score = {escore:+.1f} (threshold ±1.5; uncalibrated heuristic)",
        "llm_idioma": ("## Output language\nWrite ALL free text (justifications, reasons, summary, deviations, replies "
                       "to the Critic, opinion evidence) in **English**, even though these instructions are in "
                       "Portuguese. Keep place names, base names, resource ids and incident ids exactly as they "
                       "appear in the DATA (do not translate them). JSON keys and enumerated values (e.g. "
                       "aprova/rejeita/escala, baixa/media/alta, queima_agricola_provavel) stay exactly as specified. "
                       "When citing facts in English use forms such as \"2463 inhabitants\", \"ETA 0.4 h (limit 6 h)\" "
                       "and \"9.8 km\"."),
    },
}


def msg(chave: str, idioma: str | None = None, **campos) -> str:
    """Frase ``chave`` no idioma (cai no pt-BR se o idioma ou a chave não existir), formatada com ``campos``."""
    tabela = MENSAGENS.get(normalizar_idioma(idioma) or IDIOMA_PADRAO, MENSAGENS[IDIOMA_PADRAO])
    modelo = tabela.get(chave, MENSAGENS[IDIOMA_PADRAO][chave])
    return modelo.format(**campos) if campos else modelo


def rotulo(grupo: str, valor, idioma: str | None = None) -> str:
    """Valor enumerado traduzido (ex.: ``rotulo("tipos_recurso", "aereo", "en") == "air"``); desconhecido -> cru."""
    tabela = MENSAGENS.get(normalizar_idioma(idioma) or IDIOMA_PADRAO, MENSAGENS[IDIOMA_PADRAO])
    grupo_d = tabela.get(grupo, MENSAGENS[IDIOMA_PADRAO][grupo])
    return grupo_d.get(valor, str(valor)) if valor is not None else "-"


def prefixos_escalacao() -> tuple[str, ...]:
    """Começos de motivo do Crítico que pedem escalação, em todos os idiomas ("Escalação:", "Escalation:")."""
    return ("Escalação:", "Escalation:")
