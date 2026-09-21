import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Bath, BedDouble, Building2, CalendarCheck, FileText, MapPin, Ruler, ShieldCheck } from "lucide-react";
import { PROPERTY_DETAILS } from "@/data/propertyDetails";
import { DEMO_NOTICE, RENTALS } from "@/data/siteData";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const PropertyDetailPage = ({ onRequest }) => {
  const { propertyId } = useParams();
  const property = RENTALS.find((item) => item.id === propertyId);
  const detail = PROPERTY_DETAILS[propertyId];
  useEffect(() => window.scrollTo(0, 0), [propertyId]);

  if (!property || !detail) return <main className="flex min-h-screen items-center justify-center bg-obsidian px-6 pt-20 text-linen" data-testid="property-detail-page"><div className="max-w-lg text-center"><h1 className="font-heading text-4xl font-bold">This unit is not currently in the demonstration inventory.</h1><Button asChild className="mt-8 bg-copper"><Link to="/" data-testid="property-detail-back-btn">Return to rentals</Link></Button></div></main>;

  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${detail.coordinates.lng - 0.025}%2C${detail.coordinates.lat - 0.018}%2C${detail.coordinates.lng + 0.025}%2C${detail.coordinates.lat + 0.018}&layer=mapnik&marker=${detail.coordinates.lat}%2C${detail.coordinates.lng}`;
  return (
    <main className="bg-obsidian text-linen" data-testid="property-detail-page">
      <section className="relative flex min-h-[86vh] items-end overflow-hidden pt-20">
        <img src={detail.gallery[0]} alt={`${property.title} building exterior`} className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-obsidian via-obsidian/35 to-obsidian/20" />
        <div className="relative z-10 mx-auto w-full max-w-7xl px-5 pb-14 sm:px-8">
          <Button asChild variant="outline" className="mb-10 border-white/20 bg-obsidian/40 text-linen backdrop-blur hover:bg-white/10 hover:text-linen"><Link to="/" data-testid="property-detail-back-btn"><ArrowLeft className="h-4 w-4" /> All rentals</Link></Button>
          <Badge className="mb-5 border-gold/30 bg-obsidian/80 text-goldSoft">{property.available}</Badge>
          <h1 className="max-w-4xl font-heading text-4xl font-bold leading-[1.04] sm:text-6xl lg:text-7xl">{property.title}</h1>
          <p className="mt-5 flex items-center gap-2 text-linen/75"><MapPin className="h-4 w-4 text-gold" /> {property.address}</p>
          <div className="mt-8 flex flex-wrap items-end gap-4"><span className="font-heading text-4xl font-bold">{money.format(property.rent)}</span><span className="pb-1 text-linen/60">per month · {money.format(property.deposit)} deposit</span></div>
        </div>
      </section>

      <section className="bg-linen py-20 text-obsidian sm:py-24">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 sm:px-8 lg:grid-cols-[1fr_0.72fr]">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-copper" data-testid="property-detail-demo-notice">{DEMO_NOTICE}</p>
            <h2 className="mt-5 font-heading text-4xl font-bold">A clear view of the unit and its terms.</h2>
            <p className="mt-6 max-w-3xl leading-8 text-stone-600">{detail.overview}</p>
            <div className="mt-9 grid gap-3 sm:grid-cols-3">
              {property.beds !== null && <div className="border border-stone-200 bg-white p-5"><BedDouble className="h-4 w-4 text-copper" /><p className="mt-3 text-sm text-stone-500">Bedrooms</p><p className="text-xl font-bold">{property.beds}</p></div>}
              <div className="border border-stone-200 bg-white p-5"><Bath className="h-4 w-4 text-copper" /><p className="mt-3 text-sm text-stone-500">Baths</p><p className="text-xl font-bold">{property.baths}</p></div>
              <div className="border border-stone-200 bg-white p-5"><Ruler className="h-4 w-4 text-copper" /><p className="mt-3 text-sm text-stone-500">Space</p><p className="text-xl font-bold">{property.sqft.toLocaleString()} sq ft</p></div>
            </div>
            <div className="mt-9 grid gap-3 sm:grid-cols-2" data-testid="property-detail-gallery">{detail.gallery.map((image, index) => <img key={image} src={image} alt={`${property.title} view ${index + 1}`} className={`aspect-[4/3] w-full object-cover ${index === 0 ? "sm:col-span-2" : ""}`} data-testid={`property-gallery-image-${index + 1}`} />)}</div>
            <div className="mt-9 grid gap-3 sm:grid-cols-2">{detail.features.map((feature) => <div key={feature} className="flex items-center gap-3 border border-stone-200 bg-white p-4"><ShieldCheck className="h-4 w-4 text-copper" /><span className="font-semibold">{feature}</span></div>)}</div>
          </div>
          <aside className="space-y-5 lg:sticky lg:top-28 lg:self-start">
            <div className="border border-stone-200 bg-white p-7 shadow-xl shadow-stone-200/40" data-testid="property-detail-terms-card">
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-copper">Terms at a glance</p>
              <dl className="mt-6 space-y-4 text-sm">{[["Monthly rent", money.format(property.rent)], ["Security deposit", money.format(property.deposit)], ["Lease term", detail.leaseTerm], ["Utilities", property.utilities], ["Pet policy", property.petPolicy], ["Application", property.applicationFee], ["Qualification", property.qualification], ["Parking", detail.parking]].map(([label, value]) => <div key={label} className="border-t border-stone-200 pt-4"><dt className="text-stone-500">{label}</dt><dd className="mt-1 font-semibold leading-6">{value}</dd></div>)}</dl>
              <div className="mt-7 grid gap-3"><Button className="h-12 bg-copper text-linen hover:bg-copperDark" onClick={() => onRequest(property, "showing")} data-testid="property-detail-showing-btn"><CalendarCheck className="h-4 w-4" /> Schedule showing</Button><Button variant="outline" className="h-12 border-stone-300" onClick={() => onRequest(property, "application")} data-testid="property-detail-apply-btn"><FileText className="h-4 w-4" /> Start application</Button></div>
            </div>
            <div className="overflow-hidden border border-stone-200 bg-white" data-testid="property-detail-map"><iframe title={`${property.neighborhood} map`} src={mapUrl} className="h-72 w-full border-0" loading="lazy" /><div className="p-5"><div className="flex items-center gap-2 font-semibold"><Building2 className="h-4 w-4 text-copper" /> {property.neighborhood}</div><p className="mt-2 text-sm text-stone-500">Map shown for neighborhood context; confirm exact showing details with HawkVision.</p></div></div>
          </aside>
        </div>
      </section>
    </main>
  );
};