import { useState } from 'react';
import {
  BookOpen,
  Map as MapIcon,
  ListChecks,
  GitBranch,
  ShieldCheck,
  HelpCircle,
  ChevronDown,
  ExternalLink,
} from 'lucide-react';

// Central de ajuda: o que é o FocoCerto, como ler cada tela, como um plano é feito, glossário, limites e perguntas
// frequentes. Os textos ficam aqui (pt e en lado a lado) porque são longos; o resto da interface usa o i18nNovo.
const TEXTO = {
  pt: {
    titulo: 'Como o FocoCerto funciona',
    intro:
      'Quando há mais incêndios do que equipes, o FocoCerto propõe quais focos atender primeiro e com qual equipe, e mostra por quê. Ele é feito para o coordenador regional, que prioriza entre vários incêndios ao mesmo tempo. O sistema recomenda; quem decide é sempre o coordenador.',
    telasTitulo: 'As três telas',
    telas: [
      {
        icone: MapIcon,
        nome: 'Visão geral',
        texto: [
          'No topo: quantas equipes foram designadas, quantas ocorrências precisam de você e quantas equipes ficaram de reserva.',
          'O mapa mostra cada ocorrência pela cor da prioridade (alta, média, baixa). Um anel tracejado indica uma ocorrência escalada para você. Linhas azuis ligam cada equipe à ocorrência para onde vai (contínua: por terra; tracejada: aeronave). Quadrados são as bases, coloridos pela procedência.',
          '"Precisam de você" lista as escalações, da mais populosa para a menos. Clique numa delas para ver o motivo completo, quais equipes poderiam ter chegado a tempo e para onde cada uma foi, e para aproximar o mapa.',
          'Embaixo, as abas: ordem de atendimento (quem vai para onde, com tempo de chegada e justificativa), raciocínio e trace.',
        ],
      },
      {
        icone: ListChecks,
        nome: 'Recursos do dia',
        texto: [
          'Monte o dia em três passos: escolha um cenário pronto ou comece do zero; ajuste equipes, aeronaves e bases; defina a reserva e as notas, e gere o plano.',
          'Deixe "sample" ligado para rodar com dados reais em cache e agentes determinísticos, sem chaves nem serviços. Desligado, o plano usa o Zetaris, o Nemotron pelo Nightshift e o H-MEM configurados no servidor.',
          'Uma nota como "estrada para São Félix alagada" vira memória: no próximo plano, a equipe daquela base não sai por terra até uma nota contrária.',
        ],
      },
      {
        icone: GitBranch,
        nome: 'Histórico',
        texto: [
          'Mostra como o plano foi construído: o que o Planejador propôs em cada rodada, o que as checagens apontaram, as razões do Crítico e a contraproposta dele.',
          'Também mostra os pareceres do Analista (com nível de confiança), as memórias usadas e o trace: cada chamada ao modelo, com o modelo que respondeu e o recibo assinado.',
        ],
      },
    ],
    comoTitulo: 'Como um plano é feito',
    como: [
      [
        'Dados',
        'Focos de satélite (NASA FIRMS), localidades e população, clima e bases oficiais chegam pelas views do Zetaris.',
      ],
      [
        'Prioridade',
        'Cada ocorrência recebe uma prioridade transparente: exposição (35%), intensidade (25%), clima (20%), persistência (10%) e crescimento (10%).',
      ],
      [
        'Planejador',
        'Parte de uma alocação simples (a mais prioritária recebe o recurso viável mais próximo) e pode se desviar dela, explicando por quê.',
      ],
      [
        'Checagens',
        'O código confere regras rígidas (capacidade, tempo máximo, reserva) e cada fato citado: cidade, distância, população, tempo e ids. Fatos errados são reescritos antes do Crítico.',
      ],
      [
        'Crítico e Analista',
        'O Crítico julga as trocas e as exceções de memória; pode rejeitar com contraproposta (até 3 rodadas), chamar o Analista para uma dúvida em aberto ou escalar.',
      ],
      ['Você', 'Ocorrência com gente exposta e sem equipe é sempre escalada. Nada é despachado sem a sua aprovação.'],
    ],
    glossarioTitulo: 'Glossário',
    glossario: [
      [
        'Ocorrência',
        'Focos de satélite agrupados numa célula de cerca de 11 km, no mesmo dia. Um foco detectado não é um incêndio confirmado.',
      ],
      ['Prioridade', 'Índice de 0 a 1 calculado dos dados; as faixas alta, média e baixa são relativas ao período.'],
      [
        'Pessoas expostas',
        'População das localidades a até 15 km da ocorrência (é a população do município, então superestima perto de cidades).',
      ],
      [
        'ETA',
        'Tempo estimado de chegada: distância em linha reta × fator de tortuosidade ÷ velocidade declarada. Não é rota de navegação.',
      ],
      [
        'Escalação',
        'Decisão que volta para o coordenador, com o motivo e uma sugestão (por exemplo, pedir apoio externo).',
      ],
      ['Reserva', 'Equipes que o coordenador mandou guardar para contingência.'],
      [
        'Procedência da base',
        'Declarada (pelo coordenador), oficial (lista com fonte), OSM ou estimada (sede de município).',
      ],
      [
        'Recursos simulados',
        'As bases são reais, com fonte; a quantidade de equipes em cada base vem do cenário de demonstração.',
      ],
      ['Modo sample', 'Roda tudo com dados reais em cache e agentes determinísticos, sem chamar nenhum serviço.'],
      [
        'Memória (H-MEM)',
        'Notas do coordenador e lições aprendidas entre períodos. Uma nota contrária substitui a anterior; nada é apagado.',
      ],
      [
        'Recibo',
        'Comprovante assinado que o Nightshift devolve em cada chamada ao modelo, com o modelo que respondeu.',
      ],
    ],
    limitesTitulo: 'O que ele não faz',
    limites: [
      'Não despacha equipes: aprovar grava a decisão, não aciona ninguém, e não resolve as escalações.',
      'Não confirma incêndios: queima agrícola ou incêndio é uma inferência, com incerteza declarada.',
      'Não calcula rotas reais nem foi validado com operadores ainda.',
    ],
    faqTitulo: 'Perguntas frequentes',
    faq: [
      [
        'Por que uma ocorrência com muita gente ficou sem equipe?',
        'Abra a escalação: ela diz quais equipes poderiam ter chegado a tempo e para onde cada uma foi. A troca fica visível para você decidir, por exemplo pedindo apoio externo.',
      ],
      [
        'Aprovar despacha as equipes?',
        'Não. Aprovar registra a decisão. As escalações continuam abertas até você tratá-las.',
      ],
      [
        'De onde vêm os dados?',
        'NASA FIRMS (focos), GeoNames (localidades e população), Open-Meteo (clima), OpenStreetMap e listas oficiais de bases (CBMTO, Prevfogo/Ibama, ICMBio).',
      ],
      [
        'Qual modelo de IA decide?',
        'NVIDIA Nemotron 3 Ultra, chamado pelo Meterless Nightshift. Os números (distâncias, tempos, população) vêm sempre das ferramentas, nunca do modelo.',
      ],
      [
        'E se o modelo errar?',
        'Cada fato que ele escreve é conferido com os dados. Fatos errados e ids inventados são reescritos antes do Crítico; o caso real está no exemplo nemotron-invented-id-en.',
      ],
    ],
    rodape: 'Código, dados, gabaritos e avaliação estão no repositório.',
  },
  en: {
    titulo: 'How FocoCerto works',
    intro:
      'When there are more wildfires than crews, FocoCerto proposes which fires to answer first and with which crew, and shows why. It is built for the regional coordinator who sets priorities across simultaneous fires. The system recommends; the coordinator always decides.',
    telasTitulo: 'The three screens',
    telas: [
      {
        icone: MapIcon,
        nome: 'Overview',
        texto: [
          'At the top: how many crews are assigned, how many incidents need you, and how many crews are in reserve.',
          'The map shows each incident by priority colour (high, medium, low). A dashed ring marks an incident escalated to you. Blue lines link each crew to where it is going (solid: ground; dashed: aircraft). Squares are stations, coloured by provenance.',
          '"Need your decision" lists the escalations, most people first. Click one to read the full reason, which crews could have reached it in time and where each one went, and to zoom the map there.',
          'Below, the tabs: response order (who goes where, with arrival time and rationale), reasoning and trace.',
        ],
      },
      {
        icone: ListChecks,
        nome: 'Daily resources',
        texto: [
          'Build the day in three steps: pick a ready scenario or start from scratch; adjust crews, aircraft and stations; set the reserve and notes, and generate the plan.',
          'Keep "sample" on to run on cached real data with deterministic agents, without keys or services. Turned off, the plan uses the Zetaris, Nemotron (through Nightshift) and H-MEM configured on the server.',
          'A note such as "road to São Félix flooded" becomes memory: in the next plan, that station’s crew does not leave by road until a contrary note.',
        ],
      },
      {
        icone: GitBranch,
        nome: 'History',
        texto: [
          'Shows how the plan was built: what the Planner proposed in each round, what the checks flagged, the Critic’s reasons and counter-proposal.',
          'It also shows the Analyst’s assessments (with confidence), the memories used and the trace: every model call, with the model that answered and the signed receipt.',
        ],
      },
    ],
    comoTitulo: 'How a plan is made',
    como: [
      [
        'Data',
        'Satellite detections (NASA FIRMS), towns and population, weather and official stations come through the Zetaris views.',
      ],
      [
        'Priority',
        'Each incident gets a transparent priority: exposure (35%), intensity (25%), weather (20%), persistence (10%) and growth (10%).',
      ],
      [
        'Planner',
        'Starts from a simple allocation (the highest priority gets the nearest feasible resource) and may deviate, explaining why.',
      ],
      [
        'Checks',
        'Code verifies hard rules (capacity, maximum time, reserve) and every cited fact: town, distance, population, time and ids. Wrong facts are rewritten before the Critic.',
      ],
      [
        'Critic and Analyst',
        'The Critic judges trade-offs and memory exceptions; it can reject with a counter-proposal (up to 3 rounds), call the Analyst for an open question, or escalate.',
      ],
      [
        'You',
        'An incident with exposed people and no crew is always escalated. Nothing is dispatched without your approval.',
      ],
    ],
    glossarioTitulo: 'Glossary',
    glossario: [
      [
        'Incident',
        'Satellite detections grouped in a cell of about 11 km on the same day. A detection is not a confirmed fire.',
      ],
      [
        'Priority',
        'An index from 0 to 1 computed from the data; the high, medium and low bands are relative to the period.',
      ],
      [
        'People exposed',
        'Population of the towns within 15 km of the incident (municipal population, so it overestimates near towns).',
      ],
      [
        'ETA',
        'Estimated arrival time: straight-line distance × a tortuosity factor ÷ declared speed. Not a navigation route.',
      ],
      [
        'Escalation',
        'A decision handed back to the coordinator, with the reason and a suggestion (for example, request external support).',
      ],
      ['Reserve', 'Crews the coordinator asked to keep for contingencies.'],
      [
        'Station provenance',
        'Declared (by the coordinator), official (a sourced list), OSM, or estimated (a municipal seat).',
      ],
      [
        'Simulated resources',
        'Stations are real, with sources; how many crews each station has comes from the demo scenario.',
      ],
      ['Sample mode', 'Runs everything on cached real data with deterministic agents, without calling any service.'],
      [
        'Memory (H-MEM)',
        'Coordinator notes and lessons learned between periods. A contrary note supersedes the old one; nothing is deleted.',
      ],
      ['Receipt', 'A signed record that Nightshift returns for each model call, naming the model that answered.'],
    ],
    limitesTitulo: 'What it does not do',
    limites: [
      'It does not dispatch crews: approving records the decision, notifies no one, and does not resolve escalations.',
      'It does not confirm fires: agricultural burn versus wildfire is an inference, with stated uncertainty.',
      'It does not compute real routes, and it has not been validated with operators yet.',
    ],
    faqTitulo: 'Frequently asked questions',
    faq: [
      [
        'Why did an incident with many people get no crew?',
        'Open the escalation: it says which crews could have reached it in time and where each one went. The trade-off is visible so you can decide, for example by requesting external support.',
      ],
      [
        'Does approving dispatch the crews?',
        'No. Approving records the decision. Escalations stay open until you handle them.',
      ],
      [
        'Where does the data come from?',
        'NASA FIRMS (detections), GeoNames (towns and population), Open-Meteo (weather), OpenStreetMap and official station lists (CBMTO, Prevfogo/Ibama, ICMBio).',
      ],
      [
        'Which AI model decides?',
        'NVIDIA Nemotron 3 Ultra, called through Meterless Nightshift. Numbers (distances, times, population) always come from tools, never from the model.',
      ],
      [
        'What if the model is wrong?',
        'Every fact it writes is checked against the data. Wrong facts and invented ids are rewritten before the Critic; the real case is in the nemotron-invented-id-en example.',
      ],
    ],
    rodape: 'Code, data, answer keys and evaluation are in the repository.',
  },
};

function Pergunta({ pergunta, resposta }) {
  const [aberta, setAberta] = useState(false);
  return (
    <div className={`help-faq-item ${aberta ? 'open' : ''}`}>
      <button onClick={() => setAberta((x) => !x)} aria-expanded={aberta}>
        <span>{pergunta}</span>
        <ChevronDown size={16} />
      </button>
      {aberta && <p>{resposta}</p>}
    </div>
  );
}

export default function Ajuda({ locale }) {
  const x = TEXTO[String(locale).startsWith('en') ? 'en' : 'pt'];
  return (
    <div className="help">
      <section className="panel help-intro">
        <BookOpen size={22} />
        <div>
          <h2>{x.titulo}</h2>
          <p>{x.intro}</p>
        </div>
      </section>

      <h3 className="help-section-title">{x.telasTitulo}</h3>
      <div className="help-cards">
        {x.telas.map(({ icone: Icone, nome, texto }) => (
          <section key={nome} className="panel help-card">
            <h4>
              <Icone size={18} /> {nome}
            </h4>
            {texto.map((p) => (
              <p key={p}>{p}</p>
            ))}
          </section>
        ))}
      </div>

      <h3 className="help-section-title">{x.comoTitulo}</h3>
      <ol className="panel help-steps">
        {x.como.map(([etapa, texto], i) => (
          <li key={etapa}>
            <span className="help-step-n">{i + 1}</span>
            <div>
              <b>{etapa}</b>
              <p>{texto}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="help-two">
        <section className="panel help-glossary">
          <h3 className="help-section-title">{x.glossarioTitulo}</h3>
          <dl>
            {x.glossario.map(([termo, def]) => (
              <div key={termo}>
                <dt>{termo}</dt>
                <dd>{def}</dd>
              </div>
            ))}
          </dl>
        </section>
        <div className="help-side">
          <section className="panel help-limits">
            <h3 className="help-section-title">
              <ShieldCheck size={18} /> {x.limitesTitulo}
            </h3>
            <ul>
              {x.limites.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </section>
          <section className="panel help-faq">
            <h3 className="help-section-title">
              <HelpCircle size={18} /> {x.faqTitulo}
            </h3>
            {x.faq.map(([q, a]) => (
              <Pergunta key={q} pergunta={q} resposta={a} />
            ))}
          </section>
          <a
            className="help-repo"
            href="https://github.com/ufsm-ecomp-genai/fococerto"
            target="_blank"
            rel="noreferrer"
          >
            {x.rodape} <ExternalLink size={14} />
          </a>
        </div>
      </div>
    </div>
  );
}
