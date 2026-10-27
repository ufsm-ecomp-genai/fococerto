# FocoCerto: plan for period 2026-10-23 (tocantins)

> **SIMULATED RESOURCES: the crews and aircraft in this plan come from a demo scenario (input_examples/tocantins-escasso.yaml), not from a real inventory.**
>
> **Bases: real location with source; number of crews simulated (scenario).**
>
> Recommendation for the coordinator. Nothing is dispatched without approval: `python -m app.cli aprovar --regiao tocantins --periodo 2026-10-23`

- **Status:** ESCALATED: some decisions need the coordinator
- Planner/Critic cycle rounds: 2
- **Mode:** offline (deterministic agents, no LLM)

## Escalations: human decision required

- **ESCALATED** `cel_-105_-475` (Lagoa do Tocantins, 13.7 km): Escalation: cel_-105_-475 has 3610 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
- **ESCALATED** `cel_-113_-493` (Dueré, 7.3 km): Escalation: cel_-113_-493 has 4321 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
- **ESCALATED** `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km): Escalation: cel_-121_-466 has 4295 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
- **ESCALATED** `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km): Escalation: cel_-122_-464 has 4295 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
- **ESCALATED** `cel_-122_-473` (Conceição do Tocantins, 10.0 km): Escalation: cel_-122_-473 has 3956 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
- **ESCALATED** `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km): Escalation: cel_-90_-486 has 29357 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
- **ESCALATED** `cel_-91_-474` (Centenário, 8.7 km): Escalation: cel_-91_-474 has 2135 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
- **ESCALATED** `cel_-95_-462` (Morros, 12.0 km): Escalation: cel_-95_-462 has 4829 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
- **ESCALATED** `cel_-95_-468` (Lizarda, 14.8 km): Escalation: cel_-95_-468 has 2991 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.

## Resource order

| Order | Resource | Incident | Priority | ETA |
|---|---|---|---|---|
| 1 | `palmas-a1` (air, CBMTO 1º BBM Palmas, official base) | `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km) | 0.60 (medium) | 0.4 h |
| 2 | `saofelix-t1` (ground, Brigada Prevfogo/Ibama São Félix do Tocantins, official base) | `cel_-96_-468` (Lizarda, 5.5 km) | 0.69 (high) | 2.4 h |
| 3 | `portonac-t1` (ground, CBMTO 5ª Cia do 1º BBM Porto Nacional, official base) | `cel_-117_-491` (Gurupi, 8.8 km) | 0.66 (high) | 4.4 h |
| 4 | `palmas-t1` (ground, CBMTO 1º BBM Palmas, official base) | `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km) | 0.64 (high) | 3.4 h |
| 5 | `dianopolis-t1` (ground, CBMTO Companhia de Dianópolis, official base) | `cel_-117_-469` (Dianópolis, 4.6 km) | 0.59 (low) | 0.2 h |
| 6 | `paraiso-t1` (ground, CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins, official base) | `cel_-107_-483` (Porto Nacional, 14.1 km) | 0.59 (low) | 3.0 h |

- **Resources held in reserve:** none
- **Incidents not covered:** `cel_-91_-474` (Centenário, 8.7 km), `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km), `cel_-113_-493` (Dueré, 7.3 km), `cel_-122_-473` (Conceição do Tocantins, 10.0 km), `cel_-105_-475` (Lagoa do Tocantins, 13.7 km), `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km), `cel_-95_-462` (Morros, 12.0 km), `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km), `cel_-95_-468` (Lizarda, 14.8 km)

## Planner summary

[escalated] Adopts the Critic's counter-proposal. Critic counter-proposal (offline): local crew swap. Offline Planner (deterministic): exposed population first; same as the baseline. 6 assignments, 9 incidents without a crew, 0 crews/aircraft held in reserve.

## Priority list

_Priority computed from the data (higher = more urgent). Bands are relative to this period: high, medium, low._

| # | Incident | Priority | Status | Detections | Max FRP (MW) | Pop. in radius | Nearest place | Coverage |
|---|---|---|---|---|---|---|---|---|
| 1 | `cel_-91_-474` | 0.69 (high) | new | 2 | 199.1 | 2135 | Centenário (8.7 km) | **ESCALATED**; not covered |
| 2 | `cel_-96_-468` | 0.69 (high) | growing | 6 | 20.0 | 2991 | Lizarda (5.5 km) | covered by `saofelix-t1` |
| 3 | `cel_-117_-491` | 0.66 (high) | new | 8 | 4.0 | 87545 | Gurupi (8.8 km) | covered by `portonac-t1` |
| 4 | `cel_-107_-476` | 0.64 (high) | new | 3 | 11.3 | 7842 | Ponte Alta do Tocantins (10.3 km) | covered by `palmas-t1` |
| 5 | `cel_-122_-464` | 0.62 (high) | new | 1 | 38.4 | 4295 | Ponte Alta do Bom Jesus (10.0 km) | **ESCALATED**; not covered |
| 6 | `cel_-113_-493` | 0.62 (medium) | new | 4 | 20.4 | 4321 | Dueré (7.3 km) | **ESCALATED**; not covered |
| 7 | `cel_-122_-473` | 0.62 (medium) | new | 2 | 47.9 | 3956 | Conceição do Tocantins (10.0 km) | **ESCALATED**; not covered |
| 8 | `cel_-105_-475` | 0.61 (medium) | new | 3 | 14.0 | 3610 | Lagoa do Tocantins (13.7 km) | **ESCALATED**; not covered |
| 9 | `cel_-90_-486` | 0.61 (medium) | new | 2 | 12.1 | 29357 | Fortaleza do Tabocão (10.7 km) | **ESCALATED**; not covered |
| 10 | `cel_-103_-478` | 0.60 (medium) | growing | 11 | 7.1 | 2463 | Santa Tereza do Tocantins (9.8 km) | covered by `palmas-a1` |
| 11 | `cel_-95_-462` | 0.60 (low) | new | 1 | 9.5 | 4829 | Morros (12.0 km) | **ESCALATED**; not covered |
| 12 | `cel_-121_-466` | 0.60 (low) | new | 4 | 7.6 | 4295 | Ponte Alta do Bom Jesus (14.1 km) | **ESCALATED**; not covered |
| 13 | `cel_-95_-468` | 0.59 (low) | new | 1 | 6.0 | 2991 | Lizarda (14.8 km) | **ESCALATED**; not covered |
| 14 | `cel_-107_-483` | 0.59 (low) | new | 1 | 6.8 | 53316 | Porto Nacional (14.1 km) | covered by `paraiso-t1` |
| 15 | `cel_-117_-469` | 0.59 (low) | new | 1 | 8.7 | 22424 | Dianópolis (4.6 km) | covered by `dianopolis-t1` |

## Justifications and evidence

### 1. `palmas-a1` (air, CBMTO 1º BBM Palmas, official base) → `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km), ETA 0.4 h

**Justification:** Priority 0.60; 2463 inhabitants in the radius; Santa Tereza do Tocantins at 9.8 km; 11 detections, total FRP 52 MW; palmas-a1 (air) arrives in ETA 0.4 h from CBMTO 1º BBM Palmas. (Local crew swap proposed by the Critic.)

**Evidence:** `focos:11`, `eta:0.37`, `pop:2463`, `dist:Santa Tereza do Tocantins:9.8`, `base:osm_n5067657890`

### 2. `saofelix-t1` (ground, Brigada Prevfogo/Ibama São Félix do Tocantins, official base) → `cel_-96_-468` (Lizarda, 5.5 km), ETA 2.4 h

**Justification:** Priority 0.69; 2991 inhabitants in the radius; Lizarda at 5.5 km; 6 detections, total FRP 63 MW; saofelix-t1 (ground) arrives in ETA 2.4 h from Brigada Prevfogo/Ibama São Félix do Tocantins.

**Evidence:** `focos:6`, `eta:2.35`, `pop:2991`, `dist:Lizarda:5.5`, `base:prevfogo_sao_felix`

### 3. `portonac-t1` (ground, CBMTO 5ª Cia do 1º BBM Porto Nacional, official base) → `cel_-117_-491` (Gurupi, 8.8 km), ETA 4.4 h

**Justification:** Priority 0.66; 87545 inhabitants in the radius; Gurupi at 8.8 km; 8 detections, total FRP 24 MW; portonac-t1 (ground) arrives in ETA 4.4 h from CBMTO 5ª Cia do 1º BBM Porto Nacional.

**Evidence:** `focos:8`, `eta:4.40`, `pop:87545`, `dist:Gurupi:8.8`, `base:cbmto_porto_nacional`

### 4. `palmas-t1` (ground, CBMTO 1º BBM Palmas, official base) → `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km), ETA 3.4 h

**Justification:** Priority 0.64; 7842 inhabitants in the radius; Ponte Alta do Tocantins at 10.3 km; 3 detections, total FRP 23 MW; palmas-t1 (ground) arrives in ETA 3.4 h from CBMTO 1º BBM Palmas.

**Evidence:** `focos:3`, `eta:3.39`, `pop:7842`, `dist:Ponte Alta do Tocantins:10.3`, `base:osm_n5067657890`

### 5. `dianopolis-t1` (ground, CBMTO Companhia de Dianópolis, official base) → `cel_-117_-469` (Dianópolis, 4.6 km), ETA 0.2 h

**Justification:** Priority 0.59; 22424 inhabitants in the radius; Dianópolis at 4.6 km; 1 detections, total FRP 9 MW; dianopolis-t1 (ground) arrives in ETA 0.2 h from CBMTO Companhia de Dianópolis. (Local crew swap proposed by the Critic.)

**Evidence:** `focos:1`, `eta:0.16`, `pop:22424`, `dist:Dianópolis:4.6`, `base:cbmto_dianopolis`

### 6. `paraiso-t1` (ground, CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins, official base) → `cel_-107_-483` (Porto Nacional, 14.1 km), ETA 3.0 h

**Justification:** Priority 0.59; 53316 inhabitants in the radius; Porto Nacional at 14.1 km; 1 detections, total FRP 7 MW; paraiso-t1 (ground) arrives in ETA 3.0 h from CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins. (Local crew swap proposed by the Critic.)

**Evidence:** `focos:1`, `eta:2.95`, `pop:53316`, `dist:Porto Nacional:14.1`, `base:cbmto_paraiso`

## Bases and provenance

| Base | Provenance | Source | Resources |
|---|---|---|---|
| CBMTO 1º BBM Palmas (`osm_n5067657890`) | **official**: official list for the region, with source | CBMTO — https://conexaoto.com.br/2023/01/16/1o-batalhao-e-quatro-companhias-de-bombeiros-militar-com-novos-comandos (2023); coordenada: quartel mapeado no OpenStreetMap (node/5067657890); id reaproveitado do OSM, a mesma unidade; fundida com osm_n5067657890 (OpenStreetMap: OpenStreetMap node/5067657890) | `palmas-t1`, `palmas-a1` |
| CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins (`cbmto_paraiso`) | **official**: official list for the region, with source | CBMTO — https://conexaoto.com.br/2023/01/27/companhia-de-bombeiros-em-paraiso-tem-novo-comandante-que-vai-atuar-frente-a-uma-das-cidades-mais-movimentadas-do-estado (2023); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `paraiso-t1` |
| CBMTO 5ª Cia do 1º BBM Porto Nacional (`cbmto_porto_nacional`) | **official**: official list for the region, with source | CBMTO — https://conexaoto.com.br/2022/02/17/governador-wanderlei-autoriza-inicio-das-obras-do-quartel-do-corpo-de-bombeiros-de-porto-nacional (2022); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `portonac-t1` |
| CBMTO Companhia de Dianópolis (`cbmto_dianopolis`) | **official**: official list for the region, with source | CBMTO — https://conexaoto.com.br/2023/01/16/1o-batalhao-e-quatro-companhias-de-bombeiros-militar-com-novos-comandos (2023); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `dianopolis-t1` |
| Brigada Prevfogo/Ibama São Félix do Tocantins (`prevfogo_sao_felix`) | **official**: official list for the region, with source | Prevfogo/Ibama — https://sbtnews.sbt.com.br/noticia/brasil/ibama-autoriza-contratacao-de-brigadas-federais-para-combate-a-incendios-em-municipios-de-19-estados (2024); coordenada: sede do município (GeoNames); Portaria Ibama nº 114/2024 | `saofelix-t1` |

11 other known base(s) in the region, with no resource in this scenario: CBMTO 3º BBM Gurupi (official); CBMTO Companhia de Colinas do Tocantins (official); Brigada Prevfogo/Ibama Santa Tereza do Tocantins (official); Brigada Prevfogo/Ibama Itacajá (official); Brigada Prevfogo/Ibama Goiatins (official); Brigada Prevfogo/Ibama Arraias (official); ICMBio Esec Serra Geral do Tocantins em Rio da Conceição (official); Bombeiros (perto de Porangatu, 1 km) (OSM); SCI (Palmas) (OSM); Corpo de Bombeiros Militar (OSM); Bombeiros (perto de Barreiras, 1 km) (OSM).

## Analyst opinions

The Analyst was not called in this period.

## Memories that influenced the plan (H-MEM)

No memories were used in this period.

## Review cycle

- **Round 1:** Critic verdict `reject`; 13 violations (exposta_nao_atendida, troca_recurso_local)
  - Local crew swap: dianopolis-t1 reaches cel_-117_-469 (22424 people) in 0.16 h, but was sent to cel_-122_-464 (4295 people) at 2.51 h; I swap it and cel_-122_-464 is left uncovered (escalation).
  - Local crew swap: paraiso-t1 reaches cel_-107_-483 (53316 people) in 2.95 h, but was sent to cel_-113_-493 (4321 people) at 4.55 h; I swap it and cel_-113_-493 is left uncovered (escalation).
  - Local crew swap: palmas-a1 reaches cel_-103_-478 (2463 people) in 0.37 h, but was sent to cel_-91_-474 (2135 people) at 0.97 h; I swap it and cel_-91_-474 is left uncovered (escalation).
- **Round 2:** Critic verdict `escalate`; 9 violations (exposta_nao_atendida)
  - Escalation: cel_-91_-474 has 2135 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
  - Escalation: cel_-122_-464 has 4295 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
  - Escalation: cel_-113_-493 has 4321 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
  - Escalation: cel_-122_-473 has 3956 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
  - Escalation: cel_-105_-475 has 3610 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
  - Escalation: cel_-90_-486 has 29357 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
  - Escalation: cel_-95_-462 has 4829 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
  - Escalation: cel_-121_-466 has 4295 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.
  - Escalation: cel_-95_-468 has 2991 people exposed and the viable crews/aircraft are at other incidents with population or in reserve.

## Limitations

- A satellite detection does not confirm a fire, and clouds hide detections.
- Telling agricultural burns from wildfires is an uncertain inference.
- Distance is straight-line with a correction factor; ETA is an estimate.
- GeoNames only lists places with 1,000+ inhabitants.
- The weather index is a surface-level simplification.
- Doctrine is simplified, and there was no validation with operators.

[Full execution log](trace.jsonl)

_Generated at 2026-10-26 23:36 UTC_
