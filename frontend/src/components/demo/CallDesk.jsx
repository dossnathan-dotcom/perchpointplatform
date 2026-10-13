import { useEffect, useState } from "react";
import { Workspace, staffLinks } from "@/components/demo/RoleNav";

function csrfToken() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

async function readJson(response) {
  const body = await response.json().catch(() => ({}));
  return { response, body };
}

export function CallDesk() {
  const [view, setView] = useState("loading");
  const [items, setItems] = useState([]);
  const [callbacks, setCallbacks] = useState([]);
  const [message, setMessage] = useState("");
  const [description, setDescription] = useState("");
  const [hint, setHint] = useState("");

  function load() {
    return fetch("/api/v2/calls/desk", { credentials: "include" })
      .then(readJson)
      .then(({ response, body }) => {
        if (response.status === 401) setView("unavailable");
        else if (response.status === 403) setView("denied");
        else if (!response.ok) setView("error");
        else {
          setItems(body.items || []);
          setCallbacks(body.callbacks || []);
          setView((body.items || []).length === 0 ? "empty" : "ready");
        }
      })
      .catch(() => setView("error"));
  }

  useEffect(() => { load(); }, []);

  async function recordCall(event) {
    event.preventDefault();
    const response = await fetch("/api/v2/calls/manual", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json", "x-perchpoint-csrf": csrfToken() },
      body: JSON.stringify({
        description,
        caller_hint: hint,
        duration_source: "unknown",
        idempotency_key: crypto.randomUUID(),
      }),
    });
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok
      ? `${body.reference} was recorded from a manual note. The phone link is not proof of a connection.`
      : (body.detail?.message || "That call was not recorded."));
    if (response.ok) load();
  }

  return (
    <Workspace links={staffLinks}>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <h1 className="font-heading text-3xl font-bold">Calls</h1>
        <p className="mt-2 text-sm">Ann answers on her existing phone. This desk stores metadata and notes. It does not record audio.</p>
        {view === "loading" ? <p role="status">Loading calls.</p> : null}
        {view === "unavailable" ? <p role="status">Calls are unavailable until you sign in.</p> : null}
        {view === "denied" ? <p role="alert">You are not allowed to open the call desk.</p> : null}
        {view === "error" ? <p role="alert">Calls could not be loaded.</p> : null}
        {view === "empty" ? <p>No calls are waiting.</p> : null}
        <ul className="mt-4 space-y-3">
          {items.map((item) => (
            <li key={item.public_reference} className="bg-white p-4">
              <h2 className="font-semibold">{item.public_reference}</h2>
              <p>{item.mode} · {item.terminal_outcome || "open"} · {item.caller_status}</p>
              <p>{item.human_acknowledged ? "A person accepted the handoff." : "Nobody has accepted this handoff."}</p>
              <p>{item.duration_source === "unknown" ? "Duration unknown." : `${item.duration_kind || "duration"} ${item.duration_seconds ?? ""}`}</p>
            </li>
          ))}
        </ul>
        <section className="mt-6" aria-labelledby="callback-heading">
          <h2 id="callback-heading" className="text-xl font-semibold">Callbacks due</h2>
          {callbacks.length === 0 ? <p>No callback is due.</p> : null}
          <ul>
            {callbacks.map((item) => (
              <li key={`${item.public_reference}-${item.state}`}>{item.public_reference} · {item.state} · {item.reason}</li>
            ))}
          </ul>
        </section>
        <form className="mt-6 space-y-3 bg-white p-4" onSubmit={recordCall}>
          <h2 className="text-xl font-semibold">Record an unintegrated call</h2>
          <p className="text-sm">A tel link does not prove the call connected or how long it lasted.</p>
          <label className="block">Who called? <input className="mt-1 w-full border px-2 py-2" value={hint} onChange={(event) => setHint(event.target.value)} /></label>
          <label className="block">What was said? <textarea className="mt-1 w-full border px-2 py-2" required value={description} onChange={(event) => setDescription(event.target.value)} /></label>
          <button className="bg-[#142538] px-4 py-2 text-white" type="submit">Save call note</button>
        </form>
        {message ? <p role="status" className="mt-4">{message}</p> : null}
      </main>
    </Workspace>
  );
}
