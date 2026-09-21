import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, Building2 } from 'lucide-react';
import { RENTALS, money } from '@/data/siteData';
import { Button } from '@/components/ui/button';
import { DemoNotice } from './DemoNotice';
import { UnitFacts, UnitTerms } from './UnitFacts';

const filters = ['All', 'Residential', 'Commercial', 'Mixed-use'];
export const Listings = ({ onRequest }) => {
  const [params, setParams] = useSearchParams();
  const filter = params.get('use') || 'All';
  const location = params.get('location') || 'All locations';
  const visible = RENTALS.filter((u) => (filter === 'All' || u.use === filter || u.type === filter) && (location === 'All locations' || u.neighborhood === location));
  return <section id="rentals" className="texture-paper bg-linen py-24 sm:py-28"><div className="mx-auto max-w-7xl px-5 sm:px-8">
    <div className="mb-10 flex flex-col justify-between gap-8 lg:flex-row lg:items-end"><div className="max-w-2xl"><p className="kicker-line font-mono text-xs uppercase text-copper">Available rentals</p><h2 className="mt-5 font-heading text-4xl font-bold leading-tight sm:text-5xl">Find a space.<br />Know where you stand.</h2><p className="mt-5 max-w-xl leading-7 text-stone-600">Homes and commercial spaces, with residential and business terms shown on their own terms.</p></div>
      <div className="flex flex-wrap gap-2" data-testid="rentals-filter-group">{filters.map((item) => <button key={item} aria-pressed={filter === item} onClick={() => { const next = new URLSearchParams(params); next.set('use', item); setParams(next, { preventScrollReset: true }); }} className={`border px-4 py-3 text-sm font-semibold transition-colors ${filter === item ? 'border-obsidian bg-obsidian text-linen' : 'border-stone-400 bg-white text-stone-700 hover:border-copper'}`} data-testid={`filter-tab-${item.toLowerCase()}`}>{item}</button>)}</div>
    </div>
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-y border-stone-300 py-4 text-xs text-stone-600"><DemoNotice id="demonstration-badge-banner" /><span data-testid="rental-results-count">{visible.length} example {visible.length === 1 ? 'space' : 'spaces'}</span>{location !== 'All locations' && <button className="underline" onClick={() => { const next=new URLSearchParams(params); next.delete('location'); setParams(next); }} data-testid="clear-location-filter">Clear {location}</button>}</div>
    {!visible.length && <p className="py-16 text-stone-600" role="status" data-testid="rentals-empty-state">No published spaces match this selection.</p>}
    <div className="grid gap-7 lg:grid-cols-2">{visible.map((unit) => <article key={unit.id} className="property-card overflow-hidden border border-stone-200 bg-white" data-testid={`property-card-${unit.id}`}>
      <Link to={`/rentals/${unit.id}`} className="relative block aspect-[16/9] overflow-hidden" data-testid={`property-detail-link-${unit.id}`}><img src={unit.image} alt="Illustrative architecture, not a verified rental photograph" className="h-full w-full object-cover" loading="lazy" /><span className="absolute left-4 top-4 border border-white/30 bg-obsidian px-3 py-2 text-xs text-linen" data-testid={`unit-availability-${unit.id}`}>{unit.available}</span><span className="absolute bottom-0 left-0 right-0 bg-obsidian/90 px-5 py-3 text-sm text-linen">{unit.neighborhood} · Unit {unit.unit}<ArrowUpRight className="float-right h-4 w-4" /></span></Link>
      <div className="p-6"><div className="flex flex-wrap items-center justify-between gap-3"><p className="text-xs font-semibold text-copper" data-testid={`unit-type-${unit.id}`}>{unit.type} · {unit.use}</p><p className="text-xs text-stone-600">Fictional example</p></div><h3 className="mt-3 font-heading text-2xl font-bold" data-testid={`unit-title-${unit.id}`}>{unit.title}</h3><p className="mt-5" data-testid={`unit-rent-${unit.id}`}><span className="font-heading text-3xl font-bold">{money(unit.rent, unit.currency)}</span><span className="text-sm text-stone-600"> {unit.use === 'Commercial' ? 'base rent / month' : '/ month'}</span></p><UnitFacts unit={unit} prefix={`card-${unit.id}`} /><UnitTerms unit={unit} compact prefix={`card-term-${unit.id}`} /><div className="mt-6 flex flex-wrap gap-3"><Button className="bg-copper text-white hover:bg-copperDark" onClick={() => onRequest(unit, 'showing')} data-testid={`schedule-showing-btn-${unit.id}`}><Building2 className="h-4 w-4" />Preview showing</Button><Button asChild variant="outline" className="border-stone-400"><Link to={`/rentals/${unit.id}`} data-testid={`unit-terms-link-${unit.id}`}>View terms <ArrowUpRight size={16} /></Link></Button></div></div>
    </article>)}</div>
  </div></section>;
};