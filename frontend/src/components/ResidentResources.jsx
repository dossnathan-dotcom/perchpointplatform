import { AlertTriangle, BookOpenCheck, FileText, PhoneCall, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";

const resources = [
  [FileText, "Lease & documents", "Find signed agreements, notices, and property-specific records in your resident portal."],
  [BookOpenCheck, "Rent & account history", "Review charges, receipts, balance activity, and payment status from one household view."],
  [Wrench, "Maintenance history", "Submit non-emergency requests and follow assignment, scheduling, evidence, and completion."],
];

export const ResidentResources = ({ onMaintenance, onLogin }) => (
  <section id="resident-resources" className="bg-linen py-24 sm:py-28">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p className="kicker-line font-mono text-xs uppercase tracking-[0.28em] text-copper">Resident resources</p>
          <h2 className="mt-5 font-heading text-4xl font-bold leading-tight sm:text-5xl">Your home, records, and requests in one place.</h2>
          <p className="mt-6 max-w-xl leading-8 text-stone-600">The Resident Portal is designed around a primary household account without asking adults to share passwords or signatures.</p>
          <Button className="mt-8 bg-obsidian text-linen hover:bg-copper" onClick={onLogin} data-testid="resident-portal-signin-btn">Open resident portal preview</Button>
        </div>
        <div className="grid gap-3">
          {resources.map(([Icon, title, copy]) => <article key={title} className="grid grid-cols-[auto_1fr] gap-5 border border-stone-200 bg-white p-6" data-testid={`resource-${title.toLowerCase().replaceAll(" ", "-").replaceAll("&", "and")}`}><span className="flex h-11 w-11 items-center justify-center bg-copper/10 text-copper"><Icon className="h-5 w-5" /></span><div><h3 className="font-heading text-xl font-bold">{title}</h3><p className="mt-2 text-sm leading-6 text-stone-600">{copy}</p></div></article>)}
        </div>
      </div>

      <div id="maintenance" className="mt-16 grid overflow-hidden border border-red-900/30 bg-obsidian text-linen lg:grid-cols-[0.8fr_1.2fr]" data-testid="emergency-hotline-banner">
        <div className="bg-red-950/35 p-7 sm:p-9">
          <div className="flex items-center gap-3 text-red-300"><AlertTriangle className="h-5 w-5" /><span className="font-mono text-xs uppercase tracking-[0.2em]">Emergency maintenance</span></div>
          <h3 className="mt-5 font-heading text-3xl font-bold">Protect life first. Then protect the property.</h3>
          <p className="mt-4 text-sm leading-7 text-linen/65">For fire, immediate danger, or suspected gas exposure, leave the area and call 911. For an active property emergency, use the emergency contact listed in your lease and portal.</p>
          <a href="tel:911" className="mt-6 inline-flex items-center gap-2 font-bold text-red-200" data-testid="emergency-call-911-link"><PhoneCall className="h-4 w-4" /> Call 911 for immediate danger</a>
        </div>
        <div className="p-7 sm:p-9">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-gold">Non-emergency request</p>
          <h3 className="mt-4 font-heading text-3xl font-bold">Report the issue with the right details.</h3>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-linen/65">Describe what happened, identify the property and unit, and record entry permission. Photo upload and dispatch workflows will activate after Phase 0 contracts are finalized.</p>
          <Button className="mt-7 bg-copper text-linen hover:bg-copperDark" onClick={onMaintenance} data-testid="submit-maintenance-ticket-btn"><Wrench className="h-4 w-4" /> Submit maintenance request</Button>
        </div>
      </div>
    </div>
  </section>
);