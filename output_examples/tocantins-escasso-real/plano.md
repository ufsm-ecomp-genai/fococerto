# FocoCerto: plano do período 2026-10-23 (tocantins)

> **RECURSOS SIMULADOS: as equipes e aeronaves deste plano vêm de um cenário de demonstração (cenarios/tocantins-escasso.yaml), não de um inventário real.**
>
> **Bases: localização real com fonte; quantidade de equipes simulada (cenário).**
>
> Recomendação para o coordenador. Nada é despachado sem aprovação: `python -m app.cli aprovar --regiao tocantins --periodo 2026-10-23`

- **Situação:** ESCALADO: há decisões que precisam do coordenador
- Rodadas do ciclo Planejador/Crítico: 2
- **Modo:** LLM

## Escalações: decisão humana necessária

- **ESCALADA** `cel_-91_-474` (Centenário, 8.7 km): Obrigatória: 2135 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo.
- **ESCALADA** `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km): Obrigatória: 4295 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo.
- **ESCALADA** `cel_-113_-493` (Dueré, 7.3 km): Obrigatória: 4321 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo.
- **ESCALADA** `cel_-122_-473` (Conceição do Tocantins, 10.0 km): Obrigatória: 3956 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo.
- **ESCALADA** `cel_-105_-475` (Lagoa do Tocantins, 13.7 km): Obrigatória: 3610 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo.
- **ESCALADA** `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km): Obrigatória: 29357 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo.
- **ESCALADA** `cel_-95_-462` (Morros, 12.0 km): Obrigatória: 4829 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo.
- **ESCALADA** `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km): Obrigatória: 4295 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo.
- **ESCALADA** `cel_-95_-468` (Lizarda, 14.8 km): Obrigatória: 2991 hab. expostos e nenhum recurso designado no plano final. Sugestão: solicitar apoio externo.

## Ordem de recursos

| Ordem | Recurso | Ocorrência | Prioridade | ETA |
|---|---|---|---|---|
| 1 | `palmas-a1` (aereo, CBMTO 1º BBM Palmas, base oficial) | `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km) | 0.60 (média) | 0.4 h |
| 2 | `saofelix-t1` (terrestre, Brigada Prevfogo/Ibama São Félix do Tocantins, base oficial) | `cel_-96_-468` (Lizarda, 5.5 km) | 0.69 (alta) | 2.4 h |
| 3 | `portonac-t1` (terrestre, CBMTO 5ª Cia do 1º BBM Porto Nacional, base oficial) | `cel_-117_-491` (Gurupi, 8.8 km) | 0.66 (alta) | 4.4 h |
| 4 | `palmas-t1` (terrestre, CBMTO 1º BBM Palmas, base oficial) | `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km) | 0.64 (alta) | 3.4 h |
| 5 | `dianopolis-t1` (terrestre, CBMTO Companhia de Dianópolis, base oficial) | `cel_-117_-469` (Dianópolis, 4.6 km) | 0.59 (baixa) | 0.2 h |
| 6 | `paraiso-t1` (terrestre, CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins, base oficial) | `cel_-107_-483` (Porto Nacional, 14.1 km) | 0.59 (baixa) | 3.0 h |

- **Recursos em reserva:** nenhum
- **Ocorrências não atendidas:** `cel_-91_-474` (Centenário, 8.7 km), `cel_-122_-464` (Ponte Alta do Bom Jesus, 10.0 km), `cel_-113_-493` (Dueré, 7.3 km), `cel_-122_-473` (Conceição do Tocantins, 10.0 km), `cel_-105_-475` (Lagoa do Tocantins, 13.7 km), `cel_-90_-486` (Fortaleza do Tabocão, 10.7 km), `cel_-95_-462` (Morros, 12.0 km), `cel_-121_-466` (Ponte Alta do Bom Jesus, 14.1 km), `cel_-95_-468` (Lizarda, 14.8 km)

## Resumo do Planejador

[escala] Seis recursos designados para seis ocorrências com população exposta, todos com ETA ≤ 6 h. Trocas obrigatórias aplicadas: palmas-a1 para cel_-103_-478 (2.463 hab., ETA 0,37 h), dianopolis-t1 para cel_-117_-469 (22.424 hab., ETA 0,16 h), paraiso-t1 para cel_-107_-483 (53.316 hab., ETA 2,95 h). Nove ocorrências permanecem sem recurso viável e devem ser escaladas: cel_-91_-474 (2.135 hab.), cel_-122_-464 (4.295 hab.), cel_-113_-493 (4.321 hab.), cel_-122_-473 (3.956 hab.), cel_-105_-475 (3.610 hab.), cel_-90_-486 (29.357 hab.), cel_-95_-462 (4.829 hab.), cel_-121_-466 (4.295 hab.), cel_-95_-468 (2.991 hab.). Desvios do baseline: palmas-a1 movida de cel_-91_-474 para cel_-103_-478 (troca_recurso_local: ganho 0,6 h, população maior) | dianopolis-t1 movida de cel_-122_-464 para cel_-117_-469 (troca_recurso_local: ganho 2,35 h, população 5× maior) | paraiso-t1 movida de cel_-113_-493 para cel_-107_-483 (troca_recurso_local: ganho 1,59 h, população 12× maior) Respostas ao Crítico: Violação troca_recurso_local: palmas-a1 em cel_-91_-474 (2.135 hab., ETA 0,97 h) enquanto cel_-103_-478 (2.463 hab., ETA 0,37 h) ganha 0,6 h e atende população maior; cel_-91_-474 deve ser escalada. -> adotado (Palmas-a1 realocada para cel_-103_-478 (pop 2.463, ETA 0,37 h) em vez de cel_-91_-474 (pop 2.135, ETA 0,97 h). Ganho de 0,6 h e população maior atendida. Cel_-91_-474 fica sem recurso e deve ser escalada.) | Violação troca_recurso_local: dianopolis-t1 em cel_-122_-464 (4.295 hab., ETA 2,51 h) enquanto cel_-117_-469 (22.424 hab., ETA 0,16 h) ganha 2,35 h e atende população 5× maior; cel_-122_-464 deve ser escalada. -> adotado (Dianopolis-t1 realocada para cel_-117_-469 (pop 22.424, ETA 0,16 h) em vez de cel_-122_-464 (pop 4.295, ETA 2,51 h). Ganho de 2,35 h e população 5× maior. Cel_-122_-464 fica sem recurso e deve ser escalada.) | Violação troca_recurso_local: paraiso-t1 em cel_-113_-493 (4.321 hab., ETA 4,55 h) enquanto cel_-107_-483 (53.316 hab., ETA 2,95 h) ganha 1,59 h e atende população 12× maior; cel_-113_-493 deve ser escalada. -> adotado (Paraíso-t1 realocada para cel_-107_-483 (pop 53.316, ETA 2,95 h) em vez de cel_-113_-493 (pop 4.321, ETA 4,55 h). Ganho de 1,59 h e população 12× maior. Cel_-113_-493 fica sem recurso e deve ser escalada.) | Violação troca_recurso_local: dianopolis-t1 também mais rápido para cel_-121_-466 (4.295 hab., ETA 1,78 h vs 2,51 h); ganho 0,74 h com mesma população. -> adotado (Dianopolis-t1 já realocada para cel_-117_-469 (ganho maior). Cel_-121_-466 fica sem recurso viável (palmas-a1 ETA 1,55 h mas já alocada) e deve ser escalada.) | Nove ocorrências com população exposta ficam sem recurso; após trocas obrigatórias, restam 6 expostas não atendidas (vs 9 no plano), reduzindo risco total. -> adotado (Plano atende 6 ocorrências com população exposta (vs 6 no plano anterior), mas prioriza as de maior população e menor ETA. Nove ocorrências permanecem sem recurso por limitação de efetivo (6 recursos disponíveis); as de maior população não atendidas são cel_-90_-486 (29.357 hab.) e cel_-122_-473 (3.956 hab.). Escalação necessária.)

## Lista de prioridades

_Prioridade calculada pelos dados (maior = mais urgente). Faixas relativas a este período: alta, média, baixa._

| # | Ocorrência | Prioridade | Status | Focos | FRP máx (MW) | Pop. no raio | Localidade mais próxima | Atendimento |
|---|---|---|---|---|---|---|---|---|
| 1 | `cel_-91_-474` | 0.69 (alta) | nova | 2 | 199.1 | 2135 | Centenário (8.7 km) | **ESCALADA**; não atendida |
| 2 | `cel_-96_-468` | 0.69 (alta) | crescendo | 6 | 20.0 | 2991 | Lizarda (5.5 km) | atendida por `saofelix-t1` |
| 3 | `cel_-117_-491` | 0.66 (alta) | nova | 8 | 4.0 | 87545 | Gurupi (8.8 km) | atendida por `portonac-t1` |
| 4 | `cel_-107_-476` | 0.64 (alta) | nova | 3 | 11.3 | 7842 | Ponte Alta do Tocantins (10.3 km) | atendida por `palmas-t1` |
| 5 | `cel_-122_-464` | 0.62 (alta) | nova | 1 | 38.4 | 4295 | Ponte Alta do Bom Jesus (10.0 km) | **ESCALADA**; não atendida |
| 6 | `cel_-113_-493` | 0.62 (média) | nova | 4 | 20.4 | 4321 | Dueré (7.3 km) | **ESCALADA**; não atendida |
| 7 | `cel_-122_-473` | 0.62 (média) | nova | 2 | 47.9 | 3956 | Conceição do Tocantins (10.0 km) | **ESCALADA**; não atendida |
| 8 | `cel_-105_-475` | 0.61 (média) | nova | 3 | 14.0 | 3610 | Lagoa do Tocantins (13.7 km) | **ESCALADA**; não atendida |
| 9 | `cel_-90_-486` | 0.61 (média) | nova | 2 | 12.1 | 29357 | Fortaleza do Tabocão (10.7 km) | **ESCALADA**; não atendida |
| 10 | `cel_-103_-478` | 0.60 (média) | crescendo | 11 | 7.1 | 2463 | Santa Tereza do Tocantins (9.8 km) | atendida por `palmas-a1` |
| 11 | `cel_-95_-462` | 0.60 (baixa) | nova | 1 | 9.5 | 4829 | Morros (12.0 km) | **ESCALADA**; não atendida |
| 12 | `cel_-121_-466` | 0.60 (baixa) | nova | 4 | 7.6 | 4295 | Ponte Alta do Bom Jesus (14.1 km) | **ESCALADA**; não atendida |
| 13 | `cel_-95_-468` | 0.59 (baixa) | nova | 1 | 6.0 | 2991 | Lizarda (14.8 km) | **ESCALADA**; não atendida |
| 14 | `cel_-107_-483` | 0.59 (baixa) | nova | 1 | 6.8 | 53316 | Porto Nacional (14.1 km) | atendida por `paraiso-t1` |
| 15 | `cel_-117_-469` | 0.59 (baixa) | nova | 1 | 8.7 | 22424 | Dianópolis (4.6 km) | atendida por `dianopolis-t1` |

## Justificativas e evidências

### 1. `palmas-a1` (aereo, CBMTO 1º BBM Palmas, base oficial) → `cel_-103_-478` (Santa Tereza do Tocantins, 9.8 km), ETA 0.4 h

**Justificativa:** Único recurso aéreo viável para cel_-103_-478 (ETA 0,37 h ≤ 6 h); população 2.463 em Santa Tereza do Tocantins a 9,8 km; prioridade 0,602; 11 focos, FRP 51,9 MW. Troca ganha 0,6 h e atende população maior que cel_-91_-474.

**Evidências:** `pop:2463`, `eta:0.37`, `dist:Santa Tereza do Tocantins:9.8`, `base:osm_n5067657890`, `focos:11`, `frp:51.9`

### 2. `saofelix-t1` (terrestre, Brigada Prevfogo/Ibama São Félix do Tocantins, base oficial) → `cel_-96_-468` (Lizarda, 5.5 km), ETA 2.4 h

**Justificativa:** Único recurso terrestre viável para cel_-96_-468 (ETA 2,35 h ≤ 6 h); população 2.991 em Lizarda a 5,5 km; prioridade 0,685; 6 focos, FRP 63,3 MW.

**Evidências:** `pop:2991`, `eta:2.35`, `dist:Lizarda:5.5`, `base:prevfogo_sao_felix`, `focos:6`, `frp:63.3`

### 3. `portonac-t1` (terrestre, CBMTO 5ª Cia do 1º BBM Porto Nacional, base oficial) → `cel_-117_-491` (Gurupi, 8.8 km), ETA 4.4 h

**Justificativa:** Maior população exposta (87.545 em Gurupi a 8,8 km); portonac-t1 chega em 4,4 h ≤ 6 h. Prioridade 0,658; 8 focos, FRP 24,5 MW.

**Evidências:** `pop:87545`, `eta:4.4`, `dist:Gurupi:8.8`, `base:cbmto_porto_nacional`, `focos:8`, `frp:24.5`

### 4. `palmas-t1` (terrestre, CBMTO 1º BBM Palmas, base oficial) → `cel_-107_-476` (Ponte Alta do Tocantins, 10.3 km), ETA 3.4 h

**Justificativa:** Palmas-t1 chega em 3,39 h ≤ 6 h; população 7.842 em Ponte Alta do Tocantins a 10,3 km. Prioridade 0,636; 3 focos, FRP 23,2 MW.

**Evidências:** `pop:7842`, `eta:3.39`, `dist:Ponte Alta do Tocantins:10.3`, `base:osm_n5067657890`, `focos:3`, `frp:23.2`

### 5. `dianopolis-t1` (terrestre, CBMTO Companhia de Dianópolis, base oficial) → `cel_-117_-469` (Dianópolis, 4.6 km), ETA 0.2 h

**Justificativa:** Troca obrigatória: população 22.424 em Dianópolis a 4,6 km; ETA 0,16 h ≤ 6 h (ganho 2,35 h vs cel_-122_-464). Prioridade 0,593; 1 foco, FRP 8,7 MW.

**Evidências:** `pop:22424`, `eta:0.16`, `dist:Dianópolis:4.6`, `base:cbmto_dianopolis`, `focos:1`, `frp:8.7`

### 6. `paraiso-t1` (terrestre, CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins, base oficial) → `cel_-107_-483` (Porto Nacional, 14.1 km), ETA 3.0 h

**Justificativa:** Troca obrigatória: população 53.316 em Porto Nacional a 14,1 km; ETA 2,95 h ≤ 6 h (ganho 1,59 h vs cel_-113_-493). Prioridade 0,594; 1 foco, FRP 6,8 MW.

**Evidências:** `pop:53316`, `eta:2.95`, `dist:Porto Nacional:14.1`, `base:cbmto_paraiso`, `focos:1`, `frp:6.8`

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

Nenhuma memória foi usada neste período.

## Ciclo de revisão

- **Rodada 1:** veredicto do Crítico `rejeita`; 13 violações (exposta_nao_atendida, troca_recurso_local)
  - Violação troca_recurso_local: palmas-a1 em cel_-91_-474 (2.135 hab., ETA 0,97 h) enquanto cel_-103_-478 (2.463 hab., ETA 0,37 h) ganha 0,6 h e atende população maior; cel_-91_-474 deve ser escalada.
  - Violação troca_recurso_local: dianopolis-t1 em cel_-122_-464 (4.295 hab., ETA 2,51 h) enquanto cel_-117_-469 (22.424 hab., ETA 0,16 h) ganha 2,35 h e atende população 5× maior; cel_-122_-464 deve ser escalada.
  - Violação troca_recurso_local: paraiso-t1 em cel_-113_-493 (4.321 hab., ETA 4,55 h) enquanto cel_-107_-483 (53.316 hab., ETA 2,95 h) ganha 1,59 h e atende população 12× maior; cel_-113_-493 deve ser escalada.
  - Violação troca_recurso_local: dianopolis-t1 também mais rápido para cel_-121_-466 (4.295 hab., ETA 1,78 h vs 2,51 h); ganho 0,74 h com mesma população.
  - Nove ocorrências com população exposta ficam sem recurso; após trocas obrigatórias, restam 6 expostas não atendidas (vs 9 no plano), reduzindo risco total.
- **Rodada 2:** veredicto do Crítico `aprova`; 9 violações (exposta_nao_atendida)
  - Todos os 6 recursos designados cumprem ETA ≤ 6h (regra rígida).
  - As 3 trocas obrigatórias (troca_recurso_local) foram aplicadas corretamente: palmas-a1 para cel_-103_-478 (ganho 0,6h, pop maior), dianopolis-t1 para cel_-117_-469 (ganho 2,35h, pop 5× maior), paraiso-t1 para cel_-107_-483 (ganho 1,59h, pop 12× maior).
  - portonac-t1 atende a maior população exposta (87.545 em Gurupi) dentro do tempo limite (4,4h).
  - saofelix-t1 é o único recurso terrestre viável para cel_-96_-468 (ETA 2,35h).
  - palmas-t1 atende cel_-107_-476 (pop 7.842, ETA 3,39h) dentro do limite.
  - As 9 violações 'exposta_nao_atendida' são não-rígidas e decorrem de limitação objetiva de efetivo (6 recursos para 15 ocorrências com exposição).
  - O plano segue a prioridade composta (exposição, intensidade, tempo, persistência, crescimento) e não há violações rígidas nem citações incorretas.

## Limitações

- Detecção de satélite não confirma incêndio, e nuvens escondem focos.
- A distinção entre queima agrícola e incêndio é uma inferência com incerteza.
- A distância é em linha reta com um fator de correção; o ETA é uma estimativa.
- O GeoNames só lista localidades com 1.000+ habitantes.
- O índice de tempo é uma simplificação de superfície.
- A doutrina é simplificada, e não houve validação com operadores.

[Log completo da execução](../../../logs/20261025T232253-bbd48f.jsonl)

_Gerado em 2026-10-25 23:25 UTC_
