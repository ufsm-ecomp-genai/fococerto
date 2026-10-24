#!/usr/bin/env bash
# Regenerates input_examples/ and output_examples/ from real --sample runs (cached real FIRMS data,
# offline deterministic agents). The app never reads these folders: they are documentation for judges.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
TMP=$(mktemp -d)
rm -rf input_examples output_examples
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
done
# memory example: a coordinator note changes the next period's plan (H-MEM in sample mode)
rm -rf data/estado
nome=tocantins-escasso-com-nota
"$PY" -m app.cli nota --sample --regiao tocantins --periodo 2026-10-23 "estrada para Mateiros alagada, sem acesso" > /dev/null 2>&1
"$PY" -m app.cli run --sample --regiao tocantins --recursos input_examples/tocantins-escasso.yaml \
      --saida "$TMP/out-$nome" --pasta-logs "$TMP/logs-$nome" > /dev/null 2>&1
mkdir -p "output_examples/$nome"
cp "$TMP/out-$nome/tocantins/2026-10-23/"{plano.json,plano.md,mapa.html} "output_examples/$nome/"
cp "$TMP"/logs-"$nome"/*.jsonl "output_examples/$nome/trace.jsonl"
rm -rf data/estado "$TMP"
echo "ok: $(ls input_examples | wc -l) inputs, $(ls output_examples | wc -l) outputs"
