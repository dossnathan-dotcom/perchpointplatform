import { useEffect, useState } from "react";
import { Workspace } from "@/components/demo/RoleNav";

const links = [["Assistance", "/payments/assistance"], ["Reconciliation", "/payments/reconciliation"], ["Owner", "/owner"]];

function csrfToken() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

function money(minor) {
  return (Number(minor || 0) / 100).toLocaleString(undefined, { style: "currency", currency: "USD" });
}

export function ReconciliationDesk() {
  const [briefing, setBriefing] = useState(null);
  const [items, setItems] = useState([]);
  const [view, setView] = useState("loading");
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");

  async function load(search) {
    setView("loading");
    try {
      const [briefingResponse, queueResponse] = await Promise.all([
        fetch("/api/v2/payments/reconciliation/briefing", { credentials: "include" }),
        fetch(`/api/v2/payments/reconciliation/queue?q=${encodeURIComponent(search || "")}`, { credentials: "include" }),
      ]);
      if (briefingResponse.status === 401 || queueResponse.status === 401) {
        setView("unavailable");
        return;
      }
      if (briefingResponse.status === 403 || queueResponse.status === 403) {
        setView("denied");
        return;
      }
      if (!briefingResponse.ok || !queueResponse.ok) {
        setView("error");
        return;
      }
      setBriefing(await briefingResponse.json());
      const queue = await queueResponse.json();
      setItems(queue.items || []);
      setView(queue.empty ? "empty" : "ready");
    } catch {
      setView("error");
    }
  }

  useEffect(() => { load(""); }, []);

  async function acknowledge() {
    const response = await fetch("/api/v2/payments/reconciliation/acknowledgements", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json", "x-perchpoint-csrf": csrfToken() },
      body: JSON.stringify({ snapshot_reference: briefing.reference, idempotency_key: `ack-${briefing.reference}` }),
    });
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok && body.resolved === false ? "Acknowledged. This snapshot is not resolved." : "The acknowledgement was not recorded.");
  }

  async function claim(item) {
    const response = await fetch("/api/v2/payments/reconciliation/claims", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json", "x-perchpoint-csrf": csrfToken() },
      body: JSON.stringify({ line_reference: item.public_reference, version: item.version, idempotency_key: `claim-${item.public_reference}-${item.version}` }),
    });
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok ? `Owned at version ${body.version}.` : (body.detail?.message || "That item could not be claimed."));
    if (response.ok) load(query);
  }

  return (
    <Workspace links={links}>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="font-heading text-3xl font-bold">Reconciliation</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6">Bank and processor rows are evidence. They do not post a resident or assistance amount again. An acknowledgement is not a resolution.</p>
        {view === "loading" ? <p role="status">Loading reconciliation.</p> : null}
        {view === "denied" ? <p role="alert">You are not allowed to view reconciliation.</p> : null}
        {view === "unavailable" ? <p role="status">Sign in to view reconciliation.</p> : null}
        {view === "error" ? <p role="alert">Reconciliation could not be loaded.</p> : null}
        {briefing ? (
          <section className="mt-6" aria-labelledby="briefing-heading">
            <h2 id="briefing-heading" className="font-heading text-2xl font-bold">One briefing snapshot</h2>
            {briefing.refresh_failed ? <p role="status">The latest refresh failed. These figures are the previous snapshot, not zeros.</p> : null}
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <div><dt>Owed</dt><dd>{money(briefing.owed_minor)}</dd></div>
              <div><dt>Processing</dt><dd>{money(briefing.processing_minor)}</dd></div>
              <div><dt>Paid out</dt><dd>{money(briefing.paid_out_minor)}</dd></div>
              <div><dt>At the bank</dt><dd>{money(briefing.at_bank_minor)}</dd></div>
              <div><dt>Sycamore House</dt><dd>{money(briefing.october?.sycamore_minor)}</dd></div>
              <div><dt>Brookside House</dt><dd>{money(briefing.october?.brookside_minor)}</dd></div>
              <div><dt>{briefing.october?.maple_court_101_resident} at Maple Court 101</dt><dd>{money(briefing.october?.maple_court_101_due_minor)} due</dd></div>
            </dl>
            <p className="mt-3 text-sm">{briefing.stale_sources?.length ? `${briefing.stale_sources.length} stale source.` : "No stale source in this snapshot."}</p>
            <button className="mt-4 min-h-11 underline" type="button" onClick={acknowledge}>Acknowledge this snapshot</button>
          </section>
        ) : null}
        <form className="mt-8 flex flex-wrap gap-3" onSubmit={(event) => { event.preventDefault(); load(query); }}>
          <label className="flex flex-col text-sm">Search
            <input className="mt-1 min-h-11 border border-stone-400 px-3" value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <button className="min-h-11 self-end underline" type="submit">Search the queue</button>
        </form>
        {view === "empty" ? <p role="status">No residuals, unknown inflows, or internal transfers match this search.</p> : null}
        {items.length ? (
          <div className="mt-4 overflow-x-auto">
          <table className="w-full bg-white text-left">
            <caption className="sr-only">Reconciliation queue</caption>
            <thead><tr><th scope="col">Item</th><th scope="col">Kind</th><th scope="col">Amount</th><th scope="col">Action</th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.public_reference}>
                  <td>{item.external_id}</td>
                  <td>{item.kind}</td>
                  <td>{money(item.amount_minor)}</td>
                  <td><button className="underline" type="button" onClick={() => claim(item)}>Take ownership</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : null}
        {message ? <p role="status">{message}</p> : null}
      </main>
    </Workspace>
  );
}
