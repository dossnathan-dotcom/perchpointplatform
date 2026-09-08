import { Quote } from "lucide-react";
import { TESTIMONIALS } from "@/data/siteData";

export const Testimonials = () => {
  return (
    <section id="results" className="border-y border-white/10 bg-obsidian py-24 text-linen sm:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mb-12 max-w-3xl">
          <p className="kicker-line font-mono text-xs uppercase tracking-[0.3em] text-gold">Proof over promises</p>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight sm:text-5xl">
            Cincinnati clients call it clarity. The market calls it results.
          </h2>
        </div>
        <div className="grid gap-5 lg:grid-cols-3">
          {TESTIMONIALS.map((item, index) => (
            <figure key={item.name} className="rounded-[1.75rem] border border-white/10 bg-white/[0.06] p-7 backdrop-blur transition-colors duration-300 hover:bg-white/[0.09]" data-testid={`testimonial-card-${index + 1}`}>
              <Quote className="mb-6 h-6 w-6 text-gold" />
              <blockquote className="font-heading text-2xl font-semibold leading-9 text-linen">“{item.quote}”</blockquote>
              <figcaption className="mt-8 border-t border-white/10 pt-5">
                <div className="font-semibold">{item.name}</div>
                <div className="mt-1 text-sm text-linen/60">{item.detail}</div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
};
