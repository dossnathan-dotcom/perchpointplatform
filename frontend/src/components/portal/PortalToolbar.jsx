import { useState } from 'react';
import { Bell, Menu, Search, UserRound } from 'lucide-react';
import { PORTFOLIO, ROLE_ACCOUNTS } from '@/data/siteData';

export const PortalToolbar = ({ role, onRoleChange, onMenu, search, onSearch, context, onContext, onLogout }) => {
  const [panel, setPanel] = useState(null);
  const narrow = ['subcontractor','maintenance','resident','applicant'].includes(role.id);
  return <header className="relative border-b border-white/20 bg-obsidian p-4 sm:px-7" data-testid="portal-toolbar">
    <div className="flex flex-wrap items-center gap-3"><button aria-label="Open workspace navigation" className="portal-icon lg:hidden" onClick={onMenu} data-testid="portal-open-mobile-nav-btn"><Menu size={18} /></button>
      <label className="relative min-w-[140px] flex-1"><span className="sr-only">Search current workspace</span><Search className="absolute left-3 top-3 h-4 w-4 text-linen/75" /><input className="h-11 w-full border border-white/40 bg-white/5 pl-10 pr-3 text-sm text-linen placeholder:text-linen/75" placeholder="Search workspace…" value={search} onChange={(e) => onSearch(e.target.value)} data-testid="portal-global-search" /></label>
      <button className="portal-icon" aria-label="Notifications" aria-expanded={panel==='notifications'} onClick={() => setPanel(panel==='notifications'?null:'notifications')} data-testid="portal-notifications-btn"><Bell size={18} /></button>
      <button className="portal-icon" aria-label="Account menu" aria-expanded={panel==='account'} onClick={() => setPanel(panel==='account'?null:'account')} data-testid="portal-account-menu-btn"><UserRound size={18} /></button>
    </div>
    <div className="mt-3 flex flex-wrap items-center gap-3"><label className="grid min-w-0 flex-1 gap-1 text-xs text-linen/75">Organization / property context<select className="h-10 w-full max-w-full border border-white/40 bg-obsidian px-2 text-linen" value={narrow ? PORTFOLIO.properties[0].id : context} disabled={narrow} onChange={(e) => onContext(e.target.value)} data-testid="portal-context-select">{!narrow && <option value="all">HawkVision Homes · Demonstration portfolio</option>}{(narrow?PORTFOLIO.properties.slice(0,1):PORTFOLIO.properties).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      <label className="grid min-w-0 flex-1 gap-1 text-xs text-linen/75">Preview role<select className="h-10 w-full border border-white/40 bg-obsidian px-2 text-linen" value={role.id} onChange={(e) => onRoleChange(e.target.value)} data-testid="portal-role-switcher">{ROLE_ACCOUNTS.map((r) => <option key={r.id} value={r.id}>{r.role}</option>)}</select></label>
    </div>
    {panel && <div className="absolute right-4 top-16 z-40 w-[min(340px,calc(100%-2rem))] border border-white/40 bg-obsidian p-5 shadow-2xl" data-testid={`portal-${panel}-panel`}>
      <h2 className="font-heading text-xl">{panel==='notifications'?'Notifications':role.name}</h2><p className="mt-3 text-sm leading-6 text-linen/75">{panel==='notifications'?'No live notifications. Provider connections are disabled; all queues are synthetic.':'Role preview only. No authenticated session or account was created.'}</p><button className="mt-4 min-h-10 text-sm text-gold underline" onClick={panel==='account'?onLogout:()=>setPanel(null)} data-testid="portal-panel-action">{panel==='account'?'Leave preview':'Close notifications'}</button>
    </div>}
  </header>;
};