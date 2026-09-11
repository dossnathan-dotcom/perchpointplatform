import { ArrowUpRight, Award, MapPinned, ShieldCheck } from "lucide-react";
import { IMAGES } from "@/data/siteData";
import { Button } from "@/components/ui/button";

const stats = [
  { value: "14", label: "years advising Cincinnati movers" },
  { value: "$186M", label: "in negotiated residential volume" },
  { value: "97.4%", label: "average list-to-close strength" },
];

export const AgentStory = ({ onBookConsultation }) => {
  return (
    <section id="advisor" className="texture-paper bg-linen py-24 sm:py-32" data-testid="agent-story-section">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div className="relative overflow-hidden rounded-[2.25rem] border border-stone-200 bg-obsidian p-6 text-linen shadow-2xl shadow-stone-300/40">
          <img src={IMAGES.riverfront} alt="Cincinnati hillside and skyline" className="absolute inset-0 h-full w-full object-cover opacity-35" />
          <div className="absolute inset-0 bg-gradient-to-t from-obsidian via-obsidian/60 to-obsidian/20" />
          <div className="relative flex min-h-[560px] flex-col justify-between p-3 sm:p-6">
            <div className="flex h-20 w-20 items-center justify-center rounded-full border border-gold/40 bg-gold/15 font-heading text-3xl font-bold text-gold">
              AR
            </div>
            <div>
              <p className="kicker-line font-mono text-xs uppercase tracking-[0.3em] text-gold">Principal advisor</p>
              <h2 className="mt-5 font-heading text-4xl font-bold tracking-tight sm:text-5xl">Avery Rhodes knows Cincinnati block by block.</h2>
              <p className="mt-5 max-w-xl text-base leading-8 text-linen/70">
                A Cincinnati native and negotiation-first broker, Avery pairs private-market access with plainspoken guidance so clients move quickly without feeling rushed.
              </p>
            </div>
          </div>
        </div>

        <div>
          <p className="kicker-line font-mono text-xs uppercase tracking-[0.3em] text-copper">Local conviction</p>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-obsidian sm:text-5xl">
            The right advisor changes the quality of every decision after it.
          </h2>
          <p className="mt-6 max-w-2xl text-base leading-8 text-stone-600">
            From Mount Adams view premiums to Indian Hill acreage tradeoffs, HawkVision translates street-level detail into a confident buy or sell strategy.
          </p>

          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {stats.map((stat) => (
              <div key={stat.label} className="rounded-3xl border border-stone-200 bg-white p-6 shadow-lg shadow-stone-200/40">
                <div className="font-heading text-4xl font-bold text-obsidian">{stat.value}</div>
                <div className="mt-3 text-sm leading-6 text-stone-500">{stat.label}</div>
              </div>
            ))}
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl border border-copper/20 bg-copper/5 p-6">
              <MapPinned className="mb-4 h-5 w-5 text-copper" />
              <h3 className="font-semibold text-obsidian">Neighborhood fluency</h3>
              <p className="mt-2 text-sm leading-6 text-stone-600">Pricing nuance across Hyde Park, Mount Adams, OTR, Walnut Hills, and Indian Hill.</p>
            </div>
            <div className="rounded-3xl border border-copper/20 bg-copper/5 p-6">
              <Award className="mb-4 h-5 w-5 text-copper" />
              <h3 className="font-semibold text-obsidian">Negotiation discipline</h3>
              <p className="mt-2 text-sm leading-6 text-stone-600">Offer structure, inspection leverage, appraisal strategy, and calm execution.</p>
            </div>
          </div>

          <Button className="mt-9 h-12 rounded-full bg-obsidian px-7 text-linen hover:bg-copper" onClick={onBookConsultation} data-testid="agent-booking-btn">
            <ShieldCheck className="h-4 w-4" />
            Book Avery’s Private Consultation
            <ArrowUpRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </section>
  );
};
