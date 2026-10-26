# FocoCerto: contrato da API para o front-end

## Comece por aqui

| Quero... | Leia / use |
|---|---|
| Começar a tela **hoje, sem rodar o back-end** | [`TUTORIAL-MOCKS.md`](TUTORIAL-MOCKS.md) (setup em ~10 min, primeiro componente pronto) |
| Ver quais dados mock existem e de qual endpoint cada um vem | [`mocks/README.md`](mocks/README.md) |
| Saber o formato exato de cada endpoint | este documento (abaixo) |

Pasta `web/`:
```
web/
├── README.md            este contrato
├── TUTORIAL-MOCKS.md    passo a passo para começar com os mocks
├── mocks/               respostas REAIS da API (sample mode), para desenvolver sem back-end
├── api.yaml             configuração da API (pastas de exemplos e de cenários)
├── app/                 o app React + Vite (criado pelo tutorial)
└── dist/                o build do app (npm run build); a API serve esta pasta em "/"
```
As duas telas: **"Recursos do dia"** (montar bases, equipes, reserva e notas → gerar plano) e **plano** (escalações,
ordem de recursos, mapa, justificativas, "como chegamos aqui"). A versão final e o vídeo usam a API, nunca os mocks.

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
- Cenários montados na tela e salvos (`POST /api/cenarios`) vão para `FOCOCERTO_CENARIOS_DIR` (padrão
  `data/estado/cenarios/`, fora do git). Os cenários do repositório (`cenarios/`, `input_examples/`) nunca são
  sobrescritos.

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

### `GET /api/bases?regiao=tocantins[&sample=true]`
Bases **conhecidas** da região: camadas `oficial`, `osm` e `estimada` (`docs/CONTRATOS.md` §16), já fundidas, do
mesmo repositório que o `run` usaria (cache local com `sample=true` ou sem `ZETARIS_API_KEY`; senão Zetaris). Vem
também `periodos` (dias com dados; `null` se o repositório não informa). Nas bases da lista oficial vêm `orgao`,
`fonte_url`, `data_fonte` e `coordenada` (de onde veio a coordenada). Região sem `config/regioes/<r>.yaml` → 404;
região sem dados no cache → 404 com a explicação; Zetaris fora do ar → 503. A resposta fica 5 min em memória.
```json
{"regiao": "tocantins", "repositorio": "RepositorioCache",
 "periodos": ["2026-10-17", "2026-10-18", "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24"],
 "bases": [
  {"id": "cbmto_paraiso", "nome": "CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins", "lat": -10.17611, "lon": -48.86667,
   "confianca": "oficial",
   "fonte": "CBMTO — https://conexaoto.com.br/2023/01/27/companhia-de-bombeiros-em-paraiso-… (2023); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado",
   "simulada": false, "orgao": "CBMTO", "fonte_url": "https://conexaoto.com.br/2023/01/27/companhia-de-bombeiros-em-paraiso-…",
   "data_fonte": "2023", "coordenada": "sede do município (GeoNames); endereço do quartel não georreferenciado"},
  {"id": "osm_n3165869368", "nome": "Bombeiros (perto de Porangatu, 1 km)", "lat": -13.445225, "lon": -49.136863,
   "confianca": "osm", "fonte": "OpenStreetMap node/3165869368", "simulada": false}
 ]}
```
(Tocantins: 16 bases, das camadas `oficial` e `osm`.)

### `GET /api/cenarios`
Cenários do repositório (as duas primeiras pastas de `web/api.yaml`, `origem: "repositorio"`, com `caminho`,
aceito em `recursos` no `POST /api/run`) e os salvos pela tela (`origem: "salvo"`, `caminho: null`, com
`salvo_em`). Para usar um salvo, carregue com `GET /api/cenarios/{nome}` e mande o objeto em `cenario`.
```json
[{"caminho": "cenarios/tocantins-medio.yaml", "nome": "tocantins-medio", "origem": "repositorio", "regiao": "tocantins",
  "periodo": "2026-10-23", "simulado": true, "recursos": 10, "bases_declaradas": 0, "reserva": 1, "notas": []},
 {"caminho": null, "nome": "meu-dia-23", "origem": "salvo", "regiao": "tocantins", "periodo": "2026-10-23",
  "simulado": true, "recursos": 4, "bases_declaradas": 1, "reserva": 1, "notas": ["ponte do rio Sono interditada"],
  "salvo_em": "2026-10-26T18:57:06+00:00"}]
```
O mesmo nome pode aparecer em `cenarios/` e em `input_examples/`; `GET /api/cenarios/{nome}` devolve o de
`cenarios/`.

### `GET /api/cenarios/{nome}`
O cenário inteiro, no formato de `cenarios/*.yaml` (`Cenario`), pronto para preencher a tela. Primeiro procura
nos do repositório, depois nos salvos. Nome com caractere fora de `[A-Za-z0-9_-]` → 400; não existe → 404.
```json
{"nome": "meu-dia-23", "origem": "salvo", "caminho": null,
 "cenario": {"regiao": "tocantins", "periodo": "2026-10-23",
   "recursos": [{"id": "palmas-t1", "base_id": "osm_n5067657890", "tipo": "terrestre", "capacidade": 1, "disponivel": true},
                {"id": "palmas-a1", "base_id": "osm_n5067657890", "tipo": "aereo", "capacidade": 1, "disponivel": true},
                {"id": "gurupi-t1", "base_id": "cbmto_gurupi", "tipo": "terrestre", "capacidade": 1, "disponivel": true},
                {"id": "novoacordo-t1", "base_id": "decl_novo_acordo", "tipo": "terrestre", "capacidade": 1, "disponivel": true}],
   "bases": [{"id": "decl_novo_acordo", "nome": "Brigada municipal de Novo Acordo", "lat": -9.97, "lon": -47.68,
              "fonte": "coordenador (tela)", "simulada": false, "confianca": "declarada"}],
   "reserva": 1, "notas": ["ponte do rio Sono interditada"], "simulado": true}}
```

### `POST /api/cenarios` → `201`
Salva o cenário montado na tela em `FOCOCERTO_CENARIOS_DIR/<nome>.yaml`, depois de passar pela **mesma
validação** do `POST /api/run` (422 com a lista de erros). `sample: true` valida as bases contra o cache local.
```json
// request
{"nome": "meu-dia-23", "cenario": {"regiao": "tocantins", "periodo": "2026-10-23", "…": "mesmo objeto do POST /api/run"},
 "sample": true}
// response 201
{"ok": true, "nome": "meu-dia-23", "origem": "salvo", "substituido": false, "url": "/api/cenarios/meu-dia-23"}
// nome de um cenário do repositório → 409 (não sobrescreve)
{"detail": "'tocantins-medio' é um cenário do repositório (cenarios/tocantins-medio.yaml) e não pode ser sobrescrito. Escolha outro nome."}
// nome inválido → 400
{"detail": "Nome de cenário inválido: '../x' (use só letras, números, _ ou -; até 64)."}
```
Salvar de novo um nome já salvo **substitui** (`"substituido": true`); peça confirmação na tela.

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
- Mande **um** de dois: `recursos` (caminho) **ou** `cenario` (o objeto inteiro, montado na tela). Nenhum ou
  os dois → 422.
- `recursos`: caminho relativo de um `.yaml` numa das `pastas_cenarios` de `web/api.yaml` (`cenarios/`,
  `input_examples/`, `eval/cenarios/`, `eval/cenarios_2periodos/`; lista em `GET /api/cenarios`). Outro caminho → 400; arquivo inexistente → 404.
- `cenario`: o mesmo formato de `cenarios/*.yaml` (`regiao, periodo, recursos[{id, base_id, tipo, capacidade,
  disponivel}], bases[{id, nome, lat, lon, fonte}]` (declaradas, opcional), `reserva, notas[], simulado`). Não
  vira arquivo: vai direto para o ciclo, e `meta.arquivo_cenario` do plano diz `"cenário da tela (POST /api/run)"`.
  As bases declaradas entram com `confianca: "declarada"`. Validação (422, todos os erros juntos, no formato do
  FastAPI `[{loc, msg, type}]`): `base_id` que não está nas bases conhecidas (`GET /api/bases`) nem nas declaradas,
  id de recurso ou de base repetido, `tipo` fora de `terrestre`/`aereo`, `capacidade` < 1, `reserva` < 0, base
  declarada fora da região (bbox + 1°), período sem dados (`periodo` do pedido ou do cenário), região do cenário
  diferente de `regiao`. Exemplo real (id repetido e base inexistente):
  ```json
  {"detail": [
    {"loc": ["body", "cenario", "recursos", 1, "id"], "msg": "Id de recurso repetido: 'palmas-t1'.", "type": "value_error"},
    {"loc": ["body", "cenario", "recursos", 2, "base_id"], "msg": "A base 'cbmto_xyz' do recurso 'gurupi-t1' não existe: não está nas bases conhecidas de 'tocantins' (GET /api/bases?regiao=tocantins) nem nas declaradas no cenário.", "type": "value_error"}]}
  ```
  `"tipo": "helicoptero"` → `{"type": "literal_error", "loc": ["body", "cenario", "recursos", 0, "tipo"], "msg": "Input should be 'terrestre' or 'aereo'", …}`;
  período sem dados → `"Não há dados de 2026-09-01 para 'tocantins' (dias disponíveis: 2026-10-17 a 2026-10-24; lista em GET /api/periodos?regiao=tocantins)."`.
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

## Tela "Recursos do dia": montar o cenário e gerar o plano

O coordenador monta o dia na tela, sem YAML. Fluxo (cada passo com o endpoint; os exemplos são reais, de uma
execução em sample mode com `TestClient`):

1. **Região e dia.** `GET /api/regioes` (enquadra o mapa pela `bbox`) e `GET /api/periodos?regiao=…` (dias com
   dados). Para começar de um cenário pronto: `GET /api/cenarios` e `GET /api/cenarios/{nome}` (preenche a tela).
2. **Listar as bases.** `GET /api/bases?regiao=tocantins` → quadrados no mapa e lista ao lado, cada base com o
   selo da procedência (`oficial`, `osm`, `estimada`) e, ao abrir, `fonte`, `orgao`, `data_fonte`, `coordenada`.
3. **Adicionar equipes numa base.** O coordenador escolhe a base e diz quantas equipes terrestres e aeronaves
   tem ali. Cada uma vira um item de `recursos`: `{"id": "palmas-t1", "base_id": "osm_n5067657890", "tipo":
   "terrestre", "capacidade": 1, "disponivel": true}`. O id pode ser gerado pela tela (`<base curta>-t<n>` /
   `-a<n>`), mas tem de ser único. Uma equipe que existe mas está fora de serviço vai com `disponivel: false`.
4. **Criar base nova clicando no mapa.** Clique → pede nome (e, opcional, de onde veio a informação) → vira um
   item de `bases`: `{"id": "decl_novo_acordo", "nome": "Brigada municipal de Novo Acordo", "lat": -9.97,
   "lon": -47.68, "fonte": "coordenador (tela)"}`. Ela aparece como **declarada** (cor própria) e recebe
   equipes como as outras. A API recusa base fora da região (bbox + 1°). Se ela ficar a menos de 3 km de uma
   base conhecida, o ciclo funde as duas e a declarada vence (CONTRATOS §16): avise na tela.
5. **Reserva e notas.** `reserva` = quantos recursos manter sem designação (inteiro ≥ 0). `notas` = observações
   do dia (texto livre): o ciclo as lê como notas do coordenador **só neste período** (entram em
   `memorias_usadas` com `fonte: "cenario:<periodo>"`, sem ir ao H-MEM). Para memória que vale nos próximos
   dias, use `POST /api/nota`.
6. **Gerar o plano.** `POST /api/run` com o objeto em `cenario`:
   ```json
   {"regiao": "tocantins", "sample": true, "idioma": "en",
    "cenario": {"regiao": "tocantins", "periodo": "2026-10-23", "simulado": true, "reserva": 1,
                "notas": ["ponte do rio Sono interditada"],
                "bases": [{"id": "decl_novo_acordo", "nome": "Brigada municipal de Novo Acordo", "lat": -9.97,
                           "lon": -47.68, "fonte": "coordenador (tela)"}],
                "recursos": [
                  {"id": "palmas-t1", "base_id": "osm_n5067657890", "tipo": "terrestre", "capacidade": 1, "disponivel": true},
                  {"id": "palmas-a1", "base_id": "osm_n5067657890", "tipo": "aereo", "capacidade": 1, "disponivel": true},
                  {"id": "gurupi-t1", "base_id": "cbmto_gurupi", "tipo": "terrestre", "capacidade": 1, "disponivel": true},
                  {"id": "novoacordo-t1", "base_id": "decl_novo_acordo", "tipo": "terrestre", "capacidade": 1, "disponivel": true}]}}
   // 202
   {"job_id": "21d57e93c71b", "status": "rodando", "url": "/api/jobs/21d57e93c71b"}
   ```
   Um 422 volta com `loc` apontando o item (`["body", "cenario", "recursos", 2, "base_id"]`): destaque a linha
   certa na tela. Opcional: "Salvar cenário" → `POST /api/cenarios` com um nome, para reabrir depois.
7. **Acompanhar o job.** `GET /api/jobs/21d57e93c71b` a cada 1–2 s (trecho real):
   ```json
   {"id": "21d57e93c71b", "status": "concluido",
    "progresso": [{"t": "2026-10-26T18:57:01+00:00", "msg": "Verificando módulos..."},
                  {"t": "2026-10-26T18:57:05+00:00", "msg": "AVISO: recursos SIMULADOS (cenário da tela (POST /api/run))"},
                  {"t": "2026-10-26T18:57:05+00:00", "msg": "Região tocantins, período 2026-10-23, 4 recursos, modo offline, idioma en"},
                  {"t": "2026-10-26T18:57:05+00:00", "msg": "  sistema: fim"}],
    "erro": null,
    "resultado": {"regiao": "tocantins", "periodo": "2026-10-23", "modo": "offline", "idioma": "en", "simulado": true,
                  "aprovacao_humana": "pendente", "status": "escala", "designacoes": 3, "escalacoes": 12,
                  "ocorrencias": 15, "rodadas": 2, "plano_url": "/api/plano/tocantins/2026-10-23", "duracao_s": 3.94}}
   ```
8. **Abrir o plano.** `GET` em `resultado.plano_url`. A base criada na tela volta em `bases[]` com
   `"confianca": "declarada"`; `meta.arquivo_cenario` = `"cenário da tela (POST /api/run)"`. Com só 4 recursos
   o exemplo acima escala 12 ocorrências: é o resultado esperado de poucos recursos, não um erro.

Regras desta tela:
- **Procedência visível em toda base**: selo `oficial`/`osm`/`estimada`/`declarada` e a fonte ao abrir. Base
  `estimada` é sede de município **sem unidade verificada**: diga isso.
- **A base declarada é a do coordenador**: a tela não "corrige" a posição nem a troca por uma base conhecida; a
  procedência dela é a palavra do coordenador.
- **A quantidade de equipes vem do coordenador.** A tela não sugere nem preenche quantidades sozinha (nada de
  "padrão: 2 por base"); começar de um cenário salvo ou do repositório é escolha explícita dele.
- `simulado`: mande `true` quando as quantidades são de demonstração (o plano mostra o selo "simulado") e `false`
  quando o coordenador informa a disponibilidade real do dia. Deixe o controle visível, não escondido.

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
