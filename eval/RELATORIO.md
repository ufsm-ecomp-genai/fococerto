# Relatório da ablação

> **ATENÇÃO: este é o resultado do modo OFFLINE.** Os agentes são as versões determinísticas (`decidir_offline`),
> sem LLM. Este relatório **valida o pipeline da ablação** (cenários, injeção, checagens e métricas) e mostra o que
> as ferramentas e as heurísticas offline fazem. **Não é o resultado final do FocoCerto**: a comparação que responde à
> pergunta da Track 3 é a do modo `llm` (Nightshift), que ainda não foi rodada.

- Método, variantes, definições das checagens e das métricas: `eval/README.md`.
- Cenários e gabaritos: commit `fcf42df` ("Avaliação: cenários e gabaritos escritos antes de qualquer execução",
  24/10/2026 15:56 -03:00). Nenhum gabarito foi alterado depois.
- **Execução atual:** `.venv/bin/python -m eval.run_ablacao --modo offline --repeticoes 3`, com o código depois da
  correção dos 7 bugs (commit `b97dfe7`) e da memória derivada automática entre períodos
  (`app/agents/aprendizado.py`, ainda sem commit). São 12 cenários × 4 variantes × 3 repetições = 144 execuções, em
  cerca de 15 s. Resultados: `eval/resultados/20261024T222738Z_offline/` (um JSON por execução, logs JSONL,
  `resumo.json` e `tabela.md`).
- A tabela é idêntica, célula por célula, à da execução logo depois das correções
  (`eval/resultados/20261024T221351Z_offline/`). A memória derivada automática não muda a ablação: cada cenário é um
  período só, e a aprendizagem entre períodos roda na CLI `run` (veja `scripts/demo_3_periodos.sh`).
- Histórico: `eval/resultados/20261024T185955Z_offline_antes_correcao_grafo/` (antes da correção do recall pelo
  líder; C e D davam 48/87 cada, porque nenhuma memória chegava aos agentes) e
  `eval/resultados/20261024T220043Z_offline/` (commit `25b7f44`, antes da correção dos 7 bugs; tabela "antes" abaixo).

## Tabela atual (modo offline, depois das correções)

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** alocador simples | 18/81 (22,2%) | 15/51 | 0/27 | 0/3 | 0 | 4,399 | 6,213 | 0,0 | 0/36 | 0,0 | 0,0 | 0 |
| **B** Planejador + checador | 48/81 (59,3%) | 27/51 | 18/27 | 0/3 | 0 | 4,365 | 6,121 | 1,167 | 0/36 | 0,0 | 0,0 | 0 |
| **C** completo | 69/87 (79,3%) | 36/51 | 27/30 | 0/6 | 0 | 4,441 | 6,279 | 1,333 | 33/36 | 5,167 | 0,0 | 0 |
| **D** C sem H-MEM | 51/87 (58,6%) | 30/51 | 15/30 | 0/6 | 0 | 4,365 | 6,121 | 1,333 | 33/36 | 5,0 | 0,0 | 0 |

**Antes → depois das correções (acerto):** A 22,2% → 22,2%; B 44,4% → 59,3%; C 62,1% → 79,3%; D 55,2% → 58,6%.
O ganho do H-MEM (C − D) passou de +6 para +18 checagens. As citações falsas no plano final caíram de 9 (B) e 3
(C, D) para 0.

Os totais de checagens aplicáveis mudam entre variantes porque `parecer_conclusao` só se aplica a C e D, que têm
Analista. "ETA pond." é o ETA ponderado por exposição, com penalidade de 12 h para exposta não atendida.

Por cenário: P = passou e F = falhou, iguais nas 3 repetições; – = não se aplica.

| Cenário | A | B | C | D |
|---|---|---|---|---|
| agricola_recorrente_parana_24out | c1:F c2:– | c1:F c2:– | c1:F c2:F | c1:F c2:F |
| controle_taguatinga_liberada_21out | c1:P c2:P | c1:P c2:P | c1:P c2:P | c1:P c2:P |
| controle_vegetacao_parana_19out | c1:– c2:P | c1:– c2:P | c1:P c2:P | c1:P c2:P |
| escalar_expostas_22out | c1:F c2:F | c1:F c2:F | c1:P c2:P | c1:P c2:P |
| excecao_dianopolis_ponte_18out | c1:F c2:P | c1:F c2:P | **c1:P** c2:P | c1:F c2:P |
| excecao_mateiros_alagada_23out | c1:F c2:P c3:P c4:F | c1:F c2:P c3:P c4:F | **c1:P** c2:P c3:P c4:P | c1:F c2:P c3:P c4:P |
| fato_errado_localidade_23out | c1:F c2:F c3:F | c1:P c2:P c3:P | c1:P c2:P c3:P | c1:P c2:P c3:P |
| fato_errado_populacao_23out | c1:F c2:F c3:F | c1:P c2:P c3:P | c1:P c2:P c3:P | c1:P c2:P c3:P |
| fato_errado_tendencia_23out | c2:F c3:F | c2:F c3:F | c2:P c3:F | c2:P c3:F |
| reignicao_conceicao_20out | c1:F c2:F | c1:P c2:P | **c1:P c2:P** | c1:F c2:F |
| reignicao_morros_24out | c1:F c2:F | c1:P c2:P | **c1:P c2:P** | c1:F c2:F |
| tradeoff_noite_gurupi_20out | c1:F c2:F c3:F | c1:F c2:F c3:F | c1:F c2:F c3:F | c1:F c2:F c3:F |

## Interpretação (só do modo offline, depois das correções)

- **Variância zero.** No modo offline tudo é determinístico: as 3 repetições dão o mesmo plano em todos os
  cenários. Só confirma que o pipeline é reprodutível. A variância que interessa vem no modo LLM.
- **A → B (+30 checagens).** O checador pega a população e a localidade erradas injetadas, e a justificativa é
  reescrita a partir dos dados; B também usa as memórias (B só troca o Crítico pelo checador), por isso passa nos dois
  casos de reignição. A alocação de B ainda é quase a do alocador: o Planejador offline é praticamente o guloso.
- **D → C (+18): é a contribuição do H-MEM.** Vem das notas do coordenador (Mateiros e Dianópolis: C deixa parada a
  viatura da base bloqueada, D a manda) e, agora, das memórias derivadas de reignição (Conceição e Morros: a memória
  chega aos agentes pelo `listar` filtrado e sobe a prioridade da célula; em Conceição, ela também entra como
  evidência de vegetação no Analista, que conclui `indeterminado` e não rebaixa a célula como queima agrícola). Respeitar a exceção custa um pouco de ETA ponderado (4,441 h em C contra 4,365 h em D).
- **Queima agrícola:** `agricola_recorrente_parana_24out` falha em C e D (c1 e c2). Com o histórico agora incluindo o
  dia do período (bug 4), a célula aparece "crescendo" e o Analista conclui `indeterminado` (baixa) em vez de
  `queima_agricola_provavel`; a designação é mantida por precaução. Antes da correção, o parecer acertava (c2:P) por
  olhar só até o dia anterior. O offline também não tem a opção "deixar de reserva". No controle
  (`controle_vegetacao_parana_19out`), não houve alarme falso.
- **Fato errado:** C e D detectam e corrigem população e localidade falsas (c1–c3 passam). O fato de tendência/dia-noite
  não é coberto por nenhuma ferramenta: c3 falha em todas as variantes.
- **Trade-off da chegada à noite:** falha em todas as variantes. O guloso processa por prioridade, e gurupi-t1 vai
  para Monte do Carmo (5,1 h) antes de chegar a vez de Cariri (0,8 h). É o tipo de caso que o Crítico LLM deveria pegar.
- **Escalação:** C e D escalam corretamente em `escalar_expostas_22out`, e B aprova em silêncio. C e D escalam em 33
  de 36 execuções; nos nossos cenários de escassez quase sempre há exposta sem recurso. Ponto de atenção para o modo LLM.
- **Alarmes falsos:** nenhum nas checagens de controle, e nenhuma citação falsa no plano final.

**Conclusão provisória (offline):** a parte determinística mostra papel real do checador (A→B) e do H-MEM (D→C:
notas e memórias derivadas). As capacidades que dependem de julgamento (trade-off, fato fora do checador, decidir não
atender queima agrícola) continuam falhando no offline. Elas precisam ser medidas no modo LLM.

## Tabela antes das correções (histórico, commit `25b7f44`)

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** alocador simples | 18/81 (22,2%) | 15/51 | 0/27 | 0/3 | 0 | 4,399 | 6,213 | 0,0 | 0/36 | 0,0 | 0,0 | 0 |
| **B** Planejador + checador | 36/81 (44,4%) | 21/51 | 12/27 | 0/3 | 9 | 4,365 | 6,121 | 2,0 | 15/36 | 0,417 | 0,0 | 0 |
| **C** completo | 54/87 (62,1%) | 24/51 | 24/30 | 0/6 | 3 | 4,441 | 6,279 | 1,0 | 36/36 | 4,5 | 0,0 | 0 |
| **D** C sem H-MEM | 48/87 (55,2%) | 24/51 | 18/30 | 0/6 | 3 | 4,365 | 6,121 | 1,0 | 36/36 | 4,333 | 0,0 | 0 |

Naquela execução as memórias derivadas não chegavam aos agentes (bug 1), os dois casos de reignição falhavam em
todas as variantes, e o Crítico offline escalava com a justificativa falsa ainda no plano (bug 3).

## Bugs encontrados pela ablação (corrigidos no commit `b97dfe7`, testes em `tests/test_regressao_ablacao.py`)

Descrição original, mantida como histórico:

1. **Memória derivada não volta no recall** (`app/agents/grafo.py` + `app/memory_client.py`, donos `agentes-llm` e
   `hmem-engine`). Mesmo com uma consulta por termo, uma memória longa não passa do limiar de 0,35 contra um termo
   curto, nem pelo id da célula. Reprodução:
   ```python
   from app.memory_client import MemoriaLocal
   m = MemoriaLocal(); m.gravar("tocantins", "Derivada dos dados FIRMS (19/10): a célula cel_-120_-470 teve 6 focos em 17/10 e 5 em 18/10 e nenhum em 19/10. Se voltar a ter focos, é reignição do mesmo fogo, não foco novo.", "derivada", "dados:firms", 0.9)
   for q in ["cel_-120_-470", "reignição", "célula cel_-120_-470 reignição focos"]:
       print(q, m.recall("tocantins", q, k=5)[0])   # [] nos três casos
   ```
   Antes da correção do líder, nem as notas do coordenador voltavam: uma consulta de 92 palavras dava `[]`.
2. **`checar_citacoes` com localidades de mesmo nome** (`app/tools/citacoes.py`): `locs = {norm(nome): l}` fica só
   com a última. cel_-88_-479 (24/10) tem duas "Santa Maria do Tocantins" (10,4 km e 14,3 km), e a justificativa
   correta do alocador ("a 10.4 km") é acusada de `citacao_incorreta`. Em B isso leva a 3 rodadas e a um impasse. Para
   reproduzir: `reignicao_morros_24out`, variante B, ver `historico[*].violacoes`.
3. **O Crítico offline escala com a justificativa falsa** (`app/agents/critico.py`, `decidir_offline`). Uma
   `citacao_incorreta` é tratada como regra rígida, mas `realocar` gera os mesmos pares, então cai em "Escalação:
   não encontrei plano alternativo". O plano que vai ao coordenador mantém o texto falso. Para reproduzir:
   `fato_errado_populacao_23out`, variante C.
4. **`historico_celula` termina no dia anterior** (`app/data/repositorio.py`, `RepositorioCache`). `ate` usa
   `_ultimo_periodo`, que é o último período passado a `ocorrencias()`, e o grafo consulta o período anterior por
   último. O Analista nunca vê o dia atual. Para reproduzir: no log de `agricola_recorrente_parana_24out__C__r1`, a
   consulta `historico_celula` vai de 17/10 a 23/10 num período de 24/10.
5. **`monitor` marca "nova" uma célula que já existia** porque o grafo só pega o top 100 do dia anterior (179
   ocorrências em 23/10). cel_-124_-479 tem `periodos_seguidos=5` e status `nova` em 24/10.
6. **`interpretar_memorias` casa base por palavras genéricas** (`app/tools/memorias.py` + `tokens_nome`). "tocantins" e
   "simulada" viram tokens de nome de base. Uma nota "Estrada alagada perto de Porto Nacional, no Tocantins" bloqueia
   `sim_paraiso` ("Paraíso do Tocantins"), e qualquer nota com "simulada" bloqueia todas as bases simuladas. Os
   cenários evitam essas palavras para não confundir o teste principal.
7. **`exposta_sem_recurso` (rígida) não confere se o recurso da ocorrência sem exposição chegaria à exposta**
   (`app/tools/regras.py`). Em `reignicao_conceicao_20out`, os recursos de Conceição não alcançam Cariri, Pium nem
   Novo Acordo, mas a regra dispara, fica impossível de resolver e força a escalação.
8. (corrigido no `25b7f44`) `ResultadoPeriodo.status` não era preenchido. O `run_ablacao.py` ainda lê o prefixo
   `[escala]`/`[aprova]` do resumo se o campo vier vazio, e marca `status_lido_do_resumo`. Na execução final o campo
   veio preenchido em todas as execuções.

## Estimativa para o modo LLM (não rodado)

A estimativa usa os pontos de decisão observados no offline atual, por execução: B tem 1,17 do Planejador; C e D têm
1,33 do Planejador, 1,92 do Crítico e 0,67 do Analista. São 12 cenários × 3 repetições, e A não chama LLM.

- **Mínimo** (1 chamada por decisão): ~324 chamadas. **Máximo** (retry de JSON em tudo e 2 chamadas por
  Analista): ~744 chamadas.
- Com 30 s por chamada (suposição; a especificação fala em "dezenas de segundos"): **2,7 h a 6,2 h**. Com 60 s, o
  dobro.
- No modo LLM a trajetória pode ser mais longa (até 3 rodadas). O teto teórico é 54 chamadas por execução. Para
  calibrar a latência, rode primeiro `--cenarios fato_errado_tendencia_23out --repeticoes 1` e use a latência
  medida em `--latencia-s`.
