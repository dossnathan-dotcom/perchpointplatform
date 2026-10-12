import { useEffect, useState } from "react";

function csrfToken() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

function money(minor) {
  return (Number(minor || 0) / 100).toLocaleString(undefined, { style: "currency", currency: "USD" });
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

export function PaymentPanel({ tenancyCode, mode = "resident", initialToken = "" }) {
  const [status, setStatus] = useState("loading");
  const [summary, setSummary] = useState(null);
  const [message, setMessage] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("Additional October charge");
  const [method, setMethod] = useState("card");
  const [payAmount, setPayAmount] = useState("");
  const [refundPayment, setRefundPayment] = useState("");
  const [refundAmount, setRefundAmount] = useState("");
  const [refundNote, setRefundNote] = useState("");
  const [residentNote, setResidentNote] = useState("");
  const [returnAmount, setReturnAmount] = useState("");
  const [disputePayment, setDisputePayment] = useState("");
  const [cap, setCap] = useState("");
  const [period, setPeriod] = useState("2026-10");
  const [payerEmail, setPayerEmail] = useState("");
  const [invitationToken, setInvitationToken] = useState(initialToken);
  const [collectAmount, setCollectAmount] = useState("");
  const [settlementAmount, setSettlementAmount] = useState("");
  const [reversalReference, setReversalReference] = useState("");
  const [ledgerAccount, setLedgerAccount] = useState("");
  const [draftTenancy, setDraftTenancy] = useState(tenancyCode || "");
  const [activeTenancy, setActiveTenancy] = useState(tenancyCode || "");
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    const query = activeTenancy ? `?tenancy_code=${encodeURIComponent(activeTenancy)}` : "";
    fetch(`/api/v2/payments/summary${query}`, { credentials: "include" }).then(async (response) => {
      const body = await response.json().catch(() => ({}));
      if (!active) return;
      if (response.ok) {
        setSummary(body);
        setStatus("ready");
        return;
      }
      setMessage(body.detail?.message || "Payments could not be loaded.");
      setStatus(response.status === 403 ? "denied" : "unavailable");
    }).catch(() => { if (active) setStatus("unavailable"); });
    return () => { active = false; };
  }, [activeTenancy, version]);

  useEffect(() => {
    setDraftTenancy(tenancyCode || "");
    setActiveTenancy(tenancyCode || "");
  }, [tenancyCode]);

  useEffect(() => {
    const linked = summary?.ledger?.account_reference;
    if (linked) setLedgerAccount((current) => current || linked);
  }, [summary]);

  function load() {
    setVersion((current) => current + 1);
  }

  async function publish(event) {
    event.preventDefault();
    setMessage("Publishing the charge.");
    const tenancy = (draftTenancy || activeTenancy || tenancyCode || "").trim();
    const linked = ledgerAccount.trim();
    const { response, body } = await postJson("/api/v2/payments/charges", {
      tenancy_code: tenancy,
      amount_minor: Math.round(Number(amount) * 100),
      category: linked ? "rent" : "fee",
      description,
      account_reference: linked || undefined,
      rent_basis_minor: linked ? Math.round(Number(amount) * 100) : undefined,
      idempotency_key: `charge-${tenancy}-${Date.now()}`,
    });
    setMessage(response.ok ? "The charge is payable." : (body.detail?.message || "The charge was not published."));
    if (response.ok) {
      setActiveTenancy(tenancy);
      load();
    }
  }

  async function pay(obligation) {
    const requested = payAmount === "" ? obligation.remaining_minor : Math.round(Number(payAmount) * 100);
    setMessage("Submitting the synthetic payment.");
    const { response, body } = await postJson("/api/v2/payments/checkout", {
      obligation_reference: obligation.reference,
      amount_minor: requested,
      method,
      scenario: "callback",
      idempotency_key: `pay-${obligation.reference}-${Date.now()}`,
    });
    setMessage(response.ok ? (body.state === "processing" ? "Payment is processing. The account changes when the payment is confirmed." : `Payment ${body.state}. Ledger: ${body.ledger_status}. No money has moved.`) : (body.detail?.message || "The payment was not accepted."));
    if (response.ok) {
      setPayAmount("");
      load();
    }
  }

  async function refund(event) {
    event.preventDefault();
    setMessage("Submitting the refund request.");
    const { response, body } = await postJson("/api/v2/payments/refunds", {
      payment_reference: refundPayment,
      amount_minor: Math.round(Number(refundAmount) * 100),
      description: refundNote,
      resident_explanation: residentNote,
      idempotency_key: `refund-${refundPayment}-${Date.now()}`,
    });
    setMessage(response.ok ? `Refund ${body.state}. No money has moved.` : (body.detail?.message || "The refund was not accepted."));
    if (response.ok) load();
  }

  async function recordReturn(event) {
    event.preventDefault();
    setMessage("Recording the bank return.");
    const { response, body } = await postJson("/api/v2/payments/returns", {
      payment_reference: refundPayment,
      amount_minor: Math.round(Number(returnAmount) * 100),
    });
    setMessage(response.ok ? "The return was recorded. The original payment remains in history." : (body.detail?.message || "The return was not recorded."));
    if (response.ok) load();
  }

  async function openDispute(event) {
    event.preventDefault();
    setMessage("Opening the card dispute.");
    const payment = summary.payments.find((item) => item.public_reference === disputePayment);
    const { response, body } = await postJson("/api/v2/payments/disputes", {
      payment_reference: disputePayment,
      amount_minor: payment ? payment.amount_minor : 0,
      reason_code: "card_dispute",
    });
    setMessage(response.ok ? "A card dispute is open. This is not a resident complaint about the charge." : (body.detail?.message || "The dispute was not opened."));
    if (response.ok) load();
  }

  async function nominate(event) {
    event.preventDefault();
    const { response, body } = await postJson("/api/v2/payments/payers", { email: payerEmail, tenancy_code: activeTenancy || tenancyCode });
    setMessage(response.ok ? "The invitation was sent. Only that person can accept it." : (body.detail?.message || "The invitation was not created."));
  }

  async function revokePayer() {
    const { response, body } = await postJson("/api/v2/payments/payers/revoke", { tenancy_code: activeTenancy || tenancyCode });
    setMessage(response.ok ? "The additional payer can no longer start a payment." : (body.detail?.message || "The payer was not revoked."));
    if (response.ok) load();
  }

  async function collect(obligation) {
    const requested = collectAmount === "" ? obligation.remaining_minor : Math.round(Number(collectAmount) * 100);
    setMessage("Recording the synthetic collection.");
    const { response, body } = await postJson("/api/v2/payments/checkout", {
      obligation_reference: obligation.reference,
      amount_minor: requested,
      method: "card",
      scenario: "callback",
      idempotency_key: `staff-${obligation.reference}-${Date.now()}`,
    });
    setMessage(response.ok ? (body.state === "processing" ? "Collection is processing. The account changes when the payment is confirmed." : `Collection ${body.state}. Ledger: ${body.ledger_status}. No money has moved.`) : (body.detail?.message || "The collection was not accepted."));
    if (response.ok) {
      setCollectAmount("");
      load();
    }
  }

  async function acceptInvitation(event) {
    event.preventDefault();
    const { response, body } = await postJson("/api/v2/payments/payers/accept", { invitation_token: invitationToken });
    setMessage(response.ok ? "You can pay the granted charges." : (body.detail?.message || "The invitation was not accepted."));
    if (response.ok) {
      setInvitationToken("");
      load();
    }
  }

  async function recordSettlement(event) {
    event.preventDefault();
    setMessage("Recording the synthetic settlement.");
    const { response, body } = await postJson("/api/v2/leasing/ledger/settlements", {
      reference: ledgerAccount,
      amount_minor: Math.round(Number(settlementAmount) * 100),
      idempotency_key: `settle-${ledgerAccount}-${Date.now()}`,
    });
    setMessage(response.ok ? `Settlement recorded. Amount due ${money(body.due_minor)}. No money has moved.` : (body.detail?.message || "The settlement was not recorded."));
    if (response.ok) {
      setSettlementAmount("");
      load();
    }
  }

  async function reverseCharge(event) {
    event.preventDefault();
    setMessage("Recording the reversing entry.");
    const { response, body } = await postJson("/api/v2/leasing/ledger/reversals", {
      reference: reversalReference,
      idempotency_key: `reverse-${reversalReference}-${Date.now()}`,
    });
    setMessage(response.ok ? "The charge was reversed with a new entry. The original lines were not edited." : (body.detail?.message || "The reversal was not recorded."));
    if (response.ok) {
      setReversalReference("");
      load();
    }
  }

  async function enroll(event) {
    event.preventDefault();
    const { response, body } = await postJson("/api/v2/payments/autopay", {
      tenancy_code: tenancyCode,
      cap_minor: Math.round(Number(cap) * 100),
      day_of_month: 1,
    });
    setMessage(response.ok ? "Autopay is enrolled. The worker collects the eligible rent on the scheduled day." : (body.detail?.message || "Autopay was not enrolled."));
    if (response.ok) load();
  }

  async function runAutopay() {
    const { response, body } = await postJson("/api/v2/payments/autopay/run", {
      tenancy_code: tenancyCode,
      period_code: period,
    });
    setMessage(response.ok ? `Autopay ${body.state}${body.reason ? `: ${body.reason}` : ""}.` : (body.detail?.message || "Autopay did not run."));
    if (response.ok) load();
  }

  if (status === "loading") return <p role="status">Loading payments.</p>;
  if (status === "denied") return <p role="status">{message}</p>;
  if (status === "unavailable") return <p role="alert">{message} <button className="underline" type="button" onClick={load}>Try again</button></p>;
  if (!summary) return null;

  return (
    <section id="payments" className="mt-6 rounded-md border border-[#D9E2EF] bg-white p-5" aria-labelledby="payments-heading">
      <h2 id="payments-heading" className="font-heading text-2xl font-bold">Payments</h2>
      <p>Local synthetic Stripe-shaped checkout. A processing payment is not a confirmed payment, and nothing here moves money.</p>
      {summary.autopay ? (
        <p>
          Next collection {summary.autopay.next_on}. Cap {money(summary.autopay.cap_minor)}. Included {summary.autopay.included_categories.join(", ")}.
          Authorization {summary.autopay.state}.
          {summary.autopay.latest ? ` Latest ${summary.autopay.latest.period_code}: ${summary.autopay.latest.state}${summary.autopay.latest.reason ? ` (${summary.autopay.latest.reason})` : ""}.` : " No collection has run."}
        </p>
      ) : null}
      {summary.allowance ? (
        <p>
          Refund ceiling {money(summary.allowance.ceiling_minor)}. Calendar remaining {money(summary.allowance.calendar_remaining_minor)}.
          Rolling {summary.allowance.rolling_days}-day remaining {money(summary.allowance.rolling_remaining_minor)}.
        </p>
      ) : null}
      {summary.obligations.length === 0 ? <p>No published payment is waiting. The October demonstration balance is unchanged.</p> : null}
      <ul className="mt-3 space-y-3">
        {summary.obligations.map((item) => (
          <li key={item.reference} className="rounded border border-[#D9E2EF] p-3">
            <p>{item.description}</p>
            <p>Due {money(item.amount_minor)}. Processing {money(item.processing_minor)}. Remaining {money(item.remaining_minor)}.</p>
            {(mode === "resident" || mode === "payer") && item.remaining_minor > 0 ? (
              <div className="mt-2 flex flex-wrap items-end gap-3">
                <label>Amount to pay
                  <input className="mt-1 block border border-[#D9E2EF] px-3 py-2" inputMode="decimal" placeholder={money(item.remaining_minor)} value={payAmount} onChange={(event) => setPayAmount(event.target.value)} />
                </label>
                <label>Synthetic method
                  <select className="mt-1 block border border-[#D9E2EF] px-3 py-2" value={method} onChange={(event) => setMethod(event.target.value)}>
                    <option value="card">Synthetic card</option>
                    <option value="ach">Synthetic bank debit</option>
                  </select>
                </label>
                <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="button" onClick={() => pay(item)}>Pay {payAmount === "" ? money(item.remaining_minor) : money(Math.round(Number(payAmount) * 100))}</button>
              </div>
            ) : null}
            {mode === "staff" && item.remaining_minor > 0 ? (
              <div className="mt-2 flex flex-wrap items-end gap-3">
                <label>Amount to record
                  <input className="mt-1 block border border-[#D9E2EF] px-3 py-2" inputMode="decimal" placeholder={money(item.remaining_minor)} value={collectAmount} onChange={(event) => setCollectAmount(event.target.value)} />
                </label>
                <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="button" onClick={() => collect(item)}>Record synthetic collection</button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
      {summary.payments.length > 0 ? (
        <table className="mt-4 w-full text-left">
          <caption className="sr-only">Synthetic payments</caption>
          <thead><tr><th scope="col">Payment</th><th scope="col">Amount</th><th scope="col">State</th><th scope="col">Ledger</th></tr></thead>
          <tbody>
            {summary.payments.map((item) => (
              <tr key={item.public_reference}>
                <td>{item.method}</td>
                <td>{money(item.amount_minor)}</td>
                <td>{item.state}</td>
                <td>{item.ledger_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {mode === "resident" && tenancyCode ? (
        <form className="mt-4 space-y-3" onSubmit={nominate}>
          <h3 className="font-heading text-xl">Additional payer</h3>
          <label className="block">Email
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" type="email" required value={payerEmail} onChange={(event) => setPayerEmail(event.target.value)} />
          </label>
          <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Send invitation</button>
          <button className="min-h-11 border border-[#2457D6] px-4 py-2" type="button" onClick={revokePayer}>Revoke additional payer</button>
        </form>
      ) : null}
      {mode === "payer" ? (
        <form className="mt-4 space-y-3" onSubmit={acceptInvitation}>
          <h3 className="font-heading text-xl">Accept an invitation</h3>
          <label className="block">Invitation token
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" required value={invitationToken} onChange={(event) => setInvitationToken(event.target.value)} />
          </label>
          <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Accept invitation</button>
        </form>
      ) : null}
      {mode === "staff" && tenancyCode ? (
        <form className="mt-4 space-y-3" onSubmit={publish}>
          <h3 className="font-heading text-xl">Publish a payable charge</h3>
          <label className="block">Tenancy code
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" required value={draftTenancy} onChange={(event) => setDraftTenancy(event.target.value)} onBlur={() => setActiveTenancy(draftTenancy.trim())} />
          </label>
          <label className="block">Ledger account
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" value={ledgerAccount} onChange={(event) => setLedgerAccount(event.target.value)} />
          </label>
          <label className="block">Amount in dollars
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" inputMode="decimal" required value={amount} onChange={(event) => setAmount(event.target.value)} />
          </label>
          <label className="block">Description
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" minLength={3} required value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Publish charge</button>
        </form>
      ) : null}
      {mode === "staff" && ledgerAccount ? (
        <form className="mt-4 space-y-3" onSubmit={recordSettlement}>
          <h3 className="font-heading text-xl">Record a settlement</h3>
          <p>This posts to the ledger account above. It does not collect a saved payment method.</p>
          <label className="block">Amount in dollars
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" inputMode="decimal" required value={settlementAmount} onChange={(event) => setSettlementAmount(event.target.value)} />
          </label>
          <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Record settlement</button>
        </form>
      ) : null}
      {mode === "staff" && summary.ledger?.journals?.some((item) => item.kind === "charge") ? (
        <form className="mt-4 space-y-3" onSubmit={reverseCharge}>
          <h3 className="font-heading text-xl">Reverse a charge</h3>
          <label className="block">Charge
            <select className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" required value={reversalReference} onChange={(event) => setReversalReference(event.target.value)}>
              <option value="">Choose a charge</option>
              {summary.ledger.journals.filter((item) => item.kind === "charge").map((item) => (
                <option key={item.public_reference} value={item.public_reference}>{money(item.amount_minor)} charge</option>
              ))}
            </select>
          </label>
          <button className="min-h-11 border border-[#2457D6] px-4 py-2" type="submit">Reverse charge</button>
        </form>
      ) : null}
      {mode === "staff" && summary.payments.some((item) => item.state === "succeeded") ? (
        <form className="mt-4 space-y-3" onSubmit={refund}>
          <h3 className="font-heading text-xl">Request a refund</h3>
          <label className="block">Source payment
            <select className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" required value={refundPayment} onChange={(event) => setRefundPayment(event.target.value)}>
              <option value="">Choose a confirmed payment</option>
              {summary.payments.filter((item) => item.state === "succeeded").map((item) => (
                <option key={item.public_reference} value={item.public_reference}>{item.method} {money(item.amount_minor)}</option>
              ))}
            </select>
          </label>
          <label className="block">Amount in dollars
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" inputMode="decimal" required value={refundAmount} onChange={(event) => setRefundAmount(event.target.value)} />
          </label>
          <label className="block">Internal explanation
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" minLength={8} required value={refundNote} onChange={(event) => setRefundNote(event.target.value)} />
          </label>
          <label className="block">Resident-facing explanation
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" minLength={8} required value={residentNote} onChange={(event) => setResidentNote(event.target.value)} />
          </label>
          <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Submit refund</button>
        </form>
      ) : null}
      {mode === "staff" && summary.payments.some((item) => item.state === "succeeded") ? (
        <form className="mt-4 space-y-3" onSubmit={recordReturn}>
          <h3 className="font-heading text-xl">Record a bank return</h3>
          <p>This records an ACH return. It does not contest a card payment.</p>
          <label className="block">Returned payment
            <select className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" required value={refundPayment} onChange={(event) => setRefundPayment(event.target.value)}>
              <option value="">Choose a confirmed payment</option>
              {summary.payments.filter((item) => item.state === "succeeded").map((item) => (
                <option key={`return-${item.public_reference}`} value={item.public_reference}>{item.method} {money(item.amount_minor)}</option>
              ))}
            </select>
          </label>
          <label className="block">Returned amount in dollars
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" inputMode="decimal" required value={returnAmount} onChange={(event) => setReturnAmount(event.target.value)} />
          </label>
          <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Record return</button>
        </form>
      ) : null}
      {mode === "staff" && summary.payments.some((item) => item.state === "succeeded" && item.method === "card") ? (
        <form className="mt-4 space-y-3" onSubmit={openDispute}>
          <h3 className="font-heading text-xl">Open a card dispute</h3>
          <label className="block">Card payment
            <select className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" required value={disputePayment} onChange={(event) => setDisputePayment(event.target.value)}>
              <option value="">Choose a card payment</option>
              {summary.payments.filter((item) => item.state === "succeeded" && item.method === "card").map((item) => (
                <option key={`dispute-${item.public_reference}`} value={item.public_reference}>{money(item.amount_minor)}</option>
              ))}
            </select>
          </label>
          <button className="min-h-11 border border-[#2457D6] px-4 py-2" type="submit">Open card dispute</button>
        </form>
      ) : null}
      {mode === "staff" && tenancyCode ? (
        <form className="mt-4 space-y-3" onSubmit={enroll}>
          <h3 className="font-heading text-xl">Autopay</h3>
          <label className="block">Cap in dollars
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" inputMode="decimal" required value={cap} onChange={(event) => setCap(event.target.value)} />
          </label>
          <label className="block">Period
            <input className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" required value={period} onChange={(event) => setPeriod(event.target.value)} />
          </label>
          <div className="flex flex-wrap gap-3">
            <button className="min-h-11 bg-[#2457D6] px-4 py-2 text-white" type="submit">Enroll autopay</button>
            <button className="min-h-11 border border-[#2457D6] px-4 py-2" type="button" onClick={runAutopay}>Run this period</button>
          </div>
        </form>
      ) : null}
      {message ? <p role="status">{message}</p> : null}
    </section>
  );
}
