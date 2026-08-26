import { Check, Clock3, RotateCcw, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { ResearchRun } from '../types';
import StatusBadge from './StatusBadge';

const stages = ['literature', 'ideation', 'planning', 'baseline', 'experiment', 'validation', 'writing'];
const metric = (value: unknown) => (typeof value === 'number' ? value.toFixed(5) : '—');

type RunCardProps = {
  run: ResearchRun;
  busy: boolean;
  prominent?: boolean;
  onApprove: (id: string) => void;
  onResume: (id: string) => void;
  onCancel: (id: string) => void;
};

export default function RunCard({ run, busy, prominent = false, onApprove, onResume, onCancel }: RunCardProps) {
  const { t, i18n } = useTranslation();
  const canCancel = ['queued', 'running', 'waiting_review', 'failed'].includes(run.status);
  const updated = run.updated_at
    ? new Intl.DateTimeFormat(i18n.language, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(run.updated_at))
    : '—';

  return (
    <article className={`research-dossier ${prominent ? 'research-dossier-priority' : ''}`}>
      <div className="dossier-header flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <StatusBadge value={run.status} />
            {run.decision && <StatusBadge value={run.decision} />}
            <span className="inline-flex items-center gap-1 text-[11px] text-slate-500"><Clock3 size={12} />{updated}</span>
          </div>
          <h3 className="dossier-title text-xl font-black leading-8 md:text-2xl">
            {run.title === '离线验证演示' ? t('run.offlineDemo') : run.title}
          </h3>
          <p className="mt-2 text-xs leading-5 text-slate-500">{run.direction}</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {run.status === 'waiting_review' && (
            <button disabled={busy} onClick={() => onApprove(run.id)} className="action-primary">
              <Check size={16} />{t('run.approve')}
            </button>
          )}
          {run.status === 'failed' && (
            <button disabled={busy} onClick={() => onResume(run.id)} className="action-secondary">
              <RotateCcw size={15} />{t('run.resume')}
            </button>
          )}
          {canCancel && (
            <button disabled={busy} onClick={() => onCancel(run.id)} className="action-danger" aria-label={t('run.cancel')} title={t('run.cancel')}>
              <X size={15} />
            </button>
          )}
        </div>
      </div>

      <ResearchSpine current={run.stage} completed={run.completed_stages || []} />

      <div className="metric-ledger grid grid-cols-2 border-t md:grid-cols-4">
        <Metric label={t('run.baselineMean')} value={metric(run.metrics?.baseline_mean)} />
        <Metric label={t('run.candidateMean')} value={metric(run.metrics?.candidate_mean)} />
        <Metric label={t('run.improvement')} value={metric(run.metrics?.improvement)} />
        <Metric label={t('run.successRate')} value={typeof run.metrics?.success_rate === 'number' ? `${(run.metrics.success_rate * 100).toFixed(0)}%` : '—'} />
      </div>
      {run.error && <p className="run-error mt-4 rounded-lg border px-3 py-2 text-xs leading-5">{run.error}</p>}
    </article>
  );
}

function ResearchSpine({ current, completed }: { current: string; completed: string[] }) {
  const { t } = useTranslation();
  return (
    <div className="research-spine my-6 overflow-x-auto pb-2" aria-label={t('run.progress')}>
      <ol className="grid min-w-[700px] grid-cols-7">
        {stages.map((stage) => {
          const state = completed.includes(stage) ? 'complete' : current === stage ? 'current' : 'future';
          return (
            <li key={stage} className={`spine-stage spine-stage-${state}`} aria-current={state === 'current' ? 'step' : undefined}>
              <span className="spine-dot" />
              <span className="mt-2 block text-[10px] font-bold tracking-wide">{t(`stage.${stage}`)}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-cell px-3 py-4 md:px-4">
      <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <p className="mt-1 font-mono text-sm font-bold">{value}</p>
    </div>
  );
}
