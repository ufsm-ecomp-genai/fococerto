# FocoCerto: plan for period 2026-10-23 (tocantins)

> **SIMULATED RESOURCES: the crews and aircraft in this plan come from a demo scenario (cenarios/tocantins-escasso.yaml), not from a real inventory.**
>
> **Bases: real location with source; number of crews simulated (scenario).**
>
> Recommendation for the coordinator. Nothing is dispatched without approval: `python -m app.cli aprovar --regiao tocantins --periodo 2026-10-23`

- **Status:** ESCALATED: some decisions need the coordinator
- Planner/Critic cycle rounds: 2
- **Mode:** LLM

## Escalations: human decision required

- **ESCALATED** `cel_-91_-474` (Centenário, 8.7 km): Mandatory: 2135 people exposed and no crew/aircraft assigned in the final plan. Suggested action: request external support.
- **ESCALATED** `cel_-117_-491` (Gurupi, 8.8 km): Mandatory: 87545 people exposed and no crew/aircraft assigned in the final plan. Suggested action: request external support.
- **ESCALATED** `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km): Mandatory: 4295 people exposed and no crew/aircraft assigned in the final plan. Suggested action: request external support.
- **ESCALATED** `cel_-122_-473` (Conceição do Tocantins, 10.0 km): Mandatory: 3956 people exposed and no crew/aircraft assigned in the final plan. Suggested action: request external support.
- **ESCALATED** `cel_-105_-475` (Lagoa do Tocantins, 13.7 km): Mandatory: 3610 people exposed and no crew/aircraft assigned in the final plan. Suggested action: request external support.
- **ESCALATED** `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km): Mandatory: 29357 people exposed and no crew/aircraft assigned in the final plan. Suggested action: request external support.
- **ESCALATED** `cel_-95_-462` (Morros, 12.0 km): Mandatory: 4829 people exposed and no crew/aircraft assigned in the final plan. Suggested action: request external support.
- **ESCALATED** `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km): Mandatory: 4295 people exposed and no crew/aircraft assigned in the final plan. Suggested action: request external support.
- **ESCALATED** `cel_-95_-468` (Lizarda, 14.8 km): Mandatory: 2991 people exposed and no crew/aircraft assigned in the final plan. Suggested action: request external support.

## Resource order

| Order | Resource | Incident | Priority | ETA |
|---|---|---|---|---|
| 1 | `palmas-a1` (air, CBMTO 1º BBM Palmas, official base) | `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km) | 0.60 (medium) | 0.4 h |
| 2 | `saofelix-t1` (ground, Brigada Prevfogo/Ibama São Félix do Tocantins, official base) | `cel_-96_-468` (Lizarda, 5.5 km) | 0.69 (high) | 2.4 h |
| 3 | `portonac-t1` (ground, CBMTO 5ª Cia do 1º BBM Porto Nacional, official base) | `cel_-107_-483` (Porto Nacional, 14.1 km) | 0.59 (low) | 0.5 h |
| 4 | `palmas-t1` (ground, CBMTO 1º BBM Palmas, official base) | `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km) | 0.64 (high) | 3.4 h |
| 5 | `dianopolis-t1` (ground, CBMTO Companhia de Dianópolis, official base) | `cel_-117_-469` (Dianópolis, 4.6 km) | 0.59 (low) | 0.2 h |
| 6 | `paraiso-t1` (ground, CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins, official base) | `cel_-113_-493` (Dueré, 7.3 km) | 0.62 (medium) | 4.5 h |

- **Resources held in reserve:** none
- **Incidents not covered:** `cel_-91_-474` (Centenário, 8.7 km), `cel_-117_-491` (Gurupi, 8.8 km), `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km), `cel_-122_-473` (Conceição do Tocantins, 10.0 km), `cel_-105_-475` (Lagoa do Tocantins, 13.7 km), `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km), `cel_-95_-462` (Morros, 12.0 km), `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km), `cel_-95_-468` (Lizarda, 14.8 km)

## Planner summary

[escalated] 6 assignment(s): palmas-a1→cel_-103_-478, saofelix-t1→cel_-96_-468, portonac-t1→cel_-107_-483, palmas-t1→cel_-107_-476, dianopolis-t1→cel_-117_-469, paraiso-t1→cel_-113_-493. Without a crew: cel_-91_-474, cel_-117_-491, cel_-122_-464, cel_-122_-473, cel_-105_-475, cel_-90_-486, cel_-95_-462, cel_-121_-466, cel_-95_-468. Reserve: none. (Summary rewritten by the system from the final assignments: the agent's summary cited a nonexistent id or a coverage that does not match the plan.)

## Priority list

_Priority computed from the data (higher = more urgent). Bands are relative to this period: high, medium, low._

| # | Incident | Priority | Status | Detections | Max FRP (MW) | Pop. in radius | Nearest place | Coverage |
|---|---|---|---|---|---|---|---|---|
| 1 | `cel_-91_-474` | 0.69 (high) | new | 2 | 199.1 | 2135 | Centenário (8.7 km) | **ESCALATED**; not covered |
| 2 | `cel_-96_-468` | 0.69 (high) | growing | 6 | 20.0 | 2991 | Lizarda (5.5 km) | covered by `saofelix-t1` |
| 3 | `cel_-117_-491` | 0.66 (high) | new | 8 | 4.0 | 87545 | Gurupi (8.8 km) | **ESCALATED**; not covered |
| 4 | `cel_-107_-476` | 0.64 (high) | new | 3 | 11.3 | 7842 | Ponte Alta do Tocantins (10.3 km) | covered by `palmas-t1` |
| 5 | `cel_-122_-464` | 0.62 (high) | new | 1 | 38.4 | 4295 | Ponte Alta do Bom Jesus (10.0 km) | **ESCALATED**; not covered |
| 6 | `cel_-113_-493` | 0.62 (medium) | new | 4 | 20.4 | 4321 | Dueré (7.3 km) | covered by `paraiso-t1` |
| 7 | `cel_-122_-473` | 0.62 (medium) | new | 2 | 47.9 | 3956 | Conceição do Tocantins (10.0 km) | **ESCALATED**; not covered |
| 8 | `cel_-105_-475` | 0.61 (medium) | new | 3 | 14.0 | 3610 | Lagoa do Tocantins (13.7 km) | **ESCALATED**; not covered |
| 9 | `cel_-90_-486` | 0.61 (medium) | new | 2 | 12.1 | 29357 | Fortaleza do Tabocão (10.7 km) | **ESCALATED**; not covered |
| 10 | `cel_-103_-478` | 0.60 (medium) | growing | 11 | 7.1 | 2463 | Santa Tereza do Tocantins (9.8 km) | covered by `palmas-a1` |
| 11 | `cel_-95_-462` | 0.60 (low) | new | 1 | 9.5 | 4829 | Morros (12.0 km) | **ESCALATED**; not covered |
| 12 | `cel_-121_-466` | 0.60 (low) | new | 4 | 7.6 | 4295 | Ponte Alta do Bom Jesus (14.1 km) | **ESCALATED**; not covered |
| 13 | `cel_-95_-468` | 0.59 (low) | new | 1 | 6.0 | 2991 | Lizarda (14.8 km) | **ESCALATED**; not covered |
| 14 | `cel_-107_-483` | 0.59 (low) | new | 1 | 6.8 | 53316 | Porto Nacional (14.1 km) | covered by `portonac-t1` |
| 15 | `cel_-117_-469` | 0.59 (low) | new | 1 | 8.7 | 22424 | Dianópolis (4.6 km) | covered by `dianopolis-t1` |

## Justifications and evidence

### 1. `palmas-a1` (air, CBMTO 1º BBM Palmas, official base) → `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km), ETA 0.4 h

**Justification:** Only viable aerial resource for cel_-103_-478 (ETA 0.37 h ≤ 6 h limit); population 2463 in Santa Tereza do Tocantins at 9.8 km; priority 0.602; 11 detections, FRP 51.9 MW. Swap gains 0.6 h and serves larger population than cel_-91_-474.

**Evidence:** `pop:2463`, `eta:0.37`, `dist:Santa Tereza do Tocantins:9.8`, `base:osm_n5067657890`, `focos:11`, `frp:51.9`

### 2. `saofelix-t1` (ground, Brigada Prevfogo/Ibama São Félix do Tocantins, official base) → `cel_-96_-468` (Lizarda, 5.5 km), ETA 2.4 h

**Justification:** Only viable ground resource for cel_-96_-468 (ETA 2.35 h ≤ 6 h limit); population 2991 in Lizarda at 5.5 km; priority 0.685; 6 detections, FRP 63.3 MW.

**Evidence:** `pop:2991`, `eta:2.35`, `dist:Lizarda:5.5`, `base:prevfogo_sao_felix`, `focos:6`, `frp:63.3`

### 3. `portonac-t1` (ground, CBMTO 5ª Cia do 1º BBM Porto Nacional, official base) → `cel_-107_-483` (Porto Nacional, 14.1 km), ETA 0.5 h

**Justification:** Priority 0.59; 53316 inhabitants in the radius; Porto Nacional at 14.1 km; 1 detections, total FRP 7 MW; portonac-t1 (ground) arrives in ETA 0.5 h from CBMTO 5ª Cia do 1º BBM Porto Nacional. (Justification rewritten from the data: the previous one cited a fact that does not match.)

**Evidence:** `focos:1`, `eta:0.49`, `pop:53316`, `dist:Porto Nacional:14.1`, `base:cbmto_porto_nacional`

### 4. `palmas-t1` (ground, CBMTO 1º BBM Palmas, official base) → `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km), ETA 3.4 h

**Justification:** Palmas-t1 arrives in 3.39 h ≤ 6 h limit; population 7842 in Ponte Alta do Tocantins at 10.3 km. Priority 0.636; 3 detections, FRP 23.2 MW.

**Evidence:** `pop:7842`, `eta:3.39`, `dist:Ponte Alta do Tocantins:10.3`, `base:osm_n5067657890`, `focos:3`, `frp:23.2`

### 5. `dianopolis-t1` (ground, CBMTO Companhia de Dianópolis, official base) → `cel_-117_-469` (Dianópolis, 4.6 km), ETA 0.2 h

**Justification:** Mandatory swap: population 22424 in Dianópolis at 4.6 km; ETA 0.16 h ≤ 6 h limit (gain 2.35 h vs cel_-122_-464). Priority 0.593; 1 detection, FRP 8.7 MW.

**Evidence:** `pop:22424`, `eta:0.16`, `dist:Dianópolis:4.6`, `base:cbmto_dianopolis`, `focos:1`, `frp:8.7`

### 6. `paraiso-t1` (ground, CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins, official base) → `cel_-113_-493` (Dueré, 7.3 km), ETA 4.5 h

**Justification:** Paraíso-t1 arrives in 4.55 h ≤ 6 h limit; population 4321 in Dueré at 7.3 km. Priority 0.615; 4 detections, FRP 66.1 MW. Closest available ground resource for this region.

**Evidence:** `pop:4321`, `eta:4.55`, `dist:Dueré:7.3`, `base:cbmto_paraiso`, `focos:4`, `frp:66.1`

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
  - palmas-a1 assigned to cel_-91_-474 (2135 people, ETA 0.97 h) while cel_-103_-478 (2463 people, ETA 0.37 h) is unserved; swap gains 0.6 h and serves larger population
  - dianopolis-t1 assigned to cel_-122_-464 (4295 people, ETA 2.51 h) while cel_-117_-469 (22424 people, ETA 0.16 h) is unserved; swap gains 2.35 h and serves 5× larger population
  - paraiso-t1 assigned to cel_-113_-493 (4321 people, ETA 4.55 h) while cel_-107_-483 (53316 people, ETA 2.95 h) is unserved; swap gains 1.59 h and serves 12× larger population
  - portonac-t1 assigned to cel_-117_-491 (87545 people, ETA 4.4 h) while cel_-107_-483 (53316 people, ETA 0.49 h) is unserved; gurupi-t1 (base cbmto_gurupi) can serve cel_-117_-491 in 0.31 h, freeing portonac-t1 for higher-priority swap
  - dianopolis-t1 can serve cel_-121_-466 (4295 people, ETA 1.78 h) instead of cel_-122_-464, gaining 0.74 h for same population
- **Round 2:** Critic verdict `approve`; 13 violations (citacao_incorreta, exposta_nao_atendida)
  - All 6 assigned resources meet the rigid ETA ≤ 6 h limit.
  - Three mandatory swaps (troca_recurso_local) were correctly applied: palmas-a1 to cel_-103_-478 (gain 0.6 h, larger population 2463 vs 2135), dianopolis-t1 to cel_-117_-469 (gain 2.35 h, population 5× larger 22424 vs 4295), portonac-t1 to cel_-107_-483 (gain 3.9 h, population 53316 served by optimal ground resource while gurupi-t1 covers cel_-117_-491 at 0.31 h).
  - The refused swap (paraiso-t1 to cel_-107_-483) is justified: portonac-t1 is faster (0.49 h vs 2.95 h) and moving paraiso-t1 would leave cel_-113_-493 without any viable alternative.
  - The 9 'exposta_nao_atendida' violations are non-rigid and stem from an objective shortage of resources (6 crews for 15 incidents with exposed population). After mandatory swaps, 6 incidents remain without any viable resource and are correctly listed for escalation.
  - The plan follows the composite priority (exposure, intensity, time, persistence, growth) and contains no rigid violations or incorrect citations.

## Limitations

- A satellite detection does not confirm a fire, and clouds hide detections.
- Telling agricultural burns from wildfires is an uncertain inference.
- Distance is straight-line with a correction factor; ETA is an estimate.
- GeoNames only lists places with 1,000+ inhabitants.
- The weather index is a surface-level simplification.
- Doctrine is simplified, and there was no validation with operators.

[Full execution log](../../../fc-en2-logs/20261026T180817-eca168.jsonl)

_Generated at 2026-10-26 18:11 UTC_
