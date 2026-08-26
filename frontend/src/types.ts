export type RuntimeInfo = {
  mode: 'cloud' | 'desktop';
  compute_location: 'server' | 'local_device';
  storage_location: 'server' | 'local_device';
  provider_settings_mutable: boolean;
  durable_backend: 'sqlite' | 'postgresql';
};

export type SystemStatus = {
  status: 'running' | 'stopped';
  pid?: number | null;
  runtime?: RuntimeInfo;
};

export type ResearchRun = {
  id: string;
  title: string;
  direction: string;
  status: string;
  stage: string;
  decision?: string | null;
  completed_stages?: string[];
  updated_at?: string;
  metrics?: Record<string, number | string | null>;
  error?: string | null;
};
