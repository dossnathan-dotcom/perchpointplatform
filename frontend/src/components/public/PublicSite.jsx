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

function csrfToken() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

async function staffRequest(path, options = {}) {
  const method = options.method || "GET";
  return phase2(path, {
    ...options,
    headers: {
      ...(method !== "GET" ? { "x-perchpoint-csrf": csrfToken() } : {}),
      ...(options.headers || {}),
    },
  });
}

export function PublicStatus({ code, title, message, testId }) {
  return (
    <PageFrame title={title} testId={testId}>
      <p>Status {code}. EXAMPLE ONLY. This is a branded public state, not a hidden draft.</p>
      <p role="alert">{message}</p>
      <Link className="underline" to="/">Return home</Link>
    </PageFrame>
  );
}

export function ManagedPage({ slug, testId }) {
  const [state, setState] = useState("loading");
  const [page, setPage] = useState(null);
  useEffect(() => {
    let active = true;
    phase2(`/api/v2/public/pages/${slug}`).then(({ response, body }) => {
      if (!active) return;
      if (response.status === 410) {
        setState("gone");
        return;
      }
      if (response.status === 429) {
        setState("limited");
        return;
      }
      if (response.status >= 500) {
        setState("unavailable");
        return;
      }
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
  if (state === "unavailable") return <PageFrame title="Temporarily unavailable" testId={testId}><p role="alert">Published content could not be loaded. No draft is shown in its place.</p><button className="underline" type="button" onClick={() => window.location.reload()}>Try again</button></PageFrame>;
  if (state === "limited") return <PageFrame title="Too many requests" testId={testId}><p role="alert">Wait a moment, then try again. Nothing was saved.</p></PageFrame>;
  if (state === "gone") return <PageFrame title="This page has been removed" testId={testId}><p>The public address is gone. Drafts are not shown here.</p><Link className="underline" to="/">Return home</Link></PageFrame>;
  if (state === "missing" || !page) return <PageFrame title="This page is not published" testId={testId}><p>Nothing public is available at this address.</p><Link className="underline" to="/">Return home</Link></PageFrame>;
  const snapshot = page.snapshot || {};
  const text = snapshot.blocks?.[0]?.text || "";
  const crumbs = slug === "faq" ? [["Resources", "/resources"], ["FAQ", "/faq"]] : slug === "resources" ? [["Resources", "/resources"]] : null;
  return (
    <PageFrame title={snapshot.title || slug} testId={testId}>
      {crumbs && <nav aria-label="Breadcrumb"><ol className="flex gap-2 text-sm">{crumbs.map(([label, href]) => <li key={href}><Link className="underline" to={href}>{label}</Link></li>)}</ol></nav>}
      <p>{text}</p>
      <p><Link className="underline" to="/sign-in" data-testid="sign-in-transition">Resident or staff sign-in</Link></p>
    </PageFrame>
  );
}

export function RentalsIndex() {
  const [state, setState] = useState("loading");
  const [listings, setListings] = useState([]);
  useEffect(() => {
    let active = true;
    phase2("/api/v2/listings").then(({ response, body }) => {
      if (!active) return;
      if (!response.ok) {
        setState("unavailable");
        return;
      }
      setListings(body.listings || []);
      setState("ready");
    }).catch(() => { if (active) setState("unavailable"); });
    return () => { active = false; };
  }, []);
  return (
    <PageFrame title="Rentals" testId="rentals-index">
      <p>Available homes come from the current public listing projection. The CMS cannot change rent, fees, or availability.</p>
      {state === "loading" && <p role="status">Loading published listings.</p>}
      {state === "unavailable" && <p role="alert">Published listings could not be loaded.</p>}
      {state === "ready" && listings.length === 0 && <p>No homes are published right now.</p>}
      {state === "ready" && listings.length > 0 && (
        <ul className="space-y-3">
          {listings.map((listing) => (
            <li key={listing.listing_id}>
              <Link className="underline" to={`/rentals/${listing.listing_id}`}>{listing.property_name} — {listing.label}</Link>
            </li>
          ))}
        </ul>
      )}
    </PageFrame>
  );
}

export function ApplyGuide() {
  return <ManagedPage slug="apply" testId="apply-guide" />;
}

export function ContactPage() {
  const [status, setStatus] = useState("");
  const [alert, setAlert] = useState(false);
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (!form.get("consent")) {
      setAlert(true);
      setStatus("Consent to the synthetic contact notice is required.");
      return;
    }
    const intent = String(form.get("intent") || "general");
    const email = String(form.get("email") || "");
    const storageKey = `pp-submit-${intent}-${email}`;
    let idempotency = sessionStorage.getItem(storageKey);
    if (!idempotency) {
      idempotency = `contact-${crypto.randomUUID()}`;
      sessionStorage.setItem(storageKey, idempotency);
    }
    const first = sessionStorage.getItem("pp-first-touch") || "/contact";
    sessionStorage.setItem("pp-first-touch", first);
    setAlert(false);
    setStatus("Sending.");
    try {
      const { response, body } = await phase2("/api/v2/public/submissions", {
        method: "POST",
        body: JSON.stringify({
          intent,
          name: form.get("name"),
          email,
          message: form.get("message"),
          listing_slug: form.get("listing_slug") || null,
          consent_version: "synthetic-contact-v1",
          source_page: "/contact",
          first_touch: first,
          last_touch: "/contact",
          idempotency_key: idempotency,
          company_website: form.get("company_website"),
        }),
      });
      if (response.status === 429) {
        setAlert(true);
        setStatus("Too many requests. Wait and try again. Nothing new was saved.");
        return;
      }
      if (response.status === 409) {
        sessionStorage.removeItem(storageKey);
        setAlert(true);
        setStatus(body.detail?.message || "That request conflicts with one already received.");
        return;
      }
      if (!response.ok) {
        setAlert(true);
        setStatus(body.detail?.message || "The request was not saved.");
        return;
      }
      setStatus(`${body.message} Reference ${body.reference}.`);
    } catch {
      setAlert(true);
      setStatus("The request was not saved. You can try again.");
    }
  }
  return (
    <PageFrame title="Contact" testId="contact-page">
      <p>EXAMPLE ONLY. Choose a purpose. This form does not accept documents and is not monitored for emergencies.</p>
      <form className="grid gap-3" onSubmit={submit}>
        <label>Purpose
          <select name="intent" className="mt-1 w-full border px-3 py-2">
            <option value="general">General inquiry</option>
            <option value="rental_inquiry">Rental inquiry</option>
            <option value="application_help">Application help</option>
            <option value="resident_help">Resident help</option>
            <option value="maintenance_routing">Maintenance routing</option>
            <option value="accessibility">Accessibility</option>
            <option value="vendor_business">Vendor or business</option>
          </select>
        </label>
        <label>Name<input className="mt-1 w-full border px-3 py-2" name="name" required autoComplete="name" /></label>
        <label>Email<input className="mt-1 w-full border px-3 py-2" name="email" type="email" required autoComplete="email" /></label>
        <label>Published listing slug, if this is about a home<input className="mt-1 w-full border px-3 py-2" name="listing_slug" /></label>
        <label>Message<textarea className="mt-1 w-full border px-3 py-2" name="message" required /></label>
        <label className="flex gap-2"><input name="consent" type="checkbox" /> I understand this synthetic form is not an application, approval, or emergency channel.</label>
        <input className="hidden" name="company_website" tabIndex={-1} autoComplete="off" aria-hidden="true" />
        <button className="w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Send</button>
        <p role={alert ? "alert" : "status"}>{status}</p>
      </form>
      <p><Link className="underline" to="/sign-in">Resident or staff sign-in</Link></p>
    </PageFrame>
  );
}

export function StaffContent() {
  const [state, setState] = useState("loading");
  const [items, setItems] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [redirects, setRedirects] = useState([]);
  const [totals, setTotals] = useState([]);
  const [navigation, setNavigation] = useState([]);
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState("");

  async function load() {
    setState("loading");
    try {
      const listed = await staffRequest("/api/v2/content/items");
      if (listed.response.status === 401) {
        setState("signed-out");
        return;
      }
      if (listed.response.status === 403) {
        setNotice(listed.body.detail?.message || "This session cannot read content.");
        setState("denied");
        return;
      }
      if (!listed.response.ok) {
        setState("unavailable");
        return;
      }
      const [jobRows, redirectRows, conversionRows, navRows] = await Promise.all([
        staffRequest("/api/v2/content/jobs"),
        staffRequest("/api/v2/content/redirects"),
        staffRequest("/api/v2/content/conversions"),
        phase2("/api/v2/public/navigation"),
      ]);
      setItems(listed.body.items || []);
      setJobs(jobRows.body.jobs || []);
      setRedirects(redirectRows.body.redirects || []);
      setTotals(conversionRows.body.totals || []);
      setNavigation(navRows.body.pages || []);
      setState("ready");
    } catch {
      setState("unavailable");
    }
  }

  useEffect(() => { load(); }, []);

  async function saveDraft(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setNotice("Saving draft.");
    const { response, body } = await staffRequest("/api/v2/content/drafts", {
      method: "POST",
      body: JSON.stringify({
        slug: form.get("slug"),
        title: form.get("title"),
        body: form.get("body"),
        kind: form.get("kind"),
        risk_class: form.get("risk_class"),
        reason: form.get("reason"),
      }),
    });
    if (response.status === 409) {
      setNotice("This content changed. Reload it and try again.");
      return;
    }
    if (!response.ok) {
      setNotice(body.detail?.message || "The draft was not saved.");
      return;
    }
    setNotice(`Draft saved. Version ${body.version}. It is not public.`);
    event.currentTarget.reset();
    await load();
  }

  async function showPreview(slug) {
    const { response, body } = await staffRequest(`/api/v2/content/preview/${slug}`);
    if (!response.ok) {
      setPreview(body.detail?.message || "Preview is not available.");
      return;
    }
    setPreview(`${body.snapshot?.title || slug}: ${body.snapshot?.blocks?.[0]?.text || ""}`);
  }

  if (state === "loading") return <PageFrame title="Content studio" testId="content-studio"><p role="status">Loading the content studio.</p></PageFrame>;
  if (state === "signed-out") {
    return <PageFrame title="Content studio" testId="content-studio"><p>Authorized editors manage drafts here. Canonical rent, availability, and listing media stay read-only.</p><Link className="underline" to="/sign-in">Sign in</Link></PageFrame>;
  }
  if (state === "denied") return <PageFrame title="Content studio" testId="content-studio"><p role="alert">{notice}</p></PageFrame>;
  if (state === "unavailable") {
    return <PageFrame title="Content studio" testId="content-studio"><p role="alert">The content studio is unavailable.</p><button className="underline" type="button" onClick={load}>Try again</button></PageFrame>;
  }
  return (
    <PageFrame title="Content studio" testId="content-studio">
      <p>Drafts, reviews, and publication history stay here. Listing rent, fees, availability, and media are read-only facts.</p>
      <p role="status">{notice}</p>
      <section aria-labelledby="content-items-heading">
        <h2 id="content-items-heading" className="font-heading text-2xl">Pages</h2>
        {items.length === 0 ? <p>No content items are in this organization.</p> : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center gap-3">
                <span>{item.slug}</span>
                <span>{item.status}</span>
                <span>{item.risk_class}</span>
                <span>v{item.version}</span>
                <button className="underline" type="button" onClick={() => showPreview(item.slug)}>Preview exact revision</button>
              </li>
            ))}
          </ul>
        )}
      </section>
      {preview && <p data-testid="content-preview">{preview}</p>}
      <form className="grid gap-3" onSubmit={saveDraft} aria-labelledby="draft-heading">
        <h2 id="draft-heading" className="font-heading text-2xl">New draft</h2>
        <label>Slug<input className="mt-1 w-full border px-3 py-2" name="slug" required pattern="[a-z0-9]+(-[a-z0-9]+)*" /></label>
        <label>Title<input className="mt-1 w-full border px-3 py-2" name="title" required /></label>
        <label>Body<textarea className="mt-1 w-full border px-3 py-2" name="body" required /></label>
        <label>Kind
          <select name="kind" className="mt-1 w-full border px-3 py-2">
            <option value="page">Page</option>
            <option value="faq">FAQ</option>
            <option value="resource">Resource</option>
            <option value="announcement">Announcement</option>
            <option value="legal">Legal</option>
          </select>
        </label>
        <label>Risk
          <select name="risk_class" className="mt-1 w-full border px-3 py-2">
            <option value="routine">Routine</option>
            <option value="elevated">Elevated</option>
          </select>
        </label>
        <label>Reason<input className="mt-1 w-full border px-3 py-2" name="reason" required /></label>
        <button className="w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Save draft</button>
      </form>
      <section aria-labelledby="jobs-heading">
        <h2 id="jobs-heading" className="font-heading text-2xl">Publication jobs</h2>
        {jobs.length === 0 ? <p>No publication jobs are waiting or finished.</p> : (
          <ul>{jobs.map((job) => <li key={job.id}>{job.action} · {job.status}{job.last_error ? ` · ${job.last_error}` : ""}</li>)}</ul>
        )}
      </section>
      <section aria-labelledby="redirect-heading">
        <h2 id="redirect-heading" className="font-heading text-2xl">Redirects</h2>
        {redirects.length === 0 ? <p>No redirects are published.</p> : (
          <ul>{redirects.map((row) => <li key={row.id}>{row.source_path} → {row.destination_path}</li>)}</ul>
        )}
      </section>
      <section aria-labelledby="nav-heading">
        <h2 id="nav-heading" className="font-heading text-2xl">Published navigation</h2>
        {navigation.length === 0 ? <p>No public navigation is available.</p> : (
          <ul>{navigation.map((page) => <li key={page.slug}>{page.title || page.slug}</li>)}</ul>
        )}
      </section>
      <section aria-labelledby="conversion-heading">
        <h2 id="conversion-heading" className="font-heading text-2xl">Conversions</h2>
        {totals.length === 0 ? <p>No accepted public submissions are recorded.</p> : (
          <ul>{totals.map((row) => <li key={row.intent}>{row.intent}: {row.total}</li>)}</ul>
        )}
      </section>
    </PageFrame>
  );
}
