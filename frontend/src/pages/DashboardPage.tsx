import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { CircleAlert, FlaskConical, Pause, Play, ServerCog, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { api, apiError } from '../api/client';
import PageHeader from '../components/PageHeader';
import RunCard from '../components/RunCard';
import useRunStream from '../hooks/useRunStream';
import type { ResearchRun, SystemStatus } from '../types';

type DoctorCheck = { ok?: boolean; optional?: boolean };

export default function DashboardPage() {
  const { t } = useTranslation();
  const stream = useRunStream();
  const runs = stream.runs as ResearchRun[];
  const [system, setSystem] = useState<SystemStatus>({ status: 'stopped' });
  const [doctor, setDoctor] = useState<Record<string, DoctorCheck>>({});
  const [direction, setDirection] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const loadSystem = () => Promise.all([api.get('/system/status'), api.get('/system/doctor')])
    .then(([status, checks]) => { setSystem(status.data); setDoctor(checks.data); });

  useEffect(() => { loadSystem().catch((error) => setMessage(apiError(error))); }, []);

  const pending = useMemo(() => runs.filter((run) => run.status === 'waiting_review'), [runs]);
  const remaining = useMemo(() => runs.filter((run) => run.status !== 'waiting_review'), [runs]);
  const counts = useMemo(() => ({
    active: runs.filter((run) => ['queued', 'running', 'waiting_review'].includes(run.status)).length,
    accepted: runs.filter((run) => run.decision === 'accepted').length,
    failed: runs.filter((run) => run.status === 'failed' || run.decision === 'invalid').length,
  }), [runs]);

  const act = async (request: () => Promise<unknown>, success: string) => {
    setBusy(true); setMessage('');
    try { await request(); setMessage(success); await loadSystem(); }
    catch (error) { setMessage(apiError(error)); }
    finally { setBusy(false); }
  };

  const createResearch = (event: FormEvent) => {
    event.preventDefault();
    if (!direction.trim()) return;
    act(() => api.post('/research', { direction: direction.trim() }), t('dashboard.researchSubmitted'));
  };

  const runProps = {
    busy,
    onApprove: (id: string) => act(() => api.post(`/runs/${id}/approve`, { reviewer: system.runtime?.mode === 'desktop' ? 'desktop-user' : 'web-user' }), t('dashboard.approved')),
    onResume: (id: string) => act(() => api.post(`/runs/${id}/resume`), t('dashboard.resumeSubmitted')),
    onCancel: (id: string) => act(() => api.post(`/runs/${id}/cancel`), t('dashboard.cancelled')),
  };

  return (
    <div className="mx-auto max-w-[1320px]">
      <PageHeader
        eyebrow={t(`dashboard.eyebrow_${system.runtime?.mode || 'cloud'}`)}
        title={t('dashboard.title')}
        description={t('dashboard.description')}
        actions={(
          <div className="flex flex-wrap gap-2">
            <button disabled={busy || system.status === 'running'} onClick={() => act(() => api.post('/system/start'), t('dashboard.schedulerStarted'))} className="action-primary"><Play size={15} />{t('dashboard.start')}</button>
            <button disabled={busy || system.status !== 'running'} onClick={() => act(() => api.post('/system/stop'), t('dashboard.schedulerStopped'))} className="action-secondary"><Pause size={15} />{t('dashboard.stop')}</button>
          </div>
        )}
      />

      {(message || stream.error) && <div role="status" aria-live="polite" className="notice-strip mb-6 rounded-lg border px-4 py-3 text-sm">{message || stream.error}</div>}

      <section className="command-deck mb-8 grid overflow-hidden rounded-2xl border lg:grid-cols-[1.55fr_1fr]">
        <form onSubmit={createResearch} className="p-5 md:p-7">
          <div className="mb-4 flex items-start gap-3">
            <span className="command-icon"><Sparkles size={18} /></span>
            <div><h2 className="font-black">{t('dashboard.createDirection')}</h2><p className="mt-1 text-xs leading-5 text-slate-500">{t('dashboard.reviewHint')}</p></div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <label className="sr-only" htmlFor="research-direction">{t('dashboard.createDirection')}</label>
            <input id="research-direction" value={direction} onChange={(event) => setDirection(event.target.value)} placeholder={t('dashboard.directionPlaceholder')} className="input flex-1" />
            <button disabled={busy || !direction.trim()} className="action-primary justify-center"><FlaskConical size={16} />{t('dashboard.submit')}</button>
          </div>
        </form>

        <div className="runtime-ledger border-t p-5 lg:border-l lg:border-t-0 lg:p-7">
          <div className="mb-4 flex items-center gap-2 text-sm font-black"><ServerCog size={17} />{t('dashboard.runtimeLedger')}</div>
          <dl className="grid grid-cols-3 gap-4">
            <LedgerValue label={t('dashboard.active')} value={counts.active} />
            <LedgerValue label={t('dashboard.validated')} value={counts.accepted} />
            <LedgerValue label={t('dashboard.failed')} value={counts.failed} tone="danger" />
          </dl>
          <p className="mt-5 text-[11px] leading-5 text-slate-500">{t(`runtime.detail_${system.runtime?.mode || 'cloud'}`, { database: system.runtime?.durable_backend || '—' })}</p>
        </div>
      </section>

      {pending.length > 0 && (
        <section className="mb-10">
          <SectionHeading icon={CircleAlert} title={t('dashboard.actionRequired')} count={pending.length} urgent />
          <div className="space-y-4">{pending.map((run) => <RunCard key={run.id} run={run} prominent {...runProps} />)}</div>
        </section>
      )}

      <section>
        <SectionHeading icon={FlaskConical} title={t('dashboard.recentRuns')} count={remaining.length} />
        <div className="space-y-4">{remaining.map((run) => <RunCard key={run.id} run={run} {...runProps} />)}</div>
        {!runs.length && (
          <div className="empty-workbench rounded-2xl border px-6 py-16 text-center">
            <FlaskConical className="mx-auto mb-4 text-slate-400" size={28} strokeWidth={1.5} />
            <p className="text-sm font-bold">{t('dashboard.emptyTitle')}</p>
            <p className="mx-auto mt-2 max-w-xl text-xs leading-6 text-slate-500">{t('dashboard.empty')}</p>
          </div>
        )}
      </section>

      <details className="doctor-details mt-8 rounded-xl border px-4 py-3">
        <summary className="cursor-pointer text-xs font-bold">{t('dashboard.environment')}</summary>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(doctor).map(([key, value]) => (
            <div key={key} className="rounded-lg border px-3 py-2 text-xs">
              <span className="text-slate-500">{key}</span>
              <p className={value?.ok ? 'text-emerald-600' : value?.optional ? 'text-amber-600' : 'text-rose-600'}>{value?.ok ? t('dashboard.healthy') : value?.optional ? t('dashboard.optionalMissing') : t('dashboard.needsAttention')}</p>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}

function LedgerValue({ label, value, tone }: { label: string; value: number; tone?: 'danger' }) {
  return <div><dt className="text-[10px] leading-4 text-slate-500">{label}</dt><dd className={`mt-1 font-mono text-2xl font-bold ${tone === 'danger' ? 'text-rose-600' : ''}`}>{value}</dd></div>;
}

function SectionHeading({ icon: Icon, title, count, urgent = false }: { icon: typeof FlaskConical; title: string; count: number; urgent?: boolean }) {
  return <div className="mb-4 flex items-center gap-2"><Icon size={17} className={urgent ? 'text-amber-600' : 'text-emerald-700'} /><h2 className="section-title text-lg font-black">{title}</h2><span className="count-mark rounded-full px-2 py-0.5 text-[10px] font-bold">{count}</span></div>;
}
