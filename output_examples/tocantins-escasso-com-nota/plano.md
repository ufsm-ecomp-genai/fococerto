# FocoCerto: plano do período 2026-10-23 (tocantins)

> **RECURSOS SIMULADOS: as equipes e aeronaves deste plano vêm de um cenário de demonstração (input_examples/tocantins-escasso.yaml), não de um inventário real.**
>
> **Bases: localização real com fonte; quantidade de equipes simulada (cenário).**
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
- **ESCALADA** `cel_-96_-468` (Lizarda, 5.5 km): Escalação: respeitar a memória deixa cel_-96_-468 (com população) sem recurso viável; decisão humana sobre usar a rota.

## Ordem de recursos

| Ordem | Recurso | Ocorrência | Prioridade | ETA |
|---|---|---|---|---|
| 1 | `palmas-a1` (aereo, CBMTO 1º BBM Palmas, base oficial) | `cel_-91_-474` (Centenário, 8.7 km) | 0.69 (alta) | 1.0 h |
| 2 | `portonac-t1` (terrestre, CBMTO 5ª Cia do 1º BBM Porto Nacional, base oficial) | `cel_-117_-491` (Gurupi, 8.8 km) | 0.66 (alta) | 4.4 h |
| 3 | `palmas-t1` (terrestre, CBMTO 1º BBM Palmas, base oficial) | `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km) | 0.64 (alta) | 3.4 h |
| 4 | `dianopolis-t1` (terrestre, CBMTO Companhia de Dianópolis, base oficial) | `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km) | 0.62 (alta) | 2.5 h |
| 5 | `paraiso-t1` (terrestre, CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins, base oficial) | `cel_-113_-493` (Dueré, 7.3 km) | 0.62 (média) | 4.5 h |

- **Recursos em reserva:** `saofelix-t1`
- **Ocorrências não atendidas:** `cel_-96_-468` (Lizarda, 5.5 km), `cel_-122_-473` (Conceição do Tocantins, 10.0 km), `cel_-105_-475` (Lagoa do Tocantins, 13.7 km), `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km), `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km), `cel_-95_-462` (Morros, 12.0 km), `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km), `cel_-95_-468` (Lizarda, 14.8 km), `cel_-107_-483` (Porto Nacional, 14.1 km), `cel_-117_-469` (Dianópolis, 4.6 km)

## Resumo do Planejador

[escala] Contra-proposta do Crítico (offline). 5 designações, 10 ocorrências sem recurso, 1 recursos em reserva.

## Lista de prioridades

_Prioridade calculada pelos dados (maior = mais urgente). Faixas relativas a este período: alta, média, baixa._

| # | Ocorrência | Prioridade | Status | Focos | FRP máx (MW) | Pop. no raio | Localidade mais próxima | Atendimento |
|---|---|---|---|---|---|---|---|---|
| 1 | `cel_-91_-474` | 0.69 (alta) | nova | 2 | 199.1 | 2135 | Centenário (8.7 km) | atendida por `palmas-a1` |
| 2 | `cel_-96_-468` | 0.69 (alta) | crescendo | 6 | 20.0 | 2991 | Lizarda (5.5 km) | **ESCALADA**; não atendida |
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

### 1. `palmas-a1` (aereo, CBMTO 1º BBM Palmas, base oficial) → `cel_-91_-474` (Centenário, 8.7 km), ETA 1.0 h

**Justificativa:** Prioridade 0.69; 2135 habitantes no raio; Centenário a 8.7 km; 2 focos, FRP somado 398 MW; palmas-a1 (aereo) chega em ETA 1.0 h saindo de CBMTO 1º BBM Palmas.

**Evidências:** `focos:2`, `eta:0.97`, `pop:2135`, `dist:Centenário:8.7`, `base:osm_n5067657890`

### 2. `portonac-t1` (terrestre, CBMTO 5ª Cia do 1º BBM Porto Nacional, base oficial) → `cel_-117_-491` (Gurupi, 8.8 km), ETA 4.4 h

**Justificativa:** Prioridade 0.66; 87545 habitantes no raio; Gurupi a 8.8 km; 8 focos, FRP somado 24 MW; portonac-t1 (terrestre) chega em ETA 4.4 h saindo de CBMTO 5ª Cia do 1º BBM Porto Nacional.

**Evidências:** `focos:8`, `eta:4.40`, `pop:87545`, `dist:Gurupi:8.8`, `base:cbmto_porto_nacional`

### 3. `palmas-t1` (terrestre, CBMTO 1º BBM Palmas, base oficial) → `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km), ETA 3.4 h

**Justificativa:** Prioridade 0.64; 7842 habitantes no raio; Ponte Alta do Tocantins a 10.3 km; 3 focos, FRP somado 23 MW; palmas-t1 (terrestre) chega em ETA 3.4 h saindo de CBMTO 1º BBM Palmas.

**Evidências:** `focos:3`, `eta:3.39`, `pop:7842`, `dist:Ponte Alta do Tocantins:10.3`, `base:osm_n5067657890`

### 4. `dianopolis-t1` (terrestre, CBMTO Companhia de Dianópolis, base oficial) → `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km), ETA 2.5 h

**Justificativa:** Prioridade 0.62; 4295 habitantes no raio; Ponte Alta do Bom Jesus a 10.0 km; 1 focos, FRP somado 38 MW; dianopolis-t1 (terrestre) chega em ETA 2.5 h saindo de CBMTO Companhia de Dianópolis.

**Evidências:** `focos:1`, `eta:2.51`, `pop:4295`, `dist:Ponte Alta do Bom Jesus:10.0`, `base:cbmto_dianopolis`

### 5. `paraiso-t1` (terrestre, CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins, base oficial) → `cel_-113_-493` (Dueré, 7.3 km), ETA 4.5 h

**Justificativa:** Prioridade 0.62; 4321 habitantes no raio; Dueré a 7.3 km; 4 focos, FRP somado 66 MW; paraiso-t1 (terrestre) chega em ETA 4.5 h saindo de CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins.

**Evidências:** `focos:4`, `eta:4.55`, `pop:4321`, `dist:Dueré:7.3`, `base:cbmto_paraiso`

## Bases e procedência

| Base | Procedência | Fonte | Recursos |
|---|---|---|---|
| CBMTO 1º BBM Palmas (`osm_n5067657890`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2023/01/16/1o-batalhao-e-quatro-companhias-de-bombeiros-militar-com-novos-comandos (2023); coordenada: quartel mapeado no OpenStreetMap (node/5067657890); id reaproveitado do OSM, a mesma unidade; fundida com osm_n5067657890 (OpenStreetMap: OpenStreetMap node/5067657890) | `palmas-t1`, `palmas-a1` |
| CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins (`cbmto_paraiso`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2023/01/27/companhia-de-bombeiros-em-paraiso-tem-novo-comandante-que-vai-atuar-frente-a-uma-das-cidades-mais-movimentadas-do-estado (2023); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `paraiso-t1` |
| CBMTO 5ª Cia do 1º BBM Porto Nacional (`cbmto_porto_nacional`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2022/02/17/governador-wanderlei-autoriza-inicio-das-obras-do-quartel-do-corpo-de-bombeiros-de-porto-nacional (2022); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `portonac-t1` |
| CBMTO Companhia de Dianópolis (`cbmto_dianopolis`) | **oficial**: lista oficial da região, com fonte | CBMTO — https://conexaoto.com.br/2023/01/16/1o-batalhao-e-quatro-companhias-de-bombeiros-militar-com-novos-comandos (2023); coordenada: sede do município (GeoNames); endereço do quartel não georreferenciado | `dianopolis-t1` |
| Brigada Prevfogo/Ibama São Félix do Tocantins (`prevfogo_sao_felix`) | **oficial**: lista oficial da região, com fonte | Prevfogo/Ibama — https://sbtnews.sbt.com.br/noticia/brasil/ibama-autoriza-contratacao-de-brigadas-federais-para-combate-a-incendios-em-municipios-de-19-estados (2024); coordenada: sede do município (GeoNames); Portaria Ibama nº 114/2024 | `saofelix-t1` |

Outras 11 base(s) conhecidas na região, sem recurso neste cenário: CBMTO 3º BBM Gurupi (oficial); CBMTO Companhia de Colinas do Tocantins (oficial); Brigada Prevfogo/Ibama Santa Tereza do Tocantins (oficial); Brigada Prevfogo/Ibama Itacajá (oficial); Brigada Prevfogo/Ibama Goiatins (oficial); Brigada Prevfogo/Ibama Arraias (oficial); ICMBio Esec Serra Geral do Tocantins em Rio da Conceição (oficial); Bombeiros (perto de Porangatu, 1 km) (OSM); SCI (Palmas) (OSM); Corpo de Bombeiros Militar (OSM); Bombeiros (perto de Barreiras, 1 km) (OSM).

## Pareceres do Analista

O Analista não foi chamado neste período.

## Memórias que influenciaram o plano (H-MEM)

- `tocantins:mem-1` (nota do coordenador, confiança 1.00, coordenador:enzo): estrada para São Félix alagada, sem acesso

## Ciclo de revisão

- **Rodada 1:** veredicto do Crítico `escala`; 14 violações (exposta_nao_atendida, restricao_memoria, troca_recurso_local)
  - Exceção aceita: memória tocantins:mem-1 ("estrada para São Félix alagada, sem acesso", confiança 1.00) vale sobre a regra da base mais próxima; saofelix-t1 não deve ir por terra a cel_-96_-468.
  - Troca de recurso local: dianopolis-t1 chega a cel_-117_-469 (22424 hab.) em 0.16 h, mas foi para cel_-122_-464 (4295 hab.) a 2.51 h; troco e cel_-122_-464 fica sem recurso (escalação).
  - Troca de recurso local: paraiso-t1 chega a cel_-107_-483 (53316 hab.) em 2.95 h, mas foi para cel_-113_-493 (4321 hab.) a 4.55 h; troco e cel_-113_-493 fica sem recurso (escalação).
  - Troca de recurso local: palmas-a1 chega a cel_-103_-478 (2463 hab.) em 0.37 h, mas foi para cel_-91_-474 (2135 hab.) a 0.97 h; troco e cel_-91_-474 fica sem recurso (escalação).
  - Escalação: respeitar a memória deixa cel_-96_-468 (com população) sem recurso viável; decisão humana sobre usar a rota.
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

[Log completo da execução](trace.jsonl)

_Gerado em 2026-10-26 18:14 UTC_
