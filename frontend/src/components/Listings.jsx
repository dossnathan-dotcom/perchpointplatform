import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Bath, BedDouble, BriefcaseBusiness, Building2, Ruler } from "lucide-react";
import { DEMO_NOTICE, RENTALS } from "@/data/siteData";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const filters = ["All", "Residential", "Commercial", "Mixed-use"];
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const Listings = ({ onRequest }) => {
  const [filter, setFilter] = useState("All");
  const visible = useMemo(() => filter === "All" ? RENTALS : RENTALS.filter((item) => item.use === filter || item.type === filter), [filter]);

  return (
    <section id="rentals" className="texture-paper bg-linen py-24 sm:py-28">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mb-10 flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
          <div className="max-w-3xl">
            <p className="kicker-line font-mono text-xs uppercase tracking-[0.28em] text-copper">Current availability</p>
            <h2 className="mt-5 font-heading text-4xl font-bold leading-tight sm:text-5xl">Homes and commercial spaces with the terms shown up front.</h2>
            <p className="mt-5 max-w-2xl leading-7 text-stone-600">Each unit is tracked independently—from lease and ledger to utilities, access, and maintenance.</p>
          </div>
          <div className="flex flex-wrap gap-2" data-testid="rentals-filter-group">
            {filters.map((item) => <button key={item} onClick={() => setFilter(item)} className={`border px-4 py-2 text-sm font-semibold transition-colors ${filter === item ? "border-obsidian bg-obsidian text-linen" : "border-stone-300 bg-white text-stone-600 hover:border-copper hover:text-copper"}`} data-testid={`filter-tab-${item.toLowerCase().replaceAll("-", "-").replaceAll(" ", "-")}`}>{item}</button>)}
          </div>
        </div>

        <div className="mb-5 flex items-center justify-between border-y border-stone-300 py-3 font-mono text-[10px] uppercase tracking-[0.18em] text-stone-500" data-testid="demonstration-badge-banner">
          <span>{DEMO_NOTICE}</span><span>{visible.length} example spaces</span>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {visible.map((property) => (
            <article key={property.id} className="property-card overflow-hidden border border-stone-200 bg-white shadow-xl shadow-stone-200/40" data-testid={`property-card-${property.id}`}>
              <div className="relative aspect-[16/9] overflow-hidden">
                <img src={property.image} alt={`${property.title} demonstration rental`} className="h-full w-full object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-obsidian/80 via-transparent to-transparent" />
                <Badge className="absolute left-5 top-5 border-gold/30 bg-obsidian/85 text-goldSoft">{property.available}</Badge>
                <div className="absolute bottom-5 left-5 right-5 text-linen">
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-linen/70">{property.neighborhood} · {property.unit}</p>
                  <Link to={`/property/${property.id}`} className="mt-2 block font-heading text-2xl font-bold hover:text-gold" data-testid={`property-detail-link-${property.id}`}>{property.title}</Link>
                </div>
              </div>
              <div className="p-6">
                <div className="flex flex-wrap items-end justify-between gap-4">
                  <div><span className="font-heading text-3xl font-bold">{money.format(property.rent)}</span><span className="text-sm text-stone-500"> / month</span></div>
                  <span className="border border-stone-200 bg-stone-50 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-stone-600">{property.type} · {property.use}</span>
                </div>
                <p className="mt-5 leading-7 text-stone-600">{property.note}</p>
                <div className="mt-5 flex flex-wrap gap-4 border-y border-stone-200 py-4 text-sm font-semibold text-stone-700">
                  {property.beds !== null ? <span className="flex items-center gap-2"><BedDouble className="h-4 w-4 text-copper" />{property.beds} beds</span> : <span className="flex items-center gap-2"><BriefcaseBusiness className="h-4 w-4 text-copper" />Commercial</span>}
                  <span className="flex items-center gap-2"><Bath className="h-4 w-4 text-copper" />{property.baths} bath</span>
                  <span className="flex items-center gap-2"><Ruler className="h-4 w-4 text-copper" />{property.sqft.toLocaleString()} sq ft</span>
                </div>
                <dl className="mt-5 grid gap-2 text-sm sm:grid-cols-2">
                  <div><dt className="text-stone-500">Security deposit</dt><dd className="font-bold">{money.format(property.deposit)}</dd></div>
                  <div><dt className="text-stone-500">Application</dt><dd className="font-bold">{property.applicationFee}</dd></div>
                </dl>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button className="bg-copper text-linen hover:bg-copperDark" onClick={() => onRequest(property, "showing")} data-testid={`schedule-showing-btn-${property.id}`}><Building2 className="h-4 w-4" /> Schedule showing</Button>
                  <Button variant="outline" className="border-stone-300" onClick={() => onRequest(property, "application")} data-testid={`apply-unit-btn-${property.id}`}>Start application <ArrowUpRight className="h-4 w-4" /></Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};