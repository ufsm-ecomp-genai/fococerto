# Relatório da ablação

> **ATENÇÃO: este é o resultado do modo OFFLINE.** Os agentes são as versões determinísticas (`decidir_offline`),
> sem LLM. Este relatório **valida o pipeline da ablação** (cenários, injeção, checagens e métricas) e mostra o que
> as ferramentas e as heurísticas offline fazem. **Não é o resultado final do FocoCerto**: a comparação que responde à
> pergunta da Track 3 é a do modo `llm` (Nightshift). O Nightshift real funciona desde 25/10/2026, e a ablação no modo
> `llm` foi concluída em 25/10: veja a seção "Modo LLM" no fim deste arquivo.

- Método, variantes, definições das checagens e das métricas: `eval/README.md`.
- Cenários e gabaritos: commit `1d722b5` ("Avaliação: cenários e gabaritos escritos antes de qualquer execução",
  24/10/2026 15:56 -03:00). Nenhum gabarito foi alterado depois.
- **Execução atual:** `.venv/bin/python -m eval.run_ablacao --modo offline --repeticoes 3`, com o código depois da
  correção dos 7 bugs (commit `39e42d2`) e da memória derivada automática entre períodos
  (`app/agents/aprendizado.py`, commitada depois em `dcc949f`). São 12 cenários × 4 variantes × 3 repetições = 144 execuções, em
  cerca de 15 s. Resultados: `eval/resultados/20261024T222738Z_offline/` (um JSON por execução, logs JSONL,
  `resumo.json` e `tabela.md`).
- A tabela é idêntica, célula por célula, à da execução logo depois das correções
  (`eval/resultados/20261024T221351Z_offline/`). A memória derivada automática não muda a ablação: cada cenário é um
  período só, e a aprendizagem entre períodos roda na CLI `run` (veja `scripts/demo_3_periodos.sh`).
- Histórico: `eval/resultados/20261024T185955Z_offline_antes_correcao_grafo/` (antes da correção do recall pelo
  líder; C e D davam 48/87 cada, porque nenhuma memória chegava aos agentes) e
  `eval/resultados/20261024T220043Z_offline/` (commit `0e6261f`, antes da correção dos 7 bugs; tabela "antes" abaixo).

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

## Tabela antes das correções (histórico, commit `0e6261f`)

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** alocador simples | 18/81 (22,2%) | 15/51 | 0/27 | 0/3 | 0 | 4,399 | 6,213 | 0,0 | 0/36 | 0,0 | 0,0 | 0 |
| **B** Planejador + checador | 36/81 (44,4%) | 21/51 | 12/27 | 0/3 | 9 | 4,365 | 6,121 | 2,0 | 15/36 | 0,417 | 0,0 | 0 |
| **C** completo | 54/87 (62,1%) | 24/51 | 24/30 | 0/6 | 3 | 4,441 | 6,279 | 1,0 | 36/36 | 4,5 | 0,0 | 0 |
| **D** C sem H-MEM | 48/87 (55,2%) | 24/51 | 18/30 | 0/6 | 3 | 4,365 | 6,121 | 1,0 | 36/36 | 4,333 | 0,0 | 0 |

Naquela execução as memórias derivadas não chegavam aos agentes (bug 1), os dois casos de reignição falhavam em
todas as variantes, e o Crítico offline escalava com a justificativa falsa ainda no plano (bug 3).

## Bugs encontrados pela ablação (corrigidos no commit `39e42d2`, testes em `tests/test_regressao_ablacao.py`)

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
8. (corrigido no `0e6261f`) `ResultadoPeriodo.status` não era preenchido. O `run_ablacao.py` ainda lê o prefixo
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


## Modo LLM (Nemotron 3 Ultra via Nightshift), 25/10/2026

`eval/resultados/20261025T015525Z_llm/` · 144 execuções · 450 chamadas (449 válidas na primeira tentativa, 1 JSON
inválido recuperado, 0 fallbacks para o offline) · latência média de 29 s. A execução ficou presa 14 h numa chamada
(timeout entre pacotes, corrigido no cliente com um prazo total) e foi retomada com `--retomar`, reaproveitando as 30
execuções já feitas (a mudança foi só no transporte HTTP, sem efeito nas decisões).

| Variante | Acerto | Decisão | Detecção | Alarmes falsos | Fatos errados escritos pelo LLM e pegos | Citações falsas no plano final |
|---|---|---|---|---|---|---|
| A | 18/81 (22,2%) | 15/51 | 0/27 | 0/3 | n/a | 6 (injetadas; A não tem checador) |
| B | 53/81 (65,4%) | 32/51 | 18/27 | 0/3 | 56 | 0 |
| C | 66/87 (75,9%) | 36/51 | 24/30 | 0/6 | 54 | 0 |
| D | 64/87 (73,6%) | 37/51 | 21/30 | 0/6 | 47 | 0 |

Leitura honesta:
- **Correção de 25/10:** a coluna "fatos errados escritos pelo LLM e pegos" está inflada por falsos positivos do próprio checador (lia "dentro do limite de 6 h" como ETA citado e o nome da base de saída como localidade); o checador foi corrigido e o número real será medido de novo. O que continua valendo: nenhum plano final de B, C ou D
  chegou ao coordenador com citação falsa (conferido rodando `checar_citacoes` sobre os 108 planos finais).
- O Crítico com LLM pega o que o código não pega: em `fato_errado_tendencia`, B falha e C e D passam nas 3 repetições.
- A memória acrescenta pouco no modo LLM (C − D = +2 checagens, contra +18 no offline). `reignicao_conceicao` falha em
  todas as variantes. **Atenção (26/10):** a variante D estava contaminada; veja "Memória no modo LLM: o braço sem
  memória vazou" no fim deste relatório.
- Variação entre repetições: desvio do acerto ≤ 0,018; planos diferentes entre repetições em 2 de 12 cenários.
- ETA ponderado por exposição: 4,40 h (A) → 3,77 h (C).

### Acerto por execução única (/27 e /29)

Recalculado dos JSONs salvos com `.venv/bin/python -m eval.recalcular <pasta>`, sem rodar o LLM de novo (as
checagens recalculadas batem com as salvas em todas as 144 execuções de cada pasta). O total acima soma as 3
repetições: "66/87" não são 87 observações independentes, são 29 checagens (12 cenários) vistas 3 vezes. No
offline as 3 repetições são idênticas por construção (agentes determinísticos), então o /81 só multiplica por 3
o mesmo resultado. A amostra real é /27 (A, B) ou /29 (C, D), e uma checagem vale ~3,5 pontos percentuais.

| Variante | LLM: r1 / r2 / r3 | LLM: média (desvio, em checagens) | Offline: cada repetição |
|---|---|---|---|
| A | 6/27 · 6/27 · 6/27 | 6,0/27 (0) | 6/27 |
| B | 18/27 · 18/27 · 17/27 | 17,7/27 (0,47) | 16/27 |
| C | 22/29 · 22/29 · 22/29 | 22,0/29 (0) | 23/29 |
| D | 22/29 · 21/29 · 21/29 | 21,3/29 (0,47) | 17/29 |

Leitura: no modo LLM, **C − D é 0,67 checagem por execução** (22,0 contra 21,3), menor que uma checagem, e cabe
na variação entre repetições de D (21 a 22). Não dá para afirmar, com esta amostra, que a memória melhora o modo
LLM. No offline, C − D = 6 checagens por execução (23 contra 17).

### Sobre-escalação

Os gabaritos dão crédito a quem escala, e "escalada" inclui citar o id no motivo. Definições em
`eval/README.md` ("Sobre-escalação"). Somas sobre as 36 execuções de cada variante:

| Modo | Var. | Ocorrências escaladas | Sobre-escaladas | Sem exposição | Com recurso livre viável | Só quebrando a reserva (info) | Citadas no motivo mas atendidas | Escalações sem alvo | Por impasse | Checagens que passaram só por escalar |
|---|---|---|---|---|---|---|---|---|---|---|
| LLM | B | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 12 | 0 |
| LLM | C | 40 | 0 | 0 | 0 | 0 | 30 | 0 | 18 | 0 |
| LLM | D | 40 | 0 | 0 | 0 | 0 | 26 | 0 | 16 | 0 |
| offline | B | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| offline | C | 186 | 0 | 0 | 0 | 18 | 0 | 0 | 0 | 6 |
| offline | D | 180 | 0 | 0 | 0 | 18 | 0 | 0 | 0 | 3 |

(A nunca escala: tudo 0. Fontes: `eval/resultados/20261025T015525Z_llm/` e
`eval/resultados/20261024T222738Z_offline/`, arquivos `tabela_recalculada.md` e `resumo_recalculado.json`.)

Leitura:
- **Nenhuma sobre-escalação pela definição estrita**, nos dois modos: nenhuma ocorrência escalada estava sem
  população, e nenhuma tinha um recurso livre, viável e não bloqueado além da reserva. No offline, 18 escaladas de
  C e 18 de D seriam alcançáveis por um recurso **da reserva mínima** (informativo; respeitar a reserva é regra).
- **O crédito de escalação inflou pouco o offline:** sem ele, C cai de 69/87 para 63/87 (6 checagens:
  `escalar_expostas_22out` c2 e `excecao_mateiros_alagada_23out`, 3 repetições cada) e D de 51/87 para 48/87.
  C − D sem esse crédito continua +15. No modo LLM, nenhuma checagem passou só por escalar.
- **No modo LLM, toda escalação é impasse.** As 12 de B, 18 de C e 16 de D começam com "Impasse: 3 rodadas sem
  aprovação": o sistema escalou porque as rodadas acabaram (quase sempre por citação incorreta que o Planejador não
  conseguiu corrigir), não porque decidiu pedir apoio. 18 dessas 46 escalações estão nos **cenários de controle**
  (`controle_taguatinga_liberada_21out` e `controle_vegetacao_parana_19out`, 3 por variante), onde a decisão certa
  é a óbvia. As checagens de alarme falso desses cenários não olham o status, então isso não aparece no acerto: é um
  alarme falso que a tabela principal não mostra.
- **No modo LLM o problema é o contrário: sub-escalação.** As escalações de B não citam nenhuma ocorrência (12 sem
  alvo), e `escalar_expostas_22out` c2 ("toda exposta sem recurso está nas escalações") falha em B, C e D nas 3
  repetições. Em C e D, 30 e 26 ids citados nos motivos são de ocorrências que **foram** atendidas (o texto do
  impasse fala delas): a regra "id no motivo" dos gabaritos pode contar como escalada o que não foi. Neste conjunto,
  isso não mudou nenhuma checagem.

### Reignição em 2 períodos (memória gerada pelo `aprendizado.py`), só offline

`.venv/bin/python -m eval.run_ablacao --modo offline --repeticoes 3 --dois-periodos` →
`eval/resultados/20261025T200648Z_offline_2periodos/`. Cenários `eval/cenarios_2periodos/*_2p.yaml`, **escritos
depois da ablação** (25/10), com a previsão registrada antes de rodar. Mesmos dados, recursos e período P2 dos
originais, mas sem memória semeada: roda P1, o `aprender_entre_periodos(P1 -> P2)` grava as derivadas, e roda P2.

| Cenário (P1 → P2) | A | B | C | D | Memórias geradas sobre a célula-alvo |
|---|---|---|---|---|---|
| `reignicao_conceicao_20out_2p` (19/10 → 20/10) | c1:F c2:F | c1:F c2:F | c1:F c2:F | c1:F c2:F | nenhuma (6 derivadas "recebeu recurso e diminuiu" sobre outras células) |
| `reignicao_morros_24out_2p` (23/10 → 24/10) | c1:F c2:F | c1:F c2:F | c1:F c2:F | c1:F c2:F | nenhuma (5 derivadas sobre outras células) |

Igual nas 3 repetições. **A previsão se confirmou:** com a memória gerada pelo próprio sistema, os dois casos de
reignição falham em todas as variantes, enquanto com a memória semeada B, C passavam (offline). O motivo está no
`comparar()` do `aprendizado.py`: ele só olha células que estavam no plano de P1 (designadas ou em
`nao_atendidas`). Em Conceição, cel_-120_-470 não tem foco em 19/10 (não existe em P1). Em Morros, cel_-96_-465
está na posição 99 de 179 em 23/10, fora do top 15, e o fato que importa (13 focos e 482 MW em 22/10) é de P-2.
Ou seja: **o resultado de reignição da tabela principal depende da memória escrita no cenário**; o aprendizado
automático atual não a produz. Pedido ao `agentes-llm` (relatado ao líder): uma derivada de reignição a partir do
`historico_celula` das ocorrências de P (célula que volta depois de dia(s) sem foco, ou que teve FRP alto em P-2..P-k
e ainda queima), não só a comparação com o plano de P-1.

Observação: neste modo B, C e D escalam (12 ocorrências cada), e na ablação offline de 24/10 B não escalava. O
código dos agentes mudou depois da ablação (fila de correções do ESTADO, item 1: escalação obrigatória de exposta
sem recurso). As tabelas acima, de 24 e 25/10, são do código daquela data.


## Modo LLM, 2ª rodada depois das correções (25/10, noite)

`eval/resultados/20261025T220912Z_llm/` · 48 execuções (1 repetição) · 137 chamadas, todas válidas, 0 fallbacks ·
latência média de 25 s. Mudanças desde a 1ª rodada: citações corrigidas antes do Crítico, escalação obrigatória,
troca de equipe local, bases reais com fonte, fim dos impasses de zona cinzenta.

| Variante | Acerto | ETA ponderado |
|---|---|---|
| A | 6/27 (22,2%) | 4,40 h |
| B | 21/27 (77,8%) | 4,00 h |
| C | 24/29 (82,8%) | 3,48 h |
| D | 24/29 (82,8%) | 3,48 h |

- O sistema corrigiu 24 fatos errados escritos pelo Nemotron antes do Crítico (12 distâncias, 6 localidades,
  6 populações), cada um registrado como `citacao_corrigida`. Nenhum plano final de B, C ou D tem citação falsa
  (conferido rodando `checar_citacoes` sobre os planos finais).
- Impasses: de 30 para 6. Os 6 restantes têm regra rígida aberta (`capacidade_excedida`, `eta_acima_limite`) depois de
  3 rodadas, em `controle_vegetacao_parana_19out` e `excecao_dianopolis_ponte_18out`; escalar para o humano é o
  comportamento esperado. 8 divergências de zona cinzenta fecharam como `divergencia_zona_cinzenta`.
- C e D idênticos, mas isso **não** mostra que a memória não ajuda: o braço D estava contaminado (seção seguinte).


## Offline com o código de 26/10

`eval/resultados/20261026T225811Z_offline/` · `python -m eval.run_ablacao --modo offline` (3 repetições, idênticas) ·
código depois das correções de 25/10 e da explicação das escalações (motivo cita quem chegaria e para onde foi; as
decisões não mudam: a ablação deu o mesmo resultado antes e depois dessa mudança).

| Variante | Acerto | Decisão | Detecção | Alarmes falsos | Sinalizações de citação (qualquer rodada) |
|---|---|---|---|---|---|
| A | 18/81 (22,2%) | 15/51 | 0/27 | 0/3 | 0 |
| B | 57/81 (70,4%) | 36/51 | 18/27 | 0/3 | 0 |
| C | 72/87 (82,8%) | 39/51 | 27/30 | 0/6 | 0 |
| D | 54/87 (62,1%) | 33/51 | 15/30 | 0/6 | 3 |

C − D = +18 checagens, todas nos 4 cenários em que a memória deve mudar a decisão (Dianópolis e Mateiros: base
bloqueada; Conceição e Morros: reignição). As 3 sinalizações em D são a checagem de cobertura pegando o resumo do
próprio Planejador offline (`excecao_dianopolis_ponte_18out`, "incluído taguatinga-t1→cel_-117_-470", designação que o
plano não tem); o resumo é reescrito antes do Crítico, e nenhum plano final a carrega. A coluna "Citações falsas" das
tabelas acima conta violações `citacao_incorreta` em qualquer rodada, não só no plano final.

## Memória no modo LLM: o braço sem memória vazou

Nas duas rodadas LLM (`20261025T015525Z_llm` e `20261025T220912Z_llm`), a variante D (`usar_memoria=False`) não recebe
memória pelo código: nenhum evento `memoria_lida`, `memorias_usadas` vazio, prompt do Planejador ~200 tokens menor que
o de C (ex.: Morros, 16.731 contra 16.934). Mesmo assim, o texto do Nemotron em D cita as memórias dos cenários, às
vezes palavra por palavra:

- `reignicao_morros_24out` D: "482 MW em 22/10" (números exatos da memória derivada), já na 1ª proposta do Planejador;
- `excecao_dianopolis_ponte_18out` D: "restrição de memória (ponte caída) confirmada pelo coordenador"; o resumo da
  rodada 1 é idêntico ao de C;
- `excecao_mateiros_alagada_23out` D e `controle_taguatinga_liberada_21out` D também citam as notas.

O caminho no código está limpo (`dados_comuns` só envia `ctx.memorias`, vazio em D; `notas` é vazio em todos os
cenários; prompts e YAMLs não têm esses textos; o cliente não tem cache). D rodou segundos depois de C, com os mesmos
`meterless-app: fococerto` e `meterless-scope: user`. Hipótese: contexto ou respostas guardados do lado do Nightshift.
Os logs não guardam o prompt, então não dá para provar. Conclusão: **o modo LLM não mede o efeito da memória**; a
comparação limpa é a offline. Para medir de verdade: rodar C e D com `METERLESS_SCOPE` diferente por execução.

Duas falhas reais de C, independentes do vazamento: em Mateiros o Planejador devolveu a equipe da base bloqueada na
rodada 2 e o Crítico aprovou (`restricao_memoria` é regra não rígida, `app/tools/regras.py`); em Conceição a célula
reforçada pela memória não foi atendida.

### Causa encontrada e medição limpa (26/10, noite)

A causa não era a ordem C→D: era o escopo do Nightshift. O mesmo prompt do Planejador da variante D (Morros), que
não tem "482 MW" nem "13 focos", enviado com `meterless-scope: user` chegou ao modelo com **15.595** tokens de
entrada e a resposta citou a memória; com um escopo novo chegou com **10.682** e não citou. O Nightshift junta
~4.900 tokens de contexto lembrado de chamadas anteriores ao prompt no escopo `user`. Correção: o cliente manda um
escopo próprio por execução (`fococerto-<id da execução>`, commit `73aed60`).

Medição limpa, só os 5 cenários com memória, 1 repetição, Nemotron, escopos isolados:
`eval/resultados/20261026T232357Z_llm_memoria_escopo_isolado/`.

| Cenário | C | D | Diferença |
|---|---|---|---|
| `excecao_mateiros_alagada_23out` | 4/4 | 3/4 | c1: C respeita a base bloqueada pela nota; D manda a equipe |
| `excecao_dianopolis_ponte_18out` | 1/2 | 1/2 | — |
| `controle_taguatinga_liberada_21out` | 2/2 | 2/2 | — (controle) |
| `reignicao_conceicao_20out` | 0/2 | 1/2 | c2: D passa, C falha |
| `reignicao_morros_24out` | 2/2 | 2/2 | D chega à célula só pelos dados |
| **Total** | **9/12** | **9/12** | |

Nenhum texto da D cita memória. Leitura: com o Nemotron, a memória mudou uma decisão de forma atribuível
(Mateiros) e, no total, C = D nesta amostra (uma repetição, 12 checagens; uma checagem vale ~8 pontos). Não dá para
afirmar ganho líquido da memória no modo LLM; o efeito medido de forma limpa continua sendo o offline (+18). As
rodadas LLM completas (`20261025T015525Z_llm`, `20261025T220912Z_llm`) foram feitas com o escopo `user` e, portanto,
com contexto injetado pelo Nightshift em B, C e D.

## Modo LLM, 3ª rodada, limpa: escopo do Nightshift isolado (26/10, noite) — números oficiais

`eval/resultados/20261026T234558Z_llm/` · 12 cenários × 4 variantes × 1 repetição = 48 execuções · 122 chamadas ao
Nemotron, 0 erros, 0 fallbacks · latência média 21 s · cada execução no próprio escopo do Nightshift (commit `73aed60`).

| Variante | Acerto | Decisão | Detecção | Alarmes falsos | ETA ponderado | Impasses |
|---|---|---|---|---|---|---|
| A | 6/27 (22,2%) | 5/17 | 0/9 | 0/1 | 4,40 h | – |
| B | 17/27 (63,0%) | 11/17 | 5/9 | 0/1 | 3,87 h | 1 |
| C | 24/29 (82,8%) | 15/17 | 7/10 | 0/2 | 2,76 h | 0 |
| D | 23/29 (79,3%) | 15/17 | 6/10 | 0/2 | 3,06 h | 2 |

Por cenário (checagens que passaram, A/B/C/D): `fato_errado_tendencia` 0/0/2/2, `tradeoff_noite_gurupi` 0/0/3/3,
`controle_vegetacao_parana` 1/1/2/2, `excecao_mateiros_alagada` 2/3/4/3 (a única diferença entre C e D: c1, a equipe
da estrada alagada), `escalar_expostas` 0/2/2/2, `reignicao_morros` 0/2/2/2, os dois `fato_errado` de localidade e
população 0/3/3/3, `excecao_dianopolis_ponte` 1/1/1/1, `controle_taguatinga` 2/2/2/2, `agricola_recorrente_parana` e
`reignicao_conceicao` 0 em todas.

- Fatos errados escritos pelo Nemotron e reescritos antes do Crítico: **44** (17 localidades, 15 distâncias,
  6 populações, 1 ETA, 3 afirmações do resumo, 2 ids inexistentes). `checar_citacoes` rodado de novo sobre os 36 planos
  finais de B, C e D: **0** citações falsas (descontado o fato injetado de propósito nos cenários `fato_errado`).
- B caiu de 77,8% (2ª rodada) para 63,0%: as rodadas anteriores usavam o escopo `user`, em que o Nightshift junta
  contexto de chamadas anteriores, e isso ajudava as variantes. Estes são os números que valem; as rodadas de 25/10
  ficam como histórico.

