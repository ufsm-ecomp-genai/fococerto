#!/usr/bin/env python3
"""Checks the objective items of the hackathon submission checklist (dono: qa-integracao).

    python scripts/check_submissao.py            # exit 1 if any FAIL
    python scripts/check_submissao.py --strict   # WARN also fails

Only looks at what a judge gets from a clone: files tracked by git (plus untracked, non-ignored files,
flagged as such, so problems show up before the commit). Uses only the standard library.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PRAZO_PREEXISTENTE = "2026-10-22T00:00:00+00:00"

PADROES_SEGREDO = {
    "NVIDIA key (nvapi-)": re.compile(r"nvapi-[A-Za-z0-9_\-]{20,}"),
    "OpenAI-style key (sk-)": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "Slack token": re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "secret assigned to a long literal": re.compile(
        r"""(?i)\b[A-Z0-9_]*(TOKEN|API_KEY|APIKEY|SECRET|PASSWORD|PASSWD)[A-Z0-9_]*\s*[:=]\s*["']?([A-Za-z0-9/+_\-.]{24,})"""),
}
PLACEHOLDER = re.compile(r"(?i)replace|placeholder|your|example|changeme|xxx|<|\$\{|os\.environ|env\(")
DSN_COM_SENHA = re.compile(r"postgres(?:ql)?://[^:/\s\"']+:([^@\s\"']+)@")
SENHAS_DE_EXEMPLO = {"dev", "senha", "SENHA", "postgres", "password", "x", "placeholder", "pass"}
BINARIO = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".ico", ".woff", ".woff2", ".pyc", ".mp4"}

SECOES_README = {
    "setup / installation": r"(?im)^#+.*(setup|install)",
    "usage": r"(?im)^#+.*(usage|how to run|running|quick ?start)",
    "dependencies / requirements": r"(?im)^#+.*(dependenc|requirement|prerequisite)",
    "architecture": r"(?im)^#+.*architect",
    "agent roles": r"(?im)^#+.*(agent|role)",
    "examples": r"(?im)^#+.*example",
    "limitations": r"(?im)^#+.*limitation",
    "sample mode documented": r"(?i)--sample|SAMPLE_MODE",
    "Zetaris setup (or link to the Participant Setup Guide)": r"(?is)zetaris.*(setup|setup_zetaris|participant setup guide)",
    "Nightshift setup": r"(?i)nightshift",
    "sponsor technology (Zetaris, Meterless, NVIDIA)": r"(?is)(?=.*zetaris)(?=.*meterless)(?=.*nvidia)",
    "H-MEM conformance test documented (npm test)": r"(?is)(h-mem|hmem).*(npm test|conformance)|(npm test|conformance).*(h-mem|hmem)",
}


class Relatorio:
    def __init__(self) -> None:
        self.itens: list[tuple[str, str, str]] = []

    def add(self, status: str, item: str, detalhe: str = "") -> None:
        self.itens.append((status, item, detalhe))
        print(f"[{status:4}] {item}" + (f"\n         {detalhe}" if detalhe else ""))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True).stdout


def arquivos() -> tuple[list[str], set[str]]:
    rastreados = [f for f in git("ls-files", "-z").split("\0") if f]
    novos = {f for f in git("ls-files", "-o", "--exclude-standard", "-z").split("\0") if f}
    return [f for f in rastreados + sorted(novos) if (RAIZ / f).is_file()], novos


def env_lidas_pelo_codigo() -> set[str]:
    rx = re.compile(r"""(?:environ(?:\.get)?\(\s*|environ\[\s*|getenv\(\s*|\benv\(\s*)["']([A-Z][A-Z0-9_]+)["']"""
                    r"""|process\.env\.([A-Z][A-Z0-9_]+)|process\.env\[["']([A-Z][A-Z0-9_]+)["']\]""")
    achadas: set[str] = set()
    for pasta, globs in (("app", ["*.py"]), ("scripts", ["*.py"]), ("eval", ["*.py"]),
                         ("services/hmem/src", ["*.ts", "*.js", "*.mjs"])):
        for g in globs:
            for a in (RAIZ / pasta).rglob(g):
                if "node_modules" in a.parts:
                    continue
                for m in rx.finditer(a.read_text(encoding="utf-8", errors="ignore")):
                    achadas.add(next(x for x in m.groups() if x))
    return achadas


# ----------------------------------------------------------------------------- checks

def check_segredos(r: Relatorio, lista: list[str], novos: set[str]) -> None:
    achados = []
    for f in lista:
        p = RAIZ / f
        if p.suffix.lower() in BINARIO or p.stat().st_size > 5_000_000:
            continue
        texto = p.read_text(encoding="utf-8", errors="ignore")
        for i, linha in enumerate(texto.splitlines(), 1):
            for nome, rx in PADROES_SEGREDO.items():
                m = rx.search(linha)
                if m and not PLACEHOLDER.search(m.group(0)):
                    achados.append(f"{f}:{i} {nome}: {m.group(0)[:16]}…" + (" (untracked)" if f in novos else ""))
            m = DSN_COM_SENHA.search(linha)
            if m and len(m.group(1)) >= 6 and m.group(1) not in SENHAS_DE_EXEMPLO and not PLACEHOLDER.search(m.group(1)):
                achados.append(f"{f}:{i} Postgres DSN with a non-example password")
    r.add("FAIL" if achados else "OK", "no secrets in tracked/untracked files", "; ".join(achados[:10]))

    rastreado_env = [f for f in lista if re.fullmatch(r"(.*/)?\.env(\..+)?", f) and not f.endswith(".env.example")]
    r.add("FAIL" if rastreado_env else "OK", "no real .env committed", ", ".join(rastreado_env))

    try:
        hist = git("log", "--all", "-p", "--no-color", "-G", r"nvapi-|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}",
                   "--format=commit %h")
        commits = sorted(set(re.findall(r"^commit (\w+)", hist, re.M)))
        vazou = [c for c in commits if re.search(r"^\+.*(nvapi-[A-Za-z0-9_\-]{20,}|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16})",
                                                  git("show", "--format=", c), re.M)]
        r.add("FAIL" if vazou else "OK", "git history has no NVIDIA/AWS keys or private keys",
              f"commits: {vazou} (rewrite history or rotate the key)" if vazou else "")
    except subprocess.CalledProcessError as e:
        r.add("WARN", "git history scan", str(e))

    gi = (RAIZ / ".gitignore").read_text(encoding="utf-8") if (RAIZ / ".gitignore").exists() else ""
    r.add("OK" if re.search(r"(?m)^\.env$", gi) else "FAIL", ".gitignore ignores .env")
    falta_gi = [p for p in ("data/estado/", "services/hmem/data") if
                subprocess.run(["git", "check-ignore", "-q", p + ("x" if p.endswith("/") else "/x")],
                               cwd=RAIZ).returncode != 0]
    r.add("WARN" if falta_gi else "OK", "runtime state (memories, decisions) is git-ignored",
          f"not ignored: {falta_gi} (H-MEM service writes memories there by default)" if falta_gi else "")


def check_env_example(r: Relatorio) -> None:
    p = RAIZ / ".env.example"
    if not p.exists():
        r.add("FAIL", ".env.example exists")
        return
    r.add("OK", ".env.example exists")
    declaradas = set(re.findall(r"(?m)^#?\s*([A-Z][A-Z0-9_]+)=", p.read_text(encoding="utf-8")))
    faltam = sorted(env_lidas_pelo_codigo() - declaradas - {"HMEM_IMPL", "PATH"})
    r.add("WARN" if faltam else "OK", ".env.example lists every variable the code reads",
          f"missing: {faltam}" if faltam else f"{len(declaradas)} variables")
    suspeitos = [l for l in p.read_text(encoding="utf-8").splitlines()
                 if "=" in l and not l.lstrip().startswith("#") and re.search(r"=[A-Za-z0-9+_\-]{32,}$", l)
                 and not PLACEHOLDER.search(l)]
    r.add("FAIL" if suspeitos else "OK", ".env.example has placeholders only", "; ".join(suspeitos))


def check_logs(r: Relatorio, lista: list[str]) -> None:
    codigo = (RAIZ / "app" / "core" / "logging.py").read_text(encoding="utf-8")
    cria = "mkdir(parents=True, exist_ok=True)" in codigo
    no_repo = any(f.startswith("logs/") for f in lista)
    if no_repo:
        r.add("OK", "logs/ exists in the repo", ", ".join(f for f in lista if f.startswith("logs/"))[:200])
    elif cria:
        r.add("WARN", "logs/ is created at runtime (LogExecucao.mkdir) but has no committed example trace",
              "suggest committing the JSONL logs of the 3 example runs (e.g. under output_examples/<case>/ "
              "or logs/examples/), since logs/*.jsonl is git-ignored")
    else:
        r.add("FAIL", "logs/ exists or is created at runtime")


def check_exemplos(r: Relatorio, lista: list[str]) -> None:
    def contar(pasta: str) -> list[str]:
        return sorted({f.split("/")[1] for f in lista if f.startswith(pasta + "/") and f.count("/") >= 1})

    ent, sai = contar("input_examples"), contar("output_examples")
    cen = [f for f in lista if f.startswith("cenarios/") and f.endswith(".yaml")]
    if len(ent) >= 3 and len(sai) >= 3:
        r.add("OK", ">= 3 input and output examples", f"input={ent} output={sai}")
    else:
        r.add("FAIL", ">= 3 input examples (input_examples/) and matching outputs (output_examples/)",
              f"input_examples={ent or 'missing'} output_examples={sai or 'missing'}; there are {len(cen)} "
              "scenario files in cenarios/. Proposal: copy each cenarios/<x>.yaml to input_examples/<x>.yaml and "
              "generate output_examples/<x>/ with `python -m app.cli run --sample --recursos input_examples/<x>.yaml "
              "--saida /tmp/o` + copying plano.json, plano.md, mapa.html and the run's log. They are generated by "
              "the code (never read back by it); tests/test_integracao.py checks app/ never references them.")


def check_readme(r: Relatorio) -> None:
    p = RAIZ / "README.md"
    if not p.exists():
        r.add("FAIL", "README.md exists", "missing (owner: docs-submissao)")
        return
    texto = p.read_text(encoding="utf-8")
    faltam = [nome for nome, rx in SECOES_README.items() if not re.search(rx, texto)]
    r.add("FAIL" if faltam else "OK", "README covers the required sections", f"missing: {faltam}" if faltam else "")


def check_execucao(r: Relatorio, lista: list[str]) -> None:
    for f, nota in (("requirements.txt", "pip install -r requirements.txt"), ("Dockerfile", "strongly recommended")):
        r.add("OK" if f in lista else "FAIL", f"{f} present ({nota})",
              "untracked: commit it" if f in lista and f in set(git("ls-files", "-o", "--exclude-standard").split()) else "")
    hmem_lock = "services/hmem/package-lock.json" in lista
    r.add("OK" if hmem_lock else "WARN", "services/hmem/package-lock.json committed (npm ci reproducible)")
    rel = RAIZ / "services" / "hmem" / "conformance-report.txt"
    if rel.exists():
        ult = [l for l in rel.read_text(encoding="utf-8").splitlines() if "checks passed" in l]
        r.add("OK", "H-MEM conformance report committed", ult[-1].strip() if ult else "")


def check_tamanho(r: Relatorio, lista: list[str]) -> None:
    tam = sorted(((RAIZ / f).stat().st_size, f) for f in lista)
    total = sum(t for t, _ in tam)
    maiores = ", ".join(f"{f} {t / 1024:.0f}KB" for t, f in reversed(tam[-8:]))
    grandes = [f for t, f in tam if t > 5_000_000]
    r.add("FAIL" if grandes else ("WARN" if total > 50_000_000 else "OK"),
          f"repository is light ({len(tam)} files, {total / 1e6:.1f} MB)", "largest: " + maiores)


def check_preexistente(r: Relatorio) -> None:
    primeiro = git("log", "--reverse", "--format=%aI %h", "--all").splitlines()
    if not primeiro:
        return
    data, h = primeiro[0].split()
    from datetime import datetime
    antes = datetime.fromisoformat(data) < datetime.fromisoformat(PRAZO_PREEXISTENTE)
    r.add("WARN" if antes else "OK", "no commits before 22 Oct 2026 00:00 UTC (pre-existing work rule)",
          f"first commit {h} at {data}" + (" -> declare it in the submission form" if antes else ""))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--strict", action="store_true", help="WARN also counts as failure")
    args = ap.parse_args()
    lista, novos = arquivos()
    r = Relatorio()
    print(f"FocoCerto submission check ({len(lista)} files; {len(novos)} untracked)\n")
    check_segredos(r, lista, novos)
    check_env_example(r)
    check_logs(r, lista)
    check_exemplos(r, lista)
    check_readme(r)
    check_execucao(r, lista)
    check_tamanho(r, lista)
    check_preexistente(r)
    n = {s: sum(1 for x in r.itens if x[0] == s) for s in ("OK", "WARN", "FAIL")}
    print(f"\n{n['OK']} OK, {n['WARN']} WARN, {n['FAIL']} FAIL")
    return 1 if n["FAIL"] or (args.strict and n["WARN"]) else 0


if __name__ == "__main__":
    sys.exit(main())
