import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { phase2 } from "@/api/phase2";
import { StatementBody } from "@/components/demo/AccountView";
import { PaymentPanel } from "@/components/demo/PaymentPanel";
import { Workspace, residentLinks, staffLinks } from "@/components/demo/RoleNav";


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
  const [state, setState] = useState("loading");
  const [rows, setRows] = useState([]);
  const [workflow, setWorkflow] = useState("All");
  async function load(event) {
    if (event) event.preventDefault();
    setState("loading");
    try {
      const demo = await staffRequest("/api/v2/demo/work");
      if (demo.response.ok) {
        setRows(demo.body.items || []);
        setState(demo.body.items?.length ? "ready" : "empty");
        return;
      }
      if (demo.response.status === 403) {
        setState("denied");
        return;
      }
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
  useEffect(() => { load(); }, []);
  const visible = rows.filter((row) => workflow === "All" || row.workflow === workflow);
  return (
    <Workspace links={staffLinks}>
    <PageFrame title="Leasing queue" testId="leasing-desk">
      <p>Operational work only. This desk does not approve housing, schedule a showing, or open an application.</p>
      <form onSubmit={load} className="flex flex-wrap items-end gap-3">
        <label>Workflow
          <select className="mt-1 block border border-stone-300 bg-white px-3 py-2" value={workflow} onChange={(event) => setWorkflow(event.target.value)}>
            {["All", "Inquiry", "Showing", "Application", "Screening", "Lease", "Dispute", "Request"].map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
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
            <tr><th scope="col">Work</th><th scope="col">Subject</th><th scope="col">Home</th><th scope="col">Status</th><th scope="col">Owner</th><th scope="col">Next action</th></tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.id || row.public_receipt}>
                <td>{row.workflow || row.stage}</td>
                <td>{row.subject || row.next_action}</td>
                <td>{row.home_label || (row.unassigned ? "Unassigned" : "Assigned")}</td>
                <td>{row.status || ""}</td>
                <td>{row.assignee || ""}</td>
                <td>{row.next_action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </PageFrame>
    </Workspace>
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
  const crumbs = slug === "faq" ? [["Renter Resources", "/resources"], ["FAQ", "/faq"]] : slug === "resources" ? [["Renter Resources", "/resources"]] : null;
  return (
    <PageFrame title={slug === "resources" ? "Renter Resources" : snapshot.title || slug} testId={testId}>
      {crumbs && <nav aria-label="Breadcrumb"><ol className="flex gap-2 text-sm">{crumbs.map(([label, href]) => <li key={href}><Link className="underline" to={href}>{label}</Link></li>)}</ol></nav>}
      <p>{text}</p>
      <p><Link className="underline" to="/sign-in" data-testid="sign-in-transition">Resident or staff sign-in</Link></p>
    </PageFrame>
  );
}

export function RentalsIndex() {
  const [params, setParams] = useSearchParams();
  const [state, setState] = useState("loading");
  const [catalog, setCatalog] = useState(null);
  const [listings, setListings] = useState([]);
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
    const query = params.toString();
    phase2(`/api/v2/public/demo/listings${query ? `?${query}` : ""}`).then(({ response, body }) => {
      if (!active) return;
      if (response.status === 404) {
        return phase2("/api/v2/listings").then((fallback) => {
          if (!active) return;
          if (!fallback.response.ok) {
            setState("unavailable");
            return;
          }
          setCatalog(null);
          setListings(fallback.body.listings || []);
          setState("ready");
        });
      }
      if (!response.ok) {
        setState("unavailable");
        setNotice("Those filters could not be applied.");
        return;
      }
      setCatalog(body);
      setListings([]);
      setNotice(body.total ? `${body.total} homes match.` : "No homes match. Remove one filter and search again.");
      setState("ready");
    }).catch(() => { if (active) setState("unavailable"); });
    return () => { active = false; };
  }, [params]);
  function applyFilters(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = new URLSearchParams();
    for (const key of ["city", "home_type", "bedrooms", "min_sqft", "max_sqft"]) {
      const value = String(form.get(key) || "").trim();
      if (value && value !== "all") next.set(key, value);
    }
    setParams(next);
  }
  function goToPage(page) {
    const next = new URLSearchParams(params);
    if (page <= 1) next.delete("page");
    else next.set("page", String(page));
    setParams(next);
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
  const page = Number(catalog?.page || 1);
  const fieldClass = "mt-1 w-full border border-stone-300 bg-white px-3 py-2 text-obsidian";
  return (
    <PageFrame title="Rentals" testId="rentals-index">
      <p>Homes shown here are the current public catalog. Filters stay in the page address, and each page shows at most 10 homes.</p>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={applyFilters}>
        <label className="block text-sm font-semibold" htmlFor="filter-city">Location
          <input id="filter-city" name="city" defaultValue={params.get("city") || ""} className={fieldClass} style={{ colorScheme: "light" }} />
        </label>
        <label className="block text-sm font-semibold" htmlFor="filter-home-type">Home type
          <select id="filter-home-type" name="home_type" defaultValue={params.get("home_type") || "all"} className={fieldClass} style={{ colorScheme: "light" }}>
            <option value="all">All</option>
            <option value="house">House</option>
            <option value="apartment">Apartment</option>
          </select>
        </label>
        <label className="block text-sm font-semibold" htmlFor="filter-bedrooms">Bedrooms
          <select id="filter-bedrooms" name="bedrooms" defaultValue={params.get("bedrooms") || "all"} className={fieldClass} style={{ colorScheme: "light" }}>
            <option value="all">All</option>
            <option value="studio">Studio</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4+</option>
          </select>
        </label>
        <fieldset className="grid grid-cols-2 gap-2">
          <legend className="text-sm font-semibold">Square footage</legend>
          <label className="text-sm" htmlFor="filter-min-sqft">Minimum
            <input id="filter-min-sqft" name="min_sqft" inputMode="numeric" defaultValue={params.get("min_sqft") || ""} className={fieldClass} style={{ colorScheme: "light" }} />
          </label>
          <label className="text-sm" htmlFor="filter-max-sqft">Maximum
            <input id="filter-max-sqft" name="max_sqft" inputMode="numeric" defaultValue={params.get("max_sqft") || ""} className={fieldClass} style={{ colorScheme: "light" }} />
          </label>
        </fieldset>
        <button className="min-h-11 bg-obsidian px-4 py-2 text-linen sm:col-span-2" type="submit">Apply filters</button>
      </form>
      <p role="status">{notice}</p>
      {catalog && (
        <ul className="grid gap-4">
          {catalog.records.map((row) => (
            <li key={row.slug} className="overflow-hidden border border-stone-200 bg-white">
              <Link to={`/rentals/${row.slug}`}>
                <img src={row.hero} alt="" width="640" height="360" className="aspect-video w-full object-cover" onError={(event) => { event.currentTarget.alt = "Photo unavailable"; event.currentTarget.style.background = "#1f2933"; }} />
                <span className="block px-4 py-3 font-heading text-xl font-bold">{row.property_name}</span>
              </Link>
              <p className="px-4 text-sm">{row.label}, {row.city} · {row.bedrooms === 0 ? "Studio" : `${row.bedrooms} bed`} · {row.sqft} sq ft · ${(row.amount_minor / 100).toLocaleString()}/month</p>
              <button className="min-h-11 px-4 py-2 underline" type="button" onClick={() => favorite(row.slug)}>Save on this device</button>
            </li>
          ))}
        </ul>
      )}
      {catalog && catalog.pages > 1 && (
        <nav aria-label="Listing pages" className="flex flex-wrap gap-2">
          <button type="button" className="min-h-11 underline" disabled={page <= 1} onClick={() => goToPage(page - 1)}>Previous</button>
          {Array.from({ length: catalog.pages }, (_, index) => (
            <button key={index + 1} type="button" className="min-h-11 min-w-11 underline" aria-current={page === index + 1 ? "page" : undefined} onClick={() => goToPage(index + 1)}>{index + 1}</button>
          ))}
          <button type="button" className="min-h-11 underline" disabled={page >= catalog.pages} onClick={() => goToPage(page + 1)}>Next</button>
        </nav>
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
      {state === "ready" && !catalog && listings.length === 0 && <p>No homes are published right now.</p>}
      {state === "ready" && !catalog && listings.length > 0 && (
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

export function ResidentHub() {
  const [status, setStatus] = useState("closed");
  const [household, setHousehold] = useState(null);
  const [portalNote, setPortalNote] = useState("A household portal opens only after activation. Demo previews do not create later records.");
  useEffect(() => {
    let active = true;
    phase2("/api/v2/demo/household").then(({ response, body }) => {
      if (!active || response.status !== 200) return;
      setHousehold(body);
      setStatus("ready");
    }).catch(() => { if (active) setStatus("closed"); });
    return () => { active = false; };
  }, []);
  const demoReady = status === "ready" && household;
  return (
    <Workspace links={residentLinks}>
    <PageFrame title={demoReady ? "Your home" : "Resident household hub"} testId="portal-page">
      {demoReady ? (
        <>
          <p><Link className="underline" to="/demo">Demo Control Center</Link></p>
          <section aria-labelledby="household-heading">
            <h2 id="household-heading" className="sr-only">Household summary</h2>
            {household.statement ? <StatementBody account={household.statement} /> : null}
            <PaymentPanel tenancyCode={household.statement?.slug} mode="resident" />
            <p>{household.guidance}</p>
            <section id="lease" className="sr-only">Lease and account</section>
            <RequestForm requests={household.requests || []} />
          </section>
        </>
      ) : (
        <>
          <p>This hub shows household access, the sample lease, and later destinations. It does not collect money, open a maintenance case, or send a message.</p>
          <p>SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION</p>
          <form aria-labelledby="portal-heading" onSubmit={(event) => { event.preventDefault(); setPortalNote("The portal request could not be accepted."); }}>
            <h2 id="portal-heading" className="font-heading text-2xl">Household reference</h2>
            <label htmlFor="portal-reference">Activation reference
              <input id="portal-reference" name="reference" required className="mt-1 w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
            </label>
            <button className="mt-3 w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Open household</button>
          </form>
          <section aria-label="Demo previews">
            <h2 className="font-heading text-2xl">Demo Preview</h2>
            <p>Balance and statements remain a Phase 16 demo preview.</p>
            <p>Payments remain a Phase 17 demo preview.</p>
            <p>Maintenance remains a later demo preview.</p>
            <p>Messages remain a later demo preview.</p>
          </section>
          <p role="status">{portalNote}</p>
        </>
      )}
    </PageFrame>
    </Workspace>
  );
}

function RequestForm({ requests }) {
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");
  async function submit(event) {
    event.preventDefault();
    setStatus("Sending the request.");
    const csrf = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
    const token = csrf ? decodeURIComponent(csrf.split("=").slice(1).join("=")) : "";
    try {
      const response = await fetch("/api/v2/demo/requests", {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json", "x-perchpoint-csrf": token },
        body: JSON.stringify({ kind: "contact", note, idempotency_key: `contact-${Date.now()}` }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setStatus(body.detail?.message || "The request was not saved.");
        return;
      }
      setStatus(`Saved. Status: ${body.state}. Staff can review it from the work queue.`);
      setNote("");
    } catch {
      setStatus("The request could not be sent.");
    }
  }
  return (
    <section id="requests" className="rounded-md border border-[#D9E2EF] bg-white p-5">
      <h2 className="font-heading text-2xl font-bold">Request a contact change</h2>
      <p>Staff review this request. It does not change the lease.</p>
      <form className="mt-3 space-y-3" onSubmit={submit}>
        <label className="block">What should staff update?
          <textarea className="mt-1 w-full border border-[#D9E2EF] px-3 py-2" minLength={8} required value={note} onChange={(event) => setNote(event.target.value)} />
        </label>
        <button className="bg-[#2457D6] px-4 py-2 text-white" type="submit">Submit request</button>
      </form>
      {status ? <p role="status">{status}</p> : null}
      <ul className="mt-4 space-y-2">
        {requests.map((item) => <li key={item.id}>{item.kind}: {item.note} — {item.state}</li>)}
      </ul>
    </section>
  );
}

export function LedgerDesk() {
  const [status, setStatus] = useState("closed");
  const [accounts, setAccounts] = useState([]);
  const [selected, setSelected] = useState("");
  const [ledgerNote, setLedgerNote] = useState("A balance is derived from posted journal lines. A person cannot type an authoritative balance.");
  useEffect(() => {
    let active = true;
    phase2("/api/v2/demo/accounts").then(({ response, body }) => {
      if (!active || !response.ok) return;
      const rows = body.accounts || [];
      setAccounts(rows);
      setSelected(rows[0]?.slug || "");
      setStatus("ready");
    }).catch(() => { if (active) setStatus("closed"); });
    return () => { active = false; };
  }, []);
  const demoReady = status === "ready";
  return (
    <Workspace links={staffLinks}>
    <PageFrame title={demoReady ? "Resident accounts" : "Resident ledger"} testId="ledger-page">
      {demoReady ? <p>These balances come from the October 2026 demonstration lines. A synthetic settlement is not cash received, and no money has moved.</p> : (
        <>
          <p>This desk posts synthetic operational charges and statements. It does not move money or call a payment processor.</p>
          <p>SYNTHETIC OPERATIONAL STATEMENT — NOT A TAX RETURN — NOT A FORMAL GENERAL LEDGER</p>
          <form aria-labelledby="ledger-heading" onSubmit={(event) => { event.preventDefault(); setLedgerNote("The ledger request could not be accepted."); }}>
            <h2 id="ledger-heading" className="font-heading text-2xl">Account reference</h2>
            <label htmlFor="ledger-reference">Household reference
              <input id="ledger-reference" name="reference" required className="mt-1 w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
            </label>
            <button className="mt-3 w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Post charge</button>
          </form>
          <table>
            <caption>Derived positions</caption>
            <thead>
              <tr><th scope="col">Position</th><th scope="col">Meaning</th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">Due</th><td>Open receivable after posted lines</td></tr>
              <tr><th scope="row">Prepayment</th><td>Unapplied synthetic settlement remainder</td></tr>
            </tbody>
          </table>
          <p role="status">{ledgerNote}</p>
        </>
      )}
      {demoReady && (
        <table className="w-full text-left">
          <caption className="sr-only">Twenty resident accounts as of 2026-10-10</caption>
          <thead><tr><th scope="col">Household</th><th scope="col">Home</th><th scope="col">Status</th><th scope="col">Amount due</th></tr></thead>
          <tbody>
            {accounts.map((row) => (
              <tr key={row.slug}>
                <td>{row.person_label}</td>
                <td><Link className="underline" to={`/owner/accounts/${row.slug}`}>{row.home_label}</Link></td>
                <td>{row.status}</td>
                <td>{(row.due_minor / 100).toLocaleString(undefined, { style: "currency", currency: "USD" })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {status === "ready" && selected ? (
        <>
          <label className="mt-6 block">Household
            <select className="mt-1 w-full border border-[#D9E2EF] bg-white px-3 py-2" value={selected} onChange={(event) => setSelected(event.target.value)}>
              {accounts.map((row) => <option key={row.slug} value={row.slug}>{row.person_label} — {row.home_label}</option>)}
            </select>
          </label>
          <PaymentPanel tenancyCode={selected} mode="staff" />
        </>
      ) : null}
    </PageFrame>
    </Workspace>
  );
}

export function LeaseDesk() {
  const [status, setStatus] = useState("A person approves the lease package. A signature provider does not activate a resident.");
  return (
    <PageFrame title="Lease preparation" testId="lease-page">
      <p>This desk prepares a lease from an approved screening handoff. It does not collect a deposit or open a resident portal.</p>
      <form aria-labelledby="lease-heading" onSubmit={(event) => { event.preventDefault(); setStatus("The lease request could not be accepted."); }}>
        <h2 id="lease-heading" className="font-heading text-2xl">Handoff reference</h2>
        <label htmlFor="lease-reference">Screening reference
          <input id="lease-reference" name="reference" required className="mt-1 w-full border border-stone-300 bg-white px-3 py-2 text-obsidian" style={{ colorScheme: "light" }} />
        </label>
        <button className="mt-3 w-fit bg-obsidian px-4 py-2 text-linen" type="submit">Prepare lease</button>
      </form>
      <p role="status">{status}</p>
    </PageFrame>
  );
}
