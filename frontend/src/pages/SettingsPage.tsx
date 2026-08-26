import { useEffect, useState } from 'react';
import { Plus, Save, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { api, apiError } from '../api/client';
import PageHeader from '../components/PageHeader';
import ProviderSettings from '../components/ProviderSettings';
import type { SystemStatus } from '../types';

export default function SettingsPage() {
  const { t } = useTranslation();
  const [config, setConfig] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [newDirection, setNewDirection] = useState('');
  const [system, setSystem] = useState<SystemStatus | null>(null);

  useEffect(() => {
    Promise.all([api.get('/config'), api.get('/system/status')])
      .then(([configResponse, systemResponse]) => { setConfig(configResponse.data); setSystem(systemResponse.data); })
      .catch((error) => setMessage(apiError(error)));
  }, []);
  const cloudManaged = system?.runtime?.mode === 'cloud';
  const update = (section, key, value) => setConfig((current) => ({ ...current, [section]: { ...current[section], [key]: value } }));
  const save = async () => {
    setBusy(true); setMessage('');
    try { const { data } = await api.put('/config', config); setConfig(data.config); setMessage(data.restarted ? t('settings.savedRestarted') : t('settings.saved')); }
    catch (error) { setMessage(apiError(error)); }
    finally { setBusy(false); }
  };
  const addDirection = () => {
    const value = newDirection.trim();
    if (!value || config.research_directions.includes(value)) return;
    setConfig({ ...config, research_directions: [...config.research_directions, value] });
    setNewDirection('');
  };

  if (!config) return <div className="p-20 text-center text-slate-500">{t('settings.loading')}</div>;
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader eyebrow={t('settings.eyebrow')} title={t('settings.title')} description={t('settings.description')} actions={<button disabled={busy || cloudManaged} onClick={save} className="action-primary"><Save size={16} />{cloudManaged ? t('settings.serverManaged') : busy ? t('settings.saving') : t('settings.save')}</button>} />
      {message && <p className="mb-5 rounded-xl border border-white/10 bg-white/5 p-3 text-sm">{message}</p>}
      <div className="space-y-5">
        {cloudManaged && <p className="notice-strip rounded-xl border px-4 py-3 text-sm leading-6">{t('settings.cloudManaged')}</p>}
        <ProviderSettings editable={!cloudManaged} />
        <fieldset disabled={cloudManaged} className="min-w-0 space-y-5 border-0 p-0 disabled:opacity-70">
        <Section title={t('settings.modelReview')}>
          <Field label={t('settings.generationProvider')}><ProviderSelect value={config.llm.provider} onChange={(value) => update('llm', 'provider', value)} /></Field>
          <Field label={t('settings.reviewProvider')}><ProviderSelect value={config.llm.reviewer_provider} onChange={(value) => update('llm', 'reviewer_provider', value)} /></Field>
          <Field label={t('settings.reviewModel')}><input className="input" value={config.llm.reviewer_model} onChange={(event) => update('llm', 'reviewer_model', event.target.value)} /></Field>
          <NumberField label={t('settings.hypothesisThreshold')} value={config.workflow.hypothesis_review_threshold} onChange={(value) => update('workflow', 'hypothesis_review_threshold', value)} step="0.1" />
        </Section>
        <Section title={t('settings.experimentDiscipline')}>
          <NumberField label={t('settings.timeout')} value={config.experiment.timeout_minutes} onChange={(value) => update('experiment', 'timeout_minutes', value)} />
          <NumberField label={t('settings.maxIterations')} value={config.experiment.max_iterations} onChange={(value) => update('experiment', 'max_iterations', value)} />
          <NumberField label={t('settings.minimumSuccessRate')} value={config.experiment.minimum_success_rate} onChange={(value) => update('experiment', 'minimum_success_rate', value)} step="0.05" />
          <NumberField label={t('settings.maximumCv')} value={config.experiment.maximum_coefficient_of_variation} onChange={(value) => update('experiment', 'maximum_coefficient_of_variation', value)} step="0.01" />
          <Field label={t('settings.trainSeeds')}><SeedInput value={config.experiment.train_seeds} onChange={(value) => update('experiment', 'train_seeds', value)} /></Field>
          <Field label={t('settings.validationSeeds')}><SeedInput value={config.experiment.validation_seeds} onChange={(value) => update('experiment', 'validation_seeds', value)} /></Field>
        </Section>
        <Section title={t('settings.securityApproval')}>
          <Toggle label={t('settings.humanReview')} value={config.workflow.human_review_before_execution} onChange={(value) => update('workflow', 'human_review_before_execution', value)} />
          <Toggle label={t('settings.allowNetwork')} value={config.security.allow_network} onChange={(value) => update('security', 'allow_network', value)} />
          <NumberField label={t('settings.maxMemory')} value={config.security.max_memory_mb} onChange={(value) => update('security', 'max_memory_mb', value)} />
          <NumberField label={t('settings.maxOutput')} value={config.security.max_output_kb} onChange={(value) => update('security', 'max_output_kb', value)} />
        </Section>
        <section className="panel">
          <h2 className="mb-4 text-lg font-bold">{t('settings.directions')}</h2>
          <div className="mb-4 flex flex-wrap gap-2">{config.research_directions.map((item) => <span key={item} className="flex items-center gap-2 rounded-full bg-white/5 px-3 py-2 text-xs">{item}<button aria-label={t('settings.removeDirection', { direction: item })} title={t('settings.removeDirection', { direction: item })} onClick={() => setConfig({ ...config, research_directions: config.research_directions.filter((value) => value !== item) })}><X size={13} /></button></span>)}</div>
          <div className="flex gap-2"><input className="input flex-1" value={newDirection} onChange={(event) => setNewDirection(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && (event.preventDefault(), addDirection())} placeholder={t('settings.addDirection')} /><button onClick={addDirection} className="action-secondary"><Plus size={15} />{t('settings.add')}</button></div>
        </section>
        </fieldset>
      </div>
    </div>
  );
}

function Section({ title, children }) { return <section className="panel"><h2 className="mb-5 text-lg font-bold">{title}</h2><div className="grid gap-5 md:grid-cols-2">{children}</div></section>; }
function Field({ label, children }) { return <label className="space-y-2 text-xs font-bold text-slate-400"><span>{label}</span>{children}</label>; }
function NumberField({ label, value, onChange, step = '1' }) { return <Field label={label}><input type="number" step={step} className="input" value={value} onChange={(event) => onChange(Number(event.target.value))} /></Field>; }
function ProviderSelect({ value, onChange }) { const { t } = useTranslation(); return <select className="input" value={value} onChange={(event) => onChange(event.target.value)}><option value="openai">{t('settings.openaiCompatible')}</option><option value="anthropic">{t('settings.anthropicClaude')}</option><option value="google">{t('settings.googleGemini')}</option></select>; }
function SeedInput({ value, onChange }) { const [text, setText] = useState(value.join(', ')); return <input className="input" value={text} onChange={(event) => setText(event.target.value)} onBlur={() => { const seeds = text.split(',').map(Number).filter(Number.isInteger); onChange(seeds); setText(seeds.join(', ')); }} />; }
function Toggle({ label, value, onChange }) { return <label className="flex items-center justify-between rounded-xl bg-black/20 p-4 text-sm font-semibold"><span>{label}</span><input type="checkbox" checked={value} onChange={(event) => onChange(event.target.checked)} className="h-5 w-5 accent-cyan-300" /></label>; }
