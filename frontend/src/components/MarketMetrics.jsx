import { Activity, Binoculars, Home, TrendingUp } from "lucide-react";

const metrics = [
  { icon: Activity, value: "18", label: "average days on market", detail: "Cincinnati premium tier" },
  { icon: TrendingUp, value: "$342", label: "median Hyde Park PSF", detail: "+7.8% year over year" },
  { icon: Binoculars, value: "$84M", label: "off-market volume", detail: "tracked by HawkVision advisors" },
  { icon: Home, value: "212", label: "families moved", detail: "buy-side and sell-side combined" },
];

export const MarketMetrics = () => {
  return (
    <section className="border-y border-stone-200 bg-linen py-8">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="overflow-hidden border-y border-stone-200 py-3">
          <div className="marquee-track flex w-max gap-10 font-mono text-xs uppercase tracking-[0.26em] text-stone-500">
            {[...Array(2)].map((_, index) => (
              <span key={index} className="flex gap-10">
                <span>Mount Adams private outlook · strong</span>
                <span>Hyde Park inventory · selective</span>
                <span>Indian Hill acreage · competitive</span>
                <span>OTR penthouses · appointment only</span>
              </span>
            ))}
          </div>
        </div>

        <div className="grid gap-px overflow-hidden rounded-3xl border border-stone-200 bg-stone-200 shadow-xl shadow-stone-200/50 sm:grid-cols-2 lg:grid-cols-4">
          {metrics.map((metric) => (
            <div key={metric.label} className="bg-white p-7 transition-colors duration-300 hover:bg-[#F7EFE8]">
              <metric.icon className="mb-5 h-5 w-5 text-copper" />
              <div className="font-heading text-4xl font-bold text-obsidian">{metric.value}</div>
              <div className="mt-2 text-sm font-semibold text-stone-800">{metric.label}</div>
              <div className="mt-1 text-sm text-stone-500">{metric.detail}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
