Modo: **llm**

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 6/27 (22.2%) | 5/17 | 0/9 | 0/1 | 0 | 4.399 | 6.213 | 0.0 | 0/12 | 0.0 | 0.0 | 0 |
| **B** | 17/27 (63.0%) | 11/17 | 5/9 | 0/1 | 10 | 3.869 | 5.955 | 1.333 | 11/12 | 5.0 | 0.0 | 0 |
| **C** | 24/29 (82.8%) | 15/17 | 7/10 | 0/2 | 12 | 2.759 | 5.706 | 2.167 | 11/12 | 5.0 | 0.0 | 0 |
| **D** | 23/29 (79.3%) | 15/17 | 6/10 | 0/2 | 14 | 3.059 | 5.569 | 2.25 | 11/12 | 5.0 | 0.0 | 0 |

Por execução única (uma repetição dos cenários; o total acima soma as repetições):

| Variante | Média por execução | r1 / r2 / r3 | Mín–máx | Desvio (checagens) |
|---|---|---|---|---|
| **A** | 6.0/27 | 6/27 | 6–6 | 0.0 |
| **B** | 17.0/27 | 17/27 | 17–17 | 0.0 |
| **C** | 24.0/29 | 24/29 | 24–24 | 0.0 |
| **D** | 23.0/29 | 23/29 | 23–23 | 0.0 |

Escalação (somas sobre as execuções; definições em eval/README.md, "Sobre-escalação"):

| Variante | Ocorrências escaladas | Sobre-escaladas | Sem exposição | Com recurso livre viável | Só quebrando a reserva (info) | Com troca possível (info) | Citadas no motivo mas atendidas | Escalações sem alvo | Por impasse | Checagens que passaram só por escalar | Execuções com sobre-escalação |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/12 |
| **B** | 59 | 0 | 0 | 0 | 6 | 0 | 0 | 1 | 1 | 1 | 0/12 |
| **C** | 60 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 2 | 0/12 |
| **D** | 57 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 2 | 2 | 0/12 |

Por cenário (checagens; P = passou, F = falhou, – = não se aplica, ! = inválido; uma letra por repetição quando diferem):

| Cenário | A | B | C | D |
|---|---|---|---|---|
| agricola_recorrente_parana_24out | c1:F c2:– (ETA 1.2) | c1:F c2:– (ETA 1.2) | c1:F c2:F (ETA 1.2) | c1:F c2:F (ETA 1.339) |
| controle_taguatinga_liberada_21out | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 4.822) | c1:P c2:P (ETA 5.001) | c1:P c2:P (ETA 5.001) |
| controle_vegetacao_parana_19out | c1:– c2:P (ETA 1.772) | c1:– c2:P (ETA 1.772) | c1:P c2:P (ETA 1.772) | c1:P c2:P (ETA 1.72) |
| escalar_expostas_22out | c1:F c2:F (ETA 4.429) | c1:P c2:P (ETA 4.429) | c1:P c2:P (ETA 4.003) | c1:P c2:P (ETA 4.425) |
| excecao_dianopolis_ponte_18out | c1:F c2:P (ETA 4.687) | c1:F c2:P (ETA 3.261) | c1:F c2:P (ETA 3.261) | c1:F c2:P (ETA 2.176) |
| excecao_mateiros_alagada_23out | c1:F c2:P c3:P c4:F (ETA 8.39) | c1:F c2:P c3:P c4:P (ETA 7.439) | c1:P c2:P c3:P c4:P (ETA 5.635) | c1:F c2:P c3:P c4:P (ETA 4.9) |
| fato_errado_localidade_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) | c1:P c2:P c3:P (ETA 2.272) | c1:P c2:P c3:P (ETA 1.955) |
| fato_errado_populacao_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 2.234) | c1:P c2:P c3:P (ETA 2.056) | c1:P c2:P c3:P (ETA 3.199) |
| fato_errado_tendencia_23out | c2:F c3:F (ETA 5.547) | c2:F c3:F (ETA 5.547) | c2:P c3:P (ETA 2.056) | c2:P c3:P (ETA 2.272) |
| reignicao_conceicao_20out | c1:F c2:F (ETA 3.114) | c1:F c2:F (ETA 3.114) | c1:F c2:F (ETA 2.995) | c1:F c2:F (ETA 3.067) |
| reignicao_morros_24out | c1:F c2:F (ETA 0.58) | c1:P c2:P (ETA 0.58) | c1:P c2:P (ETA 0.58) | c1:P c2:P (ETA 0.58) |
| tradeoff_noite_gurupi_20out | c1:F c2:F c3:F (ETA 6.486) | c1:F c2:F c3:F (ETA 6.486) | c1:P c2:P c3:P (ETA 2.28) | c1:P c2:P c3:P (ETA 6.076) |
