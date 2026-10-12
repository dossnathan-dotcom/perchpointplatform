import { useEffect, useRef, useState } from "react";
import { Workspace } from "@/components/demo/RoleNav";

const links = [["Payments", "/payments"], ["Assistance", "/payments/assistance"]];

function csrfToken() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

function money(minor) {
  return (Number(minor || 0) / 100).toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function dollarsToMinor(text) {
  const match = String(text ?? "").trim().match(/^(\d+)(?:\.(\d{1,2}))?$/);
  if (!match) return null;
  return Number(match[1]) * 100 + Number((match[2] || "").padEnd(2, "0"));
}

function detailMessage(body, fallback) {
  if (typeof body.detail === "string") return body.detail;
  return body.detail?.message || fallback;
}

function reportLabel(state) {
  if (state === "reported") return "Awaiting verification";
  if (state === "matched") return "Matched to a receipt";
  if (state === "rejected") return "Not accepted";
  return state;
}

async function postJson(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json", "x-perchpoint-csrf": csrfToken() },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  return { response, body };
}

export function AssistanceDesk() {
  const [query, setQuery] = useState("");
  const [choices, setChoices] = useState([]);
  const [tenancy, setTenancy] = useState("");
  const [household, setHousehold] = useState(null);
  const [queue, setQueue] = useState(null);
  const [measures, setMeasures] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [reference, setReference] = useState("");
  const [sentOn, setSentOn] = useState("");
  const [explanation, setExplanation] = useState("");
  const [amount, setAmount] = useState("");
  const [remittanceReference, setRemittanceReference] = useState("");
  const [depositReference, setDepositReference] = useState("");
  const [offsetDollars, setOffsetDollars] = useState("0.00");
  const [remittanceLines, setRemittanceLines] = useState([
    { tenancy: "", gross: "" },
    { tenancy: "", gross: "" },
    { tenancy: "", gross: "" },
  ]);
  const [batchResult, setBatchResult] = useState(null);
  const searchGeneration = useRef(0);

  async function loadChoices(text) {
    const generation = ++searchGeneration.current;
    const response = await fetch(`/api/v2/payments/assistance/households?q=${encodeURIComponent(text)}`, { credentials: "include" });
    const body = await response.json().catch(() => ({}));
    if (generation !== searchGeneration.current) return;
    if (!response.ok) {
      setChoices([]);
      setMessage(detailMessage(body, "Households could not be loaded."));
      return;
    }
    setChoices(body.households || []);
  }

  useEffect(() => {
    loadChoices("");
  }, []);

  async function openHousehold(code) {
    setLoading(true);
    setMessage("");
    const response = await fetch(`/api/v2/payments/assistance/household?tenancy_code=${encodeURIComponent(code)}`, { credentials: "include" });
    const body = await response.json().catch(() => ({}));
    setLoading(false);
    if (!response.ok) {
      setHousehold(null);
      setMessage(detailMessage(body, "The household could not be loaded."));
      return;
    }
    setTenancy(code);
    setHousehold(body);
    if (body.resident_responsibility_minor != null) {
      setAmount((body.resident_responsibility_minor / 100).toFixed(2));
    }
  }

  async function loadQueue() {
    setMessage("");
    const measuresResponse = await fetch("/api/v2/payments/assistance/measures", { credentials: "include" });
    if (measuresResponse.ok) setMeasures(await measuresResponse.json());
    else setMeasures(null);
    const response = await fetch("/api/v2/payments/assistance/queue", { credentials: "include" });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      setQueue(null);
      setMessage(detailMessage(body, "This sign-in can review a household and report a transfer. Matching receipts is an operations task."));
      return;
    }
    setQueue(body);
  }

  async function reportTransfer(event) {
    event.preventDefault();
    if (!tenancy) {
      setMessage("Choose a household before reporting a transfer.");
      return;
    }
    const { response, body } = await postJson("/api/v2/payments/assistance/reports", {
      tenancy_code: tenancy,
      amount_minor: Math.round(Number(amount) * 100),
      reference_text: reference,
      explanation: `${sentOn} — ${explanation}`,
      idempotency_key: `report-${Date.now()}`,
    });
    if (!response.ok) {
      setMessage(detailMessage(body, "The report was not accepted."));
      return;
    }
    setReference("");
    setSentOn("");
    setExplanation("");
    await openHousehold(tenancy);
    setMessage("Awaiting verification. This report is not a payment.");
  }

  async function confirmBank(event, item) {
    event.preventDefault();
    const bankReference = String(new FormData(event.currentTarget).get("bank_reference") || "").trim();
    if (!item.service_period) {
      setMessage("This report has no service period to match.");
      return;
    }
    const { response, body } = await postJson("/api/v2/payments/assistance/receipts", {
      source: "business_bank",
      external_id: bankReference,
      method: "bank_transfer",
      purpose: "resident_rent",
      amount_minor: item.amount_minor,
      tenancy_code: item.tenancy_code,
      service_period: item.service_period,
      idempotency_key: `confirm-${item.public_reference}-${bankReference}`,
    });
    if (!response.ok) {
      setMessage(detailMessage(body, "The bank evidence was not accepted."));
      return;
    }
    const recorded = body.replayed
      ? "That bank evidence is already recorded."
      : "Verified transfer processing. Posted amount due stays unchanged until the receipt is applied.";
    if (tenancy) await openHousehold(tenancy);
    await loadQueue();
    setMessage(recorded);
  }

  async function openReturn(item) {
    const { response, body } = await postJson("/api/v2/payments/assistance/returns", {
      exception_reference: item.public_reference,
      recipient: "resident",
      idempotency_key: `return-open-${item.public_reference}`,
    });
    const recorded = response.ok
      ? "The required return is open and unpaid. These funds go back to the resident, not the agency."
      : detailMessage(body, "The required return was not opened.");
    await loadQueue();
    setMessage(recorded);
  }

  async function completeReturn(event, item) {
    event.preventDefault();
    const evidence = new FormData(event.currentTarget).get("evidence");
    const { response, body } = await postJson("/api/v2/payments/assistance/returns/complete", {
      return_reference: item.public_reference,
      evidence_key: String(evidence || ""),
      idempotency_key: `return-${item.public_reference}`,
    });
    const recorded = response.ok
      ? "The return is recorded. It is a completed synthetic settlement, and no money has moved."
      : detailMessage(body, "The return was not completed.");
    if (response.ok) await loadQueue();
    setMessage(recorded);
  }

  async function recordRemittance(event) {
    event.preventDefault();
    const rows = remittanceLines
      .map((line) => ({ tenancy_code: line.tenancy, service_period: "2026-11", gross_minor: dollarsToMinor(line.gross) }))
      .filter((line) => line.tenancy_code && line.gross_minor);
    const gross = rows.reduce((sum, line) => sum + line.gross_minor, 0);
    const recoupment = dollarsToMinor(offsetDollars);
    if (!rows.length || recoupment == null || gross < recoupment) {
      setMessage("Enter each household line and a prior-period offset that does not exceed the gross assistance.");
      return;
    }
    const { response, body } = await postJson("/api/v2/payments/assistance/batches", {
      external_id: remittanceReference.trim(),
      cash_external_id: depositReference.trim(),
      gross_minor: gross,
      recoupment_minor: recoupment,
      adjustment_minor: 0,
      net_minor: gross - recoupment,
      rows,
      idempotency_key: `batch-${remittanceReference.trim()}`,
    });
    if (!response.ok) {
      setMessage(detailMessage(body, "The remittance was not accepted."));
      return;
    }
    setBatchResult({ ...body, proposed: true });
    setMessage(body.replayed ? "That remittance is already recorded." : "The remittance is ready to apply. Nothing has been posted yet.");
  }

  async function applyRemittance() {
    if (!batchResult?.reference) return;
    const { response, body } = await postJson("/api/v2/payments/assistance/batches/apply", {
      batch_reference: batchResult.reference,
      idempotency_key: `batch-apply-${batchResult.reference}`,
    });
    if (!response.ok) {
      setMessage(detailMessage(body, "The remittance was not applied."));
      return;
    }
    setBatchResult({ ...batchResult, ...body, proposed: false });
    setMessage(body.unexplained_minor === 0 ? "The remittance is applied. The unexplained remainder is $0.00." : "Some lines still need a household or evidence.");
    await loadQueue();
    setMessage(body.unexplained_minor === 0 ? "The remittance is applied. The unexplained remainder is $0.00." : "Some lines still need a household or evidence.");
  }

  async function applyReceipt(item) {
    const { response, body } = await postJson("/api/v2/payments/assistance/receipts/apply", {
      receipt_reference: item.public_reference,
      idempotency_key: `apply-${item.public_reference}`,
    });
    setMessage(response.ok ? (body.posted ? "The receipt was applied once." : "The receipt stays open for review.") : (body.detail?.message || "The receipt was not applied."));
    if (response.ok) await loadQueue();
  }

  const residentDue = household?.resident_responsibility_minor;
  const nothingToPay = household && residentDue === 0;

  return (
    <Workspace links={links}>
      <main id="main" className="min-h-screen bg-[#F3F6FB] text-[#172B4D]">
        <div className="mx-auto max-w-3xl px-5 py-8">
          <h1 className="font-heading text-4xl font-bold">Digital payments and assistance</h1>
          <p className="mt-3 max-w-2xl">Your payment amount is your approved portion. An agency delay stays on the assistance side and does not increase what you can pay.</p>
          <form className="mt-4 space-y-3" onSubmit={(event) => { event.preventDefault(); loadChoices(query); }}>
            <label className="block">Find a household
              <input className="mt-1 block w-full border border-[#D9E2EF] px-3 py-2" value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
            <button className="min-h-11 border border-[#2457D6] px-4 py-2" type="submit">Search</button>
            <label className="block">Household
              <select
                className="mt-1 block w-full border border-[#D9E2EF] bg-white px-3 py-2"
                value={tenancy}
                onChange={(event) => openHousehold(event.target.value)}
              >
                <option value="">Choose a household</option>
                {choices.map((choice) => (
                  <option key={`${choice.tenancy_code}-${choice.service_period}`} value={choice.tenancy_code}>
                    {choice.label} · {choice.service_period} · your portion {money(choice.resident_minor)}
                  </option>
                ))}
              </select>
            </label>
          </form>
          {loading ? <p className="mt-4">Loading the household.</p> : null}
          {household ? (
            <section className="mt-6 border border-[#D9E2EF] bg-white p-4" aria-live="polite">
              <h2 className="text-xl font-semibold">{household.label || "Household responsibility"} · {household.service_period || "No approved schedule"}</h2>
              <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                <div><dt>Your portion</dt><dd className="font-semibold">{household.resident_responsibility_minor == null ? "Not on file" : money(household.resident_responsibility_minor)}</dd></div>
                <div><dt>Agency portion</dt><dd className="font-semibold">{household.agency_responsibility_minor == null ? "Not on file" : money(household.agency_responsibility_minor)}</dd></div>
                <div><dt>Agency still expected</dt><dd>{money(household.agency_outstanding_minor)}</dd></div>
                <div><dt>Amount due from you</dt><dd>{household.due_minor == null ? "Hidden on this sign-in" : money(household.due_minor)}</dd></div>
              </dl>
              {nothingToPay ? <p className="mt-3">There is no resident rent to pay. The agency portion is not added to your payment.</p> : null}
              {household.reserved_minor > 0 ? <p className="mt-3">Verified transfer processing {money(household.reserved_minor)}. Posted amount due stays {household.due_minor == null ? "hidden on this sign-in" : money(household.due_minor)} until the receipt is applied.</p> : null}
              {household.resident_returned_minor > 0 ? <p className="mt-3">Received {money(household.resident_received_minor)}, returned {money(household.resident_returned_minor)}, net retained {money(household.resident_net_minor)}.</p> : null}
              {household.reports?.length ? (
                <ul className="mt-3 space-y-1">
                  {household.reports.map((item) => (
                    <li key={item.public_reference}>{reportLabel(item.state)} · {money(item.amount_minor)}</li>
                  ))}
                </ul>
              ) : null}
              {household.exceptions?.length ? <p className="mt-3">Open follow-up: {household.exceptions[0].kind.replaceAll("_", " ")} {money(household.exceptions[0].amount_minor)}</p> : null}
            </section>
          ) : null}
          {nothingToPay ? null : (
            <form className="mt-8 space-y-3" onSubmit={reportTransfer}>
              <h2 className="text-xl font-semibold">Report a transfer</h2>
              <p>This opens a case. It does not mark the rent paid.</p>
              <label className="block">Amount you sent
                <input className="mt-1 block border border-[#D9E2EF] px-3 py-2" inputMode="decimal" required value={amount} onChange={(event) => setAmount(event.target.value)} />
              </label>
              <label className="block">Reference
                <input className="mt-1 block w-full border border-[#D9E2EF] px-3 py-2" required value={reference} onChange={(event) => setReference(event.target.value)} />
              </label>
              <label className="block">Date sent
                <input className="mt-1 block border border-[#D9E2EF] px-3 py-2" type="date" required value={sentOn} onChange={(event) => setSentOn(event.target.value)} />
              </label>
              <label className="block">What should we know
                <textarea className="mt-1 block w-full border border-[#D9E2EF] px-3 py-2" required value={explanation} onChange={(event) => setExplanation(event.target.value)} />
              </label>
              <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Submit report</button>
            </form>
          )}
          <form className="mt-8 space-y-3" onSubmit={recordRemittance}>
            <h2 className="text-xl font-semibold">Agency remittance</h2>
            <p>Gross assistance, a prior-period offset, and the bank deposit stay separate. Applying a complete remittance does not change what each resident owes.</p>
            <label className="block">Remittance reference
              <input className="mt-1 block w-full border border-[#D9E2EF] px-3 py-2" required value={remittanceReference} onChange={(event) => setRemittanceReference(event.target.value)} />
            </label>
            <label className="block">Bank deposit reference
              <input className="mt-1 block w-full border border-[#D9E2EF] px-3 py-2" required value={depositReference} onChange={(event) => setDepositReference(event.target.value)} />
            </label>
            <label className="block">Prior-period offset
              <input className="mt-1 block border border-[#D9E2EF] px-3 py-2" inputMode="decimal" required value={offsetDollars} onChange={(event) => setOffsetDollars(event.target.value)} />
            </label>
            {remittanceLines.map((line, index) => (
              <div key={index} className="grid gap-2 sm:grid-cols-2">
                <label>Household line {index + 1}
                  <select className="mt-1 block w-full border border-[#D9E2EF] bg-white px-3 py-2" value={line.tenancy} onChange={(event) => setRemittanceLines((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, tenancy: event.target.value } : item))}>
                    <option value="">Choose a household</option>
                    {choices.map((choice) => (
                      <option key={`${index}-${choice.tenancy_code}`} value={choice.tenancy_code}>{choice.label} · {choice.service_period}</option>
                    ))}
                  </select>
                </label>
                <label>Gross assistance line {index + 1}
                  <input className="mt-1 block w-full border border-[#D9E2EF] px-3 py-2" inputMode="decimal" value={line.gross} onChange={(event) => setRemittanceLines((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, gross: event.target.value } : item))} />
                </label>
              </div>
            ))}
            <button className="min-h-11 border border-[#2457D6] px-4 py-2" type="submit">Preview remittance</button>
          </form>
          {batchResult ? (
            <section className="mt-4 border border-[#D9E2EF] bg-white p-4" aria-live="polite">
              <h2 className="text-xl font-semibold">{batchResult.proposed ? "Proposed remittance" : "Applied remittance"}</h2>
              <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                <div><dt>Gross assistance</dt><dd className="font-semibold">{money(batchResult.gross_minor)}</dd></div>
                <div><dt>Prior-period offset</dt><dd className="font-semibold">{money(batchResult.recoupment_minor)}</dd></div>
                <div><dt>Net confirmed cash</dt><dd className="font-semibold">{money(batchResult.confirmed_cash_minor ?? batchResult.net_minor)}</dd></div>
                <div><dt>Unexplained remainder</dt><dd className="font-semibold">{batchResult.proposed ? "Not posted" : money(batchResult.unexplained_minor)}</dd></div>
              </dl>
              {batchResult.proposed ? <button className="mt-3 min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="button" onClick={applyRemittance}>Apply eligible rows</button> : null}
            </section>
          ) : null}
          <div className="mt-8">
            <button className="min-h-11 border border-[#2457D6] px-4 py-2" type="button" onClick={loadQueue}>Open the operations queue</button>
            {measures ? (
              <dl className="mt-4 grid gap-2 sm:grid-cols-2">
                <div><dt>Assistance expected</dt><dd className="font-semibold">{money(measures.assistance_expected_minor)}</dd><dd className="text-sm">{measures.definitions?.assistance_expected_minor}</dd></div>
                <div><dt>Assistance received</dt><dd className="font-semibold">{money(measures.assistance_received_minor)}</dd></div>
                <div><dt>Confirmed cash</dt><dd>{money(measures.confirmed_cash_minor)}</dd></div>
                <div><dt>Unmatched confirmed funds</dt><dd>{money(measures.unmatched_confirmed_minor)}</dd></div>
              </dl>
            ) : null}
            {queue ? (
              <ul className="mt-4 space-y-2">
                {queue.receipts.length === 0 && queue.exceptions.length === 0 && queue.reports.length === 0 ? <li>Nothing is waiting.</li> : null}
                {(queue.reports || []).map((item) => (
                  <li key={item.public_reference} className="border border-[#D9E2EF] bg-white p-3">
                    <p>{item.label || "Household"} · transfer report · {money(item.amount_minor)} · Awaiting verification</p>
                    <p className="mt-1">{item.next_action}</p>
                    <form className="mt-2 flex flex-wrap items-end gap-2" onSubmit={(event) => confirmBank(event, item)}>
                      <label>Bank reference
                        <input className="mt-1 block border border-[#D9E2EF] px-3 py-2" name="bank_reference" required />
                      </label>
                      <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Confirm bank evidence</button>
                    </form>
                  </li>
                ))}
                {queue.receipts.map((item) => (
                  <li key={item.public_reference} className="border border-[#D9E2EF] bg-white p-3">
                    <p>{item.label || item.source} · {item.service_period || "Period not set"} · {money(item.amount_minor)} · {item.application_state}</p>
                    <p className="mt-1">{item.next_action}</p>
                    {item.application_state === "queued" ? (
                      <button className="mt-2 min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="button" onClick={() => applyReceipt(item)}>Apply match</button>
                    ) : null}
                  </li>
                ))}
                {queue.exceptions.map((item) => (
                  <li key={item.public_reference} className="border border-[#D9E2EF] bg-white p-3">
                    <p>{item.label || "Household"} · {item.service_period} · {item.kind.replaceAll("_", " ")} · {money(item.amount_minor)}</p>
                    <p className="mt-1">{item.next_action}</p>
                    {item.kind === "resident_overpayment" ? (
                      <button className="mt-2 min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="button" onClick={() => openReturn(item)}>Open required return</button>
                    ) : null}
                    {item.kind === "required_return" ? (
                      <form className="mt-2 flex flex-wrap items-end gap-2" onSubmit={(event) => completeReturn(event, item)}>
                        <label>Verified bank evidence
                          <input className="mt-1 block border border-[#D9E2EF] px-3 py-2" name="evidence" required />
                        </label>
                        <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Record verified completion</button>
                      </form>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
          {message ? <p className="mt-4" role="status">{message}</p> : null}
        </div>
      </main>
    </Workspace>
  );
}
