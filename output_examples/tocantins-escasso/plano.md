# FocoCerto: plano do período 2026-10-23 (tocantins)

> **RECURSOS SIMULADOS: as equipes e aeronaves deste plano vêm de um cenário de demonstração (input_examples/tocantins-escasso.yaml), não de um inventário real.**
>
> Recomendação para o coordenador. Nada é despachado sem aprovação: `python -m app.cli aprovar --regiao tocantins --periodo 2026-10-23`

- **Situação:** ESCALADO: há decisões que precisam do coordenador
- Rodadas do ciclo Planejador/Crítico: 1
- **Modo:** offline (agentes determinísticos, sem LLM)

## Escalações: decisão humana necessária

- **ESCALADA** `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km): Escalação: cel_-103_-478 tem 2463 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-105_-475` (Lagoa do Tocantins, 13.7 km): Escalação: cel_-105_-475 tem 3610 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-107_-483` (Porto Nacional, 14.1 km): Escalação: cel_-107_-483 tem 53316 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-117_-469` (Dianópolis, 4.6 km): Escalação: cel_-117_-469 tem 22424 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km): Escalação: cel_-121_-466 tem 4295 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-122_-473` (Conceição do Tocantins, 10.0 km): Escalação: cel_-122_-473 tem 3956 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km): Escalação: cel_-90_-486 tem 29357 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-95_-462` (Morros, 12.0 km): Escalação: cel_-95_-462 tem 4829 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-95_-468` (Lizarda, 14.8 km): Escalação: cel_-95_-468 tem 2991 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.

## Ordem de recursos

| Ordem | Recurso | Ocorrência | Prioridade | ETA |
|---|---|---|---|---|
| 1 | `palmas-a1` (aereo, 1º Batalhão de Bombeiros Militar) | `cel_-91_-474` (Centenário, 8.7 km) | 0.69 (alta) | 1.0 h |
| 2 | `mateiros-t1` (terrestre, Mateiros/Jalapão (simulada)) | `cel_-96_-468` (Lizarda, 5.5 km) | 0.69 (alta) | 4.0 h |
| 3 | `portonac-t1` (terrestre, Porto Nacional (simulada)) | `cel_-117_-491` (Gurupi, 8.8 km) | 0.66 (alta) | 4.4 h |
| 4 | `palmas-t1` (terrestre, 1º Batalhão de Bombeiros Militar) | `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km) | 0.64 (alta) | 3.4 h |
| 5 | `dianopolis-t1` (terrestre, Dianópolis (simulada)) | `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km) | 0.62 (alta) | 2.5 h |
| 6 | `paraiso-t1` (terrestre, Paraíso do Tocantins (simulada)) | `cel_-113_-493` (Dueré, 7.3 km) | 0.62 (média) | 4.5 h |

- **Recursos em reserva:** nenhum
- **Ocorrências não atendidas:** `cel_-122_-473` (Conceição do Tocantins, 10.0 km), `cel_-105_-475` (Lagoa do Tocantins, 13.7 km), `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km), `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km), `cel_-95_-462` (Morros, 12.0 km), `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km), `cel_-95_-468` (Lizarda, 14.8 km), `cel_-107_-483` (Porto Nacional, 14.1 km), `cel_-117_-469` (Dianópolis, 4.6 km)

## Resumo do Planejador

[escala] Planejador offline (determinístico): população exposta primeiro; igual ao baseline. 6 designações, 9 ocorrências sem recurso, 0 recursos em reserva.

## Lista de prioridades

_Prioridade calculada pelos dados (maior = mais urgente). Faixas relativas a este período: alta, média, baixa._

| # | Ocorrência | Prioridade | Status | Focos | FRP máx (MW) | Pop. no raio | Localidade mais próxima | Atendimento |
|---|---|---|---|---|---|---|---|---|
| 1 | `cel_-91_-474` | 0.69 (alta) | nova | 2 | 199.1 | 2135 | Centenário (8.7 km) | atendida por `palmas-a1` |
| 2 | `cel_-96_-468` | 0.69 (alta) | crescendo | 6 | 20.0 | 2991 | Lizarda (5.5 km) | atendida por `mateiros-t1` |
| 3 | `cel_-117_-491` | 0.66 (alta) | nova | 8 | 4.0 | 87545 | Gurupi (8.8 km) | atendida por `portonac-t1` |
| 4 | `cel_-107_-476` | 0.64 (alta) | nova | 3 | 11.3 | 7842 | Ponte Alta do Tocantins (10.3 km) | atendida por `palmas-t1` |
| 5 | `cel_-122_-464` | 0.62 (alta) | nova | 1 | 38.4 | 4295 | Ponte Alta do Bom Jesus (10.0 km) | atendida por `dianopolis-t1` |
| 6 | `cel_-113_-493` | 0.62 (média) | nova | 4 | 20.4 | 4321 | Dueré (7.3 km) | atendida por `paraiso-t1` |
| 7 | `cel_-122_-473` | 0.62 (média) | nova | 2 | 47.9 | 3956 | Conceição do Tocantins (10.0 km) | **ESCALADA**; não atendida |
| 8 | `cel_-105_-475` | 0.61 (média) | nova | 3 | 14.0 | 3610 | Lagoa do Tocantins (13.7 km) | **ESCALADA**; não atendida |
| 9 | `cel_-90_-486` | 0.61 (média) | nova | 2 | 12.1 | 29357 | Fortaleza do Tabocão (10.7 km) | **ESCALADA**; não atendida |
| 10 | `cel_-103_-478` | 0.60 (média) | crescendo | 11 | 7.1 | 2463 | Santa Tereza do Tocantins (9.8 km) | **ESCALADA**; não atendida |
| 11 | `cel_-95_-462` | 0.60 (baixa) | nova | 1 | 9.5 | 4829 | Morros (12.0 km) | **ESCALADA**; não atendida |
| 12 | `cel_-121_-466` | 0.60 (baixa) | nova | 4 | 7.6 | 4295 | Ponte Alta do Bom Jesus (14.1 km) | **ESCALADA**; não atendida |
| 13 | `cel_-95_-468` | 0.59 (baixa) | nova | 1 | 6.0 | 2991 | Lizarda (14.8 km) | **ESCALADA**; não atendida |
| 14 | `cel_-107_-483` | 0.59 (baixa) | nova | 1 | 6.8 | 53316 | Porto Nacional (14.1 km) | **ESCALADA**; não atendida |
| 15 | `cel_-117_-469` | 0.59 (baixa) | nova | 1 | 8.7 | 22424 | Dianópolis (4.6 km) | **ESCALADA**; não atendida |

## Justificativas e evidências

### 1. `palmas-a1` (aereo, 1º Batalhão de Bombeiros Militar) → `cel_-91_-474` (Centenário, 8.7 km), ETA 1.0 h

**Justificativa:** Prioridade 0.69; 2135 habitantes no raio; Centenário a 8.7 km; 2 focos, FRP somado 398 MW; palmas-a1 (aereo) chega em ETA 1.0 h saindo de 1º Batalhão de Bombeiros Militar.

**Evidências:** `focos:2`, `eta:0.97`, `pop:2135`, `dist:Centenário:8.7`, `base:osm_n5067657890`

### 2. `mateiros-t1` (terrestre, Mateiros/Jalapão (simulada)) → `cel_-96_-468` (Lizarda, 5.5 km), ETA 4.0 h

**Justificativa:** Prioridade 0.69; 2991 habitantes no raio; Lizarda a 5.5 km; 6 focos, FRP somado 63 MW; mateiros-t1 (terrestre) chega em ETA 4.0 h saindo de Mateiros/Jalapão (simulada).

**Evidências:** `focos:6`, `eta:3.98`, `pop:2991`, `dist:Lizarda:5.5`, `base:sim_mateiros`

### 3. `portonac-t1` (terrestre, Porto Nacional (simulada)) → `cel_-117_-491` (Gurupi, 8.8 km), ETA 4.4 h

**Justificativa:** Prioridade 0.66; 87545 habitantes no raio; Gurupi a 8.8 km; 8 focos, FRP somado 24 MW; portonac-t1 (terrestre) chega em ETA 4.4 h saindo de Porto Nacional (simulada).

**Evidências:** `focos:8`, `eta:4.40`, `pop:87545`, `dist:Gurupi:8.8`, `base:sim_porto_nacional`

### 4. `palmas-t1` (terrestre, 1º Batalhão de Bombeiros Militar) → `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km), ETA 3.4 h

**Justificativa:** Prioridade 0.64; 7842 habitantes no raio; Ponte Alta do Tocantins a 10.3 km; 3 focos, FRP somado 23 MW; palmas-t1 (terrestre) chega em ETA 3.4 h saindo de 1º Batalhão de Bombeiros Militar.

**Evidências:** `focos:3`, `eta:3.39`, `pop:7842`, `dist:Ponte Alta do Tocantins:10.3`, `base:osm_n5067657890`

### 5. `dianopolis-t1` (terrestre, Dianópolis (simulada)) → `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km), ETA 2.5 h

**Justificativa:** Prioridade 0.62; 4295 habitantes no raio; Ponte Alta do Bom Jesus a 10.0 km; 1 focos, FRP somado 38 MW; dianopolis-t1 (terrestre) chega em ETA 2.5 h saindo de Dianópolis (simulada).

**Evidências:** `focos:1`, `eta:2.51`, `pop:4295`, `dist:Ponte Alta do Bom Jesus:10.0`, `base:sim_dianopolis`

### 6. `paraiso-t1` (terrestre, Paraíso do Tocantins (simulada)) → `cel_-113_-493` (Dueré, 7.3 km), ETA 4.5 h

**Justificativa:** Prioridade 0.62; 4321 habitantes no raio; Dueré a 7.3 km; 4 focos, FRP somado 66 MW; paraiso-t1 (terrestre) chega em ETA 4.5 h saindo de Paraíso do Tocantins (simulada).

**Evidências:** `focos:4`, `eta:4.55`, `pop:4321`, `dist:Dueré:7.3`, `base:sim_paraiso`

## Pareceres do Analista

O Analista não foi chamado neste período.

## Memórias que influenciaram o plano (H-MEM)

Nenhuma memória foi usada neste período.

## Ciclo de revisão

- **Rodada 1:** veredicto do Crítico `escala`; 9 violações (exposta_nao_atendida)
  - Escalação: cel_-122_-473 tem 3956 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-105_-475 tem 3610 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-90_-486 tem 29357 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-103_-478 tem 2463 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-95_-462 tem 4829 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-121_-466 tem 4295 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-95_-468 tem 2991 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-107_-483 tem 53316 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-117_-469 tem 22424 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.

## Limitações

- Detecção de satélite não confirma incêndio, e nuvens escondem focos.
- A distinção entre queima agrícola e incêndio é uma inferência com incerteza.
- A distância é em linha reta com um fator de correção; o ETA é uma estimativa.
- O GeoNames só lista localidades com 1.000+ habitantes.
- O índice de tempo é uma simplificação de superfície.
- A doutrina é simplificada, e não houve validação com operadores.

[Log completo da execução](../../../logs-tocantins-escasso/20261024T221501-be47ed.jsonl)

_Gerado em 2026-10-24 22:15 UTC_
