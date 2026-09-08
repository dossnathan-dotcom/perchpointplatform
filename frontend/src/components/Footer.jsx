import { ArrowUpRight, Building2, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Footer = ({ onSchedule }) => {
  return (
    <footer className="bg-[#080B10] text-linen">
      <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8">
        <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
          <div>
            <div className="mb-6 flex items-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center rounded-full border border-gold/40 bg-gold/10 text-gold">
                <Building2 className="h-5 w-5" />
              </span>
              <span className="font-heading text-3xl font-bold">HawkVision Homes</span>
            </div>
            <p className="max-w-xl text-base leading-8 text-linen/60">
              Boutique realty for buyers and sellers who want sharper Cincinnati market vision, discreet access, and decisive negotiation.
            </p>
            <div className="mt-8 font-heading text-5xl font-bold uppercase tracking-tight text-white/[0.06] sm:text-7xl">
              Cincinnati
            </div>
          </div>
          <div className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-7">
            <p className="font-mono text-xs uppercase tracking-[0.3em] text-gold">Ready when you are</p>
            <h3 className="mt-4 font-heading text-3xl font-bold">Start with a private consultation.</h3>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Button className="rounded-full bg-gold text-obsidian hover:bg-goldSoft" onClick={onSchedule} data-testid="footer-consultation-btn">
                Book Consultation <ArrowUpRight className="h-4 w-4" />
              </Button>
              <Button variant="outline" className="rounded-full border-white/15 bg-transparent text-linen hover:bg-white/10 hover:text-linen" data-testid="footer-call-btn">
                <Phone className="h-4 w-4" /> (513) 555-0198
              </Button>
            </div>
          </div>
        </div>

        <div className="mt-14 flex flex-col justify-between gap-5 border-t border-white/10 pt-7 text-sm text-linen/50 sm:flex-row">
          <span>© 2026 HawkVision Homes. Cincinnati, Ohio.</span>
          <span>Licensed Ohio brokerage · Equal Housing Opportunity</span>
        </div>
      </div>
    </footer>
  );
};
