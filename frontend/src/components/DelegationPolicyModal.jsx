import { GitBranch, ShieldCheck } from "lucide-react";
import { DELEGATION_RULES } from "@/data/portalData";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export const DelegationPolicyModal = ({ open, onOpenChange }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-h-[90vh] max-w-5xl overflow-y-auto border-white/10 bg-obsidian p-0 text-linen" data-testid="delegation-policy-modal">
      <div className="border-b border-white/10 p-7 sm:p-9">
        <DialogHeader>
          <div className="mb-4 flex h-11 w-11 items-center justify-center bg-copper/15 text-gold"><GitBranch className="h-5 w-5" /></div>
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-gold">Draft policy model · thresholds configurable</p>
          <DialogTitle className="mt-3 font-heading text-4xl text-linen">Delegation is a policy, not one number.</DialogTitle>
          <DialogDescription className="mt-3 max-w-3xl leading-6 text-linen/55">Rules can combine amount, property, unit, category, budget, monthly rent, emergency status, requestor, vendor, time window, prior spending, and active delegation.</DialogDescription>
        </DialogHeader>
      </div>
      <div className="p-5 sm:p-8">
        <div className="overflow-x-auto border border-white/10">
          <table className="w-full min-w-[760px] text-left text-sm" data-testid="delegation-policy-table">
            <thead className="bg-white/[0.06] font-mono text-[10px] uppercase tracking-[0.16em] text-linen/45"><tr>{["Decision", "Trigger", "Authority", "Control"].map((item) => <th key={item} className="px-5 py-4">{item}</th>)}</tr></thead>
            <tbody>{DELEGATION_RULES.map((rule) => <tr key={rule[0]} className="border-t border-white/10"><td className="px-5 py-5 font-bold">{rule[0]}</td><td className="px-5 py-5 text-linen/60">{rule[1]}</td><td className="px-5 py-5 text-gold">{rule[2]}</td><td className="px-5 py-5 text-linen/60">{rule[3]}</td></tr>)}</tbody>
          </table>
        </div>
        <div className="mt-5 flex items-start gap-3 border border-gold/20 bg-gold/10 p-4 text-sm text-linen/70"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-gold" /><p>Final dollar limits remain unset until Farouk approves them. Emergency authority always requires immediate notice and retrospective review.</p></div>
      </div>
    </DialogContent>
  </Dialog>
);