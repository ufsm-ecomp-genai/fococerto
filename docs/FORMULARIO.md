# Submission form texts (HackOS)

Short texts ready to paste. Check every `[[...]]` before submitting. Keep the status lines honest: Nightshift runs against the real service since 25 Oct 2026, and Zetaris runs on a real instance since the evening of 25 Oct 2026 (full real run in `output_examples/tocantins-escasso-real/`). The evaluation numbers come from `eval/RELATORIO.md` (LLM-mode ablation of 25 Oct and its second run after the fixes, 25 Oct evening); if the ablation is re-run, update them. Test count measured on 26 Oct 2026.

---

## Final texts for the HackOS form (27 Oct)

### Description (1874 of 2,000 characters)
When there are more wildfires than crews, a regional fire coordinator has to decide which fires to answer first and with which crew. Dashboards show where the fire is; they do not propose a priority or record why. FocoCerto does.

It turns NASA FIRMS satellite detections, towns and population, weather and real fire stations (each with its public source) into a priority list and a resource order with travel times. A Planner (NVIDIA Nemotron through Meterless Nightshift) proposes who goes where. Deterministic tools check hard rules and every fact the model cites: town, distance, population, time and ids; wrong facts and invented crews are rewritten before review. A Critic judges the grey zone (trade-offs between towns, exceptions from the coordinator's field notes, when to escalate) and can call an Analyst for open questions such as "agricultural burn or wildfire?", answered with stated confidence. Any fire with exposed people left without a crew is escalated, naming which crews could have reached it and where each one went. Coordinator notes and lessons learned live in Meterless H-MEM, and data comes through Zetaris SQL views. Nothing is dispatched without human approval.

The coordinator works in a web app: one screen with the map, the fires that need a decision and a plan summary; a reasoning view with every round and the Critic's reasons; and a trace with each model call and its signed receipt. English or Portuguese.

Evidence: 12 scenarios on real data with answer keys committed before any run. With Nemotron, the full system passes 82.8% of the checks against 22.2% for a greedy allocator, and exposed people wait 2.8 h for a crew instead of 4.4 h. It runs end to end for real (Zetaris, Nemotron, H-MEM) and also offline in sample mode, without keys. Limits are stated: crew counts are simulated and it has not been validated with operators yet.

### Sponsor technology explanation (3698 of 4,000 characters)
ZETARIS (data layer). Zetaris 2.4 federates three source types: Postgres (NASA FIRMS detections), file-store CSVs (GeoNames towns and population, OpenStreetMap stations, an official Tocantins station list with one source URL per row) and an Open-Meteo REST table kept with CACHE TABLE. Four SQL views do the analysis in Zetaris itself: grouping detections into occurrences, nearby towns and exposure, weather context, and a transparent priority (exposure 35%, intensity 25%, weather 20%, persistence 10%, growth 10%). scripts/setup_zetaris.py registers everything with 0 failures; the priority view returns 698 occurrences, identical to our Python reference. The agents read only through these views, and every run logs the exact SQL it sent to Zetaris in its trace.

METERLESS H-MEM (engine). We run the official H-MEM reference engine as a TypeScript service and pass its official conformance suite (13/13, npm test in services/hmem). It powers a real feature: coordinator notes and lessons learned between periods change the next plan. "Road to São Félix flooded" keeps that station's crew off the road; a later "road reopened" supersedes the old note (nothing is deleted, the ledger keeps both) and the crew comes back. Between periods the system also writes derived memories, such as a fire left unattended that grew, which raise its priority the next day.

METERLESS NIGHTSHIFT (AI provider). Every agent call (Planner, Critic, Analyst) goes through one OpenAI-compatible client to Nightshift; nothing calls a model provider directly, and a test enforces it. Each call logs the requested model, the routed model and the signed receipt (meterless.compute_receipt.v1); the web app shows them in the trace. A finding: in its default "user" scope, Nightshift added about 4,900 tokens of context remembered from earlier calls to our prompts (the same prompt reached the model with 15,595 input tokens versus 10,682 in a fresh scope, and only then quoted memories it was never sent). That had contaminated our first evaluation runs. FocoCerto now sends its own scope per run, so the only memory in the system is H-MEM, which is audited, and we re-ran the evaluation clean.

NVIDIA (reasoning model). nvidia/nemotron-3-ultra-550b-a55b, through Nightshift, makes every agent decision: the Planner's resource order, the Critic's judgement of trade-offs and memory exceptions, and the Analyst's verdicts. Numbers always come from tools; Nemotron decides and explains. Everything it writes is checked: across 48 evaluation runs it wrote 44 wrong facts (towns, distances, populations and 2 invented crew ids) and the system rewrote every one before the Critic saw the plan, so no final plan carries a false citation. In one real run it claimed a fire near 87,545 people was "covered by gurupi-t1", a crew that does not exist; the system caught the invented id and the false coverage and escalated the fire. With Nemotron, the full system passes 82.8% of our answer-key checks against 22.2% for a greedy allocator. Reasoning is turned off (enable_thinking=false) so the model returns JSON within the token budget. More than 700 real Nemotron calls so far.

WHAT WAS UNIQUE. The sponsor technologies are not pass-throughs: the analysis lives in Zetaris views, H-MEM memory changes decisions and is superseded instead of deleted, every Nemotron decision carries a Nightshift receipt a judge can verify, and every fact the model writes is checked against the data. We measured it with answer keys committed before any run, and we found and fixed a hidden-context issue in the provider instead of publishing inflated numbers.

Full write-up: docs/PATROCINADORES.md in the repository. We did not use SpaceX AI.

---

## Project name
FocoCerto

## Tagline (one line)
When there are more wildfires than crews, FocoCerto proposes which fire to attend first and with whom, shows why, and lets a critic review the plan before the coordinator approves.

## Track (exactly one)
**Track 3: Reasoning Architecture**

## Team
Team ECOMP - UFSM (Universidade Federal de Santa Maria, Brazil). Members: [[names, as registered on HackOS]]

## Short description (~100 words)
FocoCerto is a multi-agent decision aid for regional wildfire coordinators. It turns NASA FIRMS heat detections, localities, real fire stations (each with its source) and weather into a priority list of occurrences and a resource order. A Planner proposes assignments, deterministic tools check hard rules and every cited fact, and a Critic judges the grey zone (trade-offs between communities, exceptions from the coordinator's field notes, when to escalate). The Critic can call an Analyst that answers "agricultural burning or native-vegetation fire?" with stated confidence. Memory across periods uses the Meterless H-MEM engine. Every assignment carries its evidence, the model's text is checked against the plan, plans come in English or Portuguese, and nothing is dispatched without human approval.

## Long description (~250 words)
**Problem.** When fires outnumber crews, the multi-agency coordination level must decide which incidents to attend first. Public dashboards show where the fire is; they do not propose a priority or record why. In our demo data (real VIIRS detections, Tocantins, Brazil, 23 Oct 2026) there are 179 occurrences, 52 near a town, for 6 crews (real, sourced stations; simulated crew counts).

**Solution.** Zetaris federates Postgres (FIRMS), file-store CSVs (GeoNames, OpenStreetMap, an official station list with a source per row) and an Open-Meteo REST table, and SQL views compute occurrences, exposure and a transparent priority. A LangGraph loop runs Planner → rule and citation checks → Critic, with up to 3 revision rounds, an Analyst on demand, and mandatory escalation ("request external support") when an occurrence with exposed population is left without a resource. Agents call NVIDIA Nemotron through Meterless Nightshift; each call logs the model, routed model and receipt. The Meterless H-MEM engine stores coordinator notes per region: "road to São Félix flooded" makes the Critic keep the Prevfogo crew of São Félix do Tocantins off that road; "road reopened" supersedes the old note and the crew comes back.

**Evidence.** H-MEM conformance 13/13; 331 tests passing (1 skipped, needs a throwaway Postgres); an A/B/C/D ablation on 12 scenarios with answer keys committed before any run, measured with NVIDIA Nemotron through Nightshift in a clean run (each run in its own Nightshift scope, 48 runs, 122 calls, 0 fallbacks): simple allocator 22.2%, Planner + checker 63.0%, full system 82.8%, full without memory 79.3%; exposed people wait 2.8 h for a crew instead of 4.4 h. Nemotron wrote 44 wrong facts (towns, distances, populations, 2 invented ids); the system rewrote every one before the Critic, and no final plan carries a false citation. We also found that Nightshift adds ~4,900 tokens of remembered context in its default user scope, which had contaminated our earlier runs; we isolate the scope per run so the only memory is the audited H-MEM. In a real English run Nemotron claimed that an occurrence with 87,545 exposed people was "covered by gurupi-t1", a resource that does not exist; the system flagged the invented id and the false coverage, rewrote the summary from the final assignments and escalated the occurrence. A sample mode runs the whole pipeline on cached real data with deterministic agents, without any service or key.

**Status, honestly.** Nightshift works against the real service (Nightshift for Windows on a team GPU machine over Tailscale, `nvidia/nemotron-3-ultra-550b-a55b`; one LLM-mode period ≈ 23 s with 2 calls); the LLM-mode ablation is complete (clean run with an isolated Nightshift scope: memory adds one decision in LLM mode, C − D = +1 check, and +18 offline; impasses 0 in the full system). The coverage check on the summary is a heuristic over two sentence forms. Zetaris works on a real instance (Zetaris 2.4 in Docker on a team server): setup with 0 failures, and the priority view returns 698 rows, equal to the Python reference. One full real run (data through Zetaris views, 4 Nemotron calls through Nightshift, real H-MEM service; 2 rounds, ~2.5 min) is in `output_examples/tocantins-escasso-real/`; the ablation itself reads a local cache of the same real data, not Zetaris. Station locations are real (public sources) but crew counts are simulated; there was no validation with operators.

## How we used the sponsor technologies (short)
- **Zetaris:** data layer; federates Postgres + file-store CSV + REST with `CACHE TABLE`; four views (`ocorrencias`, `ocorrencias_localidades`, `ocorrencias_contexto`, `ocorrencias_prioridade`) registered by `scripts/setup_zetaris.py`. Working on a real Zetaris 2.4: 0 setup failures, 1,875 real FIRMS detections federated, `ocorrencias_prioridade` returns 698 rows (equal to the Python reference); each run logs the SQL it sent to Zetaris.
- **Meterless Engine:** H-MEM (official reference, Apache-2.0, small marked adaptations for Portuguese). Powers coordinator notes that change the plan, supersedes, and per-region memory. Test: official conformance suite, 13/13 (`services/hmem`, `npm test`).
- **Meterless Nightshift:** primary AI provider for all agents through one OpenAI-compatible client; logs `modelo`, `routed_model`, `receipt`. Working against the real service since 25 Oct 2026: each call returns a signed receipt (`meterless.compute_receipt.v1`, Ed25519) whose `routed_model` and `receipt_id` go into the log.
- **NVIDIA:** Nemotron (`nvidia/nemotron-3-ultra-550b-a55b`) through Nightshift for the Planner, Critic and Analyst, writing the plan in the language of the run (`--idioma en|pt-BR`); every id, fact and coverage it cites is checked against the plan and rewritten if wrong; reasoning turned off (`chat_template_kwargs.enable_thinking=false`) because with it the model spent the 4096-token budget thinking and returned no JSON.
- Full write-up: `docs/PATROCINADORES.md`.

## Links
- Repository (public): [[https://github.com/...]]
- Demo video: [[link]]
- Slide deck: [[link]]
- Colab: not used (the project runs locally / in Docker).

## Pre-existing components (declaration)
- **Meterless H-MEM reference engine**, copied from `github.com/meterless/meterless` (`engines/hmem`, commit `1742dec`, 19 Oct 2026), Apache-2.0. Files in `services/hmem/src/engine/` (with changes marked "FocoCerto adaptation") and the unmodified conformance runner and vectors in `services/hmem/conformance/`. See `services/hmem/NOTICE`.
- **Open-source libraries:** LangGraph, pydantic, httpx, FastAPI, uvicorn, psycopg, PyYAML, pytest (Python); tsx (Node); Leaflet 1.9.4 (map, loaded from cdnjs). Versions pinned in `requirements.txt` and `services/hmem/package-lock.json`.
- **Public data downloaded during the build window:** NASA FIRMS VIIRS 7-day CSV, GeoNames `cities1000`, OpenStreetMap fire stations (Overpass), Open-Meteo forecast; the official Tocantins station list was compiled by the team from public sources (one URL per row in `config/regioes/tocantins_bases_oficiais.csv`). A small frozen cache (17–24 Oct 2026) is in `data/cache/` for sample mode.
- **No pre-existing product code.** All other code was written during the build window (first commit 24 Oct 2026). AI coding tool: Claude Code (Anthropic), used to write and review code, tests and docs; the team reviewed and tested it and is responsible for the result.

## Checklist before pressing submit
- [ ] Repository public; README renders, including the "AI and Model Usage" section.
- [ ] Evaluation numbers in the README, the form and the slides match `eval/RELATORIO.md` (re-check if the ablation was re-run).
- [ ] Example counts in the README match the current `output_examples/*/plano.md` (re-check after `scripts/gerar_exemplos.sh`).
- [ ] Status lines above match reality (Zetaris, Nightshift, Nemotron).
- [ ] Video 1–4 min, no tokens or keys on screen.
- [ ] Track 3 selected; roster correct before the first submission.
