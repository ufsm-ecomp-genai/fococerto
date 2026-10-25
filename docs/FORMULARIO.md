# Submission form texts (HackOS)

Short texts ready to paste. Check every `[[...]]` before submitting. Keep the status lines honest: Nightshift runs against the real service since 25 Oct 2026; update the Zetaris lines only after a real Zetaris run actually happens, and the evaluation lines only after the LLM-mode ablation has results.

---

## Project name
FocoCerto

## Tagline (one line)
When there are more wildfires than crews, FocoCerto proposes which fire to attend first and with whom, shows why, and lets a critic review the plan before the coordinator approves.

## Track (exactly one)
**Track 3: Reasoning Architecture**

## Team
Team UFSM (Universidade Federal de Santa Maria, Brazil). Members: [[names, as registered on HackOS]]

## Short description (~100 words)
FocoCerto is a multi-agent decision aid for regional wildfire coordinators. It turns NASA FIRMS heat detections, localities, fire stations and weather into a priority list of occurrences and a resource order. A Planner proposes assignments, deterministic tools check hard rules and every cited fact, and a Critic judges the grey zone (trade-offs between communities, exceptions from the coordinator's field notes, when to escalate). The Critic can call an Analyst that answers "agricultural burning or native-vegetation fire?" with stated confidence. Memory across periods uses the Meterless H-MEM engine. Every assignment carries its evidence, and nothing is dispatched without human approval.

## Long description (~250 words)
**Problem.** When fires outnumber crews, the multi-agency coordination level must decide which incidents to attend first. Public dashboards show where the fire is; they do not propose a priority or record why. In our demo data (real VIIRS detections, Tocantins, Brazil, 23 Oct 2026) there are 179 occurrences, 52 near a town, for 6 crews.

**Solution.** Zetaris federates Postgres (FIRMS), file-store CSVs (GeoNames, OpenStreetMap) and an Open-Meteo REST table, and SQL views compute occurrences, exposure and a transparent priority. A LangGraph loop runs Planner → rule and citation checks → Critic, with up to 3 revision rounds, an Analyst on demand, and mandatory escalation when an occurrence with exposed population is left without a resource. Agents call NVIDIA Nemotron through Meterless Nightshift; each call logs the model, routed model and receipt. The Meterless H-MEM engine stores coordinator notes per region: "road to Mateiros flooded" makes the Critic keep a crew off that road; "road reopened" supersedes the old note and the crew comes back.

**Evidence.** H-MEM conformance 13/13; 176 tests passing (1 skipped, needs a throwaway Postgres); real Nemotron calls through Nightshift, each logged with the routed model and a signed receipt id; an A/B/C/D ablation on 12 scenarios with answer keys committed before any run. A sample mode runs the whole pipeline on cached real data with deterministic agents, without any service or key.

**Status, honestly.** Nightshift works against the real service (Nightshift for Windows on a team GPU machine over Tailscale, `nvidia/nemotron-3-ultra-550b-a55b`; one LLM-mode period ≈ 23 s with 2 calls); the LLM-mode ablation [[is still running / results: ...]]. The Zetaris views were validated in a local Spark SQL against the Python logic (698/698 identical) but [[not yet tested on a real Zetaris instance]]. Resources are simulated; there was no validation with operators.

## How we used the sponsor technologies (short)
- **Zetaris:** data layer; federates Postgres + file-store CSV + REST with `CACHE TABLE`; four views (`ocorrencias`, `ocorrencias_localidades`, `ocorrencias_contexto`, `ocorrencias_prioridade`) registered by `scripts/setup_zetaris.py`. Views validated in a local Spark SQL 4.0 (698/698 identical to Python); not yet tested on a real Zetaris instance.
- **Meterless Engine:** H-MEM (official reference, Apache-2.0, small marked adaptations for Portuguese). Powers coordinator notes that change the plan, supersedes, and per-region memory. Test: official conformance suite, 13/13 (`services/hmem`, `npm test`).
- **Meterless Nightshift:** primary AI provider for all agents through one OpenAI-compatible client; logs `modelo`, `routed_model`, `receipt`. Working against the real service since 25 Oct 2026: each call returns a signed receipt (`meterless.compute_receipt.v1`, Ed25519) whose `routed_model` and `receipt_id` go into the log.
- **NVIDIA:** Nemotron (`nvidia/nemotron-3-ultra-550b-a55b`) through Nightshift for the Planner, Critic and Analyst; reasoning turned off (`chat_template_kwargs.enable_thinking=false`) because with it the model spent the 4096-token budget thinking and returned no JSON.
- Full write-up: `docs/PATROCINADORES.md`.

## Links
- Repository (public): [[https://github.com/...]]
- Demo video: [[link]]
- Slide deck: [[link]]
- Colab: not used (the project runs locally / in Docker).

## Pre-existing components (declaration)
- **Meterless H-MEM reference engine**, copied from `github.com/meterless/meterless` (`engines/hmem`, commit `1742dec`, 19 Oct 2026), Apache-2.0. Files in `services/hmem/src/engine/` (with changes marked "FocoCerto adaptation") and the unmodified conformance runner and vectors in `services/hmem/conformance/`. See `services/hmem/NOTICE`.
- **Open-source libraries:** LangGraph, pydantic, httpx, psycopg, PyYAML, pytest (Python); tsx (Node); Leaflet 1.9.4 (map, loaded from cdnjs). Versions pinned in `requirements.txt` and `services/hmem/package-lock.json`.
- **Public data downloaded during the build window:** NASA FIRMS VIIRS 7-day CSV, GeoNames `cities1000`, OpenStreetMap fire stations (Overpass), Open-Meteo forecast. A small frozen cache (17–24 Oct 2026) is in `data/cache/` for sample mode.
- **No pre-existing product code.** All other code was written during the build window (first commit 24 Oct 2026), with AI coding assistance.

## Checklist before pressing submit
- [ ] Repository public; README renders; `<!-- EVAL_RESULTS_LLM -->` filled in the README (or left with the "LLM-mode results pending" note).
- [ ] `<!-- NEMOTRON_LOG_EXCERPT -->` filled in `docs/PATROCINADORES.md` with a real `llm_call` log line (model, routed model, receipt id).
- [ ] Status lines above match reality (Zetaris, Nightshift, Nemotron).
- [ ] Video 1–4 min, no tokens or keys on screen.
- [ ] Track 3 selected; roster correct before the first submission.
