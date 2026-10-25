Modo: **offline** (agentes offline determinísticos: validação do pipeline, não o resultado final)

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 0/12 (0.0%) | 0/6 | 0/6 | 0/0 | 0 | 1.847 | 4.058 | 0.0 | 0/6 | 0.0 | 0.0 | 0 |
| **B** | 0/12 (0.0%) | 0/6 | 0/6 | 0/0 | 0 | 1.847 | 4.058 | 1.0 | 3/6 | 2.0 | 0.0 | 0 |
| **C** | 0/12 (0.0%) | 0/6 | 0/6 | 0/0 | 0 | 1.847 | 4.058 | 1.5 | 3/6 | 2.0 | 0.0 | 0 |
| **D** | 0/12 (0.0%) | 0/6 | 0/6 | 0/0 | 0 | 1.847 | 4.058 | 1.5 | 3/6 | 2.0 | 0.0 | 0 |

Por execução única (uma repetição dos cenários; o total acima soma as repetições):

| Variante | Média por execução | r1 / r2 / r3 | Mín–máx | Desvio (checagens) |
|---|---|---|---|---|
| **A** | 0.0/4 | 0/4 / 0/4 / 0/4 | 0–0 | 0.0 |
| **B** | 0.0/4 | 0/4 / 0/4 / 0/4 | 0–0 | 0.0 |
| **C** | 0.0/4 | 0/4 / 0/4 / 0/4 | 0–0 | 0.0 |
| **D** | 0.0/4 | 0/4 / 0/4 / 0/4 | 0–0 | 0.0 |

Escalação (somas sobre as execuções; definições em eval/README.md, "Sobre-escalação"):

| Variante | Ocorrências escaladas | Sobre-escaladas | Sem exposição | Com recurso livre viável | Só quebrando a reserva (info) | Com troca possível (info) | Citadas no motivo mas atendidas | Escalações sem alvo | Por impasse | Checagens que passaram só por escalar | Execuções com sobre-escalação |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/6 |
| **B** | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/6 |
| **C** | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/6 |
| **D** | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/6 |

Por cenário (checagens; P = passou, F = falhou, – = não se aplica, ! = inválido; uma letra por repetição quando diferem):

| Cenário | A | B | C | D |
|---|---|---|---|---|
| reignicao_conceicao_20out_2p | c1:F c2:F (ETA 3.114) | c1:F c2:F (ETA 3.114) | c1:F c2:F (ETA 3.114) | c1:F c2:F (ETA 3.114) |
| reignicao_morros_24out_2p | c1:F c2:F (ETA 0.58) | c1:F c2:F (ETA 0.58) | c1:F c2:F (ETA 0.58) | c1:F c2:F (ETA 0.58) |
