import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, ChevronDown, Search } from "lucide-react";
import { toast } from "sonner";
import { HEADLINES, IMAGES } from "@/data/siteData";
import { Button } from "@/components/ui/button";

const headingMotion = {
  initial: { opacity: 0, y: 28, filter: "blur(8px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -28, filter: "blur(8px)" },
  transition: { duration: 0.58, ease: [0.16, 1, 0.3, 1] },
};

export const Hero = ({ onSchedule }) => {
  const [active, setActive] = useState(0);
  const [filters, setFilters] = useState({ neighborhood: "Anywhere", price: "Any price", type: "Any type" });

  useEffect(() => {
    const timer = setInterval(() => setActive((value) => (value + 1) % HEADLINES.length), 5000);
    return () => clearInterval(timer);
  }, []);

  const current = HEADLINES[active];
  const submitSearch = (event) => {
    event.preventDefault();
    document.querySelector("#properties")?.scrollIntoView({ behavior: "smooth" });
    toast.success(`Showing ${filters.neighborhood} homes at ${filters.price.toLowerCase()}.`);
  };

  return (
    <section id="top" className="relative min-h-screen overflow-hidden bg-obsidian pt-20 text-linen">
      <img
        src={IMAGES.hero}
        alt="Cincinnati skyline and riverfront at golden hour"
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="hero-vignette absolute inset-0" />
      <div className="texture-grid absolute inset-0 opacity-70" />
      <div className="grain-overlay absolute inset-0" />

      <div className="relative z-10 mx-auto flex min-h-[calc(100vh-5rem)] max-w-7xl flex-col justify-center px-5 py-20 sm:px-8">
        <div className="max-w-4xl">
          <div className="mb-7 inline-flex items-center gap-3 rounded-full border border-white/15 bg-white/10 px-4 py-2 backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-gold" />
            <span className="font-mono text-xs uppercase tracking-[0.28em] text-linen/75">
              Cincinnati private realty · {current.tag}
            </span>
          </div>

          <div className="min-h-[280px] sm:min-h-[330px]" data-testid="hero-heading-cycle-container">
            <AnimatePresence mode="wait">
              <motion.div key={current.title} {...headingMotion}>
                <p className="kicker-line mb-5 font-mono text-xs uppercase tracking-[0.34em] text-gold">
                  Hawk-eye market vision
                </p>
                <h1
                  className="headline-shadow max-w-4xl font-heading text-4xl font-bold leading-[1.03] tracking-tight sm:text-6xl lg:text-7xl"
                  data-testid="hero-active-heading"
                >
                  {current.title}
                </h1>
                <p className="mt-6 max-w-2xl text-base leading-8 text-linen/80 sm:text-lg">
                  {current.subtitle}
                </p>
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="mb-9 flex flex-wrap items-center gap-4">
            <Button
              size="lg"
              className="cta-pulse rounded-full bg-copper px-7 text-linen hover:bg-copperDark"
              onClick={() => document.querySelector("#properties")?.scrollIntoView({ behavior: "smooth" })}
              data-testid="hero-portfolio-btn"
            >
              Explore Private Portfolio
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="rounded-full border-white/25 bg-white/10 px-7 text-linen backdrop-blur hover:bg-white/15 hover:text-linen"
              onClick={() => document.querySelector("#valuation")?.scrollIntoView({ behavior: "smooth" })}
              data-testid="hero-valuation-btn"
            >
              What Is My Home Worth?
            </Button>
            <button
              className="group flex items-center gap-2 text-sm font-semibold text-linen/70 transition-colors hover:text-gold"
              onClick={onSchedule}
              data-testid="hero-private-tour-link"
            >
              Book a private tour
              <ChevronDown className="h-4 w-4 transition-transform group-hover:translate-y-0.5" />
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              aria-label="Previous headline"
              className="rounded-full border border-white/15 p-2 text-linen/70 transition-colors hover:border-gold hover:text-gold"
              onClick={() => setActive((active + HEADLINES.length - 1) % HEADLINES.length)}
              data-testid="hero-heading-prev-btn"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <button
              aria-label="Next headline"
              className="rounded-full border border-white/15 p-2 text-linen/70 transition-colors hover:border-gold hover:text-gold"
              onClick={() => setActive((active + 1) % HEADLINES.length)}
              data-testid="hero-heading-next-btn"
            >
              <ArrowRight className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-2 pl-2">
              {HEADLINES.map((item, index) => (
                <button
                  key={item.tag}
                  aria-label={`Show headline ${index + 1}`}
                  className={`h-2 rounded-full transition-all duration-500 ${index === active ? "w-9 bg-gold" : "w-2 bg-white/30 hover:bg-white/50"}`}
                  onClick={() => setActive(index)}
                  data-testid={`hero-heading-indicator-${index}`}
                />
              ))}
            </div>
          </div>
        </div>

        <form
          onSubmit={submitSearch}
          className="mt-14 grid gap-3 rounded-3xl border border-white/15 bg-linen/95 p-4 text-obsidian shadow-2xl shadow-black/25 backdrop-blur md:grid-cols-[1fr_1fr_1fr_auto]"
          data-testid="hero-search-form"
        >
          <label className="px-3 py-1">
            <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-stone-500">Neighborhood</span>
            <select
              className="mt-1 w-full bg-transparent text-sm font-semibold outline-none"
              value={filters.neighborhood}
              onChange={(event) => setFilters({ ...filters, neighborhood: event.target.value })}
              data-testid="hero-search-neighborhood-select"
            >
              {['Anywhere', 'Mount Adams', 'Hyde Park', 'Indian Hill', 'Over-The-Rhine'].map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <label className="border-stone-200 px-3 py-1 md:border-l">
            <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-stone-500">Price</span>
            <select
              className="mt-1 w-full bg-transparent text-sm font-semibold outline-none"
              value={filters.price}
              onChange={(event) => setFilters({ ...filters, price: event.target.value })}
              data-testid="hero-search-price-select"
            >
              {['Any price', '$500K – $900K', '$900K – $1.5M', '$1.5M+'].map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <label className="border-stone-200 px-3 py-1 md:border-l">
            <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-stone-500">Estate type</span>
            <select
              className="mt-1 w-full bg-transparent text-sm font-semibold outline-none"
              value={filters.type}
              onChange={(event) => setFilters({ ...filters, type: event.target.value })}
              data-testid="hero-search-type-select"
            >
              {['Any type', 'Historic home', 'Modern estate', 'Penthouse', 'Private acreage'].map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <Button className="h-full rounded-2xl bg-obsidian px-7 text-linen hover:bg-copper" data-testid="hero-search-submit-btn">
            <Search className="h-4 w-4" />
            Search Homes
          </Button>
        </form>
      </div>
    </section>
  );
};
