import { useState } from "react";
import axios from "axios";
import { Loader2, Wrench } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const MaintenanceModal = ({ open, onOpenChange }) => {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", property_address: "", unit: "", category: "Plumbing", description: "", permission_to_enter: false });

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/maintenance-requests`, form);
      toast.success(`Request ${data.id} submitted.`);
      onOpenChange(false);
      setForm({ name: "", email: "", property_address: "", unit: "", category: "Plumbing", description: "", permission_to_enter: false });
    } catch {
      toast.error("Please complete every required maintenance detail.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] max-w-xl overflow-y-auto border-stone-200 bg-linen p-0 text-obsidian" data-testid="maintenance-request-dialog">
        <div className="border-b border-stone-200 bg-white p-7"><div className="mb-5 flex h-12 w-12 items-center justify-center bg-copper/10 text-copper"><Wrench className="h-5 w-5" /></div><DialogHeader><DialogTitle className="font-heading text-3xl">Report a maintenance issue</DialogTitle><DialogDescription className="leading-6 text-stone-600">For immediate danger, leave the area and call 911. This form is for non-emergency requests in the Phase 0 demonstration.</DialogDescription></DialogHeader></div>
        <form onSubmit={submit} className="grid gap-4 p-7">
          <div className="grid gap-4 sm:grid-cols-2"><label className="grid gap-2 text-sm font-semibold">Name<Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="maintenance-name-input" /></label><label className="grid gap-2 text-sm font-semibold">Email<Input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="maintenance-email-input" /></label></div>
          <div className="grid gap-4 sm:grid-cols-[1.5fr_0.5fr]"><label className="grid gap-2 text-sm font-semibold">Property address<Input required value={form.property_address} onChange={(e) => setForm({ ...form, property_address: e.target.value })} data-testid="maintenance-address-input" /></label><label className="grid gap-2 text-sm font-semibold">Unit<Input required value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} data-testid="maintenance-unit-input" /></label></div>
          <label className="grid gap-2 text-sm font-semibold">Category<select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="h-10 border border-stone-300 bg-white px-3" data-testid="maintenance-category-select">{["Plumbing", "Electrical", "Heating / cooling", "Appliance", "Access / security", "Other"].map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="grid gap-2 text-sm font-semibold">What happened?<Textarea required minLength={10} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="maintenance-description-input" /></label>
          <label className="flex items-start gap-3 border border-stone-200 bg-white p-4 text-sm"><input type="checkbox" checked={form.permission_to_enter} onChange={(e) => setForm({ ...form, permission_to_enter: e.target.checked })} className="mt-1" data-testid="maintenance-entry-permission-checkbox" /><span><strong>Permission to enter</strong><span className="mt-1 block text-stone-500">Authorize entry when an adult household member is not present.</span></span></label>
          <Button disabled={loading} className="mt-2 h-12 bg-obsidian text-linen hover:bg-copper" data-testid="maintenance-submit-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wrench className="h-4 w-4" />} Submit request</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};