# Estado do trabalho (atualizado pelo líder a cada etapa)

> Para retomar numa sessão nova: leia este arquivo, `CLAUDE.md` e `docs/CONTRATOS.md`. Depois rode `git status`, `git log --oneline` e `.venv/bin/python -m pytest -q` para ver o estado real. O que estiver aqui como "em andamento" pode ter ficado pela metade.

Última atualização: 24/10/2026, ~19h UTC.

## Pronto (commitado)
- Estrutura do repositório, `CLAUDE.md`, `docs/CONTRATOS.md` (seções 1 a 11), as definições dos agentes em `.claude/agents/`
- `app/core/`: models.py, config.py, logging.py; `pyproject.toml`; `.venv` com as dependências
- **interface-ux (leva 1):** CLI, plano MD/JSON, mapa, 3 cenários (ids de base provisórios `osm_pendente_*`, trocar na integração). 12 testes.
- **hmem-engine (leva 1):** `services/hmem/` (conformidade 13/13, `npm test`), `app/memory_client.py` (`MemoriaLocal(caminho=...)` persistente + `ClienteHMEM`). 12 testes.

## Leva 1 (em andamento, sem commit)
| Agente | Tarefa | Estado | Próximo passo se interrompido |
|---|---|---|---|
| dados-zetaris | configs das regiões, ingestão FIRMS/GeoNames/OSM, lógica de ocorrências em Python, `data/cache/` do Tocantins, `REGIAO_7DIAS.md`, setup do Zetaris (não testado) | em andamento | conferir o que existe em `app/data/`, `scripts/`, `data/cache/` e continuar pela lista de prioridades do prompt (`.claude/agents/dados-zetaris.md`) |
| agentes-llm | `app/llm/client.py`, `app/tools/`, Planejador/Crítico/Analista, `app/agents/grafo.py`, testes com fakes em `tests/` | em andamento | rodar `pytest tests/test_tools_* tests/test_grafo.py` |

## Leva 2 (depois da integração da leva 1)
- Integração: rodar `python -m app.cli run --regiao tocantins --recursos cenarios/tocantins-escasso.yaml --sample` de ponta a ponta
- avaliacao: cenários e gabaritos **antes** de rodar; depois a ablação
- qa-integracao: teste a partir de um clone limpo, Dockerfile, checklist da submissão
- docs-submissao: README, patrocinadores, roteiro do vídeo, slides

## Bloqueios externos (time)
- [ ] Zetaris rodando na máquina do time + `.env`
- [ ] Nightshift: roda sem GPU dedicada? Porta 8088 acessível?
- [ ] Respostas do Help Meterless (seção 19 da especificação)
