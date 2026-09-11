import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Bath, BedDouble, CalendarCheck, Heart, Home, MapPin, Ruler, ShieldCheck, TrendingUp } from "lucide-react";
import { PROPERTY_DETAILS } from "@/data/propertyDetails";
import { LISTINGS } from "@/data/siteData";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const PropertyDetailPage = ({ onSchedule, savedIds, onToggleSaved }) => {
  const { propertyId } = useParams();
  const property = LISTINGS.find((item) => item.id === propertyId);
  const detail = PROPERTY_DETAILS[propertyId];

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [propertyId]);

  if (!property || !detail) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-obsidian px-6 pt-20 text-linen" data-testid="property-detail-page">
        <div className="max-w-lg text-center">
          <h1 className="font-heading text-4xl font-bold">This private residence is no longer available.</h1>
          <Button asChild className="mt-8 rounded-full bg-gold text-obsidian hover:bg-goldSoft">
            <Link to="/" data-testid="property-detail-back-btn">Return to portfolio</Link>
          </Button>
        </div>
      </main>
    );
  }

  const isSaved = savedIds.includes(property.id);
  const pricePerFoot = Math.round(property.price / property.sqft);
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${detail.coordinates.lng - 0.025}%2C${detail.coordinates.lat - 0.018}%2C${detail.coordinates.lng + 0.025}%2C${detail.coordinates.lat + 0.018}&layer=mapnik&marker=${detail.coordinates.lat}%2C${detail.coordinates.lng}`;

  return (
    <main className="bg-obsidian text-linen" data-testid="property-detail-page">
      <section className="relative flex min-h-[92vh] items-end overflow-hidden pt-20">
        <img src={detail.gallery[0]} alt={property.title} className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-obsidian via-obsidian/30 to-obsidian/20" />
        <div className="texture-grid absolute inset-0" />

        <div className="relative z-10 mx-auto w-full max-w-7xl px-5 pb-14 sm:px-8">
          <div className="mb-10 flex items-center justify-between gap-4">
            <Button asChild variant="outline" className="rounded-full border-white/20 bg-obsidian/40 text-linen backdrop-blur hover:bg-white/10 hover:text-linen">
              <Link to="/" data-testid="property-detail-back-btn"><ArrowLeft className="h-4 w-4" /> Portfolio</Link>
            </Button>
            <button
              aria-pressed={isSaved}
              onClick={() => onToggleSaved(property.id)}
              className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold backdrop-blur transition-colors ${isSaved ? "border-gold bg-gold text-obsidian" : "border-white/20 bg-obsidian/40 text-linen hover:border-gold"}`}
              data-testid="property-detail-save-btn"
            >
              <Heart className={`h-4 w-4 ${isSaved ? "fill-current" : ""}`} />
              {isSaved ? "Saved" : "Save home"}
            </button>
          </div>

          <Badge className="mb-5 border-gold/30 bg-obsidian/70 text-goldSoft backdrop-blur">{property.tag}</Badge>
          <h1 className="max-w-4xl font-heading text-4xl font-bold leading-[1.04] tracking-tight sm:text-6xl lg:text-7xl">
            {property.title}
          </h1>
          <div className="mt-6 flex flex-wrap items-center gap-5 text-linen/80">
            <span className="flex items-center gap-2"><MapPin className="h-4 w-4 text-gold" /> {detail.address}</span>
            <span className="font-heading text-3xl font-bold text-linen">{money.format(property.price)}</span>
          </div>

          <div className="mt-10 grid gap-3 rounded-[2rem] border border-white/10 bg-obsidian/60 p-4 backdrop-blur-xl sm:grid-cols-4">
            <div className="rounded-3xl bg-white/10 p-5"><BedDouble className="mb-3 h-5 w-5 text-gold" /><span className="text-sm text-linen/60">Bedrooms</span><div className="text-xl font-bold">{property.beds}</div></div>
            <div className="rounded-3xl bg-white/10 p-5"><Bath className="mb-3 h-5 w-5 text-gold" /><span className="text-sm text-linen/60">Baths</span><div className="text-xl font-bold">{property.baths}</div></div>
            <div className="rounded-3xl bg-white/10 p-5"><Ruler className="mb-3 h-5 w-5 text-gold" /><span className="text-sm text-linen/60">Interior</span><div className="text-xl font-bold">{property.sqft.toLocaleString()} sq ft</div></div>
            <div className="rounded-3xl bg-white/10 p-5"><TrendingUp className="mb-3 h-5 w-5 text-gold" /><span className="text-sm text-linen/60">Price / sq ft</span><div className="text-xl font-bold">${pricePerFoot}</div></div>
          </div>
        </div>
      </section>

      <section className="bg-linen py-20 text-obsidian sm:py-28">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 sm:px-8 lg:grid-cols-[1fr_0.72fr]">
          <div>
            <p className="kicker-line font-mono text-xs uppercase tracking-[0.3em] text-copper">Property story</p>
            <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight sm:text-5xl">A closer look at the way this home lives.</h2>
            <p className="mt-6 max-w-3xl text-base leading-8 text-stone-600">{detail.story}</p>

            <div className="mt-10 grid gap-4 sm:grid-cols-3" data-testid="property-detail-gallery">
              {detail.gallery.map((image, index) => (
                <img key={image} src={image} alt={`${property.title} gallery view ${index + 1}`} className={`rounded-[1.5rem] object-cover ${index === 0 ? "h-96 sm:col-span-3" : "h-56"}`} data-testid={`property-gallery-image-${index + 1}`} />
              ))}
            </div>

            <div className="mt-10 grid gap-3 sm:grid-cols-2">
              {detail.features.map((feature) => (
                <div key={feature} className="flex items-center gap-3 rounded-2xl border border-stone-200 bg-white p-4">
                  <ShieldCheck className="h-4 w-4 text-copper" />
                  <span className="font-semibold text-stone-700">{feature}</span>
                </div>
              ))}
            </div>
          </div>

          <aside className="space-y-5 lg:sticky lg:top-28 lg:self-start">
            <div className="rounded-[2rem] border border-stone-200 bg-white p-7 shadow-xl shadow-stone-200/50" data-testid="property-detail-price-card">
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-copper">Pricing detail</p>
              <div className="mt-4 font-heading text-4xl font-bold">{money.format(property.price)}</div>
              <div className="mt-6 space-y-4 border-t border-stone-200 pt-6">
                {detail.priceHistory.map((item) => (
                  <div key={item.label} className="flex items-center justify-between gap-4 text-sm">
                    <span className="text-stone-500">{item.label}</span>
                    <span className="font-bold text-obsidian">{item.value}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between gap-4 text-sm">
                  <span className="text-stone-500">Estimated taxes</span>
                  <span className="font-bold text-obsidian">{detail.taxes}</span>
                </div>
                <div className="flex items-center justify-between gap-4 text-sm">
                  <span className="text-stone-500">HOA</span>
                  <span className="font-bold text-obsidian">{detail.hoa}</span>
                </div>
              </div>
              <Button className="mt-7 h-12 w-full rounded-full bg-copper text-linen hover:bg-copperDark" onClick={() => onSchedule(property, "private_tour")} data-testid="property-detail-tour-btn">
                <CalendarCheck className="h-4 w-4" /> Schedule This Tour
              </Button>
            </div>

            <div className="overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-xl shadow-stone-200/50" data-testid="property-detail-map">
              <iframe title={`${property.neighborhood} map`} src={mapUrl} className="h-80 w-full border-0" loading="lazy" />
              <div className="p-5">
                <div className="flex items-center gap-2 font-semibold text-obsidian"><Home className="h-4 w-4 text-copper" /> {property.neighborhood}</div>
                <p className="mt-2 text-sm text-stone-500">{detail.daysPrivate} · Map provided for neighborhood context.</p>
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
};
