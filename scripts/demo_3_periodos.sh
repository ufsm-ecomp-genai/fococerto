#!/usr/bin/env bash
# Demonstração de 3 períodos em sample mode (dados reais do FIRMS em cache, agentes offline determinísticos,
# bases reais com fonte e QUANTIDADE de recursos simulada, cenário escasso). Mostra o H-MEM melhorando o plano de um período para outro:
#   - memória derivada: antes de cada período, o que ficou sem recurso no anterior e cresceu (app/agents/aprendizado.py);
#   - nota do coordenador: "estrada para São Félix alagada" e, depois, "estrada para São Félix liberada" (supersedes).
# Para cada período, imprime o que mudou por causa da memória: memórias gravadas e lidas, ocorrências puxadas
# para a lista, prioridades ajustadas e a diferença entre o plano com memória e o mesmo período sem memória.
#
# ATENÇÃO: apaga data/estado/memoria_<regiao>.json e data/estado/<regiao>/ no início (estado local do sample mode).
# Saídas e logs vão para um diretório temporário (impresso no fim).
#
# Uso: scripts/demo_3_periodos.sh [P1 P2 P3] (padrão: 2026-10-21 2026-10-22 2026-10-23)
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3
REGIAO=tocantins
CENARIO=cenarios/tocantins-escasso.yaml
P1="${1:-2026-10-21}"; P2="${2:-2026-10-22}"; P3="${3:-2026-10-23}"
TMP="$(mktemp -d -t fococerto-demo3-XXXX)"
SAIDA="$TMP/out"; LOGS="$TMP/logs"
export LLM_PROVIDER=offline

rm -f "data/estado/memoria_${REGIAO}.json"
rm -rf "data/estado/${REGIAO}"

cli() { "$PY" -m app.cli "$@" --sample --saida "$SAIDA" --pasta-logs "$LOGS"; }
run() { cli run --regiao "$REGIAO" --periodo "$1" --recursos "$CENARIO" >/dev/null 2>"$TMP/run_$1.err"; }
resumo() {
  "$PY" - "$REGIAO" "$1" "$CENARIO" "$SAIDA" "$LOGS" <<'EOF'
import json, sys
from pathlib import Path
from app.agents.grafo import executar_periodo
from app.core import config
from app.core.logging import LogExecucao
from app.data.repositorio import RepositorioCache
from app.memory_client import MemoriaLocal

regiao, periodo, cen, saida, logs = sys.argv[1:]
res = json.loads((Path(saida) / regiao / periodo / "plano.json").read_text(encoding="utf-8"))
log = Path(res["log_path"])
ev = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
print(f"\n=================== Período {periodo} ===================")
grav = [e["dados"] for e in ev if e["evento"] == "memoria_gravada" and "memoria_id" in e["dados"]]
apr = [e["dados"] for e in ev if e["dados"].get("consulta") == "aprendizado_entre_periodos"]
if apr:
    a = apr[0]
    print(f"Aprendizado {a['de']} -> {a['para']}: {a['sem_recurso_em_p_anterior']} sem recurso e "
          f"{a['designadas_em_p_anterior']} designada(s) no plano anterior; {len(grav)} memória(s) derivada(s) nova(s)")
else:
    print("Aprendizado: nenhum plano do período anterior (primeiro período)")
for g in grav:
    print(f"  + {g['memoria_id']} [{g['achado']}] {g['texto']}")
lida = [e["dados"] for e in ev if e["evento"] == "memoria_lida"]
for d in lida:
    if "ativas" in d:
        print(f"Memórias lidas do H-MEM: {len(d['ativas'])} ativa(s), {len(d['substituidas'])} substituída(s)")
        for m in d["ativas"]:
            print(f"  ativa {m['id']} ({m['tipo']}, via {d['vias'].get(m['id'])}): {m['texto']}")
        for m in d["substituidas"]:
            print(f"  SUBSTITUÍDA {m['id']}: {m['texto']}")
    if d.get("puxadas_por_memoria"):
        for p in d["puxadas_por_memoria"]:
            print(f"Puxada para a lista por memória: {p['ocorrencia_id']} ({p['n_focos']} focos, prioridade "
                  f"{p['prioridade']}) por {p['memoria_id']}")
    if "interpretacao" in d:
        i = d["interpretacao"]
        if i["bases_bloqueadas"]:
            print(f"Bases bloqueadas por memória: {i['bases_bloqueadas']}")
        if i["reforcos"]:
            print(f"Reforço de prioridade (+0,15) por memória: {i['reforcos']}")

# O mesmo período sem memória (variante D da ablação): o que muda por causa da memória.
cfg = config.regiao(regiao)
cenario = config.cenario(Path(cen)).model_copy(update={"periodo": periodo})
sem = executar_periodo(cfg, cenario, RepositorioCache(), MemoriaLocal(), LogExecucao(regiao, periodo, pasta=Path(logs)),
                       modo="offline", usar_memoria=False)
com = {(d["recurso_id"], d["ocorrencia_id"]) for d in res["plano"]["designacoes"]}
sm = {(d.recurso_id, d.ocorrencia_id) for d in sem.plano.designacoes}
print(f"Plano com memória: {len(com)} designação(ões), status {res['status']}, "
      f"{len(res['escalacoes'])} escalação(ões)")
for r, o in sorted(com):
    print(f"  {r:14s} -> {o}" + ("" if (r, o) in sm else "   [muda por causa da memória]"))
for r, o in sorted(sm - com):
    print(f"  (sem memória seria {r} -> {o})")
if com == sm:
    print("  Sem diferença nas designações em relação ao mesmo período sem memória.")
EOF
}

echo "Demo de 3 períodos (sample mode, cenário $CENARIO, bases reais com fonte, quantidade de recursos SIMULADA): $P1 -> $P2 -> $P3"
echo "Estado local limpo; saídas em $TMP"

run "$P1"; resumo "$P1"

echo; echo ">>> nota do coordenador ($P2): estrada para São Félix alagada"
cli nota --regiao "$REGIAO" --periodo "$P2" --autor coordenador "estrada para São Félix alagada" 2>/dev/null
run "$P2"; resumo "$P2"

echo; echo ">>> nota do coordenador ($P3): estrada para São Félix liberada"
cli nota --regiao "$REGIAO" --periodo "$P3" --autor coordenador "estrada para São Félix liberada" 2>/dev/null
run "$P3"; resumo "$P3"

echo; echo "Saídas e logs: $TMP"
