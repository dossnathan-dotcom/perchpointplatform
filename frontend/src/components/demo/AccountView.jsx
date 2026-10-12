import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Workspace, staffLinks } from "@/components/demo/RoleNav";

export function money(minor) {
  const value = Number(minor || 0) / 100;
  return value.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

export function StatementBody({ account }) {
  return (
    <article className="space-y-6">
      <img src={account.hero} alt="" className="aspect-video w-full rounded-md object-cover" />
      <section className="rounded-md border border-stone-300 bg-white p-5">
        <h2 className="font-heading text-2xl font-bold">{account.person_label}</h2>
        <p>{account.home_label}</p>
        <p>Lease {account.lease_start} to {account.lease_end}. Rent is due on the first of the month.</p>
        <p className="mt-3 text-sm">{account.sample_marker}</p>
      </section>
      <section className="rounded-md border border-stone-300 bg-white p-5" aria-labelledby="balance-heading">
        <h2 id="balance-heading" className="font-heading text-2xl font-bold">Account as of {account.as_of}</h2>
        <p>Amount due {money(account.due_minor)}. Past due {money(account.past_due_minor)}. Unapplied credit {money(account.credit_minor)}. Disputed {money(account.disputed_minor)}.</p>
        <p className="mt-2 text-sm">{account.statement_marker}</p>
        <p className="mt-3 flex flex-wrap gap-4">
          <a className="underline" href={`/api/v2/demo/documents/${account.slug}/lease`}>View sample lease</a>
          <a className="underline" href={`/api/v2/demo/documents/${account.slug}/statement`}>View October statement</a>
        </p>
        <p className="text-sm">No money has moved. A synthetic settlement is not cash received.</p>
        <table className="mt-4 w-full text-left">
          <caption className="sr-only">October 2026 account lines</caption>
          <thead>
            <tr><th scope="col">Date</th><th scope="col">Description</th><th scope="col">Amount</th></tr>
          </thead>
          <tbody>
            {account.lines.map((line) => (
              <tr key={`${line.posted_on}-${line.kind}`}>
                <td>{line.posted_on}</td>
                <td>{line.description}</td>
                <td>{money(line.amount_minor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </article>
  );
}

export function AccountDetail() {
  const { slug } = useParams();
  const [status, setStatus] = useState("loading");
  const [account, setAccount] = useState(null);
  const [message, setMessage] = useState("");
  useEffect(() => {
    let active = true;
    fetch(`/api/v2/demo/accounts/${slug}`, { credentials: "include" }).then(async (response) => {
      const body = await response.json().catch(() => ({}));
      if (!active) return;
      if (response.ok) {
        setAccount(body);
        setStatus("ready");
        return;
      }
      setMessage(body.detail?.message || "This account could not be opened.");
      setStatus(response.status === 403 ? "denied" : "unavailable");
    }).catch(() => { if (active) setStatus("unavailable"); });
    return () => { active = false; };
  }, [slug]);
  return (
    <Workspace links={staffLinks}>
    <main id="main" className="min-h-screen bg-[#F3F6FB] text-[#172B4D]">
      <div className="mx-auto max-w-5xl px-5 py-6">
      <h1 className="font-heading text-3xl font-bold">Resident account</h1>
      <p className="mt-3"><Link className="underline" to="/owner">Back to the owner briefing</Link></p>
      {status === "loading" && <p role="status">Loading this account.</p>}
      {status !== "loading" && status !== "ready" && <p role="alert">{message || "This account could not be loaded."}</p>}
      {status === "ready" && account && <StatementBody account={account} />}
      </div>
    </main>
    </Workspace>
  );
}
