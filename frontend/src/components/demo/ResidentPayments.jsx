import { useEffect, useState } from "react";
import { Workspace } from "@/components/demo/RoleNav";
import { PaymentPanel } from "@/components/demo/PaymentPanel";

const links = [["Payments", "/payments"]];

export function ResidentPayments() {
  const [draft, setDraft] = useState("");
  const [tenancy, setTenancy] = useState("");
  const [query, setQuery] = useState("");
  const [choices, setChoices] = useState([]);
  const [assistance, setAssistance] = useState(null);

  useEffect(() => {
    fetch(`/api/v2/payments/assistance/households?q=${encodeURIComponent(query)}`, { credentials: "include" })
      .then(async (response) => {
        const body = await response.json().catch(() => ({}));
        if (response.ok) setChoices(body.households || []);
      })
      .catch(() => setChoices([]));
  }, [query]);

  async function chooseHousehold(code) {
    setTenancy(code);
    setAssistance(null);
    if (!code) return;
    const response = await fetch(`/api/v2/payments/assistance/household?tenancy_code=${encodeURIComponent(code)}`, { credentials: "include" });
    if (response.ok) setAssistance(await response.json());
  }

  return (
    <Workspace links={links}>
      <main id="main" className="min-h-screen bg-[#F3F6FB] text-[#172B4D]">
        <div className="mx-auto max-w-3xl px-5 py-8">
          <h1 className="font-heading text-4xl font-bold">Household payments</h1>
          <p className="mt-3 max-w-2xl">Open the household you pay for, then send an invitation or pay an eligible published charge. This page does not show another household. Agency assistance is not added to the amount you pay. <a className="underline" href="/payments/assistance">Report a transfer or review assistance</a>.</p>
          <label className="mt-4 block">Find a household
            <input className="mt-1 block w-full border border-[#D9E2EF] px-3 py-2" value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <label className="mt-3 block">Household
            <select className="mt-1 block w-full border border-[#D9E2EF] bg-white px-3 py-2" value={tenancy} onChange={(event) => chooseHousehold(event.target.value)}>
              <option value="">Choose a household</option>
              {choices.map((choice) => (
                <option key={`${choice.tenancy_code}-${choice.service_period}`} value={choice.tenancy_code}>
                  {choice.label} · {choice.service_period} · your portion {(choice.resident_minor / 100).toLocaleString(undefined, { style: "currency", currency: "USD" })}
                </option>
              ))}
            </select>
          </label>
          {assistance ? (
            <p className="mt-3" role="status">Your portion for {assistance.service_period} is {(assistance.resident_responsibility_minor / 100).toLocaleString(undefined, { style: "currency", currency: "USD" })}. Agency assistance of {(assistance.agency_responsibility_minor / 100).toLocaleString(undefined, { style: "currency", currency: "USD" })} is not added to the amount you pay.</p>
          ) : null}
          <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={(event) => { event.preventDefault(); setTenancy(draft.trim()); }}>
            <label>Household code
              <input className="mt-1 block border border-[#D9E2EF] px-3 py-2" required value={draft} onChange={(event) => setDraft(event.target.value)} />
            </label>
            <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Open household</button>
          </form>
          {tenancy ? <PaymentPanel tenancyCode={tenancy} mode="resident" /> : <p className="mt-4" role="status">Enter the household code to see its payable charges.</p>}
        </div>
      </main>
    </Workspace>
  );
}
