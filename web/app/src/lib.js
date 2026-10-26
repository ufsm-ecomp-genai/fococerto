// Pure helpers shared by the screens. Colors and rules mirror app/output/mapa.py and app/output/comum.py.
import {scenarioPayload} from './api.js';
// payload do POST /api/run e /api/cenarios: o mesmo de api.scenarioPayload, sem notas vazias (uma por linha no textarea)
export function payloadCenario(scenario,region,period) {const p=scenarioPayload(scenario,region,period);return {...p,notas:(p.notas||[]).map(n=>String(n).trim()).filter(Boolean)};}
export const CORES={alta:'#c62828',media:'#ef6c00',baixa:'#f9a825'};
export const ESTILO_BASE={oficial:{cor:'#1565c0',borda:'solid'},osm:{cor:'#00838f',borda:'solid'},declarada:{cor:'#6a1b9a',borda:'dashed'},estimada:{cor:'#757575',borda:'dotted'}};
// tercis do ranking de prioridade do período (comum.faixas_prioridade)
export function faixas(ocorrencias=[]) {const s=[...ocorrencias].sort((a,b)=>b.prioridade-a.prioridade),n=s.length;return Object.fromEntries(s.map((o,i)=>{const f=n?i/n:0;return [o.id,f<1/3?'alta':f<2/3?'media':'baixa'];}));}
// procedência efetiva (comum.procedencia_base): base simulada ou declarada no cenário é "declarada"; o padrão do contrato é "osm"
export function procedencia(b) {return b?.simulada||b?.confianca==='declarada'?'declarada':b?.confianca||'osm';}
export function procedenciasPresentes(bases=[]) {const p=new Set(bases.map(procedencia));return Object.keys(ESTILO_BASE).filter(k=>p.has(k));}
// ocorrencia_id -> motivos; escalações sem ocorrência ficam na chave ""
export function escalados(escalacoes=[]) {const m={};for(const e of escalacoes){const k=e.ocorrencia_id||'';(m[k]||=[]).push(e);}return m;}
// id legível e único: <base curta>-t<n> / -a<n> (web/README.md, "Recursos do dia", passo 3)
// bases do OSM não têm nome no id: usa a última palavra do nome ("CBMTO 1º BBM Palmas" -> "palmas")
export function baseCurta(baseId,nome) {const osm=/^osm_[nwr](\d+)$/.exec(baseId);if(osm){const w=String(nome||'').replace(/\(.*?\)/g,'').trim().split(/\s+/).pop().normalize('NFD').replace(/[^A-Za-z0-9]/g,'').toLowerCase();return w||`osm${osm[1].slice(-4)}`;}return String(baseId).replace(/^(cbmto|decl|osm|prevfogo|icmbio|est)_/,'').replace(/[^A-Za-z0-9]+/g,'').slice(0,14).toLowerCase()||'base';}
export function novoIdRecurso(recursos,baseId,tipo,nome) {const pre=`${baseCurta(baseId,nome)}-${tipo==='aereo'?'a':'t'}`,ids=new Set(recursos.map(r=>r.id));let n=1;while(ids.has(`${pre}${n}`))n++;return `${pre}${n}`;}
export function distKm(a,b) {const R=6371,r=Math.PI/180,dLat=(b.lat-a.lat)*r,dLon=(b.lon-a.lon)*r,x=Math.sin(dLat/2)**2+Math.cos(a.lat*r)*Math.cos(b.lat*r)*Math.sin(dLon/2)**2;return 2*R*Math.asin(Math.sqrt(x));}
export function baseMaisProxima(ponto,bases) {let melhor=null;for(const b of bases){const d=distKm(ponto,b);if(!melhor||d<melhor.km)melhor={base:b,km:d};}return melhor;}
// a API recusa base declarada fora da bbox + 1° ([lat_min, lat_max, lon_min, lon_max])
export function dentroDaRegiao(p,bbox,folga=1) {return !bbox||(p.lat>=bbox[0]-folga&&p.lat<=bbox[1]+folga&&p.lon>=bbox[2]-folga&&p.lon<=bbox[3]+folga);}
// erros 422 do FastAPI de um campo do cenário: fieldErrors(e,'reserva'), fieldErrors(e,'bases',1)
export function fieldErrors(error,campo,indice) {return error?.details?.filter(e=>{const i=e.loc?.indexOf(campo)??-1;return i>=0&&(indice===undefined||e.loc[i+1]===indice);}).map(e=>e.msg)||[];}
export function contraPropostaDiff(proposta,contra) {
 if(!proposta||!contra)return null;const k=d=>`${d.recurso_id}→${d.ocorrencia_id}`,a=new Set((proposta.designacoes||[]).map(k)),b=new Set((contra.designacoes||[]).map(k));
 return {sai:[...a].filter(x=>!b.has(x)),entra:[...b].filter(x=>!a.has(x))};
}
