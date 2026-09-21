import { Building2, ChevronRight, DoorOpen, Landmark, Layers3 } from "lucide-react";
import { DEMO_NOTICE, PROPERTY_TREE } from "@/data/siteData";

const Node = ({ icon: Icon, label, value, testId }) => (
  <div className="flex min-w-0 items-center gap-3 border border-white/10 bg-white/[0.05] p-4" data-testid={testId}>
    <span className="flex h-9 w-9 shrink-0 items-center justify-center bg-copper/15 text-gold"><Icon className="h-4 w-4" /></span>
    <span className="min-w-0"><span className="block font-mono text-[9px] uppercase tracking-[0.2em] text-linen/45">{label}</span><span className="mt-1 block truncate text-sm font-bold text-linen">{value}</span></span>
  </div>
);

export const PropertyHierarchyView = () => (
  <section id="properties" className="bg-obsidian py-24 text-linen sm:py-28">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <div className="grid gap-12 lg:grid-cols-[0.75fr_1.25fr] lg:items-start">
        <div className="lg:sticky lg:top-28">
          <p className="kicker-line font-mono text-xs uppercase tracking-[0.28em] text-gold">Built for real portfolios</p>
          <h2 className="mt-5 font-heading text-4xl font-bold leading-tight sm:text-5xl">Every building. Every unit. Its own operating record.</h2>
          <p className="mt-6 leading-8 text-linen/65">PerchPoint is structured for houses, duplexes, triplexes, multifamily, commercial, and mixed-use properties—without flattening them into one generic listing.</p>
          <p className="mt-6 border-l-2 border-copper pl-5 text-sm leading-7 text-linen/55">A household can have one primary portal holder while each adult signer keeps an individual identity for signatures, consent, notices, and document access.</p>
        </div>

        <div className="border border-white/10 bg-[#11161d] p-5 sm:p-7" data-testid="property-hierarchy-view">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-gold">{DEMO_NOTICE}</span>
            <span className="text-xs text-linen/45">Mixed-use structure example</span>
          </div>
          <div className="grid gap-3">
            <Node icon={Landmark} label="Organization" value={PROPERTY_TREE.organization} testId="hierarchy-organization" />
            <ChevronRight className="ml-5 h-4 w-4 rotate-90 text-linen/30" />
            <Node icon={Layers3} label="Ownership entity" value={PROPERTY_TREE.entity} testId="hierarchy-ownership-entity" />
            <ChevronRight className="ml-5 h-4 w-4 rotate-90 text-linen/30" />
            <Node icon={Building2} label="Property / Building" value={PROPERTY_TREE.property} testId="hierarchy-property" />
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {PROPERTY_TREE.units.map((unit) => (
              <div key={unit.id} className="border border-white/10 bg-white/[0.04] p-4" data-testid={`unit-row-${unit.id.toLowerCase()}`}>
                <DoorOpen className="h-4 w-4 text-gold" />
                <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-linen/45">{unit.id} · {unit.type}</p>
                <h3 className="mt-2 font-heading text-xl font-bold">{unit.label}</h3>
                <p className="mt-3 text-sm text-linen/55">{unit.detail}</p>
                <span className="mt-4 inline-flex bg-white/10 px-2 py-1 text-xs text-linen/70">{unit.status}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 border border-dashed border-white/15 p-4" data-testid="hierarchy-shared-assets">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-gold">Shared spaces & assets</p>
            <div className="mt-3 flex flex-wrap gap-2">{PROPERTY_TREE.assets.map((asset) => <span key={asset} className="bg-white/[0.06] px-3 py-2 text-xs text-linen/65">{asset}</span>)}</div>
          </div>
        </div>
      </div>
    </div>
  </section>
);