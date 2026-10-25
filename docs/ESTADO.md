# Estado do trabalho (atualizado pelo líder a cada etapa)

> Para retomar numa sessão nova: leia este arquivo, `CLAUDE.md` e `docs/CONTRATOS.md`. Depois rode `git status`, `git log --oneline` e `.venv/bin/python -m pytest -q` para ver o estado real. O que estiver aqui como "em andamento" pode ter ficado pela metade.

Última atualização: 24/10/2026, ~22h30 UTC.

## Pronto (commitado)
- Estrutura, `CLAUDE.md`, contratos (seções 1 a 13), agentes em `.claude/agents/`, `app/core/`
- **interface-ux:** CLI, plano MD/JSON, mapa, 3 cenários do Tocantins (período 2026-10-23)
- **hmem-engine:** `services/hmem/` (conformidade 13/13, `npm test`), `app/memory_client.py`
- **agentes-llm:** cliente LLM (Nightshift **não testado**), ferramentas, Planejador/Crítico/Analista, grafo
- **dados-zetaris:** ingestão, ocorrências e prioridade, `data/cache/tocantins` (dados reais de 17 a 24/10), views do Zetaris validadas em Spark (**não testadas no Zetaris**)
- **Integração:** `python -m app.cli run --regiao tocantins --recursos cenarios/tocantins-escasso.yaml --sample` roda de ponta a ponta (6 designações, 9 escaladas). 99 testes passam e 1 é pulado (precisa do Postgres de teste).

## Decisões da integração
- O OSM tem só 2 bases dentro do TO, as duas em Palmas. Os cenários declaram as bases do coordenador (`Cenario.bases`) em cidades reais, marcadas `simulada: true`.
- Período da demo: 2026-10-23 (179 ocorrências, 52 com localidade a < 15 km).

## Limitações conhecidas (vão para o README)
- `pop_raio` soma a população do GeoNames, que muitas vezes é a do município inteiro e não só a da sede. Isso superestima a exposição perto de cidades médias (ex.: Porto Nacional 53 mil).
- O Planejador offline é igual ao baseline (alocador simples). As diferenças entre as variantes da ablação aparecem no modo LLM.
- TI/UC não foram ingeridos (`dist_ti_uc_km` fica nulo).

## Leva 2
- **qa-integracao (pronto):** 44 testes de integração e anti-trapaça, Docker (build e run testados), `.env.example`, `scripts/check_clean_clone.sh`, `scripts/check_submissao.py`
- **Correções do líder (commitadas):** recall do H-MEM com uma consulta por termo (a nota não voltava), `status` preenchido, escalação que não esconde ocorrências expostas, `pyproject` instalável
- **Exemplos:** `input_examples/` e `output_examples/` (4 saídas, com trace), gerados por `scripts/gerar_exemplos.sh`
- **avaliacao (pronto, commitado 87a8336):** ablação offline A 22,2% / B 44,4% / C 62,1% / D 55,2%. Encontrou 7 bugs.
- **agentes-llm (pronto, 39e42d2):** os 7 bugs da ablação (lista em eval/RELATORIO.md), com testes em `tests/test_regressao_ablacao.py`; depois roda a ablação offline de novo e `scripts/gerar_exemplos.sh`.
- **docs-submissao (pronto, commitado):** README em inglês (com marcador `<!-- EVAL_RESULTS -->`), `docs/PATROCINADORES.md`, `docs/ROTEIRO-VIDEO.md`, `slides/conteudo.md`, `docs/FORMULARIO.md`

## Depois
- **Lacunas de produto:** (1) e (2) resolvidas (aprendizado automático, `scripts/demo_3_periodos.sh`, exemplo com o Analista). (3) A Ibéria continua sem cache.
- Colar a tabela da ablação em `<!-- EVAL_RESULTS -->` (README) e nos `[[...]]` dos slides; colar um log real do Nemotron em `<!-- NEMOTRON_LOG_EXCERPT -->`
- Ligar o Nightshift real e rodar a ablação no modo LLM
- Ligar o Zetaris real: `scripts/setup_zetaris.py` e depois `run` sem `--sample`

## Bloqueios externos (time)
- [ ] Zetaris rodando na máquina do time + `.env`
- [x] **Nightshift funcionando (25/10, ~01h UTC)** numa máquina Windows do time com GPU NVIDIA, via Tailscale. Detalhes de acesso: `docs/INFRA-local.md` (fora do git). Token = arquivo `proxy-token`; modelo `nvidia/nemotron-3-ultra-550b-a55b`; raciocínio desligado com `enable_thinking=false`.
- [ ] Respostas do Help Meterless (seção 19 da especificação)

## Infraestrutura (24/10, noite)
- Zetaris: no servidor Debian do time (detalhes em `docs/INFRA-local.md`, fora do git). Bloqueio atual: acesso ao registro de imagens da Zetaris ainda não ativado.

## Ablação no modo LLM
- Disparada em 25/10 ~01h55 UTC (`eval/run_ablacao.py --modo llm --repeticoes 3`), estimativa de 1 a 2 h. A máquina do Nightshift precisa ficar ligada. Os resultados saem em `eval/resultados/<timestamp>_llm/`. Se for interrompida: rodar de novo (são independentes) ou reduzir com `--cenarios`/`--repeticoes 1`.
- **Decisão do time (25/10):** toda ocorrência com população exposta que ficar sem recurso vira escalação obrigatória ("solicitar apoio externo"), também no modo LLM. Aplicar DEPOIS que a ablação LLM em andamento terminar e rodar a ablação de novo com a regra nova.

## Fila de correções de código (revisão do juiz, 25/10; aplicar DEPOIS da ablação LLM em andamento)
1. Escalação obrigatória de ocorrência exposta sem recurso (decisão do time) + teste.
2. Crítico: regra de troca "recurso local ocioso × ocorrência exposta não atendida" (ex.: output_examples/tocantins-folgado: cel_-117_-469, 22 mil hab. a 4,6 km de Dianópolis, escalada enquanto dianopolis-t1/t2 vão para longe).
3. Métrica de sobre-escalação na ablação (os gabaritos favorecem quem escala tudo); reportar também por /27 (as repetições offline são determinísticas).
4. Reignição em 2 períodos com a memória gerada pelo aprendizado.py (hoje a memória vem escrita no cenário).
5. Analista no modo LLM recebe `sinais_heuristicos` com a conclusão pronta: medir a divergência ou tirar esse campo.
6. `app.cli avaliar` quebrado (roda o script por caminho, ModuleNotFoundError; argumentos incompatíveis).
7. Sample mode com H-MEM real (flag `--hmem`) ou documentar o caminho.
8. `npm test` regrava conformance-report.txt (versionado).
9. **Execução real de ponta a ponta** (Zetaris + Nightshift + H-MEM) commitada em output_examples/tocantins-escasso-real/ com trace; é a mudança de maior impacto segundo o juiz.
10. Antes de submeter: revisar este arquivo (notas internas).
11. **README: seção "AI and Model Usage"** (exigida em rules/ai-usage-policy.md §6): modelos pelo Nightshift e o papel de cada um, frameworks, integração com os patrocinadores, **a ferramenta de IA usada para programar (Claude Code)**, bibliotecas, fontes de dados e o que é simulado, código adaptado, limitações, sample mode.
12. **`SAMPLE_MODE=true` por variável de ambiente** (rules/submission-requirements.md §3.3); hoje só existe `--sample`.
