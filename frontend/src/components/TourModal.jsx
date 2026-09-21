import { useEffect, useState } from "react";
import axios from "axios";
import { CalendarCheck, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { PHASE0 } from '@/config/phase0';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const TourModal = ({ property, intent = "showing", open, onOpenChange }) => {
  const [form, setForm] = useState({ name: "", email: "", date: "", message: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const isShowing = intent === "showing";
  const isApplication = intent === "application";
  const title = isShowing ? "Preview a showing request" : isApplication ? "Preview application interest" : "Contact HawkVision";

  useEffect(() => {
    if (!open) return;
    setError(''); setConfirmation('');
    const subject = property ? `${property.title} (${property.unit})` : "an available HawkVision property";
    setForm((current) => ({ ...current, message: isShowing ? `I would like to schedule a showing for ${subject}.` : isApplication ? `I would like to begin an application for ${subject}.` : "I would like to speak with the HawkVision property team." }));
  }, [open, property, isShowing, isApplication]);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const {data} = await axios.post(`${API}/leads`, { name: form.name, email: form.email, preferred_date: form.date || undefined, message: form.message, intent, property_id: property?.propertyId, unit_id: property?.id });
      setConfirmation(data.message);
      toast.success('Synthetic request recorded. Nothing was sent.');
      setForm({ name: "", email: "", date: "", message: "" });
    } catch (err) {
      setError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Please review the request details and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90dvh] max-w-lg overflow-y-auto border-stone-200 bg-linen p-0 text-obsidian" data-testid="rental-request-dialog">
        <div className="border-b border-stone-200 bg-white p-7">
          <div className="mb-5 flex h-12 w-12 items-center justify-center bg-copper/10 text-copper">{isApplication ? <FileText className="h-5 w-5" /> : <CalendarCheck className="h-5 w-5" />}</div>
          <DialogHeader><DialogTitle className="font-heading text-3xl">{title}</DialogTitle><DialogDescription className="text-stone-600">{property ? `${property.title} · ${property.neighborhood}` : "Tell us how the HawkVision team can help."}</DialogDescription></DialogHeader>
        </div>
        <form onSubmit={submit} className="grid gap-5 p-7">
          <p className="text-xs leading-6 text-stone-600" data-testid="rental-synthetic-warning">Synthetic requests only. Use fictional details and an example.com email. No showing, application, message or notification is created. Do not enter sensitive information.</p>
          {isShowing && <label htmlFor="request-date" className="grid gap-2 text-sm font-semibold text-stone-700">Preferred date<Input id="request-date" type="date" required value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} data-testid="rental-request-date-input" /></label>}
          <div className="grid gap-5 sm:grid-cols-2">
            <label htmlFor="request-name" className="grid gap-2 text-sm font-semibold text-stone-700">Example name<Input id="request-name" required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} data-testid="rental-request-name-input" /></label>
            <label htmlFor="request-email" className="grid gap-2 text-sm font-semibold text-stone-700">Example email<Input id="request-email" type="email" placeholder="preview@example.com" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} data-testid="rental-request-email-input" /></label>
          </div>
          <label htmlFor="request-message" className="grid gap-2 text-sm font-semibold text-stone-700">Example message<Textarea id="request-message" required value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} data-testid="rental-request-message-input" /></label>
          {isApplication && <p className="border border-gold/30 bg-gold/10 p-3 text-xs leading-5 text-stone-600" data-testid="application-disclosure">This records interest only. Screening consent, fee collection, identity verification, and document upload are not active in Phase 0.</p>}
          {error && <p role="alert" className="text-sm text-red-800" data-testid="rental-request-error">{error}</p>}
          {confirmation && <p role="status" className="text-sm text-green-800" data-testid="rental-request-confirmation">{confirmation}</p>}
          <Button disabled={loading || !PHASE0.seedsEnabled} className="h-12 bg-obsidian text-linen hover:bg-copper" data-testid="rental-request-submit-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}Record synthetic request</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};