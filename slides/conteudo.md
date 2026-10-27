# FocoCerto: conteúdo dos slides

Estrutura do `pitch-deck-template.md` (12 slides + apêndice), adaptada ao que o Open Agent Hackathon 2026 exige do deck: (1) problema e usuários, (2) solução, (3) fluxo dos agentes e arquitetura, (4) stack técnica, (5) como o Zetaris e a Meterless foram usados, (6) o que foi único no uso dos patrocinadores, (7) visuais do produto, (8) melhorias futuras. A tabela abaixo mostra onde cada ponto aparece.

| Exigência | Slides |
|---|---|
| Problema e usuários | 3, 4 |
| Solução | 2, 5 |
| Fluxo dos agentes / arquitetura | 6, 8b |
| Stack técnica | 7 |
| Uso do Zetaris e da Meterless | 7, apêndice A |
| O que foi único | apêndice A (levar para o corpo se houver espaço) |
| Visuais do produto | 1, 5, 8 |
| Melhorias futuras | 12 |

**Regras:** todo número vem do repositório (cache de 23/10/2026, `output_examples/`, `npm test`, `eval/RELATORIO.md`). Onde houver `[[...]]`, preencher com o valor real antes de exportar. Só afirmar o que foi testado (o Nightshift real funciona desde 25/10/2026; o Zetaris real funciona desde a noite de 25/10/2026, com uma execução real de ponta a ponta em `output_examples/tocantins-escasso-real/`). Sugestão: os slides exportados ficam em inglês (juízes internacionais); este arquivo é a base em português.

---

## Slide 1: Título
- **FocoCerto**
- *Mais incêndios do que equipes: qual atender primeiro, com quem, e por quê.*
- Open Agent Hackathon 2026 · Track 3: Reasoning Architecture · Time ECOMP - UFSM (Universidade Federal de Santa Maria)
- **Visual:** à esquerda, nome e frase; à direita, captura do `mapa.html` do Tocantins (23/10) com as designações.

**Notas:** "Somos o time ECOMP - UFSM. O FocoCerto ajuda o coordenador regional a decidir quais incêndios atender primeiro quando há mais incêndios do que equipes."

## Slide 2: Resumo em 30 segundos
- **Problema:** incêndios simultâneos e equipes escassas; os painéis mostram *onde* está o fogo, não *qual atender primeiro*.
- **Usuário:** o nível de coordenação multiagência (salas de situação estaduais, PrevFogo/ICMBio; nos EUA, os MAC groups).
- **Solução:** um Planejador propõe a ordem de recursos, um Crítico contesta, um Analista responde perguntas em aberto com incerteza; cada designação traz a sua evidência; o humano aprova.
- **Prova:** dados reais do NASA FIRMS, bases reais com fonte, conformidade do H-MEM 13/13, ablação A/B/C/D com gabaritos commitados antes de rodar: no modo LLM (rodada limpa, escopo do Nightshift isolado), 82,8% (completo) contra 22,2% (alocador simples), espera da população exposta de 4,4 h para 2,8 h, 0 citações falsas no plano final.
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
- **Diferenciais:** um crítico que julga a zona cinzenta em vez de só checar regras; cada fato e cada id citados pelo modelo são conferidos contra os dados, e um resumo que afirma uma cobertura que o plano não tem é reescrito; a memória do conhecimento de campo do coordenador muda o plano seguinte; o plano inteiro sai em inglês ou português (`--idioma en`), inclusive o texto do Nemotron.
- **Bases:** o coordenador declara onde estão as equipes; as outras bases conhecidas são só contexto (apagadas no mapa), cada uma com a procedência; a declarada vence quando coincide com uma conhecida.
- **Visual:** trecho de `output_examples/tocantins-escasso/plano.md` (tabela "Ordem de recursos").

## Slide 6: Arquitetura dos agentes
- **Agentes:** Planejador (ordem de recursos; pode desviar do alocador guloso, explicando por quê) · Crítico (trade-offs, exceções da memória, escalação, contra-proposta) · Analista (chamado pelo Crítico; 7 consultas; conclusão + confiança).
- **Ferramentas (determinísticas):** `monitor`, `alocador_simples`, `checar_regras`, `checar_citacoes`, `consultar`, `interpretar_memorias`.
- **Padrão de colaboração (não linear):** Planejador → checagens → Crítico ⇄ Analista; o Crítico rejeita → Planejador (máx. 3 rodadas); aprova → plano; escala → humano. Guarda-corpos no grafo: não há aprovação com regra rígida solúvel violada; toda ocorrência com população exposta que fica sem recurso no plano final é escalada com "solicitar apoio externo", mesmo se o Crítico aprovar (no código desde 25/10, depois da 1ª ablação LLM; a 2ª rodada já o inclui). Regra `troca_recurso_local`: o Crítico troca uma equipe local para a ocorrência exposta que ela alcança primeiro. **Quando o modelo erra:** citação errada, id inexistente ou cobertura falsa no resumo são corrigidos pelo sistema antes do Crítico e registrados (`citacao_corrigida`).
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
| Qualidade | pytest 331 passaram / 1 pulado (26/10), `npm test` 13/13, `check_submissao.py`, script de clone limpo, Docker, sample mode (`--sample` ou `SAMPLE_MODE=true`) |

- **Status:** **Nightshift real funcionando** desde 25/10/2026 (Nightshift Windows numa máquina do time com GPU NVIDIA, via Tailscale; `nvidia/nemotron-3-ultra-550b-a55b`; cada chamada traz recibo assinado `meterless.compute_receipt.v1` e o log grava `routed_model` e o `receipt_id`; um período real no modo LLM levou de 1,5 a 3 min com 4 chamadas). **Zetaris real funcionando** desde 25/10/2026 à noite (Zetaris 2.4 em Docker no servidor do time, via túnel SSH/Tailscale): setup com 0 falhas, 1.875 focos reais federados, a view `ocorrencias_prioridade` devolve 698 linhas, igual ao cálculo de referência em Python. **Execução real de ponta a ponta** (Zetaris + Nemotron pelo Nightshift + serviço H-MEM): `output_examples/tocantins-escasso-real/`, 2 rodadas, 4 chamadas, ~2,5 min, 6 designações e 9 escalações.
- **Visual:** a tabela acima com os logos dos patrocinadores.

## Slide 8: Demo
- **Cenário:** Tocantins, 23/10/2026, cenário escasso (6 equipes).
- **O que observar:** (0) as bases são reais e mostram a fonte (CBMTO, Prevfogo/Ibama); (1) no cenário escasso (modo offline), o Crítico escala 9 ocorrências com população em vez de escondê-las; (2) noutro cenário (Paranã, 24/10; `output_examples/tocantins-parana-analista/`), o Crítico chama o Analista, que faz 7 consultas e responde "**indeterminado**, confiança **baixa**" (FRP baixo e longe de TI/UC, mas a ocorrência está crescendo); o Crítico mantém a designação por precaução e escala as 3 ocorrências com população sem recurso. O cenário escasso não chama o Analista; (3) a nota *"estrada para São Félix alagada"* tira `saofelix-t1` (brigada Prevfogo de São Félix do Tocantins) de Lizarda, e a nota *"liberada"* a substitui e devolve o recurso; (4) a linha `llm_call` do log com `routed_model: nvidia/nemotron-3-ultra-550b-a55b` e o `receipt` (execução real pelo Nightshift); (5) a execução real de ponta a ponta (`output_examples/tocantins-escasso-real/`): dados pelas views do Zetaris (6 consultas SQL no trace), na rodada 1 o Crítico rejeita e pede 3 trocas `troca_recurso_local` (ex.: `dianopolis-t1` para Dianópolis, 22.424 hab., ETA 0,16 h), na rodada 2 aprova; 6 designações, 9 escalações.
- **Idioma:** gravar e capturar com `--idioma en` (plano e legenda do mapa em inglês; exemplo pronto: `output_examples/tocantins-escasso-en/`).
- **Mapa:** tamanho do círculo = nº de focos; linha tracejada = aeronave; base apagada = sem equipe no cenário; anel tracejado = escalada.
- **Plano B:** o sample mode (`--sample`) roda o mesmo pipeline sem nenhum serviço; saídas em `output_examples/`.
- **Visual:** 3 capturas: terminal com o ciclo, `plano.md` com a memória, mapa com as bases por procedência; opcional: a UI do Zetaris (`localhost:3000`, Data Explorer) com a consulta à `fococerto.ocorrencias_prioridade`. **[[Condicional: se a tela web existir na hora de gravar/exportar, trocar uma captura por ela]]**.

## Slide 8b: Evidência: quando o Nemotron inventa (se houver espaço, senão vai para as notas do slide 6)
- **Execução real em inglês, 26/10/2026** (`20261026T180817-eca168`; Nemotron 3 Ultra pelo Nightshift, 4 chamadas; dados do cache real): o resumo do Planejador dizia que `cel_-117_-491`, **87.545 pessoas expostas**, estava *"covered by gurupi-t1"*. Esse recurso não existe; no plano, a ocorrência estava sem equipe.
- **O sistema:** `id_inexistente` (gurupi-t1) + `cobertura_falsa` (gurupi-t1→cel_-117_-491, recursos reais: nenhum) → resumo reescrito a partir das designações finais **antes do Crítico** → evento `citacao_corrigida` no log → plano publicado: *"ESCALATED cel_-117_-491: 87545 people exposed and no crew/aircraft assigned… request external support"*.
- **Mensagem:** um id inventado ou uma cobertura falsa (nas formas que checamos) não chega ao coordenador, seja o que for que o modelo escreva, e a correção fica no log.
- **Limites honestos:** um caso, uma execução (mostra o mecanismo, não a frequência); a checagem de cobertura é heurística (duas formas de frase, pt e en); o motivo das escalações não é conferido. Reproduzido em `tests/test_citacoes_ids.py`.
- **Visual:** à esquerda a frase do modelo com "covered by gurupi-t1" riscada; à direita o resumo reescrito e a escalação.

## Slide 9: Impacto e valor
- Decisões mais claras sob escassez: quem espera, e por quê, fica escrito (as escalações aparecem, não somem).
- **ETA ponderado por exposição** (quanto tempo a população exposta espera por um recurso), modo LLM (rodada limpa): **4,40 h** no alocador simples → **2,76 h** no sistema completo (`eval/RELATORIO.md`).
- Auditável depois: cada designação aponta para ids de evidência (`focos:`, `pop:`, `eta:`, `dist:`) e para a memória que a mudou.
- **Escala por configuração:** uma região nova é um YAML (bbox + velocidade e tortuosidade declaradas); a mesma arquitetura serve para enchentes (ex.: RS 2024).

## Slide 10: Modelo de implantação
- **Implantação:** código aberto, roda numa máquina (Docker), dados no Zetaris, IA pelo Nightshift.
- **Bases sem cadastro paralelo:** hoje a camada oficial é um CSV com fonte; na implantação real, seria o sistema do próprio órgão (ex.: Sisfogo) federado pelo Zetaris. O coordenador só informa quantas equipes há em cada base.
- **Caminho de adoção:** piloto com uma sala de situação estadual (Tocantins) na temporada de fogo, lado a lado com o processo atual, sem despacho automático.
- **O que precisamos:** acesso a operadores (Corpo de Bombeiros do Tocantins, PrevFogo/Ibama, ICMBio) e a inventários reais de recursos.

## Slide 11: Riscos, limitações e mitigações
- **Uma só execução real de ponta a ponta** (Zetaris + Nightshift + H-MEM, um período do Tocantins) → o Zetaris real devolve as mesmas 698 ocorrências do Python; a ablação lê um cache local dos mesmos dados reais, não o Zetaris. O teste real exigiu ajustes (formato `{headers, data}` da API, descrições do `DESCRIBE BY`, porta do Postgres dentro da rede do Zetaris), todos documentados.
- **Ablação no modo LLM, rodada limpa** (26/10, cada execução no próprio escopo do Nightshift, 48 execuções, 122 chamadas): A 22,2%, B 63,0%, C 82,8%, D 79,3%; 44 fatos errados do Nemotron reescritos antes do Crítico (incl. 2 ids inventados); 0 citações falsas no plano final; espera da população exposta 4,40 h → 2,76 h. Limites: 1 repetição; a memória vale uma decisão no modo LLM (Mateiros, C − D = +1) e +18 no offline; as rodadas de 25/10 usavam o escopo `user`, em que o Nightshift junta ~4.900 tokens de contexto lembrado, e ficam só como histórico.
- **Checagem de cobertura heurística** (duas formas de frase) e motivos de escalação não conferidos.
- **Agentes offline são simples** (Planejador ≈ alocador guloso) → o ganho das variantes da ablação depende do modo LLM.
- **Exposição superestimada** (população municipal do GeoNames) · **detecção ≠ incêndio** · queima agrícola inferida com incerteza · distância em linha reta × fator · Hot-Dry-Windy simplificado de superfície · TI/UC não ingeridos · quantidade de equipes simulada (bases reais, coordenada = sede do município) · sem validação com operadores.
- **IA responsável:** aprovação humana em todo plano; escalação obrigatória; incerteza declarada; só dados públicos, sem dados pessoais; dados simulados identificados.

## Slide 12: Próximos passos
- **Já:** confirmar ou inativar uma base direto no mapa (gravado na memória, com o autor); perfis de acesso por cargo (coordenador, analista, leitura); a idade da fonte de cada base em destaque; rodar a ablação pelo Zetaris real (hoje lê o cache local) e de novo no modo LLM com todas as mudanças (e em inglês); tela web sobre a API.
- **Em 2 a 3 meses:** validação com operadores; TI/UC (FUNAI/ICMBio) na exposição; filtro de queima agrícola por cobertura do solo; rotas reais; tipos de recurso (terrestre, aéreo, fluvial).
- **Depois:** modelo de propagação; outras doutrinas como configuração; outros desastres.
- **Fechamento:** *"Os painéis mostram onde está o fogo. O FocoCerto propõe qual atender primeiro e com quem, mostrando por quê, e um crítico revisa o plano antes de o coordenador aprovar."*

---

## Apêndice (só se perguntarem)

### A. Patrocinadores: como usamos e o que foi único
- **Zetaris:** a análise mora nas views (agrupamento, persistência, exposição, prioridade), federando três tipos de fonte; rodando num Zetaris 2.4 real (setup com 0 falhas; `ocorrencias_prioridade` = 698 linhas, igual ao Python; antes, validação em Spark 698/698). Cada `run` registra no log as consultas SQL feitas ao Zetaris (`fonte: zetaris`).
- **Meterless H-MEM:** as notas do coordenador mudam o plano; uma nota contrária substitui a antiga (*supersedes*, com ledger de auditoria, nada é apagado); memória por região; referência oficial + suíte de conformidade sem alterações: **13/13**.
- **Meterless Nightshift + NVIDIA Nemotron:** toda chamada de LLM passa por um único cliente; cada chamada registra `modelo`, `routed_model` e `receipt`. Funcionando no Nightshift real desde 25/10 com `nvidia/nemotron-3-ultra-550b-a55b`; raciocínio desligado (`enable_thinking=false`) porque com ele o Nemotron gastava os 4096 tokens pensando e não devolvia o JSON. Trecho real: `"agente": "planejador", "evento": "llm_call", "routed_model": "nvidia/nemotron-3-ultra-550b-a55b", "receipt": "rcpt_req_bf344q2l", "latencia_s": 15.674` (`docs/PATROCINADORES.md`).
- Detalhes: `docs/PATROCINADORES.md`.

### B. Trecho do log
- Uma linha `critico`/`escala` e uma `analista`/`consulta` de `output_examples/*/trace.jsonl` ou da execução do cenário agrícola; no modo LLM, uma linha `llm_call` com `routed_model` e `receipt` (de `logs/` da execução real pelo Nightshift).

### C. Avaliação
- Variantes A (alocador guloso), B (Planejador + checador), C (completo), D (C sem H-MEM); 12 cenários com dados reais; gabaritos commitados antes de qualquer execução (commit `1d722b5`); 3 execuções por cenário e variante no offline e na 1ª rodada LLM; 1 na rodada limpa.
- **Tabela oficial (modo LLM limpo, Nemotron pelo Nightshift, escopo isolado, 48 execuções, 122 chamadas, 0 fallbacks):** A 6/27 (22,2%) · B 17/27 (63,0%) · C 24/29 (82,8%) · D 23/29 (79,3%). ETA ponderado: 4,40 / 3,87 / 2,76 / 3,06 h. Impasses: B 1, C 0, D 2. 44 fatos errados reescritos antes do Crítico (17 localidades, 15 distâncias, 6 populações, 1 ETA, 3 do resumo, 2 ids inventados); 0 citações falsas nos 36 planos finais. Offline (código de 26/10): A 22,2%, B 70,4%, C 82,8%, D 62,1%. Histórico (escopo `user`): 1ª rodada 22,2/65,4/75,9/73,6; 2ª rodada 22,2/77,8/82,8/82,8.

### D. Fontes de dados
- NASA FIRMS VIIRS (focos), GeoNames cities1000 (localidades e população), OpenStreetMap (bases: só 2 dentro do Tocantins, as duas em Palmas), lista oficial de 12 bases do Tocantins com fonte por linha (CBMTO; Prevfogo/Ibama, Portaria nº 114/2024; ICMBio Esec Serra Geral), Open-Meteo (VPD, vento). Simulado: a quantidade de equipes por base.

### E. Componentes pré-existentes
- Engine de referência do H-MEM da Meterless (Apache-2.0, com adaptações marcadas) e bibliotecas abertas (LangGraph, pydantic, httpx, FastAPI, uvicorn, psycopg, PyYAML, pytest, tsx, Leaflet). Todo o resto foi escrito durante o hackathon, com Claude Code como ferramenta de IA para programar.
