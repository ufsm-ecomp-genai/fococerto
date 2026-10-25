# Avaliação do FocoCerto: ablação com casos-gabarito

A pergunta da Track 3 é: **os agentes e a memória tomam decisões melhores?** Para responder sem circularidade,
comparamos quatro variantes do sistema em cenários onde a decisão certa **não** sai direto das regras rígidas do
checador, e conferimos cada execução contra um gabarito escrito **antes** de rodar.

## Honestidade

- **Os gabaritos foram escritos pelo time** (agente de avaliação). Não há verdade de campo: o gabarito diz qual é a
  decisão certa *dado o que os dados e as memórias dizem*, e o porquê. As ressalvas de cada caso estão no campo
  `ressalvas` do gabarito.
- **Cenários e gabaritos foram commitados antes de qualquer execução da ablação.** A data do commit
  ("Avaliação: cenários e gabaritos escritos antes de qualquer execução") é a prova. Nenhum gabarito pode ser editado
  depois de ver resultados; se um gabarito estiver errado, a correção entra num commit separado, explicado no
  `RELATORIO.md`, e o resultado com o gabarito original continua publicado.
- Durante o desenho dos cenários usamos só ferramentas determinísticas, sem LLM e sem Crítico: a contagem de focos
  por célula e dia no cache, a matriz de ETA (`app.tools.geo.eta_recurso`), o `monitor` e o `alocador_simples`
  (o baseline), para confirmar que a situação de cada caso acontece de fato nos dados. **Nenhuma variante B, C ou D
  foi executada antes do commit.**
- **O código dos agentes já existia quando os gabaritos foram escritos:** o commit dos agentes (`e06ec8d`, 24/10
  15:28 -03:00) é 28 minutos anterior ao dos gabaritos (`1d722b5`, 15:56). Quem escreveu os gabaritos podia ter lido
  esse código; a garantia é só que nenhuma variante B, C ou D tinha sido executada.
- **Corrigimos 7 bugs depois de ver checagens falharem** (commit `39e42d2`, com testes de regressão em
  `tests/test_regressao_ablacao.py`). São correções de comportamento geral (recall de memórias, localidades de mesmo
  nome, histórico do Analista sem o dia atual, etc.), cada uma documentada com a reprodução em `RELATORIO.md`, e não
  regras para cenários específicos. Mesmo assim, foram feitas depois de ver os resultados offline, e isso favorece os
  números offline publicados; a tabela "antes" continua no `RELATORIO.md`. Não ajustamos prompts para passar nos
  gabaritos, e nenhum gabarito foi alterado. Problemas encontrados vão para o líder.
- Se C não ganhar de B, isso fica escrito no relatório, com a análise dos casos que falharam.

## O que é real e o que é simulado

- **Real:** focos (NASA FIRMS VIIRS, 17 a 24/10/2026), localidades (GeoNames), tempo (Open-Meteo), todos do
  cache congelado em `data/cache/tocantins`. O dia 24/10 é parcial (cache congelado às 18h25 UTC).
- **Simulado** (`simulado: true`): recursos, bases declaradas (cidades reais do GeoNames, sem verificar se há
  unidade de combate), memórias iniciais e os trechos injetados nos casos de fato errado.
- `pop_raio` soma a população do GeoNames, que muitas vezes é a do município: a exposição perto de cidades médias
  fica superestimada. Os gabaritos não dependem de comparar populações grandes com pequenas por causa disso.

## Variantes

| | Descrição | Como roda |
|---|---|---|
| **A** | `alocador_simples` sozinho | mesma preparação do grafo (top 15 + `monitor` + bases do cenário) e o alocador; sem checador, Crítico, Analista ou memória |
| **B** | Planejador + checador realimentando | `executar_periodo(..., usar_critico_llm=False)` |
| **C** | completo (Crítico + Analista + H-MEM) | `executar_periodo(...)` |
| **D** | C sem H-MEM | `executar_periodo(..., usar_memoria=False)` |

Cada cenário roda **3 vezes por variante** (`--repeticoes`). No modo `offline` tudo é determinístico e as 3
repetições devem coincidir: isso valida o pipeline, não mede o sistema. **A comparação que vale é no modo `llm`.**
No modo offline o Planejador é quase igual ao alocador simples, então A e B tendem a coincidir.

A memória de cada cenário é carregada numa `MemoriaLocal()` nova por execução, com `gravar` na ordem em que aparece
em `memorias_iniciais` (`supersedes_ref` aponta para o `ref` de uma memória anterior do mesmo cenário).

## Cenários (`eval/cenarios/*.yaml`)

Cada arquivo tem os campos de `Cenario` (`regiao`, `periodo`, `recursos`, `bases`, `reserva`, `notas`, `simulado`),
mais `id`, `tipo`, `titulo`, `situacao_nos_dados`, `como_verificamos`, `memorias_iniciais` e `injecao`.

| Tipo (seção 10 da especificação) | Cenários |
|---|---|
| Exceção legítima vinda da memória | `excecao_mateiros_alagada_23out`, `excecao_dianopolis_ponte_18out`, controle `controle_taguatinga_liberada_21out` |
| Queima agrícola recorrente | `agricola_recorrente_parana_24out`, controle `controle_vegetacao_parana_19out` |
| Trade-off exposição × ETA | `tradeoff_noite_gurupi_20out`, `escalar_expostas_22out` |
| Justificativa com fato errado | `fato_errado_populacao_23out`, `fato_errado_localidade_23out`, `fato_errado_tendencia_23out` |
| Reignição vista só pela memória derivada | `reignicao_conceicao_20out`, `reignicao_morros_24out` |

Os casos de **controle** medem alarme falso: a decisão certa é a "óbvia", e o erro seria o sistema inventar
uma exceção ou rebaixar sem motivo.

### Como o fato errado é injetado

Esse caso só aparece naturalmente no modo LLM. Para testá-lo de forma reprodutível, o `run_ablacao.py` envolve
`planejador.decidir` e `planejador.decidir_offline` (monkeypatch só durante a execução daquele cenário): **na
rodada 1**, o trecho de `injecao.texto` é acrescentado ao fim da justificativa da designação de
`injecao.ocorrencia` (se essa ocorrência não estiver no plano, vai para a primeira designação, e o resultado
registra onde caiu). As rodadas seguintes não são alteradas. Na variante A, o trecho é acrescentado ao plano do
alocador, que não passa por checador nenhum. Os três fatos errados: população (o `checar_citacoes` cobre),
localidade fora do raio (cobre) e tendência/dia-noite inventados (**não** cobre; só um Crítico que leia a
justificativa contra os dados pode pegar).

## Gabaritos (`eval/gabaritos/*.yaml`)

Cada gabarito tem `decisao_certa`, `por_que`, `ressalvas` e uma lista de `checagens`. Cada checagem tem uma
`categoria`: `decisao` (a decisão certa), `deteccao` (o sistema percebeu a situação) ou `alarme_falso` (se falhar,
o sistema inventou um problema).

Definições usadas nas checagens:
- **atendida:** existe designação para a ocorrência no plano final (`ResultadoPeriodo.plano`).
- **escalada:** a ocorrência aparece em `escalacoes[].ocorrencia_id` ou no texto de um `motivo` de escalação.
  A variante A não escala nada.

| Tipo | Passa quando |
|---|---|
| `recurso_nao_designado {recurso}` | o recurso não tem designação |
| `recurso_designado_para {recurso, ocorrencia}` | existe a designação recurso → ocorrência |
| `recurso_nao_designado_para {recurso, ocorrencia}` | não existe essa designação |
| `ocorrencia_atendida {ocorrencia, eta_max_h?}` | atendida (e, se dado, com `eta_h` ≤ `eta_max_h`) |
| `ocorrencia_nao_atendida {ocorrencia}` | sem designação |
| `ocorrencia_atendida_ou_escalada {ocorrencia, eta_max_h?}` | atendida dentro do ETA dado, ou escalada |
| `prioriza {ocorrencia, sobre}` | não acontece de `sobre` ser atendida e `ocorrencia` não |
| `status {valor}` | `ResultadoPeriodo.status == valor` (A não tem status: falha) |
| `expostas_nao_atendidas_escaladas` | toda ocorrência do top com `pop_raio > 0` sem designação está escalada |
| `parecer_conclusao {ocorrencia, esperada?, proibida?}` | só C e D (A e B não têm Analista: "não se aplica"). Com parecer: passa se `conclusao == esperada` (quando dada) e `!= proibida`. Sem parecer: falha se havia `esperada` (não detectou), passa se só havia `proibida` (não houve alarme falso) |
| `citacao_detectada_rodada1 {ocorrencia}` | na rodada 1 há violação `citacao_incorreta` naquela ocorrência (A não tem checador: falha) |
| `rodada1_nao_aprovada` | o veredicto da rodada 1 não é `aprova` (A: falha) |
| `texto_ausente_plano_final {trecho}` | nenhuma justificativa do plano final contém o trecho |

## Métricas (`run_ablacao.py`)

- **Acerto nos gabaritos:** checagens que passam ÷ checagens aplicáveis, no total e por categoria.
- **Detecções:** checagens `deteccao` que passam ÷ aplicáveis.
- **Alarmes falsos:** (1) checagens `alarme_falso` que falham; (2) violações `citacao_incorreta` em designações que
  **não** receberam trecho injetado, em qualquer rodada (o texto do alocador é gerado por template a partir dos
  dados, então qualquer acusação ali é alarme falso do checador).
- **ETA ponderado por exposição** (horas): média do ETA das ocorrências do top 15 com `pop_raio > 0`, ponderada por
  `pop_raio`. O ETA é o `eta_h` da designação (o menor, se houver mais de uma). **Ocorrência exposta não atendida
  conta com a penalidade 2 × `eta_max_h`** (12 h no Tocantins), escalada ou não: escalar não leva equipe ao local.
  Como `pop_raio` superestima cidades médias, também reportamos a mesma média com peso `log10(1 + pop_raio)`.
  Essa métrica não é uma regra do checador: mede quanto tempo a população exposta espera, em média.
- **Rodadas** até o fim e **escalações** (status `escala` e número de entradas em `escalacoes`).
- **Variância entre repetições:** desvio-padrão do acerto e do ETA ponderado entre as repetições, e se os planos
  (pares recurso → ocorrência) foram idênticos.

### Acerto por execução única (/27 e /29)

O "Acerto" da tabela soma as 3 repetições (81 = 27 checagens × 3 para A e B; 87 = 29 × 3 para C e D, que têm as 2
checagens de parecer a mais). Como no modo offline as 3 repetições são idênticas, "69/87" é a mesma informação
que "23/29": **o tamanho real da amostra é 27 (ou 29) checagens em 12 cenários**, e uma checagem a mais ou a menos
vale ~3,5 pontos percentuais. Por isso também reportamos, por variante, o acerto de cada repetição (`r1 / r2 / r3`,
cada uma sobre /27 ou /29), a média, o mínimo, o máximo e o desvio-padrão em número de checagens. No modo LLM a
diferença entre repetições é a variância real do sistema.

### Sobre-escalação

Os gabaritos dão crédito a quem escala (`ocorrencia_atendida_ou_escalada`, `expostas_nao_atendidas_escaladas`),
e "escalada" inclui citar o id no texto do motivo. Um sistema que escalasse tudo passaria nessas checagens. Para
medir isso, cada execução tem (somas por variante na tabela "Escalação"):

- **Ocorrências escaladas:** ocorrências do período que contam como escaladas pela regra dos gabaritos e que
  **não** têm designação no plano final (citar no motivo uma ocorrência atendida não é escalá-la).
- **Sobre-escaladas** = sem exposição ∪ com recurso livre viável:
  - **sem exposição:** escalada com `pop_raio == 0`. Escalar é pedir apoio externo, e a regra do time é escalar
    população exposta sem recurso;
  - **com recurso livre viável:** existe recurso disponível com capacidade sobrando que chega em até `eta_max_h`
    (o mesmo ETA de `app.tools.geo`), cuja base não está bloqueada pelas memórias/notas do cenário nem pelas
    `memorias_usadas` do resultado (lidas por `interpretar_memorias`; rota terrestre bloqueada para a ocorrência
    também exclui o terrestre), **e** há mais recursos livres do que a reserva mínima do cenário.
- Informativos (não entram na sobre-escalação): **só quebrando a reserva** (um recurso livre chegaria, mas é a
  reserva mínima) e **com troca possível** (um recurso que está numa ocorrência sem população chegaria à escalada
  exposta em até `eta_max_h`; é a troca que o checador chama de `liberaveis`).
- **Citadas no motivo mas atendidas:** ids que aparecem no texto de uma escalação, mas têm designação. Mostra quanto
  a regra "id no motivo" do gabarito pode contar como escalada algo que não foi.
- **Escalações sem alvo:** entradas de `escalacoes` sem `ocorrencia_id` e sem nenhum id no motivo.
- **Por impasse:** entradas cujo motivo começa com "Impasse" (o grafo escala porque acabaram as rodadas sem
  aprovação, não porque decidiu pedir apoio).
- **Checagens que passaram só por escalar:** checagens que passam com o resultado e falham se `escalacoes` for
  esvaziada (crédito que o gabarito deu à escalação). Subtraindo esse número do acerto, tem-se o acerto sem crédito
  de escalação.

Limite conhecido: a métrica não pega a troca entre duas ocorrências **expostas** (ex.: mandar a viatura local para
uma comunidade menor e escalar a maior, que fica a 10 min). Isso é trade-off de prioridade, coberto pelas checagens
de `prioriza` e pelo ETA ponderado, não por esta métrica.

## Reignição em 2 períodos (`--dois-periodos`)

Nos cenários de reignição originais, a memória derivada vem **escrita no cenário** (`memorias_iniciais`). Para
testar se o sistema a produz sozinho, o modo `--dois-periodos` usa `eval/cenarios_2periodos/` e
`eval/gabaritos_2periodos/`:

1. memória vazia (`MemoriaLocal()`), sem `memorias_iniciais`;
2. roda o período `periodo_anterior` (P1) com a mesma variante e os mesmos recursos;
3. `app.agents.aprendizado.aprender_entre_periodos(P1 -> P2)` grava as derivadas na memória (o mesmo passo da
   CLI `run`, CONTRATOS seção 15), com o plano de P1 vindo direto do resultado;
4. roda P2 (o período original) e confere contra o gabarito.

O JSON de cada execução ganha `periodo_anterior` (pares de P1, `nao_atendidas` e as memórias aprendidas, com
texto e fonte). Na variante A (sem memória) e na D (`usar_memoria=False`), a memória é gerada mas não é lida.

**Estes cenários e gabaritos foram escritos em 25/10/2026, DEPOIS da ablação original** (offline e LLM), e antes
de rodar este modo. Os gabaritos copiam sem mudança as checagens dos originais (`reignicao_conceicao_20out`,
`reignicao_morros_24out`), e cada cenário traz o campo `previsao_antes_de_rodar`.

## Como rodar

```
.venv/bin/python -m eval.run_ablacao --modo offline --repeticoes 3
.venv/bin/python -m eval.run_ablacao --modo llm --repeticoes 3      # precisa do Nightshift (LLM_PROVIDER=nightshift)
.venv/bin/python -m eval.run_ablacao --estimar                      # só estima chamadas LLM e tempo
.venv/bin/python -m eval.run_ablacao --modo offline --dois-periodos # reignição em 2 períodos
.venv/bin/python -m eval.recalcular eval/resultados/<pasta>         # recalcula tudo dos JSONs salvos, sem rodar nada
```

`eval/recalcular.py` lê os `<cenario>__<variante>__r<n>.json` de uma pasta, confere de novo contra os gabaritos,
recalcula as métricas (inclusive as de sobre-escalação e por execução única) e grava `resumo_recalculado.json` e
`tabela_recalculada.md` na própria pasta (ou em `--saida`), sem tocar no `resumo.json`/`tabela.md` originais. Avisa
se alguma checagem recalculada difere da salva. A agregação e a tabela ficam em `eval/agregacao.py`, que não
importa o código dos agentes.

Saída em `eval/resultados/<timestamp>_<modo>/`: um JSON por execução (`<cenario>__<variante>__r<n>.json`, com o
resultado, as checagens e o caminho do log JSONL), `resumo.json` e `tabela.md`.
