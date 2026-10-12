import { useSearchParams } from "react-router-dom";
import { Workspace } from "@/components/demo/RoleNav";
import { PaymentPanel } from "@/components/demo/PaymentPanel";

const payerLinks = [["Payments", "/pay"]];

export function PayerHome() {
  const [params] = useSearchParams();
  return (
    <Workspace links={payerLinks}>
      <main id="main" className="min-h-screen bg-[#F3F6FB] text-[#172B4D]">
        <div className="mx-auto max-w-3xl px-5 py-8">
          <h1 className="font-heading text-4xl font-bold">Granted payments</h1>
          <p className="mt-3 max-w-2xl">This workspace shows only the tenancy you were invited to pay. It does not include the household lease, staff notes, or another person's payment method.</p>
          <PaymentPanel mode="payer" initialToken={params.get("token") || ""} />
        </div>
      </main>
    </Workspace>
  );
}
