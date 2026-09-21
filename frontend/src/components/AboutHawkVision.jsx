import { ClipboardCheck, Landmark, MessageSquareText, ShieldCheck } from "lucide-react";
import { IMAGES } from "@/data/siteData";

const standards = [
  [ClipboardCheck, "Preventive by default", "Property-level schedules keep recurring inspections and maintenance visible before they become emergencies."],
  [MessageSquareText, "Dignified communication", "Residents, applicants, vendors, and staff receive context appropriate to their role—without exposing unrelated records."],
  [Landmark, "Clean operating records", "Each unit keeps its own lease, occupants, ledger, documents, utilities, work history, and access instructions."],
  [ShieldCheck, "Authority with boundaries", "Business approval, infrastructure administration, and delegated spending are intentionally separated and auditable."],
];

export const AboutHawkVision = () => (
  <section id="about" className="bg-white py-24 sm:py-28">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
        <div className="relative aspect-[4/5] overflow-hidden lg:aspect-[5/6]">
          <img src={IMAGES.skyline} alt="Cincinnati riverfront and skyline" className="h-full w-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-obsidian/75 via-transparent to-transparent" />
          <div className="absolute bottom-0 left-0 max-w-md p-7 text-linen sm:p-10"><p className="font-mono text-xs uppercase tracking-[0.25em] text-gold">HawkVision Homes</p><p className="mt-4 font-heading text-3xl font-bold">Local property stewardship, connected through PerchPoint.</p></div>
        </div>
        <div>
          <p className="kicker-line font-mono text-xs uppercase tracking-[0.28em] text-copper">How we operate</p>
          <h2 className="mt-5 font-heading text-4xl font-bold leading-tight sm:text-5xl">Professional systems should make property care feel more human.</h2>
          <div className="mt-9 grid gap-3">
            {standards.map(([Icon, title, copy]) => <article key={title} className="grid grid-cols-[auto_1fr] gap-4 border-t border-stone-200 py-5" data-testid={`operating-standard-${title.toLowerCase().replaceAll(" ", "-")}`}><Icon className="mt-1 h-5 w-5 text-copper" /><div><h3 className="font-bold">{title}</h3><p className="mt-2 text-sm leading-6 text-stone-600">{copy}</p></div></article>)}
          </div>
        </div>
      </div>
    </div>
  </section>
);