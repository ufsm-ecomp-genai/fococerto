"""Ponto de entrada do FocoCerto (docs/CONTRATOS.md, seção 9).

    python -m app.cli run --regiao R --periodo P --recursos cenarios/X.yaml [--sample] [--idioma pt-BR|en]
    python -m app.cli nota --regiao R "texto"
    python -m app.cli aprovar --regiao R --periodo P
    python -m app.cli avaliar [--modo offline|llm] [--repeticoes N] [--cenarios ID ...] [--sample]

SAMPLE_MODE=true (variável de ambiente) equivale a --sample em todos os subcomandos.
Idioma do plano (CONTRATOS §19): --idioma > idioma do POST /api/run > FOCOCERTO_IDIOMA > idioma do YAML da região.

Os módulos de outros donos (grafo dos agentes, repositório, cliente de memória) são importados
só quando o subcomando precisa deles. Se algum ainda não existir, a CLI diz qual e de quem é.
"""
from __future__ import annotations

import argparse
import getpass
import importlib
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

from app.core import config
from app.core.config import RAIZ
from app.core.logging import LogExecucao
from app.core.mensagens import IDIOMAS, normalizar_idioma, resolver_idioma
from app.core.models import Cenario, Plano, RegiaoCfg

DONOS = {
    "app.agents.grafo": "agentes-llm",
    "app.data.repositorio": "dados-zetaris",
    "app.memory_client": "hmem-engine",
    "app.llm.client": "agentes-llm",
    "app.agents.aprendizado": "agentes-llm",
    "eval.run_ablacao": "avaliacao",
}


class ErroCLI(Exception):
    """Erro com mensagem pronta para o coordenador (sem traceback)."""


class ErroDependencia(ErroCLI):
    pass


# ----------------------------------------------------------------------------- utilidades

def progresso(msg: str) -> None:
    print(f"[fococerto] {msg}", file=sys.stderr, flush=True)


def importar(modulo: str, *nomes: str):
    """Importa `nomes` de `modulo`. Se o módulo (ou um nome) não existir, levanta ErroDependencia clara."""
    try:
        mod = importlib.import_module(modulo)
    except ModuleNotFoundError as e:
        dono = DONOS.get(modulo, "?")
        if e.name and (e.name == modulo or modulo.startswith(e.name + ".")):
            raise ErroDependencia(
                f"O módulo {modulo} ainda não existe (dono: {dono}). "
                f"Esse subcomando depende dele; aguarde a entrega ou rode outro subcomando.") from e
        raise ErroDependencia(
            f"O módulo {modulo} (dono: {dono}) não carregou porque falta a dependência '{e.name}'. "
            f"Instale as dependências do projeto (pip install -e '.[dev]').") from e
    faltando = [n for n in nomes if not hasattr(mod, n)]
    if faltando:
        raise ErroDependencia(
            f"O módulo {modulo} existe, mas ainda não define {', '.join(faltando)} "
            f"(dono: {DONOS.get(modulo, '?')}; veja docs/CONTRATOS.md).")
    return [getattr(mod, n) for n in nomes] if len(nomes) != 1 else getattr(mod, nomes[0])


def verificar_modulos(necessarios: dict[str, tuple[str, ...]]) -> dict[str, object]:
    """Importa tudo de uma vez e junta os erros, para o coordenador ver todas as pendências juntas."""
    obtidos: dict[str, object] = {}
    erros: list[str] = []
    for modulo, nomes in necessarios.items():
        try:
            valores = importar(modulo, *nomes)
            valores = [valores] if len(nomes) == 1 else (valores or [])
            obtidos.update(dict(zip(nomes, valores)))
        except ErroDependencia as e:
            erros.append(f"  - {e}")
    if erros:
        raise ErroDependencia("Faltam módulos para executar este subcomando:\n" + "\n".join(erros))
    return obtidos


VERDADEIROS = {"1", "true", "yes", "sim", "on"}


def sample_por_ambiente() -> bool:
    """SAMPLE_MODE=true no ambiente (ou no .env) equivale a --sample (regras do hackathon, submissão §3.3)."""
    return (config.env("SAMPLE_MODE") or "").strip().lower() in VERDADEIROS


def modo_sample(args) -> bool:
    return bool(getattr(args, "sample", False)) or sample_por_ambiente()


def carregar_regiao(nome: str) -> RegiaoCfg:
    try:
        return config.regiao(nome)
    except FileNotFoundError as e:
        raise ErroCLI(f"Região '{nome}' não configurada: falta config/regioes/{nome}.yaml (dono: dados-zetaris).") from e


def carregar_cenario(caminho: Path) -> Cenario:
    if not caminho.exists():
        raise ErroCLI(f"Arquivo de recursos não encontrado: {caminho}")
    try:
        return config.cenario(caminho)
    except Exception as e:  # YAML inválido ou fora do formato Cenario
        raise ErroCLI(f"Cenário inválido em {caminho}: {e}") from e


def resolver_recursos(args) -> Path:
    if args.recursos:
        return Path(args.recursos)
    # Sem --recursos: usa o primeiro cenário da região em ordem alfabética (qualquer região, nada fixo).
    candidatos = sorted((RAIZ / "cenarios").glob(f"{args.regiao}-*.yaml"))
    if not candidatos:
        raise ErroCLI(f"Informe --recursos: não há cenarios/{args.regiao}-*.yaml.")
    progresso(f"--recursos não informado; usando {candidatos[0].relative_to(RAIZ)}")
    return candidatos[0]


def criar_repositorio(args):
    """RepositorioCache em --sample ou sem ZETARIS_API_KEY; senão RepositorioZetaris."""
    if modo_sample(args) or not config.env("ZETARIS_API_KEY"):
        motivo = "--sample/SAMPLE_MODE" if modo_sample(args) else "ZETARIS_API_KEY ausente"
        classe = importar("app.data.repositorio", "RepositorioCache")
        progresso(f"Dados: cache local (data/cache/) [{motivo}]")
    else:
        classe = importar("app.data.repositorio", "RepositorioZetaris")
        progresso("Dados: Zetaris")
    return classe()


def criar_memoria(args):
    """MemoriaLocal em --sample ou sem HMEM_URL; senão ClienteHMEM(HMEM_URL)."""
    url = config.env("HMEM_URL")
    if modo_sample(args) or not url:
        motivo = "--sample/SAMPLE_MODE" if modo_sample(args) else "HMEM_URL ausente"
        classe = importar("app.memory_client", "MemoriaLocal")
        caminho = config.RAIZ / "data" / "estado" / f"memoria_{getattr(args, 'regiao', None) or 'geral'}.json"
        progresso(f"Memória: MemoriaLocal persistida em {caminho.relative_to(config.RAIZ)} [{motivo}]")
        return classe(caminho=caminho)
    classe = importar("app.memory_client", "ClienteHMEM")
    progresso(f"Memória: H-MEM em {url}")
    return classe(url)


def idioma_execucao(args, regiao: RegiaoCfg) -> str:
    """Idioma efetivo do plano: --idioma (ou ``idioma`` do POST /api/run, que chega no mesmo campo) >
    FOCOCERTO_IDIOMA > RegiaoCfg.idioma > pt-BR. Valor explícito não suportado é erro; no ambiente ou no YAML da
    região, um idioma não suportado é ignorado (cai no próximo)."""
    pedido = getattr(args, "idioma", None)
    if pedido and not normalizar_idioma(pedido):
        raise ErroCLI(f"Idioma não suportado: {pedido!r}. Use um de {', '.join(IDIOMAS)} (ex.: en, en-US, pt, pt-BR).")
    return resolver_idioma(pedido, config.env("FOCOCERTO_IDIOMA"), regiao.idioma)


def escolher_modo(args) -> str:
    if modo_sample(args):
        os.environ["LLM_PROVIDER"] = "offline"  # garante que nenhum agente chame LLM no sample mode
        return "offline"
    return "offline" if (config.env("LLM_PROVIDER") or "").lower() == "offline" else "llm"


def caminho_log(caminho) -> str:
    """Relativo à raiz do repositório quando o log está dentro dela; absoluto quando está fora."""
    p = Path(caminho).resolve()
    try:
        return p.relative_to(RAIZ).as_posix()
    except ValueError:
        return str(p)


def pasta_saida(args, regiao: str, periodo: str) -> Path:
    return Path(args.saida) / regiao / periodo


class LogComProgresso(LogExecucao):
    """LogExecucao que também mostra cada evento no terminal (as chamadas de LLM são lentas)."""

    def evento(self, agente: str, evento: str, dados: dict | None = None, **llm) -> dict:
        linha = super().evento(agente, evento, dados, **llm)
        extra = ""
        if llm.get("modelo"):
            extra = f" modelo={llm.get('routed_model') or llm.get('modelo')}"
            if llm.get("latencia_s") is not None:
                extra += f" {llm['latencia_s']:.1f}s"
        resumo = ""
        if dados:
            for chave in ("regra", "decisao", "ocorrencia_id", "rodada", "motivo"):
                if chave in dados:
                    resumo += f" {chave}={str(dados[chave])[:60]}"
        progresso(f"  {agente}: {evento}{resumo}{extra}")
        return linha


# ----------------------------------------------------------------------------- subcomandos

def aprender_periodo_anterior(args, regiao: str, periodo: str, repo, memoria, log) -> list:
    """Memória derivada (H-MEM, especificação seção 7): antes do período P, compara o plano de P-1 (decisões
    aprovadas ou ``<saida>/<regiao>/<P-1>/plano.json``) com os dados de P e grava o que aprendeu.
    Sem plano de P-1, não faz nada. Falha aqui não impede o período (só fica no log)."""
    try:
        plano_anterior, aprender = importar("app.agents.aprendizado", "plano_anterior", "aprender_entre_periodos")
        plano, origem = plano_anterior(regiao, periodo, repo, Path(args.saida))
        if plano is None:
            progresso("Aprendizado: sem plano do período anterior; nenhuma memória derivada nova")
            return []
        gravadas = aprender(regiao, periodo, plano, repo, memoria, log)
        progresso(f"Aprendizado {plano.periodo} -> {periodo} (plano de {origem}): "
                  f"{len(gravadas)} memória(s) derivada(s) gravada(s)")
        for m in gravadas:
            progresso(f"  + {m.id}: {m.texto}")
        return gravadas
    except Exception as e:  # noqa: BLE001
        log.evento("sistema", "memoria_gravada", {"erro": f"{type(e).__name__}: {e}", "aprendizado": True})
        progresso(f"Aprendizado falhou ({type(e).__name__}: {e}); o período segue sem ele")
        return []


def cmd_run(args) -> int:
    from app.output import escrever_saidas

    progresso("Verificando módulos...")
    mods = verificar_modulos({"app.agents.grafo": ("executar_periodo",),
                              "app.data.repositorio": (), "app.memory_client": ()})
    executar_periodo = mods["executar_periodo"]

    regiao = carregar_regiao(args.regiao)
    arq = resolver_recursos(args)
    cenario = carregar_cenario(arq)
    if cenario.regiao != regiao.nome:
        raise ErroCLI(f"O cenário {arq} é da região '{cenario.regiao}', mas --regiao é '{regiao.nome}'.")
    periodo = args.periodo or cenario.periodo
    if args.periodo and args.periodo != cenario.periodo:
        progresso(f"--periodo {args.periodo} substitui o período do cenário ({cenario.periodo})")
        cenario = cenario.model_copy(update={"periodo": args.periodo})
    if cenario.simulado:
        progresso(f"AVISO: recursos SIMULADOS ({arq.name})")

    modo = escolher_modo(args)
    idioma = idioma_execucao(args, regiao)
    regiao = regiao.model_copy(update={"idioma": idioma})  # plano.md, mapa e meta.idioma usam o idioma efetivo
    progresso(f"Região {regiao.nome}, período {periodo}, {len(cenario.recursos)} recursos, modo {modo}, "
              f"idioma {idioma}")
    repo = criar_repositorio(args)
    memoria = criar_memoria(args)
    log = LogComProgresso(regiao.nome, periodo, pasta=Path(args.pasta_logs))
    progresso(f"Log: {log.caminho}")

    log.evento("sistema", "inicio", {"cenario": str(arq), "modo": modo, "sample": modo_sample(args),
                                      "simulado": cenario.simulado, "idioma": idioma})
    aprender_periodo_anterior(args, regiao.nome, periodo, repo, memoria, log)
    progresso("Rodando o ciclo Planejador/Crítico/Analista (pode demorar no modo LLM)...")
    t0 = time.monotonic()
    resultado = executar_periodo(regiao, cenario, repo, memoria, log, modo=modo, idioma=idioma)
    if not resultado.log_path:
        resultado = resultado.model_copy(update={"log_path": caminho_log(log.caminho)})
    progresso(f"Ciclo terminou em {time.monotonic() - t0:.1f}s, {resultado.rodadas} rodada(s)")
    consultas_zetaris = getattr(repo, "consultas", None)
    if consultas_zetaris is not None:
        # evidência exigida pelas regras: as consultas feitas à camada de dados (Zetaris)
        log.evento("ferramenta", "consulta", {"fonte": "zetaris", "modo_usado": getattr(repo, "modo_usado", None),
                                              "n_consultas": len(consultas_zetaris), "sql": consultas_zetaris})

    pasta = pasta_saida(args, regiao.nome, periodo)
    caminhos = escrever_saidas(resultado, regiao, cenario, pasta, modo=modo, arquivo_cenario=str(arq))
    log.evento("sistema", "fim", {"saidas": {k: str(v) for k, v in caminhos.items()},
                                   "designacoes": len(resultado.plano.designacoes),
                                   "escalacoes": len(resultado.escalacoes)})

    print(f"Plano: {len(resultado.plano.designacoes)} designação(ões), {len(resultado.escalacoes)} escalação(ões).")
    for e in resultado.escalacoes:
        print(f"  ESCALADO {e.get('ocorrencia_id') or '-'}: {e.get('motivo', '')}")
    for nome, c in caminhos.items():
        print(f"  {nome}: {c}")
    print(f"  log: {log.caminho}")
    print(f"Para aprovar: python -m app.cli aprovar --regiao {regiao.nome} --periodo {periodo}")
    return 0


def cmd_aprovar(args) -> int:
    arq = pasta_saida(args, args.regiao, args.periodo) / "plano.json"
    if not arq.exists():
        raise ErroCLI(f"Não há plano salvo em {arq}. Rode antes: python -m app.cli run --regiao {args.regiao} "
                      f"--periodo {args.periodo} --recursos cenarios/<cenario>.yaml")
    dados = json.loads(arq.read_text(encoding="utf-8"))
    plano = Plano(**dados["plano"])
    escalacoes = dados.get("escalacoes") or []
    autor = args.autor or getpass.getuser()
    repo = criar_repositorio(args)
    progresso(f"Gravando {len(plano.designacoes)} designação(ões) aprovadas por {autor}...")
    repo.salvar_decisoes(plano, aprovado_por=autor)
    LogComProgresso(args.regiao, args.periodo, pasta=Path(args.pasta_logs)).evento(
        "sistema", "aprova", {"aprovado_por": autor, "designacoes": len(plano.designacoes), "plano": str(arq)})
    print(f"Plano {args.regiao}/{args.periodo} aprovado por {autor}.")
    if escalacoes:
        print(f"Atenção: o plano tinha {len(escalacoes)} escalação(ões); a aprovação não as resolve.")
    return 0


def cmd_nota(args) -> int:
    texto = " ".join(args.texto).strip()
    if not texto:
        raise ErroCLI("A nota está vazia.")
    periodo = args.periodo or date.today().isoformat()
    autor = args.autor or getpass.getuser()
    repo = criar_repositorio(args)
    memoria = criar_memoria(args)
    progresso("Gravando a nota no banco de decisões...")
    repo.salvar_nota(args.regiao, periodo, texto, autor)
    progresso("Gravando a nota no H-MEM...")
    m = memoria.gravar(args.regiao, texto, tipo="nota", fonte=f"coordenador:{autor}")
    LogComProgresso(args.regiao, periodo, pasta=Path(args.pasta_logs)).evento(
        "sistema", "memoria_gravada", {"memoria_id": getattr(m, "id", None), "texto": texto, "autor": autor})
    print(f"Nota registrada ({args.regiao}, {periodo}) com memória {getattr(m, 'id', '?')}.")
    if getattr(m, "supersedes", None):
        print(f"  Substitui a memória {m.supersedes}.")
    return 0


def argv_ablacao(args) -> list[str]:
    """Argumentos de ``eval.run_ablacao.main`` a partir do ``avaliar``. --sample (ou SAMPLE_MODE) vira --modo offline."""
    modo = "offline" if modo_sample(args) else args.modo
    argv = ["--modo", modo]
    if args.repeticoes is not None:
        argv += ["--repeticoes", str(args.repeticoes)]
    if args.variantes:
        argv += ["--variantes", args.variantes]
    if args.cenarios:
        argv += ["--cenarios", *args.cenarios]
    if args.saida:
        argv += ["--saida", args.saida]
    return argv


def cmd_avaliar(args) -> int:
    main_ablacao = importar("eval.run_ablacao", "main")
    if args.regiao:
        progresso(f"--regiao {args.regiao} ignorado: os cenários da ablação (eval/cenarios/) já dizem a região")
    argv = argv_ablacao(args)
    progresso(f"Ablação: eval.run_ablacao.main({' '.join(argv)})")
    return int(main_ablacao(argv) or 0)


# ----------------------------------------------------------------------------- parser

def montar_parser() -> argparse.ArgumentParser:
    comum = argparse.ArgumentParser(add_help=False)
    comum.add_argument("--sample", action="store_true",
                       help="sem Zetaris, Nightshift ou chaves: dados em cache, MemoriaLocal e agentes offline "
                            "(o mesmo que SAMPLE_MODE=true)")
    comum.add_argument("--saida", default=str(RAIZ / "out"), help="pasta das saídas (padrão: out/)")
    comum.add_argument("--pasta-logs", default=str(RAIZ / "logs"), help=argparse.SUPPRESS)

    p = argparse.ArgumentParser(prog="python -m app.cli",
                                description="FocoCerto: prioridades e ordem de recursos entre incêndios simultâneos.")
    sub = p.add_subparsers(dest="comando", metavar="{run,nota,aprovar,avaliar}")

    r = sub.add_parser("run", parents=[comum], help="executa um período e gera plano.json, plano.md e mapa.html")
    r.add_argument("--regiao", default=None, help="região (config/regioes/<regiao>.yaml); padrão no --sample: tocantins")
    r.add_argument("--periodo", help="YYYY-MM-DD (padrão: o período do cenário)")
    r.add_argument("--recursos", help="cenarios/<nome>.yaml (padrão: o primeiro cenarios/<regiao>-*.yaml)")
    r.add_argument("--idioma", default=None,
                   help="idioma do plano inteiro: pt-BR ou en (aceita pt, en-US...); padrão: FOCOCERTO_IDIOMA ou o "
                        "idioma do YAML da região")
    r.set_defaults(func=cmd_run)

    n = sub.add_parser("nota", parents=[comum], help="registra uma observação do coordenador (Postgres + H-MEM)")
    n.add_argument("--regiao", required=True)
    n.add_argument("--periodo", help="YYYY-MM-DD (padrão: hoje)")
    n.add_argument("--autor", help="padrão: usuário do sistema")
    n.add_argument("texto", nargs="+", help='ex.: "estrada para São Félix alagada"')
    n.set_defaults(func=cmd_nota)

    a = sub.add_parser("aprovar", parents=[comum], help="grava as decisões do último plano salvo do período")
    a.add_argument("--regiao", required=True)
    a.add_argument("--periodo", required=True)
    a.add_argument("--autor", help="padrão: usuário do sistema")
    a.set_defaults(func=cmd_aprovar)

    v = sub.add_parser("avaliar", help="roda a ablação (eval/run_ablacao.py)")
    v.add_argument("--sample", action="store_true", help="equivale a --modo offline")
    v.add_argument("--modo", choices=["offline", "llm"], default="offline")
    v.add_argument("--repeticoes", type=int, default=None, help="padrão: o da ablação (3)")
    v.add_argument("--variantes", default=None, help="padrão: ABCD")
    v.add_argument("--cenarios", nargs="*", help="ids de eval/cenarios (padrão: todos)")
    v.add_argument("--saida", default=None, help="pasta dos resultados (padrão: eval/resultados/)")
    v.add_argument("--regiao", default=None, help="aceito por compatibilidade; os cenários já dizem a região")
    v.add_argument("--pasta-logs", default=str(RAIZ / "logs"), help=argparse.SUPPRESS)
    v.set_defaults(func=cmd_avaliar)
    return p


def main(argv: list[str] | None = None) -> int:
    config.carregar_env()
    parser = montar_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    # Aceita também "python -m app.cli --sample" (spec, seção 9): vira "run --sample".
    if argv and argv[0] == "--sample":
        argv = ["run", *argv]
    args = parser.parse_args(argv)
    if not getattr(args, "comando", None):
        parser.print_help()
        return 2
    if args.comando == "run" and args.regiao is None:
        if not modo_sample(args):
            parser.error("run: --regiao é obrigatório fora do --sample")
        args.regiao = "tocantins"
    try:
        return args.func(args)
    except ErroCLI as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
