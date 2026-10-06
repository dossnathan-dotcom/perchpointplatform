import { useEffect, useState } from "react";
import { phase2 } from "@/api/phase2";

export function PortfolioAdmin() {
  const [state, setState] = useState("loading");
  const [records, setRecords] = useState([]);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    phase2("/api/v2/portfolio/inventory").then(({ response, body }) => {
      if (!active) return;
      if (response.status === 401 || response.status === 403) {
        setState("denied");
        return;
      }
      if (!response.ok) {
        setState("error");
        return;
      }
      setRecords(body.records || []);
      setState(body.records?.length ? "ready" : "empty");
    }).catch(() => { if (active) setState("error"); });
    return () => { active = false; };
  }, []);

  return (
    <main id="main" data-testid="listing-administration" className="min-h-screen bg-linen px-4 py-8 text-obsidian sm:px-8" style={{ colorScheme: "light" }}>
      <h1 className="font-heading text-3xl font-bold">Portfolio administration</h1>
      <p className="mt-2 max-w-2xl text-sm">EXAMPLE ONLY. Canonical property facts, pricing, and publication stay on the server. This workspace does not syndicate listings.</p>
      {state === "loading" && <p role="status" className="mt-6">Loading portfolio.</p>}
      {state === "denied" && <p role="alert" className="mt-6">You do not have authority to administer this portfolio.</p>}
      {state === "error" && <p role="alert" className="mt-6">Portfolio inventory could not be loaded. Safe drafts remain available after the service recovers.</p>}
      {state === "empty" && <p className="mt-6">No properties are visible in this scope.</p>}
      {state === "ready" && (
        <table className="mt-6 w-full border-collapse text-left text-sm">
          <caption className="sr-only">Properties and spaces in scope</caption>
          <thead>
            <tr>
              <th className="border-b py-2" scope="col">Property</th>
              <th className="border-b py-2" scope="col">Space</th>
              <th className="border-b py-2" scope="col">Lifecycle</th>
              <th className="border-b py-2" scope="col">Publication</th>
            </tr>
          </thead>
          <tbody>
            {records.map((row) => (
              <tr key={`${row.property_id}-${row.space_id}`}>
                <td className="border-b py-2">{row.name}</td>
                <td className="border-b py-2">{row.label}</td>
                <td className="border-b py-2">{row.lifecycle}</td>
                <td className="border-b py-2">{row.publication || "unpublished"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form className="mt-8 max-w-xl space-y-4" onSubmit={(event) => { event.preventDefault(); setNotice("High-impact changes are confirmed on the server. This form does not publish locally."); }}>
        <h2 className="font-heading text-2xl">Prepare a routine price</h2>
        <label className="block">Space reference<input className="mt-1 w-full border border-stone-500 bg-white px-3 py-2 text-obsidian" name="space" required /></label>
        <label className="block">Amount in cents<input className="mt-1 w-full border border-stone-500 bg-white px-3 py-2 text-obsidian" name="amount" inputMode="numeric" required /></label>
        <label className="block">Reason<textarea className="mt-1 w-full border border-stone-500 bg-white px-3 py-2 text-obsidian" name="reason" required /></label>
        <button className="bg-obsidian px-4 py-3 text-linen" type="submit">Review on the server</button>
        <p role="status">{notice}</p>
      </form>
    </main>
  );
}
