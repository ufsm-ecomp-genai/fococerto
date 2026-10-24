# Relatório da ablação

> **ATENÇÃO: este é o resultado do modo OFFLINE.** Os agentes são as versões determinísticas (`decidir_offline`),
> sem LLM. Este relatório **valida o pipeline da ablação** (cenários, injeção, checagens e métricas) e mostra o que
> as ferramentas e as heurísticas offline fazem. **Não é o resultado final do FocoCerto**: a comparação que responde à
> pergunta da Track 3 é a do modo `llm` (Nightshift), que ainda não foi rodada.

- Método, variantes, definições das checagens e das métricas: `eval/README.md`.
- Cenários e gabaritos: commit `fcf42df` ("Avaliação: cenários e gabaritos escritos antes de qualquer execução",
  24/10/2026 15:56 -03:00). Nenhum gabarito foi alterado depois.
- Execução: `.venv/bin/python -m eval.run_ablacao --modo offline --repeticoes 3`, com o código do commit `25b7f44`
  (recall de uma consulta por termo, `ResultadoPeriodo.status` preenchido e escalação que lista todas as expostas sem
  recurso). São 12 cenários × 4 variantes × 3 repetições = 144 execuções, em cerca de 14 s.
- Resultados: `eval/resultados/20261024T220043Z_offline/`, com um JSON por execução, os logs JSONL, `resumo.json` e
  `tabela.md`.
- A execução anterior à correção está em `eval/resultados/20261024T185955Z_offline_antes_correcao_grafo/`. Nela,
  C e D davam o mesmo resultado (48/87 cada), porque nenhuma memória chegava aos agentes.

## Tabela (modo offline)

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** alocador simples | 18/81 (22,2%) | 15/51 | 0/27 | 0/3 | 0 | 4,399 | 6,213 | 0,0 | 0/36 | 0,0 | 0,0 | 0 |
| **B** Planejador + checador | 36/81 (44,4%) | 21/51 | 12/27 | 0/3 | 9 | 4,365 | 6,121 | 2,0 | 15/36 | 0,417 | 0,0 | 0 |
| **C** completo | 54/87 (62,1%) | 24/51 | 24/30 | 0/6 | 3 | 4,441 | 6,279 | 1,0 | 36/36 | 4,5 | 0,0 | 0 |
| **D** C sem H-MEM | 48/87 (55,2%) | 24/51 | 18/30 | 0/6 | 3 | 4,365 | 6,121 | 1,0 | 36/36 | 4,333 | 0,0 | 0 |

Os totais de checagens aplicáveis mudam entre variantes porque `parecer_conclusao` só se aplica a C e D, que têm
Analista. "ETA pond." é o ETA ponderado por exposição, com penalidade de 12 h para exposta não atendida.

Por cenário: P = passou e F = falhou, iguais nas 3 repetições; – = não se aplica.

| Cenário | A | B | C | D |
|---|---|---|---|---|
| agricola_recorrente_parana_24out | c1:F c2:– | c1:F c2:– | c1:F c2:P | c1:F c2:P |
| controle_taguatinga_liberada_21out | c1:P c2:P | c1:P c2:P | c1:P c2:P | c1:P c2:P |
| controle_vegetacao_parana_19out | c1:– c2:P | c1:– c2:P | c1:P c2:P | c1:P c2:P |
| escalar_expostas_22out | c1:F c2:F | c1:F c2:F | c1:P c2:P | c1:P c2:P |
| excecao_dianopolis_ponte_18out | c1:F c2:P | c1:F c2:P | **c1:P** c2:P | c1:F c2:P |
| excecao_mateiros_alagada_23out | c1:F c2:P c3:P c4:F | c1:F c2:P c3:P c4:F | **c1:P** c2:P c3:P c4:P | c1:F c2:P c3:P c4:P |
| fato_errado_localidade_23out | c1:F c2:F c3:F | c1:P c2:P c3:P | c1:P c2:P c3:F | c1:P c2:P c3:F |
| fato_errado_populacao_23out | c1:F c2:F c3:F | c1:P c2:P c3:P | c1:P c2:P c3:F | c1:P c2:P c3:F |
| fato_errado_tendencia_23out | c2:F c3:F | c2:F c3:F | c2:P c3:F | c2:P c3:F |
| reignicao_conceicao_20out | c1:F c2:F | c1:F c2:F | c1:F c2:F | c1:F c2:F |
| reignicao_morros_24out | c1:F c2:F | c1:F c2:F | c1:F c2:F | c1:F c2:F |
| tradeoff_noite_gurupi_20out | c1:F c2:F c3:F | c1:F c2:F c3:F | c1:F c2:F c3:F | c1:F c2:F c3:F |

## Interpretação (só do modo offline)

- **Variância zero.** No modo offline tudo é determinístico: as 3 repetições dão o mesmo plano em todos os
  cenários. É o esperado e só confirma que o pipeline é reprodutível. A variância que interessa vem no modo LLM.
- **A → B (+18 checagens).** O ganho vem do checador: B pega a população e a localidade erradas injetadas e
  reescreve a justificativa na rodada 2. A e B tomam as mesmas decisões de alocação. Como o líder já tinha observado,
  o Planejador offline é praticamente o alocador.
- **D → C (+6): é a contribuição do H-MEM**, e vem só das notas do coordenador. Em Mateiros e Dianópolis, C
  deixa a viatura da base bloqueada parada. D manda a viatura (c1 falha). Isso custa um pouco de ETA ponderado
  (4,441 h em C contra 4,365 h em D), porque respeitar a exceção tira um recurso próximo. É o preço esperado.
- **As memórias derivadas (reignição) não chegam aos agentes**, nem depois da correção: veja o bug 1 abaixo. Por isso
  os dois casos de reignição falham igual em todas as variantes. Fizemos um diagnóstico **fora da ablação**,
  entregando a mesma memória como nota do período (`cenario.notas`, que não passa pelo recall). Com isso,
  `reignicao_morros_24out` passa (c1 e c2). `reignicao_conceicao_20out` continua falhando: a memória sobe a
  prioridade da célula, mas o Analista conclui `queima_agricola_provavel` (média), porque o mesmo padrão "queimou,
  parou, voltou, FRP baixo, diurno" é a assinatura de manejo da heurística. O Crítico então rebaixa a célula. A
  conclusão do Analista não leva a memória em conta. Esse conflito entre reignição e queima recorrente está
  registrado como ambiguidade no gabarito.
- **Queima agrícola:** em C e D, o Analista acerta o parecer (`queima_agricola_provavel`, média) em
  `agricola_recorrente_parana_24out`, mas a decisão falha. O Crítico offline só multiplica a prioridade por 0,3 e
  realoca. Como parana-t1 não tem outra ocorrência viável, ele continua indo para a queima. O offline não tem a
  opção "deixar de reserva". No controle (`controle_vegetacao_parana_19out`), não houve alarme falso: o parecer saiu
  `indeterminado` e a designação foi mantida.
- **Fato errado:** C e D detectam o erro (c1 e c2), mas **pioram em relação a B na decisão (c3)**. O Crítico offline
  escala na rodada 1 com a justificativa falsa ainda no plano (bug 3). O fato de tendência/dia-noite não é coberto
  por nenhuma ferramenta, e c3 falha em todas as variantes. Em C e D, c2 passa por outro motivo (a escalação), não
  porque o erro foi visto.
- **Trade-off da chegada à noite:** falha em todas as variantes. O guloso processa por prioridade, e gurupi-t1 vai
  para Monte do Carmo (5,1 h) antes de chegar a vez de Cariri (0,8 h). O Crítico offline só troca recursos entre uma
  exposta e uma ocorrência *sem* exposição, e aqui as duas têm exposição. Esse é exatamente o tipo de caso que o
  Crítico LLM deveria pegar.
- **Escalação em zona cinzenta:** C e D escalam corretamente em `escalar_expostas_22out`, e B aprova em silêncio.
  Mas C e D escalam **em 36 de 36 execuções**, inclusive no controle de Taguatinga. Nos nossos cenários (escassez)
  sempre há exposta sem recurso, então ainda não dá para dizer se o Crítico escala demais. Fica como ponto de
  atenção para o modo LLM.
- **Alarmes falsos:** nenhum nas checagens de controle. O checador de citações gerou 9 alarmes falsos em B e 3 em C
  e D, todos o mesmo bug (2).

**Conclusão provisória (offline):** a parte determinística já mostra papel real do checador (A→B) e das notas no
H-MEM (D→C). As capacidades que dependem de julgamento (trade-off, fato fora do checador, decidir não atender
queima agrícola) falham no offline, como era de se esperar. Elas precisam ser medidas no modo LLM.

## Bugs encontrados (não corrigidos: são de outros donos)

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

A estimativa usa os pontos de decisão observados no offline, por execução: B tem 2,0 do Planejador; C e D têm 1,0
do Planejador, 1,42 do Crítico e 0,5 do Analista. São 12 cenários × 3 repetições, e A não chama LLM.

- **Mínimo** (1 chamada por decisão): ~282 chamadas. **Máximo** (retry de JSON em tudo e 2 chamadas por
  Analista): ~636 chamadas.
- Com 30 s por chamada (suposição; a especificação fala em "dezenas de segundos"): **2,4 h a 5,3 h**. Com 60 s, o
  dobro.
- No modo LLM a trajetória pode ser mais longa (até 3 rodadas). O teto teórico é 54 chamadas por execução. Para
  calibrar a latência, rode primeiro `--cenarios fato_errado_tendencia_23out --repeticoes 1` e use a latência
  medida em `--latencia-s`.
