# FocoCerto: regras do projeto (vale para todos os agentes)

Projeto do time UFSM para o Open Agent Hackathon 2026, Track 3 (Reasoning Architecture).
- Especificação completa: `../PROJETO-queimadas.md`. Leia as seções relevantes ao seu papel antes de começar.
- Interfaces entre módulos: `docs/CONTRATOS.md`. **Elas valem mais do que a sua preferência.**
- Regras oficiais do hackathon: `~/Downloads/genai-docs/rules/`.

**Prazo: terça, 27/10/2026, 23:45 UTC (20:45 em Brasília).** Priorize o que está como "Precisa ter" na seção 12 da especificação.

## Como trabalhamos
- **Cada agente só edita as pastas que são dele** (tabela abaixo). Se precisar mudar algo de outro dono ou um contrato, **não mude**: descreva a mudança no relatório final, e o líder (a sessão principal) decide.
- **Os contratos vêm primeiro.** Os tipos de `app/core/` e o `docs/CONTRATOS.md` são do líder. Implemente contra eles. Se algo de que você depende ainda não existe, use um *stub* com a mesma assinatura e avise no relatório.
- **Passos pequenos que funcionam.** Cada entrega precisa rodar. Nada de esqueleto que "vai funcionar depois".
- **Teste o que fizer**, com `pytest`, um script ou uma execução real, e diga como testou.
- **Nunca invente dados, números ou resultados.** Dados simulados ficam marcados como simulados. Se algo não foi testado, diga que não foi.

| Pasta | Dono |
|---|---|
| `app/core/`, `docs/CONTRATOS.md`, `CLAUDE.md`, `pyproject.toml` | líder (sessão principal) |
| `app/data/`, `sql/`, `scripts/ingest_*`, `config/regioes/`, `data/` | `dados-zetaris` |
| `app/agents/`, `app/tools/`, `app/llm/` | `agentes-llm` |
| `services/hmem/`, `app/memory_client.py` | `hmem-engine` |
| `eval/` | `avaliacao` |
| `app/cli.py`, `app/output/`, `web/`, `cenarios/` | `interface-ux` |
| `tests/`, `Dockerfile`, `.env.example`, `scripts/check_*` | `qa-integracao` |
| `README.md`, `docs/` (exceto CONTRATOS), `slides/` | `docs-submissao` |

## Regras do hackathon que não podem ser quebradas
- **Zetaris** é a camada de dados: os agentes consultam dados **pelo Zetaris**, não direto nas fontes. A exceção é a escrita (decisões e notas), que vai direto ao Postgres, porque o Zetaris é só leitura sobre as fontes.
- **Meterless Nightshift** é o provedor principal de IA. Toda chamada de LLM passa por `app/llm/client.py`. Ninguém chama a NVIDIA ou outro provedor direto do código dos agentes.
- **O H-MEM** precisa ter um papel real numa funcionalidade, e a suíte de conformidade precisa passar.
- **Logs:** todo evento relevante vira uma linha em `logs/<execucao>.jsonl` (formato em CONTRATOS), **incluindo qual modelo respondeu** (`modelo`, `routed_model`, `receipt`).
- **Sample mode** (`--sample`): roda sem Zetaris, Nightshift ou chaves, com **lógica real** sobre dados em cache e agentes offline determinísticos. **É proibido** mapear uma entrada conhecida para uma saída pronta.
- **Nada de segredos no código.** Configuração vem de variáveis de ambiente, e o `.env.example` só tem valores de exemplo.
- **Nada de caminhos de demo fixos no código** (if cenário == demo …).

## Stack
- App: **Python 3.12**, LangGraph, httpx, pydantic, pytest. Rodar com `python -m app.cli`.
- H-MEM: **TypeScript** (referência oficial em `../02-meterless-engines/Meterless`), exposto como serviço HTTP em `services/hmem/`.
- Dados: Postgres + Zetaris (Docker). Credenciais no `.env` (veja `.env.example`).

## Relatório final de cada agente (obrigatório)
Termine sempre com:
1. **Feito:** arquivos criados ou alterados.
2. **Como testei:** comando e resultado real (se falhou, mostre a falha).
3. **Pendências e bloqueios:** inclusive o que depende de outro agente.
4. **Pedidos de mudança de contrato:** se houver.
