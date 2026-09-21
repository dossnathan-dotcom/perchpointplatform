import { useEffect, useState } from "react";
import { KeyRound, LockKeyhole } from "lucide-react";
import { toast } from "sonner";
import { ROLE_ACCOUNTS } from "@/data/siteData";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export const LoginModal = ({ open, onOpenChange, onSuccess, initialRole = "resident" }) => {
  const [roleId, setRoleId] = useState(initialRole);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const selectRole = (id) => {
    const account = ROLE_ACCOUNTS.find((item) => item.id === id);
    setRoleId(id);
    setEmail(account.email);
    setPassword(account.password);
    setError("");
  };

  useEffect(() => { if (open) selectRole(initialRole); }, [open, initialRole]);

  const submit = (event) => {
    event.preventDefault();
    const account = ROLE_ACCOUNTS.find((item) => item.email === email && item.password === password);
    if (!account) {
      setError("Use the selected seeded access profile to enter this Phase 0 preview.");
      return;
    }
    toast.success(`${account.role} workspace opened.`);
    onSuccess(account);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] max-w-lg overflow-y-auto border-stone-200 bg-linen p-0 text-obsidian" data-testid="perchpoint-login-dialog">
        <div className="border-b border-stone-200 bg-white p-7">
          <div className="mb-5 flex h-12 w-12 items-center justify-center bg-copper/10 text-copper"><LockKeyhole className="h-5 w-5" /></div>
          <DialogHeader>
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-copper">PerchPoint · Phase 0 access preview</p>
            <DialogTitle className="mt-3 font-heading text-3xl">Role-aware from the first screen.</DialogTitle>
            <DialogDescription className="mt-2 leading-6 text-stone-600">Seeded demonstration access only. No production account, password, screening record, or financial record is created.</DialogDescription>
          </DialogHeader>
        </div>
        <form onSubmit={submit} className="grid gap-5 p-7">
          <label className="grid gap-2 text-sm font-semibold text-stone-700">Preview role
            <select value={roleId} onChange={(event) => selectRole(event.target.value)} className="h-11 border border-stone-300 bg-white px-3 text-sm" data-testid="perchpoint-role-select">
              {ROLE_ACCOUNTS.map((account) => <option key={account.id} value={account.id}>{account.role}</option>)}
            </select>
          </label>
          <div className="border border-stone-200 bg-white p-4" data-testid="perchpoint-role-scope"><KeyRound className="h-4 w-4 text-copper" /><p className="mt-3 text-sm leading-6 text-stone-600">{ROLE_ACCOUNTS.find((item) => item.id === roleId)?.scope}</p></div>
          <label className="grid gap-2 text-sm font-semibold text-stone-700">Email<Input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} data-testid="perchpoint-login-email-input" /></label>
          <label className="grid gap-2 text-sm font-semibold text-stone-700">Password<Input type="password" required value={password} onChange={(event) => setPassword(event.target.value)} data-testid="perchpoint-login-password-input" /></label>
          {error && <p className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" data-testid="perchpoint-login-error">{error}</p>}
          <Button className="h-12 bg-obsidian text-linen hover:bg-copper" data-testid="perchpoint-login-submit-btn">Enter seeded workspace</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};