#!/usr/bin/env bash
# Reproduces what a judge does: fresh clone -> venv -> pip install -r requirements.txt -> pytest -> run --sample
# -> (if node exists) npm ci && npm test in services/hmem. Nothing from the working copy leaks in
# (no .env, no .venv, no data/estado, no node_modules).
#
# Usage: scripts/check_clean_clone.sh [repo-dir-or-url]
#   INCLUDE_UNCOMMITTED=1  also copy modified/untracked (non-ignored) files from the working copy,
#                          to test before committing. The default tests only what is committed.
#   KEEP=1                 keep the temporary folder at the end.
#   PYTHON=python3.12      interpreter used to create the venv.
set -euo pipefail

SRC="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PY="${PYTHON:-python3}"
TMP="$(mktemp -d -t fococerto-clean-XXXXXX)"
DEST="$TMP/fococerto"
FALHAS=()

cleanup() { if [[ "${KEEP:-0}" == "1" ]]; then echo "kept: $TMP"; else rm -rf "$TMP"; fi; }
trap cleanup EXIT
passo() { echo; echo "=== $* ==="; }
falha() { echo "FAIL: $*"; FALHAS+=("$*"); }

passo "clone $SRC"
git clone --quiet "$SRC" "$DEST"
echo "HEAD: $(git -C "$DEST" log -1 --format='%h %s')"
if [[ "${INCLUDE_UNCOMMITTED:-0}" == "1" && -d "$SRC/.git" ]]; then
  echo "INCLUDE_UNCOMMITTED=1: copying modified/untracked files from the working copy:"
  (cd "$SRC" && git ls-files -m -o --exclude-standard -z) | while IFS= read -r -d '' f; do
    if [[ -f "$SRC/$f" ]]; then mkdir -p "$DEST/$(dirname "$f")"; cp "$SRC/$f" "$DEST/$f"; echo "  + $f"; fi
  done
fi
cd "$DEST"
if [[ -e .env ]]; then falha ".env is committed"; fi
du -sh --exclude=.git . | sed 's/^/repo size without .git: /'

passo "venv + pip install -r requirements.txt ($("$PY" --version))"
"$PY" -m venv .venv
if [[ ! -f requirements.txt ]]; then
  falha "requirements.txt missing in the clone"
  echo "fallback: pip install -e .[dev]"; .venv/bin/pip install -q -e ".[dev]" > "$TMP/pip.err" 2>&1 || { grep -m1 "error:" "$TMP/pip.err" || true; falha "pip install -e .[dev] (pyproject.toml)"; }
else
  .venv/bin/pip install -q --disable-pip-version-check -r requirements.txt || falha "pip install -r requirements.txt"
fi

TEM_NODE=0
if command -v node > /dev/null && command -v npm > /dev/null; then TEM_NODE=1; fi
if (( TEM_NODE )); then
  passo "npm ci in services/hmem (node $(node --version)); before pytest so the H-MEM HTTP tests run"
  (cd services/hmem && npm ci --no-audit --no-fund --silent) || falha "npm ci"
fi

passo "pytest"
if .venv/bin/python -m pytest -q -p no:cacheprovider > "$TMP/pytest.out" 2>&1; then
  tail -n 3 "$TMP/pytest.out"
else
  tail -n 30 "$TMP/pytest.out"; falha "pytest"
fi

passo "run --sample (empty environment: no .env, no keys)"
OUT="$TMP/saida"
if env -u ZETARIS_API_KEY -u HMEM_URL -u METERLESS_RUNTIME_TOKEN -u LLM_PROVIDER \
    .venv/bin/python -m app.cli run --sample --regiao tocantins --recursos cenarios/tocantins-escasso.yaml \
    --saida "$OUT" > "$TMP/run.out" 2> "$TMP/run.err"; then
  head -n 1 "$TMP/run.out"
  for f in plano.json plano.md mapa.html; do
    if [[ -s "$OUT/tocantins/2026-10-23/$f" ]]; then echo "  ok $f"; else falha "missing $f"; fi
  done
  LOG="$(ls -t logs/*.jsonl 2>/dev/null | head -n 1 || true)"
  if [[ -n "$LOG" ]]; then echo "  ok log $LOG ($(wc -l < "$LOG") lines)"; else falha "no logs/*.jsonl"; fi
else
  tail -n 20 "$TMP/run.err"; falha "run --sample"
fi

passo "python -m app.cli --sample (shortcut documented in the spec)"
if .venv/bin/python -m app.cli --sample --saida "$TMP/saida2" > /dev/null 2>&1; then echo "  ok"; else falha "app.cli --sample"; fi

passo "H-MEM conformance (services/hmem)"
if (( TEM_NODE )); then
  if (cd services/hmem && npm test > "$TMP/npm.out" 2>&1); then tail -n 2 "$TMP/npm.out"; else tail -n 20 "$TMP/npm.out"; falha "npm test"; fi
else
  echo "node not found: skipped"
fi

passo "result"
if (( ${#FALHAS[@]} )); then printf 'FAILED: %s\n' "${FALHAS[@]}"; exit 1; fi
echo "OK: clean clone installs, tests pass and sample mode runs"
