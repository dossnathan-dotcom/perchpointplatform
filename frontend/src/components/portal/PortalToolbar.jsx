import { useEffect, useState } from 'react';
import { Bell, Menu, Search, Star, UserRound } from 'lucide-react';
import { PORTFOLIO, ROLE_ACCOUNTS } from '@/data/siteData';
import { NOTIFICATION_EXAMPLE } from '@/design-system/library';
import { DENSITIES, THEMES, applyDocumentTheme, readPreference, storePreference } from '@/design-system/theme';

const readIds = (key) => {
  try { return JSON.parse(localStorage.getItem(key) || '[]'); } catch { return []; }
};

export const PortalToolbar = ({ role, onRoleChange, onMenu, onCommands, search, onSearch, context, onContext, onLogout }) => {
  const [panel, setPanel] = useState(null);
  const [noticeState, setNoticeState] = useState('ready');
  const [theme, setTheme] = useState(() => readPreference("pp-theme", THEMES, "dark"));
  const [density, setDensity] = useState(() => readPreference("pp-density", DENSITIES, "comfortable"));
  const [recent, setRecent] = useState(() => readIds('pp-recent-contexts'));
  const [favorites, setFavorites] = useState(() => readIds('pp-favorite-contexts'));
  const narrow = ['subcontractor','maintenance','resident','applicant'].includes(role.id);
  useEffect(() => {
    if (!context || context === 'all') return;
    const next = [context, ...readIds('pp-recent-contexts').filter((id) => id !== context)].slice(0, 5);
    localStorage.setItem('pp-recent-contexts', JSON.stringify(next));
    setRecent(next);
  }, [context]);
  const propertyName = PORTFOLIO.properties.find((property) => property.id === context)?.name || 'All-portfolio scope';
  const toggleFavorite = () => {
    if (!context || context === 'all') return;
    const next = favorites.includes(context) ? favorites.filter((id) => id !== context) : [...favorites, context];
    localStorage.setItem('pp-favorite-contexts', JSON.stringify(next));
    setFavorites(next);
  };
  return <header className="relative border-b border-white/20 bg-obsidian p-4 sm:px-7" data-testid="portal-toolbar">
    <div className="flex flex-wrap items-center gap-3"><button aria-label="Open workspace navigation" className="portal-icon lg:hidden" onClick={onMenu} data-testid="portal-open-mobile-nav-btn"><Menu size={18} /></button>
      <label className="relative min-w-[140px] flex-1"><span className="sr-only">Search current workspace</span><Search className="absolute left-3 top-3 h-4 w-4 text-linen/75" /><input className="h-11 w-full border border-white/40 bg-white/5 pl-10 pr-3 text-sm text-linen placeholder:text-linen/75" placeholder="Filter this preview…" value={search} onChange={(e) => onSearch(e.target.value)} data-testid="portal-global-search" /></label>
      <button type="button" className="min-h-11 px-3 text-sm underline" onClick={onCommands} data-testid="portal-command-palette">Search</button>
      <button className="portal-icon" aria-label="Notifications" aria-expanded={panel==='notifications'} onClick={() => setPanel(panel==='notifications'?null:'notifications')} data-testid="portal-notifications-btn"><Bell size={18} /></button>
      <button className="portal-icon" aria-label="Account menu" aria-expanded={panel==='account'} onClick={() => setPanel(panel==='account'?null:'account')} data-testid="portal-account-menu-btn"><UserRound size={18} /></button>
    </div>
    <div className="mt-3 flex flex-wrap items-center gap-3"><label className="grid min-w-0 flex-1 gap-1 text-xs text-linen/75">Organization / property context<select className="h-10 w-full max-w-full border border-white/40 bg-obsidian px-2 text-linen" value={narrow ? PORTFOLIO.properties[0].id : context} disabled={narrow} onChange={(e) => onContext(e.target.value)} data-testid="portal-context-select">{!narrow && <option value="all">HawkVision Homes · Demonstration portfolio</option>}{(narrow?PORTFOLIO.properties.slice(0,1):PORTFOLIO.properties).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      <button type="button" className="min-h-11 px-2 text-sm underline" onClick={toggleFavorite} data-testid="portal-favorite-context"><Star size={14} /> Favorite</button>
      <label className="grid min-w-0 flex-1 gap-1 text-xs text-linen/75">Preview role<select className="h-10 w-full border border-white/40 bg-obsidian px-2 text-linen" value={role.id} onChange={(e) => onRoleChange(e.target.value)} data-testid="portal-role-switcher">{ROLE_ACCOUNTS.map((r) => <option key={r.id} value={r.id}>{r.role}</option>)}</select></label>
      <label className="grid gap-1 text-xs text-linen/75">Theme<select className="h-10 border border-white/40 bg-obsidian px-2 text-linen" value={theme} data-testid="portal-theme-select" onChange={(event) => { setTheme(event.target.value); storePreference("pp-theme", event.target.value, THEMES); applyDocumentTheme(window.location.pathname); }}>{THEMES.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
      <label className="grid gap-1 text-xs text-linen/75">Density<select className="h-10 border border-white/40 bg-obsidian px-2 text-linen" value={density} data-testid="portal-density-select" onChange={(event) => { setDensity(event.target.value); storePreference("pp-density", event.target.value, DENSITIES); applyDocumentTheme(window.location.pathname); }}>{DENSITIES.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
    </div>
    <p className="mt-3 text-xs text-linen/75" data-testid="portal-context-summary">Organization HawkVision Homes · Property {propertyName} · Role {role.role} · Environment local · Recent {recent.length} · Favorites {favorites.length}</p>
    {panel === 'notifications' && <div className="absolute right-4 top-16 z-40 w-[min(360px,calc(100%-2rem))] border border-white/40 bg-obsidian p-5 shadow-2xl" data-testid="portal-notifications-panel">
      <h2 className="font-heading text-xl">Notifications</h2>
      <label className="mt-3 block text-xs">Example state<select className="ml-2 h-10 border border-white/40 bg-obsidian" value={noticeState} onChange={(event) => setNoticeState(event.target.value)} data-testid="notification-state-select"><option value="ready">ready</option><option value="empty">empty</option><option value="loading">loading</option><option value="error">error</option><option value="denied">denied</option></select></label>
      {noticeState === 'ready' && <article className="mt-3 text-sm" data-testid="notification-example"><p>Category: {NOTIFICATION_EXAMPLE.category}</p><p>Priority: {NOTIFICATION_EXAMPLE.priority}</p><p>Read: {NOTIFICATION_EXAMPLE.read ? 'Read' : 'Unread'}</p><p>Record: {NOTIFICATION_EXAMPLE.record}</p><p>Time: <time dateTime={NOTIFICATION_EXAMPLE.timestamp}>{NOTIFICATION_EXAMPLE.timestamp}</time></p><p>Next action: {NOTIFICATION_EXAMPLE.action}</p><p>Source: {NOTIFICATION_EXAMPLE.source}</p></article>}
      {noticeState === 'empty' && <p role="status">No notices in this preview.</p>}
      {noticeState === 'loading' && <p role="status">Loading notices.</p>}
      {noticeState === 'error' && <p role="alert">Notices could not be loaded. Nothing was changed.</p>}
      {noticeState === 'denied' && <p role="status">This preview role cannot see that notice.</p>}
      <button className="mt-4 min-h-10 text-sm text-gold underline" onClick={() => setPanel(null)} data-testid="portal-panel-action">Close notifications</button>
    </div>}
    {panel === 'account' && <div className="absolute right-4 top-16 z-40 w-[min(340px,calc(100%-2rem))] border border-white/40 bg-obsidian p-5 shadow-2xl" data-testid="portal-account-panel">
      <h2 className="font-heading text-xl">{role.name}</h2><p className="mt-3 text-sm leading-6 text-linen/75">Role preview only. No authenticated session or account was created.</p><button className="mt-4 min-h-10 text-sm text-gold underline" onClick={onLogout} data-testid="portal-panel-action">Leave preview</button>
    </div>}
  </header>;
};