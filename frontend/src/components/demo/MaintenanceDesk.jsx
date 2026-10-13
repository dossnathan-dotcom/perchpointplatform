import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Workspace, residentLinks, staffLinks } from "@/components/demo/RoleNav";
import { ManagedPage } from "@/components/public/PublicSite";

const STATUS = {
  received: "Received",
  reviewed: "Reviewed",
  accepted: "Responsibility accepted",
  visit_planned: "Visit planned",
  completed: "Work completed",
  withdrawn: "Withdrawn",
};

function csrfToken() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

async function readJson(response) {
  const body = await response.json().catch(() => ({}));
  return { response, body };
}

function State({ view }) {
  if (view === "loading") return <p role="status">Loading maintenance.</p>;
  if (view === "unavailable") return <p role="status">Maintenance is unavailable until you sign in.</p>;
  if (view === "denied") return <p role="alert">You are not allowed to open this maintenance view.</p>;
  if (view === "error") return <p role="alert">Maintenance could not be loaded.</p>;
  return null;
}

export function MaintenanceHome() {
  const [desk, setDesk] = useState(null);
  useEffect(() => {
    fetch("/api/v2/maintenance/desk/queue", { credentials: "include" })
      .then((response) => setDesk(response.ok))
      .catch(() => setDesk(false));
  }, []);
  if (desk === null) return <main className="mx-auto max-w-5xl px-4 py-8"><p role="status">Loading maintenance.</p></main>;
  if (!desk) return <ManagedPage slug="maintenance" testId="maintenance-page" />;
  return <MaintenanceDesk />;
}

export function MaintenanceDesk() {
  const [view, setView] = useState("loading");
  const [items, setItems] = useState([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let ignore = false;
    fetch("/api/v2/maintenance/desk/queue", { credentials: "include" })
      .then(readJson)
      .then(({ response, body }) => {
        if (ignore) return;
        if (response.status === 401) setView("unavailable");
        else if (response.status === 403) setView("denied");
        else if (!response.ok) setView("error");
        else {
          setItems(body.items || []);
          setView((body.items || []).length === 0 ? "empty" : "ready");
        }
      })
      .catch(() => { if (!ignore) setView("error"); });
    return () => { ignore = true; };
  }, []);

  async function acknowledge(item) {
    const response = await fetch("/api/v2/maintenance/desk/acknowledge", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json", "x-perchpoint-csrf": csrfToken() },
      body: JSON.stringify({ reference: item.public_reference, version: item.version || 1 }),
    });
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok ? `${item.public_reference} is reviewed. Delivery is not accepted responsibility.` : (body.detail?.message || "That case could not be reviewed."));
  }

  return (
    <Workspace links={staffLinks}>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="font-heading text-3xl font-bold">Maintenance</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6">Triage, unaccepted handoffs, and blockers stay on the same case. A delivered notice is not accepted responsibility, and no payment is created here.</p>
        <State view={view} />
        {view === "empty" ? <p>No request is waiting.</p> : null}
        {view === "ready" ? (
          <ul className="mt-6 space-y-3">
            {items.map((item) => (
              <li key={item.public_reference} className="bg-white p-4">
                <h2 className="font-heading text-xl font-bold">{item.place_label}</h2>
                <p>{item.public_reference} · {STATUS[item.summary] || item.summary} · {item.severity}</p>
                <button className="mt-3 min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="button" onClick={() => acknowledge(item)}>Review</button>
              </li>
            ))}
          </ul>
        ) : null}
        {message ? <p role="status" className="mt-4">{message}</p> : null}
      </main>
    </Workspace>
  );
}

export function TechnicianJobs() {
  const [view, setView] = useState("loading");
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let ignore = false;
    fetch("/api/v2/maintenance/jobs", { credentials: "include" })
      .then(readJson)
      .then(({ response, body }) => {
        if (ignore) return;
        if (response.status === 401) setView("unavailable");
        else if (response.status === 403) setView("denied");
        else if (!response.ok) setView("error");
        else {
          setItems(body.items || []);
          setView((body.items || []).length === 0 ? "empty" : "ready");
        }
      })
      .catch(() => { if (!ignore) setView("error"); });
    return () => { ignore = true; };
  }, []);

  async function post(path, extra) {
    const reference = selected || items[0]?.public_reference;
    if (!reference) return;
    const response = await fetch(path, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json", "x-perchpoint-csrf": csrfToken() },
      body: JSON.stringify({ reference, idempotency_key: `${path}-${reference}-${Date.now()}`, ...extra }),
    });
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok ? "Recorded. Missing location or photos do not reject the time." : (body.detail?.message || "That action was not recorded."));
  }

  function checkIn() {
    if (!navigator.geolocation || !window.isSecureContext) {
      post("/api/v2/maintenance/jobs/location", { outcome: "unsupported" });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      () => post("/api/v2/maintenance/jobs/location", { outcome: "synthetic", latitude: 39.1, longitude: -84.5, accuracy_meters: 20 }),
      () => post("/api/v2/maintenance/jobs/location", { outcome: "denied" }),
      { enableHighAccuracy: false, timeout: 8000 },
    );
  }

  return (
    <Workspace links={staffLinks}>
      <main className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="font-heading text-3xl font-bold">My jobs</h1>
        <p className="mt-2 text-sm leading-6">Time is recorded from the server clock. Location is a separate check-in and does not prove you are at the home.</p>
        <State view={view} />
        {view === "empty" ? <p>No job is assigned to you.</p> : null}
        {view === "ready" ? (
          <>
            <label className="mt-4 block">Current job
              <select className="mt-1 w-full border border-stone-300 px-3 py-2" value={selected} onChange={(event) => setSelected(event.target.value)}>
                {items.map((item) => <option key={item.public_reference} value={item.public_reference}>{item.public_reference} · {item.place_label} · {STATUS[item.summary] || item.summary}</option>)}
              </select>
            </label>
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="button" onClick={() => post("/api/v2/maintenance/jobs/time/start", { category: "on_site" })}>Start time</button>
              <button className="min-h-11 border border-stone-400 px-4 py-2" type="button" onClick={() => post("/api/v2/maintenance/jobs/time/stop", {})}>Stop time</button>
              <button className="min-h-11 border border-stone-400 px-4 py-2" type="button" onClick={checkIn}>Check in location</button>
            </div>
          </>
        ) : null}
        {message ? <p role="status" className="mt-4">{message}</p> : null}
      </main>
    </Workspace>
  );
}

export function ResidentReport() {
  const [danger, setDanger] = useState(false);
  const [description, setDescription] = useState("");
  const [place, setPlace] = useState("");
  const [view, setView] = useState("ready");
  const [message, setMessage] = useState("");

  async function submit(event) {
    event.preventDefault();
    setView("loading");
    const response = await fetch("/api/v2/maintenance/intake", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json", "x-perchpoint-csrf": csrfToken() },
      body: JSON.stringify({
        description,
        place_label: place,
        place_kind: "unit",
        source: "resident",
        urgency: { immediate_danger: danger, human_emergency: danger },
        idempotency_key: crypto.randomUUID(),
      }),
    });
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) setView("unavailable");
    else if (response.status === 403) setView("denied");
    else if (!response.ok) {
      setView("error");
      setMessage(body.detail?.message || "The report was not saved.");
    } else {
      setView("ready");
      setMessage(`${body.reference} is ${STATUS[body.summary] || "received"}. ${body.safety_message || "A photo is not required."}`);
    }
  }

  return (
    <Workspace links={residentLinks}>
      <main className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="font-heading text-3xl font-bold">Report a problem</h1>
        <p className="mt-2 text-sm leading-6">If you are in immediate danger, leave the area and contact local emergency services (911 in the US). This form does not dispatch help. A missing photo does not block the report.</p>
        <State view={view === "ready" ? "idle" : view} />
        <form className="mt-6 space-y-4" onSubmit={submit}>
          <label className="flex min-h-11 items-center gap-3">
            <input type="checkbox" checked={danger} onChange={(event) => setDanger(event.target.checked)} />
            Someone may be in immediate danger, or essential services are failing now
          </label>
          <label className="block">Where is it?
            <input className="mt-1 w-full border border-stone-300 px-3 py-2" required value={place} onChange={(event) => setPlace(event.target.value)} />
          </label>
          <label className="block">What is happening?
            <textarea className="mt-1 w-full border border-stone-300 px-3 py-2" required minLength={8} value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Submit report</button>
        </form>
        {message ? <p role="status" className="mt-4">{message}</p> : null}
        <p className="mt-6"><Link className="underline" to="/portal/requests">My requests</Link></p>
      </main>
    </Workspace>
  );
}

export function ResidentRequests() {
  const [view, setView] = useState("loading");
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();
    fetch("/api/v2/maintenance/mine", { credentials: "include", signal: controller.signal })
      .then(readJson)
      .then(async ({ response, body }) => {
        if (ignore) return;
        if (response.status === 401) setView("unavailable");
        else if (response.status === 403) setView("denied");
        else if (!response.ok) setView("error");
        else {
          setItems(body.items || []);
          setView((body.items || []).length === 0 ? "empty" : "ready");
        }
      })
      .catch((error) => { if (!ignore && error.name !== "AbortError") setView("error"); });
    return () => { ignore = true; controller.abort(); };
  }, []);

  async function open(reference) {
    const generation = reference;
    setSelected({ reference, generation, view: "loading" });
    const response = await fetch(`/api/v2/maintenance/mine/${reference}`, { credentials: "include" });
    const body = await response.json().catch(() => ({}));
    setSelected((current) => {
      if (!current || current.generation !== generation) return current;
      if (response.status === 403) return { reference, generation, view: "denied" };
      if (!response.ok) return { reference, generation, view: "error" };
      return { reference, generation, view: "ready", body };
    });
  }

  return (
    <Workspace links={residentLinks}>
      <main className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="font-heading text-3xl font-bold">My requests</h1>
        <State view={view} />
        {view === "empty" ? <p>You have not reported a problem.</p> : null}
        {view === "ready" ? (
          <ul className="mt-4 space-y-2">
            {items.map((item) => (
              <li key={item.public_reference}>
                <button className="min-h-11 underline" type="button" onClick={() => open(item.public_reference)}>{item.public_reference} · {item.place_label} · {STATUS[item.summary] || item.summary}</button>
              </li>
            ))}
          </ul>
        ) : null}
        {selected?.view === "ready" ? (
          <section className="mt-6 bg-white p-4" aria-live="polite">
            <h2 className="font-heading text-xl font-bold">{selected.body.place_label}</h2>
            <p>{STATUS[selected.body.summary] || selected.body.summary}</p>
            <p>{selected.body.on_the_way ? "A visit is planned." : "Nobody is marked on the way."}</p>
          </section>
        ) : null}
        {selected?.view === "denied" ? <p role="alert">That request is not available to this household.</p> : null}
      </main>
    </Workspace>
  );
}
