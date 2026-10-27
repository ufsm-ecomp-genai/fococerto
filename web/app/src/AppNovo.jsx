import { useEffect, useRef, useState } from 'react';
import {
  Flame,
  LayoutDashboard,
  Truck,
  GitBranch,
  ArrowUpRight,
  ArrowRight,
  ChevronDown,
  Search,
  AlertTriangle,
  MapPin,
  ShieldCheck,
  Plus,
  X,
  Download,
  Check,
  Clock,
  Layers,
  Trash2,
  LoaderCircle,
  NotebookPen,
  Globe,
  ChevronRight,
  Sun,
  Moon,
} from 'lucide-react';
import { api, enc, resourceErrors } from './api';
import { translator } from './i18nNovo';
import OperationMap from './MapaPlano';
import './novo.css';
import './tema.css';
import logo from './assets/logo.png';
import { Steps, ScenarioStart, ReviewSummary, JourneyActions, Coverage } from './Journey';
import { NeedsYou, ReserveList, ReasoningPanels, MapLegend, TraceTable, ResourceIcon, ProvenanceBadge } from './Plan';
import {
  novoIdRecurso,
  fieldErrors,
  baseMaisProxima,
  dentroDaRegiao,
  payloadCenario as scenarioPayload,
  fmt,
  localeNumeros,
} from './lib';

// tema claro/escuro: começa pela preferência do sistema; a escolha fica neste navegador (localStorage pode falhar)
const temaInicial = () => {
  try {
    const t = localStorage.getItem('fococerto-tema');
    if (t === 'light' || t === 'dark') return t;
  } catch {}
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};
const emptyScenario = () => ({ recursos: [], bases: [], reserva: 0, notas: [], simulado: true });
const num = (v, locale) => fmt(v, locale);
// idioma inicial: o do navegador; fora do português, inglês (os juízes são internacionais)
const idiomaInicial = () =>
  String(globalThis.navigator?.language || '')
    .toLowerCase()
    .startsWith('pt')
    ? 'pt-BR'
    : 'en';
const place = (o) => o?.localidades?.[0]?.nome || o?.id;
function Badge({ children, tone = '', title }) {
  return (
    <span className={`badge ${tone}`} title={title || undefined}>
      {children}
    </span>
  );
}
function Modal({ title, onClose, children }) {
  const ref = useRef();
  useEffect(() => {
    const prev = document.activeElement;
    ref.current.showModal();
    return () => {
      ref.current?.close();
      prev?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="modal-head">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Fechar / Close" onClick={onClose}>
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

export default function App() {
  const [resourceStep, setResourceStep] = useState(0);
  function goStep(step) {
    setResourceStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  const [locale, setLocale] = useState(idiomaInicial),
    [view, setView] = useState('overview');
  const t = translator(locale);
  const [regions, setRegions] = useState([]),
    [region, setRegion] = useState(''),
    [period, setPeriod] = useState(''),
    [periods, setPeriods] = useState([]),
    [saved, setSaved] = useState([]),
    [examples, setExamples] = useState([]),
    [scenarios, setScenarios] = useState([]),
    [bases, setBases] = useState([]);
  const [data, setData] = useState(null),
    [example, setExample] = useState(''),
    [selected, setSelected] = useState(null),
    [scenario, setScenario] = useState(emptyScenario),
    [sample, setSample] = useState(true),
    [error, setError] = useState(null),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [notice, setNotice] = useState(''),
    [modal, setModal] = useState(null),
    [author, setAuthor] = useState(''),
    [note, setNote] = useState(''),
    [saveName, setSaveName] = useState(''),
    [newBase, setNewBase] = useState(null),
    [job, setJob] = useState(null),
    [trace, setTrace] = useState(null),
    [query, setQuery] = useState(''),
    [filter, setFilter] = useState('assigned'),
    [tab, setTab] = useState('ordem'),
    [openNeed, setOpenNeed] = useState(null),
    [health, setHealth] = useState(null),
    [theme, setTheme] = useState(temaInicial);
  const initVersion = useRef(0),
    planVersion = useRef(0),
    contextVersion = useRef(0);
  const regionCfg = regions.find((r) => r.nome === region),
    plan = data?.plano;
  const allBases = [...scenario.bases, ...bases.filter((b) => !scenario.bases.some((x) => x.id === b.id))];
  async function loadPlan(path, exampleName = '') {
    const version = ++planVersion.current;
    setLoading(true);
    setError(null);
    try {
      const d = await api(path);
      if (version !== planVersion.current) return;
      setData(d);
      setExample(exampleName);
      setSelected(null);
      setOpenNeed(null);
      setTrace(null);
      setLocale(d.meta.idioma?.startsWith('en') ? 'en' : 'pt-BR');
    } catch (e) {
      if (version === planVersion.current) {
        setError(e);
        setData(null);
      }
    } finally {
      if (version === planVersion.current) setLoading(false);
    }
  }
  async function initialize() {
    const version = ++initVersion.current;
    setLoading(true);
    setError(null);
    try {
      const [rs, es, cs] = await Promise.all([api('/api/regioes'), api('/api/exemplos'), api('/api/cenarios')]);
      if (version !== initVersion.current) return;
      setRegions(rs);
      setExamples(es);
      setScenarios(cs);
      const r = rs.find((x) => x.tem_cache) || rs[0];
      if (!r) {
        setLoading(false);
        return;
      }
      setRegion(r.nome);
      const daRegiao = es.filter((e) => e.regiao === r.nome),
        mesmoIdioma = daRegiao.filter((e) => String(e.idioma).slice(0, 2) === locale.slice(0, 2)),
        recente = (l) => [...l].sort((a, b) => String(b.gerado_em).localeCompare(String(a.gerado_em)))[0];
      const first = recente(mesmoIdioma.filter((e) => e.modo === 'llm')) || recente(mesmoIdioma) || recente(daRegiao);
      if (first) {
        setPeriod(first.periodo);
        await loadPlan(`/api/exemplos/${enc(first.nome)}`, first.nome);
      } else setLoading(false);
    } catch (e) {
      setError(e);
      setLoading(false);
    }
  }
  useEffect(() => {
    initialize();
    return () => {
      initVersion.current++;
      planVersion.current++;
    };
  }, []);
  useEffect(() => {
    if (!region) return;
    const controller = new AbortController();
    setBases([]);
    setPeriods([]);
    setSaved([]);
    Promise.allSettled([
      api(`/api/periodos?regiao=${enc(region)}`, undefined, controller.signal),
      api(`/api/bases?regiao=${enc(region)}&sample=${sample}`, undefined, controller.signal),
    ]).then(([p, b]) => {
      if (controller.signal.aborted) return;
      if (p.status === 'fulfilled') {
        setPeriods(p.value.periodos_cache);
        setSaved(p.value.periodos_com_plano);
        setPeriod((old) => (p.value.periodos_cache.includes(old) ? old : p.value.periodos_cache.at(-1) || ''));
      } else setError(p.reason);
      if (b.status === 'fulfilled') setBases(b.value.bases);
      else setError(b.reason);
    });
    return () => controller.abort();
  }, [region, sample]);
  useEffect(() => {
    let alive = true;
    const check = () =>
      api('/api/saude').then(
        (h) => alive && setHealth(h),
        () => alive && setHealth({ ok: false }),
      );
    check();
    const timer = setInterval(check, 30000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem('fococerto-tema', theme);
    } catch {}
  }, [theme]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [view]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(''), 7000);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    if (!job?.id || ['concluido', 'erro'].includes(job.status)) return;
    let cancelled = false,
      timer;
    const poll = async () => {
      try {
        const next = await api(`/api/jobs/${enc(job.id)}`);
        if (cancelled) return;
        setJob(next);
        if (next.status === 'erro') {
          setError(new Error(next.erro));
          setBusy(false);
        } else if (next.status === 'concluido') {
          setBusy(false);
          setModal(null);
          setRegion(next.resultado.regiao);
          setPeriod(next.resultado.periodo);
          setView('overview');
          setSaved((old) => [...new Set([...old, next.resultado.periodo])]);
          await loadPlan(next.resultado.plano_url);
        } else timer = setTimeout(poll, 1500);
      } catch (e) {
        if (!cancelled) {
          setError(e);
          setBusy(false);
          setJob((old) => ({ ...old, status: 'erro' }));
        }
      }
    };
    timer = setTimeout(poll, 1000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [job?.id, job?.status]);
  function changeRegion(value) {
    contextVersion.current++;
    planVersion.current++;
    setRegion(value);
    setPeriod('');
    setData(null);
    setExample('');
    setScenario(emptyScenario());
    setResourceStep(0);
    setError(null);
    setLoading(false);
    setSelected(null);
  }
  async function act(fn) {
    setError(null);
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function loadScenario(name) {
    if (!name) return;
    const version = contextVersion.current;
    await act(async () => {
      const d = await api(`/api/cenarios/${enc(name)}`);
      if (version !== contextVersion.current) return;
      setScenario({ ...emptyScenario(), ...d.cenario });
      goStep(1);
      setPeriod(d.cenario.periodo);
      setData(null);
      setExample('');
    });
  }
  async function generate() {
    if (!period) {
      setError(new Error(t('Selecione um período com dados.')));
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const result = await api('/api/run', {
        regiao: region,
        periodo: period,
        sample,
        idioma: locale,
        cenario: scenarioPayload(scenario, region, period),
      });
      setJob({ id: result.job_id, status: result.status, progresso: [] });
      setModal('job');
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }
  async function saveScenario(replace = false) {
    if (!replace && scenarios.some((s) => s.nome === saveName && s.origem === 'salvo')) {
      setModal('replace');
      return;
    }
    await act(async () => {
      await api('/api/cenarios', { nome: saveName, cenario: scenarioPayload(scenario, region, period), sample });
      setScenarios(await api('/api/cenarios'));
      setModal(null);
      setNotice(t('Cenário salvo.'));
    });
  }
  function addResource() {
    if (!allBases.length) return;
    setScenario((s) => ({
      ...s,
      recursos: [
        ...s.recursos,
        {
          id: novoIdRecurso(s.recursos, allBases[0].id, 'terrestre', allBases[0].nome),
          base_id: allBases[0].id,
          tipo: 'terrestre',
          capacidade: 1,
          disponivel: true,
        },
      ],
    }));
  }
  function addCrew(baseId, tipo) {
    setScenario((s) => ({
      ...s,
      recursos: [
        ...s.recursos,
        {
          id: novoIdRecurso(s.recursos, baseId, tipo, allBases.find((b) => b.id === baseId)?.nome),
          base_id: baseId,
          tipo,
          capacidade: 1,
          disponivel: true,
        },
      ],
    }));
  }
  function patchResource(index, patch) {
    setScenario((s) => ({ ...s, recursos: s.recursos.map((r, i) => (i === index ? { ...r, ...patch } : r)) }));
  }
  function exportPlan() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `fococerto-${data.meta.regiao}-${data.meta.periodo}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
  const isApproved = ['aprovado', 'aprovada'].includes(data?.meta.aprovacao_humana);
  const escaladas = new Set((data?.escalacoes || []).map((e) => e.ocorrencia_id).filter(Boolean));
  // mapa e lista "precisam de você" abrem a mesma ocorrência; escalação geral (sem ocorrência) só abre na lista
  function pickOccurrence(o) {
    setOpenNeed(o?.id ?? null);
    setSelected(o && o.lat != null ? o : null);
  }
  const assignments = [...(plan?.designacoes || [])].sort((a, b) => a.ordem - b.ordem);
  const recById = Object.fromEntries((data?.recursos || []).map((r) => [r.id, r])),
    baseById = Object.fromEntries((data?.bases || []).map((b) => [b.id, b]));
  const rows = data
    ? [
        ...assignments.map((a) => ({ a, o: data.ocorrencias.find((o) => o.id === a.ocorrencia_id) })),
        ...data.ocorrencias
          .filter((o) => !assignments.some((a) => a.ocorrencia_id === o.id))
          .sort((a, b) => b.prioridade - a.prioridade)
          .map((o) => ({ o })),
      ].filter(
        ({ a, o }) =>
          o &&
          (filter === 'all' || (filter === 'assigned' ? !!a : !a)) &&
          `${place(o)} ${o.id} ${a?.recurso_id || ''}`.toLowerCase().includes(query.toLowerCase()),
      )
    : [];
  const tracePanel = data && (
    <section className="panel reasoning">
      <div className="panel-heading">
        <h2>{t('Rastro da execução')}</h2>
        <button
          className="secondary"
          disabled={!example || busy}
          onClick={() => act(async () => setTrace(await api(`/api/exemplos/${enc(example)}/trace?limite=500`)))}
        >
          {t('Carregar trace')}
        </button>
      </div>
      {trace && <TraceTable trace={trace} t={t} locale={locale} />}
      {!example && (
        <p className="fine-print">
          {t('O trace deste plano está no servidor')}: <code>{data.log_path}</code>.{' '}
          {t('A API serve o trace só dos exemplos.')}
        </p>
      )}
    </section>
  );
  const nav = [
    ['overview', LayoutDashboard, 'Visão geral'],
    ['resources', Truck, 'Recursos do dia'],
    ['reasoning', GitBranch, 'Raciocínio e memória'],
  ];
  return (
    <div className="shell">
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            setView('overview');
          }}
        >
          <span className="brand-icon">
            <img src={logo} alt="" />
          </span>
          Foco<span>Certo</span>
        </a>
        <div className="workspace-label">
          <span className="live-dot" />
          {t('COORDENAÇÃO REGIONAL')}
        </div>
        <nav>
          {nav.map(([id, Icon, label]) => (
            <button
              key={id}
              aria-label={t(label)}
              title={t(label)}
              onClick={() => setView(id)}
              className={view === id ? 'active' : ''}
            >
              <Icon size={19} />
              <span>{t(id === 'reasoning' ? 'Histórico' : label)}</span>
              {id === 'overview' && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="human">
            <ShieldCheck size={16} />
            {t('Revisão humana obrigatória')}
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            FocoCerto <ChevronRight size={14} />
            <span>{t(nav.find((n) => n[0] === view)?.[2])}</span>
          </div>
          <div className="top-right">
            <span className={`api-status ${health && !health.ok ? 'down' : ''}`} title={health?.saida || ''}>
              <span className="live-dot" />
              {t(health == null ? 'Verificando API…' : health.ok ? 'API conectada' : 'API fora do ar')}
            </span>
            <button
              className="theme-toggle"
              aria-label={t(theme === 'dark' ? 'Tema claro' : 'Tema escuro')}
              title={t(theme === 'dark' ? 'Tema claro' : 'Tema escuro')}
              onClick={() => setTheme((x) => (x === 'dark' ? 'light' : 'dark'))}
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <Globe size={15} />
            <select aria-label="Idioma / Language" value={locale} onChange={(e) => setLocale(e.target.value)}>
              <option value="pt-BR">PT-BR</option>
              <option value="en">EN</option>
            </select>
          </div>
        </header>
        <main className={`page-${view}`}>
          {view !== 'overview' && (
            <div className="page-heading">
              <div>
                <div className="eyebrow">
                  {t('COORDENAÇÃO REGIONAL')} <span>/ {region || '—'}</span>
                </div>
                <h1>
                  {t(view === 'resources' ? 'Recursos do dia' : view === 'reasoning' ? 'Como chegamos aqui' : '')}
                </h1>
                <p>
                  {t(
                    view === 'resources'
                      ? 'Informe a disponibilidade do dia ou carregue um cenário existente.'
                      : 'O que o Planejador, o Crítico e o Analista decidiram, e por quê.',
                  )}
                </p>
              </div>
            </div>
          )}
          <div className="context-bar">
            <div className="context-fields">
              <label>
                <MapPin size={16} />
                <span>{t('Região')}</span>
                <select
                  aria-label={t('Região')}
                  disabled={busy}
                  value={region}
                  onChange={(e) => changeRegion(e.target.value)}
                >
                  {regions.map((r) => (
                    // região sem cache e sem plano salvo: aparece (mostra que a região é configuração), mas não abre
                    <option key={r.nome} value={r.nome} disabled={r.tem_cache === false && !r.planos_salvos}>
                      {r.nome}
                      {r.tem_cache === false && !r.planos_salvos ? ` (${t('sem dados')})` : ''}
                    </option>
                  ))}
                </select>
              </label>
              <div className="divider" />
              <label>
                <Clock size={16} />
                <span>{t('Período UTC')}</span>
                <select
                  aria-label={t('Período UTC')}
                  disabled={busy}
                  value={period}
                  onChange={(e) => {
                    planVersion.current++;
                    setPeriod(e.target.value);
                    setData(null);
                    setExample('');
                    setSelected(null);
                    setLoading(false);
                  }}
                >
                  {!periods.length && <option value="">—</option>}
                  {[...new Set([...periods, ...saved])].sort().map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
              </label>
              {view !== 'resources' && (
                <>
                  <div className="divider" />
                  <label>
                    <Layers size={16} />
                    <select
                      aria-label={t('Escolha um exemplo')}
                      value={example}
                      disabled={busy}
                      onChange={(e) => {
                        const x = examples.find((x) => x.nome === e.target.value);
                        if (x) {
                          setPeriod(x.periodo);
                          loadPlan(`/api/exemplos/${enc(x.nome)}`, x.nome);
                        }
                      }}
                    >
                      <option value="">{t(saved.includes(period) ? 'Plano do período' : 'Escolha um exemplo')}</option>
                      {examples
                        .filter((x) => x.regiao === region)
                        .map((x) => (
                          <option key={x.nome} value={x.nome}>
                            {x.nome}
                          </option>
                        ))}
                    </select>
                  </label>
                  <button
                    className="text-button"
                    disabled={!saved.includes(period) || busy}
                    onClick={() => loadPlan(`/api/plano/${enc(region)}/${enc(period)}`)}
                  >
                    {t('Abrir plano salvo')}
                    <ArrowUpRight size={15} />
                  </button>
                </>
              )}
            </div>
            <div className="context-right">
              <Badge
                tone="sand"
                title={
                  (view === 'resources' ? scenario.simulado : (data?.meta.simulado ?? scenario.simulado))
                    ? `${t('as equipes e aeronaves deste plano vêm de um cenário de demonstração, não de um inventário real.')}${
                        data?.meta.arquivo_cenario && view !== 'resources' ? ` (${data.meta.arquivo_cenario})` : ''
                      }`
                    : ''
                }
              >
                <span className="tiny-dot" />
                {t(
                  (view === 'resources' ? scenario.simulado : (data?.meta.simulado ?? scenario.simulado))
                    ? 'Recursos simulados'
                    : 'Disponibilidade real',
                )}
              </Badge>
              {view === 'overview' && (
                <button
                  className="primary"
                  onClick={() => {
                    setView('resources');
                    goStep(0);
                  }}
                >
                  <Plus size={17} />
                  {t('Gerar novo plano')}
                </button>
              )}
            </div>
          </div>
          {error && (
            <div className="error" role="alert">
              <AlertTriangle size={20} />
              <div style={{ whiteSpace: 'pre-wrap' }}>{error.message}</div>
              <button className="icon-button" onClick={() => setError(null)} aria-label={t('Fechar')}>
                <X size={17} />
              </button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              <Check size={18} />
              {notice}
            </div>
          )}
          {view === 'overview' &&
            (loading ? (
              <div className="empty">
                <LoaderCircle className="spin" />
                {t('Carregando dados…')}
              </div>
            ) : !data ? (
              <div className="empty">
                <Flame size={34} />
                <h2>{t('Nenhum plano selecionado')}</h2>
                <p>{t('Selecione um exemplo ou configure os recursos do dia para começar.')}</p>
                {!regions.length && <button onClick={initialize}>{t('Tentar novamente')}</button>}
              </div>
            ) : (
              <>
                <div className="status-line" role="status">
                  <span>
                    <b>{assignments.length}</b> {t('equipes designadas')}
                  </span>
                  <span className={data.escalacoes.length ? 'needs' : ''}>
                    <b>{data.escalacoes.length}</b> {t('ocorrências precisam de você')}
                  </span>
                  <span>
                    <b>{plan.reserva.length}</b> {t('em reserva')}
                  </span>
                  <span
                    className="status-mode"
                    title={t(data.meta.modo === 'llm' ? 'Modelo via Nightshift' : 'Agentes determinísticos')}
                  >
                    <span className="live-dot" />
                    {t(data.meta.modo === 'llm' ? 'Modelo via Nightshift' : 'Agentes determinísticos')}
                  </span>
                  <span className={`badge ${isApproved ? '' : 'sand'}`}>
                    {isApproved
                      ? `${t('Aprovado por')} ${data.meta.aprovado_por || t('coordenador')}${
                          data.meta.aprovado_em
                            ? ` · ${new Date(data.meta.aprovado_em).toLocaleString(localeNumeros(locale))}`
                            : ''
                        }`
                      : t('Aprovação pendente')}
                  </span>
                </div>
                <div className="ops-grid">
                  <section className="panel map-panel">
                    <OperationMap
                      bbox={regionCfg?.bbox}
                      bases={data.bases}
                      occurrences={data.ocorrencias}
                      assignments={assignments}
                      resources={data.recursos}
                      escalations={data.escalacoes}
                      selected={selected}
                      onSelect={pickOccurrence}
                      locale={locale}
                      t={t}
                    />
                    <MapLegend bases={data.bases} t={t} />
                  </section>
                  <aside className="panel side-panel">
                    {selected && !escaladas.has(selected.id) && (
                      <div className="side-occurrence">
                        <div className="side-occurrence-head">
                          <strong>{place(selected)}</strong>
                          <button className="icon-button" onClick={() => pickOccurrence(null)} aria-label={t('Fechar')}>
                            <X size={16} />
                          </button>
                        </div>
                        <Occurrence o={selected} t={t} locale={locale} />
                      </div>
                    )}
                    <NeedsYou data={data} selectedId={openNeed} onPick={pickOccurrence} locale={locale} t={t} />
                    <div className="side-actions">
                      <div className="side-buttons">
                        <button
                          className="primary"
                          disabled={!!example || busy || isApproved}
                          title={example ? t('Exemplos não podem ser aprovados') : ''}
                          onClick={() => setModal('approve')}
                        >
                          <Check size={17} />
                          {t('Aprovar plano')}
                        </button>
                        <button className="secondary" onClick={() => setModal('note')}>
                          <NotebookPen size={16} />
                          {t('Nota')}
                        </button>
                      </div>
                      <p className="fine-print">{t('A aprovação não resolve as escalações e não despacha equipes.')}</p>
                      {example && (
                        <button
                          className="text-button example-cta"
                          onClick={() => {
                            setView('resources');
                            goStep(0);
                          }}
                        >
                          {t('Criar meu plano a partir de um cenário')}
                          <ArrowRight size={14} />
                        </button>
                      )}
                    </div>
                  </aside>
                </div>
                <div className="overview-tabs tabs" role="tablist">
                  {[
                    ['ordem', 'Ordem de recursos'],
                    ['raciocinio', 'Raciocínio'],
                    ['trace', 'Trace'],
                  ].map(([key, label]) => (
                    <button
                      key={key}
                      role="tab"
                      aria-selected={tab === key}
                      className={tab === key ? 'selected' : ''}
                      onClick={() => setTab(key)}
                    >
                      {t(label)}
                    </button>
                  ))}
                </div>
                {tab === 'raciocinio' && <ReasoningPanels data={data} t={t} />}
                {tab === 'trace' && tracePanel}
                {tab === 'ordem' && (
                  <>
                    <section className="panel assignments">
                      <div className="panel-heading">
                        <div>
                          <h2>
                            {t('Ordem de atendimento')} <span className="count">{assignments.length}</span>
                          </h2>
                          <p>{t('Prioridade, deslocamento e justificativa')}</p>
                        </div>
                        <button className="text-button" onClick={exportPlan}>
                          <Download size={15} />
                          {t('Exportar JSON')}
                        </button>
                      </div>
                      <div className="table-toolbar">
                        <div className="tabs">
                          {[
                            ['all', 'Todas'],
                            ['assigned', 'Designadas'],
                            ['unassigned', 'Sem recurso'],
                          ].map(([key, label]) => (
                            <button
                              key={key}
                              className={filter === key ? 'selected' : ''}
                              onClick={() => setFilter(key)}
                            >
                              {t(label)}
                            </button>
                          ))}
                        </div>
                        <label className="search">
                          <Search size={16} />
                          <input
                            aria-label={t('Buscar ocorrência ou recurso')}
                            placeholder={t('Buscar ocorrência ou recurso')}
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                          />
                        </label>
                      </div>
                      <div className="assignment-head">
                        <span># / {t('Ocorrência')}</span>
                        <span>{t('Prioridade')}</span>
                        <span>{t('Designação')}</span>
                        <span>{t('Chegada estimada')}</span>
                      </div>
                      {rows.map(({ a, o }) => (
                        <details className="assignment-row" key={`${o.id}-${a?.recurso_id || ''}`}>
                          <summary>
                            <div className="incident-name">
                              <span className={`order ${a ? '' : 'unassigned'}`}>
                                {a ? String(a.ordem).padStart(2, '0') : '—'}
                              </span>
                              <div>
                                <strong>{place(o)}</strong>
                                <small>
                                  {o.n_focos} {t('focos')} · {t('até')} {num(o.pop_raio, locale)}{' '}
                                  {t('habitantes no raio')}
                                </small>
                              </div>
                            </div>
                            <div className="priority">
                              <b>{num(o.prioridade, locale)}</b>
                              <span>
                                <i style={{ width: `${o.prioridade * 100}%` }} />
                              </span>
                            </div>
                            <div>
                              {a ? (
                                <div className="assignment-resource">
                                  <span className="resource-pill">
                                    <ResourceIcon tipo={recById[a.recurso_id]?.tipo} />
                                    {a.recurso_id}
                                  </span>
                                  {baseById[recById[a.recurso_id]?.base_id] && (
                                    <small>
                                      {baseById[recById[a.recurso_id].base_id].nome}{' '}
                                      <ProvenanceBadge base={baseById[recById[a.recurso_id].base_id]} t={t} />
                                    </small>
                                  )}
                                </div>
                              ) : (
                                <Badge tone="red">{t('Sem recurso')}</Badge>
                              )}
                            </div>
                            <div className="eta">
                              {a ? (
                                <>
                                  <Clock size={14} />~{num(a.eta_h, locale)} h
                                </>
                              ) : (
                                '—'
                              )}
                              <ChevronDown size={16} />
                            </div>
                          </summary>
                          <div className="assignment-expanded">
                            {a && (
                              <>
                                <h4>{t('Justificativa e evidências')}</h4>
                                <p>{a.justificativa}</p>
                                <div className="evidence-list">
                                  {a.evidencias.map((e, i) => (
                                    <code key={i}>{e}</code>
                                  ))}
                                </div>
                              </>
                            )}
                            <Occurrence o={o} t={t} locale={locale} />
                            <button className="text-button" onClick={() => pickOccurrence(o)}>
                              <MapPin size={14} />
                              {t('Mapa da operação')}
                            </button>
                          </div>
                        </details>
                      ))}
                      {!rows.length && <div className="empty compact">{t('Nenhum resultado para a busca.')}</div>}
                      <div className="table-foot">
                        <span>
                          <Clock size={13} />
                          {t('ETA é estimativa por distância, tortuosidade e velocidade; não é uma rota real.')}
                        </span>
                        <span>{t('O último dia do cache pode estar incompleto.')}</span>
                      </div>
                    </section>
                    <ReserveList data={data} t={t} />
                  </>
                )}
              </>
            ))}
          {view === 'resources' && (
            <div className={`resource-flow step-${resourceStep}`}>
              <Steps step={resourceStep} onStep={goStep} busy={busy} t={t} />
              {resourceStep === 0 && (
                <ScenarioStart
                  scenarios={scenarios}
                  region={region}
                  onLoad={loadScenario}
                  onBlank={() => {
                    setScenario(emptyScenario());
                    goStep(1);
                  }}
                  busy={busy}
                  t={t}
                />
              )}
              <div className="resource-top">
                <label>
                  {t('Carregar cenário')}
                  <select disabled={busy} value="" onChange={(e) => loadScenario(e.target.value)}>
                    <option value="">{t('Carregar cenário')}…</option>
                    {scenarios
                      .filter((s) => s.regiao === region)
                      .map((s, i) => (
                        <option key={`${s.nome}-${i}`} value={s.nome}>
                          {s.nome} · {s.recursos}
                        </option>
                      ))}
                  </select>
                </label>
                <button className="secondary" disabled={busy} onClick={() => setScenario(emptyScenario())}>
                  {t('Começar em branco')}
                </button>
              </div>
              <div className="resource-grid">
                {resourceStep === 2 && <ReviewSummary scenario={scenario} period={period} region={region} t={t} />}
                <section className="panel base-map-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>{t('Bases e equipes')}</h2>
                      <p>{t('Clique no mapa para declarar uma base')}</p>
                    </div>
                    <MapPin size={20} />
                  </div>
                  {resourceStep === 1 && (
                    <OperationMap
                      bbox={regionCfg?.bbox}
                      bases={allBases}
                      resources={scenario.recursos}
                      crewCounts
                      locale={locale}
                      t={t}
                      onClick={(latlng) => {
                        if (!busy) {
                          setNewBase({
                            id: `decl_${crypto.randomUUID().slice(0, 8)}`,
                            nome: '',
                            lat: latlng.lat,
                            lon: latlng.lng,
                            fonte: '',
                            confianca: 'declarada',
                            simulada: scenario.simulado,
                          });
                          setModal('base');
                        }
                      }}
                    />
                  )}
                  <div className="base-list">
                    {allBases.map((b) => {
                      const n = scenario.recursos.filter((r) => r.base_id === b.id).length,
                        bi = scenario.bases.findIndex((x) => x.id === b.id),
                        errs = bi >= 0 ? fieldErrors(error, 'bases', bi) : [];
                      return (
                        <details key={b.id} className={errs.length ? 'invalid-row' : ''}>
                          <summary>
                            <span>
                              {b.nome}
                              {n > 0 && <span className="count">{n}</span>}
                            </span>
                            <Badge>
                              {t(b.confianca || 'Não disponível')}
                              {b.simulada && ` · ${t('Simulado')}`}
                            </Badge>
                          </summary>
                          <p>{b.fonte || '—'}</p>
                          {b.confianca === 'estimada' && <p>{t('Sede municipal sem unidade verificada.')}</p>}
                          {(b.orgao || b.coordenada) && (
                            <p>
                              {b.orgao} {b.data_fonte} · {b.coordenada}
                            </p>
                          )}
                          {errs.map((m, k) => (
                            <small className="field-error" key={k}>
                              {m}
                            </small>
                          ))}
                          <div className="crew-add">
                            <button
                              type="button"
                              className="secondary"
                              disabled={busy}
                              onClick={() => addCrew(b.id, 'terrestre')}
                            >
                              <Plus size={14} />
                              <Truck size={14} />
                              {t('Terrestre')}
                            </button>
                            <button
                              type="button"
                              className="secondary"
                              disabled={busy}
                              onClick={() => addCrew(b.id, 'aereo')}
                            >
                              <Plus size={14} />
                              {t('Aéreo')}
                            </button>
                          </div>
                        </details>
                      );
                    })}
                  </div>
                </section>
                <section className="panel settings">
                  <div className="panel-heading">
                    <h2>{t('Configuração do período')}</h2>
                  </div>
                  <div className="form-stack">
                    <label className="switch-line">
                      <input
                        type="checkbox"
                        checked={scenario.simulado}
                        onChange={(e) => setScenario((s) => ({ ...s, simulado: e.target.checked }))}
                      />
                      {t('Recursos simulados')}
                    </label>
                    <label>
                      {t('Reserva mínima')}
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={scenario.reserva}
                        onChange={(e) => setScenario((s) => ({ ...s, reserva: e.target.value }))}
                      />
                      {fieldErrors(error, 'reserva').map((m, k) => (
                        <small className="field-error" key={k}>
                          {m}
                        </small>
                      ))}
                    </label>
                    <label>
                      {t('Modo de execução')}
                      <select value={String(sample)} onChange={(e) => setSample(e.target.value === 'true')}>
                        <option value="true">{t('Sample · sem serviços externos')}</option>
                        <option value="false">{t('Serviços configurados no servidor')}</option>
                      </select>
                    </label>
                    <label>
                      {t('Idioma do plano')}
                      <select value={locale} onChange={(e) => setLocale(e.target.value)}>
                        <option value="pt-BR">Português</option>
                        <option value="en">English</option>
                      </select>
                    </label>
                    <label>
                      {t('Notas deste período')}
                      <textarea
                        rows="4"
                        value={scenario.notas.join('\n')}
                        onChange={(e) => setScenario((s) => ({ ...s, notas: e.target.value.split('\n') }))}
                      />
                      <small>{t('Uma observação por linha. Não é salva na memória permanente.')}</small>
                    </label>
                    <p className="fine-print">
                      {t('Esta execução substitui o plano salvo para a mesma região e período.')}
                    </p>
                    <button
                      className="primary wide"
                      disabled={busy || !period || !scenario.recursos.length}
                      onClick={generate}
                    >
                      {busy ? <LoaderCircle className="spin" size={17} /> : <GitBranch size={17} />} {t('Gerar plano')}
                    </button>
                    <button className="secondary wide" disabled={busy || !period} onClick={() => setModal('save')}>
                      {t('Salvar cenário')}
                    </button>
                  </div>
                </section>
              </div>
              <section className="panel resources-table">
                <div className="panel-heading">
                  <h2>
                    {t('Recursos do dia')} <span className="count">{scenario.recursos.length}</span>
                  </h2>
                  <button className="secondary" disabled={!allBases.length || busy} onClick={addResource}>
                    <Plus size={16} />
                    {t('Adicionar recurso')}
                  </button>
                </div>
                {!scenario.recursos.length ? (
                  <div className="empty compact">
                    {t('Nenhum recurso informado. Adicione equipes ou carregue um cenário.')}
                  </div>
                ) : (
                  <div className="resource-scroll">
                    <table>
                      <thead>
                        <tr>
                          {['Identificador', 'Base', 'Tipo', 'Capacidade', 'Disponível', 'Remover'].map((x) => (
                            <th key={x}>{t(x)}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {scenario.recursos.map((r, i) => (
                          <tr key={i} className={resourceErrors(error, i).length ? 'invalid-row' : ''}>
                            <td>
                              <input
                                aria-label={`${t('Identificador')} ${i + 1}`}
                                value={r.id}
                                onChange={(e) => patchResource(i, { id: e.target.value })}
                              />
                              {resourceErrors(error, i).map((msg, k) => (
                                <small className="field-error" key={k}>
                                  {msg}
                                </small>
                              ))}
                            </td>
                            <td>
                              <select
                                aria-label={`${t('Base')} ${i + 1}`}
                                value={r.base_id}
                                onChange={(e) => patchResource(i, { base_id: e.target.value })}
                              >
                                {allBases.map((b) => (
                                  <option key={b.id} value={b.id}>
                                    {b.nome}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td>
                              <select
                                aria-label={`${t('Tipo')} ${i + 1}`}
                                value={r.tipo}
                                onChange={(e) => patchResource(i, { tipo: e.target.value })}
                              >
                                <option value="terrestre">{t('Terrestre')}</option>
                                <option value="aereo">{t('Aéreo')}</option>
                              </select>
                            </td>
                            <td>
                              <input
                                aria-label={`${t('Capacidade')} ${i + 1}`}
                                type="number"
                                min="1"
                                step="1"
                                value={r.capacidade}
                                onChange={(e) => patchResource(i, { capacidade: e.target.value })}
                              />
                            </td>
                            <td>
                              <input
                                aria-label={`${t('Disponível')} ${i + 1}`}
                                type="checkbox"
                                checked={r.disponivel}
                                onChange={(e) => patchResource(i, { disponivel: e.target.checked })}
                              />
                            </td>
                            <td>
                              <button
                                className="icon-button"
                                aria-label={`${t('Remover')} ${r.id}`}
                                onClick={() =>
                                  setScenario((s) => ({ ...s, recursos: s.recursos.filter((_, j) => j !== i) }))
                                }
                              >
                                <Trash2 size={16} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
              {resourceStep > 0 && (
                <JourneyActions
                  step={resourceStep}
                  onStep={goStep}
                  count={scenario.recursos.length}
                  busy={busy}
                  onGenerate={generate}
                  canGenerate={!!period && !!scenario.recursos.length}
                  t={t}
                />
              )}
            </div>
          )}
          {view === 'reasoning' &&
            (!data ? (
              <div className="empty">{t('Selecione um exemplo ou configure os recursos do dia para começar.')}</div>
            ) : (
              <>
                <div className="agent-flow">
                  {[
                    [Layers, 'Planejador', 'Propõe a alocação'],
                    [ShieldCheck, 'Crítico', 'Revisa regras e conflitos'],
                    [Search, 'Analista', 'Investiga incertezas'],
                  ].map(([Icon, title, caption]) => (
                    <div key={title}>
                      <Icon size={24} />
                      <h3>{t(title)}</h3>
                      <p>{t(caption)}</p>
                    </div>
                  ))}
                </div>
                <ReasoningPanels data={data} t={t} />
                {tracePanel}
              </>
            ))}
          <footer>
            <span className="footer-brand">
              <img src={logo} alt="" />
              FocoCerto
            </span>
            <span>NASA FIRMS · Open-Meteo · GeoNames</span>
            <span>{t('A decisão continua com você.')}</span>
          </footer>
        </main>
      </div>
      {modal && (
        <Modal
          title={t(
            {
              approve: 'Aprovar plano',
              note: 'Registrar nota',
              save: 'Salvar cenário',
              replace: 'Substituir o cenário salvo?',
              base: 'Nova base declarada',
              job: 'Executando o ciclo de decisão',
            }[modal],
          )}
          onClose={() => setModal(null)}
        >
          {error && (
            <div className="error" role="alert">
              {error.message}
            </div>
          )}
          {modal === 'approve' && (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                act(async () => {
                  const result = await api('/api/aprovar', {
                    regiao: data.meta.regiao,
                    periodo: data.meta.periodo,
                    autor: author,
                    sample,
                  });
                  setModal(null);
                  setNotice(result.mensagens.join(' '));
                  await loadPlan(`/api/plano/${enc(data.meta.regiao)}/${enc(data.meta.periodo)}`);
                });
              }}
            >
              <p>{t('A aprovação não resolve as escalações e não despacha equipes.')}</p>
              <label>
                {t('Nome do coordenador')}
                <input required value={author} onChange={(e) => setAuthor(e.target.value)} />
              </label>
              <button className="primary" disabled={busy || !author.trim()}>
                {t('Confirmar aprovação')}
              </button>
            </form>
          )}
          {modal === 'note' && (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                act(async () => {
                  await api('/api/nota', { regiao: region, periodo: period, autor: author, texto: note, sample });
                  setModal(null);
                  setNote('');
                  setNotice(t('Nota registrada para a próxima execução.'));
                });
              }}
            >
              <p>{t('Notas valem a partir da próxima execução.')}</p>
              <label>
                {t('Nome do coordenador')}
                <input required value={author} onChange={(e) => setAuthor(e.target.value)} />
              </label>
              <label>
                {t('Observação para os próximos períodos')}
                <textarea required rows="4" value={note} onChange={(e) => setNote(e.target.value)} />
              </label>
              <button className="primary" disabled={busy || !note.trim() || !author.trim()}>
                {t('Salvar nota')}
              </button>
            </form>
          )}
          {modal === 'save' && (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                saveScenario();
              }}
            >
              <label>
                {t('Nome do cenário')}
                <input
                  required
                  pattern="[A-Za-z0-9_-]{1,64}"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                />
              </label>
              <button className="primary" disabled={busy}>
                {t('Salvar')}
              </button>
            </form>
          )}
          {modal === 'replace' && (
            <>
              <p>{saveName}</p>
              <button className="primary" disabled={busy} onClick={() => saveScenario(true)}>
                {t('Sim, substituir')}
              </button>
            </>
          )}
          {modal === 'base' && (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                setScenario((s) => ({ ...s, bases: [...s.bases, newBase] }));
                setModal(null);
              }}
            >
              <p>
                {newBase.lat.toFixed(5)}, {newBase.lon.toFixed(5)}
              </p>
              <label>
                {t('Nome da base')}
                <input
                  required
                  value={newBase.nome}
                  onChange={(e) => setNewBase((b) => ({ ...b, nome: e.target.value }))}
                />
              </label>
              <label>
                {t('Procedência da informação')}
                <input value={newBase.fonte} onChange={(e) => setNewBase((b) => ({ ...b, fonte: e.target.value }))} />
              </label>
              {!dentroDaRegiao(newBase, regionCfg?.bbox) && (
                <p className="field-error">{t('Fora da região (bbox + 1°): a API vai recusar esta base.')}</p>
              )}
              {(() => {
                const m = baseMaisProxima(newBase, bases);
                return m && m.km < 3 ? (
                  <p className="field-error">
                    {t('A menos de 3 km de')} {m.base.nome} ({m.km.toFixed(1)} km):{' '}
                    {t('as duas serão fundidas e a declarada prevalece.')}
                  </p>
                ) : (
                  <p className="fine-print">
                    {t('Bases a menos de 3 km são fundidas; a declarada prevalece.')}
                    {m && ` ${t('Base conhecida mais próxima')}: ${m.base.nome} (${m.km.toFixed(1)} km).`}
                  </p>
                );
              })()}
              <button className="primary" disabled={!newBase.nome.trim()}>
                {t('Adicionar base')}
              </button>
            </form>
          )}
          {modal === 'job' && (
            <div className="job-progress">
              <LoaderCircle size={32} className={busy ? 'spin' : ''} />
              <Badge>{t(job?.status)}</Badge>
              <p aria-live="polite">{job?.progresso?.at(-1)?.msg || t('Aguardando progresso…')}</p>
              <pre>{job?.progresso?.map((p) => p.msg).join('\n')}</pre>
            </div>
          )}
        </Modal>
      )}
      {busy && job && !modal && (
        <button className="job-floating" onClick={() => setModal('job')}>
          <LoaderCircle size={18} className="spin" />
          {t('Executando o ciclo de decisão')}
        </button>
      )}
    </div>
  );
}

function Occurrence({ o, t, locale }) {
  return (
    <div className="occurrence-content">
      <div className="occurrence-meta">
        <code>{o.id}</code>
        <Badge>{t(o.status || 'Sem par anterior')}</Badge>
        <span>
          {t('Vento')}: {num(o.vento_kmh, locale)} km/h
        </span>
        <span>FRP: {num(o.frp_soma, locale)} MW</span>
      </div>
      <h4>
        {t('Índice de prioridade')} · {num(o.prioridade, locale)}
      </h4>
      <div className="components">
        {Object.entries(o.componentes || {}).map(([k, v]) => (
          <div key={k}>
            <span>
              {t(
                {
                  exposicao: 'Exposição',
                  intensidade: 'Intensidade',
                  tempo: 'Clima',
                  persistencia: 'Persistência',
                  crescimento: 'Crescimento',
                }[k] || k,
              )}
            </span>
            <div>
              <i style={{ width: `${Math.min(100, Math.max(0, v * 100))}%` }} />
            </div>
            <b>{num(v, locale)}</b>
          </div>
        ))}
      </div>
      <p className="fine-print">
        {t('até')} {num(o.pop_raio, locale)} {t('habitantes no raio')}.{' '}
        {t('População municipal no raio; não representa pessoas diretamente em risco.')}
      </p>
    </div>
  );
}
