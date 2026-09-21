import { useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, CalendarCheck, FileText } from 'lucide-react';
import { ALL_UNITS, money, PORTFOLIO } from '@/data/siteData';
import { Button } from '@/components/ui/button';
import { DemoNotice } from './DemoNotice';
import { UnitFacts, UnitTerms } from './UnitFacts';

export const PropertyDetailPage = ({ onRequest }) => {
  const { unitId, propertyId } = useParams();
  const unit = ALL_UNITS.find((u) => u.id === (unitId || propertyId));
  useEffect(() => window.scrollTo(0, 0), [unitId, propertyId]);
  if (!unit) return <main className="min-h-screen bg-obsidian px-6 pb-20 pt-40 text-linen" data-testid="property-detail-page"><h1 className="font-heading text-4xl">This example unit is not available.</h1><Link className="mt-8 block underline" to="/#rentals" data-testid="property-detail-back-btn">Return to rentals</Link></main>;
  const building = PORTFOLIO.buildings.find((b) => b.id === unit.buildingId);
  return <main data-testid="property-detail-page">
    <section className="relative bg-obsidian pb-14 pt-36 text-linen">
      <img src={unit.image} alt="Illustrative architecture, not this synthetic unit" className="absolute inset-0 h-full w-full object-cover" />
      <div className="hero-vignette absolute inset-0" />
      <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
        <Link to="/#rentals" className="inline-flex items-center gap-2 py-4 text-sm underline" data-testid="property-detail-back-btn"><ArrowLeft size={16} />All rental examples</Link>
        <DemoNotice id="property-detail-demo-notice" className="mt-8 text-gold" />
        <h1 className="mt-5 max-w-4xl font-heading text-4xl font-bold leading-tight sm:text-5xl lg:text-6xl" data-testid="unit-detail-title">{unit.title}</h1>
        <p className="mt-6 max-w-2xl leading-7" data-testid="unit-detail-address">{unit.address} · {unit.neighborhood}</p>
        <p className="mt-8 font-heading text-3xl" data-testid="unit-detail-rent">{money(unit.rent, unit.currency)} <span className="font-body text-base">{unit.use === 'Commercial' ? `base rent / ${unit.commercial.rent_period}` : '/ month'}</span></p>
      </div>
    </section>
    <section className="bg-linen py-16"><div className="mx-auto grid max-w-7xl gap-12 px-5 sm:px-8 lg:grid-cols-[1.2fr_1fr]">
      <div><p className="text-sm text-copper" data-testid="unit-detail-hierarchy">{unit.propertyName} → {building.name} → Unit {unit.unit}</p><h2 className="mt-5 font-heading text-3xl font-bold">A space with its own story.</h2><p className="mt-5 leading-8 text-stone-600">{unit.note}</p><UnitFacts unit={unit} prefix="detail" /><img className="mt-8 aspect-[4/3] w-full object-contain bg-stone-100" src={unit.image} alt="Illustrative reference only; not a verified unit photograph" data-testid="property-gallery-image-1" /><p className="mt-3 text-sm text-stone-600" data-testid="unit-photo-disclosure">Illustrative imagery. The address, terms and unit are fictional examples.</p></div>
      <aside className="border-t border-stone-300 pt-6" data-testid="property-detail-terms-card"><h2 className="font-heading text-2xl font-bold">{unit.use === 'Commercial' ? 'Commercial leasing terms' : 'Residential terms'}</h2><UnitTerms unit={unit} prefix="detail-term" /><div className="mt-8 flex flex-wrap gap-3"><Button className="bg-copper text-white hover:bg-copperDark" onClick={() => onRequest(unit, 'showing')} data-testid="property-detail-showing-btn"><CalendarCheck size={16} />Preview showing request</Button><Button variant="outline" onClick={() => onRequest(unit, 'application')} data-testid="property-detail-apply-btn"><FileText size={16} />Application interest</Button></div></aside>
    </div></section>
  </main>;
};