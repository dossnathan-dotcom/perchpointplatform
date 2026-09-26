import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Building, Pause, Play, Search, Wrench } from 'lucide-react';
import { HEADLINES, IMAGES } from '@/data/siteData';
import { Button } from '@/components/ui/button';
import { DemoNotice } from './DemoNotice';

export const Hero = ({ onSchedule, onMaintenance }) => {
  const navigate = useNavigate();
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [filters, setFilters] = useState({ location: 'All locations', use: 'All' });
  useEffect(() => {
    if (paused) return;
    const timer = setInterval(() => setActive((v) => (v + 1) % HEADLINES.length), 8000);
    return () => clearInterval(timer);
  }, [paused]);
  const search = (event) => { event.preventDefault(); navigate(`/?${new URLSearchParams(filters)}#rentals`); document.getElementById('rentals')?.scrollIntoView({ behavior: 'smooth' }); };
  return <section id="top" className="relative overflow-hidden bg-obsidian pt-32 text-linen" aria-label="HawkVision Homes" data-testid="public-hero">
    <img src={IMAGES.hero} alt="Cincinnati skyline and riverfront at dusk" className="absolute inset-0 h-full w-full object-cover" />
    <div className="hero-vignette absolute inset-0" />
    <div className="relative mx-auto max-w-7xl px-5 pb-10 pt-14 sm:px-8 sm:pt-20">
      <p className="mb-6 font-mono text-xs uppercase text-gold" data-testid="hero-brand-badge">HawkVision Homes · Powered by PerchPoint</p>
      <div className="grid max-w-4xl" data-testid="hero-heading-cycle-container">{HEADLINES.map((slide, index) => <div key={slide.title} className={`col-start-1 row-start-1 transition-opacity duration-500 ${active === index ? 'visible opacity-100' : 'invisible opacity-0'}`} aria-hidden={active !== index}>
        {active === index ? <h1 className="font-heading text-4xl font-bold leading-[1.1] sm:text-5xl lg:text-6xl" data-testid="hero-active-heading">{slide.title}</h1> : <p className="font-heading text-4xl font-bold leading-[1.1] sm:text-5xl lg:text-6xl">{slide.title}</p>}
        <p className="mt-6 max-w-2xl text-base leading-8 text-linen" data-testid={`hero-slide-copy-${index}`}>{slide.subtitle}</p>
      </div>)}</div>
      <div className="mt-8 flex flex-wrap gap-3"><Button className="h-12 bg-copper px-6 text-white hover:bg-copperDark" onClick={() => document.getElementById('rentals')?.scrollIntoView({ behavior: 'smooth' })} data-testid="hero-browse-rentals-btn"><Building size={16} />Browse available rentals</Button><Button className="h-12 border border-white/60 bg-obsidian/80 px-6 text-linen hover:bg-obsidian" onClick={onSchedule} data-testid="hero-schedule-showing-btn">Schedule a showing</Button><button className="flex min-h-12 items-center gap-2 px-3 text-sm font-semibold text-linen hover:text-gold" onClick={onMaintenance} data-testid="hero-maintenance-link"><Wrench size={16} />Resident maintenance</button></div>
      <div className="my-7 flex items-center gap-3"><button aria-label="Previous headline" className="hero-control" onClick={() => {setPaused(true);setActive((active + HEADLINES.length - 1) % HEADLINES.length);}} data-testid="hero-heading-prev-btn"><ArrowLeft size={16} /></button><button aria-label="Next headline" className="hero-control" onClick={() => {setPaused(true);setActive((active + 1) % HEADLINES.length);}} data-testid="hero-heading-next-btn"><ArrowRight size={16} /></button><button aria-label={paused ? 'Play headline carousel' : 'Pause headline carousel'} aria-pressed={paused} className="hero-control" onClick={() => setPaused(!paused)} data-testid="hero-pause-btn">{paused ? <Play size={16} /> : <Pause size={16} />}</button><span className="text-xs text-linen" data-testid="hero-slide-position">0{active+1} / 03</span></div>
      <form onSubmit={search} className="grid gap-3 border border-white/30 bg-linen p-4 text-obsidian md:grid-cols-[1fr_1fr_auto]" data-testid="hero-rental-search-form">
        {[['Location', 'location', ['All locations', 'Cincinnati']], ['Space', 'use', ['All', 'Residential', 'Commercial']]].map(([label,key,options]) => <label key={key} className="grid gap-2 px-2 text-xs text-stone-700">{label}<select className="min-h-10 w-full border-b border-stone-400 bg-transparent text-sm font-semibold text-obsidian" value={filters[key]} onChange={(e) => setFilters({...filters,[key]:e.target.value})} data-testid={`hero-search-${key}-select`}>{options.map((o) => <option key={o}>{o}</option>)}</select></label>)}
        <Button className="h-full min-h-12 bg-obsidian px-7 text-linen hover:bg-copper" data-testid="hero-search-submit-btn"><Search size={16} />Search rentals</Button>
      </form><DemoNotice id="hero-demo-notice" className="mt-4 text-xs text-linen" />
    </div>
  </section>;
};