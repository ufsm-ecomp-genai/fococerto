# Escolha da região com o arquivo FIRMS de 7 dias

Fonte: `SUOMI_VIIRS_C2_Global_7d.csv` (NASA FIRMS, VIIRS Suomi-NPP), baixado em 24/10/2026; dias UTC 2026-10-17 a 2026-10-24. **2026-10-24 está incompleto** (o arquivo termina no meio do dia).
Ocorrência = célula de 0,1° com foco no dia. Exposta = alguma localidade do GeoNames `cities1000` (1.000+ hab.) a < 15 km do centroide dos focos da célula.
Gerado por `python -m app.data.comparar_regioes` (dados reais, nada simulado).

## Tocantins/Jalapão [-13.0, -8.0, -49.5, -45.5]

| Dia (UTC) | Detecções | Ocorrências | Ocorrências com localidade < 15 km |
|---|---|---|---|
| 2026-10-17 | 323 | 134 | 35 |
| 2026-10-18 | 51 | 23 | 7 |
| 2026-10-19 | 62 | 29 | 8 |
| 2026-10-20 | 130 | 43 | 9 |
| 2026-10-21 | 84 | 46 | 11 |
| 2026-10-22 | 660 | 223 | 57 |
| 2026-10-23 | 514 | 179 | 52 |
| 2026-10-24 | 51 | 21 | 7 |
| **média dias completos** | 261 | 97 | 26 |

## Pantanal [-22.5, -15.5, -59.5, -54.5]

| Dia (UTC) | Detecções | Ocorrências | Ocorrências com localidade < 15 km |
|---|---|---|---|
| 2026-10-17 | 54 | 8 | 0 |
| 2026-10-18 | 36 | 18 | 1 |
| 2026-10-19 | 74 | 30 | 4 |
| 2026-10-20 | 55 | 26 | 5 |
| 2026-10-21 | 113 | 34 | 4 |
| 2026-10-22 | 172 | 35 | 1 |
| 2026-10-23 | 113 | 34 | 2 |
| 2026-10-24 | 51 | 19 | 3 |
| **média dias completos** | 88 | 26 | 2 |

## Sudeste do Pará [-10.0, -4.0, -53.5, -48.0]

| Dia (UTC) | Detecções | Ocorrências | Ocorrências com localidade < 15 km |
|---|---|---|---|
| 2026-10-17 | 378 | 109 | 22 |
| 2026-10-18 | 135 | 32 | 5 |
| 2026-10-19 | 50 | 17 | 2 |
| 2026-10-20 | 117 | 50 | 1 |
| 2026-10-21 | 82 | 35 | 7 |
| 2026-10-22 | 221 | 113 | 24 |
| 2026-10-23 | 183 | 82 | 13 |
| 2026-10-24 | 127 | 58 | 5 |
| **média dias completos** | 167 | 63 | 11 |

## Península Ibérica [36.0, 44.0, -10.0, 4.0]

| Dia (UTC) | Detecções | Ocorrências | Ocorrências com localidade < 15 km |
|---|---|---|---|
| 2026-10-17 | 37 | 26 | 26 |
| 2026-10-18 | 49 | 21 | 21 |
| 2026-10-19 | 21 | 11 | 11 |
| 2026-10-20 | 8 | 7 | 7 |
| 2026-10-21 | 57 | 31 | 31 |
| 2026-10-22 | 30 | 21 | 21 |
| 2026-10-23 | 87 | 44 | 43 |
| 2026-10-24 | 36 | 26 | 26 |
| **média dias completos** | 41 | 23 | 23 |

## Resumo (média por dia completo)

| Região | Detecções | Ocorrências | Expostas | Dias com ≥ 20 ocorrências expostas |
|---|---|---|---|---|
| Tocantins/Jalapão | 261 | 97 | 26 | 3 de 7 |
| Pantanal | 88 | 26 | 2 | 0 de 7 |
| Sudeste do Pará | 167 | 63 | 11 | 2 de 7 |
| Península Ibérica | 41 | 23 | 23 | 5 de 7 |

## Conclusão (calculada)

- Mais ocorrências por dia (escassez): **Tocantins/Jalapão** (97).
- Mais ocorrências expostas por dia: **Tocantins/Jalapão** (26).
- A contagem varia muito de um dia para outro; para a demo, prefira um dia de pico (veja a coluna de ocorrências da região principal).
