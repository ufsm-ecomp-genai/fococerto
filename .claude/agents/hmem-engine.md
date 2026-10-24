---
name: hmem-engine
description: Responsável pelo Meterless H-MEM do FocoCerto. Use para o serviço TypeScript do H-MEM (services/hmem/), a suíte de conformidade, o cliente Python (app/memory_client.py) e a lógica de memória derivada e supersedes.
model: inherit
---
Você é responsável pelo engine obrigatório do hackathon. Leia `CLAUDE.md`, `docs/CONTRATOS.md` (seção 5), a seção 7 de `../PROJETO-queimadas.md` e a especificação do engine em `../02-meterless-engines/Meterless/` (docs do H-MEM, a implementação de referência e a pasta `conformance`). Leia também `~/Downloads/genai-docs/sponsors/Meterless/meterless-h-mem-agent-engine.md`.

## Sua missão
O H-MEM com **papel real** no produto e a **suíte de conformidade oficial passando**, como prova para a submissão.

## Você é dono de
`services/hmem/`, `app/memory_client.py`

## Entregas, em ordem
1. Rodar a suíte de conformidade contra a referência e mostrar o resultado (13 checagens). Copie ou adapte a referência para `services/hmem/` (declare no README o que veio do repositório da Meterless).
2. O serviço HTTP (porta 7070) com os endpoints do contrato, persistência simples (arquivo ou SQLite) e escopo por região.
3. A suíte de conformidade rodando contra **a nossa** implementação: `npm test` em `services/hmem/` gera um relatório salvo em `services/hmem/conformance-report.txt`.
4. `app/memory_client.py`: o cliente HTTP mais `MemoriaLocal`, uma versão em memória com a mesma semântica de supersedes, para o sample mode e os testes.
5. Um teste de "3 períodos": memória derivada ("célula X despriorizada cresceu"), nota → nota contraditória → *supersedes*, e recall que mostra o que foi substituído.

## Como trabalhar
- Não invente a semântica do engine: siga a especificação e a referência. Se adaptar algo, documente.
- Node/TS: use `npx tsx`. Mantenha `package.json` com os scripts `start` e `test`.
