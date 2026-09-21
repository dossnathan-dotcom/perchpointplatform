import { useState } from "react";
import { ArrowLeft, Bell, Building2, ChevronRight, GitBranch, LogOut, Menu, Shield, X } from "lucide-react";
import { ROLE_ACCOUNTS, DEMO_NOTICE } from "@/data/siteData";
import { PORTAL_VIEWS } from "@/data/portalData";
import { Button } from "@/components/ui/button";
import { DelegationPolicyModal } from "@/components/DelegationPolicyModal";

const statusColor = (status) => status.includes("Emergency") ? "text-red-300 bg-red-500/10" : status.includes("Complete") || status.includes("Approved") ? "text-emerald-300 bg-emerald-500/10" : "text-gold bg-gold/10";

export const PerchPointPortal = ({ user, onRoleChange, onLogout, onReturn }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [policyOpen, setPolicyOpen] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const view = PORTAL_VIEWS[user.id];

  const changeRole = (event) => {
    const account = ROLE_ACCOUNTS.find((item) => item.id === event.target.value);
    setActiveTab(0);
    onRoleChange(account);
  };

  return (
    <main className="min-h-screen bg-[#090d12] text-linen" data-testid="perchpoint-portal-page">
      <div className="flex min-h-screen">
        <aside className={`${mobileNav ? "fixed inset-y-0 left-0 z-50 flex" : "hidden"} w-[280px] shrink-0 flex-col border-r border-white/10 bg-obsidian p-5 lg:sticky lg:top-0 lg:flex lg:h-screen`} data-testid="perchpoint-sidebar">
          <div className="flex items-start justify-between">
            <button onClick={onReturn} className="flex items-center gap-3 text-left" data-testid="portal-brand-home-btn"><span className="flex h-10 w-10 items-center justify-center bg-copper text-white"><Building2 className="h-5 w-5" /></span><span><span className="block font-heading text-xl font-bold">PerchPoint</span><span className="font-mono text-[8px] uppercase tracking-[0.17em] text-linen/45">HawkVision Property Operations</span></span></button>
            <button className="p-2 lg:hidden" onClick={() => setMobileNav(false)} data-testid="portal-close-mobile-nav-btn"><X className="h-5 w-5" /></button>
          </div>
          <div className="mt-10">
            <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-linen/35">Workspace</p>
            <p className="mt-2 text-sm font-bold">{view.label}</p>
          </div>
          <nav className="mt-7 grid gap-1" data-testid="portal-workspace-navigation">
            {view.tabs.map((tab, index) => <button key={tab} onClick={() => { setActiveTab(index); setMobileNav(false); }} className={`flex items-center justify-between px-3 py-3 text-left text-sm transition-colors ${activeTab === index ? "bg-copper text-white" : "text-linen/55 hover:bg-white/5 hover:text-linen"}`} data-testid={`portal-tab-${user.id}-${index}`}><span>{tab}</span><ChevronRight className="h-4 w-4" /></button>)}
          </nav>
          {(user.id === "owner" || user.id === "super-admin") && <button onClick={() => setPolicyOpen(true)} className="mt-6 flex items-center gap-3 border border-gold/20 bg-gold/10 px-4 py-3 text-left text-sm font-semibold text-gold" data-testid="delegation-policy-trigger-btn"><GitBranch className="h-4 w-4" /> View delegation matrix</button>}
          <div className="mt-auto border-t border-white/10 pt-5">
            <button onClick={onLogout} className="flex w-full items-center gap-3 px-3 py-3 text-sm text-linen/50 hover:text-linen" data-testid="portal-logout-btn"><LogOut className="h-4 w-4" /> Sign out of preview</button>
          </div>
        </aside>

        <section className="min-w-0 flex-1">
          <header className="sticky top-0 z-30 flex min-h-20 items-center justify-between gap-4 border-b border-white/10 bg-[#090d12]/95 px-5 backdrop-blur-xl sm:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <button className="p-2 lg:hidden" onClick={() => setMobileNav(true)} data-testid="portal-open-mobile-nav-btn"><Menu className="h-5 w-5" /></button>
              <div className="min-w-0"><p className="truncate font-heading text-xl font-bold sm:text-2xl">{view.tabs[activeTab]}</p><p className="truncate text-xs text-linen/40">{user.role}</p></div>
            </div>
            <div className="flex items-center gap-2">
              <button className="relative flex h-10 w-10 items-center justify-center border border-white/10 bg-white/[0.04]" aria-label="Notifications" data-testid="portal-notifications-btn"><Bell className="h-4 w-4" /><span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-copper" /></button>
              <select value={user.id} onChange={changeRole} className="h-10 max-w-[180px] border border-white/10 bg-white/[0.04] px-3 text-xs text-linen outline-none" data-testid="portal-role-switcher">
                {ROLE_ACCOUNTS.map((account) => <option key={account.id} value={account.id} className="bg-obsidian">{account.role}</option>)}
              </select>
            </div>
          </header>

          <div className="mx-auto max-w-[1500px] p-5 sm:p-8">
            <div className="flex flex-col justify-between gap-6 border-b border-white/10 pb-8 lg:flex-row lg:items-end">
              <div><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-gold" data-testid="portal-demo-notice">{DEMO_NOTICE}</p><h1 className="mt-4 font-heading text-4xl font-bold sm:text-5xl">Good morning, {user.name}.</h1><p className="mt-4 max-w-3xl leading-7 text-linen/55" data-testid="portal-role-scope">{user.scope}</p></div>
              <Button variant="outline" className="self-start border-white/15 bg-white/[0.04] text-linen hover:bg-white/10 hover:text-linen" onClick={onReturn} data-testid="portal-return-public-btn"><ArrowLeft className="h-4 w-4" /> Public site</Button>
            </div>

            <div className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {view.metrics.map(([label, value], index) => <article key={label} className="border border-white/10 bg-[#11161d] p-5" data-testid={`portal-metric-${index}`}><p className="font-mono text-[9px] uppercase tracking-[0.18em] text-linen/35">{label}</p><p className="mt-5 font-heading text-3xl font-bold">{value}</p><div className="mt-5 h-px bg-gradient-to-r from-copper to-transparent" /></article>)}
            </div>

            <div className="mt-8 grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
              <section className="border border-white/10 bg-[#11161d]" data-testid="portal-work-queue">
                <div className="flex items-center justify-between border-b border-white/10 px-5 py-4"><div><p className="font-heading text-xl font-bold">Active work</p><p className="mt-1 text-xs text-linen/40">Role-filtered operational queue</p></div><span className="font-mono text-[9px] uppercase tracking-[0.16em] text-linen/35">Seeded preview</span></div>
                <div>{view.tasks.map(([type, detail, status], index) => <button key={`${type}-${detail}`} className="grid w-full gap-3 border-b border-white/10 px-5 py-5 text-left transition-colors hover:bg-white/[0.03] sm:grid-cols-[0.7fr_1.6fr_auto] sm:items-center" data-testid={`portal-task-${index}`}><span className="text-sm font-bold">{type}</span><span className="text-sm text-linen/55">{detail}</span><span className={`w-fit px-2 py-1 text-xs ${statusColor(status)}`}>{status}</span></button>)}</div>
              </section>
              <aside className="border border-white/10 bg-[#11161d] p-6" data-testid="portal-access-boundary-card">
                <Shield className="h-5 w-5 text-gold" /><p className="mt-6 font-mono text-[10px] uppercase tracking-[0.18em] text-gold">Access boundary</p><h2 className="mt-3 font-heading text-2xl font-bold">Only what this role needs.</h2><p className="mt-4 text-sm leading-7 text-linen/55">Sensitive identity or screening access is intended to create a reasoned, timestamped audit event. Production permissions remain unimplemented until Phase 0 contracts are approved.</p>
              </aside>
            </div>
          </div>
        </section>
      </div>
      <DelegationPolicyModal open={policyOpen} onOpenChange={setPolicyOpen} />
    </main>
  );
};