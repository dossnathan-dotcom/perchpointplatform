import { useState } from "react";
import axios from "axios";
import { ArrowRight, Home, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const Valuation = () => {
  const [form, setForm] = useState({
    address: "",
    property_type: "single_family",
    beds: 3,
    baths: 2,
    condition: "well_kept",
    email: "",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/valuation`, {
        ...form,
        beds: Number(form.beds),
        baths: Number(form.baths),
        email: form.email || undefined,
      });
      setResult(data);
      toast.success("Your Cincinnati valuation range is ready.");
    } catch (error) {
      toast.error("Please complete the required valuation details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="valuation" className="texture-paper bg-linen py-24 sm:py-32">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div>
          <p className="kicker-line font-mono text-xs uppercase tracking-[0.3em] text-copper">Seller advantage</p>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-obsidian sm:text-5xl">
            What is your Cincinnati home worth right now?
          </h2>
          <p className="mt-6 max-w-xl text-base leading-8 text-stone-600">
            Get an instant preliminary range, then let a HawkVision advisor refine it with private comps, buyer demand, and street-level condition context.
          </p>
          {result && (
            <div className="mt-8 rounded-[1.75rem] border border-copper/25 bg-white p-7 shadow-xl shadow-stone-200/50" data-testid="valuation-result-card">
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-copper">{result.confidence}</p>
              <div className="mt-3 font-heading text-4xl font-bold text-obsidian">
                {money.format(result.estimate_low)} – {money.format(result.estimate_high)}
              </div>
              <p className="mt-4 text-sm leading-6 text-stone-600">{result.message}</p>
            </div>
          )}
        </div>

        <form onSubmit={submit} className="rounded-[2rem] border border-stone-200 bg-white p-6 shadow-2xl shadow-stone-200/60 sm:p-8" data-testid="valuation-form">
          <div className="mb-7 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-copper/10 text-copper">
              <Home className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-heading text-2xl font-bold text-obsidian">Instant valuation</h3>
              <p className="text-sm text-stone-500">No obligation. Local advisor follow-up only if requested.</p>
            </div>
          </div>

          <div className="grid gap-5">
            <label className="grid gap-2 text-sm font-semibold text-stone-700">
              Property address
              <Input required placeholder="1234 Observatory Ave, Cincinnati, OH" value={form.address} onChange={(event) => update("address", event.target.value)} data-testid="valuation-address-input" />
            </label>
            <div className="grid gap-5 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-semibold text-stone-700">
                Property type
                <select className="h-10 rounded-md border border-input bg-white px-3 text-sm" value={form.property_type} onChange={(event) => update("property_type", event.target.value)} data-testid="valuation-property-type-select">
                  <option value="single_family">Single-family home</option>
                  <option value="condo">Condo / penthouse</option>
                  <option value="luxury_estate">Luxury estate</option>
                  <option value="multi_family">Multi-family</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm font-semibold text-stone-700">
                Condition
                <select className="h-10 rounded-md border border-input bg-white px-3 text-sm" value={form.condition} onChange={(event) => update("condition", event.target.value)} data-testid="valuation-condition-select">
                  <option value="needs_work">Needs work</option>
                  <option value="well_kept">Well kept</option>
                  <option value="updated">Updated</option>
                  <option value="renovated">Fully renovated</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm font-semibold text-stone-700">
                Beds
                <Input type="number" min="0" max="20" value={form.beds} onChange={(event) => update("beds", event.target.value)} data-testid="valuation-beds-input" />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-stone-700">
                Baths
                <Input type="number" min="0" max="20" step="0.5" value={form.baths} onChange={(event) => update("baths", event.target.value)} data-testid="valuation-baths-input" />
              </label>
            </div>
            <label className="grid gap-2 text-sm font-semibold text-stone-700">
              Email for full report (optional)
              <Input type="email" placeholder="you@example.com" value={form.email} onChange={(event) => update("email", event.target.value)} data-testid="valuation-email-input" />
            </label>
            <Button disabled={loading} className="h-12 rounded-full bg-obsidian text-linen hover:bg-copper" data-testid="valuation-estimate-btn">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
              Get My Instant Estimate
            </Button>
          </div>
        </form>
      </div>
    </section>
  );
};
