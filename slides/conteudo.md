# FocoCerto: conteúdo dos slides

Estrutura do `pitch-deck-template.md` (12 slides + apêndice), adaptada ao que o Open Agent Hackathon 2026 exige do deck: (1) problema e usuários, (2) solução, (3) fluxo dos agentes e arquitetura, (4) stack técnica, (5) como o Zetaris e a Meterless foram usados, (6) o que foi único no uso dos patrocinadores, (7) visuais do produto, (8) melhorias futuras. A tabela abaixo mostra onde cada ponto aparece.

| Exigência | Slides |
|---|---|
| Problema e usuários | 3, 4 |
| Solução | 2, 5 |
| Fluxo dos agentes / arquitetura | 6 |
| Stack técnica | 7 |
| Uso do Zetaris e da Meterless | 7, apêndice A |
| O que foi único | apêndice A (levar para o corpo se houver espaço) |
| Visuais do produto | 1, 5, 8 |
| Melhorias futuras | 12 |

**Regras:** todo número vem do repositório (cache de 23/10/2026, `output_examples/`, `npm test`, `eval/RELATORIO.md`). Onde houver `[[...]]`, preencher com o valor real antes de exportar. Nada de "testado no Zetaris" enquanto não for verdade (o Nightshift real funciona desde 25/10/2026; o Zetaris real ainda não foi testado). Sugestão: os slides exportados ficam em inglês (juízes internacionais); este arquivo é a base em português.

---

## Slide 1: Título
- **FocoCerto**
- *Mais incêndios do que equipes: qual atender primeiro, com quem, e por quê.*
- Open Agent Hackathon 2026 · Track 3: Reasoning Architecture · Time UFSM (Universidade Federal de Santa Maria)
- **Visual:** à esquerda, nome e frase; à direita, captura do `mapa.html` do Tocantins (23/10) com as designações.

**Notas:** "Somos o time UFSM. O FocoCerto ajuda o coordenador regional a decidir quais incêndios atender primeiro quando há mais incêndios do que equipes."

## Slide 2: Resumo em 30 segundos
- **Problema:** incêndios simultâneos e equipes escassas; os painéis mostram *onde* está o fogo, não *qual atender primeiro*.
- **Usuário:** o nível de coordenação multiagência (salas de situação estaduais, PrevFogo/ICMBio; nos EUA, os MAC groups).
- **Solução:** um Planejador propõe a ordem de recursos, um Crítico contesta, um Analista responde perguntas em aberto com incerteza; cada designação traz a sua evidência; o humano aprova.
- **Prova:** dados reais do NASA FIRMS, bases reais com fonte, conformidade do H-MEM 13/13, ablação A/B/C/D com gabaritos commitados antes de rodar: no modo LLM, 75,9% (completo) contra 22,2% (alocador simples), 0 citações falsas no plano final.
- **Visual:** 4 ícones em linha (dados → planejar → criticar → aprovar).

## Slide 3: O problema
- **Hoje (Tocantins, 23/10/2026, dados VIIRS reais):** 514 detecções → **179 ocorrências**, **52** com uma cidade a menos de 15 km. Cenário da demo: **6 equipes** em bases reais (CBMTO e Prevfogo/Ibama, com fonte); a quantidade de equipes é simulada.
- As ferramentas públicas (FIRMS, GWIS/EFFIS, Painel do Fogo/BDQueimadas) mostram o fogo e o perigo; os sistemas de despacho registram pedidos.
- Não encontramos uma ferramenta aberta que proponha a prioridade entre ocorrências com um crítico que revise os trade-offs e deixe a justificativa auditável.
- **Enunciado:** *quando há mais incêndios do que equipes, o coordenador decide sob pressão, com dados espalhados e sem registro do porquê.*
- **Visual:** mapa com as 179 ocorrências, os 6 recursos e as bases coloridas por procedência.

**Notas:** "Detecção não é incêndio: o mesmo fogo aparece várias vezes, e parte é queima agrícola. Isso também faz parte do problema."

## Slide 4: Usuários e encaixe no desafio
- **Usuário principal:** coordenador regional/multiagência (define prioridades entre incidentes e aloca recursos escassos).
- **Não é o usuário:** o comandante do incidente (continua dono do Plano de Ação do incidente).
- **Secundários:** analistas da sala de situação; comandantes que recebem a nota de designação.
- **Por que a Track 3:** o valor está no *raciocínio*: trade-offs entre comunidades, exceções vindas do conhecimento de campo, quando escalar, com a incerteza declarada. Doutrina: vida → estabilização do incidente → propriedade e meio ambiente.
- **Limite honesto:** enquadramento baseado na doutrina pública; ainda não conversamos com operadores.

## Slide 5: A solução
- **Entrada:** cenário do coordenador (`cenarios/*.yaml`: equipes por base, reserva, notas) + configuração da região + bases em camadas (declarada → oficial com fonte → OSM → sede de município estimada), cada uma com a procedência no plano e no mapa.
- **Capacidades:** lista de prioridades calculada pelos dados (fórmula transparente) · ordem de recursos com ETA · checagem de regras e de citações · Crítico com contra-proposta · Analista (queima agrícola × incêndio em vegetação nativa) · memória entre períodos (H-MEM) · escalação obrigatória · aprovação humana.
- **Saída:** `plano.md` (escalações, ordem de recursos, lista de prioridades, justificativas com ids de evidência, bases e procedência, memórias usadas, ciclo de revisão, limitações), `plano.json`, `mapa.html`, `logs/<execucao>.jsonl`; a mesma coisa pela API HTTP (`app/api.py`) para uma tela web.
- **Diferenciais:** um crítico que julga a zona cinzenta em vez de só checar regras; cada fato citado numa justificativa é conferido contra os dados; a memória do conhecimento de campo do coordenador muda o plano seguinte.
- **Visual:** trecho de `output_examples/tocantins-escasso/plano.md` (tabela "Ordem de recursos").

## Slide 6: Arquitetura dos agentes
- **Agentes:** Planejador (ordem de recursos; pode desviar do alocador guloso, explicando por quê) · Crítico (trade-offs, exceções da memória, escalação, contra-proposta) · Analista (chamado pelo Crítico; 7 consultas; conclusão + confiança).
- **Ferramentas (determinísticas):** `monitor`, `alocador_simples`, `checar_regras`, `checar_citacoes`, `consultar`, `interpretar_memorias`.
- **Padrão de colaboração (não linear):** Planejador → checagens → Crítico ⇄ Analista; o Crítico rejeita → Planejador (máx. 3 rodadas); aprova → plano; escala → humano. Guarda-corpos no grafo: não há aprovação com regra rígida solúvel violada; toda ocorrência com população exposta que fica sem recurso no plano final é escalada com "solicitar apoio externo", mesmo se o Crítico aprovar (no código desde 25/10, depois das ablações). Regra `troca_recurso_local`: o Crítico troca uma equipe local para a ocorrência exposta que ela alcança primeiro.
- **Visual:** o diagrama mermaid do README ("The loop is not linear").

**Notas:** "O LLM decide o que o código não decide; números como ETA e população vêm sempre das ferramentas."

## Slide 7: Implementação técnica (stack)
| Camada | Escolha |
|---|---|
| Dados | **Zetaris** federando Postgres (FIRMS) + CSV no file store (GeoNames, OSM, lista oficial de bases com fonte) + REST do Open-Meteo com `CACHE TABLE`; 4 views SQL |
| IA | **Meterless Nightshift** (compatível com OpenAI) → **NVIDIA Nemotron** |
| Engine Meterless | **H-MEM**, referência oficial (serviço TypeScript, porta 7070) + versão em Python para o modo offline |
| Agentes | Python 3.12, LangGraph, pydantic, httpx; código escrito e revisado com Claude Code (Anthropic), sob responsabilidade do time |
| Interface | CLI (`run`, `nota`, `aprovar`, `avaliar`), API HTTP (FastAPI, `uvicorn app.api:app`), plano em Markdown/JSON, mapa Leaflet; tela web **[[se existir na hora de exportar]]** |
| Qualidade | pytest 221 passaram / 1 pulado (25/10), `npm test` 13/13, `check_submissao.py`, script de clone limpo, Docker, sample mode (`--sample` ou `SAMPLE_MODE=true`) |

- **Status:** **Nightshift real funcionando** desde 25/10/2026 (Nightshift Windows numa máquina do time com GPU NVIDIA, via Tailscale; `nvidia/nemotron-3-ultra-550b-a55b`; cada chamada traz recibo assinado `meterless.compute_receipt.v1` e o log grava `routed_model` e o `receipt_id`; um período no modo LLM ≈ 23 s, 2 chamadas). **Zetaris implementado, ainda não testado numa instância real** **[[atualizar se mudar]]**.
- **Visual:** a tabela acima com os logos dos patrocinadores.

## Slide 8: Demo
- **Cenário:** Tocantins, 23/10/2026, cenário escasso (6 equipes).
- **O que observar:** (0) as bases são reais e mostram a fonte (CBMTO, Prevfogo/Ibama); (1) no cenário escasso (modo offline), o Crítico escala 9 ocorrências com população em vez de escondê-las; (2) noutro cenário (Paranã, 24/10; `output_examples/tocantins-parana-analista/`), o Crítico chama o Analista, que faz 7 consultas e responde "**indeterminado**, confiança **baixa**" (FRP baixo e longe de TI/UC, mas a ocorrência está crescendo); o Crítico mantém a designação por precaução e escala as 3 ocorrências com população sem recurso. O cenário escasso não chama o Analista; (3) a nota *"estrada para São Félix alagada"* tira `saofelix-t1` (brigada Prevfogo de São Félix do Tocantins) de Lizarda, e a nota *"liberada"* a substitui e devolve o recurso; (4) a linha `llm_call` do log com `routed_model: nvidia/nemotron-3-ultra-550b-a55b` e o `receipt` (execução real pelo Nightshift).
- **Plano B:** o sample mode (`--sample`) roda o mesmo pipeline sem nenhum serviço; saídas em `output_examples/`.
- **Visual:** 3 capturas: terminal com o ciclo, `plano.md` com a memória, mapa com as bases por procedência. **[[Condicional: se a tela web existir na hora de gravar/exportar, trocar uma captura por ela]]**.

## Slide 9: Impacto e valor
- Decisões mais claras sob escassez: quem espera, e por quê, fica escrito (as escalações aparecem, não somem).
- **ETA ponderado por exposição** (quanto tempo a população exposta espera por um recurso), modo LLM: **4,40 h** no alocador simples → **3,77 h** no sistema completo (`eval/RELATORIO.md`).
- Auditável depois: cada designação aponta para ids de evidência (`focos:`, `pop:`, `eta:`, `dist:`) e para a memória que a mudou.
- **Escala por configuração:** uma região nova é um YAML (bbox + velocidade e tortuosidade declaradas); a mesma arquitetura serve para enchentes (ex.: RS 2024).

## Slide 10: Modelo de implantação
- **Implantação:** código aberto, roda numa máquina (Docker), dados no Zetaris, IA pelo Nightshift.
- **Bases sem cadastro paralelo:** hoje a camada oficial é um CSV com fonte; na implantação real, seria o sistema do próprio órgão (ex.: Sisfogo) federado pelo Zetaris. O coordenador só informa quantas equipes há em cada base.
- **Caminho de adoção:** piloto com uma sala de situação estadual (Tocantins) na temporada de fogo, lado a lado com o processo atual, sem despacho automático.
- **O que precisamos:** acesso a operadores (Corpo de Bombeiros do Tocantins, PrevFogo/Ibama, ICMBio) e a inventários reais de recursos.

## Slide 11: Riscos, limitações e mitigações
- **Zetaris ainda não testado numa instância real** → views validadas em Spark SQL 4.0 (698/698 iguais ao Python); passos para ligar documentados (`scripts/setup_zetaris.py`, `.env`).
- **Ablação no modo LLM concluída** (25/10): A 22,2%, B 65,4%, C 75,9%, D 73,6%; fatos errados do Nemotron corrigidos pelo checador (número a medir de novo: a contagem anterior tinha falsos positivos do checador); 0 citações falsas no plano final; 0 sobre-escalação. Limites: ganho da memória dentro da variação (C − D = 0,67 checagem por execução); no modo LLM as escalações vieram de impasse (sendo corrigido; ablação ainda não rodada de novo).
- **Agentes offline são simples** (Planejador ≈ alocador guloso) → o ganho das variantes da ablação depende do modo LLM.
- **Exposição superestimada** (população municipal do GeoNames) · **detecção ≠ incêndio** · queima agrícola inferida com incerteza · distância em linha reta × fator · Hot-Dry-Windy simplificado de superfície · TI/UC não ingeridos · quantidade de equipes simulada (bases reais, coordenada = sede do município) · sem validação com operadores.
- **IA responsável:** aprovação humana em todo plano; escalação obrigatória; incerteza declarada; só dados públicos, sem dados pessoais; dados simulados identificados.

## Slide 12: Próximos passos
- **Já:** rodar no Zetaris real (servidor do time); rodar a ablação no modo LLM de novo com a escalação obrigatória e a troca de recurso local; tela web sobre a API.
- **Em 2 a 3 meses:** validação com operadores; TI/UC (FUNAI/ICMBio) na exposição; filtro de queima agrícola por cobertura do solo; rotas reais; tipos de recurso (terrestre, aéreo, fluvial).
- **Depois:** modelo de propagação; outras doutrinas como configuração; outros desastres.
- **Fechamento:** *"Os painéis mostram onde está o fogo. O FocoCerto propõe qual atender primeiro e com quem, mostrando por quê, e um crítico revisa o plano antes de o coordenador aprovar."*

---

## Apêndice (só se perguntarem)

### A. Patrocinadores: como usamos e o que foi único
- **Zetaris:** a análise mora nas views (agrupamento, persistência, exposição, prioridade), federando três tipos de fonte; validação em Spark 698/698. *Ainda não rodou num Zetaris real.*
- **Meterless H-MEM:** as notas do coordenador mudam o plano; uma nota contrária substitui a antiga (*supersedes*, com ledger de auditoria, nada é apagado); memória por região; referência oficial + suíte de conformidade sem alterações: **13/13**.
- **Meterless Nightshift + NVIDIA Nemotron:** toda chamada de LLM passa por um único cliente; cada chamada registra `modelo`, `routed_model` e `receipt`. Funcionando no Nightshift real desde 25/10 com `nvidia/nemotron-3-ultra-550b-a55b`; raciocínio desligado (`enable_thinking=false`) porque com ele o Nemotron gastava os 4096 tokens pensando e não devolvia o JSON. Trecho real: `"agente": "planejador", "evento": "llm_call", "routed_model": "nvidia/nemotron-3-ultra-550b-a55b", "receipt": "rcpt_req_bf344q2l", "latencia_s": 15.674` (`docs/PATROCINADORES.md`).
- Detalhes: `docs/PATROCINADORES.md`.

### B. Trecho do log
- Uma linha `critico`/`escala` e uma `analista`/`consulta` de `output_examples/*/trace.jsonl` ou da execução do cenário agrícola; no modo LLM, uma linha `llm_call` com `routed_model` e `receipt` (de `logs/` da execução real pelo Nightshift).

### C. Avaliação
- Variantes A (alocador guloso), B (Planejador + checador), C (completo), D (C sem H-MEM); 12 cenários com dados reais; gabaritos commitados antes de qualquer execução (commit `1d722b5`); 3 execuções por cenário e variante.
- **Tabela (modo LLM, Nemotron pelo Nightshift, 144 execuções, 450 chamadas):** A 18/81 (22,2%) · B 53/81 (65,4%) · C 66/87 (75,9%) · D 64/87 (73,6%). Por execução: A 6,0/27, B 17,7/27, C 22,0/29, D 21,3/29. Fatos errados do LLM pegos: B 56, C 54, D 47; citações falsas no plano final: 0. Sobre-escalação: 0 em todas as variantes; escalações do modo LLM vieram de impasse. Offline (validação do pipeline): A 22,2%, B 59,3%, C 79,3%, D 58,6%.

### D. Fontes de dados
- NASA FIRMS VIIRS (focos), GeoNames cities1000 (localidades e população), OpenStreetMap (bases: só 2 dentro do Tocantins, as duas em Palmas), lista oficial de 12 bases do Tocantins com fonte por linha (CBMTO; Prevfogo/Ibama, Portaria nº 114/2024; ICMBio Esec Serra Geral), Open-Meteo (VPD, vento). Simulado: a quantidade de equipes por base.

### E. Componentes pré-existentes
- Engine de referência do H-MEM da Meterless (Apache-2.0, com adaptações marcadas) e bibliotecas abertas (LangGraph, pydantic, httpx, FastAPI, uvicorn, psycopg, PyYAML, pytest, tsx, Leaflet). Todo o resto foi escrito durante o hackathon, com Claude Code como ferramenta de IA para programar.
