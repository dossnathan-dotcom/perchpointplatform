import { ArrowUpRight, Building2, ShieldCheck, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Footer = ({ onContact, onMaintenance }) => (
  <footer id="contact" className="bg-[#080B10] text-linen">
    <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8">
      <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
        <div><div className="mb-6 flex items-center gap-3"><span className="flex h-12 w-12 items-center justify-center border border-gold/40 bg-gold/10 text-gold"><Building2 className="h-5 w-5" /></span><span><span className="block font-heading text-3xl font-bold">HawkVision Homes</span><span className="font-mono text-[9px] uppercase tracking-[0.2em] text-linen/45">Connected by PerchPoint</span></span></div><p className="max-w-xl text-base leading-8 text-linen/60">Property operations and rental experiences built around clear records, responsive care, and accountable access.</p><div className="mt-8 font-heading text-5xl font-bold uppercase text-white/[0.06] sm:text-7xl">Cincinnati</div></div>
        <div className="border border-white/10 bg-white/[0.05] p-7"><p className="font-mono text-xs uppercase tracking-[0.25em] text-gold">Need the right next step?</p><h3 className="mt-4 font-heading text-3xl font-bold">Talk with the property team.</h3><div className="mt-7 flex flex-col gap-3 sm:flex-row"><Button className="bg-gold text-obsidian hover:bg-goldSoft" onClick={onContact} data-testid="footer-contact-btn">Contact HawkVision <ArrowUpRight className="h-4 w-4" /></Button><Button variant="outline" className="border-white/15 bg-transparent text-linen hover:bg-white/10 hover:text-linen" onClick={onMaintenance} data-testid="footer-maintenance-btn"><Wrench className="h-4 w-4" /> Maintenance</Button></div></div>
      </div>
      <div className="mt-14 grid gap-5 border-t border-white/10 pt-7 text-sm text-linen/45 md:grid-cols-[1fr_auto] md:items-center"><div><p>© 2026 HawkVision Homes · Cincinnati, Ohio</p><p className="mt-2">Phase 0 demonstration. Property availability, pricing, and portfolio data are seeded examples until verified by HawkVision.</p></div><div className="flex items-center gap-2" data-testid="footer-fair-housing"><ShieldCheck className="h-4 w-4 text-gold" /> Equal Housing Opportunity</div></div>
    </div>
  </footer>
);