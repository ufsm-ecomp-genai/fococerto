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
- **Prova:** dados reais do NASA FIRMS, conformidade do H-MEM 13/13, ablação A/B/C/D com gabaritos commitados antes de rodar.
- **Visual:** 4 ícones em linha (dados → planejar → criticar → aprovar).

## Slide 3: O problema
- **Hoje (Tocantins, 23/10/2026, dados VIIRS reais):** 514 detecções → **179 ocorrências**, **52** com uma cidade a menos de 15 km. Cenário da demo: **6 equipes** (simuladas).
- As ferramentas públicas (FIRMS, GWIS/EFFIS, Painel do Fogo/BDQueimadas) mostram o fogo e o perigo; os sistemas de despacho registram pedidos.
- Não encontramos uma ferramenta aberta que proponha a prioridade entre ocorrências com um crítico que revise os trade-offs e deixe a justificativa auditável.
- **Enunciado:** *quando há mais incêndios do que equipes, o coordenador decide sob pressão, com dados espalhados e sem registro do porquê.*
- **Visual:** mapa com as 179 ocorrências e os 6 recursos.

**Notas:** "Detecção não é incêndio: o mesmo fogo aparece várias vezes, e parte é queima agrícola. Isso também faz parte do problema."

## Slide 4: Usuários e encaixe no desafio
- **Usuário principal:** coordenador regional/multiagência (define prioridades entre incidentes e aloca recursos escassos).
- **Não é o usuário:** o comandante do incidente (continua dono do Plano de Ação do incidente).
- **Secundários:** analistas da sala de situação; comandantes que recebem a nota de designação.
- **Por que a Track 3:** o valor está no *raciocínio*: trade-offs entre comunidades, exceções vindas do conhecimento de campo, quando escalar, com a incerteza declarada. Doutrina: vida → estabilização do incidente → propriedade e meio ambiente.
- **Limite honesto:** enquadramento baseado na doutrina pública; ainda não conversamos com operadores.

## Slide 5: A solução
- **Entrada:** cenário do coordenador (`cenarios/*.yaml`: equipes, bases, reserva, notas) + configuração da região.
- **Capacidades:** lista de prioridades calculada pelos dados (fórmula transparente) · ordem de recursos com ETA · checagem de regras e de citações · Crítico com contra-proposta · Analista (queima agrícola × incêndio em vegetação nativa) · memória entre períodos (H-MEM) · escalação obrigatória · aprovação humana.
- **Saída:** `plano.md` (escalações, ordem de recursos, lista de prioridades, justificativas com ids de evidência, memórias usadas, ciclo de revisão, limitações), `plano.json`, `mapa.html`, `logs/<execucao>.jsonl`.
- **Diferenciais:** um crítico que julga a zona cinzenta em vez de só checar regras; cada fato citado numa justificativa é conferido contra os dados; a memória do conhecimento de campo do coordenador muda o plano seguinte.
- **Visual:** trecho de `output_examples/tocantins-escasso/plano.md` (tabela "Ordem de recursos").

## Slide 6: Arquitetura dos agentes
- **Agentes:** Planejador (ordem de recursos; pode desviar do alocador guloso, explicando por quê) · Crítico (trade-offs, exceções da memória, escalação, contra-proposta) · Analista (chamado pelo Crítico; 7 consultas; conclusão + confiança).
- **Ferramentas (determinísticas):** `monitor`, `alocador_simples`, `checar_regras`, `checar_citacoes`, `consultar`, `interpretar_memorias`.
- **Padrão de colaboração (não linear):** Planejador → checagens → Crítico ⇄ Analista; o Crítico rejeita → Planejador (máx. 3 rodadas); aprova → plano; escala → humano. Guarda-corpos no grafo: não há aprovação com regra rígida solúvel violada; toda ocorrência com população exposta que fica sem recurso obriga a escalar (decisão do time, entra no código depois da ablação LLM em curso).
- **Visual:** o diagrama mermaid do README ("The loop is not linear").

**Notas:** "O LLM decide o que o código não decide; números como ETA e população vêm sempre das ferramentas."

## Slide 7: Implementação técnica (stack)
| Camada | Escolha |
|---|---|
| Dados | **Zetaris** federando Postgres (FIRMS) + CSV no file store (GeoNames, OSM) + REST do Open-Meteo com `CACHE TABLE`; 4 views SQL |
| IA | **Meterless Nightshift** (compatível com OpenAI) → **NVIDIA Nemotron** |
| Engine Meterless | **H-MEM**, referência oficial (serviço TypeScript, porta 7070) + versão em Python para o modo offline |
| Agentes | Python 3.12, LangGraph, pydantic, httpx |
| Interface | CLI (`run`, `nota`, `aprovar`) + `eval.run_ablacao`, plano em Markdown/JSON, mapa Leaflet |
| Qualidade | pytest 176 passaram / 1 pulado (com `npm ci` em `services/hmem`), `npm test` 13/13, `check_submissao.py`, script de clone limpo, Docker, sample mode |

- **Status:** **Nightshift real funcionando** desde 25/10/2026 (Nightshift Windows numa máquina do time com GPU NVIDIA, via Tailscale; `nvidia/nemotron-3-ultra-550b-a55b`; cada chamada traz recibo assinado `meterless.compute_receipt.v1` e o log grava `routed_model` e o `receipt_id`; um período no modo LLM ≈ 23 s, 2 chamadas). **Zetaris implementado, ainda não testado numa instância real** **[[atualizar se mudar]]**.
- **Visual:** a tabela acima com os logos dos patrocinadores.

## Slide 8: Demo
- **Cenário:** Tocantins, 23/10/2026, cenário escasso (6 equipes).
- **O que observar:** (1) no cenário escasso (modo offline), o Crítico escala 9 ocorrências com população em vez de escondê-las; (2) noutro cenário (Paranã, 24/10; `output_examples/tocantins-parana-analista/`), o Crítico chama o Analista, que faz 7 consultas e responde "**indeterminado**, confiança **baixa**" (FRP baixo e longe de TI/UC, mas a ocorrência está crescendo); o Crítico mantém a designação por precaução e escala as 3 ocorrências com população sem recurso. O cenário escasso não chama o Analista; (3) a nota *"estrada para Mateiros alagada"* tira `mateiros-t1` de Lizarda, e a nota *"liberada"* a substitui e devolve o recurso; (4) a linha `llm_call` do log com `routed_model: nvidia/nemotron-3-ultra-550b-a55b` e o `receipt` (execução real pelo Nightshift).
- **Plano B:** o sample mode (`--sample`) roda o mesmo pipeline sem nenhum serviço; saídas em `output_examples/`.
- **Visual:** 3 capturas: terminal com o ciclo, `plano.md` com a memória, mapa.

## Slide 9: Impacto e valor
- Decisões mais claras sob escassez: quem espera, e por quê, fica escrito (as escalações aparecem, não somem).
- **ETA ponderado por exposição** (quanto tempo a população exposta espera por um recurso) como métrica de impacto da ablação: **[[valor de eval/RELATORIO.md]]**.
- Auditável depois: cada designação aponta para ids de evidência (`focos:`, `pop:`, `eta:`, `dist:`) e para a memória que a mudou.
- **Escala por configuração:** uma região nova é um YAML (bbox + velocidade e tortuosidade declaradas); a mesma arquitetura serve para enchentes (ex.: RS 2024).

## Slide 10: Modelo de implantação
- **Implantação:** código aberto, roda numa máquina (Docker), dados no Zetaris, IA pelo Nightshift.
- **Caminho de adoção:** piloto com uma sala de situação estadual (Tocantins) na temporada de fogo, lado a lado com o processo atual, sem despacho automático.
- **O que precisamos:** acesso a operadores (Corpo de Bombeiros do Tocantins, PrevFogo/Ibama, ICMBio) e a inventários reais de recursos.

## Slide 11: Riscos, limitações e mitigações
- **Zetaris ainda não testado numa instância real** → views validadas em Spark SQL 4.0 (698/698 iguais ao Python); passos para ligar documentados (`scripts/setup_zetaris.py`, `.env`).
- **Ablação no modo LLM concluída** (25/10): A 22,2%, B 65,4%, C 75,9%, D 73,6%; ~50 fatos errados escritos pelo Nemotron, todos pegos; ganho da memória pequeno no modo LLM (+2 checagens).
- **Agentes offline são simples** (Planejador ≈ alocador guloso) → o ganho das variantes da ablação depende do modo LLM.
- **Exposição superestimada** (população municipal do GeoNames) · **detecção ≠ incêndio** · queima agrícola inferida com incerteza · distância em linha reta × fator · Hot-Dry-Windy simplificado de superfície · TI/UC não ingeridos · recursos simulados · sem validação com operadores.
- **IA responsável:** aprovação humana em todo plano; escalação obrigatória; incerteza declarada; só dados públicos, sem dados pessoais; dados simulados identificados.

## Slide 12: Próximos passos
- **Já:** rodar no Zetaris real (servidor do time); terminar a ablação no modo LLM (Nightshift/Nemotron real já funciona).
- **Em 2 a 3 meses:** validação com operadores; TI/UC (FUNAI/ICMBio) na exposição; filtro de queima agrícola por cobertura do solo; rotas reais; tipos de recurso (terrestre, aéreo, fluvial).
- **Depois:** modelo de propagação; outras doutrinas como configuração; outros desastres.
- **Fechamento:** *"Os painéis mostram onde está o fogo. O FocoCerto propõe qual atender primeiro e com quem, mostrando por quê, e um crítico revisa o plano antes de o coordenador aprovar."*

---

## Apêndice (só se perguntarem)

### A. Patrocinadores: como usamos e o que foi único
- **Zetaris:** a análise mora nas views (agrupamento, persistência, exposição, prioridade), federando três tipos de fonte; validação em Spark 698/698. *Ainda não rodou num Zetaris real.*
- **Meterless H-MEM:** as notas do coordenador mudam o plano; uma nota contrária substitui a antiga (*supersedes*, com ledger de auditoria, nada é apagado); memória por região; referência oficial + suíte de conformidade sem alterações: **13/13**.
- **Meterless Nightshift + NVIDIA Nemotron:** toda chamada de LLM passa por um único cliente; cada chamada registra `modelo`, `routed_model` e `receipt`. Funcionando no Nightshift real desde 25/10 com `nvidia/nemotron-3-ultra-550b-a55b`; raciocínio desligado (`enable_thinking=false`) porque com ele o Nemotron gastava os 4096 tokens pensando e não devolvia o JSON. **[[trecho do log de docs/PATROCINADORES.md]]**
- Detalhes: `docs/PATROCINADORES.md`.

### B. Trecho do log
- Uma linha `critico`/`escala` e uma `analista`/`consulta` de `output_examples/*/trace.jsonl` ou da execução do cenário agrícola; no modo LLM, uma linha `llm_call` com `routed_model` e `receipt` (de `logs/` da execução real pelo Nightshift).

### C. Avaliação
- Variantes A (alocador guloso), B (Planejador + checador), C (completo), D (C sem H-MEM); 12 cenários com dados reais; gabaritos commitados antes de qualquer execução (commit `1d722b5`); 3 execuções por cenário e variante.
- **Tabela:** **[[colar de eval/RELATORIO.md, dizendo o modo: offline ou LLM]]**.

### D. Fontes de dados
- NASA FIRMS VIIRS (focos), GeoNames cities1000 (localidades e população), OpenStreetMap (bases: só 2 dentro do Tocantins, as duas em Palmas; as demais são declaradas pelo coordenador e marcadas simuladas), Open-Meteo (VPD, vento).

### E. Componentes pré-existentes
- Engine de referência do H-MEM da Meterless (Apache-2.0, com adaptações marcadas) e bibliotecas abertas (LangGraph, pydantic, httpx, psycopg, PyYAML, pytest, tsx, Leaflet). Todo o resto foi escrito durante o hackathon.
