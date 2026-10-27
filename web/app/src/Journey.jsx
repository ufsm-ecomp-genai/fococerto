import { rotuloCenario } from './lib.js';
import { ArrowRight, Check, Layers, MapPin, Plus, ShieldCheck, Truck, ArrowLeft, LoaderCircle } from 'lucide-react';

export function Steps({ step, onStep, busy, t }) {
  const steps = [
    ['Definir o cenário', 'Escolha como começar'],
    ['Organizar equipes', 'Bases e disponibilidade'],
    ['Revisar e gerar', 'Reserva, notas e execução'],
  ];
  return (
    <nav className="journey-steps" aria-label={t('Etapas do planejamento')}>
      {steps.map(([title, description], i) => (
        <button
          key={title}
          disabled={busy}
          onClick={() => onStep(i)}
          className={i === step ? 'current' : i < step ? 'complete' : ''}
          aria-current={i === step ? 'step' : undefined}
        >
          <span className="step-number">{i < step ? <Check size={17} /> : String(i + 1).padStart(2, '0')}</span>
          <span>
            <strong>{t(title)}</strong>
            <small>{t(description)}</small>
          </span>
        </button>
      ))}
    </nav>
  );
}

export function ScenarioStart({ scenarios, region, onLoad, onBlank, busy, t }) {
  const options = scenarios.filter((s, i, all) => s.regiao === region && all.findIndex((x) => x.nome === s.nome) === i);
  return (
    <section className="scenario-start">
      <div className="section-intro">
        <span className="section-kicker">01 / {t('PONTO DE PARTIDA')}</span>
        <h2>{t('Uma boa decisão começa com o cenário certo.')}</h2>
        <p>{t('Use um cenário existente ou informe os recursos disponíveis para esta operação.')}</p>
      </div>
      <div className="scenario-cards">
        <button className="scenario-card blank" disabled={busy} onClick={onBlank}>
          <span className="scenario-icon">
            <Plus size={25} />
          </span>
          <h3>{t('Montar minha operação')}</h3>
          <p>{t('Comece do zero, declare suas bases e adicione as equipes do dia.')}</p>
          <span className="scenario-link">
            {t('Começar em branco')}
            <ArrowRight size={17} />
          </span>
        </button>
        {options.map((s) => (
          <button className="scenario-card" key={s.nome} disabled={busy} onClick={() => onLoad(s.nome)}>
            <div className="scenario-card-top">
              <span className="scenario-icon">
                <Layers size={23} />
              </span>
              <span className={`source-tag ${s.simulado ? 'demo' : ''}`}>
                {t(s.simulado ? 'Simulado' : 'Disponibilidade real')}
              </span>
            </div>
            <h3>{t(rotuloCenario(s.nome))}</h3>
            <div className="scenario-facts">
              <span>
                <Truck size={14} />
                {s.recursos} {t('recursos')}
              </span>
              <span>
                <ShieldCheck size={14} />
                {s.reserva} {t('em reserva')}
              </span>
            </div>
            <p>
              {s.periodo} · {t(s.origem === 'salvo' ? 'Cenário salvo' : 'Cenário do repositório')}
            </p>
            <span className="scenario-link">
              {t('Usar este cenário')}
              <ArrowRight size={17} />
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

export function ReviewSummary({ scenario, period, region, t }) {
  const active = scenario.recursos.filter((r) => r.disponivel);
  return (
    <section className="review-summary">
      <span className="section-kicker">03 / {t('ANTES DE GERAR')}</span>
      <h2>{t('Tudo pronto para planejar?')}</h2>
      <p>
        {t(
          'Confira os recursos e ajuste as condições da operação. Os agentes vão propor uma alocação para sua revisão.',
        )}
      </p>
      <div className="review-location">
        <MapPin size={18} />
        <strong>{region}</strong>
        <span>{period || '—'}</span>
      </div>
      <div className="review-numbers">
        <div>
          <strong>{active.filter((r) => r.tipo === 'terrestre').length}</strong>
          <span>{t('Equipes terrestres')}</span>
        </div>
        <div>
          <strong>{active.filter((r) => r.tipo === 'aereo').length}</strong>
          <span>{t('Aeronaves disponíveis')}</span>
        </div>
        <div>
          <strong>{scenario.recursos.length - active.length}</strong>
          <span>{t('Fora de serviço')}</span>
        </div>
      </div>
      <div className="review-note">
        <ShieldCheck size={21} />
        <p>{t('Nenhuma equipe é despachada automaticamente. Você revisa as evidências e toma a decisão final.')}</p>
      </div>
    </section>
  );
}

export function JourneyActions({ step, onStep, count, busy, onGenerate, canGenerate, t }) {
  return (
    <div className="journey-actions">
      <div>
        <span className="action-dot" />
        <span>
          <strong>{count}</strong> {t('recursos informados')}
        </span>
      </div>
      <div>
        {step > 0 && (
          <button className="secondary" disabled={busy} onClick={() => onStep(step - 1)}>
            <ArrowLeft size={16} />
            {t('Voltar')}
          </button>
        )}
        {step === 1 && (
          <button className="primary" disabled={busy || !count} onClick={() => onStep(2)}>
            {t('Revisar operação')}
            <ArrowRight size={17} />
          </button>
        )}
        {step === 2 && (
          <button className="primary" disabled={busy || !canGenerate} onClick={onGenerate}>
            {busy ? <LoaderCircle className="spin" size={16} /> : <Layers size={16} />} {t('Gerar plano')}
          </button>
        )}
      </div>
    </div>
  );
}

export function Coverage({ data, t }) {
  const count = new Set(data.plano.designacoes.map((a) => a.ocorrencia_id)).size;
  const total = data.ocorrencias.length;
  return (
    <div className="coverage">
      <div className="coverage-top">
        <span>{t('Cobertura proposta')}</span>
        <strong>
          {count}
          <small> / {total}</small>
        </strong>
      </div>
      <div className="coverage-track">
        <span style={{ width: `${total ? (count / total) * 100 : 0}%` }} />
      </div>
      <p>{t('Ocorrências com recurso designado neste plano.')}</p>
    </div>
  );
}
