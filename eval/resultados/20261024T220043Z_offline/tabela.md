Modo: **offline** (agentes offline determinísticos: validação do pipeline, não o resultado final)

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 18/81 (22.2%) | 15/51 | 0/27 | 0/3 | 0 | 4.399 | 6.213 | 0.0 | 0/36 | 0.0 | 0.0 | 0 |
| **B** | 36/81 (44.4%) | 21/51 | 12/27 | 0/3 | 9 | 4.365 | 6.121 | 2.0 | 15/36 | 0.417 | 0.0 | 0 |
| **C** | 54/87 (62.1%) | 24/51 | 24/30 | 0/6 | 3 | 4.441 | 6.279 | 1.0 | 36/36 | 4.5 | 0.0 | 0 |
| **D** | 48/87 (55.2%) | 24/51 | 18/30 | 0/6 | 3 | 4.365 | 6.121 | 1.0 | 36/36 | 4.333 | 0.0 | 0 |

Por cenário (checagens; P = passou, F = falhou, – = não se aplica, ! = inválido; uma letra por repetição quando diferem):

| Cenário | A | B | C | D |
|---|---|---|---|---|
| agricola_recorrente_parana_24out | c1:F c2:– (ETA 1.2) | c1:F c2:– (ETA 1.2) | c1:F c2:P (ETA 1.2) | c1:F c2:P (ETA 1.2) |
| controle_taguatinga_liberada_21out | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.493) |
| controle_vegetacao_parana_19out | c1:– c2:P (ETA 1.772) | c1:– c2:P (ETA 1.772) | c1:P c2:P (ETA 1.772) | c1:P c2:P (ETA 1.772) |
| escalar_expostas_22out | c1:F c2:F (ETA 4.429) | c1:F c2:F (ETA 4.429) | c1:P c2:P (ETA 4.429) | c1:P c2:P (ETA 4.429) |
| excecao_dianopolis_ponte_18out | c1:F c2:P (ETA 4.687) | c1:F c2:P (ETA 4.277) | c1:P c2:P (ETA 5.085) | c1:F c2:P (ETA 4.277) |
| excecao_mateiros_alagada_23out | c1:F c2:P c3:P c4:F (ETA 8.39) | c1:F c2:P c3:P c4:F (ETA 8.39) | c1:P c2:P c3:P c4:P (ETA 8.491) | c1:F c2:P c3:P c4:P (ETA 8.39) |
| fato_errado_localidade_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) | c1:P c2:P c3:F (ETA 5.547) | c1:P c2:P c3:F (ETA 5.547) |
| fato_errado_populacao_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) | c1:P c2:P c3:F (ETA 5.547) | c1:P c2:P c3:F (ETA 5.547) |
| fato_errado_tendencia_23out | c2:F c3:F (ETA 5.547) | c2:F c3:F (ETA 5.547) | c2:P c3:F (ETA 5.547) | c2:P c3:F (ETA 5.547) |
| reignicao_conceicao_20out | c1:F c2:F (ETA 3.114) | c1:F c2:F (ETA 3.114) | c1:F c2:F (ETA 3.114) | c1:F c2:F (ETA 3.114) |
| reignicao_morros_24out | c1:F c2:F (ETA 0.58) | c1:F c2:F (ETA 0.58) | c1:F c2:F (ETA 0.58) | c1:F c2:F (ETA 0.58) |
| tradeoff_noite_gurupi_20out | c1:F c2:F c3:F (ETA 6.486) | c1:F c2:F c3:F (ETA 6.486) | c1:F c2:F c3:F (ETA 6.486) | c1:F c2:F c3:F (ETA 6.486) |
