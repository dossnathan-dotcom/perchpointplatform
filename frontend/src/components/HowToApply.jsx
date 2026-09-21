import { CalendarCheck, CheckCircle2, FileCheck2, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";

const steps = [
  [CalendarCheck, "01", "Tour the space", "Choose an available unit and schedule a showing with the HawkVision team."],
  [FileCheck2, "02", "Review criteria", "See rent, deposit, fees, utility responsibility, and qualification guidance before paying."],
  [CheckCircle2, "03", "Apply individually", "Each adult applicant submits their own identity, screening consent, and required documents."],
  [KeyRound, "04", "Sign and activate", "Approved households sign attributable documents and receive individual PerchPoint access."],
];

export const HowToApply = ({ onApply }) => (
  <section id="how-to-apply" className="bg-white py-24 sm:py-28">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <div className="max-w-3xl">
        <p className="kicker-line font-mono text-xs uppercase tracking-[0.28em] text-copper">A transparent path home</p>
        <h2 className="mt-5 font-heading text-4xl font-bold leading-tight sm:text-5xl">Know the steps before you start.</h2>
        <p className="mt-5 leading-7 text-stone-600">No hidden brokerage fees. Screening criteria and required documents are presented before an application payment is requested.</p>
      </div>
      <div className="mt-12 grid border-y border-stone-200 md:grid-cols-2 xl:grid-cols-4">
        {steps.map(([Icon, number, title, copy], index) => (
          <article key={title} className={`p-6 sm:p-8 ${index ? "border-t border-stone-200 md:border-l md:border-t-0" : ""}`} data-testid={`application-step-${number}`}>
            <div className="flex items-center justify-between"><Icon className="h-5 w-5 text-copper" /><span className="font-mono text-xs text-stone-400">{number}</span></div>
            <h3 className="mt-10 font-heading text-2xl font-bold">{title}</h3>
            <p className="mt-4 text-sm leading-7 text-stone-600">{copy}</p>
          </article>
        ))}
      </div>
      <Button className="mt-8 bg-obsidian text-linen hover:bg-copper" onClick={onApply} data-testid="how-to-apply-start-btn">Start an application</Button>
    </div>
  </section>
);