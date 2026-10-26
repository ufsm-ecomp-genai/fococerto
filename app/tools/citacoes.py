"""checar_citacoes: confere se os fatos citados nas justificativas batem com os dados (regra="citacao_incorreta").

Verifica (i) os tokens de ``Designacao.evidencias`` (``pop:N``, ``eta:H``, ``dist:<nome>:<km>``, ``loc:<nome>``,
``base:<id>``, ``focos:N``, ``frp:X``, ``ti_uc:<km>``), (ii) o campo ``eta_h`` e (iii) o texto livre da justificativa:
localidades/bases citadas, "N habitantes", "ETA X h" e "X km". O texto livre pode estar em pt-BR ou em inglês
("N people/inhabitants/residents", "ETA X h", "arrives in X h", "X km", "within the 6 h limit"); os tokens de
evidência não dependem do idioma. As sugestões saem no idioma de ``regiao_cfg.idioma`` (app/core/mensagens.py).
"""
from __future__ import annotations

import re

from app.core.mensagens import msg
from app.core.models import Base, Designacao, Ocorrencia, Plano, Recurso, RegiaoCfg, Violacao
from app.tools.geo import eta_recurso, haversine_km
from app.tools.texto import contem_termo, norm, sem_sufixo_simulada

# pt: "7.297 habitantes", "300 pessoas"; en: "7,297 inhabitants", "300 people/residents/persons"
RE_POP = re.compile(r"(\d{1,3}(?:[.,]\d{3})+(?![.,]?\d)|\d+)\s*(?:hab\w*|pessoas|moradores|residentes"
                    r"|people|inhabitants?|residents?|persons?)\b")
# pt: "ETA 2,4 h", "chega em 2,4 h"; en: "ETA 2.4 h", "arrives in 2.4 hours", "reaches it in 2.4 h"
RE_ETA = re.compile(r"\b(?:eta|cheg\w*|arriv\w*|reach\w*)\D{0,20}?(\d+(?:[.,]\d+)?)\s*(?:h\b|hora|hour)")
RE_KM = re.compile(r"(\d+(?:[.,]\d+)?)\s*km\b")
# "ETA ≤ 6 h", "chega em ≤6h", "ETA máximo 6 h": o número é o limite da região, não o ETA citado
# en: "ETA ≤ 6 h", "within the 6 h limit", "limit 6 h", "max 6 h", "up to 6 h", "under/below/above 6 h"
RE_LIMITE = re.compile(r"[≤<>≥]|\bate\b|limite|maxim|\bmax\b|acima|abaixo|dentro|exced|ultrapass"
                       r"|limit|within|\bup to\b|\bunder\b|below|above|beyond|exceed")


def resolver_localidade(nome: str, locs: dict[str, list[dict]]) -> list[dict] | None:
    """Localidades (homônimas) desta ocorrência que ``nome`` cita: nome exato (sem acento/caixa) ou prefixo
    inequívoco por palavras inteiras ("Divinopolis" -> "Divinópolis do Tocantins"). None se não casa ou se o
    prefixo é ambíguo entre duas localidades diferentes da ocorrência."""
    n = norm(nome).strip()
    if n in locs:
        return locs[n]
    if len(n) < 4:
        return None
    cands = [k for k in locs if re.match(re.escape(n) + r"(?![a-z0-9])", k)]
    return locs[cands[0]] if len(cands) == 1 else None


def _num(s: str) -> float:
    s = s.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
        return float(s.replace(".", ""))
    return float(s.replace(",", "."))


def _num_pop(s: str) -> float:
    """População: "7.297" (pt) e "7,297" (en) são milhares; pessoa não tem casa decimal."""
    s = s.strip()
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
        return float(re.sub(r"[.,]", "", s))
    return float(s)


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
    idioma = regiao_cfg.idioma if regiao_cfg is not None else None
    todas_locs = {loc["nome"] for o in ocorrencias for loc in o.localidades if loc.get("nome")}
    vs: list[Violacao] = []
    for d in plano.designacoes:
        o = occ.get(d.ocorrencia_id)
        if o is None:
            continue
        # nome -> todas as localidades com esse nome (há homônimas na mesma ocorrência, ex. dois pontos do
        # GeoNames com o mesmo nome a 10,4 e 14,3 km): a citação vale se bater com qualquer uma delas
        locs: dict[str, list[dict]] = {}
        for l in o.localidades:
            if l.get("nome"):
                locs.setdefault(norm(l["nome"]), []).append(l)
        pops_validas = [o.pop_raio] + [int(l.get("pop", 0) or 0) for l in o.localidades]
        base = None
        r = rec.get(d.recurso_id)
        if r is not None:
            base = por_base.get(r.base_id)
        for tok in d.evidencias:
            if tok.startswith("base:"):
                bid = tok[5:]
                if bid not in por_base:
                    vs.append(_v(d, "base", bid, None, msg("cit_base_inexistente", idioma)))
                elif r is not None and r.base_id != bid:
                    vs.append(_v(d, "base", bid, r.base_id, msg("cit_base_errada", idioma, bid=r.base_id)))
                elif base is None:
                    base = por_base[bid]
        eta_real = None
        if base is not None and regiao_cfg is not None:
            eta_real = eta_recurso(r or Recurso(id=d.recurso_id, base_id=base.id, tipo="terrestre"), base, o, regiao_cfg)
            if not _perto(d.eta_h, eta_real, 0.15, 0.25):
                vs.append(_v(d, "eta_h", d.eta_h, round(eta_real, 2), msg("cit_eta_h", idioma, eta=eta_real)))
        eta_ref = eta_real if eta_real is not None else d.eta_h

        for tok in d.evidencias:
            chave, _, valor = tok.partition(":")
            try:
                if chave == "pop":
                    if not any(_perto(float(valor), p, 0.05, 1) for p in pops_validas):
                        vs.append(_v(d, "pop", valor, o.pop_raio, msg("cit_pop", idioma, pop=o.pop_raio)))
                elif chave == "eta":
                    if not _perto(float(valor), eta_ref, 0.15, 0.25):
                        vs.append(_v(d, "eta", valor, round(eta_ref, 2), msg("cit_eta", idioma, eta=eta_ref)))
                elif chave == "focos":
                    if int(float(valor)) != o.n_focos:
                        vs.append(_v(d, "focos", valor, o.n_focos, msg("cit_focos", idioma, n=o.n_focos)))
                elif chave == "frp":
                    if not (_perto(float(valor), o.frp_soma, 0.1, 1) or _perto(float(valor), o.frp_max, 0.1, 1)):
                        vs.append(_v(d, "frp", valor, o.frp_soma, msg("cit_frp", idioma, frp=o.frp_soma)))
                elif chave == "ti_uc":
                    if o.dist_ti_uc_km is None or not _perto(float(valor), o.dist_ti_uc_km, 0.15, 1):
                        vs.append(_v(d, "ti_uc", valor, o.dist_ti_uc_km, msg("cit_ti_uc", idioma)))
                elif chave in ("loc", "dist"):
                    nome, _, km = valor.partition(":")
                    homonimas = resolver_localidade(nome, locs)
                    if not homonimas and base is not None and norm(nome).strip() in (
                            norm(base.nome), sem_sufixo_simulada(base.nome)):
                        # a base de saída citada como lugar ("dist:Paranã:42"): confere a distância até a base
                        d_base = haversine_km(base.lat, base.lon, o.lat, o.lon)
                        reais_b = [d_base] + ([d_base * regiao_cfg.fator_tortuosidade] if regiao_cfg else [])
                        if chave == "dist" and km and not any(_perto(float(km), x, 0.15, 1) for x in reais_b):
                            vs.append(_v(d, "dist", f"{nome}:{km}", round(d_base, 1),
                                         msg("cit_dist_base", idioma, nome=base.nome, km=d_base)))
                        continue
                    if not homonimas:
                        vs.append(_v(d, "localidade", nome, sorted(locs), msg("cit_localidade_fora", idioma)))
                    elif chave == "dist" and km and not any(
                            _perto(float(km), float(l.get("dist_km", 0) or 0), 0.15, 1) for l in homonimas):
                        reais = [l.get("dist_km") for l in homonimas]
                        real = reais[0] if len(reais) == 1 else reais
                        vs.append(_v(d, "dist", f"{nome}:{km}", real,
                                     msg("cit_dist", idioma, nome=nome,
                                         kms=msg("ou", idioma).join(str(x) for x in reais))))
            except ValueError:
                vs.append(_v(d, chave, valor, None, msg("cit_mal_formatada", idioma)))

        # texto livre
        t = norm(d.justificativa)
        nomes_base = {norm(b.nome) for b in bases}
        # o nome da base de saída ("saindo de Porto Nacional (simulada)") não é localidade citada
        # nem o id do recurso ("dianopolis-t1")
        ids_recurso = {norm(d.recurso_id)} | {norm(r.id) for r in (recursos or [])}
        for nb in sorted(nomes_base | ids_recurso, key=len, reverse=True):
            t = t.replace(nb, " ")
        citadas_aqui = [k for k in locs if contem_termo(t, k)]
        for nome in todas_locs:
            n = norm(nome)
            if any(contem_termo(k, n) for k in citadas_aqui):
                continue  # "Divinópolis" de outra ocorrência dentro de "Divinópolis do Tocantins", que é daqui
            if len(n) >= 4 and n not in locs and n not in nomes_base and contem_termo(t, nome):
                vs.append(_v(d, "localidade", nome, sorted(l["nome"] for l in o.localidades),
                             msg("cit_localidade_texto", idioma, nome=nome)))
        for m in RE_POP.finditer(t):
            val = _num_pop(m.group(1))
            if not any(_perto(val, p, 0.05, 1) for p in pops_validas):
                vs.append(_v(d, "pop_texto", val, o.pop_raio, msg("cit_pop", idioma, pop=o.pop_raio)))
        for m in RE_ETA.finditer(t):
            val = _num(m.group(1))
            if (regiao_cfg is not None and abs(val - regiao_cfg.eta_max_h) < 0.01
                    and RE_LIMITE.search(t[max(0, m.start(1) - 25):m.start(1)])):
                continue  # cita o limite da região ("ETA ≤ 6 h"), não um ETA
            if not _perto(val, eta_ref, 0.15, 0.25):
                vs.append(_v(d, "eta_texto", val, round(eta_ref, 2), msg("cit_eta", idioma, eta=eta_ref)))
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
            if re.search(r"(?:raio|radius)\D{0,6}$", t[max(0, m.start() - 12):m.start()]) or \
                    re.match(r"\s*(?:de\s+)?(?:raio|radius)\b", t[m.end():m.end() + 12]):
                continue  # o raio de exposição ("raio de 15 km", "15 km radius"), não uma distância citada
            val = _num(m.group(1))
            if not any(_perto(val, x, 0.15, 1) for x in dists_validas):
                vs.append(_v(d, "dist_texto", val, [round(x, 1) for x in dists_validas], msg("cit_dist_texto", idioma)))
    return vs
