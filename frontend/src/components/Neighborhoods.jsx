import { ArrowUpRight, MapPin } from "lucide-react";
import { IMAGES } from "@/data/siteData";

const areas = [
  { name: "Downtown & OTR", image: IMAGES.mixedUse, detail: "Historic mixed-use blocks, apartments above local businesses, and direct access to the urban core." },
  { name: "Clifton", image: IMAGES.duplex, detail: "Duplexes and smaller multifamily homes near institutions, transit, and neighborhood retail." },
  { name: "Cincinnati neighborhoods", image: IMAGES.triplex, detail: "A flexible operating model for single-family, small multifamily, and future portfolio growth." },
];

export const Neighborhoods = () => (
  <section id="neighborhoods" className="bg-obsidian py-24 text-linen sm:py-28">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <div className="max-w-3xl"><p className="kicker-line font-mono text-xs uppercase tracking-[0.28em] text-gold">Greater Cincinnati</p><h2 className="mt-5 font-heading text-4xl font-bold leading-tight sm:text-5xl">Property care should respect the block, not just the building.</h2><p className="mt-5 leading-7 text-linen/60">PerchPoint is designed to expand across municipalities and states while preserving property, building, and unit-level context.</p></div>
      <div className="mt-12 grid gap-5 md:grid-cols-3">
        {areas.map((area) => <article key={area.name} className="group relative flex min-h-[400px] items-end overflow-hidden border border-white/20" data-testid={`neighborhood-${area.name.toLowerCase().replaceAll(" ", "-").replaceAll("&", "and")}`}><img src={area.image} alt={`${area.name} illustrative neighborhood context`} className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.03]" /><div className="absolute inset-0 bg-black/70" /><div className="relative p-6"><MapPin className="h-4 w-4 text-gold" /><h3 className="mt-4 font-heading text-2xl font-bold">{area.name}</h3><p className="mt-3 text-sm leading-6 text-linen">{area.detail}</p><ArrowUpRight className="mt-5 h-5 w-5 text-gold" /></div></article>)}
      </div>
    </div>
  </section>
);