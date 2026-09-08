import { useMemo, useState } from "react";
import { ArrowUpRight, BedDouble, Bath, Ruler } from "lucide-react";
import { toast } from "sonner";
import { LISTINGS } from "@/data/siteData";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const filters = ["All", "Hyde Park", "Indian Hill", "Mount Adams", "Over-The-Rhine"];
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const Listings = ({ onSchedule }) => {
  const [filter, setFilter] = useState("All");
  const visible = useMemo(
    () => (filter === "All" ? LISTINGS : LISTINGS.filter((item) => item.neighborhood === filter)),
    [filter]
  );

  const filterTestId = (item) =>
    item === "All"
      ? "listings-filter-all"
      : `listings-filter-${item.toLowerCase().replaceAll(" ", "-").replace("over-the-rhine", "over-the-rhine")}`;

  return (
    <section id="properties" className="texture-paper bg-linen py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mb-12 flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
          <div className="max-w-3xl">
            <p className="kicker-line font-mono text-xs uppercase tracking-[0.3em] text-copper">Curated access</p>
            <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-obsidian sm:text-5xl">
              Cincinnati residences with presence, privacy, and proof of value.
            </h2>
          </div>
          <div className="flex flex-wrap gap-2" data-testid="listings-filter-group">
            {filters.map((item) => (
              <button
                key={item}
                onClick={() => setFilter(item)}
                className={`rounded-full border px-4 py-2 text-sm font-semibold transition-all duration-300 ${filter === item ? "border-obsidian bg-obsidian text-linen" : "border-stone-300 bg-white text-stone-600 hover:border-copper hover:text-copper"}`}
                data-testid={filterTestId(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {visible.map((property, index) => (
            <article
              key={property.id}
              className={`property-card group overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-xl shadow-stone-200/40 ${index === 0 ? "md:row-span-2" : ""}`}
              data-testid={`property-card-${index + 1}`}
            >
              <div className={`relative overflow-hidden ${index === 0 ? "h-[420px]" : "h-72"}`}>
                <img src={property.image} alt={property.title} className="h-full w-full object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-obsidian/70 via-transparent to-transparent" />
                <Badge className="absolute left-5 top-5 border-gold/30 bg-obsidian/80 text-goldSoft backdrop-blur">
                  {property.tag}
                </Badge>
                <div className="absolute bottom-5 left-5 right-5 flex items-end justify-between gap-4 text-linen">
                  <div>
                    <p className="font-mono text-xs uppercase tracking-[0.24em] text-linen/70">{property.neighborhood}</p>
                    <h3 className="mt-2 font-heading text-2xl font-bold sm:text-3xl">{property.title}</h3>
                  </div>
                  <div className="rounded-full bg-linen px-4 py-2 text-sm font-bold text-obsidian">
                    {money.format(property.price)}
                  </div>
                </div>
              </div>

              <div className="p-6 sm:p-7">
                <p className="leading-7 text-stone-600">{property.note}</p>
                <div className="mt-6 flex flex-wrap gap-5 border-y border-stone-200 py-4 text-sm font-semibold text-stone-700">
                  <span className="flex items-center gap-2"><BedDouble className="h-4 w-4 text-copper" />{property.beds} beds</span>
                  <span className="flex items-center gap-2"><Bath className="h-4 w-4 text-copper" />{property.baths} baths</span>
                  <span className="flex items-center gap-2"><Ruler className="h-4 w-4 text-copper" />{property.sqft.toLocaleString()} sq ft</span>
                </div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button className="rounded-full bg-copper text-linen hover:bg-copperDark" onClick={() => onSchedule(property)} data-testid={`property-card-${index + 1}-tour-btn`}>
                    Schedule Private Tour
                    <ArrowUpRight className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    className="rounded-full border-stone-300 text-obsidian hover:border-gold hover:text-copper"
                    onClick={() => toast.success(`${property.neighborhood} market brief requested.`)}
                    data-testid={`property-card-${index + 1}-analyze-ai-btn`}
                  >
                    Request Market Brief
                  </Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};
