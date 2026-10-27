Modo: **llm**

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **C** | 9/12 (75.0%) | 6/7 | 2/4 | 0/1 | 17 | 3.509 | 5.658 | 2.6 | 4/5 | 4.4 | 0.0 | 0 |
| **D** | 9/12 (75.0%) | 7/7 | 1/4 | 0/1 | 6 | 3.134 | 5.031 | 2.4 | 4/5 | 4.2 | 0.0 | 0 |

Por execução única (uma repetição dos cenários; o total acima soma as repetições):

| Variante | Média por execução | r1 / r2 / r3 | Mín–máx | Desvio (checagens) |
|---|---|---|---|---|
| **C** | 9.0/12 | 9/12 | 9–9 | 0.0 |
| **D** | 9.0/12 | 9/12 | 9–9 | 0.0 |

Escalação (somas sobre as execuções; definições em eval/README.md, "Sobre-escalação"):

| Variante | Ocorrências escaladas | Sobre-escaladas | Sem exposição | Com recurso livre viável | Só quebrando a reserva (info) | Com troca possível (info) | Citadas no motivo mas atendidas | Escalações sem alvo | Por impasse | Checagens que passaram só por escalar | Execuções com sobre-escalação |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **C** | 22 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0/5 |
| **D** | 19 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 2 | 1 | 0/5 |

Por cenário (checagens; P = passou, F = falhou, – = não se aplica, ! = inválido; uma letra por repetição quando diferem):

| Cenário | C | D |
|---|---|---|
| controle_taguatinga_liberada_21out | c1:P c2:P (ETA 5.001) | c1:P c2:P (ETA 5.001) |
| excecao_dianopolis_ponte_18out | c1:F c2:P (ETA 3.261) | c1:F c2:P (ETA 2.544) |
| excecao_mateiros_alagada_23out | c1:P c2:P c3:P c4:P (ETA 5.635) | c1:F c2:P c3:P c4:P (ETA 4.9) |
| reignicao_conceicao_20out | c1:F c2:F (ETA 3.067) | c1:F c2:P (ETA 2.646) |
| reignicao_morros_24out | c1:P c2:P (ETA 0.58) | c1:P c2:P (ETA 0.58) |
