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
grep -q '"agente": "analista"' "output_examples/$nome/trace.jsonl" || { echo "erro: o Analista não foi chamado em $nome" >&2; exit 1; }
rm -rf data/estado "$TMP"
echo "ok: $(ls input_examples | wc -l) inputs, $(ls output_examples | wc -l) outputs"
