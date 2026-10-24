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
class Base:            id: str; nome: str; lat: float; lon: float
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

`cenarios/<nome>.yaml`: `regiao`, `periodo`, `recursos: [{id, base_id, tipo, capacidade, disponivel}]`, `reserva`, `notas: [texto]`, `simulado: true`.

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
