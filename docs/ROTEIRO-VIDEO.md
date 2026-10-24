# Roteiro do vídeo de demonstração (até 4 min)

Baseado na seção 14 da especificação, ajustado ao que **existe de fato** no repositório em 24/10/2026. O vídeo vale 15 pontos e precisa mostrar o agente funcionando (não slides), a integração com o Zetaris, o engine Meterless e **uma requisição real passando pelo Nightshift**.

Legenda: **[NIGHTSHIFT]** = depende do Nightshift real (ainda não testado). **[ZETARIS]** = depende do Zetaris real (ainda não testado). Cada trecho marcado tem um **plano B** que já funciona hoje e não finge o que não aconteceu.

## Antes de gravar (checklist)
- [ ] `rm -rf data/estado out` para começar com a memória vazia.
- [ ] Terminal com fonte grande; `.env` **nunca** aparece na tela (nem token, nem chave da NVIDIA).
- [ ] Se o Nightshift estiver no ar: `LLM_PROVIDER=nightshift` e rodar **sem** `--sample`. Rodar uma vez antes para medir o tempo (cada chamada pode levar dezenas de segundos) e gravar a execução real, cortando só a espera.
- [ ] Se o Zetaris estiver no ar: `scripts/setup_zetaris.py --regioes tocantins` feito antes e `--so-cache` depois de qualquer reinício.
- [ ] Abrir `out/tocantins/2026-10-23/mapa.html` no navegador já com o zoom no Tocantins.
- [ ] Ter a tabela da ablação pronta (de `eval/RELATORIO.md`, do modo que tiver rodado de verdade).

---

## 1. (0:00–0:25) O problema
**Tela:** `mapa.html` do Tocantins, período 23/10/2026.

**Fala:** "Ontem, 23 de outubro, o satélite VIIRS da NASA registrou 514 detecções no Tocantins. Agrupadas, são 179 ocorrências, e 52 têm uma cidade a menos de 15 km. O coordenador regional tem 6 equipes. Qual ocorrência atender primeiro, e com quem? O FocoCerto propõe a ordem de recursos, um crítico revisa, e o coordenador aprova."

**Dizer na tela (legenda):** "Focos reais (NASA FIRMS). Recursos e a maioria das bases: simulados."

## 2. (0:25–0:55) Os dados pelo Zetaris
**[ZETARIS] Se o Zetaris estiver no ar:** mostrar no SQL editor do Zetaris um `SELECT * FROM fococerto.ocorrencias_prioridade WHERE regiao='tocantins' AND dia='2026-10-23' ORDER BY prioridade DESC LIMIT 15`, e depois o `run` sem `--sample` imprimindo `Dados: Zetaris`.

**Fala:** "Uma camada no Zetaris federa três tipos de fonte: os focos no Postgres, as cidades e as bases em CSV no file store, e o tempo do Open-Meteo numa tabela REST com cache. Quatro views calculam as ocorrências, a exposição e a prioridade, com uma fórmula transparente."

**Plano B (funciona hoje, honesto):** mostrar `sql/zetaris_views.sql` (a view `ocorrencias_prioridade`) e `python scripts/setup_zetaris.py --dry-run | head -40`. Fala: "As views foram validadas num Spark SQL local, o motor sob o Zetaris: 698 de 698 ocorrências iguais à implementação em Python. A ligação com o Zetaris real é o próximo passo." **Não** dizer que rodou no Zetaris.

## 3. (0:55–2:00) O raciocínio: Planejador, Crítico e Analista
**Tela:** terminal.
```bash
python -m app.cli run --regiao tocantins --recursos cenarios/tocantins-escasso.yaml   # [NIGHTSHIFT]
# plano B: o mesmo comando com --sample
```
**Mostrar:** as linhas de progresso (planejador: proposta → ferramenta: violacao → critico: escala) e o resultado: 6 designações e 9 escaladas no modo offline.

**[NIGHTSHIFT] Se o Nightshift estiver no ar:** mostrar no log as linhas `llm_call` com `routed_model` e `receipt`:
```bash
grep llm_call logs/<execucao>.jsonl | python -c "import sys,json;[print(j['agente'],j['modelo'],j['routed_model'],j['latencia_s']) for j in map(json.loads,sys.stdin)]"
```
Fala: "Cada agente fala com o Nemotron pelo Nightshift, e o log registra qual modelo respondeu." **É o trecho que prova a requisição real pelo Nightshift: não cortar.**

**Fala (vale nos dois modos):** "O alocador guloso propõe. As ferramentas aplicam as regras rígidas e conferem cada fato citado. O Crítico julga o que fica em zona cinzenta: aqui há 9 ocorrências com população e nenhum recurso viável livre, então ele escala para o coordenador em vez de esconder o problema."

**O Analista (≈20 s):** rodar um cenário em que o Crítico tem uma pergunta em aberto:
```bash
python -m app.cli run --sample --regiao tocantins --recursos eval/cenarios/agricola_recorrente_parana_24out.yaml
```
Mostrar as linhas `analista: consulta` (7 consultas) e, no `plano.md`, o parecer: "`cel_-124_-479`: provável queima agrícola ou de manejo (confiança média): 12 focos em 7 dias, 0% à noite, FRP baixo". Fala: "O Crítico chama o Analista, que consulta o histórico de 7 dias e conclui, com incerteza declarada, que é provável queima de manejo. O Crítico usa isso: o recurso rende mais numa ocorrência com população. Como não encontra um plano que resolva todas as regras rígidas, ele escala, com o parecer anexado."

**No modo offline, dizer:** "Aqui os agentes rodam em modo determinístico, sem LLM; no modo LLM, as mesmas decisões passam pelo Nemotron."

## 4. (2:00–2:50) A memória: a nota "estrada para Mateiros alagada" muda o plano
**Tela:** terminal + `plano.md` (seções "Ordem de recursos" e "Memórias que influenciaram o plano").
```bash
python -m app.cli nota --regiao tocantins --periodo 2026-10-23 "estrada para Mateiros alagada"
python -m app.cli run  --regiao tocantins --recursos cenarios/tocantins-escasso.yaml [--sample]
```
**Resultado real (sample):** `mateiros-t1` deixa de ir por terra a `cel_-96_-468` (Lizarda) e fica em reserva; a ocorrência é escalada (5 designações, 10 escaladas). No ciclo de revisão: "Exceção aceita: memória tocantins:mem-1 (…) vale sobre a regra da base mais próxima".

```bash
python -m app.cli nota --regiao tocantins --periodo 2026-10-24 "estrada para Mateiros liberada"
#  -> "Substitui a memória tocantins:mem-1."
python -m app.cli run  --regiao tocantins --recursos cenarios/tocantins-escasso.yaml [--sample]
```
**Resultado real:** `mateiros-t1` volta para Lizarda (6 designações, 9 escaladas); o plano mostra "`tocantins:mem-2` … substitui `tocantins:mem-1`".

**Fala:** "A nota do coordenador vira uma memória no H-MEM, o engine da Meterless. O Crítico decide se a exceção vale. Quando chega a nota contrária, o H-MEM detecta o conflito e marca a antiga como substituída, sem apagar nada. A memória é separada por região."

**Prova (5 s):** `cd services/hmem && npm test` terminando em `13/13 checks passed`.

**Atenção:** usar exatamente as frases "estrada para Mateiros alagada" e "estrada para Mateiros liberada". Com "alagada, sem acesso" o plano também volta, mas o *supersedes* automático não dispara (a similaridade fica abaixo do limiar do engine).

**Aprendizado ao longo de 3 períodos:** mostrar com `scripts/demo_3_periodos.sh` (21 → 22 → 23/10). No dia 22, células que ficaram sem recurso no dia 21 e cresceram viram memória derivada e mudam o plano (ex.: `palmas-a1` vai para `cel_-97_-491`, Abreulândia, "[muda por causa da memória]"). No dia 23, a nota "liberada" substitui a "alagada" e o recurso de Mateiros volta.

## 5. (2:50–3:30) A prova: ablação A/B/C/D
**Tela:** a tabela de `eval/RELATORIO.md`.

**Fala:** "Para saber se o Crítico e a memória decidem melhor, comparamos quatro variantes em 12 cenários com dados reais, com gabaritos escritos e commitados antes de rodar: A, só o alocador; B, Planejador com o checador; C, o sistema completo; D, o completo sem memória. Medimos acerto nos gabaritos, alarmes falsos, o tempo médio de espera da população exposta e a variância em 3 execuções."

**Regra:** só mostrar números que estejam no `RELATORIO.md`. Se a tabela for do modo offline, dizer: "No modo offline os agentes são determinísticos, então isso valida o pipeline; a comparação que vale é no modo LLM." **[NIGHTSHIFT]** para a tabela do modo LLM. Se C não ganhar de B, dizer isso.

## 6. (3:30–3:45) Saída para o coordenador
**Tela:** `plano.md` rolando (justificativas com evidências `pop:`, `eta:`, `dist:`) e o mapa.
```bash
python -m app.cli aprovar --regiao tocantins --periodo 2026-10-23
```
**Fala:** "Nada é despachado sem aprovação. Cada designação traz a evidência, e o log mostra cada passo."

## 7. (3:45–4:00) Limitações e próximos passos
**Fala:** "Limitações: detecção não é incêndio; a exposição usa a população do município e fica superestimada; a distância é em linha reta com um fator; não validamos com operadores. Próximos passos: validar com o Corpo de Bombeiros do Tocantins e o PrevFogo, rotas reais, e as áreas protegidas."

---

## O que ficou de fora da seção 14 original (e por quê)
| Item da especificação | Situação |
|---|---|
| "Mesmo código, outra região" (Península Ibérica) | Só existe `config/regioes/iberia.yaml`; não há dados em cache nem execução. Não mostrar, a não ser que alguém rode de verdade antes de gravar. |
| SQL federada ao vivo no Zetaris | **[ZETARIS]**: só se o Zetaris real estiver no ar. |
| Nemotron respondendo, com `routed_model` | **[NIGHTSHIFT]**: obrigatório pelas regras ("one real request passing through Nightshift"); sem isso, o vídeo fica incompleto nesse requisito. |
