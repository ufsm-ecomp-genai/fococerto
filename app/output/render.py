"""plano.json e plano.md a partir de um ResultadoPeriodo (docs/CONTRATOS.md, seções 9 e 10).

O Markdown é a lista de prioridades + ordem de recursos, com o mais urgente primeiro:
aviso de recursos simulados, escalações, ordem de recursos, prioridades e só depois os detalhes.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import RAIZ
from app.core.models import Cenario, RegiaoCfg, ResultadoPeriodo
from app.output.comum import (aviso_bases, bases_usadas, campo, faixas_prioridade, ids_escalados,
                               localidade_proxima, procedencia_base)
from app.output.textos import textos

VERSAO_FORMATO = 1


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def render_json(resultado: ResultadoPeriodo, regiao: RegiaoCfg, cenario: Cenario | None = None, *,
                modo: str | None = None, arquivo_cenario: str | None = None) -> str:
    """JSON completo do período: metadados + ResultadoPeriodo. `aprovar` relê a chave "plano"."""
    meta = {
        "versao_formato": VERSAO_FORMATO,
        "regiao": regiao.nome,
        "periodo": resultado.plano.periodo,
        "idioma": regiao.idioma,
        "modo": modo,
        "simulado": bool(cenario.simulado) if cenario else None,
        "arquivo_cenario": arquivo_cenario,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "aprovacao_humana": "pendente",
    }
    dados = {"meta": meta, **resultado.model_dump(mode="json")}
    return json.dumps(dados, ensure_ascii=False, indent=2, default=str)


def _cel(texto: object) -> str:
    """Texto seguro para uma célula de tabela Markdown."""
    return str(texto).replace("|", "\\|").replace("\n", " ").strip()


def _num(v: float | None, casas: int = 1) -> str:
    return "-" if v is None else f"{v:.{casas}f}"


def _link_log(log_path: str, pasta_saida: Path | None) -> str:
    """Link do log relativo à pasta do plano.md. ``log_path`` pode ser absoluto ou relativo à raiz do repositório
    (o grafo grava relativo quando o log fica dentro do repositório, para não vazar o caminho da máquina)."""
    if not log_path:
        return ""
    if pasta_saida is None:
        return log_path
    alvo = log_path if os.path.isabs(log_path) else str(RAIZ / log_path)
    try:
        return Path(os.path.relpath(alvo, os.path.abspath(pasta_saida))).as_posix()
    except ValueError:
        return log_path


def render_markdown(resultado: ResultadoPeriodo, regiao: RegiaoCfg, cenario: Cenario | None = None, *,
                    modo: str | None = None, arquivo_cenario: str | None = None,
                    pasta_saida: Path | None = None) -> str:
    T = textos(regiao.idioma)
    plano = resultado.plano
    ocorr = {o.id: o for o in resultado.ocorrencias}
    bases = {b.id: b for b in resultado.bases}
    recursos = {r.id: r for r in resultado.recursos}
    faixas = faixas_prioridade(resultado)
    escalados = ids_escalados(resultado)
    nome_faixa = {"alta": T["faixa_alta"], "media": T["faixa_media"], "baixa": T["faixa_baixa"]}

    def rot_ocorrencia(oid: str) -> str:
        o = ocorr.get(oid)
        if o is None:
            return f"`{oid}`"
        loc = localidade_proxima(o.localidades)
        perto = f" ({loc.get('nome', '?')}, {_num(loc.get('dist_km'))} {T['km']})" if loc else ""
        return f"`{oid}`{perto}"

    def rot_recurso(rid: str) -> str:
        r = recursos.get(rid)
        if r is None:
            return f"`{rid}`"
        b = bases.get(r.base_id)
        if b is None:
            return f"`{rid}` ({r.tipo}, {r.base_id})"
        proc = T["procedencias"].get(procedencia_base(b, cenario), procedencia_base(b, cenario))
        return f"`{rid}` ({r.tipo}, {b.nome}, {T['base_rotulo'].format(procedencia=proc)})"

    L: list[str] = []
    L.append(f"# {T['titulo'].format(periodo=plano.periodo, regiao=regiao.nome)}")
    L.append("")
    if cenario is not None and cenario.simulado:
        L.append(f"> **{T['aviso_simulado'].format(arquivo=arquivo_cenario or '-')}**")
        L.append(">")
        av_bases = aviso_bases(resultado, cenario, T)
        if av_bases:
            L.append(f"> **{av_bases}**")
            L.append(">")
    L.append(f"> {T['aviso_aprovacao'].format(regiao=regiao.nome, periodo=plano.periodo)}")
    L.append("")
    status = T["status_escalado"] if resultado.escalacoes else T["status_aprovado"]
    L.append(f"- **{T['situacao']}:** {status}")
    L.append(f"- {T['rodadas'].format(n=resultado.rodadas)}")
    if modo:
        L.append(f"- **{T['modo']}:** {T['modo_offline'] if modo == 'offline' else T['modo_llm']}")
    L.append("")

    # 1. Escalações: sempre em destaque, logo no topo.
    L.append(f"## {T['escalacoes']}")
    L.append("")
    if resultado.escalacoes:
        for e in resultado.escalacoes:
            oid = campo(e, "ocorrencia_id")
            alvo = rot_ocorrencia(oid) if oid else "-"
            L.append(f"- **{T['escalada']}** {alvo}: {campo(e, 'motivo', '')}")
    else:
        L.append(T["sem_escalacoes"])
    L.append("")

    # 2. Ordem de recursos.
    L.append(f"## {T['ordem_recursos']}")
    L.append("")
    designacoes = sorted(plano.designacoes, key=lambda d: d.ordem)
    if designacoes:
        L.append(f"| {T['col_ordem']} | {T['col_recurso']} | {T['col_ocorrencia']} | {T['col_prioridade']} | {T['col_eta']} |")
        L.append("|---|---|---|---|---|")
        for d in designacoes:
            o = ocorr.get(d.ocorrencia_id)
            prio = f"{_num(o.prioridade, 2)} ({nome_faixa[faixas[o.id]]})" if o else "-"
            L.append(f"| {d.ordem} | {_cel(rot_recurso(d.recurso_id))} | {_cel(rot_ocorrencia(d.ocorrencia_id))} | "
                     f"{_cel(prio)} | {_num(d.eta_h)} {T['h']} |")
    else:
        L.append(T["sem_designacoes"])
    L.append("")
    L.append(f"- **{T['reserva']}:** {', '.join(f'`{r}`' for r in plano.reserva) or T['nenhum']}")
    L.append(f"- **{T['nao_atendidas']}:** {', '.join(rot_ocorrencia(o) for o in plano.nao_atendidas) or T['nenhum']}")
    L.append("")

    if plano.resumo:
        L.append(f"## {T['resumo']}")
        L.append("")
        L.append(plano.resumo.strip())
        L.append("")

    # 3. Lista de prioridades.
    L.append(f"## {T['lista_prioridades']}")
    L.append("")
    L.append(f"_{T['prioridade_nota']}_")
    L.append("")
    atendidas: dict[str, list[str]] = {}
    for d in designacoes:
        atendidas.setdefault(d.ocorrencia_id, []).append(d.recurso_id)
    L.append(f"| # | {T['col_ocorrencia']} | {T['col_prioridade']} | {T['col_status']} | {T['col_focos']} | "
             f"{T['col_frp']} | {T['col_pop']} | {T['col_localidade']} | {T['col_atendimento']} |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for i, o in enumerate(sorted(resultado.ocorrencias, key=lambda o: o.prioridade, reverse=True), 1):
        loc = localidade_proxima(o.localidades)
        loc_txt = f"{loc.get('nome', '?')} ({_num(loc.get('dist_km'))} {T['km']})" if loc else "-"
        if o.id in atendidas:
            atend = T["atendida_por"].format(recursos=", ".join(f"`{r}`" for r in atendidas[o.id]))
        else:
            atend = T["nao_atendida"]
        if o.id in escalados:
            atend = f"**{T['escalada']}**; {atend}"
        L.append(f"| {i} | `{o.id}` | {_num(o.prioridade, 2)} ({nome_faixa[faixas[o.id]]}) | {o.status or '-'} | "
                 f"{o.n_focos} | {_num(o.frp_max)} | {o.pop_raio} | {_cel(loc_txt)} | {_cel(atend)} |")
    L.append("")

    # 4. Detalhe de cada designação.
    if designacoes:
        L.append(f"## {T['detalhes']}")
        L.append("")
        for d in designacoes:
            L.append(f"### {d.ordem}. {rot_recurso(d.recurso_id)} → {rot_ocorrencia(d.ocorrencia_id)}, "
                     f"{T['col_eta']} {_num(d.eta_h)} {T['h']}")
            L.append("")
            L.append(f"**{T['justificativa']}:** {d.justificativa.strip()}")
            L.append("")
            ev = ", ".join(f"`{e}`" for e in d.evidencias) or T["sem_evidencias"]
            L.append(f"**{T['evidencias']}:** {ev}")
            L.append("")

    # 4b. Bases e procedência (docs/CONTRATOS.md, seção 16).
    usadas = bases_usadas(resultado)
    if usadas:
        L.append(f"## {T['bases_procedencia']}")
        L.append("")
        L.append(f"| {T['col_base']} | {T['col_procedencia']} | {T['col_fonte']} | {T['col_recursos']} |")
        L.append("|---|---|---|---|")
        for b in usadas:
            proc = procedencia_base(b, cenario)
            recs = ", ".join(f"`{r.id}`" for r in resultado.recursos if r.base_id == b.id)
            L.append(f"| {_cel(b.nome)} (`{b.id}`) | **{T['procedencias'].get(proc, proc)}**: "
                     f"{_cel(T['procedencia_desc'].get(proc, ''))} | {_cel(b.fonte or '-')} | {recs} |")
        L.append("")
        ids_usadas = {b.id for b in usadas}
        sem = [b for b in resultado.bases if b.id not in ids_usadas]
        if sem:
            lista = "; ".join(f"{b.nome} ({T['procedencias'].get(procedencia_base(b, cenario), '?')})" for b in sem)
            L.append(T["bases_sem_recurso"].format(n=len(sem), lista=lista))
            L.append("")

    # 5. Pareceres do Analista.
    L.append(f"## {T['pareceres']}")
    L.append("")
    if resultado.pareceres:
        for p in resultado.pareceres:
            conc = T["conclusoes"].get(p.conclusao, p.conclusao)
            conf = T["confiancas"].get(p.confianca, p.confianca)
            L.append(f"- {rot_ocorrencia(p.ocorrencia_id)}: **{conc}** ({T['confianca'].lower()}: **{conf}**)")
            L.append(f"  - {T['pergunta']}: {p.pergunta}")
            if p.evidencias:
                L.append(f"  - {T['evidencias']}: {', '.join(f'`{e}`' for e in p.evidencias)}")
            if p.consultas:
                L.append(f"  - {T['consultas']}: {', '.join(f'`{c}`' for c in p.consultas)}")
    else:
        L.append(T["sem_pareceres"])
    L.append("")

    # 6. Memórias.
    L.append(f"## {T['memorias']}")
    L.append("")
    if resultado.memorias_usadas:
        for m in resultado.memorias_usadas:
            extra = f"; {T['substitui'].format(id=m.supersedes)}" if m.supersedes else ""
            L.append(f"- `{m.id}` ({T['memoria_tipo'].get(m.tipo, m.tipo)}, {T['confianca'].lower()} "
                     f"{m.confianca:.2f}, {m.fonte}{extra}): {m.texto}")
    else:
        L.append(T["sem_memorias"])
    L.append("")

    # 7. Ciclo de revisão.
    L.append(f"## {T['ciclo']}")
    L.append("")
    if resultado.historico:
        for h in resultado.historico:
            veredicto = campo(h, "veredicto")
            decisao = campo(veredicto, "decisao", "-")
            motivos = campo(veredicto, "motivos", []) or []
            violacoes = campo(h, "violacoes", []) or []
            regras = sorted({str(campo(v, "regra", "?")) for v in violacoes})
            linha = (f"- **{T['rodada'].format(n=campo(h, 'rodada', '?'))}:** {T['veredicto']} `{decisao}`; "
                     f"{len(violacoes)} {T['violacoes']}")
            if regras:
                linha += f" ({', '.join(regras)})"
            L.append(linha)
            for mt in motivos:
                L.append(f"  - {mt}")
    else:
        L.append(T["sem_ciclo"])
    L.append("")

    # 8. Limitações (especificação, seção 16).
    L.append(f"## {T['limitacoes']}")
    L.append("")
    for item in T["limitacoes_lista"]:
        L.append(f"- {item}")
    L.append("")

    link = _link_log(resultado.log_path, pasta_saida)
    if link:
        L.append(f"[{T['log']}]({link})")
        L.append("")
    L.append(f"_{T['gerado_em'].format(t=_agora())}_")
    L.append("")
    return "\n".join(L)


def escrever_saidas(resultado: ResultadoPeriodo, regiao: RegiaoCfg, cenario: Cenario | None, pasta: Path, *,
                    modo: str | None = None, arquivo_cenario: str | None = None) -> dict[str, Path]:
    """Grava plano.json, plano.md e mapa.html em `pasta` e devolve os caminhos."""
    from app.output.mapa import render_mapa

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = {
        "json": pasta / "plano.json",
        "markdown": pasta / "plano.md",
        "mapa": pasta / "mapa.html",
    }
    caminhos["json"].write_text(
        render_json(resultado, regiao, cenario, modo=modo, arquivo_cenario=arquivo_cenario), encoding="utf-8")
    caminhos["markdown"].write_text(
        render_markdown(resultado, regiao, cenario, modo=modo, arquivo_cenario=arquivo_cenario, pasta_saida=pasta),
        encoding="utf-8")
    caminhos["mapa"].write_text(render_mapa(resultado, regiao, cenario, arquivo_cenario=arquivo_cenario), encoding="utf-8")
    return caminhos


__all__ = ["render_json", "render_markdown", "escrever_saidas"]
