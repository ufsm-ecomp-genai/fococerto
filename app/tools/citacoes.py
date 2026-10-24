"""checar_citacoes: confere se os fatos citados nas justificativas batem com os dados (regra="citacao_incorreta").

Verifica (i) os tokens de ``Designacao.evidencias`` (``pop:N``, ``eta:H``, ``dist:<nome>:<km>``, ``loc:<nome>``,
``base:<id>``, ``focos:N``, ``frp:X``, ``ti_uc:<km>``), (ii) o campo ``eta_h`` e (iii) o texto livre da justificativa:
localidades/bases citadas, "N habitantes", "ETA X h" e "X km".
"""
from __future__ import annotations

import re

from app.core.models import Base, Designacao, Ocorrencia, Plano, Recurso, RegiaoCfg, Violacao
from app.tools.geo import eta_recurso, haversine_km
from app.tools.texto import contem_termo, norm

RE_POP = re.compile(r"(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:hab\w*|pessoas|moradores|residentes)")
RE_ETA = re.compile(r"\b(?:eta|cheg\w*)\D{0,20}?(\d+(?:[.,]\d+)?)\s*(?:h\b|hora)")
RE_KM = re.compile(r"(\d+(?:[.,]\d+)?)\s*km\b")


def _num(s: str) -> float:
    s = s.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
        return float(s.replace(".", ""))
    return float(s.replace(",", "."))


def _perto(a: float, b: float, rel: float, abs_: float) -> bool:
    return abs(a - b) <= max(abs_, rel * abs(b))


def _v(d: Designacao, campo: str, citado, real, sug: str) -> Violacao:
    return Violacao(regra="citacao_incorreta", ocorrencia_id=d.ocorrencia_id, recurso_id=d.recurso_id,
                    evidencia={"campo": campo, "citado": citado, "real": real, "justificativa": d.justificativa},
                    sugestao=sug, rigida=True)


def checar_citacoes(plano: Plano, ocorrencias: list[Ocorrencia], bases: list[Base],
                    recursos: list[Recurso] | None = None, regiao_cfg: RegiaoCfg | None = None) -> list[Violacao]:
    """``recursos`` e ``regiao_cfg`` são opcionais (extensão do contrato): com eles o ETA é recalculado da base
    do recurso; sem eles, só da ``base:<id>`` citada nas evidências."""
    occ = {o.id: o for o in ocorrencias}
    por_base = {b.id: b for b in bases}
    rec = {r.id: r for r in (recursos or [])}
    todas_locs = {loc["nome"] for o in ocorrencias for loc in o.localidades if loc.get("nome")}
    vs: list[Violacao] = []
    for d in plano.designacoes:
        o = occ.get(d.ocorrencia_id)
        if o is None:
            continue
        locs = {norm(l["nome"]): l for l in o.localidades if l.get("nome")}
        pops_validas = [o.pop_raio] + [int(l.get("pop", 0) or 0) for l in o.localidades]
        base = None
        r = rec.get(d.recurso_id)
        if r is not None:
            base = por_base.get(r.base_id)
        for tok in d.evidencias:
            if tok.startswith("base:"):
                bid = tok[5:]
                if bid not in por_base:
                    vs.append(_v(d, "base", bid, None, "citar uma base existente"))
                elif r is not None and r.base_id != bid:
                    vs.append(_v(d, "base", bid, r.base_id, f"o recurso sai da base {r.base_id}"))
                elif base is None:
                    base = por_base[bid]
        eta_real = None
        if base is not None and regiao_cfg is not None:
            eta_real = eta_recurso(r or Recurso(id=d.recurso_id, base_id=base.id, tipo="terrestre"), base, o, regiao_cfg)
            if not _perto(d.eta_h, eta_real, 0.15, 0.25):
                vs.append(_v(d, "eta_h", d.eta_h, round(eta_real, 2), f"ETA correto ≈ {eta_real:.1f} h"))
        eta_ref = eta_real if eta_real is not None else d.eta_h

        for tok in d.evidencias:
            chave, _, valor = tok.partition(":")
            try:
                if chave == "pop":
                    if not any(_perto(float(valor), p, 0.05, 1) for p in pops_validas):
                        vs.append(_v(d, "pop", valor, o.pop_raio, f"população no raio = {o.pop_raio}"))
                elif chave == "eta":
                    if not _perto(float(valor), eta_ref, 0.15, 0.25):
                        vs.append(_v(d, "eta", valor, round(eta_ref, 2), f"ETA ≈ {eta_ref:.1f} h"))
                elif chave == "focos":
                    if int(float(valor)) != o.n_focos:
                        vs.append(_v(d, "focos", valor, o.n_focos, f"focos = {o.n_focos}"))
                elif chave == "frp":
                    if not (_perto(float(valor), o.frp_soma, 0.1, 1) or _perto(float(valor), o.frp_max, 0.1, 1)):
                        vs.append(_v(d, "frp", valor, o.frp_soma, f"FRP somado = {o.frp_soma:.0f} MW"))
                elif chave == "ti_uc":
                    if o.dist_ti_uc_km is None or not _perto(float(valor), o.dist_ti_uc_km, 0.15, 1):
                        vs.append(_v(d, "ti_uc", valor, o.dist_ti_uc_km, "conferir a distância até TI/UC"))
                elif chave in ("loc", "dist"):
                    nome, _, km = valor.partition(":")
                    l = locs.get(norm(nome))
                    if l is None:
                        vs.append(_v(d, "localidade", nome, sorted(locs), "citar só localidades no raio desta ocorrência"))
                    elif chave == "dist" and km and not _perto(float(km), float(l.get("dist_km", 0)), 0.15, 1):
                        vs.append(_v(d, "dist", f"{nome}:{km}", l.get("dist_km"), f"{nome} fica a {l.get('dist_km')} km"))
            except ValueError:
                vs.append(_v(d, chave, valor, None, "evidência mal formatada"))

        # texto livre
        t = norm(d.justificativa)
        nomes_base = {norm(b.nome) for b in bases}
        # o nome da base de saída ("saindo de Porto Nacional (simulada)") não é localidade citada
        # nem o id do recurso ("dianopolis-t1")
        ids_recurso = {norm(d.recurso_id)} | {norm(r.id) for r in (recursos or [])}
        for nb in sorted(nomes_base | ids_recurso, key=len, reverse=True):
            t = t.replace(nb, " ")
        for nome in todas_locs:
            n = norm(nome)
            if len(n) >= 4 and n not in locs and n not in nomes_base and contem_termo(t, nome):
                vs.append(_v(d, "localidade", nome, sorted(l["nome"] for l in o.localidades),
                             f"{nome} não está no raio desta ocorrência"))
        for m in RE_POP.finditer(t):
            val = _num(m.group(1))
            if not any(_perto(val, p, 0.05, 1) for p in pops_validas):
                vs.append(_v(d, "pop_texto", val, o.pop_raio, f"população no raio = {o.pop_raio}"))
        for m in RE_ETA.finditer(t):
            val = _num(m.group(1))
            if not _perto(val, eta_ref, 0.15, 0.25):
                vs.append(_v(d, "eta_texto", val, round(eta_ref, 2), f"ETA ≈ {eta_ref:.1f} h"))
        dists_validas = [float(l.get("dist_km")) for l in o.localidades if l.get("dist_km") is not None]
        if o.dist_ti_uc_km is not None:
            dists_validas.append(o.dist_ti_uc_km)
        if base is not None:
            dists_validas.append(haversine_km(base.lat, base.lon, o.lat, o.lon))
            if regiao_cfg is not None:
                dists_validas.append(dists_validas[-1] * regiao_cfg.fator_tortuosidade)
        if regiao_cfg is not None:
            dists_validas.append(regiao_cfg.raio_exposicao_km)
        for m in RE_KM.finditer(t):
            if re.search(r"raio\D{0,6}$", t[max(0, m.start() - 10):m.start()]):
                continue
            val = _num(m.group(1))
            if not any(_perto(val, x, 0.15, 1) for x in dists_validas):
                vs.append(_v(d, "dist_texto", val, [round(x, 1) for x in dists_validas], "conferir a distância citada"))
    return vs
