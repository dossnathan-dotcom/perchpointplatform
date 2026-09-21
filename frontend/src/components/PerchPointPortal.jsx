import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, Building2, FileLock2, GitBranch, X } from 'lucide-react';
import { ROLE_ACCOUNTS, slug } from '@/data/siteData';
import { PORTAL_VIEWS, previewRecords } from '@/data/portalData';
import { PHASE0 } from '@/config/phase0';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { DelegationPolicyModal } from './DelegationPolicyModal';
import { DemoNotice } from './DemoNotice';
import { PortalToolbar } from './portal/PortalToolbar';
import { PreviewState } from './portal/PreviewState';

export const PerchPointPortal = () => {
  const { roleId, viewId } = useParams();
  const navigate = useNavigate();
  const role = ROLE_ACCOUNTS.find((r) => r.id === roleId);
  const view = role && PORTAL_VIEWS[role.id];
  const tab = view?.tabs.find((t) => slug(t) === viewId) || view?.tabs[0];
  const [search,setSearch] = useState('');
  const [context,setContext] = useState('all');
  const [state,setState] = useState('seeded');
  const [menu,setMenu] = useState(false);
  const [policy,setPolicy] = useState(false);
  const [selected,setSelected] = useState(null);
  useEffect(() => {setSearch('');setContext('all');setState('seeded');setSelected(null);setMenu(false);},[roleId,viewId]);
  if (!role || !PHASE0.seedsEnabled) return <main className="min-h-screen bg-obsidian px-6 py-24 text-linen" data-testid="workspace-unavailable"><h1 className="font-heading text-4xl">Workspace preview unavailable</h1><Link className="mt-6 block underline" to="/" data-testid="workspace-unavailable-home">Return to HawkVision</Link></main>;
  const records = previewRecords(role.id,tab).filter((r) => (context==='all'||r.propertyId===context) && `${r.title} ${r.detail} ${r.status}`.toLowerCase().includes(search.toLowerCase()));
  return <main className="min-h-screen bg-[#090d12] text-linen" data-testid="perchpoint-portal-page"><div className="flex min-h-screen">
    {menu && <button className="fixed inset-0 z-40 bg-black/70 lg:hidden" aria-label="Close workspace navigation" onClick={() => setMenu(false)} data-testid="portal-nav-backdrop" />}
    <aside className={`${menu?'fixed inset-y-0 left-0 z-50 flex':'hidden'} w-[min(280px,90vw)] shrink-0 flex-col border-r border-white/20 bg-obsidian p-5 lg:sticky lg:top-0 lg:flex lg:h-screen`} data-testid="perchpoint-sidebar"><div className="flex items-start justify-between gap-2"><Link className="flex items-center gap-3" to="/" data-testid="portal-brand-home-btn"><Building2 className="h-7 w-7 text-gold" /><span className="font-heading text-2xl font-bold">PerchPoint</span></Link><button className="portal-icon lg:hidden" aria-label="Close navigation" onClick={() => setMenu(false)} data-testid="portal-close-mobile-nav-btn"><X size={18} /></button></div><p className="mt-3 text-xs leading-5 text-linen/75">HawkVision Homes Property Operations</p><p className="mb-3 mt-8 text-xs font-semibold text-gold" data-testid="portal-workspace-label">{view.label}</p>
      <nav className="grid gap-1 overflow-y-auto" aria-label="Workspace" data-testid="portal-workspace-navigation">{view.tabs.map((t,i) => <Link key={t} to={`/perchpoint/${role.id}/${slug(t)}`} aria-current={t===tab?'page':undefined} className={`border-l-2 px-3 py-3 text-sm transition-colors ${t===tab?'border-gold bg-white/10 text-white':'border-transparent text-linen/75 hover:bg-white/5'}`} data-testid={`portal-tab-${role.id}-${i}`}>{t}</Link>)}</nav>
      <div className="mt-auto grid gap-2 border-t border-white/20 pt-5">{['owner','super-admin'].includes(role.id) && <button className="flex min-h-11 items-center gap-2 text-left text-sm text-gold" onClick={() => setPolicy(true)} data-testid="delegation-policy-trigger-btn"><GitBranch size={16} />Delegation policy</button>}<Link className="flex min-h-11 items-center gap-2 text-sm text-linen/75" to="/foundation" data-testid="portal-foundation-link"><FileLock2 size={16} />Foundation contracts</Link><Link className="flex min-h-11 items-center gap-2 text-sm text-linen/75" to="/" data-testid="portal-logout-btn"><ArrowLeft size={16} />Leave preview</Link></div>
    </aside>
    <section className="min-w-0 flex-1"><PortalToolbar role={role} onRoleChange={(id) => navigate(`/perchpoint/${id}`)} onMenu={() => setMenu(true)} search={search} onSearch={setSearch} context={context} onContext={setContext} onLogout={() => navigate('/')} />
      <div className="mx-auto max-w-[1400px] p-5 sm:p-8"><DemoNotice id="portal-demo-notice" className="text-xs text-gold">Seeded workspace · no production authentication or live operations</DemoNotice><div className="mt-5 flex flex-wrap items-end justify-between gap-5"><div><p className="text-sm text-linen/75" data-testid="portal-role-label">{role.role}</p><h1 className="mt-3 font-heading text-4xl font-bold sm:text-5xl" data-testid="portal-active-page-title">{tab}</h1></div><label className="grid gap-2 text-xs text-linen/75">State preview<select className="h-10 border border-white/40 bg-obsidian px-3 text-linen" value={state} onChange={(e) => setState(e.target.value)} data-testid="portal-state-select">{['seeded','empty','loading','error','denied'].map((s) => <option key={s} value={s}>{s}</option>)}</select></label></div><p className="mt-5 max-w-3xl text-sm leading-7 text-linen/75" data-testid="portal-role-scope">{role.scope}</p>
        <div className="my-7 flex flex-wrap gap-6 border-y border-white/20 py-4 text-xs"><span data-testid="portal-record-count">{records.length} synthetic {records.length===1?'record':'records'}</span><span data-testid="portal-provider-status" className="text-gold">Providers disconnected</span><span data-testid="portal-security-status" className="text-linen/75">Permissions: contract simulation only</span></div>
        {state!=='seeded' || records.length===0 ? <PreviewState state={state==='seeded'?'empty':state} onReset={() => {setState('seeded');setSearch('');setContext('all');}} /> : <div className={role.id==='leasing'&&tab==='Operations Console'?'grid gap-x-8 md:grid-cols-2':'divide-y divide-white/20'} data-testid="portal-work-queue">{records.map((r,i) => <button key={r.id} className="group flex w-full items-start justify-between gap-4 border-b border-white/20 py-5 text-left transition-colors hover:bg-white/5" onClick={() => setSelected(r)} data-testid={`portal-task-${i}`}><span><span className="block text-sm font-semibold">{r.title}</span><span className="mt-2 block text-sm leading-6 text-linen/75">{r.detail}</span><span className="mt-3 block text-xs text-gold" data-testid={`portal-task-status-${i}`}>{r.status}</span></span><ArrowUpRight className="mt-1 h-4 w-4 shrink-0 text-linen/75 group-hover:text-gold" /></button>)}</div>}
        <div className="mt-10 border-l-2 border-copper pl-5" data-testid="portal-access-boundary-card"><h2 className="font-heading text-lg">Access is a relationship, not just a role.</h2><p className="mt-3 max-w-3xl text-sm leading-7 text-linen/75">Organization, property, assignment, household, sensitivity, action and current status must all be evaluated by the future server. This preview does not protect production records.</p></div>
      </div>
    </section>
  </div><DelegationPolicyModal open={policy} onOpenChange={setPolicy} /><Dialog open={!!selected} onOpenChange={(open) => {if(!open)setSelected(null);}}><DialogContent className="border-white/30 bg-obsidian text-linen" data-testid="portal-record-dialog"><DialogHeader><DialogTitle className="font-heading text-2xl">{selected?.title}</DialogTitle><DialogDescription className="text-linen/75">{selected?.detail}</DialogDescription></DialogHeader><p className="text-sm text-gold" data-testid="portal-record-disclosure">Synthetic preview only. No real workflow is started.</p><Button disabled className="bg-white/10 text-linen" data-testid="portal-record-planned-action">Workflow planned · unavailable in Phase 0</Button></DialogContent></Dialog></main>;
};