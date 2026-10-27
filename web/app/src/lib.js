// Pure helpers shared by the screens. Colors and rules mirror app/output/mapa.py and app/output/comum.py.
import { scenarioPayload } from './api.js';
// payload do POST /api/run e /api/cenarios: o mesmo de api.scenarioPayload, sem notas vazias (uma por linha no textarea)
export function payloadCenario(scenario, region, period) {
  const p = scenarioPayload(scenario, region, period);
  return { ...p, notas: (p.notas || []).map((n) => String(n).trim()).filter(Boolean) };
}
export const CORES = { alta: '#c62828', media: '#ef6c00', baixa: '#f9a825' };
export const ESTILO_BASE = {
  oficial: { cor: '#1565c0', borda: 'solid' },
  osm: { cor: '#00838f', borda: 'solid' },
  declarada: { cor: '#6a1b9a', borda: 'dashed' },
  estimada: { cor: '#757575', borda: 'dotted' },
};
// tercis do ranking de prioridade do período (comum.faixas_prioridade)
export function faixas(ocorrencias = []) {
  const s = [...ocorrencias].sort((a, b) => b.prioridade - a.prioridade),
    n = s.length;
  return Object.fromEntries(
    s.map((o, i) => {
      const f = n ? i / n : 0;
      return [o.id, f < 1 / 3 ? 'alta' : f < 2 / 3 ? 'media' : 'baixa'];
    }),
  );
}
// procedência efetiva (comum.procedencia_base): base simulada ou declarada no cenário é "declarada"; o padrão do contrato é "osm"
export function procedencia(b) {
  return b?.simulada || b?.confianca === 'declarada' ? 'declarada' : b?.confianca || 'osm';
}
export function procedenciasPresentes(bases = []) {
  const p = new Set(bases.map(procedencia));
  return Object.keys(ESTILO_BASE).filter((k) => p.has(k));
}
// ocorrencia_id -> motivos; escalações sem ocorrência ficam na chave ""
export function escalados(escalacoes = []) {
  const m = {};
  for (const e of escalacoes) {
    const k = e.ocorrencia_id || '';
    (m[k] ||= []).push(e);
  }
  return m;
}
// id legível e único: <base curta>-t<n> / -a<n> (web/README.md, "Recursos do dia", passo 3)
// bases do OSM não têm nome no id: usa a última palavra do nome ("CBMTO 1º BBM Palmas" -> "palmas")
export function baseCurta(baseId, nome) {
  const osm = /^osm_[nwr](\d+)$/.exec(baseId);
  if (osm) {
    const w = String(nome || '')
      .replace(/\(.*?\)/g, '')
      .trim()
      .split(/\s+/)
      .pop()
      .normalize('NFD')
      .replace(/[^A-Za-z0-9]/g, '')
      .toLowerCase();
    return w || `osm${osm[1].slice(-4)}`;
  }
  return (
    String(baseId)
      .replace(/^(cbmto|decl|osm|prevfogo|icmbio|est)_/, '')
      .replace(/[^A-Za-z0-9]+/g, '')
      .slice(0, 14)
      .toLowerCase() || 'base'
  );
}
export function novoIdRecurso(recursos, baseId, tipo, nome) {
  const pre = `${baseCurta(baseId, nome)}-${tipo === 'aereo' ? 'a' : 't'}`,
    ids = new Set(recursos.map((r) => r.id));
  let n = 1;
  while (ids.has(`${pre}${n}`)) n++;
  return `${pre}${n}`;
}
export function distKm(a, b) {
  const R = 6371,
    r = Math.PI / 180,
    dLat = (b.lat - a.lat) * r,
    dLon = (b.lon - a.lon) * r,
    x = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}
export function baseMaisProxima(ponto, bases) {
  let melhor = null;
  for (const b of bases) {
    const d = distKm(ponto, b);
    if (!melhor || d < melhor.km) melhor = { base: b, km: d };
  }
  return melhor;
}
// a API recusa base declarada fora da bbox + 1° ([lat_min, lat_max, lon_min, lon_max])
export function dentroDaRegiao(p, bbox, folga = 1) {
  return (
    !bbox ||
    (p.lat >= bbox[0] - folga && p.lat <= bbox[1] + folga && p.lon >= bbox[2] - folga && p.lon <= bbox[3] + folga)
  );
}
// erros 422 do FastAPI de um campo do cenário: fieldErrors(e,'reserva'), fieldErrors(e,'bases',1)
export function fieldErrors(error, campo, indice) {
  return (
    error?.details
      ?.filter((e) => {
        const i = e.loc?.indexOf(campo) ?? -1;
        return i >= 0 && (indice === undefined || e.loc[i + 1] === indice);
      })
      .map((e) => e.msg) || []
  );
}
export function contraPropostaDiff(proposta, contra) {
  if (!proposta || !contra) return null;
  const k = (d) => `${d.recurso_id}→${d.ocorrencia_id}`,
    a = new Set((proposta.designacoes || []).map(k)),
    b = new Set((contra.designacoes || []).map(k));
  return { sai: [...a].filter((x) => !b.has(x)), entra: [...b].filter((x) => !a.has(x)) };
}

// plano.resumo -> {texto, desvios, respostas}, como app/output/comum.py (dividir_resumo): as marcas que o
// back-end acrescenta (app/core/mensagens.py: sufixo_desvios, sufixo_respostas) em qualquer idioma, itens unidos por " | "
const MARCAS = {
  desvios: ['Desvios do baseline:', 'Deviations from the baseline:'],
  respostas: ['Respostas ao Crítico:', 'Replies to the Critic:'],
};
function acharMarca(texto, chave) {
  const achados = MARCAS[chave].map((m) => [texto.indexOf(m), m.length]).filter(([i]) => i >= 0);
  if (!achados.length) return [-1, -1];
  const [i, n] = achados.sort((a, b) => a[0] - b[0])[0];
  return [i, i + n];
}
const itens = (trecho) =>
  trecho
    .split(' | ')
    .map((p) => p.trim())
    .filter(Boolean);
export function dividirResumo(resumo) {
  let t = (resumo || '').trim(),
    respostas = [],
    desvios = [];
  let [ini, fim] = acharMarca(t, 'respostas');
  if (ini >= 0) [t, respostas] = [t.slice(0, ini), itens(t.slice(fim))];
  [ini, fim] = acharMarca(t, 'desvios');
  if (ini >= 0) [t, desvios] = [t.slice(0, ini), itens(t.slice(fim))];
  return { texto: t.trim(), desvios, respostas };
}
// "<ponto> -> <decisão> (<motivo>)" -> {ponto, acao, motivo} (comum.partes_resposta); fora do formato: só o ponto
const RE_RESPOSTA = /^([\s\S]*?)\s+->\s+((?:(?!->)[^()])+?)(?:\s+\(([\s\S]*)\))?\s*$/;
export function partesResposta(resposta) {
  const s = String(resposta).trim(),
    m = RE_RESPOSTA.exec(s);
  if (!m) return { ponto: s, acao: null, motivo: null };
  return { ponto: m[1].trim(), acao: m[2].trim(), motivo: (m[3] || '').trim() || null };
}

// números no formato do idioma da interface ("87,545" em EN, "87.545" em PT): todo toLocaleString passa por aqui
export const localeNumeros = (locale) => (String(locale || '').startsWith('en') ? 'en-US' : 'pt-BR');
export const fmt = (v, locale, digitos = 2, minimo = 0) =>
  v == null || Number.isNaN(Number(v))
    ? '—'
    : Number(v).toLocaleString(localeNumeros(locale), {
        maximumFractionDigits: digitos,
        minimumFractionDigits: Math.min(minimo, digitos),
      });
// prioridade sempre com duas casas ("0.60", não "0.6"), para as colunas alinharem
export const fmtPrio = (v, locale) => fmt(v, locale, 2, 2);
// nome legível dos exemplos de output_examples/ (em português; o i18nNovo traduz). Desconhecido: o nome do arquivo.
const ROTULOS_EXEMPLO = {
  'tocantins-escasso-real-en': 'Execução real · equipes escassas (EN)',
  'tocantins-escasso-real': 'Execução real · equipes escassas (PT)',
  'nemotron-invented-id-en': 'Execução real · modelo inventou uma equipe (EN)',
  'tocantins-escasso-en': 'Amostra · equipes escassas (EN)',
  'tocantins-escasso': 'Amostra · equipes escassas',
  'tocantins-escasso-com-nota': 'Amostra · equipes escassas + nota de estrada alagada',
  'tocantins-medio': 'Amostra · equipes médias',
  'tocantins-folgado': 'Amostra · equipes folgadas',
  'tocantins-parana-analista': 'Amostra · caso do Analista (Paranã)',
};
export const rotuloExemplo = (nome) => ROTULOS_EXEMPLO[nome] || nome;
const ROTULOS_CENARIO = {
  'tocantins-escasso': 'Tocantins · equipes escassas',
  'tocantins-medio': 'Tocantins · equipes médias',
  'tocantins-folgado': 'Tocantins · equipes folgadas',
  'tocantins-parana-analista': 'Tocantins · caso do Analista (Paranã)',
};
export const rotuloCenario = (nome) => ROTULOS_CENARIO[nome] || String(nome).replaceAll('-', ' ');
// tempo de chegada legível: "22 min", "2 h 21 min" (o plano guarda horas decimais)
export const fmtDuracao = (h) => {
  if (h == null || Number.isNaN(Number(h))) return '—';
  const min = Math.round(Number(h) * 60);
  if (min < 60) return `${min} min`;
  const resto = min % 60;
  return `${Math.floor(min / 60)} h${resto ? ` ${String(resto).padStart(2, '0')} min` : ''}`;
};
// "precisam de você": escalações gerais primeiro, depois por população exposta (e prioridade no empate)
export function ordenarEscalacoes(escalacoes = [], ocorrencias = []) {
  const occ = Object.fromEntries(ocorrencias.map((o) => [o.id, o]));
  const chave = (e) => [
    e.ocorrencia_id ? 1 : 0,
    -(occ[e.ocorrencia_id]?.pop_raio ?? 0),
    -(occ[e.ocorrencia_id]?.prioridade ?? 0),
  ];
  return [...escalacoes].sort((a, b) => {
    const [x, y] = [chave(a), chave(b)];
    return x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
  });
}
