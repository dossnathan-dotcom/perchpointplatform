import { useEffect, useState } from 'react';
import { ArrowRight, Shield } from 'lucide-react';
import { ROLE_ACCOUNTS } from '@/data/siteData';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { PHASE0 } from '@/config/phase0';

export const LoginModal = ({ open, onOpenChange, onSuccess, initialRole = 'resident' }) => {
  const [roleId, setRoleId] = useState(initialRole);
  useEffect(() => { if (open) setRoleId(initialRole); }, [open, initialRole]);
  const account = ROLE_ACCOUNTS.find((item) => item.id === roleId);
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto border-stone-200 bg-linen p-7 text-obsidian" data-testid="perchpoint-login-dialog">
      <Shield className="h-7 w-7 text-copper" />
      <DialogHeader><DialogTitle className="font-heading text-3xl">Sign in to PerchPoint</DialogTitle>
        <DialogDescription data-testid="preview-access-disclosure">Production sign-in is not available. This is a role-specific interface preview, not authentication.</DialogDescription>
      </DialogHeader>
      {PHASE0.seedsEnabled ? <>
        <label className="grid gap-2 text-sm font-semibold">Preview role
          <select className="h-12 border border-stone-400 bg-white px-3" value={roleId} onChange={(e) => setRoleId(e.target.value)} data-testid="perchpoint-role-select">
            {ROLE_ACCOUNTS.map((role) => <option key={role.id} value={role.id}>{role.role}</option>)}
          </select>
        </label>
        <p className="border-l-2 border-copper pl-4 text-sm leading-7 text-stone-600" data-testid="perchpoint-role-scope">{account.scope}</p>
        <Button className="h-12 bg-obsidian text-linen hover:bg-copper" data-testid="perchpoint-login-submit-btn" onClick={() => { onOpenChange(false); onSuccess(account); }}>Enter seeded workspace <ArrowRight className="h-4 w-4" /></Button>
      </> : <p data-testid="preview-disabled-message">Workspace previews are disabled. No production account can be created here.</p>}
    </DialogContent>
  </Dialog>;
};