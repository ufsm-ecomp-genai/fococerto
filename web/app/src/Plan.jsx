import {useState} from 'react';
import {AlertTriangle,MapPin,ShieldCheck,Plane,Truck,Cpu} from 'lucide-react';
import {CORES,ESTILO_BASE,procedencia,procedenciasPresentes,contraPropostaDiff} from './lib.js';

const place=o=>o?.localidades?.[0]?.nome||o?.id;
export function ResourceIcon({tipo,size=14}) {return tipo==='aereo'?<Plane size={size}/>:<Truck size={size}/>;}
export function ProvenanceBadge({base,t}) {const p=procedencia(base);return <span className="badge provenance" style={{'--prov':ESTILO_BASE[p]?.cor}}><i style={{borderStyle:ESTILO_BASE[p]?.borda}}/>{t(p)}</span>;}

// escalações no topo, abertas (web/README.md, regra 3): o coordenador não pode deixar de ver
export function EscalationList({data,onLocate,t}) {
 if(!data.escalacoes.length)return null;
 const occ=Object.fromEntries(data.ocorrencias.map(o=>[o.id,o])),gerais=data.escalacoes.filter(e=>!e.ocorrencia_id),porOc=data.escalacoes.filter(e=>e.ocorrencia_id).sort((a,b)=>(occ[b.ocorrencia_id]?.prioridade??0)-(occ[a.ocorrencia_id]?.prioridade??0));
 return <section className="panel escalations-inline" aria-labelledby="esc-title"><div className="panel-heading"><div><h2 id="esc-title"><AlertTriangle size={19}/>{t('Escalações: decisão humana necessária')} <span className="count">{data.escalacoes.length}</span></h2><p>{t('A aprovação não resolve as escalações e não despacha equipes.')}</p></div></div>
  {gerais.map((e,i)=><article key={`g${i}`} className="escalation-item general"><span className="badge red">{t('Escalação geral')}</span><p>{e.motivo}</p>{e.sugestao&&<strong>{e.sugestao}</strong>}</article>)}
  {porOc.map((e,i)=>{const o=occ[e.ocorrencia_id];return <article key={i} className="escalation-item"><div className="escalation-head"><strong>{o?place(o):e.ocorrencia_id}</strong><code>{e.ocorrencia_id}</code>{o&&<span>{t('Prioridade')} {o.prioridade.toFixed(2)} · {t('até')} {o.pop_raio?.toLocaleString()} {t('habitantes no raio')}</span>}{o&&<button className="text-button" onClick={()=>onLocate(o)}><MapPin size={14}/>{t('Ver no mapa')}</button>}</div><p>{e.motivo}</p>{e.sugestao&&<span className="badge sand">{t('Sugestão')}: {e.sugestao}</span>}</article>;})}
 </section>;
}

export function PlanLists({data,t}) {
 const rec=Object.fromEntries(data.recursos.map(r=>[r.id,r])),base=Object.fromEntries(data.bases.map(b=>[b.id,b])),occ=Object.fromEntries(data.ocorrencias.map(o=>[o.id,o]));
 return <div className="two-columns plan-lists"><section className="panel"><div className="panel-heading"><h2>{t('Recursos em reserva')} <span className="count">{data.plano.reserva.length}</span></h2></div>{!data.plano.reserva.length?<p className="fine-print">{t('nenhum')}</p>:<ul className="id-list">{data.plano.reserva.map(id=><li key={id}><span className="resource-pill"><ResourceIcon tipo={rec[id]?.tipo}/>{id}</span><small>{base[rec[id]?.base_id]?.nome||rec[id]?.base_id||''}</small></li>)}</ul>}</section>
  <section className="panel"><div className="panel-heading"><h2>{t('Ocorrências não atendidas')} <span className="count">{data.plano.nao_atendidas.length}</span></h2></div>{!data.plano.nao_atendidas.length?<p className="fine-print">{t('nenhum')}</p>:<ul className="id-list">{data.plano.nao_atendidas.map(id=><li key={id}><strong>{place(occ[id])}</strong><small><code>{id}</code>{occ[id]&&` · ${t('Prioridade')} ${occ[id].prioridade.toFixed(2)}`}</small></li>)}</ul>}</section></div>;
}

export function MapLegend({bases,t}) {
 return <div className="map-legend"><span>{t('Prioridade (faixa do período)')}:</span>{Object.entries(CORES).map(([k,c])=><span key={k}><i className="legend-circle" style={{background:c}}/>{t(k)}</span>)}<span><i className="legend-circle ring"/>{t('Escalada')}</span>{procedenciasPresentes(bases).map(p=><span key={p}><i className="legend-square" style={{background:ESTILO_BASE[p].cor,borderStyle:ESTILO_BASE[p].borda}}/>{t('Base')} {t(p)}</span>)}<span><i className="legend-line"/>{t('Terrestre')}</span><span><i className="legend-line air"/>{t('Aéreo')}</span></div>;
}

// "como chegamos aqui": violações do checador, veredito do Crítico e o que a contra-proposta mudou
export function Round({h,open,t}) {
 const diff=contraPropostaDiff(h.plano,h.veredicto?.contra_proposta),v=h.violacoes||[];
 return <details open={open}><summary><span>{t('Rodada')} {h.rodada}</span><span className={`badge ${h.veredicto?.decisao==='rejeita'?'red':'sand'}`}>{t(h.veredicto?.decisao||'—')}</span>{h.origem_critico&&<small className="origin">{t('Crítico')}: {t(h.origem_critico)}</small>}</summary>
  {h.plano?.resumo&&<p><b>{t('Proposta do Planejador')}:</b> {h.plano.resumo}</p>}
  {v.length>0&&<div className="resource-scroll"><table className="violations"><thead><tr><th>{t('Regra')}</th><th>{t('Ocorrência')}</th><th>{t('Recurso')}</th><th>{t('Sugestão')}</th></tr></thead><tbody>{v.map((x,i)=><tr key={i}><td>{t(x.regra)}{x.rigida&&<span className="badge red">{t('rígida')}</span>}</td><td><code>{x.ocorrencia_id||'—'}</code></td><td><code>{x.recurso_id||'—'}</code></td><td>{x.sugestao||'—'}</td></tr>)}</tbody></table></div>}
  {!v.length&&<p className="fine-print">{t('Nenhuma violação de regra nesta rodada.')}</p>}
  {h.veredicto?.motivos?.length>0&&<><h4>{t('Motivos do Crítico')}</h4>{h.veredicto.motivos.map((m,j)=><p key={j}>{m}</p>)}</>}
  {diff&&(diff.sai.length+diff.entra.length>0)&&<div className="diff"><h4>{t('Contra-proposta do Crítico')}</h4>{diff.sai.map(x=><code key={x} className="out">− {x}</code>)}{diff.entra.map(x=><code key={x} className="in">+ {x}</code>)}</div>}
  <details><summary>{t('Histórico completo')}</summary><pre>{JSON.stringify(h,null,2)}</pre></details>
 </details>;
}

// procedência da execução: quem fez o quê e, nas chamadas de LLM, qual modelo respondeu
export function TraceTable({trace,t,locale}) {
 const [soLlm,setSoLlm]=useState(false),rows=soLlm?trace.filter(e=>e.evento==='llm_call'):trace,llm=trace.filter(e=>e.evento==='llm_call');
 return <><div className="trace-toolbar"><span><Cpu size={15}/>{llm.length} {t('chamadas de LLM')}{llm.length>0&&` · ${[...new Set(llm.map(e=>e.routed_model||e.modelo))].join(', ')}`}</span><label className="switch-line"><input type="checkbox" checked={soLlm} onChange={e=>setSoLlm(e.target.checked)}/>{t('Só chamadas de LLM')}</label></div>
  <div className="resource-scroll"><table className="trace"><thead><tr><th>{t('Hora (UTC)')}</th><th>{t('Agente')}</th><th>{t('Evento')}</th><th>{t('Modelo')}</th><th>routed_model</th><th>receipt</th><th>tokens</th><th>{t('Latência')}</th></tr></thead><tbody>{rows.map((e,i)=><tr key={i} className={e.evento==='llm_call'?'llm':''}><td>{e.t?.slice(11,19)}</td><td>{t(e.agente)}</td><td title={JSON.stringify(e.dados)}>{e.evento}</td><td>{e.modelo||'—'}</td><td>{e.routed_model||'—'}</td><td><code>{e.receipt||'—'}</code></td><td>{e.tokens?.toLocaleString(locale)??'—'}</td><td>{e.latencia_s!=null?`${e.latencia_s.toFixed(1)} s`:'—'}</td></tr>)}</tbody></table></div></>;
}
