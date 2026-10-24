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
- **avaliacao (em andamento):** cenários e gabaritos commitados ANTES de rodar (fcf42df); faltam `eval/run_ablacao.py`, `eval/RELATORIO.md` e `tests/test_eval.py`. Se interrompido: retomar e rodar a ablação offline com o código atual.
- **docs-submissao (em andamento):** README em inglês (com marcador `<!-- EVAL_RESULTS -->`), `docs/PATROCINADORES.md`, `docs/ROTEIRO-VIDEO.md`, `slides/conteudo.md`, `docs/FORMULARIO.md`

## Depois
- docs-submissao: README (em inglês), patrocinadores, roteiro do vídeo, slides (depois da ablação)
- Ligar o Nightshift real e rodar a ablação no modo LLM
- Ligar o Zetaris real: `scripts/setup_zetaris.py` e depois `run` sem `--sample`

## Bloqueios externos (time)
- [ ] Zetaris rodando na máquina do time + `.env`
- [ ] Nightshift: roda sem GPU dedicada? Porta 8088 acessível? Onde vêm o `routed_model` e o `receipt`?
- [ ] Respostas do Help Meterless (seção 19 da especificação)
