import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {ApiError} from '../src/api.js';
import {faixas,procedencia,procedenciasPresentes,escalados,novoIdRecurso,baseCurta,distKm,baseMaisProxima,dentroDaRegiao,fieldErrors,payloadCenario,contraPropostaDiff} from '../src/lib.js';

const mock=nome=>JSON.parse(readFileSync(new URL(`../../mocks/${nome}`,import.meta.url),'utf8'));

test('priority bands are terciles of the period ranking, like app/output/comum.faixas_prioridade',()=>{
 const oc=[0.9,0.8,0.7,0.6,0.5,0.4].map((p,i)=>({id:`o${i}`,prioridade:p}));
 assert.deepEqual(faixas(oc),{o0:'alta',o1:'alta',o2:'media',o3:'media',o4:'baixa',o5:'baixa'});
 assert.deepEqual(faixas([]),{});
 const plano=mock('plano_tocantins-escasso-real.json'),f=faixas(plano.ocorrencias),top=[...plano.ocorrencias].sort((a,b)=>b.prioridade-a.prioridade)[0];
 assert.equal(f[top.id],'alta');assert.equal(Object.keys(f).length,plano.ocorrencias.length);
});

test('base provenance follows comum.procedencia_base: simulated or declared is "declarada", default "osm"',()=>{
 assert.equal(procedencia({confianca:'oficial'}),'oficial');
 assert.equal(procedencia({confianca:'oficial',simulada:true}),'declarada');
 assert.equal(procedencia({confianca:'declarada'}),'declarada');
 assert.equal(procedencia({}),'osm');
 assert.deepEqual(procedenciasPresentes(mock('bases_tocantins.json').bases),['oficial','osm']);
});

test('escalations are grouped by incident, general ones under ""',()=>{
 const m=escalados([{ocorrencia_id:'a',motivo:'x'},{ocorrencia_id:null,motivo:'impasse'},{ocorrencia_id:'a',motivo:'y'}]);
 assert.equal(m.a.length,2);assert.equal(m[''][0].motivo,'impasse');
});

test('generated crew ids are readable and unique per base and type',()=>{
 assert.equal(baseCurta('cbmto_porto_nacional'),'portonacional');
 assert.equal(baseCurta('osm_n5067657890','CBMTO 1º BBM Palmas'),'palmas');assert.equal(baseCurta('osm_n3165869368','Bombeiros (perto de Porangatu, 1 km)'),'bombeiros');assert.equal(baseCurta('osm_n5067657890'),'osm7890');
 const r=[{id:'gurupi-t1'},{id:'gurupi-t2'}];
 assert.equal(novoIdRecurso(r,'cbmto_gurupi','terrestre'),'gurupi-t3');
 assert.equal(novoIdRecurso(r,'cbmto_gurupi','aereo'),'gurupi-a1');
 assert.equal(novoIdRecurso([],'decl_novo_acordo','terrestre'),'novoacordo-t1');
});

test('declared station checks: distance, nearest known station and region bbox + 1°',()=>{
 const palmas={lat:-10.206127,lon:-48.343395};
 assert.ok(Math.abs(distKm(palmas,{lat:-10.17611,lon:-48.86667})-57.3)<1); // Palmas -> Paraíso, ~57 km
 const m=baseMaisProxima({lat:-10.21,lon:-48.35},mock('bases_tocantins.json').bases);
 assert.equal(m.base.id,'osm_n5067657890');assert.ok(m.km<3);
 const bbox=[-13.0,-8.0,-49.5,-45.5];
 assert.ok(dentroDaRegiao({lat:-13.5,lon:-46},bbox));
 assert.ok(!dentroDaRegiao({lat:-15,lon:-46},bbox));
 assert.ok(dentroDaRegiao({lat:0,lon:0},undefined));
});

test('422 errors map to reserve and declared stations, not only to crews',()=>{
 const e=new ApiError([{loc:['body','cenario','bases',1,'lat'],msg:'Fora da região'},{loc:['body','cenario','reserva'],msg:'Reserva negativa'},{loc:['body','cenario','recursos',0,'id'],msg:'Id repetido'}],422);
 assert.deepEqual(fieldErrors(e,'reserva'),['Reserva negativa']);
 assert.deepEqual(fieldErrors(e,'bases',1),['Fora da região']);
 assert.deepEqual(fieldErrors(e,'bases',0),[]);
 assert.deepEqual(fieldErrors(null,'reserva'),[]);
});

test('scenario payload drops blank note lines and keeps everything else',()=>{
 const p=payloadCenario({recursos:[{id:'r',base_id:'b',tipo:'terrestre',capacidade:'1',disponivel:true}],bases:[],reserva:'1',notas:['ponte interditada','','  '],simulado:true},'tocantins','2026-10-23');
 assert.deepEqual(p.notas,['ponte interditada']);assert.equal(p.reserva,1);assert.equal(p.recursos[0].capacidade,1);assert.equal(p.periodo,'2026-10-23');
});

test('counter-proposal diff lists the assignments the Critic removed and added (real plan history)',()=>{
 assert.equal(contraPropostaDiff({designacoes:[]},null),null);
 const d=contraPropostaDiff({designacoes:[{recurso_id:'a',ocorrencia_id:'x'},{recurso_id:'b',ocorrencia_id:'y'}]},{designacoes:[{recurso_id:'a',ocorrencia_id:'x'},{recurso_id:'b',ocorrencia_id:'z'}]});
 assert.deepEqual(d,{sai:['b→y'],entra:['b→z']});
 const h=mock('plano_tocantins-folgado.json').historico.find(x=>x.veredicto?.contra_proposta);
 if(h){const r=contraPropostaDiff(h.plano,h.veredicto.contra_proposta);assert.ok(r.sai.length+r.entra.length>0);}
});
