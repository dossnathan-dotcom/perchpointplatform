import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const STATE_LABEL = {
  implemented: "Implemented",
  implemented_synthetic_provider: "Implemented with a synthetic provider",
  preview: "Existing surface, production workflow not open",
  intentionally_disabled: "Intentionally closed",
};

export function DemoControl() {
  const [status, setStatus] = useState("loading");
  const [personas, setPersonas] = useState([]);
  const [features, setFeatures] = useState([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    let active = true;
    fetch("/api/v2/demo/status").then(async (response) => {
      if (!active) return;
      if (response.status === 404) {
        setStatus("closed");
        return;
      }
      if (!response.ok) {
        setStatus("unavailable");
        return;
      }
      const [people, inventory] = await Promise.all([
        fetch("/api/v2/demo/personas").then((item) => item.json()),
        fetch("/api/v2/demo/features").then((item) => item.json()),
      ]);
      if (!active) return;
      setPersonas(people.personas || []);
      setFeatures(inventory.features || []);
      setStatus("ready");
    }).catch(() => { if (active) setStatus("unavailable"); });
    return () => { active = false; };
  }, []);

  async function enter(persona) {
    setBusy(persona.id);
    setMessage("");
    try {
      const csrf = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
      const response = await fetch("/api/v2/demo/enter", {
        method: "POST",
        credentials: "include",
        headers: {
          "content-type": "application/json",
          "x-perchpoint-csrf": csrf ? decodeURIComponent(csrf.split("=").slice(1).join("=")) : "",
        },
        body: JSON.stringify({ persona: persona.id }),
      });
      const body = await response.json();
      if (!response.ok) {
        setMessage(body.detail?.message || "That workspace could not be opened.");
        return;
      }
      const now = String(Date.now());
      sessionStorage.clear();
      sessionStorage.setItem("pp_session_started_at", now);
      sessionStorage.setItem("pp_session_last_authorized_at", now);
      sessionStorage.setItem("pp_active_context", JSON.stringify({
        organization_id: body.organization_id,
        role_name: body.role,
        assurance: body.assurance,
      }));
      window.location.assign(body.workspace);
    } catch {
      setMessage("The local demo service is unavailable.");
    } finally {
      setBusy("");
    }
  }

  if (status === "loading") return <main id="main" className="min-h-screen bg-linen px-6 py-16"><p role="status">Loading the demo control center.</p></main>;
  if (status === "closed") return <main id="main" className="min-h-screen bg-linen px-6 py-16"><h1 className="font-heading text-4xl">This demo is not available.</h1><p className="mt-4">The control center is closed in this environment.</p><Link className="mt-6 inline-block underline" to="/">Return home</Link></main>;
  if (status === "unavailable") return <main id="main" className="min-h-screen bg-linen px-6 py-16" role="alert"><h1 className="font-heading text-4xl">The demo control center is unavailable.</h1><button className="mt-6 underline" type="button" onClick={() => window.location.reload()}>Try again</button></main>;

  const openFeatures = features.filter((feature) => feature.executable);
  return (
    <main id="main" className="min-h-screen bg-linen px-5 py-10 text-obsidian">
      <p className="bg-obsidian px-4 py-3 text-sm text-linen" role="status">Synthetic local demo. No live provider, payment, or executable document is active.</p>
      <div className="mx-auto max-w-6xl">
        <p className="mt-8 font-mono text-xs uppercase tracking-widest text-copper">HawkVision Homes</p>
        <h1 className="mt-3 font-heading text-4xl font-bold">Demo Control Center</h1>
        <p className="mt-3 max-w-2xl">Each card opens a separate server-issued session. Leaving one persona ends that session before the next one starts. The same addresses can also use normal sign-in. The local password lives only in the ignored <span className="font-mono">backend/.env.demo.local</span> file. Change that file and restart the API to rotate it. Outbound email is not sent.</p>
        {message && <p className="mt-4" role="alert">{message}</p>}
        <section className="mt-8" aria-labelledby="persona-heading">
          <h2 id="persona-heading" className="font-heading text-2xl font-bold">Personas</h2>
          <ul className="mt-4 grid gap-4 md:grid-cols-2">
            {personas.map((persona) => (
              <li key={persona.id} className="border border-stone-300 bg-white p-5">
                <h3 className="font-heading text-xl font-bold">{persona.title}</h3>
                <p className="mt-2 text-sm leading-6">{persona.summary}</p>
                <p className="mt-2 text-sm text-stone-600">{persona.email}</p>
                <p className="text-sm text-stone-600">HawkVision Homes — synthetic organization</p>
                <button className="mt-4 min-h-11 bg-obsidian px-4 py-2 text-linen disabled:opacity-60" type="button" disabled={busy === persona.id} onClick={() => enter(persona)}>
                  {busy === persona.id ? "Opening workspace" : "Enter workspace"}
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section className="mt-12" aria-labelledby="explorer-heading">
          <h2 id="explorer-heading" className="font-heading text-2xl font-bold">Feature Explorer</h2>
          <p className="mt-2 text-sm">{openFeatures.length} implemented entries can be opened. Closed capabilities stay visible and cannot run.</p>
          <ul className="mt-4 divide-y divide-stone-200 border border-stone-300 bg-white">
            {features.map((feature) => (
              <li key={feature.name} className="grid gap-2 px-4 py-4 md:grid-cols-[1.2fr_0.8fr_1fr]">
                <div>
                  <h3 className="font-semibold">{feature.name}</h3>
                  <p className="text-sm text-stone-600">Phase {feature.phase} · {feature.scenario}</p>
                </div>
                <p className="text-sm">{STATE_LABEL[feature.state] || feature.state}</p>
                <div className="text-sm">
                  <p>{feature.boundary}</p>
                  {feature.executable && feature.persona && (
                    <button className="mt-2 min-h-11 underline" type="button" onClick={() => enter(personas.find((item) => item.id === feature.persona))}>Open with {feature.persona.replaceAll("_", " ")}</button>
                  )}
                  {feature.executable && !feature.persona && feature.route && <Link className="mt-2 inline-flex min-h-11 items-center underline" to={feature.route}>Open</Link>}
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}
