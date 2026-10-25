# Contratos entre módulos

Este arquivo é do **líder**. Mudanças só por pedido no relatório de um agente. Os tipos em Python ficam em `app/core/models.py` e devem seguir exatamente o que está aqui.

## 1. Estrutura de pastas
```
app/core/        models.py (tipos), config.py (lê .env e YAML de região), logging.py (logger JSONL)
app/data/        repositorio.py: acesso a dados (Zetaris ou cache), insere decisões e notas no Postgres
app/tools/       monitor, checar_regras, checar_citacoes, alocador_simples, consultar
app/llm/         client.py: Nightshift | offline
app/agents/      planejador.py, critico.py, analista.py, grafo.py (LangGraph)
app/memory_client.py   cliente HTTP do serviço H-MEM (+ versão em memória para o sample mode)
app/output/      templates Markdown e JSON, gerador do mapa
app/cli.py       ponto de entrada
services/hmem/   serviço TypeScript do H-MEM
sql/             DDL do Postgres e views do Zetaris
scripts/         ingest_firms.py, ingest_geonames.py, ingest_osm.py, setup_zetaris.py
config/regioes/  <regiao>.yaml
cenarios/        recursos por cenário (YAML)
eval/            ablação: cenarios/, gabaritos/, run_ablacao.py, resultados/
data/cache/      dados congelados para o sample mode (pequenos; o repositório tem que ficar leve)
```

## 2. Tipos (app/core/models.py, pydantic)
```python
class Ocorrencia:      id: str  # "cel_<lat10>_<lon10>"
                       lat: float; lon: float; n_focos: int; frp_soma: float; frp_max: float
                       primeiro: datetime; ultimo: datetime; periodos_seguidos: int
                       status: Literal["nova","crescendo","estavel","diminuindo"] | None
                       pop_raio: int; dist_ti_uc_km: float | None; vpd_kpa: float | None; vento_kmh: float | None
                       prioridade: float; componentes: dict[str, float]   # exposicao, intensidade, tempo, ...
                       localidades: list[dict]   # [{nome, pop, dist_km}]
class Base:            id: str; nome: str; lat: float; lon: float; fonte: str = ""; simulada: bool = False
                       confianca: Literal["declarada","oficial","osm","estimada"] = "osm"   # procedência (seção 16)
class Recurso:         id: str; base_id: str; tipo: Literal["terrestre","aereo"]; capacidade: int; disponivel: bool
class Designacao:      recurso_id: str; ocorrencia_id: str; ordem: int; eta_h: float; justificativa: str
                       evidencias: list[str]   # ids de focos, "pop:...", "eta:..."
class Plano:           periodo: str; regiao: str; designacoes: list[Designacao]; reserva: list[str]
                       nao_atendidas: list[str]; resumo: str; rodada: int
class Violacao:        regra: str; ocorrencia_id: str | None; recurso_id: str | None
                       evidencia: dict; sugestao: str; rigida: bool
class ParecerAnalista: ocorrencia_id: str; pergunta: str
                       conclusao: Literal["queima_agricola_provavel","incendio_vegetacao_provavel","indeterminado"]
                       confianca: Literal["baixa","media","alta"]; evidencias: list[str]; consultas: list[str]
class VeredictoCritico: decisao: Literal["aprova","rejeita","escala"]; motivos: list[str]
                       contra_proposta: Plano | None; pedir_analista: list[str]   # ids de ocorrências
class Memoria:         id: str; regiao: str; texto: str; tipo: Literal["derivada","nota"]
                       fonte: str; confianca: float; supersedes: str | None; criada_em: datetime
```

Também em `models.py`: `RegiaoCfg` (o YAML de região, seção 8) e `Cenario` (o YAML de cenário). Para lê-los, use `app/core/config.py`: `regiao(nome)` e `cenario(caminho)`. O logger fica em `app/core/logging.py`: `LogExecucao(regiao, periodo).evento(agente, evento, dados, modelo=…, routed_model=…, receipt=…, tokens=…, latencia_s=…)`.

## 3. Dados (o que o repositório entrega)
`app/data/repositorio.py`:
```python
class Repositorio(Protocol):
    def ocorrencias(self, regiao: str, periodo: str, top: int = 15) -> list[Ocorrencia]
    def bases(self, regiao: str) -> list[Base]
    def historico_celula(self, ocorrencia_id: str, dias: int = 7) -> list[dict]   # por dia: n_focos, frp, dia_noite
    def salvar_decisoes(self, plano: Plano, aprovado_por: str) -> None             # Postgres direto
    def salvar_nota(self, regiao: str, periodo: str, texto: str, autor: str) -> None
```
Duas implementações: `RepositorioZetaris` (REST do Zetaris + Postgres) e `RepositorioCache` (lê `data/cache/`).

As views do Zetaris se chamam `ocorrencias`, `ocorrencias_contexto` e `ocorrencias_prioridade`, com as colunas de `Ocorrencia`.

## 4. LLM (app/llm/client.py)
```python
def chat(messages: list[dict], papel: str, json_schema: dict | None = None) -> LLMResult
class LLMResult: texto: str; json: dict | None; modelo: str; routed_model: str | None
                 receipt: str | None; tokens: int | None; latencia_s: float
```
- Provider por variável de ambiente: `LLM_PROVIDER=nightshift|offline`.
- Nightshift: compatível com OpenAI em `METERLESS_BASE_URL`, com o token `METERLESS_RUNTIME_TOKEN`.
- `offline`: **não chama LLM**. Os agentes usam a própria lógica determinística (cada agente implementa `decidir_offline()`).
- Toda chamada é registrada no log com `modelo`, `routed_model` e `receipt`.

## 5. H-MEM (serviço HTTP, porta 7070)
```
GET  /health                                   -> {ok: true}
POST /memorias   {regiao, texto, tipo, fonte, confianca, supersedes?}  -> Memoria
POST /recall     {regiao, consulta, k}         -> {memorias: [Memoria], substituidas: [Memoria]}
GET  /memorias?regiao=..                       -> [Memoria]   (para auditoria)
```
- A resolução de conflito e o *supersedes* seguem a semântica do engine de referência (Meterless, Apache-2.0; adaptações marcadas "FocoCerto adaptation" em `services/hmem/`).
- Ids no formato `<regiao>:mem-<n>`. `supersedes` precisa apontar para uma memória da mesma região. Ao substituir, o serviço também marca `substituida_por` na memória antiga, e é isso que a tira do ranking.
- Política de conflito entre notas (`HMEM_POLITICA_NOTAS`, padrão `coordenador_mais_recente`): a nota mais nova do coordenador vence. Com `fila`, o conflito fica na fila do engine, que não é persistida.
- Extras para auditoria: `GET /ledger?regiao=..`, `GET /conflitos?regiao=..`. O `gravar` devolve também `conflitos` e o `recall` devolve `trace`; em Python ficam em `ultimos_conflitos` e `ultimo_trace` (úteis no log).
- O recall compara palavras, não significado (embedder da referência, limiar 0,35). Consulte com termos da própria memória (id da célula, nome do lugar) ou use `listar()`.
- `app/memory_client.py` expõe as mesmas operações, com uma versão `MemoriaLocal` em memória para o sample mode e os testes.

## 6. Ferramentas (app/tools/)
```python
monitor(atuais: list[Ocorrencia], anteriores: list[Ocorrencia]) -> list[Ocorrencia]   # preenche status
checar_regras(plano: Plano, ocorrencias, recursos, bases, regiao_cfg, memorias) -> list[Violacao]
checar_citacoes(plano: Plano, ocorrencias, bases) -> list[Violacao]                   # regra="citacao_incorreta"
alocador_simples(ocorrencias, recursos, bases, regiao_cfg, reserva: int) -> Plano
eta_h(lat1, lon1, lat2, lon2, regiao_cfg) -> float   # haversine × tortuosidade ÷ velocidade
```

## 7. Log JSONL (app/core/logging.py)
Uma linha por evento em `logs/<execucao_id>.jsonl`:
```json
{"t":"ISO8601","execucao":"…","regiao":"…","periodo":"…","agente":"planejador|critico|analista|ferramenta|sistema",
 "evento":"inicio|proposta|violacao|rejeita|aprova|escala|consulta|memoria_lida|memoria_gravada|llm_call|fim",
 "dados":{…},"modelo":null,"routed_model":null,"receipt":null,"tokens":null,"latencia_s":null}
```

## 8. Configuração
`config/regioes/<regiao>.yaml`: `bbox [lat_min, lat_max, lon_min, lon_max]`, `idioma`, `velocidade_kmh`, `fator_tortuosidade`, `raio_exposicao_km`, `eta_max_h`.

`cenarios/<nome>.yaml`: `regiao`, `periodo`, `recursos: [{id, base_id, tipo, capacidade, disponivel}]`, `bases: [{id, nome, lat, lon, fonte, simulada}]` (opcional; as bases declaradas pelo coordenador são somadas às do repositório pelo grafo), `reserva`, `notas: [texto]`, `simulado: true`.

As bases vêm em camadas (seção 16). Os cenários da demo do Tocantins não declaram bases: usam as da lista oficial (`config/regioes/tocantins_bases_oficiais.csv`) e a de Palmas; só a **quantidade** de equipes é simulada.

## 9. CLI
```
python -m app.cli run --regiao R --periodo P --recursos cenarios/X.yaml [--sample]
python -m app.cli nota --regiao R [--periodo P] [--autor A] "texto"
python -m app.cli aprovar --regiao R --periodo P
python -m app.cli avaliar --regiao R
```
Saídas em `out/<regiao>/<periodo>/`: `plano.json` (`{"meta": {...}, ...ResultadoPeriodo}`, com o plano na chave `"plano"`; é o que o `aprovar` lê), `plano.md`, `mapa.html`.
Construtores usados pela CLI: `RepositorioCache()`, `RepositorioZetaris()` (configuração por variáveis de ambiente), `MemoriaLocal()`, `ClienteHMEM(HMEM_URL)`.

## 10. Execução de um período (a interface entre os agentes e a CLI)
`app/agents/grafo.py` (dono: `agentes-llm`):
```python
def executar_periodo(regiao: RegiaoCfg, cenario: Cenario, repo: Repositorio,
                     memoria: ClienteMemoria, log: LogExecucao,
                     modo: Literal["llm", "offline"] = "llm",
                     usar_critico_llm: bool = True, usar_memoria: bool = True) -> ResultadoPeriodo
```
- `usar_critico_llm` e `usar_memoria` existem para a ablação: a variante B usa `usar_critico_llm=False`, e a D usa `usar_memoria=False`.
- `ResultadoPeriodo` está em `app/core/models.py`. `executar_periodo` deve preencher `log_path` com `str(log.caminho)`.

## 11. Cliente de memória em Python (app/memory_client.py, dono: `hmem-engine`)
```python
class ClienteMemoria(Protocol):
    def gravar(self, regiao: str, texto: str, tipo: str, fonte: str,
               confianca: float = 1.0, supersedes: str | None = None) -> Memoria
    def recall(self, regiao: str, consulta: str, k: int = 5) -> tuple[list[Memoria], list[Memoria]]  # (ativas, substituidas)
    def listar(self, regiao: str) -> list[Memoria]
```
Implementações: `ClienteHMEM(base_url)` (HTTP, porta 7070) e `MemoriaLocal(caminho: str | Path | None = None)` (em memória; com `caminho`, persiste em JSON). A CLI usa `data/estado/memoria_<regiao>.json`.

## 12. Semântica adotada na leva 1 (agentes-llm)
- `Recurso.capacidade` = número de ocorrências que o recurso atende ao mesmo tempo (1 = não pode estar em duas). `Plano.reserva` = recursos disponíveis sem designação.
- `RegiaoCfg.velocidade_aereo_kmh` (padrão 180, linha reta, suposição declarada). `ResultadoPeriodo.status`: `aprova` ou `escala`.
- `historico_celula` devolve, por dia: `{dia, n_focos, frp_soma, frp_max, dia_noite: {D, N}}`.
- As notas de `cenario.notas` entram como contexto do período, mesmo com `usar_memoria=False`. Quem grava no H-MEM é a CLI (`nota`).
- `LLMResult` é um `dataclass` (o campo `json` conflita com o pydantic).
- Parâmetros opcionais extras: `chat(..., log=None)`, `checar_regras(..., reserva_minima=0)`, `checar_citacoes(..., recursos=None, regiao_cfg=None)`, `alocador_simples(..., periodo="", regiao=None)`, `eta_h(..., tipo="terrestre")`.
- Nomes de `Violacao.regra`:
  - rígidas: `capacidade_excedida`, `recurso_duplicado`, `eta_acima_limite`, `recurso_indisponivel`, `recurso_inexistente`, `ocorrencia_inexistente`, `exposta_sem_recurso`, `reserva_nao_mantida`, `citacao_incorreta`, `exposicao_sem_recurso_viavel` (esta não tem solução no plano e obriga escalação);
  - não rígidas (zona cinzenta, decididas pelo Crítico): `exposta_nao_atendida`, `restricao_memoria`.

## 13. Semântica adotada na leva 1 (dados-zetaris)
- `periodo` = data UTC `AAAA-MM-DD`. `RepositorioCache.periodos_disponiveis()` lista os dias que existem no cache.
- As views do Zetaris são `ocorrencias`, `ocorrencias_localidades`, `ocorrencias_contexto` e `ocorrencias_prioridade`, todas com as colunas `regiao` e `dia`; os componentes ficam em `c_exposicao` … `c_crescimento`. Elas foram validadas em Spark SQL 4.0 local contra o Python (698/698 ocorrências iguais). **Ainda não foram testadas no Zetaris.**
- Extras fora do Protocol: `RepositorioCache.decisoes_salvas/notas_salvas` (gravam em `data/estado/<regiao>/`) e `RepositorioZetaris.aquecer_cache/consultas/modo_usado`.
- Constantes declaradas da fórmula (`app/data/ocorrencias.py` e o SQL): `POP_REF=100000` (log), `HDW_REF=400`, intensidade em log, `PERSIST_REF=4` dias.

## 14. Ajustes depois da correção dos bugs da ablação
- `ClienteMemoria` ganha `substituida_por(memoria_id) -> str | None` (nos dois clientes). O engine, ao resolver um conflito, marca só a memória perdedora; a vencedora não recebe `supersedes`.
- O grafo lê memórias por duas vias, recall por termo **e** `listar(regiao)` filtrado (célula do período, base, localidade, palavra-chave), sem as substituídas. O log `memoria_lida` traz `vias` com a origem de cada memória.
- `exposta_sem_recurso` só é rígida se algum recurso que está numa ocorrência sem exposição chega à exposta dentro de `eta_max_h` (evidência: `liberaveis`, `liberaveis_em`); senão, a violação vira `exposta_nao_atendida` (não rígida).
- `Ocorrencia.status` pode vir `None` quando a célula já existia (`periodos_seguidos > 1`) mas não há par no período anterior.
- Citação incorreta nunca força escalação sozinha: o Crítico reescreve a justificativa a partir dos dados, e o plano final passa de novo pelo `checar_citacoes`.

## 15. Aprendizado entre períodos
- A CLI `run` chama `app.agents.aprendizado.plano_anterior` e depois `aprender_entre_periodos` antes de `executar_periodo` (a assinatura da seção 10 não muda). Fonte do plano de P-1: as decisões aprovadas (`repo.decisoes_salvas`, quando existir) ou então `<saida>/<regiao>/<P-1>/plano.json`.
- As memórias geradas são `tipo="derivada"`, `fonte="aprendizado:<P-1>-><P>"`, com o id da célula e a localidade no texto. O evento é `memoria_gravada`. A geração é idempotente.
- A lista do período é o top 15 mais até 5 ocorrências citadas pelo id numa derivada ativa de reforço (`memoria_lida.puxadas_por_memoria`), então o LLM pode ver até 20 ocorrências. Pela via `listar`, uma derivada só entra por célula ou localidade do período.
- Risco conhecido: derivadas de texto parecido com números diferentes podem ser marcadas como conflito pelo engine. O `substituida_por` aparece no evento `memoria_gravada` para isso ficar visível.

## 16. Bases em camadas, com procedência
Uma base é a localização de uma unidade de combate. A quantidade de equipes em cada uma continua vindo do cenário (o coordenador informa). Camadas, da maior para a menor confiança (`Base.confianca`):

| Camada | `confianca` | Origem | Quem soma |
|---|---|---|---|
| 1 | `declarada` | `Cenario.bases` (o coordenador declara) | o grafo |
| 2 | `oficial` | `config/regioes/<regiao>_bases_oficiais.csv` (opcional): `id,nome,orgao,lat,lon,fonte,data_fonte[,coordenada]`. No Zetaris: `fococerto_arq.bases_oficiais` (coluna `regiao` a mais), registrada por `scripts/setup_zetaris.py` | `Repositorio.bases` |
| 3 | `osm` | OpenStreetMap `amenity=fire_station` (`data/cache/<regiao>/bases.csv`, `fococerto_arq.bases`) | `Repositorio.bases` |
| 4 | `estimada` | sede de município do GeoNames com `pop >= bases_estimadas_pop_min` (padrão 20000), unidade **não verificada**. Só entra se nenhuma base das camadas 2–3 cai dentro da bbox, ou se o YAML da região tem `bases_estimadas: sempre` (`nunca` desliga; padrão `auto`) | `Repositorio.bases` |

- **Fusão** (`app/data/bases.py`): mesma unidade = mesmo id ou distância < 3 km (`RAIO_FUSAO_KM`). Fica o registro de maior confiança; as fundidas entram no texto de `fonte` ("fundida com <id> (<camada>: <fonte>)"). `fundir_com_apelidos` também devolve `{id descartado: id mantido}`.
- `Repositorio.bases(regiao)` devolve as camadas 2–4 já fundidas. Para somar as declaradas sem duplicata: `app.data.bases.fundir_bases(repo_bases, declaradas)` (marca as declaradas como `declarada`, e elas vencem no mesmo lugar) ou `fundir_bases_com_apelidos(...)` para remapear `Recurso.base_id`.
- `fonte` e `simulada` continuam (compatibilidade). Uma base de `Cenario.bases` ou com `simulada: true` é mostrada como `declarada` mesmo que o YAML não traga `confianca`.
- **Saída:** `plano.md` rotula a base de cada recurso (`base oficial`, `base OSM`, …), tem a seção "Bases e procedência" (procedência, fonte, recursos) e, com cenário simulado, o aviso "Bases: localização real com fonte; quantidade de equipes simulada (cenário)" (ou a contagem de declaradas/estimadas). No `mapa.html`, a cor e a borda do quadrado da base mudam com a procedência, com legenda e fonte no popup.
- **Tocantins (primeiro exemplo da camada 2):** CBMTO (1º BBM Palmas, 3ª Cia Paraíso, 5ª Cia Porto Nacional, 3º BBM Gurupi, Cias de Dianópolis e Colinas), brigadas federais Prevfogo/Ibama da Portaria nº 114/2024 (São Félix do Tocantins, Santa Tereza do Tocantins, Itacajá, Goiatins, Arraias) e ICMBio Esec Serra Geral do Tocantins (Rio da Conceição). Coordenada = sede do município no GeoNames (o endereço do quartel não está georreferenciado), exceto Palmas, que usa o ponto do OSM e reaproveita o id `osm_n5067657890`. **Ressalva:** algumas companhias do CBMTO foram reorganizadas em 2023; cada base "existe segundo a fonte citada" (URL e ano no CSV), não segundo um inventário oficial atualizado.
- Na implantação real, a camada 2 é o sistema do órgão (ex.: Sisfogo) federado pelo Zetaris, no lugar do CSV.

## 17. Ajustes da revisão (25/10)
- `log_path`: relativo à raiz do repo quando o log está dentro dela; absoluto quando está fora.
- CLI: `avaliar [--modo offline|llm] [--repeticoes N] [--variantes ABCD] [--cenarios ID…] [--saida DIR] [--sample]` chama `eval.run_ablacao.main` por import (`--regiao` é aceito e ignorado). `SAMPLE_MODE=true` (ou 1/yes/sim/on) equivale a `--sample` em todos os subcomandos.
- Nova regra não rígida `troca_recurso_local`: ocorrência exposta sem recurso X e um recurso r designado a outra exposta Y; dispara se r chega a X dentro de `eta_max_h` (sem bloqueio por memória), chega a X ≥ 0,5 h antes do que chega a Y, e pop(Y) ≤ 1,1 × pop(X). A evidência traz os candidatos.
- Guarda-corpo no grafo: toda ocorrência com `pop_raio > 0` sem designação no plano final vira escalação (`sugestao: "solicitar apoio externo"`), mesmo com o Crítico aprovando; o status vira `escala`. `ResultadoPeriodo.escalacoes[]` ganha a chave opcional `sugestao`.

## 18. Ciclo no modo LLM (25/10)
- Citação incorreta é corrigida pelo sistema ANTES do Crítico (`base.reescrever_citacoes` no nó de checagem). Novo evento `ferramenta/citacao_corrigida` (`rodada`, `agente_que_errou`, `correcoes[]` com campo, citado, real, justificativa antes/depois) e `historico[].citacoes_corrigidas`. O Crítico recebe só as violações do plano corrigido; `historico[].violacoes` mantém todas.
- `checar_citacoes` aceita prefixo inequívoco de localidade, "ETA ≤/limite de N h" quando N = `eta_max_h`, e o nome da base de saída em `loc:`/`dist:`.
- Planejador: `SaidaPlano.respostas_ao_critico` (opcional); na rodada ≥ 2 recebe os pontos do Crítico e a contra-proposta.
- Última rodada rejeitada sem violação rígida aberta → `divergencia_zona_cinzenta`: status `aprova` (salvo o guarda-corpo das expostas), com a contra-proposta do Crítico se ela não violar regra rígida. Impasse só com regra rígida aberta.
- Aprendizado também grava derivada de reignição a partir do `historico_celula` (queima atual ≤ 2 dias, depois de ≥ 1 dia sem foco, com ≥ 3 focos antes na janela de 7 dias).
