import { CheckCircle2, KeyRound, Save } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, apiError } from '../api/client';

export default function ProviderSettings({ editable = true }: { editable?: boolean }) {
  const { t } = useTranslation();
  const [providers, setProviders] = useState([]);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api.get('/providers')
      .then(({ data }) => setProviders(Array.isArray(data) ? data : []))
      .catch((error) => setMessage(apiError(error)));
  }, []);

  const updateProvider = (updated) => {
    setProviders((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  };

  return (
    <section className="panel">
      <div className="mb-5">
        <h2 className="text-lg font-bold">{t('providers.title')}</h2>
        <p className="mt-2 text-xs leading-5 text-slate-500">{editable ? t('providers.description') : t('providers.cloudManaged')}</p>
      </div>
      {message && <p className="mb-4 rounded-xl bg-rose-300/10 p-3 text-sm text-rose-200">{message}</p>}
      <div className="grid gap-4 lg:grid-cols-3">
        {providers.map((provider) => (
          <ProviderCard key={provider.id} provider={provider} onSaved={updateProvider} editable={editable} />
        ))}
      </div>
    </section>
  );
}

function ProviderCard({ provider, onSaved, editable }) {
  const { t } = useTranslation();
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState(provider.base_url || '');
  const [modelId, setModelId] = useState(provider.model_id || '');
  const [apiMode, setApiMode] = useState(provider.api_mode || '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  const save = async () => {
    setBusy(true); setMessage('');
    try {
      const { data } = await api.put(`/providers/${provider.id}`, {
        base_url: baseUrl || null,
        model_id: modelId || null,
        api_mode: provider.id === 'openai' ? apiMode : null,
        api_key: apiKey || null,
      });
      onSaved(data.provider); setApiKey('');
      setMessage(data.restarted ? t('providers.savedRestarted') : t('providers.saved'));
    } catch (error) { setMessage(apiError(error)); }
    finally { setBusy(false); }
  };

  return (
    <article className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-sm font-bold">{t(`providers.names.${provider.id}`, { defaultValue: provider.label })}</h3>
        <span className={provider.api_key_configured ? 'text-emerald-300' : 'text-slate-600'} title={provider.api_key_configured ? t('providers.keyConfigured') : t('providers.keyMissing')}>
          {provider.api_key_configured ? <CheckCircle2 size={17} /> : <KeyRound size={17} />}
        </span>
      </div>
      <label className="mb-3 block space-y-2 text-xs font-bold text-slate-400">
        <span>{t('providers.baseUrl')}</span>
        <input disabled={!editable} type="url" className="input" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://..." />
      </label>
      <label className="mb-3 block space-y-2 text-xs font-bold text-slate-400">
        <span>{t('providers.modelId')}</span>
        <input disabled={!editable} className="input" value={modelId} onChange={(event) => setModelId(event.target.value)} placeholder={t('providers.modelPlaceholder')} />
      </label>
      {provider.id === 'openai' && <label className="mb-3 block space-y-2 text-xs font-bold text-slate-400">
        <span>{t('providers.apiMode')}</span>
        <select disabled={!editable} className="input" value={apiMode} onChange={(event) => setApiMode(event.target.value)}>
          <option value="chat_completions">{t('providers.chatCompletions')}</option>
          <option value="responses">{t('providers.responses')}</option>
        </select>
        <span className="block font-normal leading-5 text-slate-600">{t('providers.apiModeHint')}</span>
      </label>}
      <label className="block space-y-2 text-xs font-bold text-slate-400">
        <span>{t('providers.apiKey')}</span>
        <input disabled={!editable} type="password" autoComplete="new-password" className="input" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={provider.api_key_configured ? t('providers.replaceKey') : t('providers.enterKey')} />
      </label>
      {message && <p className="mt-3 text-xs text-cyan-200">{message}</p>}
      <button disabled={busy || !editable} onClick={save} className="action-secondary mt-4 w-full justify-center"><Save size={14} />{editable ? busy ? t('providers.saving') : t('providers.save') : t('settings.serverManaged')}</button>
    </article>
  );
}
