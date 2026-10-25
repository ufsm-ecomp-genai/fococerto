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
- **avaliacao (pronto, commitado e3c95c9):** ablação offline A 22,2% / B 44,4% / C 62,1% / D 55,2%. Encontrou 7 bugs.
- **agentes-llm (pronto, b97dfe7):** os 7 bugs da ablação (lista em eval/RELATORIO.md), com testes em `tests/test_regressao_ablacao.py`; depois roda a ablação offline de novo e `scripts/gerar_exemplos.sh`.
- **docs-submissao (pronto, commitado):** README em inglês (com marcador `<!-- EVAL_RESULTS -->`), `docs/PATROCINADORES.md`, `docs/ROTEIRO-VIDEO.md`, `slides/conteudo.md`, `docs/FORMULARIO.md`

## Depois
- **Lacunas de produto:** (1) e (2) resolvidas (aprendizado automático, `scripts/demo_3_periodos.sh`, exemplo com o Analista). (3) A Ibéria continua sem cache.
- Colar a tabela da ablação em `<!-- EVAL_RESULTS -->` (README) e nos `[[...]]` dos slides; colar um log real do Nemotron em `<!-- NEMOTRON_LOG_EXCERPT -->`
- Ligar o Nightshift real e rodar a ablação no modo LLM
- Ligar o Zetaris real: `scripts/setup_zetaris.py` e depois `run` sem `--sample`

## Bloqueios externos (time)
- [ ] Zetaris rodando na máquina do time + `.env`
- [x] **Nightshift funcionando (25/10, ~01h UTC)** no PC Windows com NVIDIA da irmã do Enzo (`desktop-tlhi7b9`, Tailscale `100.90.123.23`, porta 8088 repassada só para `100.64.0.0/10`). Token = conteúdo do arquivo `proxy-token` (o da tela dá 401). Modelo: `nvidia/nemotron-3-ultra-550b-a55b`. O raciocínio é desligado com `chat_template_kwargs.enable_thinking=false`. Um período completo no modo LLM leva ~23 s.
- [ ] Respostas do Help Meterless (seção 19 da especificação)

## Infraestrutura (24/10, noite)
- O professor não respondeu. Plano B: servidor pessoal Debian 13 (12 threads, 15 GB, KVM, AMD RX 550, Tailscale 100.70.74.48). Passos: Docker → Zetaris → VM Windows 11 de avaliação para o Nightshift (teste: pode não rodar sem GPU NVIDIA) → opção C (provedor Runtime + Nemotron hospedado; elegível segundo a resposta da Meterless em chat5:1642, mas provavelmente perde o prêmio NVIDIA).

## Ablação no modo LLM
- Disparada em 25/10 ~01h55 UTC (`eval/run_ablacao.py --modo llm --repeticoes 3`), estimativa de 1 a 2 h. O PC da irmã precisa ficar ligado. Os resultados saem em `eval/resultados/<timestamp>_llm/`. Se for interrompida: rodar de novo (são independentes) ou reduzir com `--cenarios`/`--repeticoes 1`.
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
10. Antes de submeter: limpar este arquivo de notas internas (ex.: "PC da irmã").
