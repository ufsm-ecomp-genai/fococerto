# Roteiro do vídeo de demonstração (até 4 min)

Baseado na seção 14 da especificação, ajustado ao que **existe de fato** no repositório em 25/10/2026 (bases em camadas, API HTTP, ablação no modo LLM concluída, **Zetaris real funcionando** e uma execução real de ponta a ponta em `output_examples/tocantins-escasso-real/`). O vídeo vale 15 pontos e precisa mostrar o agente funcionando (não slides), a integração com o Zetaris, o engine Meterless e **uma requisição real passando pelo Nightshift**.

Legenda: **[NIGHTSHIFT]** = precisa do Nightshift real no ar na hora de gravar (funciona desde 25/10/2026 ~01h UTC: Nightshift Windows na máquina do time com GPU NVIDIA, via Tailscale, modelo `nvidia/nemotron-3-ultra-550b-a55b`). **[ZETARIS]** = precisa do Zetaris real no ar na hora de gravar (funciona desde 25/10/2026 à noite: Zetaris 2.4 em Docker no servidor Debian do time, acessado por túnel SSH/Tailscale; UI em `http://localhost:3000` pelo túnel). **[WEB]** = depende da tela web (front-end) existir e funcionar na hora de gravar: hoje só existe a API (`uvicorn app.api:app --port 8000`, contrato em `web/README.md`), ainda não há tela. Cada trecho marcado tem um **plano B** que não finge o que não aconteceu.

**Base da gravação:** a execução real de 25/10/2026 (23:22–23:25 UTC) salva em `output_examples/tocantins-escasso-real/` (dados pelas views do Zetaris, decisões do Nemotron 3 Ultra pelo Nightshift, memória no serviço H-MEM real): 2 rodadas, 4 chamadas ao Nemotron, ~2,5 min, 6 designações e 9 escalações obrigatórias. Gravar uma execução nova igual a essa; se algo cair na hora, mostrar os arquivos dessa execução (plano, mapa e trace), dizendo que é a execução de 25/10.

## Antes de gravar (checklist)
- [ ] `rm -rf data/estado out` para começar com a memória vazia (com o serviço H-MEM real, a memória fica em `services/hmem/data/`: esvaziar também, se quiser começar do zero).
- [ ] Terminal com fonte grande; `.env` **nunca** aparece na tela (nem token, nem chave da NVIDIA).
- [ ] Nightshift: ligar a máquina do time e o Tailscale; `.env` com `LLM_PROVIDER=nightshift`, `METERLESS_BASE_URL` (endereço Tailscale), `METERLESS_RUNTIME_TOKEN` (conteúdo do arquivo `proxy-token`) e `METERLESS_MODEL=nvidia/nemotron-3-ultra-550b-a55b`; rodar **sem** `--sample`. Rodar uma vez antes: no teste de 25/10 um período do cenário escasso levou ~23 s com 2 chamadas (Planejador e Crítico). Gravar a execução real, cortando só a espera.
- [ ] Zetaris: subir o servidor e o túnel; conferir que `scripts/setup_zetaris.py --regioes tocantins` já foi feito (rodar `--so-cache` depois de qualquer reinício do Zetaris, senão a tabela do Open-Meteo perde o cache). `.env` com `ZETARIS_REST_URL`, `ZETARIS_ORG_ID`, `ZETARIS_API_KEY`, `POSTGRES_DSN`, `ZETARIS_PG_HOST`, `ZETARIS_PG_PORT`. Abrir a UI em `http://localhost:3000` já logado, no Data Explorer, com a consulta da seção 2 pronta no SQL editor.
- [ ] Serviço H-MEM no ar (`cd services/hmem && npm start`, porta 7070) e `HMEM_URL=http://127.0.0.1:7070` no `.env`.
- [ ] Ensaiar uma vez: na execução de 25/10 a leitura dos dados pelo Zetaris levou ~1 min e as 4 chamadas ao Nemotron ~1,5 min. Cortar só a espera.
- [ ] Abrir `out/tocantins/2026-10-23/mapa.html` no navegador já com o zoom no Tocantins.
- [ ] Ter a tabela da ablação pronta (de `eval/RELATORIO.md`, seção "Modo LLM").
- [ ] **[WEB]** Se a tela existir: API no ar (`.venv/bin/uvicorn app.api:app --port 8000`) e a tela aberta no navegador, já com o período 23/10. Conferir antes que ela mostra a procedência das bases e as escalações.

---

## 1. (0:00–0:25) O problema
**Tela:** `mapa.html` do Tocantins, período 23/10/2026.

**Fala:** "Ontem, 23 de outubro, o satélite VIIRS da NASA registrou 514 detecções no Tocantins. Agrupadas, são 179 ocorrências, e 52 têm uma cidade a menos de 15 km. O coordenador regional tem 6 equipes, em quartéis do Corpo de Bombeiros e brigadas do Prevfogo que existem de verdade. Qual ocorrência atender primeiro, e com quem? O FocoCerto propõe a ordem de recursos, um crítico revisa, e o coordenador aprova."

**Dizer na tela (legenda):** "Focos reais (NASA FIRMS). Bases reais, com fonte (CBMTO, Prevfogo/Ibama). Quantidade de equipes: simulada."

**Mostrar (5 s):** no mapa, a legenda das bases por procedência (oficial, OSM, declarada, estimada) e o popup de uma base com a fonte; ou, no `plano.md`, a tabela "Bases e procedência". **Fala:** "Cada base mostra de onde veio. Hoje a camada oficial é uma lista com fonte; numa implantação real, seria o sistema do próprio órgão, como o Sisfogo, federado pelo Zetaris."

## 2. (0:25–0:55) Os dados pelo Zetaris
**[ZETARIS] Tela:** a UI do Zetaris (`http://localhost:3000`). No **Data Explorer**, mostrar o container `fococerto` e as fontes registradas (`fococerto_pg.focos` no Postgres, os CSVs `fococerto_arq.*` no file store, `fococerto.clima` vindo do Open-Meteo). Depois, no SQL editor:
```sql
SELECT * FROM fococerto.ocorrencias_prioridade WHERE regiao='tocantins' AND dia='2026-10-23' ORDER BY prioridade DESC LIMIT 15
```
Mostrar as colunas `c_exposicao` … `c_crescimento` e a `prioridade`. No terminal, o `run` sem `--sample` imprime `Dados: Zetaris`.

**Fala:** "Uma camada no Zetaris federa três tipos de fonte: os focos no Postgres, as cidades, as bases do OSM e a lista oficial de bases (com fonte) em CSV no file store, e o tempo do Open-Meteo numa tabela REST com cache. Quatro views calculam as ocorrências, a exposição e a prioridade, com uma fórmula transparente. É um Zetaris real, no servidor do time: 1.875 focos reais de uma semana, e a view de prioridade devolve as mesmas 698 ocorrências que o cálculo de referência em Python."

**Fala opcional (honestidade, 5 s):** "Escrevemos a integração antes de ter um Zetaris; ao rodar de verdade, tivemos de ajustar o formato da resposta da API, as descrições das tabelas e a porta do Postgres dentro da rede do Zetaris."

**Plano B (se o Zetaris cair na hora):** mostrar `sql/zetaris_views.sql` (a view `ocorrencias_prioridade`) e, no `trace.jsonl` de `output_examples/tocantins-escasso-real/`, o evento `ferramenta`/`consulta` com `fonte: zetaris`, `modo_usado: views` e as 6 consultas SQL. Fala: "Esta é a execução real de 25 de outubro: as seis consultas que o FocoCerto fez às views do Zetaris."

## 3. (0:55–2:00) O raciocínio: Planejador, Crítico e Analista
**Tela:** terminal.
```bash
python -m app.cli run --regiao tocantins --recursos cenarios/tocantins-escasso.yaml   # [ZETARIS] + [NIGHTSHIFT] + H-MEM, sem --sample
# plano B: mostrar output_examples/tocantins-escasso-real/ (execução real de 25/10); plano C: o mesmo comando com --sample
```
**Mostrar:** as linhas de progresso e o resultado. **Resultado da execução real de 25/10** (`output_examples/tocantins-escasso-real/`): 2 rodadas e 4 chamadas ao Nemotron (Planejador, Crítico, Planejador, Crítico). Na rodada 1 o Crítico **rejeita** o plano e pede 3 trocas `troca_recurso_local`: `palmas-a1` para Santa Tereza do Tocantins (ganho de 0,6 h), `dianopolis-t1` para Dianópolis (22.424 hab., ETA 0,16 h em vez de 2,51 h) e `paraiso-t1` para Porto Nacional (53.316 hab.). Na rodada 2 o Planejador adota as trocas e o Crítico **aprova**. Final: 6 designações e 9 escalações obrigatórias ("solicitar apoio externo"), entre elas Fortaleza do Tabocão (29.357 hab.). Se a execução gravada der outro resultado, mostrar o que sair, sem trocar por estes números. Neste cenário o Crítico **não** chama o Analista; o Analista aparece no cenário abaixo.

**[NIGHTSHIFT] Mostrar no log** as linhas `llm_call` com `routed_model` e `receipt`:
```bash
grep llm_call logs/<execucao>.jsonl | python -c "import sys,json;[print(j['agente'],j['modelo'],j['routed_model'],j['receipt'],j['latencia_s']) for j in map(json.loads,sys.stdin)]"
```
Na execução de 25/10 saem 4 linhas com `nvidia/nemotron-3-ultra-550b-a55b` e recibos `rcpt_req_ffku2qfy`, `rcpt_req_66s1etud`, `rcpt_req_qumkyxqs`, `rcpt_req_5gjg112f` (6,9 a 33,5 s cada). Fala: "Cada agente fala com o Nemotron pelo Nightshift, e o log registra qual modelo respondeu, com o recibo assinado." **É o trecho que prova a requisição real pelo Nightshift: não cortar.** Plano B: o mesmo `grep` no `trace.jsonl` da execução de 25/10.

**Fala:** "O alocador guloso propõe. As ferramentas aplicam as regras rígidas e conferem cada fato citado. O Crítico julga o que fica em zona cinzenta: aqui ele recusou a primeira proposta, porque três recursos chegavam mais rápido a ocorrências com mais gente, e o Planejador refez o plano. Nove ocorrências com população ficaram sem recurso, e o sistema escala para o coordenador em vez de esconder o problema, com a sugestão de pedir apoio externo." (Desde 25/10, toda ocorrência com população que termina sem recurso é escalada com "solicitar apoio externo", mesmo se o Crítico aprovar.)

**Fala curta (ponta a ponta):** "Nesta execução tudo é real: os dados vêm das views do Zetaris, as decisões do Nemotron pelo Nightshift, e a memória do serviço H-MEM. Só a quantidade de equipes é simulada."

**O Analista (≈20 s):** rodar o cenário em que o Crítico tem uma pergunta em aberto (o mesmo de `output_examples/tocantins-parana-analista/`, período 24/10):
```bash
python -m app.cli run --sample --regiao tocantins --recursos input_examples/tocantins-parana-analista.yaml
```
Mostrar as linhas `analista: consulta` (7 consultas: histórico, dia/noite, FRP, persistência, TI/UC, tempo, exposição) e, no `plano.md`, a seção "Pareceres do Analista". **Resultado real no modo offline:** "`cel_-124_-479`: **indeterminado** (confiança: **baixa**)", com evidências dos dois lados: FRP baixo (6,7 MW por foco) e longe de TI/UC apontam para queima agrícola, mas a ocorrência está crescendo em relação ao período anterior; escore +0,5 com limiar ±1,5 (heurística não calibrada). No ciclo de revisão: "Analista inconclusivo sobre cel_-124_-479 (indeterminado, baixa): designação mantida por precaução", e o Crítico escala as 3 ocorrências com população que ficaram sem recurso (Juarina, Santa Maria do Tocantins, Centenário).

Fala: "O Crítico pergunta ao Analista se essa ocorrência sem população perto é queima agrícola recorrente. O Analista faz 7 consultas e responde com incerteza declarada: não dá para saber, os sinais apontam para os dois lados. Com confiança baixa, o Crítico não tira o recurso de lá, mantém por precaução, e escala para o coordenador as ocorrências com população que ficaram sem equipe." **Não** dizer que o Analista concluiu "queima agrícola": no exemplo atual ele não conclui. Se gravar no modo LLM, mostrar o parecer que sair.

**No modo offline, dizer:** "Aqui os agentes rodam em modo determinístico, sem LLM; no modo LLM, as mesmas decisões passam pelo Nemotron."

## 4. (2:00–2:50) A memória: a nota "estrada para São Félix alagada" muda o plano
**Tela:** terminal + `plano.md` (seções "Ordem de recursos" e "Memórias que influenciaram o plano").
```bash
python -m app.cli nota --regiao tocantins --periodo 2026-10-23 "estrada para São Félix alagada"
python -m app.cli run  --regiao tocantins --recursos cenarios/tocantins-escasso.yaml [--sample]
```
**Resultado real (sample):** `saofelix-t1` (brigada Prevfogo/Ibama de São Félix do Tocantins) deixa de ir por terra a `cel_-96_-468` (Lizarda) e fica em reserva; a ocorrência é escalada (5 designações, 10 escaladas). No ciclo de revisão: "Exceção aceita: memória tocantins:mem-1 (…) vale sobre a regra da base mais próxima".

```bash
python -m app.cli nota --regiao tocantins --periodo 2026-10-24 "estrada para São Félix liberada"
#  -> "Substitui a memória tocantins:mem-1."
python -m app.cli run  --regiao tocantins --recursos cenarios/tocantins-escasso.yaml [--sample]
```
**Resultado real:** `saofelix-t1` volta para Lizarda (6 designações, 9 escaladas); o plano mostra "`tocantins:mem-2` … substitui `tocantins:mem-1`".

**Fala:** "A nota do coordenador vira uma memória no H-MEM, o engine da Meterless. O Crítico decide se a exceção vale. Quando chega a nota contrária, o H-MEM detecta o conflito e marca a antiga como substituída, sem apagar nada. A memória é separada por região."

**Prova (5 s):** `cd services/hmem && npm test` terminando em `13/13 checks passed`.

**Atenção:** usar as frases "estrada para São Félix alagada" e "estrada para São Félix liberada". Conferido em 25/10 no `MemoriaLocal`: "liberada" substitui tanto "alagada" quanto "alagada, sem acesso" (`supersedes = tocantins:mem-1`). Rodar uma vez antes de gravar.

**Aprendizado ao longo de 3 períodos:** mostrar com `scripts/demo_3_periodos.sh` (21 → 22 → 23/10). No dia 22, células que ficaram sem recurso no dia 21 e cresceram viram memória derivada e mudam o plano (o script imprime as designações marcadas "[muda por causa da memória]"; anotar quais são ao ensaiar, porque o cenário mudou com as bases em camadas). No dia 23, a nota "liberada" substitui a "alagada" e o recurso de São Félix volta.

## 5. (2:50–3:30) A prova: ablação A/B/C/D
**Tela:** a tabela de `eval/RELATORIO.md`.

**Fala:** "Para saber se o Crítico e a memória decidem melhor, comparamos quatro variantes em 12 cenários com dados reais, com gabaritos escritos e commitados antes de rodar: A, só o alocador; B, Planejador com o checador; C, o sistema completo; D, o completo sem memória. Medimos acerto nos gabaritos, alarmes falsos, o tempo médio de espera da população exposta e a variância em 3 execuções."

**Tela:** a tabela do modo LLM (Nemotron pelo Nightshift, 25/10: 144 execuções, 450 chamadas, 0 fallbacks): A 22,2%, B 65,4%, C 75,9%, D 73,6%.

**Fala:** "Com o Nemotron, o sistema completo acerta 76% das checagens contra 22% do alocador simples. O Nemotron escreveu uns 50 fatos errados, cidade, distância ou população, e o checador pegou todos: nenhum plano final chegou ao coordenador com citação falsa. O Crítico pega o que nenhuma ferramenta pega, como uma tendência inventada. E dizemos o que não deu certo: no modo LLM, a memória quase não muda o acerto, a diferença fica dentro da variação entre execuções, e as escalações vieram de impasse, não de decisão; estamos corrigindo isso."

**Regra:** só mostrar números que estejam no `RELATORIO.md`. Não dizer que o problema das escalações por impasse já foi corrigido, a não ser que a ablação tenha sido rodada de novo e o `RELATORIO.md` mostre isso.

## 6. (3:30–3:45) Saída para o coordenador
**Tela:** **[WEB]** se a tela existir, mostrar nela o plano (escalações, ordem de recursos com a procedência da base, justificativas com evidências) e o botão de aprovar, que chama `POST /api/aprovar`. **Plano B:** `plano.md` rolando (justificativas com evidências `pop:`, `eta:`, `dist:`) e o mapa, e o comando abaixo.
```bash
python -m app.cli aprovar --regiao tocantins --periodo 2026-10-23
```
**Fala:** "Nada é despachado sem aprovação. Cada designação traz a evidência, e o log mostra cada passo."

## 7. (3:45–4:00) Limitações e próximos passos
**Fala:** "Limitações: detecção não é incêndio; a exposição usa a população do município e fica superestimada; a distância é em linha reta com um fator; não validamos com operadores. Próximos passos: validar com o Corpo de Bombeiros do Tocantins e o PrevFogo, ligar a camada oficial de bases ao sistema do órgão pelo Zetaris, rotas reais, e as áreas protegidas."

---

## O que ficou de fora da seção 14 original (e por quê)
| Item da especificação | Situação |
|---|---|
| Tela web (front-end) | **[WEB]**: só a API existe hoje (`app/api.py`, contrato em `web/README.md`). Mostrar só se a tela existir e funcionar na hora de gravar. |
| "Mesmo código, outra região" (Península Ibérica) | Só existe `config/regioes/iberia.yaml`; não há dados em cache nem execução. Não mostrar, a não ser que alguém rode de verdade antes de gravar. |
| SQL federada ao vivo no Zetaris | **[ZETARIS]**: funciona (Zetaris 2.4 no servidor do time, 25/10). Mostrar a UI em `localhost:3000` (Data Explorer + consulta à `fococerto.ocorrencias_prioridade`). Plano B: o trace da execução real de 25/10. |
| Nemotron respondendo, com `routed_model` | **[NIGHTSHIFT]**: obrigatório pelas regras ("one real request passing through Nightshift"). Já funciona (25/10); basta o Nightshift estar no ar na hora de gravar. Mostrar a linha `llm_call` com `routed_model` e o `receipt` (ex.: `rcpt_req_…`). |
