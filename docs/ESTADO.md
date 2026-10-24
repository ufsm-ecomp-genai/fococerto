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
- [ ] Nightshift: roda sem GPU dedicada? Porta 8088 acessível? Onde vêm o `routed_model` e o `receipt`?
- [ ] Respostas do Help Meterless (seção 19 da especificação)

## Infraestrutura (24/10, noite)
- O professor não respondeu. Plano B: servidor pessoal Debian 13 (12 threads, 15 GB, KVM, AMD RX 550, Tailscale 100.70.74.48). Passos: Docker → Zetaris → VM Windows 11 de avaliação para o Nightshift (teste: pode não rodar sem GPU NVIDIA) → opção C (provedor Runtime + Nemotron hospedado; elegível segundo a resposta da Meterless em chat5:1642, mas provavelmente perde o prêmio NVIDIA).
