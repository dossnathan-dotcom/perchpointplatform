import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { phase2, moneyMinor } from '@/api/phase2';

const filters = ['All', 'Residential', 'Commercial'];

export const Listings = () => {
  const [params, setParams] = useSearchParams();
  const filter = params.get('use') || 'All';
  const [state, setState] = useState('loading');
  const [listings, setListings] = useState([]);

  useEffect(() => {
    let active = true;
    setState('loading');
    phase2('/api/v2/listings').then(({ response, body }) => {
      if (!active) return;
      if (!response.ok) {
        setState('unavailable');
        return;
      }
      setListings(body.listings || []);
      setState('ready');
    }).catch(() => { if (active) setState('unavailable'); });
    return () => { active = false; };
  }, []);

  const visible = listings.filter((item) => filter === 'All' || item.use === filter.toLowerCase());
  return <section id="rentals" className="texture-paper bg-linen py-24 sm:py-28" aria-busy={state === 'loading'}><div className="mx-auto max-w-7xl px-5 sm:px-8">
    <div className="mb-10 flex flex-col justify-between gap-8 lg:flex-row lg:items-end"><div className="max-w-2xl"><p className="kicker-line font-mono text-xs uppercase text-copper">Available rentals</p><h2 className="mt-5 font-heading text-4xl font-bold leading-tight sm:text-5xl">Find a space.<br />Know where you stand.</h2><p className="mt-5 max-w-xl leading-7 text-stone-600">Published homes and commercial spaces from the current inventory.</p></div>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by use">{filters.map((item) => <button key={item} type="button" aria-pressed={filter === item} onClick={() => { const next = new URLSearchParams(params); next.set('use', item); setParams(next, { preventScrollReset: true }); }} className={`border px-4 py-3 text-sm font-semibold transition-colors ${filter === item ? 'border-obsidian bg-obsidian text-linen' : 'border-stone-400 bg-white text-stone-700 hover:border-copper'}`}>{item}</button>)}</div>
    </div>
    {state === 'loading' && <p className="py-16 text-stone-600" role="status">Loading published listings.</p>}
    {state === 'unavailable' && <div className="border border-stone-300 bg-white p-8" role="alert"><h3 className="font-heading text-2xl">Listings are unavailable.</h3><p className="mt-3 text-stone-600">The public inventory could not be loaded. Nothing from the foundation preview is shown in its place.</p><button type="button" className="mt-5 underline" onClick={() => window.location.reload()}>Try again</button></div>}
    {state === 'ready' && !visible.length && <p className="py-16 text-stone-600" role="status">No published spaces match this selection.</p>}
    {state === 'ready' && <p className="mb-5 border-y border-stone-300 py-4 text-xs text-stone-600">{visible.length} published {visible.length === 1 ? 'space' : 'spaces'}</p>}
    <div className="grid gap-7 lg:grid-cols-2">{visible.map((listing) => <article key={listing.listing_id} className="overflow-hidden border border-stone-200 bg-white">
      <Link to={`/rentals/${listing.listing_id}`} className="block bg-obsidian px-6 py-10 text-linen"><p className="text-xs uppercase tracking-widest text-gold">{listing.municipality}, {listing.state}</p><h3 className="mt-3 font-heading text-3xl">{listing.property_name}</h3><p className="mt-2">{listing.label} · {listing.use}</p></Link>
      <div className="p-6"><p className="text-xs font-semibold capitalize text-copper">{listing.use} · {listing.availability}</p><p className="mt-4 font-heading text-3xl font-bold">{moneyMinor(listing.amount_minor, listing.currency)}<span className="font-body text-sm text-stone-600"> / month</span></p><Link className="mt-6 inline-flex items-center gap-2 underline" to={`/rentals/${listing.listing_id}`}>View this listing <ArrowUpRight size={16} /></Link></div>
    </article>)}</div>
  </div></section>;
};
