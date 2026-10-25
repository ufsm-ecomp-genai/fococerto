"""mapa.html autocontido: Leaflet 1.9.4 (cdnjs, versão fixa) e os dados embutidos no próprio arquivo.

Ocorrências coloridas pela faixa de prioridade do período, bases, linhas recurso→ocorrência
(da base do recurso até a ocorrência) e popups com a justificativa. Escalações ganham um anel tracejado.
"""
from __future__ import annotations

import html
import json

from app.core.models import Cenario, RegiaoCfg, ResultadoPeriodo
from app.output.comum import aviso_bases, faixas_prioridade, ids_escalados, localidade_proxima, procedencia_base
from app.output.textos import textos

LEAFLET_VERSAO = "1.9.4"
LEAFLET_CSS = f"https://cdnjs.cloudflare.com/ajax/libs/leaflet/{LEAFLET_VERSAO}/leaflet.min.css"
LEAFLET_JS = f"https://cdnjs.cloudflare.com/ajax/libs/leaflet/{LEAFLET_VERSAO}/leaflet.min.js"

CORES = {"alta": "#c62828", "media": "#ef6c00", "baixa": "#f9a825"}
# base por procedência (docs/CONTRATOS.md, seção 16): cor do quadrado e estilo da borda
ESTILO_BASE = {
    "oficial": {"cor": "#1565c0", "borda": "solid"},
    "osm": {"cor": "#00838f", "borda": "solid"},
    "declarada": {"cor": "#6a1b9a", "borda": "dashed"},
    "estimada": {"cor": "#757575", "borda": "dotted"},
}


def _dados_mapa(resultado: ResultadoPeriodo, regiao: RegiaoCfg, cenario: Cenario | None,
                arquivo_cenario: str | None = None) -> dict:
    T = textos(regiao.idioma)
    faixas = faixas_prioridade(resultado)
    escalados = ids_escalados(resultado)
    bases = {b.id: b for b in resultado.bases}
    recursos = {r.id: r for r in resultado.recursos}
    ocorr = {o.id: o for o in resultado.ocorrencias}
    designacoes = sorted(resultado.plano.designacoes, key=lambda d: d.ordem)
    nome_faixa = {"alta": T["faixa_alta"], "media": T["faixa_media"], "baixa": T["faixa_baixa"]}

    oc = []
    for o in resultado.ocorrencias:
        loc = localidade_proxima(o.localidades)
        oc.append({
            "id": o.id, "lat": o.lat, "lon": o.lon, "prioridade": round(o.prioridade, 3),
            "faixa": faixas[o.id], "faixa_nome": nome_faixa[faixas[o.id]], "cor": CORES[faixas[o.id]],
            "status": o.status, "n_focos": o.n_focos, "frp_max": o.frp_max, "pop_raio": o.pop_raio,
            "localidade": (f"{loc.get('nome', '?')} ({loc.get('dist_km', '?')} km)" if loc else None),
            "escalada": o.id in escalados, "motivo_escalacao": escalados.get(o.id),
            "designacoes": [
                {"ordem": d.ordem, "recurso": d.recurso_id, "eta_h": d.eta_h, "justificativa": d.justificativa,
                 "evidencias": d.evidencias}
                for d in designacoes if d.ocorrencia_id == o.id
            ],
        })
    bs = []
    for b in resultado.bases:
        proc = procedencia_base(b, cenario)
        bs.append({"id": b.id, "nome": b.nome, "lat": b.lat, "lon": b.lon, "procedencia": proc,
                   "procedencia_nome": T["procedencias"].get(proc, proc),
                   "procedencia_desc": T["procedencia_desc"].get(proc, ""), "fonte": b.fonte or "",
                   "recursos": [f"{r.id} ({r.tipo})" for r in resultado.recursos if r.base_id == b.id]})
    linhas = []
    for d in designacoes:
        r = recursos.get(d.recurso_id)
        b = bases.get(r.base_id) if r else None
        o = ocorr.get(d.ocorrencia_id)
        if b is None or o is None:
            continue  # sem coordenada de origem ou destino: a designação continua no plano.md
        linhas.append({"de": [b.lat, b.lon], "para": [o.lat, o.lon], "ordem": d.ordem,
                       "recurso": d.recurso_id, "ocorrencia": d.ocorrencia_id, "eta_h": d.eta_h,
                       "aereo": r.tipo == "aereo", "justificativa": d.justificativa})
    lat_min, lat_max, lon_min, lon_max = regiao.bbox
    return {
        "ocorrencias": oc, "bases": bs, "linhas": linhas,
        "bbox": [[lat_min, lon_min], [lat_max, lon_max]],
        "simulado": bool(cenario.simulado) if cenario else False,
        "cores": CORES, "estilo_base": ESTILO_BASE,
        "procedencias": {k: T["procedencias"][k] for k in ESTILO_BASE},
        "procedencias_presentes": sorted({b["procedencia"] for b in bs}, key=list(ESTILO_BASE).index),
        "t": {k: T[k] for k in ("mapa_legenda", "mapa_ocorrencia", "mapa_base", "mapa_designacao", "mapa_escalada",
                                 "mapa_motivo", "mapa_recursos_na_base", "col_prioridade", "col_status", "col_focos",
                                 "col_frp", "col_pop", "col_localidade", "col_eta", "justificativa", "evidencias",
                                 "faixa_alta", "faixa_media", "faixa_baixa", "nao_atendida", "col_ordem", "h",
                                 "mapa_procedencia", "mapa_fonte")},
        "aviso": T["aviso_simulado"].format(arquivo=arquivo_cenario or "-") if cenario and cenario.simulado else None,
        "aviso_bases": aviso_bases(resultado, cenario, T),
    }


def _json_seguro(dados: dict) -> str:
    """JSON que pode ir dentro de <script> sem fechar a tag."""
    return (json.dumps(dados, ensure_ascii=False, default=str)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


_JS = r"""
(function () {
  var D = JSON.parse(document.getElementById('dados').textContent);
  var T = D.t;
  function esc(s) {
    return String(s == null ? '-' : s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }
  var mapa = L.map('mapa');
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 18, attribution: 'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, USGS, &copy; OpenStreetMap contributors'
  }).addTo(mapa);
  var limites = L.latLngBounds(D.bbox);

  D.linhas.forEach(function (l) {
    L.polyline([l.de, l.para], {color: '#1565c0', weight: 3, opacity: 0.8, dashArray: l.aereo ? '2 6' : null})
      .bindTooltip('#' + l.ordem + ' ' + esc(l.recurso) + ' → ' + esc(l.ocorrencia) + ' (' + esc(l.eta_h) + ' ' + T.h + ')')
      .bindPopup('<b>#' + l.ordem + ' ' + esc(l.recurso) + ' → ' + esc(l.ocorrencia) + '</b><br>' +
                 T.col_eta + ': ' + esc(l.eta_h) + ' ' + T.h + '<br>' + T.justificativa + ': ' + esc(l.justificativa))
      .addTo(mapa);
  });

  function quadrado(proc, extra) {
    var e = D.estilo_base[proc] || D.estilo_base.osm;
    return '<div class="base-q ' + (extra || '') + '" style="background:' + e.cor + ';outline:2px ' + e.borda +
           ' ' + e.cor + '"></div>';
  }
  function fonteHtml(f) {
    // a fonte pode ter uma URL: vira link (o resto do texto continua escapado)
    var m = String(f || '').match(/https?:\/\/[^\s;()]+/);
    if (!m) return esc(f);
    var i = f.indexOf(m[0]);
    return esc(f.slice(0, i)) + '<a href="' + esc(m[0]) + '" target="_blank" rel="noopener">' + esc(m[0]) + '</a>' +
           esc(f.slice(i + m[0].length));
  }
  D.bases.forEach(function (b) {
    var icone = L.divIcon({className: 'base', html: quadrado(b.procedencia, b.recursos.length ? '' : 'vazia'),
                           iconSize: [14, 14]});
    L.marker([b.lat, b.lon], {icon: icone})
      .bindPopup('<b>' + T.mapa_base + ': ' + esc(b.nome) + '</b><br><code>' + esc(b.id) + '</code><br>' +
                 T.mapa_procedencia + ': <b>' + esc(b.procedencia_nome) + '</b> (' + esc(b.procedencia_desc) + ')<br>' +
                 T.mapa_fonte + ': ' + (b.fonte ? fonteHtml(b.fonte) : '-') + '<br>' +
                 T.mapa_recursos_na_base + ': ' + (b.recursos.length ? b.recursos.map(esc).join(', ') : '-'),
                 {maxWidth: 380})
      .addTo(mapa);
    limites.extend([b.lat, b.lon]);
  });

  D.ocorrencias.forEach(function (o) {
    var r = 6 + Math.min(10, Math.sqrt(o.n_focos) * 2);
    if (o.escalada) {
      L.circleMarker([o.lat, o.lon], {radius: r + 7, color: '#000', weight: 3, dashArray: '4 4', fill: false})
        .addTo(mapa);
    }
    var html = '<b>' + T.mapa_ocorrencia + ' <code>' + esc(o.id) + '</code></b>';
    if (o.escalada) html += '<div class="esc">' + T.mapa_escalada + '<br>' + T.mapa_motivo + ': ' + esc(o.motivo_escalacao) + '</div>';
    html += '<br>' + T.col_prioridade + ': ' + esc(o.prioridade) + ' (' + esc(o.faixa_nome) + ')' +
            '<br>' + T.col_status + ': ' + esc(o.status) +
            '<br>' + T.col_focos + ': ' + esc(o.n_focos) + ' · ' + T.col_frp + ': ' + esc(o.frp_max) +
            '<br>' + T.col_pop + ': ' + esc(o.pop_raio) +
            '<br>' + T.col_localidade + ': ' + esc(o.localidade);
    if (o.designacoes.length) {
      o.designacoes.forEach(function (d) {
        html += '<hr><b>#' + d.ordem + ' ' + esc(d.recurso) + '</b> · ' + T.col_eta + ' ' + esc(d.eta_h) + ' ' + T.h +
                '<br>' + T.justificativa + ': ' + esc(d.justificativa) +
                '<br>' + T.evidencias + ': ' + (d.evidencias.length ? d.evidencias.map(esc).join(', ') : '-');
      });
    } else {
      html += '<hr><i>' + T.nao_atendida + '</i>';
    }
    L.circleMarker([o.lat, o.lon], {radius: r, color: '#333', weight: 1, fillColor: o.cor, fillOpacity: 0.85})
      .bindPopup(html, {maxWidth: 360})
      .addTo(mapa);
    limites.extend([o.lat, o.lon]);
  });

  mapa.fitBounds(limites, {padding: [20, 20]});

  var legenda = L.control({position: 'bottomright'});
  legenda.onAdd = function () {
    var div = L.DomUtil.create('div', 'legenda');
    div.innerHTML = '<b>' + T.mapa_legenda + '</b><br>' +
      ['alta', 'media', 'baixa'].map(function (f) {
        return '<span class="pt" style="background:' + D.cores[f] + '"></span>' + T.mapa_ocorrencia + ' · ' +
               T.col_prioridade.toLowerCase() + ' ' + T['faixa_' + f];
      }).join('<br>') +
      '<br><span class="pt anel"></span>' + T.mapa_escalada +
      D.procedencias_presentes.map(function (p) {
        var e = D.estilo_base[p];
        return '<br><span class="base-q inl" style="background:' + e.cor + ';outline:2px ' + e.borda + ' ' + e.cor +
               '"></span>' + T.mapa_base + ' ' + esc(D.procedencias[p]);
      }).join('') +
      '<br><span class="ln"></span>' + T.mapa_designacao;
    return div;
  };
  legenda.addTo(mapa);
})();
"""

_CSS = """
html, body { height: 100%; margin: 0; font-family: system-ui, sans-serif; background: #fff; color: #111; }
#topo { padding: 8px 16px; background: #222; color: #fff; font-size: 15px; }
#aviso { padding: 6px 16px; background: #fff3cd; color: #5c4400; font-weight: 600; font-size: 14px; }
#mapa { position: absolute; top: var(--topo, 40px); bottom: 0; left: 0; right: 0; }
.legenda { background: #fff; padding: 8px 10px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,.3); font-size: 12px; line-height: 1.7; }
.pt { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 6px; vertical-align: middle; border: 1px solid #333; }
.pt.anel { background: transparent; border: 2px dashed #000; }
.base-q { width: 12px; height: 12px; background: #1565c0; border: 2px solid #fff; outline-offset: 0; }
.base-q.vazia { opacity: 0.55; }
.base-q.inl { display: inline-block; margin-right: 6px; vertical-align: middle; width: 8px; height: 8px; }
.ln { display: inline-block; width: 18px; height: 3px; background: #1565c0; margin-right: 6px; vertical-align: middle; }
.esc { margin-top: 4px; padding: 4px 6px; background: #000; color: #fff; font-weight: 600; }
"""


def render_mapa(resultado: ResultadoPeriodo, regiao: RegiaoCfg, cenario: Cenario | None = None, *,
                arquivo_cenario: str | None = None) -> str:
    T = textos(regiao.idioma)
    dados = _dados_mapa(resultado, regiao, cenario, arquivo_cenario)
    titulo = html.escape(T["mapa_titulo"].format(regiao=regiao.nome, periodo=resultado.plano.periodo))
    avisos = [a for a in (dados["aviso"], dados["aviso_bases"]) if a]
    aviso = f'<div id="aviso">{"<br>".join(html.escape(a) for a in avisos)}</div>' if avisos else ""
    topo_px = 40 + 30 * len(avisos)
    return f"""<!doctype html>
<html lang="{html.escape(regiao.idioma)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<link rel="stylesheet" href="{LEAFLET_CSS}">
<style>:root {{ --topo: {topo_px}px; }}{_CSS}</style>
</head>
<body>
<div id="topo">{titulo}</div>
{aviso}
<div id="mapa"></div>
<script id="dados" type="application/json">{_json_seguro(dados)}</script>
<script src="{LEAFLET_JS}"></script>
<script>{_JS}</script>
</body>
</html>
"""
