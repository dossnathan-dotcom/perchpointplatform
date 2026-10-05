import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { phase2 } from "@/api/phase2";

function PageFrame({ title, children, testId }) {
  return (
    <main id="main" className="mx-auto min-h-screen max-w-3xl px-5 pb-24 pt-32" data-testid={testId}>
      <p className="font-mono text-xs uppercase text-copper">HawkVision Homes · synthetic</p>
      <h1 className="mt-4 font-heading text-4xl font-bold">{title}</h1>
      <div className="mt-6 space-y-4 leading-7 text-stone-700">{children}</div>
    </main>
  );
}

export function ManagedPage({ slug, testId }) {
  const [state, setState] = useState("loading");
  const [page, setPage] = useState(null);
  useEffect(() => {
    let active = true;
    phase2(`/api/v2/public/pages/${slug}`).then(({ response, body }) => {
      if (!active) return;
      if (!response.ok) {
        setState("missing");
        return;
      }
      setPage(body);
      setState("ready");
    }).catch(() => { if (active) setState("unavailable"); });
    return () => { active = false; };
  }, [slug]);
  if (state === "loading") return <PageFrame title="Loading" testId={testId}><p role="status">Loading published content.</p></PageFrame>;
  if (state === "unavailable") return <PageFrame title="Temporarily unavailable" testId={testId}><p role="alert">Published content could not be loaded. No draft is shown in its place.</p></PageFrame>;
  if (state === "missing" || !page) return <PageFrame title="This page is not published" testId={testId}><p>Nothing public is available at this address.</p><Link className="underline" to="/">Return home</Link></PageFrame>;
  const snapshot = page.snapshot || {};
  const text = snapshot.blocks?.[0]?.text || "";
  const crumbs = slug === "faq" ? [["Resources", "/resources"], ["FAQ", "/faq"]] : slug === "resources" ? [["Resources", "/resources"]] : null;
  return (
    <PageFrame title={snapshot.title || slug} testId={testId}>
      {crumbs && <nav aria-label="Breadcrumb"><ol className="flex gap-2 text-sm">{crumbs.map(([label, href]) => <li key={href}><Link className="underline" to={href}>{label}</Link></li>)}</ol></nav>}
      <p>{text}</p>
    </PageFrame>
  );
}

export function RentalsIndex() {
  return <PageFrame title="Rentals" testId="rentals-index"><p>Available homes come from the current public listing projection. The CMS cannot change rent, fees, or availability.</p><Link className="underline" to="/#rentals">View published listings</Link></PageFrame>;
}

export function ApplyGuide() {
  return <ManagedPage slug="apply" testId="apply-guide" />;
}

export function ContactPage() {
  const [status, setStatus] = useState("");
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setStatus("Sending.");
    const { response, body } = await phase2("/api/v2/public/submissions", {
      method: "POST",
      body: JSON.stringify({
        intent: form.get("intent"),
        name: form.get("name"),
        email: form.get("email"),
        message: form.get("message"),
        consent_version: "synthetic-contact-v1",
        source_page: "/contact",
        idempotency_key: `contact-${Date.now()}`,
        company_website: form.get("company_website"),
      }),
    });
    setStatus(response.ok ? `${body.message} Reference ${body.reference}.` : "The request was not saved.");
  }
  return (
    <PageFrame title="Contact" testId="contact-page">
      <p>EXAMPLE ONLY. Choose a purpose. This form does not accept documents and is not monitored for emergencies.</p>
      <form className="grid gap-3" onSubmit={submit}>
        <label>Purpose<select name="intent" className="mt-1 w-full border px-3 py-2"><option value="general">General inquiry</option><option value="rental_inquiry">Rental inquiry</option><option value="resident_help">Resident help</option><option value="maintenance_routing">Maintenance routing</option><option value="accessibility">Accessibility</option><option value="vendor_business">Vendor or business</option></select></label>
        <label>Name<input className="mt-1 w-full border px-3 py-2" name="name" required /></label>
        <label>Email<input className="mt-1 w-full border px-3 py-2" name="email" type="email" required /></label>
        <label>Message<textarea className="mt-1 w-full border px-3 py-2" name="message" required /></label>
        <input className="hidden" name="company_website" tabIndex={-1} autoComplete="off" aria-hidden="true" />
        <button className="w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Send</button>
        <p role="status">{status}</p>
      </form>
    </PageFrame>
  );
}

export function StaffContent() {
  return <PageFrame title="Content studio" testId="content-studio"><p>Authorized editors manage drafts here. Canonical rent, availability, and listing media stay read-only.</p><Link className="underline" to="/sign-in">Sign in</Link></PageFrame>;
}
