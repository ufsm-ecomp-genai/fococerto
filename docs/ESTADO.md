# Estado do trabalho

> Para retomar numa sessão nova: leia este arquivo, `CLAUDE.md` e `docs/CONTRATOS.md`. Depois rode `git status`,
> `git log --oneline` e `.venv/bin/python -m pytest -q` para ver o estado real.

Última atualização: 26/10/2026, ~21h40 (Brasília). Entrega: **27/10, 23:45 UTC (20:45 Brasília); alvo: ~18h**.

## Pronto (na `main`)
- Pipeline completo: dados reais (NASA FIRMS, GeoNames, OSM, Open-Meteo, 12 bases oficiais do Tocantins com fonte),
  Planejador ⇄ Crítico ⇄ Analista (LangGraph), checagem de regras, citações, ids inventados e coberturas falsas,
  escalação obrigatória que diz quem poderia ter ido (`escalacoes[].alcance`), plano em PT ou EN, mapa, API HTTP.
- Patrocinadores funcionando de verdade: Zetaris 2.4 (4 views, 698 ocorrências iguais ao Python), H-MEM
  (conformidade 13/13), Nightshift + Nemotron 3 Ultra (recibo assinado por chamada, escopo isolado por execução).
- Execuções reais de ponta a ponta: `output_examples/tocantins-escasso-real-en/` (26/10) e `-real/` (25/10).
- Avaliação oficial: ablação LLM limpa `eval/resultados/20261026T234558Z_llm/` (A 22,2 · B 63,0 · C 82,8 · D 79,3)
  e offline `20261026T225811Z_offline/` (22,2 · 70,4 · 82,8 · 62,1). Detalhes e histórico em `eval/RELATORIO.md`.
- Achado: o escopo `user` do Nightshift injeta ~4.900 tokens de contexto lembrado; corrigido (commit `73aed60`).
- 331 testes passam (1 pulado: precisa de um Postgres descartável); `check_submissao.py` 17 OK.
- Deck (Artifact Slides, privado) atualizado até a rodada limpa; banner do time feito (fora do repositório).

## Em andamento (time)
- **Front-end** na branch `front-end`: tarefas em `web/MUDANCAS-FRONT.md` (Visão geral em uma tela, abrir em EN,
  números no idioma, resumo dividido, limpeza). Eles começam com `git merge origin/main`.
- **Teste de juiz** num clone limpo, na máquina de outro colega, seguindo só o README.
- **Vídeo**: roteiro em `docs/ROTEIRO-VIDEO.md` (números da rodada limpa), narração em inglês.

## Fila para 27/10
1. Merge da `front-end` na `main`; build em `web/dist`; README com `docker compose -f web/compose.yaml up -d --build`.
2. Slide da demo alinhado ao que o vídeo mostra; exportar o deck (PDF/PPTX) para o HackOS.
3. Opcional, com os servidores ligados: refazer a execução real em EN para ela ter `escalacoes[].alcance`.
4. Revisão de segredos no histórico, repositório público, formulário (`docs/FORMULARIO.md`, preencher `[[...]]`),
   submissão no HackOS com margem.

## Limitações conhecidas (estão no README)
- Quantidade de equipes por base é simulada; não validado com operadores.
- `pop_raio` usa a população do município (superestima perto de cidades).
- Restrição de memória é regra não rígida: em Mateiros o Planejador pode devolver a equipe bloqueada e o Crítico
  aprovar (visto nas rodadas de 25/10).
- Ablação LLM limpa com 1 repetição; avaliação roda em português.
