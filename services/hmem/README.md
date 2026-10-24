# services/hmem: o H-MEM do FocoCerto

Serviço HTTP (TypeScript, Node 24, porta 7070) que expõe o **Meterless H-MEM** para os agentes do FocoCerto. O engine é a **implementação de referência oficial da Meterless**, copiada para `src/engine/` (Apache-2.0; origem, commit e alterações em `NOTICE`). O serviço não chama nenhum modelo: o `HMEM` é criado sem `minerFn`, então o engine fica no caminho determinístico.

## Rodar

```bash
npm ci          # uma vez (só instala o tsx)
npm start       # http://127.0.0.1:7070
npm test        # suíte de conformidade oficial contra src/engine -> conformance-report.txt
```

| Variável | Padrão | |
|---|---|---|
| `HMEM_PORT` | `7070` | |
| `HMEM_HOST` | `127.0.0.1` | |
| `HMEM_DATA_DIR` | `services/hmem/data` | `:memory:` desliga a persistência |
| `HMEM_POLITICA_NOTAS` | `coordenador_mais_recente` | ou `fila` (só o engine; veja abaixo) |

## Endpoints (docs/CONTRATOS.md, seção 5)

```
GET  /health                       -> {ok: true}
POST /memorias {regiao, texto, tipo, fonte, confianca?, supersedes?} -> Memoria + {substituida_por, conflitos}
POST /recall   {regiao, consulta, k?}  -> {memorias, substituidas, trace}
GET  /memorias?regiao=..           -> [Memoria]
GET  /ledger?regiao=..             -> ledger de auditoria do engine (extra)
GET  /conflitos?regiao=..          -> conflitos na fila (extra)
```

- **Ids:** `<regiao>:mem-<n>`. `supersedes` precisa ser da mesma região (400) e existir (404).
- **Escopo por região:** uma instância `HMEM` por região, com `data/<regiao>/state.json` e `data/<regiao>/ledger.jsonl` (a persistência JSON do próprio engine). Ranking e conflitos nunca cruzam regiões.
- **Mapeamento:** `texto`→`content`, `fonte`→`source`, `confianca`→`confidence`, `tipo`→tag `tipo:<tipo>` (o `type` do engine é `factual` e a camada é `working`), origem `manual` para nota e `plan_completion` para derivada.

## Semântica de supersedes e conflito

Tudo vem do engine, exceto os pontos marcados como **adaptação**.

1. **Ranking** (engine): fórmula híbrida canônica, penalidade de −0.20 para quem tem `supersededBy`, limiar de 0.35 na nota final e top-N = `k`. Nada é apagado.
2. **`supersedes` explícito** (adaptação no serviço): o engine guarda `supersedes` como aresta, mas só aplica a penalidade a `supersededBy`, que na referência só a resolução de conflito preenche. O serviço faz `store.update(antiga, {supersededBy: nova})` (fica no ledger com estado anterior e novo), para a memória substituída cair no ranking.
3. **Detecção automática de supersedes** (engine): similaridade > 0.85 mais linguagem de correção. **Adaptação:** termos em português ("na verdade", "em vez de", "deixou de"...), testados em texto sem acentos.
4. **Conflito** (engine): a cada gravação, `scanFor(nova)` checa os pares com a memória nova (pares opostos, números divergentes) e chama `autoResolve`, que só resolve com confiança de decisão ≥ 0.70. **Adaptação:** pares opostos em português (`alagada/bloqueada/interditada/fechada` × `liberada/aberta/desbloqueada`, `sempre/nunca`, `disponível/indisponível`...).
5. **Política do coordenador** (adaptação, desligável com `HMEM_POLITICA_NOTAS=fila`): na prática, o gate de 0.70 põe na fila quase todo conflito entre duas notas parecidas, porque a margem entre elas é pequena. A especificação headless manda esses casos para um supervisor. Aqui, quando o engine enfileira um conflito entre uma nota nova e uma nota anterior do coordenador, a nota nova vence: a anterior recebe `supersededBy` via `resolveBySupervisor` (ledger `conflict_resolved` com o ator `supervisor:<fonte>`), e a nova passa a ter `supersedes`.
6. **Recall:** `memorias` são as recuperadas sem `supersededBy`, em ordem de relevância. `substituidas` são as recuperadas com `supersededBy` mais, recursivamente, as que foram substituídas por alguma recuperada. Como o top-N inclui substituídas, `memorias` pode ter menos que `k` itens.

Limitações: a fila de conflitos não é persistida pelo engine (some ao reiniciar); o embedder é o mock determinístico da referência (hash de tokens), então a similaridade é lexical, não semântica.

## Conformidade

`npm test` roda `conformance/runner.ts` (cópia sem alterações) com `HMEM_IMPL=src/engine/index.ts`, o mesmo engine que o servidor usa, e salva a saída em `conformance-report.txt`. Resultado atual: 13/13. As adaptações não mudam nada em texto ASCII, então os vetores oficiais continuam passando.

O cliente Python (`app/memory_client.py`) tem `ClienteHMEM` (este serviço) e `MemoriaLocal`, uma tradução para Python do engine e desta camada, verificada contra o serviço em `tests/test_memoria.py::test_local_e_servico_concordam`.
