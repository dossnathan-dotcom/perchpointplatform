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

export function LeasingDesk() {
  const [state, setState] = useState("idle");
  const [rows, setRows] = useState([]);
  async function load(event) {
    event.preventDefault();
    setState("loading");
    try {
      const { response, body } = await staffRequest("/api/v2/leasing/queue");
      if (response.status === 401 || response.status === 403) {
        setState("denied");
        return;
      }
      if (!response.ok) {
        setState("unavailable");
        return;
      }
      setRows(body.inquiries || []);
      setState(body.inquiries?.length ? "ready" : "empty");
    } catch {
      setState("unavailable");
    }
  }
  return (
    <PageFrame title="Leasing queue" testId="leasing-desk">
      <p>Operational work only. This desk does not approve housing, schedule a showing, or open an application.</p>
      <form onSubmit={load}>
        <button className="underline" type="submit">Refresh queue</button>
      </form>
      {state === "loading" && <p role="status">Loading the queue.</p>}
      {state === "denied" && <p role="alert">This queue is not available for the current session.</p>}
      {state === "unavailable" && <p role="alert">The leasing queue is temporarily unavailable.</p>}
      {state === "empty" && <p>No open inquiries are in this queue.</p>}
      {state === "ready" && (
        <table className="w-full text-left">
          <caption className="sr-only">Open leasing inquiries</caption>
          <thead>
            <tr><th scope="col">Stage</th><th scope="col">Next action</th><th scope="col">Due</th></tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.public_receipt}>
                <td>{row.stage}</td>
                <td>{row.next_action}</td>
                <td>{row.unassigned ? "Unassigned" : "Assigned"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </PageFrame>
  );
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
  const [discovery, setDiscovery] = useState([]);
  const [notice, setNotice] = useState("");
  const [inquiryState, setInquiryState] = useState("idle");
  const [receipt, setReceipt] = useState("");
  const [favorites, setFavorites] = useState(() => {
    try {
      return JSON.parse(window.localStorage.getItem("pp-discovery-favorites") || "[]");
    } catch {
      return [];
    }
  });
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
  async function search(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const params = new URLSearchParams();
    for (const [key, value] of form.entries()) {
      if (String(value).trim()) params.set(key, String(value).trim());
    }
    setNotice("Searching approved listings.");
    try {
      const { response, body } = await phase2(`/api/v2/public/discovery/search?${params.toString()}`);
      if (!response.ok) {
        setNotice("Search is temporarily unavailable. The published list below is unchanged.");
        return;
      }
      setDiscovery(body.records || []);
      setNotice(body.total ? `${body.total} approved listings match.` : "No listings match. Remove one filter and search again.");
    } catch {
      setNotice("Search is temporarily unavailable. The published list below is unchanged.");
    }
  }
  async function inquire(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (!form.get("disclosure")) {
      setInquiryState("invalid");
      return;
    }
    setInquiryState("loading");
    try {
      const { response, body } = await phase2("/api/v2/public/leasing/inquiries", {
        method: "POST",
        body: JSON.stringify({
          name: String(form.get("name") || ""),
          email: String(form.get("email") || ""),
          message: String(form.get("message") || ""),
          disclosure: true,
          honeypot: String(form.get("company") || ""),
          idempotency_key: `web-${crypto.randomUUID()}`,
        }),
      });
      if (!response.ok) {
        setInquiryState("invalid");
        return;
      }
      setReceipt(body.receipt || "");
      setInquiryState("received");
    } catch {
      setInquiryState("unavailable");
    }
  }
  function favorite(slug) {
    const next = favorites.includes(slug) ? favorites.filter((item) => item !== slug) : [...favorites, slug].slice(0, 3);
    setFavorites(next);
    window.localStorage.setItem("pp-discovery-favorites", JSON.stringify(next));
  }
  return (
    <PageFrame title="Rentals" testId="rentals-index">
      <p>Available homes come from the current public listing projection. The CMS cannot change rent, fees, or availability.</p>
      <form className="space-y-3" onSubmit={search}>
        <label className="block text-sm font-semibold" htmlFor="discovery-city">City</label>
        <input id="discovery-city" name="city" className="w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
        <label className="block text-sm font-semibold" htmlFor="discovery-use">Use</label>
        <select id="discovery-use" name="use_code" className="w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }}>
          <option value="">Any approved use</option>
          <option value="residential">Residential</option>
          <option value="commercial">Commercial</option>
        </select>
        <button className="underline" type="submit">Search approved listings</button>
      </form>
      <p role="status">{notice}</p>
      {discovery.length > 0 && (
        <ul className="space-y-3">
          {discovery.map((row) => (
            <li key={row.public_slug}>
              <Link className="underline" to={`/rentals/${row.public_slug}`}>{row.payload.property_name} — {row.payload.label}</Link>
              <button className="ml-3 underline" type="button" onClick={() => favorite(row.public_slug)}>Save on this device</button>
            </li>
          ))}
        </ul>
      )}
      {favorites.length > 0 && <p>Saved on this device: {favorites.join(", ")}. Nothing was sent to the server.</p>}
      <form className="space-y-3" onSubmit={inquire} data-testid="leasing-inquiry">
        <h2 className="font-heading text-2xl font-bold">Ask about a home</h2>
        <p>This records leasing interest only. It does not schedule a showing or start an application.</p>
        <label className="block text-sm font-semibold" htmlFor="inquiry-name">Name</label>
        <input id="inquiry-name" name="name" required className="w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
        <label className="block text-sm font-semibold" htmlFor="inquiry-email">Email</label>
        <input id="inquiry-email" name="email" type="email" required autoComplete="email" className="w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
        <label className="block text-sm font-semibold" htmlFor="inquiry-message">Message</label>
        <textarea id="inquiry-message" name="message" required className="w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
        <label className="block text-sm font-semibold" htmlFor="inquiry-disclosure">
          <input id="inquiry-disclosure" name="disclosure" type="checkbox" className="mr-2" />
          I understand HawkVision will use this message to respond about leasing.
        </label>
        <div className="absolute -left-[10000px] h-px w-px overflow-hidden" aria-hidden="true">
          <label htmlFor="inquiry-company">Company</label>
          <input id="inquiry-company" name="company" tabIndex={-1} autoComplete="off" />
        </div>
        <button className="underline" type="submit">Send inquiry</button>
      </form>
      {inquiryState === "loading" && <p role="status">Sending the inquiry.</p>}
      {inquiryState === "invalid" && <p role="alert">The inquiry could not be accepted. Check the name, email, message, and acknowledgement.</p>}
      {inquiryState === "unavailable" && <p role="alert">Inquiry intake is temporarily unavailable.</p>}
      {inquiryState === "received" && <p role="status">Inquiry received. Reference {receipt}. No staff notes or other records are shown.</p>}
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
  const [history, setHistory] = useState(null);

  async function act(path, payload) {
    const { response, body } = await staffRequest(path, { method: "POST", body: JSON.stringify(payload) });
    if (response.status === 409) {
      setNotice("This content changed. Reload it and try again.");
    } else if (!response.ok) {
      setNotice(body.detail?.message || "The change was not saved.");
    } else if (body.published) {
      setNotice("Published.");
    } else if (body.unpublished) {
      setNotice("Unpublished.");
    } else if (body.scheduled) {
      setNotice("Scheduled. The job will recheck authority when it runs.");
    } else {
      setNotice("The content change was recorded.");
    }
    await load();
  }

  async function openHistory(item) {
    const { response, body } = await staffRequest(`/api/v2/content/items/${item.id}/history`);
    if (!response.ok) {
      setNotice(body.detail?.message || "History is not available.");
      return;
    }
    setHistory({ item, ...body });
  }

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
                <button className="underline" type="button" onClick={() => act(`/api/v2/content/${item.id}/publish`, { expected_version: item.version })}>Publish</button>
                <button className="underline" type="button" onClick={() => act(`/api/v2/content/${item.id}/unpublish`, { expected_version: item.version })}>Unpublish</button>
                <button className="underline" type="button" onClick={() => openHistory(item)}>History</button>
              </li>
            ))}
          </ul>
        )}
      </section>
      {preview && <p data-testid="content-preview">{preview}</p>}
      {history && (
        <section aria-labelledby="history-heading" data-testid="content-history">
          <h2 id="history-heading" className="font-heading text-2xl">History for {history.item.slug}</h2>
          {history.revisions?.length ? (
            <ul>
              {history.revisions.map((revision) => (
                <li key={revision.id}>
                  Version {revision.version}: {revision.reason}
                  <button className="ml-3 underline" type="button" onClick={() => act(`/api/v2/content/${history.item.id}/rollback`, { expected_version: history.item.version, revision_id: revision.id, reason: "Restore an earlier approved revision" })}>Roll back to this revision</button>
                </li>
              ))}
            </ul>
          ) : <p>No revisions are recorded.</p>}
          <h3 className="font-heading text-xl">Publication record</h3>
          {history.publications?.length ? (
            <ul>{history.publications.map((row) => <li key={row.id}>{row.slug} published {row.published_at}{row.superseded_at ? `, superseded ${row.superseded_at}` : ", current"}</li>)}</ul>
          ) : <p>This item has not been published.</p>}
          <form className="grid gap-3" onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            act(`/api/v2/content/${history.item.id}/schedule`, {
              expected_version: history.item.version,
              run_at: new Date(form.get("run_at")).toISOString(),
              time_zone: "America/New_York",
              action: form.get("action"),
            });
          }}>
            <h3 className="font-heading text-xl">Schedule</h3>
            <label>When<input className="mt-1 w-full border px-3 py-2" name="run_at" type="datetime-local" required /></label>
            <label>Action
              <select name="action" className="mt-1 w-full border px-3 py-2"><option value="publish">Publish</option><option value="expire">Expire</option></select>
            </label>
            <button className="w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Schedule</button>
          </form>
        </section>
      )}
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

export function ShowingDesk() {
  const [status, setStatus] = useState("Enter a showing receipt to see property-local times.");
  const [slots, setSlots] = useState([]);
  async function loadSlots(event) {
    event.preventDefault();
    const receipt = new FormData(event.currentTarget).get("receipt");
    setStatus("Checking available times.");
    try {
      const capability = await phase2("/api/v2/public/showings/capabilities", { method: "POST", body: JSON.stringify({ receipt }) });
      if (!capability.response.ok) {
        setStatus("The showing request could not be accepted.");
        setSlots([]);
        return;
      }
      const listed = await phase2("/api/v2/public/showings/slots", { method: "POST", body: JSON.stringify({ capability: capability.body.capability, day: "2026-10-20" }) });
      if (!listed.response.ok) {
        setStatus("Times are temporarily unavailable.");
        setSlots([]);
        return;
      }
      setSlots(listed.body.slots || []);
      setStatus(listed.body.slots?.length ? "Property time is America/New_York." : "No open time is available for that day.");
    } catch {
      setStatus("Showing times are temporarily unavailable.");
      setSlots([]);
    }
  }
  return (
    <PageFrame title="Schedule a showing" testId="showing-page">
      <p>Choose a property-local time. A showing lasts 30 minutes. Self-guided entry is not available.</p>
      <form className="grid gap-3" onSubmit={loadSlots} aria-labelledby="showing-heading">
        <h2 id="showing-heading" className="font-heading text-2xl">Available times</h2>
        <label htmlFor="showing-receipt">Showing receipt
          <input id="showing-receipt" name="receipt" required className="mt-1 w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
        </label>
        <button className="w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Show times</button>
      </form>
      <p role="status">{status}</p>
      {slots.length > 0 ? (
        <ul>
          {slots.map((slot) => (
            <li key={slot.wall_start}>
              <button type="button" className="underline">{slot.wall_start} America/New_York, {slot.duration_minutes} minutes</button>
            </li>
          ))}
        </ul>
      ) : null}
    </PageFrame>
  );
}

export function ApplicationDesk() {
  const [status, setStatus] = useState("Enter an inquiry receipt to start or resume an application.");
  async function begin(event) {
    event.preventDefault();
    const receipt = new FormData(event.currentTarget).get("receipt");
    setStatus("Checking the listing and disclosure.");
    try {
      const started = await phase2("/api/v2/public/applications", {
        method: "POST",
        body: JSON.stringify({ receipt, disclosure: true, application_type: "residential", idempotency_key: `browser-${receipt}` }),
      });
      if (!started.response.ok) {
        setStatus("The application request could not be accepted.");
        return;
      }
      setStatus(started.body.replayed ? "The existing application was resumed." : "A draft application was saved.");
    } catch {
      setStatus("Applications are temporarily unavailable.");
    }
  }
  return (
    <PageFrame title="Rental application" testId="application-page">
      <p>This application collects household and document facts. It does not screen, approve, deny, collect a fee, or create a lease.</p>
      <form className="grid gap-3" onSubmit={begin} aria-labelledby="application-heading">
        <h2 id="application-heading" className="font-heading text-2xl">Start or resume</h2>
        <label htmlFor="application-receipt">Inquiry receipt
          <input id="application-receipt" name="receipt" required className="mt-1 w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
        </label>
        <button className="w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Continue application</button>
      </form>
      <p role="status">{status}</p>
    </PageFrame>
  );
}

export function ScreeningDesk() {
  const [status, setStatus] = useState("A screening decision is recorded by an authorized person. A provider does not decide.");
  return (
    <PageFrame title="Screening review" testId="screening-page">
      <p>This desk reviews a ready application. It does not order a live report, collect a fee, or create a lease.</p>
      <form aria-labelledby="screening-heading" onSubmit={(event) => { event.preventDefault(); setStatus("The screening request could not be accepted."); }}>
        <h2 id="screening-heading" className="font-heading text-2xl">Case reference</h2>
        <label htmlFor="screening-reference">Application reference
          <input id="screening-reference" name="reference" required className="mt-1 w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
        </label>
        <button className="mt-3 w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Review case</button>
      </form>
      <p role="status">{status}</p>
    </PageFrame>
  );
}
