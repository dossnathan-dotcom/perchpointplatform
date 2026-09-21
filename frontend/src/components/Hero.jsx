import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Building, Search, Wrench } from "lucide-react";
import { toast } from "sonner";
import { HEADLINES, IMAGES } from "@/data/siteData";
import { Button } from "@/components/ui/button";

const headingMotion = {
  initial: { opacity: 0, y: 26, filter: "blur(7px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -26, filter: "blur(7px)" },
  transition: { duration: 0.58, ease: [0.16, 1, 0.3, 1] },
};

export const Hero = ({ onSchedule, onMaintenance }) => {
  const [active, setActive] = useState(0);
  const [filters, setFilters] = useState({ location: "Greater Cincinnati", use: "All spaces", timing: "Any availability" });

  useEffect(() => {
    const timer = setInterval(() => setActive((value) => (value + 1) % HEADLINES.length), 5500);
    return () => clearInterval(timer);
  }, []);

  const search = (event) => {
    event.preventDefault();
    document.querySelector("#rentals")?.scrollIntoView({ behavior: "smooth" });
    toast.success(`Showing ${filters.use.toLowerCase()} across ${filters.location}.`);
  };

  const current = HEADLINES[active];
  return (
    <section id="top" className="relative min-h-[94vh] overflow-hidden bg-obsidian pt-20 text-linen">
      <img src={IMAGES.hero} alt="Cincinnati skyline and riverfront at dusk" className="absolute inset-0 h-full w-full object-cover" />
      <div className="hero-vignette absolute inset-0" />
      <div className="texture-grid absolute inset-0 opacity-60" />
      <div className="relative z-10 mx-auto flex min-h-[calc(94vh-5rem)] max-w-7xl flex-col justify-end px-5 pb-10 pt-20 sm:px-8 lg:pb-14">
        <div className="max-w-4xl">
          <div className="mb-7 inline-flex items-center gap-3 rounded-full border border-white/15 bg-black/25 px-4 py-2 backdrop-blur-md" data-testid="hero-brand-badge">
            <span className="h-2 w-2 rounded-full bg-copper" />
            <span className="font-mono text-xs uppercase tracking-[0.22em] text-linen/75">HawkVision Homes · {current.tag}</span>
          </div>
          <div className="min-h-[250px] sm:min-h-[285px]" data-testid="hero-heading-cycle-container">
            <AnimatePresence mode="wait">
              <motion.div key={current.title} {...headingMotion}>
                <p className="kicker-line mb-5 font-mono text-xs uppercase tracking-[0.28em] text-gold">PerchPoint property operations</p>
                <h1 className="headline-shadow max-w-4xl font-heading text-4xl font-bold leading-[1.04] sm:text-6xl lg:text-7xl" data-testid="hero-active-heading">{current.title}</h1>
                <p className="mt-6 max-w-2xl text-base leading-8 text-linen/80 sm:text-lg">{current.subtitle}</p>
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="mb-8 flex flex-wrap gap-3">
            <Button size="lg" className="cta-pulse bg-copper px-7 text-linen hover:bg-copperDark" onClick={() => document.querySelector("#rentals")?.scrollIntoView({ behavior: "smooth" })} data-testid="hero-browse-rentals-btn"><Building className="h-4 w-4" /> Browse available rentals</Button>
            <Button size="lg" variant="outline" className="border-white/25 bg-white/10 px-7 text-linen backdrop-blur hover:bg-white/15 hover:text-linen" onClick={onSchedule} data-testid="hero-schedule-showing-btn">Schedule a showing</Button>
            <button className="flex items-center gap-2 px-2 text-sm font-semibold text-linen/70 hover:text-gold" onClick={onMaintenance} data-testid="hero-maintenance-link"><Wrench className="h-4 w-4" /> Resident maintenance</button>
          </div>

          <div className="mb-8 flex items-center gap-3">
            <button aria-label="Previous headline" className="hero-control" onClick={() => setActive((active + HEADLINES.length - 1) % HEADLINES.length)} data-testid="hero-heading-prev-btn"><ArrowLeft className="h-4 w-4" /></button>
            <button aria-label="Next headline" className="hero-control" onClick={() => setActive((active + 1) % HEADLINES.length)} data-testid="hero-heading-next-btn"><ArrowRight className="h-4 w-4" /></button>
            {HEADLINES.map((item, index) => <button key={item.tag} aria-label={`Show headline ${index + 1}`} className={`h-2 rounded-full transition-[width,background-color] duration-500 ${index === active ? "w-9 bg-gold" : "w-2 bg-white/30"}`} onClick={() => setActive(index)} data-testid={`hero-heading-indicator-${index}`} />)}
          </div>
        </div>

        <form onSubmit={search} className="grid gap-2 border border-white/15 bg-linen/95 p-3 text-obsidian shadow-2xl backdrop-blur md:grid-cols-[1fr_1fr_1fr_auto]" data-testid="hero-rental-search-form">
          {[["Location", "location", ["Greater Cincinnati", "Downtown / OTR", "Clifton"]], ["Space", "use", ["All spaces", "Residential", "Commercial", "Mixed-use"]], ["Timing", "timing", ["Any availability", "Available now", "Available soon"]]].map(([label, key, options], index) => (
            <label key={key} className={`px-3 py-2 ${index ? "md:border-l md:border-stone-200" : ""}`}>
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-stone-500">{label}</span>
              <select className="mt-1 w-full bg-transparent text-sm font-semibold outline-none" value={filters[key]} onChange={(event) => setFilters({ ...filters, [key]: event.target.value })} data-testid={`hero-search-${key}-select`}>
                {options.map((item) => <option key={item}>{item}</option>)}
              </select>
            </label>
          ))}
          <Button className="h-full bg-obsidian px-7 text-linen hover:bg-copper" data-testid="hero-search-submit-btn"><Search className="h-4 w-4" /> Search rentals</Button>
        </form>
      </div>
    </section>
  );
};