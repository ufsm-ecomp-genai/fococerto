Modo: **offline** (agentes offline determinísticos: validação do pipeline, não o resultado final)

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 18/81 (22.2%) | 15/51 | 0/27 | 0/3 | 0 | 4.399 | 6.213 | 0.0 | 0/36 | 0.0 | 0.0 | 0 |
| **B** | 57/81 (70.4%) | 36/51 | 18/27 | 0/3 | 0 | 4.365 | 6.121 | 1.0 | 33/36 | 5.0 | 0.0 | 0 |
| **C** | 72/87 (82.8%) | 39/51 | 27/30 | 0/6 | 0 | 3.29 | 6.035 | 1.75 | 33/36 | 5.25 | 0.0 | 0 |
| **D** | 54/87 (62.1%) | 33/51 | 15/30 | 0/6 | 3 | 2.945 | 5.795 | 1.917 | 33/36 | 5.083 | 0.0 | 0 |

Por execução única (uma repetição dos cenários; o total acima soma as repetições):

| Variante | Média por execução | r1 / r2 / r3 | Mín–máx | Desvio (checagens) |
|---|---|---|---|---|
| **A** | 6.0/27 | 6/27 / 6/27 / 6/27 | 6–6 | 0.0 |
| **B** | 19.0/27 | 19/27 / 19/27 / 19/27 | 19–19 | 0.0 |
| **C** | 24.0/29 | 24/29 / 24/29 / 24/29 | 24–24 | 0.0 |
| **D** | 18.0/29 | 18/29 / 18/29 / 18/29 | 18–18 | 0.0 |

Escalação (somas sobre as execuções; definições em eval/README.md, "Sobre-escalação"):

| Variante | Ocorrências escaladas | Sobre-escaladas | Sem exposição | Com recurso livre viável | Só quebrando a reserva (info) | Com troca possível (info) | Citadas no motivo mas atendidas | Escalações sem alvo | Por impasse | Checagens que passaram só por escalar | Execuções com sobre-escalação |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/36 |
| **B** | 180 | 0 | 0 | 0 | 18 | 0 | 0 | 0 | 0 | 3 | 0/36 |
| **C** | 186 | 0 | 0 | 0 | 9 | 3 | 3 | 0 | 3 | 6 | 0/36 |
| **D** | 180 | 0 | 0 | 0 | 9 | 3 | 3 | 0 | 3 | 6 | 0/36 |

Por cenário (checagens; P = passou, F = falhou, – = não se aplica, ! = inválido; uma letra por repetição quando diferem):

| Cenário | A | B | C | D |
|---|---|---|---|---|
| agricola_recorrente_parana_24out | c1:F c2:– (ETA 1.2) | c1:F c2:– (ETA 1.2) | c1:F c2:F (ETA 1.2) | c1:F c2:F (ETA 1.2) |
| controle_taguatinga_liberada_21out | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.001) | c1:P c2:P (ETA 5.001) |
| controle_vegetacao_parana_19out | c1:– c2:P (ETA 1.772) | c1:– c2:P (ETA 1.772) | c1:P c2:P (ETA 1.72) | c1:P c2:P (ETA 1.72) |
| escalar_expostas_22out | c1:F c2:F (ETA 4.429) | c1:P c2:P (ETA 4.429) | c1:P c2:P (ETA 4.425) | c1:P c2:P (ETA 4.425) |
| excecao_dianopolis_ponte_18out | c1:F c2:P (ETA 4.687) | c1:F c2:P (ETA 4.277) | c1:P c2:P (ETA 5.085) | c1:F c2:P (ETA 3.925) |
| excecao_mateiros_alagada_23out | c1:F c2:P c3:P c4:F (ETA 8.39) | c1:F c2:P c3:P c4:P (ETA 8.39) | c1:P c2:P c3:P c4:P (ETA 8.491) | c1:F c2:P c3:P c4:P (ETA 5.512) |
| fato_errado_localidade_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) | c1:P c2:P c3:P (ETA 2.272) | c1:P c2:P c3:P (ETA 2.272) |
| fato_errado_populacao_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) | c1:P c2:P c3:P (ETA 2.272) | c1:P c2:P c3:P (ETA 2.272) |
| fato_errado_tendencia_23out | c2:F c3:F (ETA 5.547) | c2:F c3:F (ETA 5.547) | c2:P c3:P (ETA 2.272) | c2:P c3:P (ETA 2.272) |
| reignicao_conceicao_20out | c1:F c2:F (ETA 3.114) | c1:P c2:P (ETA 3.114) | c1:P c2:P (ETA 3.114) | c1:F c2:F (ETA 3.114) |
| reignicao_morros_24out | c1:F c2:F (ETA 0.58) | c1:P c2:P (ETA 0.58) | c1:P c2:P (ETA 0.58) | c1:F c2:F (ETA 0.58) |
| tradeoff_noite_gurupi_20out | c1:F c2:F c3:F (ETA 6.486) | c1:F c2:F c3:F (ETA 6.486) | c1:F c2:F c3:F (ETA 3.045) | c1:F c2:F c3:F (ETA 3.045) |
