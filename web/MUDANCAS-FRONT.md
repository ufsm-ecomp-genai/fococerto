# Mudanças no front-end antes da entrega (27/10)

Revisão feita em 26/10 à noite sobre o commit `a653e5f` (modo claro/escuro), com o build servido pela API atual
da `main` e navegado em 1440 px e 390 px. **O que está bom:** build e testes passam (15/15), não quebra no celular,
usa a API real, o fluxo "Recursos do dia → organizar → revisar → gerar plano" funciona de ponta a ponta, exemplos
não podem ser aprovados, o selo de simulado aparece e o modo escuro ficou bom. Nada disso precisa mudar.

O problema principal é **excesso de informação**: a Visão geral tem **4.468 px de altura** (umas 5 telas). O
coordenador precisa responder em 5 segundos "o que eu tenho que decidir agora", e hoje o mapa só aparece depois de
9 parágrafos de escalação. Product & UX vale 10 pontos e é julgado por "how intuitive … for its intended users".

Ordem de prioridade: faça de cima para baixo e pare onde o tempo acabar.

---

## 1. Visão geral em uma tela (o mais importante, ~2–3 h)

Hoje as escalações aparecem **4 vezes** (banner "Atenção do coordenador", lista "Escalações", 9 linhas "Sem
recurso" na tabela de ordem, quadro "Ocorrências não atendidas") e o selo de simulado aparece 2 vezes.

Layout proposto, sem rolar em 1440×900:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Tocantins · 2026-10-23 · [exemplo ▾]          ● simulado     ☀  EN ▾        │
│ 6 equipes designadas · 9 ocorrências precisam de você · 0 em reserva         │  ← uma linha de status
├───────────────────────────────────────────────┬──────────────────────────────┤
│                                               │ PRECISAM DE VOCÊ (9)         │
│                                               │ ▸ Gurupi        87.545  0.66 │  ← ordenado por população
│                  MAPA (grande)                │ ▸ F. Tabocão    29.357  0.61 │     clicar: abre o motivo
│                                               │ ▸ Morros         4.829  0.60 │     completo e centraliza
│                                               │   … ver todas                │     o mapa
│                                               │──────────────────────────────│
│                                               │ [Aprovar plano] [Nota]       │
├───────────────────────────────────────────────┴──────────────────────────────┤
│ [Ordem de recursos] [Raciocínio] [Trace]        ← abas, abaixo da dobra      │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Tirar:** o bloco "Central de operações" com os slogans ("Priorize ocorrências…", "Inteligência para agir",
  "Cada recurso, no lugar certo") — ocupa o topo e não ajuda quem opera; o banner "Atenção do coordenador" (vira a
  linha de status); o quadro "Ocorrências não atendidas" (são as escalações); os cards de reserva quando a reserva
  está vazia; um dos dois selos de simulado (manter o da linha de status; o texto longo pode ir num tooltip).
- **Escalações compactas:** localidade, população, prioridade. O `motivo` completo só ao expandir. O motivo agora
  diz quem poderia ter chegado e para onde foi (ex.: *"Could reach it within the 6 h limit: palmas-a1 (1.0 h;
  assigned to the incident near Santa Tereza do Tocantins (2463 people)) …"*), então ele é útil, mas é longo.
- **Aba "Ordem de recursos":** abrir no filtro **Designadas** (as sem recurso já estão na coluna da direita).

## 2. Abrir em inglês, no exemplo real em inglês (~15 min)

Os juízes são internacionais. Hoje abre em PT-BR com `tocantins-escasso-real`.
- Idioma inicial: o do navegador (`navigator.language`); se não começar com `pt`, usar EN.
- Exemplo inicial: `tocantins-escasso-real-en` (execução real de 26/10: Zetaris + Nemotron + H-MEM, escalações
  explicadas). Em PT, pode continuar `tocantins-escasso-real`.

## 3. Números no formato do idioma (~15 min)

Em EN aparece "up to 87.545 residents" (separador de milhar do português). Todo `toLocaleString()` sem argumento
(ex.: `MapaPlano.jsx`, popup do mapa) deve receber o locale da interface (`en-US` / `pt-BR`), como já faz o
`num()` do `AppNovo.jsx`.

## 4. Separar o resumo do Planejador (~30 min)

Em "Raciocínio"/"Ler análise completa", `plano.resumo` aparece num bloco só. O `plano.md` já separa; façam igual:
- `" Desvios do baseline: "` ou `" Deviations from the baseline: "` → lista, itens separados por `" | "`;
- `" Respostas ao Crítico: "` ou `" Replies to the Critic: "` → lista, uma resposta por item, no formato
  `<ponto do Crítico> -> <decisão> (<motivo>)`; destaquem a decisão.

Os dois marcadores podem faltar (rodada 1, modo offline). A lógica de referência, com testes, está em
`app/output/comum.py` (`dividir_resumo`, `partes_resposta`) na `main`.

## 5. Limpeza do código (~15 min)

- **Apagar o código morto:** `App.jsx`, `Map.jsx` e `i18n.js` (só `AppNovo.jsx`, `MapaPlano.jsx` e `i18nNovo.js`
  são usados). Um juiz que abrir a pasta vai estranhar duas versões.
- **Formatar:** `AppNovo.jsx` tem ~34 KB em 92 linhas (linhas de milhares de caracteres), parece minificado.
  `npx prettier --write "src/**/*.{js,jsx,css}" "tema/**/*.js" "tests/**/*.js"` resolve em segundos. Rodem os
  testes depois.

## 6. O que NÃO mudar

- O contrato da API e o formato do `plano.json` (a `main` não mudou nada nele hoje; o texto das escalações mudou,
  os campos não).
- `sample: true` como padrão do formulário (quem avalia não tem as chaves).
- O selo de recursos simulados e o aviso de que aprovar não despacha equipes.

## Do lado do backend (Enzo, não é com vocês)

- `POST /api/aprovar` ainda não grava `meta.aprovacao_humana` no plano (o `RUNNING.md` de vocês já anota isso).
- Se ajudar o item 1, a API pode devolver em cada escalação um campo extra com a lista estruturada de "quem
  poderia chegar" (recurso, ETA, para onde foi), para vocês não precisarem cortar o texto. É um campo a mais,
  não quebra nada: peçam se quiserem.
- Login: decidido **não** fazer agora (ver abaixo).

## Login?

Não para a entrega. Os juízes precisam abrir e usar sem credenciais, e um login de mentira não protege nada. O que
protege hoje: o `compose.yaml` publica a porta só em `127.0.0.1`, a API só aceita CORS de localhost e o padrão é o
modo de amostra (sem chamar Nightshift nem gravar no Postgres). **Não publiquem a porta 8000 na internet.** No
README fica declarado como limitação: protótipo de um usuário, local; em produção entraria autenticação da
instituição (SSO) e perfis por cargo, que já estão nos próximos passos.

## Quando terminarem

Avisem no grupo. O Enzo faz o merge da `front-end` na `main`, commita o build em `web/dist` e atualiza o README
com o jeito de abrir a interface (`docker compose -f web/compose.yaml up -d --build` → http://localhost:8000).
