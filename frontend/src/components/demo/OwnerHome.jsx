import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Workspace, staffLinks } from "@/components/demo/RoleNav";

function csrfToken() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

function OwnerMaintenance() {
  const [briefing, setBriefing] = useState(null);
  useEffect(() => {
    fetch("/api/v2/maintenance/briefing", { credentials: "include" }).then(async (response) => {
      if (response.ok) setBriefing(await response.json());
    }).catch(() => setBriefing(null));
  }, []);
  if (!briefing) return null;
  const items = [...(briefing.blocked || []), ...(briefing.decisions_needed || [])];
  return (
    <section className="mt-8" aria-labelledby="maintenance-heading">
      <h2 id="maintenance-heading" className="font-heading text-2xl font-bold">Maintenance</h2>
      <p className="mt-2 text-sm">{briefing.queue_count} open requests use the same queue as operations. Nothing here moves money.</p>
      {items.length === 0 ? <p>No maintenance decision is waiting.</p> : null}
      <ul className="mt-3 space-y-2">
        {items.map((item) => (
          <li key={`${item.public_reference}-${item.kind || item.summary}`} className="bg-white p-3">
            <Link className="underline" to="/maintenance">{item.place_label || item.kind} · {item.public_reference}</Link>
            <p>{item.severity || item.reason} · {item.summary || "blocked"}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function OwnerCalls() {
  const [desk, setDesk] = useState(null);
  const [state, setState] = useState("loading");
  useEffect(() => {
    fetch("/api/v2/calls/desk", { credentials: "include" }).then(async (response) => {
      if (response.ok) {
        setDesk(await response.json());
        setState("ready");
      } else setState("unavailable");
    }).catch(() => setState("unavailable"));
  }, []);
  return (
    <section className="mt-8" aria-labelledby="calls-heading">
      <h2 id="calls-heading" className="font-heading text-2xl font-bold">Calls needing follow-up</h2>
      {state === "loading" ? <p role="status">Loading call follow-up.</p> : null}
      {state === "unavailable" ? <p role="status">Call follow-up is unavailable. This is not zero calls.</p> : null}
      {state === "ready" ? (
        <ul className="mt-3 space-y-2">
          {(desk.callbacks || []).map((item) => (
            <li key={`${item.public_reference}-${item.state}`} className="bg-white p-3">
              <Link className="underline" to="/calls">{item.public_reference}</Link>
              <p>{item.state} · {item.reason}</p>
            </li>
          ))}
          {(desk.callbacks || []).length === 0 ? <li>No callback is due.</li> : null}
        </ul>
      ) : null}
      <p className="mt-2 text-sm">Budget, purchasing, and document sources are not available in this phase. They are not shown as zero.</p>
    </section>
  );
}

function OwnerExceptions() {
  const [rows, setRows] = useState([]);
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  function load() {
    fetch("/api/v2/payments/refunds/exceptions", { credentials: "include" }).then(async (response) => {
      const body = await response.json().catch(() => ({}));
      if (response.ok) setRows(body.exceptions || []);
      else setNote(body.detail?.message || "Owner refund decisions could not be loaded.");
    }).catch(() => setNote("Owner refund decisions could not be loaded."));
  }
  useEffect(() => { load(); }, []);
  async function approve(row) {
    const response = await fetch("/api/v2/payments/refunds/exceptions", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json", "x-perchpoint-csrf": csrfToken() },
      body: JSON.stringify({
        reference: row.public_reference,
        amount_minor: row.amount_minor,
        reason,
        idempotency_key: `owner-${row.public_reference}-${Date.now()}`,
      }),
    });
    const body = await response.json().catch(() => ({}));
    setNote(response.ok ? "The exact exception was recorded. The ordinary cap was not reset." : (body.detail?.message || "The exception was not approved."));
    if (response.ok) load();
  }
  return (
    <section className="mt-8" aria-labelledby="exception-heading">
      <h2 id="exception-heading" className="font-heading text-2xl font-bold">Owner refund decisions</h2>
      <p className="mt-2 text-sm">An approval covers one exact case. It does not reset the ordinary monthly refund cap, and it cannot refund more than the source payment still holds.</p>
      {rows.length === 0 ? <p>No refund is waiting for an owner decision.</p> : null}
      <label className="mt-3 block">Reason for an exact exception
        <textarea className="mt-1 w-full border border-stone-300 px-3 py-2" minLength={8} value={reason} onChange={(event) => setReason(event.target.value)} />
      </label>
      <ul className="mt-3 space-y-2">
        {rows.map((row) => (
          <li key={row.public_reference} className="flex flex-wrap items-center justify-between gap-3 bg-white p-3">
            <span>{row.tenancy_code}: {(row.amount_minor / 100).toLocaleString(undefined, { style: "currency", currency: "USD" })} — {row.description}</span>
            <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="button" onClick={() => approve(row)}>Approve exact amount</button>
          </li>
        ))}
      </ul>
      {note ? <p role="status">{note}</p> : null}
    </section>
  );
}

export function OwnerHome() {
  const [status, setStatus] = useState("loading");
  const [owner, setOwner] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    fetch("/api/v2/demo/owner", { credentials: "include" }).then(async (response) => {
      const body = await response.json().catch(() => ({}));
      if (!active) return;
      if (response.ok) {
        setOwner(body);
        setStatus("ready");
        return;
      }
      setMessage(body.detail?.message || "The owner workspace could not be opened.");
      setStatus(response.status === 403 ? "denied" : "signed-out");
    }).catch(() => { if (active) setStatus("unavailable"); });
    return () => { active = false; };
  }, []);

  return (
    <Workspace links={staffLinks}>
    <main id="main" className="min-h-screen bg-[#F3F6FB] text-[#172B4D]">
      <div className="bg-[#142538] px-5 py-8 text-white">
        <p className="font-mono text-xs uppercase tracking-widest text-gold">Synthetic local demo</p>
        <h1 className="mt-3 font-heading text-4xl font-bold">Owner workspace</h1>
        <p className="mt-3 max-w-2xl text-linen/80">HawkVision Homes — synthetic organization. This account is only the owner. It cannot switch into the resident or technical operator.</p>
        <p className="mt-4"><Link className="underline" to="/demo">Return to the Demo Control Center</Link></p>
        <p className="mt-2"><Link className="underline" to="/payments/assistance">Review digital payments and assistance</Link></p>
      </div>
      <div className="mx-auto max-w-6xl px-5 py-8">
        {status === "loading" && <p role="status">Loading the owner workspace.</p>}
        {status === "unavailable" && <p role="alert">The owner workspace could not be loaded. <button className="underline" type="button" onClick={() => window.location.reload()}>Try again</button></p>}
        {(status === "signed-out" || status === "denied") && <p role="status">{message} <Link className="underline" to="/demo">Open the Demo Control Center</Link></p>}
        {status === "ready" && owner && (
          <>
            <p className="max-w-3xl leading-7">{owner.briefing}</p>
            <p className="mt-2 text-sm text-stone-600">Signed in as {owner.email}</p>
            <ul className="mt-6 grid gap-4 md:grid-cols-3">
              {owner.cards.map((card) => (
                <li key={card.label} className="border border-stone-300 bg-white p-5 shadow-sm">
                  <h2 className="font-heading text-xl font-bold">{card.label}</h2>
                  <p className="mt-2 text-2xl text-copper">{card.value}</p>
                  <p className="mt-2 text-sm leading-6">{card.detail}</p>
                  <Link className="mt-4 inline-flex min-h-11 items-center underline" to={card.href}>{card.action || "Open"}</Link>
                </li>
              ))}
            </ul>
            <section className="mt-8" aria-labelledby="attention-heading">
              <h2 id="attention-heading" className="font-heading text-2xl font-bold">Needs a decision or a balance review</h2>
              <p className="mt-2 text-sm">As of {owner.as_of}. Past-due, partial, and disputed accounts from the same 20-household cohort.</p>
              <table className="mt-4 w-full bg-white text-left">
                <caption className="sr-only">Accounts that need attention</caption>
                <thead>
                  <tr><th scope="col">Household</th><th scope="col">Home</th><th scope="col">Status</th><th scope="col">Amount due</th><th scope="col">Action</th></tr>
                </thead>
                <tbody>
                  {(owner.attention || []).map((row) => (
                    <tr key={row.slug}>
                      <td>{row.person_label}</td>
                      <td>{row.home_label}</td>
                      <td>{row.status}</td>
                      <td>{(row.due_minor / 100).toLocaleString(undefined, { style: "currency", currency: "USD" })}</td>
                      <td><Link className="underline" to={`/owner/accounts/${row.slug}`}>Review {row.home_label}</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <p className="mt-6"><Link className="underline" to="/payments/reconciliation">Open the financial briefing</Link></p>
            <OwnerMaintenance />
            <OwnerCalls />
            <OwnerExceptions />
          </>
        )}
      </div>
    </main>
    </Workspace>
  );
}
