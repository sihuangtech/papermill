import {
  Cloud,
  FileText,
  FlaskConical,
  HardDrive,
  LayoutDashboard,
  ScrollText,
  Settings,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import { FaGithub } from 'react-icons/fa6';
import { SiBilibili, SiXiaohongshu } from 'react-icons/si';
import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router-dom';
import { api } from '../api/client';
import type { RuntimeInfo } from '../types';
import LanguageSwitcher from './LanguageSwitcher';
import ThemeSwitcher from './ThemeSwitcher';

type AppShellProps = { children: ReactNode };
type NavigationItem = { to: string; label: string; icon: LucideIcon };

const GITHUB_REPOSITORY = 'https://github.com/sihuangtech/sk-agentic-research';
const BILIBILI_URL = 'https://space.bilibili.com/3546644962347701';
const XIAOHONGSHU_URL = 'https://www.xiaohongshu.com/user/profile/6825745a000000000e01ee38';

export default function AppShell({ children }: AppShellProps) {
  const { t } = useTranslation();
  const [runtime, setRuntime] = useState<RuntimeInfo | null>(null);
  const links: NavigationItem[] = [
    { to: '/', label: t('nav.dashboard'), icon: LayoutDashboard },
    { to: '/ideas', label: t('nav.ideas'), icon: FlaskConical },
    { to: '/papers', label: t('nav.papers'), icon: FileText },
    { to: '/logs', label: t('nav.logs'), icon: ScrollText },
    { to: '/settings', label: t('nav.settings'), icon: Settings },
  ];

  useEffect(() => {
    api.get('/system/status').then(({ data }) => setRuntime(data.runtime || null)).catch(() => { });
  }, []);

  return (
    <div className="app-shell min-h-screen">
      <aside className="app-sidebar fixed inset-y-0 left-0 z-30 hidden w-60 border-r px-5 py-6 lg:flex lg:flex-col">
        <div className="brand-lockup flex items-center gap-3 px-2">
          <img src="/brand/app-icon.png" alt="" className="h-10 w-10 rounded-[13px]" />
          <div>
            <p className="brand-name text-xl font-black tracking-tight">{t('app.displayName')}</p>
            <p className="text-[9px] font-bold uppercase tracking-[0.22em] text-slate-500">Agentic Research</p>
          </div>
        </div>

        <nav className="mt-10 space-y-1" aria-label={t('app.primaryNavigation')}>
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-item ${isActive ? 'nav-item-active' : ''}`}
            >
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto space-y-3">
          <RuntimeStamp runtime={runtime} />
          <div className="grid grid-cols-2 gap-2">
            <ThemeSwitcher compact />
            <LanguageSwitcher compact />
          </div>
          <p className="px-2 text-[11px] leading-5 text-slate-500">
            {runtime?.mode === 'desktop' ? t('app.safetyDesktop') : t('app.safetyCloud')}
          </p>
          <SocialLinks />
        </div>
      </aside>

      <header className="app-mobilebar sticky top-0 z-30 flex items-center justify-between border-b px-4 py-3 lg:hidden">
        <div className="flex items-center gap-2">
          <img src="/brand/app-icon.png" alt="" className="h-8 w-8 rounded-[10px]" />
          <span className="brand-name font-black">{t('app.displayName')}</span>
        </div>
        <div className="flex gap-2"><ThemeSwitcher compact /><LanguageSwitcher compact /></div>
      </header>

      <main className="app-main min-h-screen px-4 pb-28 pt-6 md:px-8 lg:ml-60 lg:px-12 lg:pb-12 lg:pt-10">
        {children}
        <footer className="mt-10 flex justify-center lg:hidden">
          <SocialLinks />
        </footer>
      </main>

      <nav className="mobile-dock fixed inset-x-3 bottom-3 z-40 grid grid-cols-5 rounded-2xl border p-1.5 lg:hidden" aria-label={t('app.primaryNavigation')}>
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `mobile-nav ${isActive ? 'mobile-nav-active' : ''}`}>
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function SocialLinks() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-center gap-2">
      <a
        href={GITHUB_REPOSITORY}
        target="_blank"
        rel="noopener noreferrer"
        className="social-link"
        aria-label={t('app.githubRepositoryLabel')}
      >
        <FaGithub size={16} aria-hidden="true" />
      </a>
      <a
        href={BILIBILI_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="social-link"
        aria-label={t('app.bilibiliLabel')}
      >
        <SiBilibili size={16} aria-hidden="true" />
      </a>
      <a
        href={XIAOHONGSHU_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="social-link"
        aria-label={t('app.xiaohongshuLabel')}
      >
        <SiXiaohongshu size={16} aria-hidden="true" />
      </a>
    </div>
  );
}

function RuntimeStamp({ runtime }: { runtime: RuntimeInfo | null }) {
  const { t } = useTranslation();
  const Icon = runtime?.mode === 'desktop' ? HardDrive : Cloud;
  return (
    <div className="runtime-stamp flex items-start gap-3 rounded-xl border p-3">
      <Icon size={17} className="mt-0.5 shrink-0" />
      <div>
        <p className="text-xs font-bold">{t(`runtime.${runtime?.mode || 'detecting'}`)}</p>
        <p className="mt-1 text-[10px] leading-4 text-slate-500">
          {runtime ? t(`runtime.${runtime.compute_location}`) : t('runtime.detectingHint')}
        </p>
      </div>
    </div>
  );
}
