"""Carrega cenários/gabaritos da avaliação, confere checagens e calcula métricas (método em eval/README.md).

Trabalha sobre um "resultado" em dict (``ResultadoPeriodo.model_dump(mode="json")`` mais os campos
``variante`` e ``injecao_aplicada``), para poder ser testado com resultados sintéticos.
"""
from __future__ import annotations

import math
import re
import statistics
from pathlib import Path

import yaml

from app.core.models import Cenario

RAIZ_EVAL = Path(__file__).resolve().parent
DIR_CENARIOS = RAIZ_EVAL / "cenarios"
DIR_GABARITOS = RAIZ_EVAL / "gabaritos"

FATOR_PENALIDADE = 2.0  # exposta não atendida conta como FATOR_PENALIDADE × eta_max_h no ETA ponderado
VARIANTES_COM_ANALISTA = {"C", "D"}
VARIANTES_COM_CHECADOR = {"B", "C", "D"}

TIPOS = {"recurso_nao_designado", "recurso_designado_para", "recurso_nao_designado_para", "ocorrencia_atendida",
         "ocorrencia_nao_atendida", "ocorrencia_atendida_ou_escalada", "prioriza", "status",
         "expostas_nao_atendidas_escaladas", "parecer_conclusao", "citacao_detectada_rodada1",
         "rodada1_nao_aprovada", "texto_ausente_plano_final"}
CATEGORIAS = {"decisao", "deteccao", "alarme_falso"}


# ------------------------------------------------------------------ carga
def carregar_cenario(caminho: str | Path) -> dict:
    """Devolve {"meta": dict com tudo, "cenario": Cenario}."""
    d = yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))
    cen = Cenario.model_validate({k: v for k, v in d.items() if k in Cenario.model_fields})
    return {"meta": d, "cenario": cen}


def carregar_gabarito(caminho: str | Path) -> dict:
    g = yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))
    for c in g.get("checagens", []):
        if c["tipo"] not in TIPOS:
            raise ValueError(f"{caminho}: tipo de checagem desconhecido {c['tipo']!r}")
        if c["categoria"] not in CATEGORIAS:
            raise ValueError(f"{caminho}: categoria desconhecida {c['categoria']!r}")
    return g


def listar_casos(filtro: list[str] | None = None, dir_cenarios: Path | None = None,
                 dir_gabaritos: Path | None = None) -> list[tuple[dict, dict]]:
    """Pares (cenário, gabarito) por id. Todo cenário precisa de gabarito e vice-versa."""
    cen = {p.stem: p for p in sorted(Path(dir_cenarios or DIR_CENARIOS).glob("*.yaml"))}
    gab = {p.stem: p for p in sorted(Path(dir_gabaritos or DIR_GABARITOS).glob("*.yaml"))}
    if set(cen) != set(gab):
        raise ValueError(f"cenários sem gabarito: {sorted(set(cen) - set(gab))}; "
                         f"gabaritos sem cenário: {sorted(set(gab) - set(cen))}")
    ids = [i for i in cen if not filtro or i in filtro]
    return [(carregar_cenario(cen[i]), carregar_gabarito(gab[i])) for i in ids]


# ------------------------------------------------------------------ leitura do resultado
def _designacoes(res: dict) -> list[dict]:
    return res["plano"]["designacoes"]


def _atendidas(res: dict) -> dict[str, float]:
    """ocorrencia_id -> menor eta_h entre as designações do plano final."""
    out: dict[str, float] = {}
    for d in _designacoes(res):
        out[d["ocorrencia_id"]] = min(out.get(d["ocorrencia_id"], math.inf), float(d["eta_h"]))
    return out


CELULA = re.compile(r"cel_-?\d+_-?\d+")


def _escalada(res: dict, oid: str) -> bool:
    for e in res.get("escalacoes") or []:
        if e.get("ocorrencia_id") == oid or oid in (e.get("motivo") or ""):
            return True
    return False


def _rodada1(res: dict) -> dict | None:
    h = res.get("historico") or []
    return h[0] if h else None


# ------------------------------------------------------------------ checagens
def checar(chk: dict, res: dict) -> dict:
    """Devolve {id, tipo, categoria, descricao, resultado: passou|falhou|nao_se_aplica|invalido, detalhe}."""
    t, p, var = chk["tipo"], chk.get("params") or {}, res.get("variante")
    atend = _atendidas(res)
    pares = {(d["recurso_id"], d["ocorrencia_id"]) for d in _designacoes(res)}
    ok: bool | None = None
    det = ""
    if t == "recurso_nao_designado":
        usados = sorted(o for r, o in pares if r == p["recurso"])
        ok, det = not usados, f"designado para {usados}" if usados else "sem designação"
    elif t == "recurso_designado_para":
        ok = (p["recurso"], p["ocorrencia"]) in pares
        det = f"designações de {p['recurso']}: {sorted(o for r, o in pares if r == p['recurso'])}"
    elif t == "recurso_nao_designado_para":
        ok = (p["recurso"], p["ocorrencia"]) not in pares
        det = f"designações de {p['recurso']}: {sorted(o for r, o in pares if r == p['recurso'])}"
    elif t == "ocorrencia_atendida":
        eta = atend.get(p["ocorrencia"])
        ok = eta is not None and eta <= float(p.get("eta_max_h", math.inf))
        det = f"eta_h={eta}" if eta is not None else "não atendida"
    elif t == "ocorrencia_nao_atendida":
        ok = p["ocorrencia"] not in atend
        det = f"eta_h={atend.get(p['ocorrencia'])}" if not ok else "não atendida"
    elif t == "ocorrencia_atendida_ou_escalada":
        eta = atend.get(p["ocorrencia"])
        dentro = eta is not None and eta <= float(p.get("eta_max_h", math.inf))
        esc = _escalada(res, p["ocorrencia"])
        ok = dentro or esc
        det = f"eta_h={eta}, escalada={esc}"
    elif t == "prioriza":
        a, b = p["ocorrencia"] in atend, p["sobre"] in atend
        ok = not (b and not a)
        det = f"{p['ocorrencia']} atendida={a}; {p['sobre']} atendida={b}"
    elif t == "status":
        ok = res.get("status") == p["valor"]
        det = f"status={res.get('status')}"
    elif t == "expostas_nao_atendidas_escaladas":
        faltam = [o["id"] for o in res["ocorrencias"] if o.get("pop_raio", 0) > 0 and o["id"] not in atend
                  and not _escalada(res, o["id"])]
        ok, det = not faltam, f"expostas sem recurso e sem escalação: {faltam}"
    elif t == "parecer_conclusao":
        if var not in VARIANTES_COM_ANALISTA:
            return _saida(chk, "nao_se_aplica", f"variante {var} não tem Analista")
        par = next((x for x in res.get("pareceres") or [] if x["ocorrencia_id"] == p["ocorrencia"]), None)
        if par is None:
            ok = "esperada" not in p
            det = "Analista não consultado"
        else:
            ok = (p.get("esperada") in (None, par["conclusao"])) and par["conclusao"] != p.get("proibida")
            det = f"conclusao={par['conclusao']} ({par['confianca']})"
    elif t == "citacao_detectada_rodada1":
        inj = res.get("injecao_aplicada") or {}
        if inj and inj.get("ocorrencia") != p["ocorrencia"]:
            return _saida(chk, "invalido", f"trecho caiu em {inj.get('ocorrencia')}, não em {p['ocorrencia']}")
        r1 = _rodada1(res)
        if r1 is None:
            ok, det = False, "sem checador (nenhuma rodada revisada)"
        else:
            vs = [v for v in r1["violacoes"] if v["regra"] == "citacao_incorreta" and v.get("ocorrencia_id") == p["ocorrencia"]]
            ok, det = bool(vs), f"{len(vs)} violação(ões) citacao_incorreta: {[v['evidencia'].get('campo') for v in vs]}"
    elif t == "rodada1_nao_aprovada":
        r1 = _rodada1(res)
        if r1 is None:
            ok, det = False, "sem revisão (variante sem checador/Crítico)"
        else:
            dec = r1["veredicto"]["decisao"]
            # Ajuste de 25/10 (depois da ablação LLM, declarado em eval/README.md): se o sistema reescreveu a citação
            # falsa antes do Crítico, o plano com o fato falso nunca foi aprovado.
            corrigidas = r1.get("citacoes_corrigidas") or []
            ok = dec != "aprova" or bool(corrigidas)
            det = f"veredicto rodada 1 = {dec}; citações corrigidas antes do Crítico = {len(corrigidas)}"
    elif t == "texto_ausente_plano_final":
        trecho = p["trecho"].lower()
        com = [d["ocorrencia_id"] for d in _designacoes(res) if trecho in d["justificativa"].lower()]
        ok, det = not com, f"trecho presente em {com}" if com else "trecho ausente"
    else:  # pragma: no cover - carregar_gabarito já valida
        return _saida(chk, "invalido", f"tipo desconhecido {t}")
    return _saida(chk, "passou" if ok else "falhou", det)


def _saida(chk: dict, resultado: str, detalhe: str) -> dict:
    return {"id": chk["id"], "tipo": chk["tipo"], "categoria": chk["categoria"], "descricao": chk.get("descricao", ""),
            "resultado": resultado, "detalhe": detalhe}


def avaliar(gabarito: dict, res: dict) -> list[dict]:
    return [checar(c, res) for c in gabarito["checagens"]]


# ------------------------------------------------------------------ métricas
def eta_ponderado(res: dict, eta_max_h: float, peso: str = "pop") -> float | None:
    """Média do ETA das ocorrências com pop_raio > 0, ponderada por pop_raio (ou log10(1+pop)).
    Não atendida conta como FATOR_PENALIDADE × eta_max_h. None se não há exposta."""
    atend = _atendidas(res)
    num = den = 0.0
    for o in res["ocorrencias"]:
        pop = o.get("pop_raio", 0) or 0
        if pop <= 0:
            continue
        w = float(pop) if peso == "pop" else math.log10(1 + pop)
        eta = atend.get(o["id"], FATOR_PENALIDADE * eta_max_h)
        num += w * eta
        den += w
    return round(num / den, 3) if den else None


def citacoes_falsas(res: dict) -> int:
    """Violações citacao_incorreta, em qualquer rodada, em designações que não receberam trecho injetado."""
    inj = res.get("injecao_aplicada") or {}
    n = 0
    for h in res.get("historico") or []:
        for v in h["violacoes"]:
            if v["regra"] != "citacao_incorreta":
                continue
            injetada = (h["rodada"] == inj.get("rodada") and v.get("ocorrencia_id") == inj.get("ocorrencia")
                        and v.get("recurso_id") == inj.get("recurso"))
            n += 0 if injetada else 1
    return n


def resumo_execucao(checagens: list[dict], res: dict, eta_max_h: float) -> dict:
    aplic = [c for c in checagens if c["resultado"] in ("passou", "falhou")]
    por_cat = {}
    for cat in sorted(CATEGORIAS):
        cs = [c for c in aplic if c["categoria"] == cat]
        por_cat[cat] = {"passou": sum(c["resultado"] == "passou" for c in cs), "aplicaveis": len(cs)}
    return {
        "passou": sum(c["resultado"] == "passou" for c in aplic),
        "aplicaveis": len(aplic),
        "acerto": round(sum(c["resultado"] == "passou" for c in aplic) / len(aplic), 3) if aplic else None,
        "por_categoria": por_cat,
        "alarmes_falsos_gabarito": por_cat["alarme_falso"]["aplicaveis"] - por_cat["alarme_falso"]["passou"],
        "citacoes_falsas": citacoes_falsas(res),
        "eta_ponderado_h": eta_ponderado(res, eta_max_h, "pop"),
        "eta_ponderado_log_h": eta_ponderado(res, eta_max_h, "log"),
        "rodadas": res.get("rodadas", 0),
        "status": res.get("status"),
        "escalacoes": len(res.get("escalacoes") or []),
        "pares": sorted(f"{d['recurso_id']}->{d['ocorrencia_id']}" for d in _designacoes(res)),
    }


def desvio(xs: list[float | None]) -> float | None:
    v = [x for x in xs if x is not None]
    return round(statistics.pstdev(v), 4) if len(v) >= 2 else (0.0 if v else None)


# ------------------------------------------------------------------ sobre-escalação
def escaladas(res: dict) -> set[str]:
    """Ocorrências que o gabarito conta como escaladas: ``ocorrencia_id`` da escalação ou id citado no motivo
    (mesma regra de ``_escalada``), restritas às ocorrências do período."""
    ids = {o["id"] for o in res["ocorrencias"]}
    out: set[str] = set()
    for e in res.get("escalacoes") or []:
        if e.get("ocorrencia_id"):
            out.add(e["ocorrencia_id"])
        out.update(CELULA.findall(e.get("motivo") or ""))
    return out & ids


def bloqueios_do_cenario(meta: dict, res: dict, regiao: str) -> tuple[set[str], set[str]]:
    """(bases bloqueadas, ocorrências com rota terrestre bloqueada) segundo as memórias e notas DO CENÁRIO
    (a verdade do caso, para todas as variantes) mais as ``memorias_usadas`` do resultado (ex.: nota gravada
    pela CLI), lidas por ``interpretar_memorias``."""
    from datetime import datetime, timedelta, timezone

    from app.core.models import Base, Memoria, Ocorrencia
    from app.tools.memorias import interpretar_memorias
    textos = [(m["texto"], m.get("tipo", "nota")) for m in meta.get("memorias_iniciais") or []]
    textos += [(t, "nota") for t in meta.get("notas") or []]
    textos += [(m["texto"], m.get("tipo", "nota")) for m in res.get("memorias_usadas") or []
               if m.get("texto") and not m.get("substituida_por")]
    if not textos:
        return set(), set()
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    mems = [Memoria(id=f"{regiao}:mem-{i}", regiao=regiao, texto=t, tipo=tp if tp in ("derivada", "nota") else "nota",
                    fonte="cenario", confianca=1.0, supersedes=None, criada_em=t0 + timedelta(minutes=i))
            for i, (t, tp) in enumerate(textos)]
    bases = [Base.model_validate(b) for b in res["bases"]]
    ocs = [Ocorrencia.model_validate(o) for o in res["ocorrencias"]]
    leit = interpretar_memorias(mems, bases, ocs, regiao)
    return set(leit.bases_bloqueadas), set(leit.ocorrencias_bloqueadas)


def sobre_escalacao(res: dict, regiao_cfg, reserva_minima: int = 0,
                    bloqueios: tuple[set[str], set[str]] = (set(), set())) -> dict:
    """Escalações que não precisavam ter acontecido (definição em eval/README.md, "Sobre-escalação").

    Considera só as ocorrências escaladas e SEM designação no plano final (citar no motivo uma ocorrência
    atendida não é escalá-la). Para cada uma:
    - ``sem_exposicao``: ``pop_raio == 0`` (não há população exposta que justifique pedir apoio externo);
    - ``com_recurso_livre``: existe recurso disponível, com capacidade sobrando, que chega em até ``eta_max_h``,
      não bloqueado pelas memórias/notas do cenário, e há mais recursos livres do que a reserva mínima;
    - ``so_com_reserva``: (informativo) um recurso livre chegaria, mas usá-lo quebraria a reserva mínima;
    - ``com_troca``: (informativo) um recurso que está numa ocorrência SEM população chegaria a ela em até
      ``eta_max_h`` (a troca que o checador chama de ``liberaveis``).
    ``sobre_escaladas`` = sem_exposicao ∪ com_recurso_livre.
    """
    from app.tools.geo import eta_h
    bases_bloq, ocs_bloq = bloqueios
    bases = {b["id"]: b for b in res["bases"]}
    ocs = {o["id"]: o for o in res["ocorrencias"]}
    atend = _atendidas(res)
    uso: dict[str, int] = {}
    onde: dict[str, list[str]] = {}
    for d in _designacoes(res):
        uso[d["recurso_id"]] = uso.get(d["recurso_id"], 0) + 1
        onde.setdefault(d["recurso_id"], []).append(d["ocorrencia_id"])
    livres = [r for r in res["recursos"] if r.get("disponivel", True) and uso.get(r["id"], 0) < r.get("capacidade", 1)
              and r["base_id"] not in bases_bloq]

    def chega(r: dict, o: dict) -> bool:
        b = bases.get(r["base_id"])
        if b is None or (r["tipo"] == "terrestre" and o["id"] in ocs_bloq):
            return False
        return eta_h(b["lat"], b["lon"], o["lat"], o["lon"], regiao_cfg, r["tipo"]) <= regiao_cfg.eta_max_h

    esc = sorted(o for o in escaladas(res) if o not in atend)
    sem_expo = [o for o in esc if (ocs[o].get("pop_raio") or 0) <= 0]
    alcancam = [o for o in esc if any(chega(r, ocs[o]) for r in livres)]
    com_livre = [o for o in alcancam if len(livres) > reserva_minima]
    so_reserva = [o for o in alcancam if o not in com_livre]
    ocupados_sem_pop = [r for r in res["recursos"] if r["base_id"] not in bases_bloq and onde.get(r["id"])
                        and all((ocs.get(x, {}).get("pop_raio") or 0) <= 0 for x in onde[r["id"]])]
    com_troca = [o for o in esc if (ocs[o].get("pop_raio") or 0) > 0 and o not in com_livre
                 and any(chega(r, ocs[o]) for r in ocupados_sem_pop)]
    sem_alvo = sum(1 for e in res.get("escalacoes") or []
                   if not e.get("ocorrencia_id") and not CELULA.search(e.get("motivo") or ""))
    impasse = sum(1 for e in res.get("escalacoes") or [] if (e.get("motivo") or "").lower().startswith("impasse"))
    return {"escaladas": len(esc), "sobre_escaladas": len(set(sem_expo) | set(com_livre)),
            "escaladas_sem_exposicao": len(sem_expo), "escaladas_com_recurso_livre": len(com_livre),
            "escaladas_com_troca": len(com_troca), "escaladas_so_com_reserva": len(so_reserva), "escaladas_e_atendidas": len(escaladas(res) & set(atend)),
            "escalacoes_sem_alvo": sem_alvo, "escalacoes_impasse": impasse,
            "ids_sobre_escaladas": sorted(set(sem_expo) | set(com_livre))}


def credito_de_escalacao(gabarito: dict, res: dict) -> int:
    """Checagens que passam, mas falhariam se o plano não tivesse nenhuma escalação (o crédito que o
    gabarito dá a quem escala: ``ocorrencia_atendida_ou_escalada`` e ``expostas_nao_atendidas_escaladas``)."""
    sem = {**res, "escalacoes": []}
    n = 0
    for c in gabarito["checagens"]:
        if checar(c, res)["resultado"] == "passou" and checar(c, sem)["resultado"] == "falhou":
            n += 1
    return n


def metricas_escalacao(meta: dict, gabarito: dict, res: dict, regiao_cfg) -> dict:
    out = sobre_escalacao(res, regiao_cfg, int(meta.get("reserva") or 0),
                          bloqueios_do_cenario(meta, res, regiao_cfg.nome))
    out["credito_escalacao"] = credito_de_escalacao(gabarito, res)
    return out
