import { useEffect, useState } from "react";
import axios from "axios";
import { CalendarCheck, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const TourModal = ({ property, open, onOpenChange }) => {
  const [form, setForm] = useState({ name: "", email: "", date: "", message: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && property) {
      setForm((current) => ({ ...current, message: `I would like a private tour of ${property.title}.` }));
    }
  }, [open, property]);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/leads`, {
        name: form.name,
        email: form.email,
        preferred_date: form.date,
        message: form.message,
        intent: "private_tour",
        property_id: property?.id,
      });
      toast.success("Tour request received. A HawkVision advisor will confirm shortly.");
      onOpenChange(false);
      setForm({ name: "", email: "", date: "", message: "" });
    } catch (error) {
      toast.error("Please complete the tour request details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg border-stone-200 bg-linen p-0 text-obsidian" data-testid="tour-modal-dialog">
        <div className="border-b border-stone-200 bg-white p-7">
          <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-full bg-copper/10 text-copper">
            <CalendarCheck className="h-5 w-5" />
          </div>
          <DialogHeader>
            <DialogTitle className="font-heading text-3xl">Schedule a private tour</DialogTitle>
            <DialogDescription className="text-stone-600">
              {property ? property.title : "Tell us what Cincinnati home you want to see."}
            </DialogDescription>
          </DialogHeader>
        </div>
        <form onSubmit={submit} className="grid gap-5 p-7">
          <label className="grid gap-2 text-sm font-semibold text-stone-700">
            Preferred date
            <Input type="date" required value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} data-testid="tour-modal-date-picker" />
          </label>
          <div className="grid gap-5 sm:grid-cols-2">
            <label className="grid gap-2 text-sm font-semibold text-stone-700">
              Name
              <Input required placeholder="Your name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} data-testid="tour-modal-name-input" />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-stone-700">
              Email
              <Input type="email" required placeholder="you@example.com" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} data-testid="tour-modal-email-input" />
            </label>
          </div>
          <label className="grid gap-2 text-sm font-semibold text-stone-700">
            Notes
            <Textarea value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} data-testid="tour-modal-message-input" />
          </label>
          <Button disabled={loading} className="h-12 rounded-full bg-obsidian text-linen hover:bg-copper" data-testid="tour-modal-submit-btn">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarCheck className="h-4 w-4" />}
            Request Tour
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
