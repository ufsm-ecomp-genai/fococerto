// Textos das telas novas (AppNovo, Plan, MapaPlano). Estende i18n.js sem alterá-lo: o que não está aqui cai no translator original.
// Valores enumerados do JSON (regra, origem_critico, agente, faixa) são traduzidos na tela (web/README.md, regra 7).
import {translator as base} from './i18n.js';
const en={
 'Escalações: decisão humana necessária':'Escalations: human decision required','Ver no mapa':'Show on map','Sugestão':'Suggestion','Escalação geral':'General escalation',
 'RECURSOS SIMULADOS':'SIMULATED RESOURCES','as equipes e aeronaves deste plano vêm de um cenário de demonstração, não de um inventário real.':'the crews and aircraft in this plan come from a demonstration scenario, not from a real inventory.',
 'ocorrências sem recurso designado':'incidents with no assigned resource','Justificativa e evidências':'Justification and evidence','estimativa':'estimate','faixa':'band',
 'Recursos em reserva':'Resources in reserve','Ocorrências não atendidas':'Unserved incidents','nenhum':'none',
 'Prioridade (faixa do período)':'Priority (band for this period)','Escalada':'Escalated','Base':'Station','Terrestre':'Ground','Aéreo':'Air','Equipes':'Crews',
 'Rodada':'Round','Crítico':'Critic','Proposta do Planejador':'Planner proposal','Regra':'Rule','Ocorrência':'Incident','Recurso':'Resource','rígida':'hard rule',
 'Nenhuma violação de regra nesta rodada.':'No rule violations in this round.','Motivos do Crítico':'Critic reasons','Contra-proposta do Crítico':'Critic counter-proposal','Histórico completo':'Full history',
 'chamadas de LLM':'LLM calls','Só chamadas de LLM':'LLM calls only','Hora (UTC)':'Time (UTC)','Agente':'Agent','Evento':'Event','Modelo':'Model','Latência':'Latency',
 'O trace deste plano está no servidor':'This plan’s trace is on the server','A API serve o trace só dos exemplos.':'The API serves traces for examples only.',
 'Verificando API…':'Checking API…','API conectada':'API connected','API fora do ar':'API offline',
 'Fora da região (bbox + 1°): a API vai recusar esta base.':'Outside the region (bbox + 1°): the API will reject this station.','A menos de 3 km de':'Less than 3 km from','as duas serão fundidas e a declarada prevalece.':'the two will be merged and the declared one prevails.','Base conhecida mais próxima':'Nearest known station',
 'capacidade_excedida':'Capacity exceeded','citacao_incorreta':'Incorrect citation','eta_acima_limite':'ETA above limit','exposicao_sem_recurso_viavel':'Exposure with no viable resource','exposta_nao_atendida':'Exposed incident unserved','exposta_sem_recurso':'Exposed incident without resource','ocorrencia_inexistente':'Unknown incident','recurso_duplicado':'Duplicated resource','recurso_indisponivel':'Unavailable resource','recurso_inexistente':'Unknown resource','reserva_nao_mantida':'Reserve not kept','restricao_memoria':'Memory constraint','troca_recurso_local':'Local crew swap',
 'offline_deterministico':'offline (deterministic)','llm':'LLM','sistema':'system','ferramenta':'tool','planejador':'planner','critico':'critic','analista':'analyst','persistente':'Persistent',
};
const pt={
 'capacidade_excedida':'Capacidade excedida','citacao_incorreta':'Citação incorreta','eta_acima_limite':'ETA acima do limite','exposicao_sem_recurso_viavel':'Exposição sem recurso viável','exposta_nao_atendida':'Exposta não atendida','exposta_sem_recurso':'Exposta sem recurso','ocorrencia_inexistente':'Ocorrência inexistente','recurso_duplicado':'Recurso duplicado','recurso_indisponivel':'Recurso indisponível','recurso_inexistente':'Recurso inexistente','reserva_nao_mantida':'Reserva não mantida','restricao_memoria':'Restrição da memória','troca_recurso_local':'Troca de equipe local',
 'offline_deterministico':'offline (determinístico)','llm':'LLM','sistema':'sistema','ferramenta':'ferramenta','planejador':'Planejador','critico':'Crítico','analista':'Analista','persistente':'Persistente',
};
export function translator(locale) {const t=base(locale),extra=locale?.startsWith('en')?en:pt;return text=>extra[text]||t(text);}
