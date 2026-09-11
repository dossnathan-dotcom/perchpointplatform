import { ArrowUpRight, CalendarCheck, Eye, LogOut, MapPin } from "lucide-react";
import { LISTINGS } from "@/data/siteData";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const ClientDashboard = ({ user, savedIds = [], open, onOpenChange, onLogout, onSchedule }) => {
  if (!user) return null;
  const mergedSavedIds = [...new Set([...user.savedIds, ...savedIds])];
  const saved = LISTINGS.filter((item) => mergedSavedIds.includes(item.id));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] max-w-4xl overflow-y-auto border-white/10 bg-obsidian p-0 text-linen" data-testid="client-dashboard-panel">
        <div className="relative overflow-hidden border-b border-white/10 p-7 sm:p-9">
          <div className="texture-grid absolute inset-0" />
          <div className="relative flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
            <DialogHeader>
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-gold">{user.role}</p>
              <DialogTitle className="mt-3 font-heading text-4xl font-bold text-linen">Welcome, {user.name}</DialogTitle>
              <DialogDescription className="mt-2 text-linen/60">
                Your private Cincinnati portfolio and next recommended steps.
              </DialogDescription>
            </DialogHeader>
            <Button variant="outline" className="border-white/15 bg-white/5 text-linen hover:bg-white/10 hover:text-linen" onClick={onLogout} data-testid="client-dashboard-logout-btn">
              <LogOut className="h-4 w-4" /> Log out
            </Button>
          </div>
        </div>

        <div className="grid gap-5 p-7 sm:grid-cols-3 sm:p-9">
          <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-5">
            <Eye className="mb-4 h-5 w-5 text-gold" />
            <div className="text-sm text-linen/60">Market watchlist</div>
            <div className="mt-2 font-semibold">{user.watchlist}</div>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-5">
            <CalendarCheck className="mb-4 h-5 w-5 text-gold" />
            <div className="text-sm text-linen/60">Buying position</div>
            <div className="mt-2 font-semibold">{user.limit}</div>
          </div>
          <button onClick={onSchedule} className="rounded-3xl bg-gold p-5 text-left text-obsidian transition-transform hover:-translate-y-1" data-testid="client-dashboard-schedule-btn">
            <ArrowUpRight className="mb-4 h-5 w-5" />
            <div className="text-sm font-semibold uppercase tracking-[0.16em]">Next step</div>
            <div className="mt-2 font-heading text-xl font-bold">Book a private tour</div>
          </button>
        </div>

        <div className="px-7 pb-8 sm:px-9" data-testid="client-dashboard-saved-listings">
          <div className="mb-5 flex items-end justify-between gap-4">
            <h3 className="font-heading text-2xl font-bold">Saved Cincinnati homes</h3>
            <span className="font-mono text-xs uppercase tracking-[0.22em] text-gold" data-testid="client-dashboard-saved-count">{saved.length} saved</span>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {saved.map((item) => (
              <article key={item.id} className="overflow-hidden rounded-3xl border border-white/10 bg-white/[0.06]">
                <img src={item.image} alt={item.title} className="h-36 w-full object-cover" />
                <div className="p-5">
                  <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-gold">
                    <MapPin className="h-3 w-3" /> {item.neighborhood}
                  </div>
                  <h4 className="mt-3 font-semibold leading-6">{item.title}</h4>
                  <div className="mt-3 text-sm font-bold text-linen/70">{money.format(item.price)}</div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
