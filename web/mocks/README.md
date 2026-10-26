# Mocks for the front end

Real API responses, captured from `app.api` in sample mode (`SAMPLE_MODE=true`, cached real FIRMS data,
offline agents) on 26 Oct 2026. Use them to build screens without running the backend.
**The final app and the demo must call the API** (no hard-coded data in the UI); these files are for development only.

| File | Endpoint | Screen |
|---|---|---|
| `regioes.json` | `GET /api/regioes` | region selector |
| `periodos_tocantins.json` | `GET /api/periodos?regiao=tocantins` | period (day) selector |
| `bases_tocantins.json` | `GET /api/bases?regiao=tocantins` | "Recursos do dia": known bases with provenance (`confianca`, `fonte`) |
| `cenarios.json` | `GET /api/cenarios` | saved / repository scenarios |
| `cenario_tocantins-escasso.json` | `GET /api/cenarios/tocantins-escasso` | a scenario to edit (crews, reserve, notes) |
| `run_resposta_202.json` | `POST /api/run` with a `cenario` body (`idioma: en`) | "generate plan" → job id |
| `job_concluido.json` | `GET /api/jobs/{id}` (finished) | progress → link to the plan |
| `run_erro_422.json` | `POST /api/run` with a duplicated crew id | validation messages |
| `exemplos.json` | `GET /api/exemplos` | example list |
| `plano_tocantins-escasso-real.json` | `GET /api/exemplos/tocantins-escasso-real` | plan from the **real** run (Zetaris + Nemotron + H-MEM) |
| `plano_tocantins-escasso-en.json` | same, English | plan screen in English |
| `plano_tocantins-folgado.json` | same | plan with a local-crew swap |
| `plano_tocantins-escasso-com-nota.json` | same | plan changed by a coordinator note (memory) |
| `plano_tocantins-parana-analista.json` | same | plan with the Analyst's opinion and uncertainty |

The full API contract is in `web/README.md`.
