import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { phase2, moneyMinor } from '@/api/phase2';

export const PropertyDetailPage = () => {
  const { unitId, propertyId } = useParams();
  const listingId = unitId || propertyId;
  const [state, setState] = useState('loading');
  const [listing, setListing] = useState(null);
  const [form, setForm] = useState({ name: '', email: '', message: '', company_website: '' });
  const [notice, setNotice] = useState('');

  useEffect(() => {
    window.scrollTo(0, 0);
    let active = true;
    setState('loading');
    phase2(`/api/v2/listings/${listingId}`).then(({ response, body }) => {
      if (!active) return;
      if (response.status === 404) setState('missing');
      else if (!response.ok) setState('unavailable');
      else { setListing(body); setState('ready'); }
    }).catch(() => { if (active) setState('unavailable'); });
    return () => { active = false; };
  }, [listingId]);

  async function submit(event) {
    event.preventDefault();
    if (!form.name.trim() || !form.email.includes('@') || form.message.trim().length < 2) {
      setNotice('Enter your name, email, and a short message.');
      return;
    }
    if (form.company_website) {
      setNotice('The inquiry was not accepted.');
      return;
    }
    const key = sessionStorage.getItem(`inquiry-${listingId}`) || `web-${listingId}-${Date.now()}`;
    sessionStorage.setItem(`inquiry-${listingId}`, key);
    setNotice('Sending inquiry.');
    const { response, body } = await phase2('/api/v2/inquiries', { method: 'POST', body: JSON.stringify({ listing_id: listingId, name: form.name, email: form.email, intent: 'showing', message: form.message, idempotency_key: key, company_website: form.company_website }) });
    if (response.status === 409) setNotice('This page already sent a different inquiry with the same key. Refresh and try again.');
    else if (!response.ok) setNotice(body.detail?.message || 'The inquiry was not accepted.');
    else setNotice(`Inquiry received. Reference ${body.inquiry_id}. Sending again will not create a duplicate.`);
  }

  if (state === 'loading') return <main className="min-h-screen bg-linen px-6 pb-20 pt-40"><p role="status">Loading listing.</p></main>;
  if (state === 'missing') return <main className="min-h-screen bg-obsidian px-6 pb-20 pt-40 text-linen"><h1 className="font-heading text-4xl">This listing is not public.</h1><p className="mt-4">It may be unpublished, restricted, or unknown.</p><Link className="mt-8 block underline" to="/#rentals">Return to rentals</Link></main>;
  if (state === 'unavailable') return <main className="min-h-screen bg-linen px-6 pb-20 pt-40" role="alert"><h1 className="font-heading text-4xl">This listing is unavailable.</h1><button type="button" className="mt-6 underline" onClick={() => window.location.reload()}>Try again</button></main>;
  return <main>
    <section className="bg-obsidian pb-14 pt-36 text-linen"><div className="mx-auto max-w-7xl px-5 sm:px-8">
      <Link to="/#rentals" className="inline-flex items-center gap-2 py-4 text-sm underline"><ArrowLeft size={16} />All published rentals</Link>
      <p className="mt-6 text-xs uppercase tracking-widest text-gold">{listing.use} · {listing.availability}</p>
      <h1 className="mt-4 font-heading text-5xl font-bold">{listing.property_name}</h1>
      <p className="mt-4">{listing.label} · {listing.municipality}, {listing.state}</p>
      <p className="mt-6 font-heading text-3xl">{moneyMinor(listing.amount_minor, listing.currency)} <span className="font-body text-base">/ month</span></p>
    </div></section>
    <section className="bg-linen py-16"><div className="mx-auto max-w-xl px-5">
      <h2 className="font-heading text-3xl">Request a showing</h2>
      <form className="relative mt-6 space-y-4" onSubmit={submit}>
        <label className="block">Name<input className="mt-1 w-full border px-3 py-2" name="guest-name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
        <label className="block">Email<input className="mt-1 w-full border px-3 py-2" name="guest-email" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></label>
        <label className="block">Message<textarea className="mt-1 w-full border px-3 py-2" name="guest-message" value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} required /></label>
        <div className="absolute -left-[10000px] h-px w-px overflow-hidden" aria-hidden="true"><label>Company website<input name="company_website" tabIndex={-1} autoComplete="off" value={form.company_website} onChange={(event) => setForm({ ...form, company_website: event.target.value })} /></label></div>
        <button className="bg-obsidian px-4 py-3 text-linen" type="submit" data-testid="public-inquiry-submit">Submit inquiry</button>
      </form>
      <p className="mt-4" role="status" data-testid="public-inquiry-status">{notice}</p>
    </div></section>
  </main>;
};
