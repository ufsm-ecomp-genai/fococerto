Modo: **llm**

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 18/81 (22.2%) | 15/51 | 0/27 | 0/3 | 0 | 4.399 | 6.213 | 0.0 | 0/36 | 0.0 | 0.0 | 0 |
| **B** | 53/81 (65.4%) | 32/51 | 18/27 | 0/3 | 56 | 3.898 | 6.005 | 2.167 | 12/36 | 0.333 | 0.0175 | 2 |
| **C** | 66/87 (75.9%) | 36/51 | 24/30 | 0/6 | 54 | 3.771 | 5.96 | 2.611 | 18/36 | 0.5 | 0.0 | 2 |
| **D** | 64/87 (73.6%) | 37/51 | 21/30 | 0/6 | 47 | 3.762 | 5.877 | 2.528 | 16/36 | 0.444 | 0.0163 | 2 |

Por execução única (uma repetição dos cenários; o total acima soma as repetições):

| Variante | Média por execução | r1 / r2 / r3 | Mín–máx | Desvio (checagens) |
|---|---|---|---|---|
| **A** | 6.0/27 | 6/27 / 6/27 / 6/27 | 6–6 | 0.0 |
| **B** | 17.667/27 | 18/27 / 18/27 / 17/27 | 17–18 | 0.4714 |
| **C** | 22.0/29 | 22/29 / 22/29 / 22/29 | 22–22 | 0.0 |
| **D** | 21.333/29 | 22/29 / 21/29 / 21/29 | 21–22 | 0.4714 |

Escalação (somas sobre as execuções; definições em eval/README.md, "Sobre-escalação"):

| Variante | Ocorrências escaladas | Sobre-escaladas | Sem exposição | Com recurso livre viável | Só quebrando a reserva (info) | Com troca possível (info) | Citadas no motivo mas atendidas | Escalações sem alvo | Por impasse | Checagens que passaram só por escalar | Execuções com sobre-escalação |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/36 |
| **B** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 12 | 0 | 0/36 |
| **C** | 40 | 0 | 0 | 0 | 0 | 0 | 30 | 0 | 18 | 0 | 0/36 |
| **D** | 40 | 0 | 0 | 0 | 0 | 0 | 26 | 0 | 16 | 0 | 0/36 |

Por cenário (checagens; P = passou, F = falhou, – = não se aplica, ! = inválido; uma letra por repetição quando diferem):

| Cenário | A | B | C | D |
|---|---|---|---|---|
| agricola_recorrente_parana_24out | c1:F c2:– (ETA 1.2) | c1:F c2:– (ETA 1.2) | c1:P c2:F (ETA 1.207) | c1:P c2:F (ETA 1.207) |
| controle_taguatinga_liberada_21out | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.469) | c1:P c2:P (ETA 5.469) |
| controle_vegetacao_parana_19out | c1:– c2:P (ETA 1.772) | c1:– c2:PPF (ETA 1.712) | c1:P c2:F (ETA 1.406) | c1:P c2:F (ETA 1.298) |
| escalar_expostas_22out | c1:F c2:F (ETA 4.429) | c1:P c2:F (ETA 4.672) | c1:P c2:F (ETA 4.672) | c1:PFF c2:F (ETA 4.806) |
| excecao_dianopolis_ponte_18out | c1:F c2:P (ETA 4.687) | c1:F c2:P (ETA 3.925) | c1:P c2:P (ETA 4.567) | c1:P c2:P (ETA 4.533) |
| excecao_mateiros_alagada_23out | c1:F c2:P c3:P c4:F (ETA 8.39) | c1:P c2:F c3:P c4:F (ETA 8.491) | c1:P c2:F c3:P c4:F (ETA 8.491) | c1:F c2:P c3:P c4:F (ETA 8.39) |
| fato_errado_localidade_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 3.088) | c1:P c2:P c3:P (ETA 2.167) | c1:P c2:P c3:P (ETA 2.167) |
| fato_errado_populacao_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 2.167) | c1:P c2:P c3:P (ETA 2.167) | c1:P c2:P c3:P (ETA 2.167) |
| fato_errado_tendencia_23out | c2:F c3:F (ETA 5.547) | c2:F c3:F (ETA 3.088) | c2:P c3:P (ETA 2.167) | c2:P c3:P (ETA 2.167) |
| reignicao_conceicao_20out | c1:F c2:F (ETA 3.114) | c1:F c2:F (ETA 5.987) | c1:F c2:F (ETA 5.987) | c1:F c2:F (ETA 5.987) |
| reignicao_morros_24out | c1:F c2:F (ETA 0.58) | c1:P c2:P (ETA 0.58) | c1:P c2:P (ETA 0.58) | c1:P c2:P (ETA 0.58) |
| tradeoff_noite_gurupi_20out | c1:F c2:F c3:F (ETA 6.486) | c1:P c2:P c3:P (ETA 6.367) | c1:P c2:P c3:P (ETA 6.367) | c1:P c2:P c3:P (ETA 6.367) |
