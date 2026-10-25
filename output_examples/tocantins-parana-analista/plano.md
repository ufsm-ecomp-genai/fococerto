# FocoCerto: plano do período 2026-10-24 (tocantins)

> **RECURSOS SIMULADOS: as equipes e aeronaves deste plano vêm de um cenário de demonstração (input_examples/tocantins-parana-analista.yaml), não de um inventário real.**
>
> **Bases: 0 com localização real e fonte, 5 declarada(s) ou estimada(s) sem verificação (sim_guarai, sim_gurupi, sim_miracema, sim_paraiso, sim_parana); quantidade de equipes simulada (cenário).**
>
> Recomendação para o coordenador. Nada é despachado sem aprovação: `python -m app.cli aprovar --regiao tocantins --periodo 2026-10-24`

- **Situação:** ESCALADO: há decisões que precisam do coordenador
- Rodadas do ciclo Planejador/Crítico: 1
- **Modo:** offline (agentes determinísticos, sem LLM)

## Escalações: decisão humana necessária

- **ESCALADA** `cel_-83_-490` (Juarina, 14.5 km): Escalação: cel_-83_-490 tem 2305 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-88_-479` (Santa Maria do Tocantins, 10.4 km): Escalação: cel_-88_-479 tem 2726 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
- **ESCALADA** `cel_-90_-475` (Centenário, 11.7 km): Escalação: cel_-90_-475 tem 2135 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.

## Ordem de recursos

| Ordem | Recurso | Ocorrência | Prioridade | ETA |
|---|---|---|---|---|
| 1 | `paraiso-t1` (terrestre, Paraíso do Tocantins (simulada), base declarada) | `cel_-104_-489` (Pugmil, 6.2 km) | 0.61 (alta) | 0.8 h |
| 2 | `guarai-t1` (terrestre, Guaraí (simulada), base declarada) | `cel_-86_-487` (Itaporã do Tocantins, 2.0 km) | 0.59 (alta) | 1.2 h |
| 3 | `miracema-t1` (terrestre, Miracema do Tocantins (simulada), base declarada) | `cel_-93_-486` (Rio dos Bois, 12.8 km) | 0.56 (alta) | 1.4 h |
| 4 | `gurupi-t1` (terrestre, Gurupi (simulada), base declarada) | `cel_-117_-491` (Gurupi, 9.1 km) | 0.54 (alta) | 0.3 h |
| 5 | `parana-t1` (terrestre, Paranã (simulada), base declarada) | `cel_-124_-479` | 0.31 (baixa) | 1.2 h |

- **Recursos em reserva:** nenhum
- **Ocorrências não atendidas:** `cel_-88_-479` (Santa Maria do Tocantins, 10.4 km), `cel_-90_-475` (Centenário, 11.7 km), `cel_-83_-490` (Juarina, 14.5 km), `cel_-82_-461`, `cel_-96_-465`, `cel_-91_-479`, `cel_-105_-482`, `cel_-106_-481`, `cel_-104_-466`, `cel_-87_-495`

## Resumo do Planejador

[escala] Planejador offline (determinístico): população exposta primeiro; igual ao baseline. 5 designações, 10 ocorrências sem recurso, 0 recursos em reserva.

## Lista de prioridades

_Prioridade calculada pelos dados (maior = mais urgente). Faixas relativas a este período: alta, média, baixa._

| # | Ocorrência | Prioridade | Status | Focos | FRP máx (MW) | Pop. no raio | Localidade mais próxima | Atendimento |
|---|---|---|---|---|---|---|---|---|
| 1 | `cel_-104_-489` | 0.61 (alta) | nova | 4 | 2.4 | 2231 | Pugmil (6.2 km) | atendida por `paraiso-t1` |
| 2 | `cel_-86_-487` | 0.59 (alta) | nova | 3 | 2.9 | 2464 | Itaporã do Tocantins (2.0 km) | atendida por `guarai-t1` |
| 3 | `cel_-93_-486` | 0.56 (alta) | diminuindo | 4 | 2.6 | 2833 | Rio dos Bois (12.8 km) | atendida por `miracema-t1` |
| 4 | `cel_-117_-491` | 0.54 (alta) | diminuindo | 2 | 1.4 | 87545 | Gurupi (9.1 km) | atendida por `gurupi-t1` |
| 5 | `cel_-88_-479` | 0.49 (alta) | nova | 1 | 1.8 | 2726 | Santa Maria do Tocantins (10.4 km) | **ESCALADA**; não atendida |
| 6 | `cel_-90_-475` | 0.45 (média) | estavel | 2 | 0.7 | 2135 | Centenário (11.7 km) | **ESCALADA**; não atendida |
| 7 | `cel_-83_-490` | 0.43 (média) | nova | 1 | 1.1 | 2305 | Juarina (14.5 km) | **ESCALADA**; não atendida |
| 8 | `cel_-82_-461` | 0.40 (média) | crescendo | 4 | 3.5 | 0 | - | não atendida |
| 9 | `cel_-96_-465` | 0.38 (média) | crescendo | 3 | 3.7 | 0 | - | não atendida |
| 10 | `cel_-91_-479` | 0.38 (média) | crescendo | 4 | 3.0 | 0 | - | não atendida |
| 11 | `cel_-105_-482` | 0.33 (baixa) | nova | 5 | 1.5 | 0 | - | não atendida |
| 12 | `cel_-106_-481` | 0.32 (baixa) | crescendo | 3 | 1.8 | 0 | - | não atendida |
| 13 | `cel_-124_-479` | 0.31 (baixa) | crescendo | 2 | 0.9 | 0 | - | atendida por `parana-t1` |
| 14 | `cel_-104_-466` | 0.31 (baixa) | nova | 2 | 2.9 | 0 | - | não atendida |
| 15 | `cel_-87_-495` | 0.28 (baixa) | nova | 2 | 1.9 | 0 | - | não atendida |

## Justificativas e evidências

### 1. `paraiso-t1` (terrestre, Paraíso do Tocantins (simulada), base declarada) → `cel_-104_-489` (Pugmil, 6.2 km), ETA 0.8 h

**Justificativa:** Prioridade 0.61; 2231 habitantes no raio; Pugmil a 6.2 km; 4 focos, FRP somado 10 MW; paraiso-t1 (terrestre) chega em ETA 0.8 h saindo de Paraíso do Tocantins (simulada).

**Evidências:** `focos:4`, `eta:0.78`, `pop:2231`, `dist:Pugmil:6.2`, `base:sim_paraiso`

### 2. `guarai-t1` (terrestre, Guaraí (simulada), base declarada) → `cel_-86_-487` (Itaporã do Tocantins, 2.0 km), ETA 1.2 h

**Justificativa:** Prioridade 0.59; 2464 habitantes no raio; Itaporã do Tocantins a 2.0 km; 3 focos, FRP somado 7 MW; guarai-t1 (terrestre) chega em ETA 1.2 h saindo de Guaraí (simulada).

**Evidências:** `focos:3`, `eta:1.17`, `pop:2464`, `dist:Itaporã do Tocantins:2.0`, `base:sim_guarai`

### 3. `miracema-t1` (terrestre, Miracema do Tocantins (simulada), base declarada) → `cel_-93_-486` (Rio dos Bois, 12.8 km), ETA 1.4 h

**Justificativa:** Prioridade 0.56; 2833 habitantes no raio; Rio dos Bois a 12.8 km; 4 focos, FRP somado 7 MW; miracema-t1 (terrestre) chega em ETA 1.5 h saindo de Miracema do Tocantins (simulada).

**Evidências:** `focos:4`, `eta:1.45`, `pop:2833`, `dist:Rio dos Bois:12.8`, `base:sim_miracema`

### 4. `gurupi-t1` (terrestre, Gurupi (simulada), base declarada) → `cel_-117_-491` (Gurupi, 9.1 km), ETA 0.3 h

**Justificativa:** Prioridade 0.54; 87545 habitantes no raio; Gurupi a 9.1 km; 2 focos, FRP somado 3 MW; gurupi-t1 (terrestre) chega em ETA 0.3 h saindo de Gurupi (simulada).

**Evidências:** `focos:2`, `eta:0.32`, `pop:87545`, `dist:Gurupi:9.1`, `base:sim_gurupi`

### 5. `parana-t1` (terrestre, Paranã (simulada), base declarada) → `cel_-124_-479`, ETA 1.2 h

**Justificativa:** Prioridade 0.31; sem população no raio; 2 focos, FRP somado 2 MW; parana-t1 (terrestre) chega em ETA 1.2 h saindo de Paranã (simulada).

**Evidências:** `focos:2`, `eta:1.17`, `base:sim_parana`

## Bases e procedência

| Base | Procedência | Fonte | Recursos |
|---|---|---|---|
| Guaraí (simulada) (`sim_guarai`) | **declarada**: declarada pelo coordenador no cenário | GeoNames 3398573 | `guarai-t1` |
| Gurupi (simulada) (`sim_gurupi`) | **declarada**: declarada pelo coordenador no cenário | GeoNames 3461724 | `gurupi-t1` |
| Miracema do Tocantins (simulada) (`sim_miracema`) | **declarada**: declarada pelo coordenador no cenário | GeoNames 3394817 | `miracema-t1` |
| Paraíso do Tocantins (simulada) (`sim_paraiso`) | **declarada**: declarada pelo coordenador no cenário | GeoNames 3479329 | `paraiso-t1` |
| Paranã (simulada) (`sim_parana`) | **declarada**: declarada pelo coordenador no cenário | GeoNames 3455079 | `parana-t1` |

Outras 16 base(s) conhecidas na região, sem recurso neste cenário: CBMTO 1º BBM Palmas (oficial); CBMTO 3ª Cia do 1º BBM Paraíso do Tocantins (oficial); CBMTO 5ª Cia do 1º BBM Porto Nacional (oficial); CBMTO 3º BBM Gurupi (oficial); CBMTO Companhia de Dianópolis (oficial); CBMTO Companhia de Colinas do Tocantins (oficial); Brigada Prevfogo/Ibama São Félix do Tocantins (oficial); Brigada Prevfogo/Ibama Santa Tereza do Tocantins (oficial); Brigada Prevfogo/Ibama Itacajá (oficial); Brigada Prevfogo/Ibama Goiatins (oficial); Brigada Prevfogo/Ibama Arraias (oficial); ICMBio Esec Serra Geral do Tocantins em Rio da Conceição (oficial); Bombeiros (perto de Porangatu, 1 km) (OSM); SCI (Palmas) (OSM); Corpo de Bombeiros Militar (OSM); Bombeiros (perto de Barreiras, 1 km) (OSM).

## Pareceres do Analista

- `cel_-124_-479`: **indeterminado** (confiança: **baixa**)
  - Pergunta: Esta ocorrência é provavelmente queima agrícola ou de manejo recorrente, ou incêndio em vegetação nativa?
  - Evidências: `agrícola: FRP baixo (6.7 MW por foco)`, `vegetação: ocorrência crescendo em relação ao período anterior`, `agrícola: longe de TI/UC (sem TI/UC no raio)`, `escore agrícola−vegetação = +0.5 (limiar ±1,5; heurística não calibrada)`
  - Consultas feitas: `historico_celula(cel_-124_-479, dias=7)`, `padrao_dia_noite(cel_-124_-479, dias=7)`, `padrao_frp(cel_-124_-479, dias=7)`, `persistencia(cel_-124_-479, dias=7)`, `proximidade_ti_uc(cel_-124_-479)`, `tempo(cel_-124_-479)`, `exposicao(cel_-124_-479)`

## Memórias que influenciaram o plano (H-MEM)

Nenhuma memória foi usada neste período.

## Ciclo de revisão

- **Rodada 1:** veredicto do Crítico `escala`; 3 violações (exposta_nao_atendida)
  - Analista inconclusivo sobre cel_-124_-479 (indeterminado, baixa): designação mantida por precaução.
  - Escalação: cel_-88_-479 tem 2726 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-90_-475 tem 2135 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.
  - Escalação: cel_-83_-490 tem 2305 hab. expostos e os recursos viáveis estão em outras ocorrências com população ou na reserva.

## Limitações

- Detecção de satélite não confirma incêndio, e nuvens escondem focos.
- A distinção entre queima agrícola e incêndio é uma inferência com incerteza.
- A distância é em linha reta com um fator de correção; o ETA é uma estimativa.
- O GeoNames só lista localidades com 1.000+ habitantes.
- O índice de tempo é uma simplificação de superfície.
- A doutrina é simplificada, e não houve validação com operadores.

[Log completo da execução](trace.jsonl)

_Gerado em 2026-10-25 20:13 UTC_
