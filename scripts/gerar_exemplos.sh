#!/usr/bin/env bash
# Regenerates input_examples/ and output_examples/ from real --sample runs (cached real FIRMS data,
# offline deterministic agents). The app never reads these folders: they are documentation for judges.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
TMP=$(mktemp -d)
# Rewrites log_path in plano.json and the log link in plano.md to the copied trace.jsonl (repo-relative), so the
# examples never carry the /tmp path of the machine that generated them.
fix_log() {
  "$PY" - "$1" "$TMP" <<'PYEOF'
import json, re, sys
from pathlib import Path
pasta, tmp = Path(sys.argv[1]), sys.argv[2]
tr = pasta / "trace.jsonl"  # output paths inside the trace: $TMP/out-<nome>/<regiao>/<periodo>/x -> output_examples/<nome>/x
tr.write_text(re.sub(re.escape(tmp) + r"/out-[^/\"]+/[^/\"]+/[^/\"]+/", pasta.as_posix() + "/",
                     tr.read_text(encoding="utf-8")), encoding="utf-8")
pj = pasta / "plano.json"
d = json.loads(pj.read_text(encoding="utf-8"))
d["log_path"] = f"{pasta.as_posix()}/trace.jsonl"
pj.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
md = pasta / "plano.md"
md.write_text(re.sub(r"\]\([^)]*\.jsonl\)", "](trace.jsonl)", md.read_text(encoding="utf-8")), encoding="utf-8")
PYEOF
}
# only the folders this script regenerates (output_examples/ also holds hand-published runs that must stay:
# nemotron-trace/ and tocantins-escasso-real/)
GERADOS="tocantins-escasso tocantins-medio tocantins-folgado tocantins-escasso-com-nota tocantins-parana-analista
         tocantins-escasso-en"
rm -rf input_examples
for g in $GERADOS; do rm -rf "output_examples/$g"; done
mkdir -p input_examples output_examples
for c in cenarios/tocantins-escasso.yaml cenarios/tocantins-medio.yaml cenarios/tocantins-folgado.yaml; do
  nome=$(basename "$c" .yaml)
  cp "$c" "input_examples/$nome.yaml"
  rm -rf data/estado
  "$PY" -m app.cli run --sample --regiao tocantins --recursos "input_examples/$nome.yaml" \
        --saida "$TMP/out-$nome" --pasta-logs "$TMP/logs-$nome" > "$TMP/$nome.txt" 2>&1
  periodo=$("$PY" -c "import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))['periodo'])" "input_examples/$nome.yaml")
  mkdir -p "output_examples/$nome"
  cp "$TMP/out-$nome/tocantins/$periodo/"{plano.json,plano.md,mapa.html} "output_examples/$nome/"
  cp "$TMP"/logs-"$nome"/*.jsonl "output_examples/$nome/trace.jsonl"
  fix_log "output_examples/$nome"
done
# memory example: a coordinator note changes the next period's plan (H-MEM in sample mode)
rm -rf data/estado
nome=tocantins-escasso-com-nota
"$PY" -m app.cli nota --sample --regiao tocantins --periodo 2026-10-23 "estrada para São Félix alagada, sem acesso" > /dev/null 2>&1
"$PY" -m app.cli run --sample --regiao tocantins --recursos input_examples/tocantins-escasso.yaml \
      --saida "$TMP/out-$nome" --pasta-logs "$TMP/logs-$nome" > /dev/null 2>&1
mkdir -p "output_examples/$nome"
cp "$TMP/out-$nome/tocantins/2026-10-23/"{plano.json,plano.md,mapa.html} "output_examples/$nome/"
cp "$TMP"/logs-"$nome"/*.jsonl "output_examples/$nome/trace.jsonl"
fix_log "output_examples/$nome"
# Analyst example: a small recurring burn far from people (Paranã, 24/10). The Critic asks the Analyst
# "agricultural burn or vegetation fire?" before spending the only nearby resource on it. The input is the
# eval scenario eval/cenarios/agricola_recorrente_parana_24out.yaml copied as a plain scenario (eval-only
# fields removed: no answer key, no injected memories).
rm -rf data/estado
nome=tocantins-parana-analista
"$PY" - eval/cenarios/agricola_recorrente_parana_24out.yaml "input_examples/$nome.yaml" <<'PYEOF'
import sys, yaml
src, dst = sys.argv[1:]
d = yaml.safe_load(open(src, encoding="utf-8"))
for k in ("id", "tipo", "titulo", "situacao_nos_dados", "como_verificamos", "injecao", "memorias_iniciais"):
    d.pop(k, None)
cab = ("# DADOS SIMULADOS (simulado: true): recursos e bases de demonstração (cidades reais do GeoNames, unidade\n"
       "# não verificada). Focos, localidades e tempo são reais (cache FIRMS/GeoNames/Open-Meteo, 24/10/2026, dia parcial).\n"
       "# Copiado de eval/cenarios/agricola_recorrente_parana_24out.yaml sem os campos de avaliação.\n")
open(dst, "w", encoding="utf-8").write(cab + yaml.safe_dump(d, allow_unicode=True, sort_keys=False))
PYEOF
"$PY" -m app.cli run --sample --regiao tocantins --recursos "input_examples/$nome.yaml" \
      --saida "$TMP/out-$nome" --pasta-logs "$TMP/logs-$nome" > /dev/null 2>&1
mkdir -p "output_examples/$nome"
cp "$TMP/out-$nome/tocantins/2026-10-24/"{plano.json,plano.md,mapa.html} "output_examples/$nome/"
cp "$TMP"/logs-"$nome"/*.jsonl "output_examples/$nome/trace.jsonl"
fix_log "output_examples/$nome"
grep -q '"agente": "analista"' "output_examples/$nome/trace.jsonl" || { echo "erro: o Analista não foi chamado em $nome" >&2; exit 1; }
# English example: the same scarce scenario with --idioma en (labels AND content: justifications, Critic reasons,
# escalations, summary). Same input file as tocantins-escasso; only the language changes, not the decision.
rm -rf data/estado
nome=tocantins-escasso-en
"$PY" -m app.cli run --sample --regiao tocantins --recursos input_examples/tocantins-escasso.yaml --idioma en \
      --saida "$TMP/out-$nome" --pasta-logs "$TMP/logs-$nome" > /dev/null 2>&1
mkdir -p "output_examples/$nome"
cp "$TMP/out-$nome/tocantins/2026-10-23/"{plano.json,plano.md,mapa.html} "output_examples/$nome/"
cp "$TMP"/logs-"$nome"/*.jsonl "output_examples/$nome/trace.jsonl"
fix_log "output_examples/$nome"
grep -q '"idioma": "en"' "output_examples/$nome/plano.json" || { echo "erro: $nome não saiu em inglês" >&2; exit 1; }
rm -rf data/estado "$TMP"
n_out=0; for g in $GERADOS; do [ -f "output_examples/$g/plano.json" ] && n_out=$((n_out + 1)); done
echo "ok: $(ls input_examples | wc -l) inputs, $n_out generated outputs (kept: nemotron-trace, tocantins-escasso-real)"
