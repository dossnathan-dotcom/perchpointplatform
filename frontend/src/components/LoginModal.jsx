import { useState } from "react";
import { KeyRound, LockKeyhole } from "lucide-react";
import { toast } from "sonner";
import { MOCK_ACCOUNTS } from "@/data/siteData";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export const LoginModal = ({ open, onOpenChange, onSuccess }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const quickFill = (index) => {
    const account = MOCK_ACCOUNTS[index];
    setEmail(account.email);
    setPassword(account.password);
    setError("");
  };

  const submit = (event) => {
    event.preventDefault();
    const account = MOCK_ACCOUNTS.find((item) => item.email === email && item.password === password);
    if (!account) {
      setError("Use one of the mock profiles below to enter the demo portal.");
      return;
    }
    toast.success(`Welcome back, ${account.name}.`);
    onSuccess(account);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md border-stone-200 bg-linen p-0 text-obsidian" data-testid="login-modal-dialog">
        <div className="border-b border-stone-200 bg-white p-7">
          <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-full bg-copper/10 text-copper">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <DialogHeader>
            <DialogTitle className="font-heading text-3xl">Client portal preview</DialogTitle>
            <DialogDescription className="text-stone-600">
              This is a mock login for the HawkVision demo experience. No real account is created.
            </DialogDescription>
          </DialogHeader>
        </div>

        <form onSubmit={submit} className="grid gap-5 p-7">
          <label className="grid gap-2 text-sm font-semibold text-stone-700">
            Email
            <Input type="email" required placeholder="buyer@hawkvision.com" value={email} onChange={(event) => setEmail(event.target.value)} data-testid="login-modal-email-input" />
          </label>
          <label className="grid gap-2 text-sm font-semibold text-stone-700">
            Password
            <Input type="password" required placeholder="hawk-demo" value={password} onChange={(event) => setPassword(event.target.value)} data-testid="login-modal-password-input" />
          </label>
          {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" data-testid="login-modal-error">{error}</p>}

          <div className="grid gap-3 sm:grid-cols-2">
            <button type="button" onClick={() => quickFill(0)} className="rounded-2xl border border-stone-200 bg-white p-4 text-left transition-colors hover:border-copper" data-testid="login-modal-quick-fill-buyer">
              <KeyRound className="mb-3 h-4 w-4 text-copper" />
              <span className="block text-sm font-bold">VIP Buyer</span>
              <span className="text-xs text-stone-500">buyer@hawkvision.com</span>
            </button>
            <button type="button" onClick={() => quickFill(1)} className="rounded-2xl border border-stone-200 bg-white p-4 text-left transition-colors hover:border-copper" data-testid="login-modal-quick-fill-seller">
              <KeyRound className="mb-3 h-4 w-4 text-copper" />
              <span className="block text-sm font-bold">Luxury Seller</span>
              <span className="text-xs text-stone-500">seller@hawkvision.com</span>
            </button>
          </div>

          <Button className="h-12 rounded-full bg-obsidian text-linen hover:bg-copper" data-testid="login-modal-submit-btn">
            Enter Mock Portal
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
