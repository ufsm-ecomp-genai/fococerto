# FocoCerto: contrato da API para o front-end

Este documento é para quem vai escrever a tela. Ele cobre os conceitos, cada endpoint com request e response
**reais** (tirados de `output_examples/` e de uma execução em sample mode) e as regras de interface que não são
negociáveis.

A API é um envelope fino sobre a CLI (`app/cli.py`). Ela não decide nada sozinha: lê os planos que a CLI grava
em `out/<regiao>/<periodo>/plano.json`, roda o mesmo ciclo da CLI num job e grava notas e aprovações pelos mesmos
caminhos.

## Subir a API

```bash
.venv/bin/python -m pip install -e .            # inclui fastapi e uvicorn
.venv/bin/uvicorn app.api:app --port 8000       # http://localhost:8000/docs tem o OpenAPI interativo
```

- **CORS:** liberado para `http://localhost:<qualquer porta>` e `http://127.0.0.1:<porta>` (o Vite roda em
  5173). Para outra origem, use a variável `FOCOCERTO_CORS_ORIGENS` com uma regex.
- **Front compilado:** se `web/dist/` existir quando a API sobe, ela serve os arquivos em `/` (o `index.html`
  na raiz). As rotas da API ficam todas em `/api/...`.
- **Sem rede e sem chaves:** os endpoints de leitura funcionam sempre. Para rodar um período sem Zetaris, Nightshift
  ou H-MEM, mande `"sample": true` no `POST /api/run`.
- **Comece por `GET /api/exemplos`:** são planos completos, já gerados, e servem para desenhar a tela sem rodar
  nada.
- Pasta das saídas: `out/` (ou `FOCOCERTO_SAIDA`). O `.env` da raiz é lido quando o servidor sobe, igual à CLI.
- `web/api.yaml` diz onde estão os exemplos e de quais pastas o `POST /api/run` aceita cenários
  (sobrescreva com `FOCOCERTO_EXEMPLOS` e `FOCOCERTO_PASTAS_CENARIOS`).

## Conceitos

| Conceito | O que é | Onde aparece no JSON |
|---|---|---|
| **Período** | Um dia UTC (`AAAA-MM-DD`). O sistema decide uma vez por período. O último dia do cache pode estar incompleto. | `meta.periodo`, `plano.periodo` |
| **Ocorrência** | Um incêndio provável: os focos do satélite (NASA FIRMS VIIRS) agrupados numa célula de ~0,1° (`cel_<lat×10>_<lon×10>`). Traz intensidade (FRP), população no raio, localidades próximas, tempo, a `prioridade` (0 a 1) e os `componentes` que a compõem. | `ocorrencias[]` |
| **Base** | De onde saem os recursos: quartel, brigada ou base declarada pelo coordenador. Toda base tem `fonte`; as que não foram verificadas vêm com `simulada: true`. Algumas trazem `confianca` (ex.: `"oficial"`). | `bases[]` |
| **Recurso** | Uma equipe ou aeronave (`tipo`: `terrestre` ou `aereo`) ligada a uma base. `capacidade` = quantas ocorrências atende ao mesmo tempo. Os recursos são informação do coordenador e, na demo, são **simulados**. | `recursos[]` |
| **Designação** | A decisão: recurso → ocorrência, com `ordem`, `eta_h` (chegada estimada em horas), `justificativa` em texto e `evidencias` (ids que permitem conferir a justificativa contra os dados). | `plano.designacoes[]` |
| **Reserva** | Recursos disponíveis que ficaram sem designação de propósito. | `plano.reserva[]` |
| **Não atendidas** | Ocorrências da lista do período sem recurso. | `plano.nao_atendidas[]` |
| **Escalação** | O sistema devolve a decisão ao coordenador: tipicamente população exposta sem recurso viável ("solicitar apoio externo"), ou impasse entre Planejador e Crítico. `ocorrencia_id` pode vir `null` (escalação geral, por exemplo um impasse); o `motivo` é texto livre. | `escalacoes[]`, `status == "escala"` |
| **Parecer** | Resposta do agente Analista a uma pergunta sobre uma ocorrência (ex.: queima agrícola ou incêndio em vegetação?), com `conclusao`, `confianca` (`baixa`/`media`/`alta`), `evidencias` e as `consultas` que fez. | `pareceres[]` |
| **Memória** | O que o sistema lembra entre períodos (H-MEM): `nota` do coordenador ou `derivada` dos dados. Tem `fonte`, `confianca` e pode substituir outra (`supersedes`). | `memorias_usadas[]` |
| **Rodada / histórico** | Cada proposta do Planejador e o que o checador e o Crítico disseram dela: `violacoes` (regras), `veredicto` (`aprova`/`rejeita`/`escala`) e a contra-proposta. | `historico[]`, `rodadas` |
| **Status** | `aprova` (o sistema aprovou o próprio plano) ou `escala` (precisa de decisão humana). **Nos dois casos a aprovação humana continua pendente**: `meta.aprovacao_humana`. | `status` |

## Endpoints

Erros vêm sempre como `{"detail": "<mensagem em português, pronta para mostrar>"}`, com 400 (pedido inválido),
404 (não existe) ou 422 (corpo fora do formato; o `detail` é a lista de erros do FastAPI).

### `GET /api/saude`
```json
{"ok": true, "saida": "/…/fococerto/out", "exemplos": true, "web_dist": false}
```

### `GET /api/regioes`
Regiões configuradas em `config/regioes/`. Use `bbox` (`[lat_min, lat_max, lon_min, lon_max]`) para enquadrar o
mapa e `idioma` para os textos.
```json
[
  {"nome": "iberia", "idioma": "es-ES", "bbox": [36.0, 44.0, -10.0, 4.0], "eta_max_h": 3.0,
   "raio_exposicao_km": 15.0, "tem_cache": false, "planos_salvos": 0},
  {"nome": "tocantins", "idioma": "pt-BR", "bbox": [-13.0, -8.0, -49.5, -45.5], "eta_max_h": 6.0,
   "raio_exposicao_km": 15.0, "tem_cache": true, "planos_salvos": 1}
]
```

### `GET /api/periodos?regiao=tocantins`
Dias com dados no cache e dias que já têm plano salvo. Região sem `config/regioes/<r>.yaml` → 404. Região sem cache
→ `periodos_cache: []` e `erro_cache` com a explicação.
```json
{"regiao": "tocantins",
 "periodos_cache": ["2026-10-17", "2026-10-18", "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24"],
 "periodos_com_plano": ["2026-10-23"], "erro_cache": null}
```

### `GET /api/cenarios`
Arquivos de recursos que o `POST /api/run` aceita (as duas primeiras pastas de `web/api.yaml`: `cenarios/` e
`input_examples/`).
```json
[{"caminho": "cenarios/tocantins-escasso.yaml", "nome": "tocantins-escasso", "regiao": "tocantins",
  "periodo": "2026-10-23", "simulado": true, "recursos": 6, "reserva": 0, "notas": []}]
```

### `GET /api/exemplos` e `GET /api/exemplos/{nome}`
A lista traz o cabeçalho de cada exemplo. O detalhe devolve o `plano.json` inteiro (mesmo formato do
`GET /api/plano`).
```json
[{"nome": "tocantins-escasso", "regiao": "tocantins", "periodo": "2026-10-23", "modo": "offline", "idioma": "pt-BR",
  "simulado": true, "gerado_em": "2026-10-25T20:12:03.215163+00:00", "aprovacao_humana": "pendente",
  "status": "escala", "designacoes": 6, "escalacoes": 9, "ocorrencias": 15, "rodadas": 2, "tem_trace": true}]
```

### `GET /api/exemplos/{nome}/trace?limite=500`
Os eventos do log JSONL do exemplo, um objeto por evento (formato em `docs/CONTRATOS.md`, seção 7). É a
**procedência**: qual agente fez o quê, em que rodada, e, nas chamadas de LLM, qual modelo respondeu. Exemplo real
de uma chamada ao Nemotron (log da ablação no modo LLM):
```json
{"t": "2026-10-25T18:29:01.980755+00:00", "execucao": "fato_errado_populacao_23out__B__r3",
 "regiao": "tocantins", "periodo": "2026-10-23", "agente": "planejador", "evento": "llm_call",
 "dados": {"status": "ok", "tentativas": 1, "json_ok": true},
 "modelo": "nvidia/nemotron-3-ultra-550b-a55b", "routed_model": "nvidia/nemotron-3-ultra-550b-a55b",
 "receipt": "rcpt_req_3s3g0aaw", "tokens": 15196, "latencia_s": 28.548}
```

### `GET /api/plano/{regiao}/{periodo}`
O `plano.json` do período. Se não existe: 404 com
`"Não há plano para tocantins/2026-10-19 (esperado em out/tocantins/2026-10-19/plano.json). Rode POST /api/run ou: python -m app.cli run …"`.

Estrutura (trechos reais de `output_examples/tocantins-folgado/plano.json`; listas encurtadas):
```json
{
  "meta": {"versao_formato": 1, "regiao": "tocantins", "periodo": "2026-10-23", "idioma": "pt-BR",
           "modo": "offline", "simulado": true, "arquivo_cenario": "input_examples/tocantins-folgado.yaml",
           "gerado_em": "2026-10-25T20:12:07.510051+00:00", "aprovacao_humana": "pendente"},
  "plano": {
    "periodo": "2026-10-23", "regiao": "tocantins", "rodada": 2,
    "designacoes": [
      {"recurso_id": "palmas-a1", "ocorrencia_id": "cel_-91_-474", "ordem": 1, "eta_h": 0.97,
       "justificativa": "Prioridade 0.69; 2135 habitantes no raio; Centenário a 8.7 km; 2 focos, FRP somado 398 MW; palmas-a1 (aereo) chega em ETA 1.0 h saindo de CBMTO 1º BBM Palmas.",
       "evidencias": ["focos:2", "eta:0.97", "pop:2135", "dist:Centenário:8.7", "base:osm_n5067657890"]}
    ],
    "reserva": ["palmas-t2", "palmas-t3", "paraiso-t1"],
    "nao_atendidas": ["cel_-122_-464", "cel_-121_-466"],
    "resumo": "[escala] Adota a contra-proposta do Crítico. … 13 designações, 2 ocorrências sem recurso, 3 recursos em reserva."
  },
  "status": "escala",
  "ocorrencias": [
    {"id": "cel_-91_-474", "lat": -9.02206, "lon": -47.30267, "n_focos": 2, "frp_soma": 398.28, "frp_max": 199.14,
     "primeiro": "2026-10-23T16:37:00", "ultimo": "2026-10-23T16:37:00", "periodos_seguidos": 1, "status": "nova",
     "pop_raio": 2135, "dist_ti_uc_km": null, "vpd_kpa": 4.03, "vento_kmh": 19.2, "prioridade": 0.6855,
     "componentes": {"exposicao": 0.6659, "intensidade": 0.9799, "tempo": 0.5373, "persistencia": 0.0, "crescimento": 1.0},
     "localidades": [{"nome": "Centenário", "pop": 2135, "dist_km": 8.7}]}
  ],
  "bases": [
    {"id": "osm_n5067657890", "nome": "CBMTO 1º BBM Palmas", "lat": -10.206127, "lon": -48.343395,
     "fonte": "CBMTO — https://conexaoto.com.br/… (2023); coordenada: quartel mapeado no OpenStreetMap (node/5067657890); …",
     "simulada": false, "confianca": "oficial"}
  ],
  "recursos": [{"id": "palmas-t1", "base_id": "osm_n5067657890", "tipo": "terrestre", "capacidade": 1, "disponivel": true}],
  "escalacoes": [
    {"ocorrencia_id": "cel_-121_-466",
     "motivo": "Escalação: cel_-121_-466 tem 4295 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.",
     "sugestao": "solicitar apoio externo"}
  ],
  "pareceres": [],
  "memorias_usadas": [],
  "historico": [
    {"rodada": 1, "plano": {"…": "mesmo formato de plano"},
     "violacoes": [
       {"regra": "troca_recurso_local", "ocorrencia_id": "cel_-121_-466", "recurso_id": "dianopolis-t1",
        "evidencia": {"pop_raio": 4295, "de_ocorrencia": "cel_-122_-464", "eta_atual_h": 2.51, "eta_para_exposta_h": 1.78},
        "sugestao": "trocar: dianopolis-t1 sai de cel_-122_-464 (4295 hab., ETA 2.51 h) e vai para cel_-121_-466 …",
        "rigida": false}],
     "veredicto": {"decisao": "rejeita",
                   "motivos": ["Troca de recurso local: dianopolis-t1 chega a cel_-117_-469 (22424 hab.) em 0.16 h, mas foi para cel_-122_-464 (4295 hab.) a 2.51 h; troco e cel_-122_-464 fica sem recurso (escalação)."],
                   "contra_proposta": {"…": "plano"}, "pedir_analista": []},
     "origem_critico": "offline_deterministico"}
  ],
  "rodadas": 2,
  "log_path": "output_examples/tocantins-folgado/trace.jsonl"
}
```

Um parecer real (`output_examples/tocantins-parana-analista`):
```json
{"ocorrencia_id": "cel_-124_-479",
 "pergunta": "Esta ocorrência é provavelmente queima agrícola ou de manejo recorrente, ou incêndio em vegetação nativa?",
 "conclusao": "indeterminado", "confianca": "baixa",
 "evidencias": ["agrícola: FRP baixo (6.7 MW por foco)", "vegetação: ocorrência crescendo em relação ao período anterior",
                "agrícola: longe de TI/UC (sem TI/UC no raio)",
                "escore agrícola−vegetação = +0.5 (limiar ±1,5; heurística não calibrada)"],
 "consultas": ["historico_celula(cel_-124_-479, dias=7)", "padrao_dia_noite(cel_-124_-479, dias=7)", "…"]}
```

Uma memória real (`output_examples/tocantins-escasso-com-nota`):
```json
{"id": "tocantins:mem-1", "regiao": "tocantins", "texto": "estrada para São Félix alagada, sem acesso",
 "tipo": "nota", "fonte": "coordenador:enzo", "confianca": 1.0, "supersedes": null,
 "criada_em": "2026-10-25T20:12:08.359000Z"}
```

Campos que podem faltar ou vir `null`: `ocorrencia.status` (célula antiga sem par no dia anterior),
`dist_ti_uc_km` (TI/UC ainda não ingeridos), `vpd_kpa`/`vento_kmh`, `escalacao.ocorrencia_id`,
`escalacao.sugestao`, `base.confianca`, `base.fonte`, `veredicto.contra_proposta`. Trate todos como opcionais.

### `POST /api/run` → `202`
Roda um período em segundo plano, com o mesmo ciclo da CLI (`python -m app.cli run`). Uma execução por vez: se já
houver uma rodando, o job fica `na_fila`. No modo LLM um período leva minutos (cada chamada ao modelo leva ~30 s);
no sample mode, 1 a 2 s.

```json
// request
{"regiao": "tocantins", "periodo": "2026-10-23", "recursos": "cenarios/tocantins-medio.yaml", "sample": true,
 "idioma": "en"}
// response 202
{"job_id": "61db0e96f557", "status": "rodando", "url": "/api/jobs/61db0e96f557"}
```
- `recursos`: caminho relativo de um `.yaml` numa das `pastas_cenarios` de `web/api.yaml` (`cenarios/`,
  `input_examples/`, `eval/cenarios/`, `eval/cenarios_2periodos/`; lista em `GET /api/cenarios`). Outro caminho → 400; arquivo inexistente → 404.
- `periodo` é opcional (padrão: o do cenário). `sample` é opcional (padrão `false`, como a CLI: sem
  `ZETARIS_API_KEY` usa o cache, sem `HMEM_URL` usa a memória local, e o LLM segue `LLM_PROVIDER`).
- `idioma` é opcional: `"pt-BR"` ou `"en"` (aceita `"pt"`, `"en-US"`...; vazio ou `null` = padrão). É o idioma do
  plano **inteiro**: rótulos do `plano.md`/`mapa.html` e o conteúdo (justificativas, motivos do Crítico,
  escalações, pareceres, resumo; no modo LLM o modelo também escreve nesse idioma). Padrão: `FOCOCERTO_IDIOMA` do
  servidor, senão o `idioma` da região. Idioma não suportado → 400. O idioma efetivo volta em `meta.idioma` do
  plano e em `resultado.idioma` do job. A tela pode ter um seletor PT/EN que manda este campo.
- O plano é salvo em `out/<regiao>/<periodo>/` e **substitui** o anterior do mesmo período (rodar o mesmo
  período em outro idioma também substitui).

### `GET /api/jobs/{id}` (e `GET /api/jobs` para a lista)
Faça polling a cada 1 a 2 s até `status` ser `concluido` ou `erro`. `progresso` são as mesmas mensagens que a CLI
mostra no terminal, em ordem (mostre a última como "o que está acontecendo agora"). Não há porcentagem: o número
de rodadas não é conhecido antes. Os jobs ficam só na memória do servidor (reiniciou, sumiram).
```json
{
  "id": "61db0e96f557", "status": "concluido",
  "pedido": {"regiao": "tocantins", "periodo": "2026-10-23", "recursos": "cenarios/tocantins-medio.yaml", "sample": true,
             "idioma": null},
  "criado_em": "2026-10-25T20:12:24+00:00", "iniciado_em": "2026-10-25T20:12:24+00:00", "terminado_em": "2026-10-25T20:12:26+00:00",
  "progresso": [
    {"t": "2026-10-25T20:12:24+00:00", "msg": "Verificando módulos..."},
    {"t": "2026-10-25T20:12:25+00:00", "msg": "AVISO: recursos SIMULADOS (tocantins-medio.yaml)"},
    {"t": "2026-10-25T20:12:25+00:00", "msg": "Região tocantins, período 2026-10-23, 10 recursos, modo offline, idioma pt-BR"},
    {"t": "2026-10-25T20:12:26+00:00", "msg": "  sistema: fim"}
  ],
  "erro": null,
  "resultado": {"regiao": "tocantins", "periodo": "2026-10-23", "modo": "offline", "idioma": "pt-BR", "simulado": true,
                "gerado_em": "2026-10-25T20:12:26.046871+00:00", "aprovacao_humana": "pendente", "status": "escala",
                "designacoes": 8, "escalacoes": 7, "ocorrencias": 15, "rodadas": 2,
                "plano_url": "/api/plano/tocantins/2026-10-23", "duracao_s": 1.3}
}
```
Com erro: `"status": "erro"` e `"erro"` com a mensagem da CLI (ex.: `"O cenário … é da região 'tocantins', mas
--regiao é 'iberia'."`). Erros inesperados trazem também `traceback`.

### `POST /api/nota`
Registra uma observação do coordenador no banco de decisões e no H-MEM (igual a `python -m app.cli nota`). Ela
vale a partir do próximo `run`. `periodo` é opcional (padrão: hoje).
```json
// request
{"regiao": "tocantins", "periodo": "2026-10-23", "texto": "estrada para São Félix alagada", "autor": "coord", "sample": true}
// response 200
{"ok": true, "regiao": "tocantins", "periodo": "2026-10-23", "memoria_id": "tocantins:mem-1",
 "mensagens": ["Nota registrada (tocantins, 2026-10-23) com memória tocantins:mem-1."]}
```
Texto ou autor vazio → 400.

### `POST /api/aprovar`
Grava as designações do plano salvo do período como decisões aprovadas (igual a `python -m app.cli aprovar`). A
aprovação **não** resolve as escalações: a mensagem avisa.
```json
// request
{"regiao": "tocantins", "periodo": "2026-10-23", "autor": "coord", "sample": true}
// response 200
{"ok": true, "regiao": "tocantins", "periodo": "2026-10-23", "aprovado_por": "coord",
 "mensagens": ["Plano tocantins/2026-10-23 aprovado por coord.",
               "Atenção: o plano tinha 7 escalação(ões); a aprovação não as resolve."]}
// sem plano salvo → 404
{"detail": "Não há plano salvo em …/out/tocantins/2026-10-19/plano.json. Rode antes: python -m app.cli run --regiao tocantins --periodo 2026-10-19 --recursos cenarios/<cenario>.yaml"}
```

## Regras da tela (não negociáveis)

1. **Nada fixo na tela.** Região, período, ids, nomes de bases e localidades, idioma, limites (`eta_max_h`) e o
   enquadramento do mapa (`bbox`) vêm da API. Nenhum `if regiao == "tocantins"`, nenhuma lista de cidades no
   código do front, nenhum plano de demonstração embutido: para a demo, use `GET /api/exemplos`.
2. **Fundo de mapa Esri World Street Map**, o mesmo do `mapa.html`:
   `https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}`, com a
   atribuição `Tiles © Esri — Esri, HERE, Garmin, USGS, © OpenStreetMap contributors`. Não use os tiles do
   OpenStreetMap (bloqueiam uso fora do site deles) nem os do CARTO (exigem chave).
3. **O mais importante primeiro.** O coordenador está sob pressão: **escalações em destaque, no topo**, depois a
   lista de designações em `ordem`, com ETA e justificativa. `status == "escala"` precisa ser impossível de não ver.
4. **Mostrar a incerteza, não esconder:**
   - `eta_h` é uma **estimativa** (distância × tortuosidade ÷ velocidade, ou linha reta para aeronave), não rota real;
   - `pop_raio` soma a população do GeoNames dentro do raio e muitas vezes é a do **município inteiro**:
     mostre como "até N habitantes no raio", não como pessoas em risco;
   - o `parecer.confianca` (`baixa`/`media`/`alta`) aparece junto da conclusão, e `indeterminado` é uma resposta
     válida;
   - a `prioridade` é um índice (0 a 1) com `componentes`: mostre a decomposição, não só o número;
   - o último dia do cache pode estar incompleto; ocorrência com `status: null` não tem par no dia anterior.
5. **Mostrar a procedência:**
   - `meta.simulado` e `base.simulada` → selo "simulado" visível (recursos e bases da demo são simulados);
   - `base.fonte` (e `confianca`, quando houver) no popup da base;
   - as `evidencias` de cada designação, para o coordenador conferir a justificativa;
   - em cada memória usada: `tipo` (nota do coordenador ou derivada dos dados), `fonte`, `confianca` e, se
     substitui outra, `supersedes`;
   - `meta.modo` (`offline` = agentes determinísticos; `llm` = modelo via Nightshift) e, no trace, `modelo`,
     `routed_model` e `receipt` de cada chamada de LLM;
   - o `historico` (o que o Crítico rejeitou e por quê) acessível, mesmo que recolhido.
6. **A decisão é humana.** `meta.aprovacao_humana` começa `pendente`. O botão de aprovar chama `POST /api/aprovar`;
   escalações continuam abertas depois da aprovação. Notas (`POST /api/nota`) só valem a partir do próximo `run`:
   diga isso na tela.
7. **Português primeiro, fácil de traduzir:** use `meta.idioma` e mantenha os textos da interface num arquivo de
   tradução. Os textos que vêm da API (`justificativa`, `motivo`, `resumo`, pareceres) já vêm no idioma do plano
   (`meta.idioma`) e são mostrados como vieram. Os valores enumerados do JSON **não** são traduzidos pela API
   (`status`, `decisao`, `conclusao`, `confianca`, `tipo`, `Ocorrencia.status`, `regra`): traduza-os na tela.
   Exemplo em inglês: `output_examples/tocantins-escasso-en/` (`GET /api/exemplos/tocantins-escasso-en`).
