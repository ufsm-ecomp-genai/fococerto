import { useState } from 'react';
import { AlertTriangle, ChevronRight, Plane, Truck, Cpu, Users } from 'lucide-react';
import {
  CORES,
  ESTILO_BASE,
  procedencia,
  procedenciasPresentes,
  contraPropostaDiff,
  dividirResumo,
  partesResposta,
  fmt,
  ordenarEscalacoes,
} from './lib.js';

const place = (o) => o?.localidades?.[0]?.nome || o?.id;
export function ResourceIcon({ tipo, size = 14 }) {
  return tipo === 'aereo' ? <Plane size={size} /> : <Truck size={size} />;
}
export function ProvenanceBadge({ base, t }) {
  const p = procedencia(base);
  return (
    <span className="badge provenance" style={{ '--prov': ESTILO_BASE[p]?.cor }}>
      <i style={{ borderStyle: ESTILO_BASE[p]?.borda }} />
      {t(p)}
    </span>
  );
}

// "precisam de você": compacta (localidade, população, prioridade); motivo, alcance e sugestão só ao expandir.
// Clicar centraliza o mapa (onPick). A linha aberta é a ocorrência selecionada no mapa ou na lista.
export function NeedsYou({ data, selectedId, onPick, locale, t, limite = 6 }) {
  const [todas, setTodas] = useState(false);
  const occ = Object.fromEntries(data.ocorrencias.map((o) => [o.id, o])),
    lista = ordenarEscalacoes(data.escalacoes, data.ocorrencias),
    visiveis = todas ? lista : lista.slice(0, limite);
  return (
    <section className="needs-you" aria-labelledby="needs-title">
      <h2 id="needs-title">
        <AlertTriangle size={16} />
        {t('Precisam de você')} <span className="count">{lista.length}</span>
      </h2>
      {!lista.length && <p className="fine-print">{t('Nenhuma escalação neste período.')}</p>}
      <ul>
        {visiveis.map((e, i) => {
          const o = occ[e.ocorrencia_id],
            id = e.ocorrencia_id || `geral-${i}`,
            aberta = selectedId === id;
          return (
            <li key={id} className={aberta ? 'open' : ''}>
              <button className="need-row" aria-expanded={aberta} onClick={() => onPick(aberta ? null : o || { id })}>
                <ChevronRight size={14} className="chev" />
                <strong>{o ? place(o) : t('Escalação geral')}</strong>
                {o && (
                  <span className="need-pop" title={t('até N habitantes no raio (população municipal)')}>
                    <Users size={13} />
                    {fmt(o.pop_raio, locale, 0)}
                  </span>
                )}
                {o && <span className="need-prio">{fmt(o.prioridade, locale)}</span>}
              </button>
              {aberta && (
                <div className="need-detail">
                  {o && (
                    <p className="fine-print">
                      <code>{o.id}</code> · {t('até')} {fmt(o.pop_raio, locale, 0)} {t('habitantes no raio')}
                    </p>
                  )}
                  {Array.isArray(e.alcance) &&
                    (e.alcance.length ? (
                      <>
                        <h4>{t('Quem poderia chegar a tempo')}</h4>
                        <ul className="reach">
                          {e.alcance.map((a) => (
                            <li key={a.recurso_id}>
                              <code>{a.recurso_id}</code> ~{fmt(a.eta_h, locale, 1)} h · {t(`alcance_${a.situacao}`)}
                              {a.destinos?.length > 0 &&
                                `: ${a.destinos
                                  .map((d) => `${d.localidade || d.ocorrencia_id} (${fmt(d.pop_raio, locale, 0)})`)
                                  .join(', ')}`}
                            </li>
                          ))}
                        </ul>
                      </>
                    ) : (
                      <p className="fine-print">{t('Nenhum recurso chega dentro do ETA máximo.')}</p>
                    ))}
                  <p>{e.motivo}</p>
                  {e.sugestao && (
                    <span className="badge sand">
                      {t('Sugestão')}: {e.sugestao}
                    </span>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
      {lista.length > limite && (
        <button className="text-button" onClick={() => setTodas((x) => !x)}>
          {todas ? t('Mostrar menos') : `${t('Ver todas')} (${lista.length})`}
        </button>
      )}
    </section>
  );
}

// reserva só aparece quando há recurso parado de propósito
export function ReserveList({ data, t }) {
  if (!data.plano.reserva.length) return null;
  const rec = Object.fromEntries(data.recursos.map((r) => [r.id, r])),
    base = Object.fromEntries(data.bases.map((b) => [b.id, b]));
  return (
    <section className="panel reserve-list">
      <div className="panel-heading">
        <h2>
          {t('Recursos em reserva')} <span className="count">{data.plano.reserva.length}</span>
        </h2>
      </div>
      <ul className="id-list">
        {data.plano.reserva.map((id) => (
          <li key={id}>
            <span className="resource-pill">
              <ResourceIcon tipo={rec[id]?.tipo} />
              {id}
            </span>
            <small>{base[rec[id]?.base_id]?.nome || rec[id]?.base_id || ''}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}

// plano.resumo separado como no plano.md: texto, desvios do baseline e respostas ao Crítico (decisão em destaque)
export function PlannerSummary({ resumo, t }) {
  const { texto, desvios, respostas } = dividirResumo(resumo);
  return (
    <div className="planner-summary">
      {texto && <p>{texto}</p>}
      {desvios.length > 0 && (
        <>
          <h4>{t('Desvios do baseline')}</h4>
          <ul>
            {desvios.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </>
      )}
      {respostas.length > 0 && (
        <>
          <h4>{t('Respostas ao Crítico')}</h4>
          <ul>
            {respostas.map((r, i) => {
              const { ponto, acao, motivo } = partesResposta(r);
              return (
                <li key={i}>
                  {ponto}
                  {acao && (
                    <>
                      {' → '}
                      <strong className="decision">{acao}</strong>
                      {motivo && `: ${motivo}`}
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}

// "como chegamos aqui": resumo do Planejador, rodadas, pareceres do Analista e memórias (aba Raciocínio e Histórico)
export function ReasoningPanels({ data, t }) {
  return (
    <>
      <section className="panel reasoning">
        <div className="panel-heading">
          <h2>{t('Resumo do Planejador')}</h2>
        </div>
        <PlannerSummary resumo={data.plano.resumo} t={t} />
      </section>
      <section className="panel reasoning">
        <div className="panel-heading">
          <h2>{t('Como chegamos aqui')}</h2>
          <span className="badge">
            {data.rodadas} {t('Rodada')}
          </span>
        </div>
        {data.historico.map((h, i) => (
          <Round key={i} h={h} open={i === 0} t={t} />
        ))}
      </section>
      <div className="two-columns">
        <section className="panel reasoning">
          <div className="panel-heading">
            <h2>{t('Pareceres do analista')}</h2>
          </div>
          {!data.pareceres.length && <p>{t('Nenhum parecer solicitado.')}</p>}
          {data.pareceres.map((p, i) => (
            <article key={i}>
              <h3>{p.pergunta}</h3>
              <span className="badge">{t(p.conclusao)}</span>{' '}
              <span className="badge sand">
                {t('Confiança')}: {t(p.confianca)}
              </span>
              <p>{p.evidencias?.join(' · ')}</p>
              <details>
                <summary>{t('Consultas')}</summary>
                <pre>{JSON.stringify(p.consultas, null, 2)}</pre>
              </details>
            </article>
          ))}
        </section>
        <section className="panel reasoning">
          <div className="panel-heading">
            <h2>{t('Memórias utilizadas')}</h2>
          </div>
          {!data.memorias_usadas.length && <p>{t('Nenhuma memória utilizada.')}</p>}
          {data.memorias_usadas.map((m, i) => (
            <article key={i}>
              <span className="badge">{t(m.tipo)}</span>
              <p>{m.texto}</p>
              <small>
                {t('Fonte')}: {m.fonte} · {t('Confiança')}: {t(String(m.confianca))}
              </small>
              {m.supersedes && (
                <p>
                  {t('Substitui')}: {m.supersedes}
                </p>
              )}
            </article>
          ))}
        </section>
      </div>
    </>
  );
}

export function MapLegend({ bases, t }) {
  return (
    <div className="map-legend">
      <span>{t('Prioridade (faixa do período)')}:</span>
      {Object.entries(CORES).map(([k, c]) => (
        <span key={k}>
          <i className="legend-circle" style={{ background: c }} />
          {t(k)}
        </span>
      ))}
      <span>
        <i className="legend-circle ring" />
        {t('Escalada')}
      </span>
      {procedenciasPresentes(bases).map((p) => (
        <span key={p}>
          <i className="legend-square" style={{ background: ESTILO_BASE[p].cor, borderStyle: ESTILO_BASE[p].borda }} />
          {t('Base')} {t(p)}
        </span>
      ))}
      <span>
        <i className="legend-line" />
        {t('Terrestre')}
      </span>
      <span>
        <i className="legend-line air" />
        {t('Aéreo')}
      </span>
    </div>
  );
}

// "como chegamos aqui": violações do checador, veredito do Crítico e o que a contra-proposta mudou
export function Round({ h, open, t }) {
  const diff = contraPropostaDiff(h.plano, h.veredicto?.contra_proposta),
    v = h.violacoes || [];
  return (
    <details open={open}>
      <summary>
        <span>
          {t('Rodada')} {h.rodada}
        </span>
        <span className={`badge ${h.veredicto?.decisao === 'rejeita' ? 'red' : 'sand'}`}>
          {t(h.veredicto?.decisao || '—')}
        </span>
        {h.origem_critico && (
          <small className="origin">
            {t('Crítico')}: {t(h.origem_critico)}
          </small>
        )}
      </summary>
      {h.plano?.resumo && (
        <>
          <h4>{t('Proposta do Planejador')}</h4>
          <PlannerSummary resumo={h.plano.resumo} t={t} />
        </>
      )}
      {v.length > 0 && (
        <div className="resource-scroll">
          <table className="violations">
            <thead>
              <tr>
                <th>{t('Regra')}</th>
                <th>{t('Ocorrência')}</th>
                <th>{t('Recurso')}</th>
                <th>{t('Sugestão')}</th>
              </tr>
            </thead>
            <tbody>
              {v.map((x, i) => (
                <tr key={i}>
                  <td>
                    {t(x.regra)}
                    {x.rigida && <span className="badge red">{t('rígida')}</span>}
                  </td>
                  <td>
                    <code>{x.ocorrencia_id || '—'}</code>
                  </td>
                  <td>
                    <code>{x.recurso_id || '—'}</code>
                  </td>
                  <td>{x.sugestao || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!v.length && <p className="fine-print">{t('Nenhuma violação de regra nesta rodada.')}</p>}
      {h.veredicto?.motivos?.length > 0 && (
        <>
          <h4>{t('Motivos do Crítico')}</h4>
          {h.veredicto.motivos.map((m, j) => (
            <p key={j}>{m}</p>
          ))}
        </>
      )}
      {diff && diff.sai.length + diff.entra.length > 0 && (
        <div className="diff">
          <h4>{t('Contra-proposta do Crítico')}</h4>
          {diff.sai.map((x) => (
            <code key={x} className="out">
              − {x}
            </code>
          ))}
          {diff.entra.map((x) => (
            <code key={x} className="in">
              + {x}
            </code>
          ))}
        </div>
      )}
      {h.veredicto?.contra_proposta?.resumo && (
        <details className="counter-summary">
          <summary>{t('Resumo da contra-proposta')}</summary>
          <PlannerSummary resumo={h.veredicto.contra_proposta.resumo} t={t} />
        </details>
      )}
      <details>
        <summary>{t('Histórico completo')}</summary>
        <pre>{JSON.stringify(h, null, 2)}</pre>
      </details>
    </details>
  );
}

// procedência da execução: quem fez o quê e, nas chamadas de LLM, qual modelo respondeu
export function TraceTable({ trace, t, locale }) {
  const [soLlm, setSoLlm] = useState(false),
    rows = soLlm ? trace.filter((e) => e.evento === 'llm_call') : trace,
    llm = trace.filter((e) => e.evento === 'llm_call');
  return (
    <>
      <div className="trace-toolbar">
        <span>
          <Cpu size={15} />
          {llm.length} {t('chamadas de LLM')}
          {llm.length > 0 && ` · ${[...new Set(llm.map((e) => e.routed_model || e.modelo))].join(', ')}`}
        </span>
        <label className="switch-line">
          <input type="checkbox" checked={soLlm} onChange={(e) => setSoLlm(e.target.checked)} />
          {t('Só chamadas de LLM')}
        </label>
      </div>
      <div className="resource-scroll">
        <table className="trace">
          <thead>
            <tr>
              <th>{t('Hora (UTC)')}</th>
              <th>{t('Agente')}</th>
              <th>{t('Evento')}</th>
              <th>{t('Modelo')}</th>
              <th>routed_model</th>
              <th>receipt</th>
              <th>tokens</th>
              <th>{t('Latência')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e, i) => (
              <tr key={i} className={e.evento === 'llm_call' ? 'llm' : ''}>
                <td>{e.t?.slice(11, 19)}</td>
                <td>{t(e.agente)}</td>
                <td title={JSON.stringify(e.dados)}>{e.evento}</td>
                <td>{e.modelo || '—'}</td>
                <td>{e.routed_model || '—'}</td>
                <td>
                  <code>{e.receipt || '—'}</code>
                </td>
                <td>{e.tokens != null ? fmt(e.tokens, locale, 0) : '—'}</td>
                <td>{e.latencia_s != null ? `${e.latencia_s.toFixed(1)} s` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
