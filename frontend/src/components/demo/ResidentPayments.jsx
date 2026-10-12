import { useState } from "react";
import { Workspace } from "@/components/demo/RoleNav";
import { PaymentPanel } from "@/components/demo/PaymentPanel";

const links = [["Payments", "/payments"]];

export function ResidentPayments() {
  const [draft, setDraft] = useState("");
  const [tenancy, setTenancy] = useState("");

  return (
    <Workspace links={links}>
      <main id="main" className="min-h-screen bg-[#F3F6FB] text-[#172B4D]">
        <div className="mx-auto max-w-3xl px-5 py-8">
          <h1 className="font-heading text-4xl font-bold">Household payments</h1>
          <p className="mt-3 max-w-2xl">Open the household you pay for, then send an invitation or pay an eligible published charge. This page does not show another household.</p>
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
