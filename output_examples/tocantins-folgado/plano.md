# FocoCerto: plano do período 2026-10-23 (tocantins)

> **RECURSOS SIMULADOS: as equipes e aeronaves deste plano vêm de um cenário de demonstração (input_examples/tocantins-folgado.yaml), não de um inventário real.**
>
> **Bases: localização real com fonte; quantidade de equipes simulada (cenário).**
>
> Recomendação para o coordenador. Nada é despachado sem aprovação: `python -m app.cli aprovar --regiao tocantins --periodo 2026-10-23`

- **Situação:** ESCALADO: há decisões que precisam do coordenador
- Rodadas do ciclo Planejador/Crítico: 2
- **Modo:** offline (agentes determinísticos, sem LLM)

## Escalações: decisão humana necessária

- **ESCALADA** `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km): Escalação: cel_-121_-466 tem 4295 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km): Escalação: cel_-122_-464 tem 4295 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.

## Ordem de recursos

| Ordem | Recurso | Ocorrência | Prioridade | ETA |
|---|---|---|---|---|
| 1 | `palmas-a1` (aereo, CBMTO 1º BBM Palmas, base oficial) | `cel_-91_-474` (Centenário, 8.7 km) | 0.69 (alta) | 1.0 h |
| 2 | `palmas-a2` (aereo, CBMTO 1º BBM Palmas, base oficial) | `cel_-96_-468` (Lizarda, 5.5 km) | 0.69 (alta) | 1.1 h |
| 3 | `gurupi-t1` (terrestre, CBMTO 3º BBM Gurupi, base oficial) | `cel_-117_-491` (Gurupi, 8.8 km) | 0.66 (alta) | 0.3 h |
| 4 | `santatereza-t1` (terrestre, Brigada Prevfogo/Ibama Santa Tereza do Tocantins, base oficial) | `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km) | 0.64 (alta) | 1.7 h |
| 5 | `dianopolis-t1` (terrestre, CBMTO Companhia de Dianópolis, base oficial) | `cel_-117_-469` (Dianópolis, 4.6 km) | 0.59 (baixa) | 0.2 h |
| 6 | `gurupi-t2` (terrestre, CBMTO 3º BBM Gurupi, base oficial) | `cel_-113_-493` (Dueré, 7.3 km) | 0.62 (média) | 1.9 h |
| 7 | `arraias-t1` (terrestre, Brigada Prevfogo/Ibama Arraias, base oficial) | `cel_-122_-473` (Conceição do Tocantins, 10.0 km) | 0.62 (média) | 3.3 h |
| 8 | `saofelix-t1` (terrestre, Brigada Prevfogo/Ibama São Félix do Tocantins, base oficial) | `cel_-105_-475` (Lagoa do Tocantins, 13.7 km) | 0.61 (média) | 3.3 h |
| 9 | `colinas-t1` (terrestre, CBMTO Companhia de Colinas do Tocantins, base oficial) | `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km) | 0.61 (média) | 3.5 h |
| 10 | `palmas-t1` (terrestre, CBMTO 1º BBM Palmas, base oficial) | `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km) | 0.60 (média) | 2.3 h |
| 11 | `saofelix-t2` (terrestre, Brigada Prevfogo/Ibama São Félix do Tocantins, base oficial) | `cel_-95_-462` (Morros, 12.0 km) | 0.60 (baixa) | 3.2 h |
| 12 | `itacaja-t1` (terrestre, Brigada Prevfogo/Ibama Itacajá, base oficial) | `cel_-95_-468` (Lizarda, 14.8 km) | 0.59 (baixa) | 5.8 h |
| 13 | `portonac-t1` (terrestre, CBMTO 5ª Cia do 1º BBM Porto Nacional, base oficial) | `cel_-107_-483` (Porto Nacional, 14.1 km) | 0.59 (baixa) | 0.5 h |

- **Recursos em reserva:** `palmas-t2`, `palmas-t3`, `paraiso-t1`
- **Ocorrências não atendidas:** `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km), `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km)

## Resumo do Planejador

[escala] Adota a contra-proposta do Crítico. Contra-proposta do Crítico (offline): troca de recurso local. Planejador offline (determinístico): população exposta primeiro; igual ao baseline. 13 designações, 2 ocorrências sem recurso, 3 recursos em reserva.

## Lista de prioridades

_Prioridade calculada pelos dados (maior = mais urgente). Faixas relativas a este período: alta, média, baixa._

| # | Ocorrência | Prioridade | Status | Focos | FRP máx (MW) | Pop. no raio | Localidade mais próxima | Atendimento |
|---|---|---|---|---|---|---|---|---|
| 1 | `cel_-91_-474` | 0.69 (alta) | nova | 2 | 199.1 | 2135 | Centenário (8.7 km) | atendida por `palmas-a1` |
| 2 | `cel_-96_-468` | 0.69 (alta) | crescendo | 6 | 20.0 | 2991 | Lizarda (5.5 km) | atendida por `palmas-a2` |
| 3 | `cel_-117_-491` | 0.66 (alta) | nova | 8 | 4.0 | 87545 | Gurupi (8.8 km) | atendida por `gurupi-t1` |
| 4 | `cel_-107_-476` | 0.64 (alta) | nova | 3 | 11.3 | 7842 | Ponte Alta do Tocantins (10.3 km) | atendida por `santatereza-t1` |
| 5 | `cel_-122_-464` | 0.62 (alta) | nova | 1 | 38.4 | 4295 | Ponte Alta do Bom Jesus (10.0 km) | **ESCALADA**; não atendida |
| 6 | `cel_-113_-493` | 0.62 (média) | nova | 4 | 20.4 | 4321 | Dueré (7.3 km) | atendida por `gurupi-t2` |
| 7 | `cel_-122_-473` | 0.62 (média) | nova | 2 | 47.9 | 3956 | Conceição do Tocantins (10.0 km) | atendida por `arraias-t1` |
| 8 | `cel_-105_-475` | 0.61 (média) | nova | 3 | 14.0 | 3610 | Lagoa do Tocantins (13.7 km) | atendida por `saofelix-t1` |
| 9 | `cel_-90_-486` | 0.61 (média) | nova | 2 | 12.1 | 29357 | Fortaleza do Tabocão (10.7 km) | atendida por `colinas-t1` |
| 10 | `cel_-103_-478` | 0.60 (média) | crescendo | 11 | 7.1 | 2463 | Santa Tereza do Tocantins (9.8 km) | atendida por `palmas-t1` |
| 11 | `cel_-95_-462` | 0.60 (baixa) | nova | 1 | 9.5 | 4829 | Morros (12.0 km) | atendida por `saofelix-t2` |
| 12 | `cel_-121_-466` | 0.60 (baixa) | nova | 4 | 7.6 | 4295 | Ponte Alta do Bom Jesus (14.1 km) | **ESCALADA**; não atendida |
| 13 | `cel_-95_-468` | 0.59 (baixa) | nova | 1 | 6.0 | 2991 | Lizarda (14.8 km) | atendida por `itacaja-t1` |
| 14 | `cel_-107_-483` | 0.59 (baixa) | nova | 1 | 6.8 | 53316 | Porto Nacional (14.1 km) | atendida por `portonac-t1` |
| 15 | `cel_-117_-469` | 0.59 (baixa) | nova | 1 | 8.7 | 22424 | Dianópolis (4.6 km) | atendida por `dianopolis-t1` |

## Justificativas e evidências

### 1. `palmas-a1` (aereo, CBMTO 1º BBM Palmas, base oficial) → `cel_-91_-474` (Centenário, 8.7 km), ETA 1.0 h

**Justificativa:** Prioridade 0.69; 2135 habitantes no raio; Centenário a 8.7 km; 2 focos, FRP somado 398 MW; palmas-a1 (aereo) chega em ETA 1.0 h saindo de CBMTO 1º BBM Palmas.

**Evidências:** `focos:2`, `eta:0.97`, `pop:2135`, `dist:Centenário:8.7`, `base:osm_n5067657890`

### 2. `palmas-a2` (aereo, CBMTO 1º BBM Palmas, base oficial) → `cel_-96_-468` (Lizarda, 5.5 km), ETA 1.1 h

**Justificativa:** Prioridade 0.69; 2991 habitantes no raio; Lizarda a 5.5 km; 6 focos, FRP somado 63 MW; palmas-a2 (aereo) chega em ETA 1.1 h saindo de CBMTO 1º BBM Palmas.

**Evidências:** `focos:6`, `eta:1.07`, `pop:2991`, `dist:Lizarda:5.5`, `base:osm_n5067657890`

### 3. `gurupi-t1` (terrestre, CBMTO 3º BBM Gurupi, base oficial) → `cel_-117_-491` (Gurupi, 8.8 km), ETA 0.3 h

**Justificativa:** Prioridade 0.66; 87545 habitantes no raio; Gurupi a 8.8 km; 8 focos, FRP somado 24 MW; gurupi-t1 (terrestre) chega em ETA 0.3 h saindo de CBMTO 3º BBM Gurupi.

**Evidências:** `focos:8`, `eta:0.31`, `pop:87545`, `dist:Gurupi:8.8`, `base:cbmto_gurupi`

### 4. `santatereza-t1` (terrestre, Brigada Prevfogo/Ibama Santa Tereza do Tocantins, base oficial) → `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km), ETA 1.7 h

**Justificativa:** Prioridade 0.64; 7842 habitantes no raio; Ponte Alta do Tocantins a 10.3 km; 3 focos, FRP somado 23 MW; santatereza-t1 (terrestre) chega em ETA 1.7 h saindo de Brigada Prevfogo/Ibama Santa Tereza do Tocantins.

**Evidências:** `focos:3`, `eta:1.72`, `pop:7842`, `dist:Ponte Alta do Tocantins:10.3`, `base:prevfogo_santa_tereza`

### 5. `dianopolis-t1` (terrestre, CBMTO Companhia de Dianópolis, base oficial) → `cel_-117_-469` (Dianópolis, 4.6 km), ETA 0.2 h

**Justificativa:** Prioridade 0.59; 22424 habitantes no raio; Dianópolis a 4.6 km; 1 focos, FRP somado 9 MW; dianopolis-t1 (terrestre) chega em ETA 0.2 h saindo de CBMTO Companhia de Dianópolis. (Troca de recurso local proposta pelo Crítico.)

**Evidências:** `focos:1`, `eta:0.16`, `pop:22424`, `dist:Dianópolis:4.6`, `base:cbmto_dianopolis`

### 6. `gurupi-t2` (terrestre, CBMTO 3º BBM Gurupi, base oficial) → `cel_-113_-493` (Dueré, 7.3 km), ETA 1.9 h

**Justificativa:** Prioridade 0.62; 4321 habitantes no raio; Dueré a 7.3 km; 4 focos, FRP somado 66 MW; gurupi-t2 (terrestre) chega em ETA 1.9 h saindo de CBMTO 3º BBM Gurupi.

**Evidências:** `focos:4`, `eta:1.89`, `pop:4321`, `dist:Dueré:7.3`, `base:cbmto_gurupi`

### 7. `arraias-t1` (terrestre, Brigada Prevfogo/Ibama Arraias, base oficial) → `cel_-122_-473` (Conceição do Tocantins, 10.0 km), ETA 3.3 h

**Justificativa:** Prioridade 0.62; 3956 habitantes no raio; Conceição do Tocantins a 10.0 km; 2 focos, FRP somado 62 MW; arraias-t1 (terrestre) chega em ETA 3.3 h saindo de Brigada Prevfogo/Ibama Arraias.

**Evidências:** `focos:2`, `eta:3.34`, `pop:3956`, `dist:Conceição do Tocantins:10.0`, `base:prevfogo_arraias`

### 8. `saofelix-t1` (terrestre, Brigada Prevfogo/Ibama São Félix do Tocantins, base oficial) → `cel_-105_-475` (Lagoa do Tocantins, 13.7 km), ETA 3.3 h

**Justificativa:** Prioridade 0.61; 3610 habitantes no raio; Lagoa do Tocantins a 13.7 km; 3 focos, FRP somado 20 MW; saofelix-t1 (terrestre) chega em ETA 3.3 h saindo de Brigada Prevfogo/Ibama São Félix do Tocantins.

**Evidências:** `focos:3`, `eta:3.26`, `pop:3610`, `dist:Lagoa do Tocantins:13.7`, `base:prevfogo_sao_felix`

### 9. `colinas-t1` (terrestre, CBMTO Companhia de Colinas do Tocantins, base oficial) → `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km), ETA 3.5 h

**Justificativa:** Prioridade 0.61; 29357 habitantes no raio; Fortaleza do Tabocão a 10.7 km; 2 focos, FRP somado 17 MW; colinas-t1 (terrestre) chega em ETA 3.5 h saindo de CBMTO Companhia de Colinas do Tocantins.

**Evidências:** `focos:2`, `eta:3.52`, `pop:29357`, `dist:Fortaleza do Tabocão:10.7`, `base:cbmto_colinas`

### 10. `palmas-t1` (terrestre, CBMTO 1º BBM Palmas, base oficial) → `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km), ETA 2.3 h

**Justificativa:** Prioridade 0.60; 2463 habitantes no raio; Santa Tereza do Tocantins a 9.8 km; 11 focos, FRP somado 52 MW; palmas-t1 (terrestre) chega em ETA 2.3 h saindo de CBMTO 1º BBM Palmas.

**Evidências:** `focos:11`, `eta:2.32`, `pop:2463`, `dist:Santa Tereza do Tocantins:9.8`, `base:osm_n5067657890`

### 11. `saofelix-t2` (terrestre, Brigada Prevfogo/Ibama São Félix do Tocantins, base oficial) → `cel_-95_-462` (Morros, 12.0 km), ETA 3.2 h

**Justificativa:** Prioridade 0.60; 4829 habitantes no raio; Morros a 12.0 km; 1 focos, FRP somado 9 MW; saofelix-t2 (terrestre) chega em ETA 3.2 h saindo de Brigada Prevfogo/Ibama São Félix do Tocantins.

**Evidências:** `focos:1`, `eta:3.25`, `pop:4829`, `dist:Morros:12.0`, `base:prevfogo_sao_felix`

### 12. `itacaja-t1` (terrestre, Brigada Prevfogo/Ibama Itacajá, base oficial) → `cel_-95_-468` (Lizarda, 14.8 km), ETA 5.8 h

**Justificativa:** Prioridade 0.59; 2991 habitantes no raio; Lizarda a 14.8 km; 1 focos, FRP somado 6 MW; itacaja-t1 (terrestre) chega em ETA 5.8 h saindo de Brigada Prevfogo/Ibama Itacajá.

**Evidências:** `focos:1`, `eta:5.82`, `pop:2991`, `dist:Lizarda:14.8`, `base:prevfogo_itacaja`

### 13. `portonac-t1` (terrestre, CBMTO 5ª Cia do 1º BBM Porto Nacional, base oficial) → `cel_-107_-483` (Porto Nacional, 14.1 km), ETA 0.5 h

**Justificativa:** Prioridade 0.59; 53316 habitantes no raio; Porto Nacional a 14.1 km; 1 focos, FRP somado 7 MW; portonac-t1 (terrestre) chega em ETA 0.5 h saindo de CBMTO 5ª Cia do 1º BBM Porto Nacional.

**Evidências:** `focos:1`, `eta:0.49`, `pop:53316`, `dist:Porto Nacional:14.1`, `base:cbmto_porto_nacional`

## Bases e procedência

| Base | Procedência | Fonte | Recursos |
|---|---|---|---|
| CBMTO 1º BBM Palmas (`osm_n5067657890`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2023/01/16/1o-batalhao-e-quatro-companhias-de-bombeiros-militar-com-novos-comandos (2023); coordenada: quartel mapeado no OpenStreetMap (node/5067657890); id reaproveitado do OSM, a mesma unidade; fundida com osm_n5067657890 (OpenStreetMap: OpenStreetMap node/5067657890) | `palmas-t1`, `palmas-t2`, `palmas-t3`, `palmas-a1`, `palmas-a2` |
| CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins (`cbmto_paraiso`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2023/01/27/companhia-de-bombeiros-em-paraiso-tem-novo-comandante-que-vai-atuar-frente-a-uma-das-cidades-mais-movimentadas-do-estado (2023); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `paraiso-t1` |
| CBMTO 5ª Cia do 1º BBM Porto Nacional (`cbmto_porto_nacional`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2022/02/17/governador-wanderlei-autoriza-inicio-das-obras-do-quartel-do-corpo-de-bombeiros-de-porto-nacional (2022); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `portonac-t1` |
| CBMTO 3º BBM Gurupi (`cbmto_gurupi`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2023/07/09/praias-de-palmas-e-do-interior-recebem-apoio-com-presenca-de-bombeiros-militares (2023); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `gurupi-t1`, `gurupi-t2` |
| CBMTO Companhia de Dianópolis (`cbmto_dianopolis`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2023/01/16/1o-batalhao-e-quatro-companhias-de-bombeiros-militar-com-novos-comandos (2023); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `dianopolis-t1` |
| CBMTO Companhia de Colinas do Tocantins (`cbmto_colinas`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2023/01/16/1o-batalhao-e-quatro-companhias-de-bombeiros-militar-com-novos-comandos (2023); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `colinas-t1` |
| Brigada Prevfogo/Ibama São Félix do Tocantins (`prevfogo_sao_felix`) | **oficial**: lista oficial da região, com fonte | Prevfogo/Ibama — https://sbtnews.sbt.com.br/noticia/brasil/ibama-autoriza-contratacao-de-brigadas-federais-para-combate-a-incendios-em-municipios-de-19-estados (2024); coordenada: sede do município (GeoNames); Portaria Ibama nº 114/2024 | `saofelix-t1`, `saofelix-t2` |
| Brigada Prevfogo/Ibama Santa Tereza do Tocantins (`prevfogo_santa_tereza`) | **oficial**: lista oficial da região, com fonte | Prevfogo/Ibama — https://sbtnews.sbt.com.br/noticia/brasil/ibama-autoriza-contratacao-de-brigadas-federais-para-combate-a-incendios-em-municipios-de-19-estados (2024); coordenada: sede do município (GeoNames); Portaria Ibama nº 114/2024 | `santatereza-t1` |
| Brigada Prevfogo/Ibama Itacajá (`prevfogo_itacaja`) | **oficial**: lista oficial da região, com fonte | Prevfogo/Ibama — https://sbtnews.sbt.com.br/noticia/brasil/ibama-autoriza-contratacao-de-brigadas-federais-para-combate-a-incendios-em-municipios-de-19-estados (2024); coordenada: sede do município (GeoNames); Portaria Ibama nº 114/2024 | `itacaja-t1` |
| Brigada Prevfogo/Ibama Arraias (`prevfogo_arraias`) | **oficial**: lista oficial da região, com fonte | Prevfogo/Ibama — https://sbtnews.sbt.com.br/noticia/brasil/ibama-autoriza-contratacao-de-brigadas-federais-para-combate-a-incendios-em-municipios-de-19-estados (2024); coordenada: sede do município (GeoNames); Portaria Ibama nº 114/2024 | `arraias-t1` |

Outras 6 base(s) conhecidas na região, sem recurso neste cenário: Brigada Prevfogo/Ibama Goiatins (oficial); ICMBio Esec Serra Geral do Tocantins em Rio da Conceição (oficial); Bombeiros (perto de Porangatu, 1 km) (OSM); SCI (Palmas) (OSM); Corpo de Bombeiros Militar (OSM); Bombeiros (perto de Barreiras, 1 km) (OSM).

## Pareceres do Analista

O Analista não foi chamado neste período.

## Memórias que influenciaram o plano (H-MEM)

Nenhuma memória foi usada neste período.

## Ciclo de revisão

- **Rodada 1:** veredicto do Crítico `rejeita`; 4 violações (exposta_nao_atendida, troca_recurso_local)
  - Troca de recurso local: dianopolis-t1 chega a cel_-117_-469 (22424 hab.) em 0.16 h, mas foi para cel_-122_-464 (4295 hab.) a 2.51 h; troco e cel_-122_-464 fica sem recurso (escalação).
- **Rodada 2:** veredicto do Crítico `escala`; 2 violações (exposta_nao_atendida)
  - Escalação: cel_-122_-464 tem 4295 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-121_-466 tem 4295 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.

## Limitações

- Detecção de satélite não confirma incêndio, e nuvens escondem focos.
- A distinção entre queima agrícola e incêndio é uma inferência com incerteza.
- A distância é em linha reta com um fator de correção; o ETA é uma estimativa.
- O GeoNames só lista localidades com 1.000+ habitantes.
- O índice de tempo é uma simplificação de superfície.
- A doutrina é simplificada, e não houve validação com operadores.

[Log completo da execução](trace.jsonl)

_Gerado em 2026-10-26 23:36 UTC_
