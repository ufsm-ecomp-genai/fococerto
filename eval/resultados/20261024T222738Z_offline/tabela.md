Modo: **offline** (agentes offline determinísticos: validação do pipeline, não o resultado final)

| Variante | Acerto | Decisão | Detecção | Alarmes falsos (gabarito) | Citações falsas | ETA pond. (h) | ETA pond. log (h) | Rodadas | Status escala | Escalações | Desvio acerto entre rep. | Cenários com planos ≠ entre rep. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 18/81 (22.2%) | 15/51 | 0/27 | 0/3 | 0 | 4.399 | 6.213 | 0.0 | 0/36 | 0.0 | 0.0 | 0 |
| **B** | 48/81 (59.3%) | 27/51 | 18/27 | 0/3 | 0 | 4.365 | 6.121 | 1.167 | 0/36 | 0.0 | 0.0 | 0 |
| **C** | 69/87 (79.3%) | 36/51 | 27/30 | 0/6 | 0 | 4.441 | 6.279 | 1.333 | 33/36 | 5.167 | 0.0 | 0 |
| **D** | 51/87 (58.6%) | 30/51 | 15/30 | 0/6 | 0 | 4.365 | 6.121 | 1.333 | 33/36 | 5.0 | 0.0 | 0 |

Por cenário (checagens; P = passou, F = falhou, – = não se aplica, ! = inválido; uma letra por repetição quando diferem):

| Cenário | A | B | C | D |
|---|---|---|---|---|
| agricola_recorrente_parana_24out | c1:F c2:– (ETA 1.2) | c1:F c2:– (ETA 1.2) | c1:F c2:F (ETA 1.2) | c1:F c2:F (ETA 1.2) |
| controle_taguatinga_liberada_21out | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.493) | c1:P c2:P (ETA 5.493) |
| controle_vegetacao_parana_19out | c1:– c2:P (ETA 1.772) | c1:– c2:P (ETA 1.772) | c1:P c2:P (ETA 1.772) | c1:P c2:P (ETA 1.772) |
| escalar_expostas_22out | c1:F c2:F (ETA 4.429) | c1:F c2:F (ETA 4.429) | c1:P c2:P (ETA 4.429) | c1:P c2:P (ETA 4.429) |
| excecao_dianopolis_ponte_18out | c1:F c2:P (ETA 4.687) | c1:F c2:P (ETA 4.277) | c1:P c2:P (ETA 5.085) | c1:F c2:P (ETA 4.277) |
| excecao_mateiros_alagada_23out | c1:F c2:P c3:P c4:F (ETA 8.39) | c1:F c2:P c3:P c4:F (ETA 8.39) | c1:P c2:P c3:P c4:P (ETA 8.491) | c1:F c2:P c3:P c4:P (ETA 8.39) |
| fato_errado_localidade_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) |
| fato_errado_populacao_23out | c1:F c2:F c3:F (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) | c1:P c2:P c3:P (ETA 5.547) |
| fato_errado_tendencia_23out | c2:F c3:F (ETA 5.547) | c2:F c3:F (ETA 5.547) | c2:P c3:F (ETA 5.547) | c2:P c3:F (ETA 5.547) |
| reignicao_conceicao_20out | c1:F c2:F (ETA 3.114) | c1:P c2:P (ETA 3.114) | c1:P c2:P (ETA 3.114) | c1:F c2:F (ETA 3.114) |
| reignicao_morros_24out | c1:F c2:F (ETA 0.58) | c1:P c2:P (ETA 0.58) | c1:P c2:P (ETA 0.58) | c1:F c2:F (ETA 0.58) |
| tradeoff_noite_gurupi_20out | c1:F c2:F c3:F (ETA 6.486) | c1:F c2:F c3:F (ETA 6.486) | c1:F c2:F c3:F (ETA 6.486) | c1:F c2:F c3:F (ETA 6.486) |
