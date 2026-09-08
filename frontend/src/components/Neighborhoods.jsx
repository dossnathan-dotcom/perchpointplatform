import { ArrowRight } from "lucide-react";
import { NEIGHBORHOODS } from "@/data/siteData";

export const Neighborhoods = () => {
  return (
    <section id="neighborhoods" className="bg-obsidian py-24 text-linen sm:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mb-14 grid gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:items-end">
          <div>
            <p className="kicker-line font-mono text-xs uppercase tracking-[0.3em] text-gold">Seven hills, one strategy</p>
            <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight sm:text-5xl">
              Know the block before you chase the address.
            </h2>
          </div>
          <p className="max-w-2xl text-base leading-8 text-linen/70 lg:justify-self-end">
            HawkVision pairs neighborhood instinct with hard transaction signals so buyers avoid overpaying and sellers know exactly where their leverage starts.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {NEIGHBORHOODS.map((area, index) => (
            <a
              key={area.name}
              href="#valuation"
              className={`group relative overflow-hidden rounded-[1.75rem] border border-white/10 bg-white/5 ${index % 2 ? "lg:translate-y-10" : ""}`}
              data-testid={`neighborhood-card-${index + 1}`}
            >
              <img src={area.image} alt={`${area.name} Cincinnati neighborhood`} className="h-80 w-full object-cover opacity-72 transition-all duration-700 group-hover:scale-105 group-hover:opacity-90" />
              <div className="absolute inset-0 bg-gradient-to-t from-obsidian via-obsidian/20 to-transparent" />
              <div className="absolute inset-x-0 bottom-0 p-6">
                <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-full border border-gold/40 bg-obsidian/60 font-mono text-sm text-gold backdrop-blur">
                  {area.score}
                </div>
                <h3 className="font-heading text-2xl font-bold">{area.name}</h3>
                <p className="mt-2 text-sm leading-6 text-linen/70">{area.detail}</p>
                <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-gold">
                  Explore value <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </span>
              </div>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
};
