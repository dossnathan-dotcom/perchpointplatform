import { useEffect, useState } from "react";
import axios from "axios";
import { CalendarCheck, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const TourModal = ({ property, intent = "showing", open, onOpenChange }) => {
  const [form, setForm] = useState({ name: "", email: "", date: "", message: "" });
  const [loading, setLoading] = useState(false);
  const isShowing = intent === "showing";
  const isApplication = intent === "application";
  const title = isShowing ? "Schedule a showing" : isApplication ? "Start your application" : "Contact HawkVision";

  useEffect(() => {
    if (!open) return;
    const subject = property ? `${property.title} (${property.unit})` : "an available HawkVision property";
    setForm((current) => ({ ...current, message: isShowing ? `I would like to schedule a showing for ${subject}.` : isApplication ? `I would like to begin an application for ${subject}.` : "I would like to speak with the HawkVision property team." }));
  }, [open, property, isShowing, isApplication]);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/leads`, { name: form.name, email: form.email, preferred_date: form.date || undefined, message: form.message, intent, property_id: property?.id });
      toast.success(isShowing ? "Showing request received." : isApplication ? "Application interest recorded." : "Message received.");
      onOpenChange(false);
      setForm({ name: "", email: "", date: "", message: "" });
    } catch {
      toast.error("Please review the request details and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg border-stone-200 bg-linen p-0 text-obsidian" data-testid="rental-request-dialog">
        <div className="border-b border-stone-200 bg-white p-7">
          <div className="mb-5 flex h-12 w-12 items-center justify-center bg-copper/10 text-copper">{isApplication ? <FileText className="h-5 w-5" /> : <CalendarCheck className="h-5 w-5" />}</div>
          <DialogHeader><DialogTitle className="font-heading text-3xl">{title}</DialogTitle><DialogDescription className="text-stone-600">{property ? `${property.title} · ${property.neighborhood}` : "Tell us how the HawkVision team can help."}</DialogDescription></DialogHeader>
        </div>
        <form onSubmit={submit} className="grid gap-5 p-7">
          {isShowing && <label className="grid gap-2 text-sm font-semibold text-stone-700">Preferred date<Input type="date" required value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} data-testid="rental-request-date-input" /></label>}
          <div className="grid gap-5 sm:grid-cols-2">
            <label className="grid gap-2 text-sm font-semibold text-stone-700">Name<Input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} data-testid="rental-request-name-input" /></label>
            <label className="grid gap-2 text-sm font-semibold text-stone-700">Email<Input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} data-testid="rental-request-email-input" /></label>
          </div>
          <label className="grid gap-2 text-sm font-semibold text-stone-700">Message<Textarea required value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} data-testid="rental-request-message-input" /></label>
          {isApplication && <p className="border border-gold/30 bg-gold/10 p-3 text-xs leading-5 text-stone-600" data-testid="application-disclosure">This records interest only. Screening consent, fee collection, identity verification, and document upload are not active in Phase 0.</p>}
          <Button disabled={loading} className="h-12 bg-obsidian text-linen hover:bg-copper" data-testid="rental-request-submit-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : isApplication ? <FileText className="h-4 w-4" /> : <CalendarCheck className="h-4 w-4" />}{isShowing ? "Request showing" : isApplication ? "Record application interest" : "Send message"}</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};