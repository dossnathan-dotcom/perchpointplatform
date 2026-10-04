import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

const NAV = [
  ["onboarding", "Access summary"],
  ["security", "Security Center"],
  ["users-access", "Users and Access"],
  ["delegations", "Delegation Center"],
  ["access-requests", "Access requests"],
  ["access-reviews", "Access reviews"],
  ["vendor-access", "Vendor access"],
  ["maintenance-history", "Maintenance history"],
];

const inputClass = "mt-1 w-full rounded border border-white/40 bg-transparent px-3 py-2";
const buttonClass = "rounded border border-white/50 px-4 py-2 hover:bg-white/10 disabled:opacity-60";

function csrf() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

export async function phase6Api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    ...options,
    headers: {
      ...(options.body ? { "content-type": "application/json" } : {}),
      ...(options.method && options.method !== "GET" ? { "x-perchpoint-csrf": csrf() } : {}),
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) {
      sessionStorage.removeItem("pp_active_context");
      sessionStorage.removeItem("pp_session_started_at");
      window.dispatchEvent(new Event("perchpoint:session-expired"));
    }
    const error = new Error(body.detail?.message || "The request could not be completed.");
    error.code = body.detail?.code || `http_${response.status}`;
    error.status = response.status;
    error.correlationId = response.headers.get("x-request-id") || response.headers.get("x-correlation-id") || "";
    throw error;
  }
  if (path.startsWith("/api/v2/")) sessionStorage.setItem("pp_session_last_authorized_at", String(Date.now()));
  return body;
}

function useSafeDraft(key, initial) {
  const [value, setValue] = useState(initial);
  const clear = () => {
    setValue(initial);
  };
  void key;
  return [value, setValue, clear];
}

function ErrorSummary({ error, retry }) {
  const ref = useRef(null);
  useEffect(() => { ref.current?.focus(); }, [error]);
  if (!error) return null;
  return (
    <div ref={ref} tabIndex="-1" role="alert" className="my-5 border border-rose-300 bg-rose-950/40 p-4">
      <h2 className="font-semibold">This section could not be completed</h2>
      <p className="mt-1">{error.message}</p>
      {error.correlationId ? <p className="mt-1 text-sm">Correlation ID: <code>{error.correlationId}</code></p> : null}
      {retry ? <button type="button" className={`${buttonClass} mt-3`} onClick={retry}>Try again</button> : null}
    </div>
  );
}

function SectionState({ loading, items, empty = "No records are available." }) {
  if (loading) return <p role="status">Loading…</p>;
  if (!items?.length) return <p role="status">{empty}</p>;
  return null;
}

export function SessionClock({ role }) {
  const navigate = useNavigate();
  const [remaining, setRemaining] = useState(null);
  const [announcement, setAnnouncement] = useState("");
  useEffect(() => {
    const started = Number(sessionStorage.getItem("pp_session_started_at"));
    if (!started) return undefined;
    const privileged = ["owner", "platform_admin"].includes(role);
    const idleDuration = (privileged ? 15 : 60) * 60 * 1000;
    const absoluteDuration = (privileged ? 8 : 24) * 60 * 60 * 1000;
    const tick = () => {
      const lastAuthorized = Number(sessionStorage.getItem("pp_session_last_authorized_at")) || started;
      const deadline = Math.min(lastAuthorized + idleDuration, started + absoluteDuration);
      const next = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemaining(next);
      if (next === 300) setAnnouncement("Session expires in five minutes.");
      if (next === 60) setAnnouncement("Session expires in one minute.");
      if (next === 0) setAnnouncement("Session expired.");
      if (next === 0) navigate("/session-expired?draft=preserved", { replace: true });
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [navigate, role]);
  if (remaining === null || remaining > 300) return null;
  const minutes = Math.floor(remaining / 60);
  const seconds = String(remaining % 60).padStart(2, "0");
  return (
    <aside aria-live="off" className="border-b border-amber-300 bg-amber-950 px-5 py-3 text-linen">
      <span className="sr-only" role="status" aria-live="polite">{announcement}</span>
      Session expires in {minutes}:{seconds}. Safe, non-sensitive form drafts remain in this browser tab.{" "}
      <Link className="underline" to="/sign-in">Sign in again</Link>
    </aside>
  );
}

function ContextBar({ me, contexts, onSwitch, busy }) {
  const available = contexts.length ? contexts : [me];
  return (
    <section aria-label="Active access context" className="border border-white/25 bg-white/5 p-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <p><span className="block text-xs uppercase text-linen/70">Organization</span>{me.organization_id}</p>
        <p><span className="block text-xs uppercase text-linen/70">Role</span>{me.role_name}</p>
        <p><span className="block text-xs uppercase text-linen/70">Scope</span>Current membership</p>
        <p><span className="block text-xs uppercase text-linen/70">Authority</span>{me.assurance === "aal2" ? "Elevated (AAL2)" : "Standard (AAL1)"}</p>
      </div>
      <label className="mt-4 block max-w-lg">Switch access context
          <select className={inputClass} value={me.membership_id} disabled={busy || available.length < 2} aria-describedby="context-help" onChange={(event) => onSwitch(event.target.value)}>
            {available.map((item) => <option key={item.membership_id} value={item.membership_id} label={`${item.role_name} — ${item.organization_id}`} />)}
          </select>
      </label>
      <p id="context-help" className="mt-2 text-sm text-linen/70">{available.length < 2 ? "Switching is unavailable because no additional current membership is exposed by the authorized directory." : "Changing context updates the server-authorized organization and role."}</p>
    </section>
  );
}

function Onboarding({ me }) {
  const [factors, setFactors] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const loadFactors = useCallback(() => {
    setLoading(true); setError(null);
    phase6Api("/api/v2/auth/mfa/factors").then((body) => setFactors(body.factors || [])).catch(setError).finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    loadFactors();
  }, [loadFactors]);
  const checks = [
    ["Invitation and identity", "Validated by the server before this session was opened."],
    ["Credentials", "Established; passwords are never displayed or retained by this page."],
    ["Multi-factor authentication", loading ? "Checking factor status…" : factors.some((item) => item.confirmed_at) || me.assurance === "aal2" ? "Confirmed." : "Setup still required for protected work."],
    ["Policies", "Policy acceptance state is unavailable because the Phase 6 API does not expose it."],
    ["Profile", `Account ${me.account_id}; profile editing is unavailable because the API does not expose it.`],
    ["Access summary", `${me.role_name} in organization ${me.organization_id}, current membership ${me.membership_id}.`],
  ];
  return <section aria-labelledby="onboarding-title">
    <h2 id="onboarding-title" className="text-2xl">First access checklist</h2>
    <ErrorSummary error={error} retry={loadFactors} />
    <ol className="mt-5 grid gap-3 md:grid-cols-2">
      {checks.map(([label, detail]) => <li className="border border-white/20 p-4" key={label}><strong>{label}</strong><p className="mt-1 text-sm text-linen/75">{detail}</p></li>)}
    </ol>
    <div className="mt-6 flex flex-wrap gap-3">
      <Link className={buttonClass} to="/mfa">Manage MFA</Link>
      <Link className={buttonClass} to="/access/security">Review security</Link>
    </div>
  </section>;
}

function SecurityCenter() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [factors, setFactors] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventUnavailable, setEventUnavailable] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState("");
  const [status, setStatus] = useState("");
  const [codes, setCodes] = useState([]);
  const [email, setEmail] = useState("");
  const load = async () => {
    setLoading(true); setError(null);
    try {
      const [sessionBody, factorBody] = await Promise.all([phase6Api("/api/v2/me/sessions"), phase6Api("/api/v2/auth/mfa/factors")]);
      setSessions(sessionBody.sessions || []);
      setFactors(factorBody.factors || []);
      try {
        const eventBody = await phase6Api("/api/v2/access/security-events");
        setEvents(eventBody.events || []);
        setEventUnavailable("");
      } catch (eventError) {
        setEventUnavailable(eventError.status === 403 || eventError.status === 404 ? "Security events are unavailable in this access context." : eventError.message);
      }
    } catch (loadError) { setError(loadError); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const action = async (path, confirmation, options = {}) => {
    if (!window.confirm(confirmation)) return;
    setPending(path); setStatus("");
    setError(null);
    try { await phase6Api(path, { method: "POST", ...options }); setStatus("The security action completed."); await load(); }
    catch (actionError) { setError(actionError); }
    finally { setPending(""); }
  };
  const signOut = async () => {
    if (!window.confirm("Sign out this browser session now?")) return;
    setPending("sign-out");
    try {
      await phase6Api("/api/v2/auth/sign-out", { method: "POST" });
      sessionStorage.removeItem("pp_session_started_at");
      sessionStorage.removeItem("pp_active_context");
      navigate("/sign-in", { replace: true });
    } catch (actionError) { setError(actionError); setPending(""); }
  };
  const generateCodes = async () => {
    if (!window.confirm("Generate new recovery codes and revoke other sessions?")) return;
    setPending("codes");
    try { setCodes((await phase6Api("/api/v2/auth/recovery-codes", { method: "POST" })).codes || []); setStatus("New recovery codes were generated."); }
    catch (actionError) { setError(actionError); }
    finally { setPending(""); }
  };
  const removeFactor = async (factorId) => {
    if (!window.confirm("Remove this authentication factor and sign out all affected sessions?")) return;
    setPending(`factor-${factorId}`);
    try {
      await phase6Api(`/api/v2/auth/mfa/factors/${factorId}`, { method: "DELETE" });
      navigate("/sign-in", { replace: true });
    } catch (actionError) { setError(actionError); setPending(""); }
  };
  const changeEmail = async (event) => {
    event.preventDefault();
    try {
      await phase6Api("/api/v2/auth/contact/email-change", { method: "POST", body: JSON.stringify({ email }) });
      setEmail("");
    } catch (actionError) { setError(actionError); }
  };
  return <div className="space-y-8">
    <ErrorSummary error={error} retry={load} />
    <p role="status" aria-live="polite">{status || (pending ? "Security action in progress…" : "")}</p>
    <section aria-labelledby="sessions-title">
      <h2 id="sessions-title" className="text-2xl">Devices and sessions</h2>
      <SectionState loading={loading} items={sessions} empty="No sessions are available." />
      <ul className="mt-4 space-y-3">{sessions.map((item) => <li className="flex flex-wrap items-center justify-between gap-3 border border-white/20 p-4" key={item.id}>
        <span><strong>{item.device_label || "Browser session"}</strong><span className="block text-sm text-linen/70">{item.revoked ? "Revoked" : "Active"}</span></span>
        {!item.revoked ? <button className={buttonClass} disabled={Boolean(pending)} type="button" onClick={() => action(`/api/v2/me/sessions/${item.id}/revoke`, "Revoke this session immediately?")}>Revoke session</button> : null}
      </li>)}</ul>
      <button className={`${buttonClass} mt-4`} disabled={Boolean(pending)} type="button" onClick={() => action("/api/v2/me/sessions/revoke-others", "Sign out every other session now?")}>Sign out all other sessions</button>
    </section>
    <section aria-labelledby="factors-title">
      <h2 id="factors-title" className="text-2xl">Authentication factors</h2>
      <SectionState loading={loading} items={factors} empty="No authenticator factor is enrolled." />
      <ul className="mt-4 space-y-3">{factors.map((factor) => <li className="flex flex-wrap items-center justify-between gap-3 border border-white/20 p-4" key={factor.provider_factor_id}>
        <span><strong>Authenticator</strong> — {factor.confirmed_at ? "Confirmed" : "Pending"}</span>
        <button className={buttonClass} disabled={Boolean(pending)} type="button" onClick={() => removeFactor(factor.provider_factor_id)}>Remove factor and sign out</button>
      </li>)}</ul>
      <div className="mt-4 flex flex-wrap gap-3"><Link className={buttonClass} to="/mfa">Add or verify factor</Link><button className={buttonClass} disabled={Boolean(pending)} type="button" onClick={generateCodes}>Generate new recovery codes</button></div>
      {codes.length ? <div className="mt-4 border border-amber-300 p-4"><p><strong>Save these one-time codes now.</strong> Generating them revoked other sessions.</p><ul className="mt-3 grid grid-cols-2 gap-2 font-mono">{codes.map((code) => <li key={code}>{code}</li>)}</ul></div> : null}
    </section>
    <section aria-labelledby="contact-title">
      <h2 id="contact-title" className="text-2xl">Verified contact</h2>
      <p className="mt-1 text-sm text-linen/70">Changing email requires elevated assurance and separate provider verification.</p>
      <form className="mt-4 flex max-w-xl flex-col gap-3 sm:flex-row sm:items-end" onSubmit={changeEmail}>
        <label className="flex-1">New email<input className={inputClass} type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <button className={buttonClass} type="submit">Request email change</button>
      </form>
    </section>
    <section aria-labelledby="events-title">
      <h2 id="events-title" className="text-2xl">Security events</h2>
      {eventUnavailable ? <p role="status" className="mt-2">{eventUnavailable}</p> : <SectionState loading={loading} items={events} empty="No security events are visible." />}
      <ul className="mt-4 space-y-2">{events.map((item) => <li className="border border-white/20 p-3" key={item.id}><strong>{item.action}</strong> — {item.outcome}{item.reason_code ? ` (${item.reason_code})` : ""}</li>)}</ul>
    </section>
    <section aria-labelledby="password-title"><h2 id="password-title" className="text-2xl">Password and sign-out</h2><div className="mt-4 flex flex-wrap gap-3"><Link className={buttonClass} to="/password-reset">Change password</Link><button className={buttonClass} disabled={Boolean(pending)} type="button" onClick={signOut}>Sign out this session</button></div></section>
  </div>;
}

function UsersAccess() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reason, setReason] = useState({});
  const [pending, setPending] = useState("");
  const [status, setStatus] = useState("");
  const load = () => {
    setLoading(true); setError(null);
    phase6Api("/api/v2/access/users").then((body) => setUsers(body.users || [])).catch(setError).finally(() => setLoading(false));
  };
  useEffect(load, []);
  const lifecycle = async (accountId, action) => {
    if (!window.confirm(`${action === "suspend" ? "Suspend" : "Restore"} this identity? Active sessions and access may change immediately.`)) return;
    setPending(accountId); setStatus("");
    try {
      await phase6Api(`/api/v2/access/users/${accountId}/${action}`, { method: "POST", body: JSON.stringify({ reason: reason[accountId] || "" }) });
      setReason((current) => ({ ...current, [accountId]: "" }));
      await load();
      setStatus(`Identity ${action} completed.`);
    } catch (actionError) { setError(actionError); }
    finally { setPending(""); }
  };
  return <section aria-labelledby="directory-title"><h2 id="directory-title" className="text-2xl">Authorized directory</h2><ErrorSummary error={error} retry={load} /><SectionState loading={loading} items={users} />
    <p role="status" aria-live="polite">{status || (pending ? "Identity change in progress…" : "")}</p>
    <ul className="mt-4 space-y-3">{users.map((user) => <li className="border border-white/20 p-4" key={user.membership_id}><strong>{user.email}</strong><p className="text-sm text-linen/70">{user.role_name} · {user.lifecycle_status}{user.is_self ? " · current account" : ""}</p>
      <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-end"><label>Lifecycle reason<input className={inputClass} disabled={user.is_self || Boolean(pending)} value={reason[user.account_id] || ""} onChange={(event) => setReason((current) => ({ ...current, [user.account_id]: event.target.value }))} /></label>{user.can_suspend ? <button className={buttonClass} disabled={Boolean(pending) || !(reason[user.account_id] || "").trim()} type="button" onClick={() => lifecycle(user.account_id, "suspend")}>Suspend</button> : <span className="text-sm text-linen/70">Suspend unavailable</span>}{user.can_restore ? <button className={buttonClass} disabled={Boolean(pending) || !(reason[user.account_id] || "").trim()} type="button" onClick={() => lifecycle(user.account_id, "restore")}>Restore</button> : <span className="text-sm text-linen/70">Restore unavailable</span>}</div>
    </li>)}</ul>
  </section>;
}

function Delegations({ me }) {
  const initial = { grantee_id: "", capability: "", reason: "", days: "7", amount_ceiling_minor: "", resource_type: "property", resource_id: "", decision_types: "", approval_id: "" };
  const [draft, setDraft, clearDraft] = useSafeDraft("delegation", initial);
  const [items, setItems] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState("");
  const [status, setStatus] = useState("");
  const load = async () => {
    setLoading(true); setError(null);
    try {
      const body = await phase6Api("/api/v2/access/delegations");
      setItems(body.delegations || []);
      try { setUsers((await phase6Api("/api/v2/access/users")).users || []); } catch { setUsers([]); }
    } catch (loadError) { setError(loadError); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const submit = async (event) => {
    event.preventDefault();
    const payload = { ...draft, days: Number(draft.days), amount_ceiling_minor: draft.amount_ceiling_minor ? Number(draft.amount_ceiling_minor) : null, resource_id: draft.resource_id || null, decision_types: draft.decision_types.split(",").map((item) => item.trim()).filter(Boolean) };
    if (!window.confirm("Create this bounded delegation with the selected independent owner approval?")) return;
    setPending("create"); setStatus("");
    try { await phase6Api("/api/v2/access/delegations", { method: "POST", body: JSON.stringify(payload) }); clearDraft(); setStatus("Delegation created."); await load(); }
    catch (actionError) { setError(actionError); }
    finally { setPending(""); }
  };
  const revoke = async (id) => {
    if (!window.confirm("Revoke this delegation immediately?")) return;
    setPending(id); setStatus("");
    try { await phase6Api(`/api/v2/access/delegations/${id}/revoke`, { method: "POST" }); setStatus("Delegation revoked."); await load(); } catch (actionError) { setError(actionError); }
    finally { setPending(""); }
  };
  return <div className="space-y-8"><ErrorSummary error={error} retry={load} />
    <p role="status" aria-live="polite">{status || (pending ? "Delegation change in progress…" : "")}</p>
    <section aria-labelledby="grants-title"><h2 id="grants-title" className="text-2xl">Incoming and outgoing grants</h2><SectionState loading={loading} items={items} empty="No delegation grants are visible." />
      <ul className="mt-4 space-y-3">{items.map((item) => <li className="border border-white/20 p-4" key={item.id}><strong>{item.capability}</strong><p className="text-sm text-linen/70">{item.grantor_id === me.account_id ? "Outgoing" : "Incoming"} · {item.status} · expires {String(item.ends_at)}</p><p>{item.reason}</p><p className="text-sm">Limit: {item.amount_ceiling_minor == null ? "No monetary limit recorded" : `${item.amount_ceiling_minor} minor units`}</p>{item.status === "active" ? <button className={`${buttonClass} mt-3`} disabled={Boolean(pending)} type="button" onClick={() => revoke(item.id)}>Revoke grant</button> : null}</li>)}</ul>
      <p className="mt-3 text-sm text-linen/70">Usage is audited by the server; aggregate usage details are unavailable from the current listing API.</p>
    </section>
    <section aria-labelledby="create-grant-title"><h2 id="create-grant-title" className="text-2xl">Create bounded delegation</h2>
      <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={submit}>
        <label>Grantee{users.length ? <select className={inputClass} required value={draft.grantee_id} onChange={(e) => setDraft({ ...draft, grantee_id: e.target.value })}><option value="">Choose a person</option>{users.filter((item) => item.account_id !== me.account_id).map((item) => <option key={item.account_id} value={item.account_id} label={item.email} />)}</select> : <input className={inputClass} required value={draft.grantee_id} onChange={(e) => setDraft({ ...draft, grantee_id: e.target.value })} />}</label>
        <label>Capability<input className={inputClass} required value={draft.capability} onChange={(e) => setDraft({ ...draft, capability: e.target.value })} /></label>
        <label>Duration in days<input className={inputClass} type="number" min="1" max="30" required value={draft.days} onChange={(e) => setDraft({ ...draft, days: e.target.value })} /></label>
        <label>Amount ceiling, minor units<input className={inputClass} required type="number" min="0" max="120000" value={draft.amount_ceiling_minor} onChange={(e) => setDraft({ ...draft, amount_ceiling_minor: e.target.value })} /></label>
        <label>Resource type<input className={inputClass} required value={draft.resource_type} onChange={(e) => setDraft({ ...draft, resource_type: e.target.value })} /></label>
        <label>Resource ID<input className={inputClass} required value={draft.resource_id} onChange={(e) => setDraft({ ...draft, resource_id: e.target.value })} /></label>
        <label>Independent owner approval{users.length ? <select className={inputClass} required value={draft.approval_id} onChange={(e) => setDraft({ ...draft, approval_id: e.target.value })}><option value="">Choose an owner</option>{users.filter((item) => item.role_name === "owner" && item.account_id !== me.account_id && item.account_id !== draft.grantee_id).map((item) => <option key={item.account_id} value={item.account_id} label={item.email} />)}</select> : <input className={inputClass} required value={draft.approval_id} onChange={(e) => setDraft({ ...draft, approval_id: e.target.value })} />}</label>
        <label className="md:col-span-2">Decision types, comma separated<input className={inputClass} required value={draft.decision_types} onChange={(e) => setDraft({ ...draft, decision_types: e.target.value })} /></label>
        <label className="md:col-span-2">Reason<textarea className={inputClass} required value={draft.reason} onChange={(e) => setDraft({ ...draft, reason: e.target.value })} /></label>
        <button className={`${buttonClass} md:col-span-2 md:justify-self-start`} disabled={Boolean(pending)} type="submit">Create delegation</button>
      </form>
    </section>
  </div>;
}

function AccessRequests({ me }) {
  const [params] = useSearchParams();
  const initial = { purpose: "", capability: "", scope_type: "organization", scope_resource_id: "", duration_hours: "24", justification: "" };
  const [draft, setDraft, clearDraft] = useSafeDraft("access_request", initial);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState("");
  const [status, setStatus] = useState("");
  const load = () => { setLoading(true); setError(null); phase6Api("/api/v2/access/requests").then((body) => setItems(body.requests || [])).catch(setError).finally(() => setLoading(false)); };
  useEffect(load, []);
  useEffect(() => {
    if (params.get("purpose") || params.get("scope") || params.get("capability")) {
      setDraft((current) => ({
        ...current,
        purpose: current.purpose || params.get("purpose") || "",
        scope_resource_id: current.scope_resource_id || params.get("scope") || "",
        capability: current.capability || params.get("capability") || "",
      }));
    }
  }, [params, setDraft]);
  const submit = async (event) => {
    event.preventDefault();
    const payload = {
      capability: draft.capability,
      purpose: draft.purpose,
      scope_type: draft.scope_type,
      scope_resource_id: draft.scope_resource_id || null,
      duration_hours: Number(draft.duration_hours),
      justification: draft.justification,
    };
    try { await phase6Api("/api/v2/access/requests", { method: "POST", body: JSON.stringify(payload) }); clearDraft(); await load(); }
    catch (actionError) { setError(actionError); }
  };
  const decide = async (id, approve) => {
    if (!window.confirm(`${approve ? "Approve" : "Deny"} this access request?`)) return;
    setPending(id); setStatus("");
    try { await phase6Api(`/api/v2/access/requests/${id}`, { method: "POST", body: JSON.stringify({ approve }) }); setStatus(`Access request ${approve ? "approved" : "denied"}.`); await load(); } catch (actionError) { setError(actionError); }
    finally { setPending(""); }
  };
  return <div className="space-y-8"><ErrorSummary error={error} retry={load} /><section aria-labelledby="request-title"><h2 id="request-title" className="text-2xl">Request access</h2><p className="mt-2 text-sm text-linen/70">Purpose, scope, duration, and justification are enforced as separate server fields.</p>
    <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={submit}>
      <label>Purpose<input className={inputClass} required value={draft.purpose} onChange={(e) => setDraft({ ...draft, purpose: e.target.value })} /></label><label>Capability<input className={inputClass} required value={draft.capability} onChange={(e) => setDraft({ ...draft, capability: e.target.value })} /></label><label>Scope type<input className={inputClass} required value={draft.scope_type} onChange={(e) => setDraft({ ...draft, scope_type: e.target.value })} /></label><label>Scope resource ID (optional)<input className={inputClass} value={draft.scope_resource_id} onChange={(e) => setDraft({ ...draft, scope_resource_id: e.target.value })} /></label><label>Duration in hours<input className={inputClass} type="number" min="1" max="720" required value={draft.duration_hours} onChange={(e) => setDraft({ ...draft, duration_hours: e.target.value })} /></label><label className="md:col-span-2">Justification<textarea className={inputClass} required value={draft.justification} onChange={(e) => setDraft({ ...draft, justification: e.target.value })} /></label><button className={`${buttonClass} md:col-span-2 md:justify-self-start`} type="submit">Submit access request</button>
    </form></section>
    <section aria-labelledby="request-list-title"><h2 id="request-list-title" className="text-2xl">Request details and decisions</h2><p role="status" aria-live="polite">{status || (pending ? "Access decision in progress…" : "")}</p><SectionState loading={loading} items={items} empty="No access requests are visible." /><ul className="mt-4 space-y-3">{items.map((item) => <li className="border border-white/20 p-4" key={item.id}><strong>{item.capability}</strong><p className="whitespace-pre-line">{item.justification}</p><p className="text-sm text-linen/70">Status: {item.status}{item.requested_until ? ` · until ${item.requested_until}` : ""}</p>{item.status === "pending" && item.requester_id !== me.account_id ? <div className="mt-3 flex gap-3"><button className={buttonClass} disabled={Boolean(pending)} type="button" onClick={() => decide(item.id, true)}>Approve</button><button className={buttonClass} disabled={Boolean(pending)} type="button" onClick={() => decide(item.id, false)}>Deny</button></div> : item.status === "pending" ? <p className="mt-2 text-sm text-linen/70">You cannot decide your own request.</p> : null}</li>)}</ul></section>
  </div>;
}

function AccessReviews() {
  const [campaigns, setCampaigns] = useState([]);
  const [itemIds, setItemIds] = useState({});
  const [changes, setChanges] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState("");
  const [status, setStatus] = useState("");
  const load = () => { setLoading(true); setError(null); phase6Api("/api/v2/access/reviews").then((body) => setCampaigns(body.reviews || [])).catch(setError).finally(() => setLoading(false)); };
  useEffect(load, []);
  const decide = async (campaign, decision) => {
    if (!window.confirm(`${decision === "attest" ? "Attest" : decision === "revoke" ? "Revoke" : "Require a change to"} this reviewed access?`)) return;
    setPending(campaign.id); setStatus("");
    try { await phase6Api(`/api/v2/access/reviews/${campaign.id}/items/${itemIds[campaign.id]}`, { method: "POST", body: JSON.stringify({ decision, change: decision === "change" ? { description: changes[campaign.id] } : {} }) }); setStatus("Access review decision recorded."); await load(); }
    catch (actionError) { setError(actionError); }
    finally { setPending(""); }
  };
  return <section aria-labelledby="reviews-title"><h2 id="reviews-title" className="text-2xl">Access review campaigns</h2><p className="mt-2 text-sm text-linen/70">The API lists campaign totals but does not list review items. Enter an item ID from the authorized review notice to act on it.</p><ErrorSummary error={error} retry={load} /><p role="status" aria-live="polite">{status || (pending ? "Review decision in progress…" : "")}</p><SectionState loading={loading} items={campaigns} empty="No access review campaigns are open." /><ul className="mt-4 space-y-3">{campaigns.map((campaign) => <li className="border border-white/20 p-4" key={campaign.id}><strong>{campaign.title}</strong><p>{campaign.pending_count} pending of {campaign.item_count}; due {String(campaign.due_at)}</p><label className="mt-3 block">Review item ID<input className={inputClass} required value={itemIds[campaign.id] || ""} onChange={(e) => setItemIds({ ...itemIds, [campaign.id]: e.target.value })} /></label><label className="mt-3 block">Required change (for change decision)<input className={inputClass} value={changes[campaign.id] || ""} onChange={(e) => setChanges({ ...changes, [campaign.id]: e.target.value })} /></label><div className="mt-3 flex flex-wrap gap-3"><button className={buttonClass} disabled={Boolean(pending) || !itemIds[campaign.id]} type="button" onClick={() => decide(campaign, "attest")}>Attest</button><button className={buttonClass} disabled={Boolean(pending) || !itemIds[campaign.id]} type="button" onClick={() => decide(campaign, "revoke")}>Revoke access</button><button className={buttonClass} disabled={Boolean(pending) || !itemIds[campaign.id] || !changes[campaign.id]} type="button" onClick={() => decide(campaign, "change")}>Require change</button></div></li>)}</ul></section>;
}

function VendorAccess() {
  const initial = { vendor_relationship_id: "", email: "", role_name: "technician", property_id: "", starts_at: "", ends_at: "" };
  const [draft, setDraft, clearDraft] = useSafeDraft("vendor_proposal", initial);
  const [proposalId, setProposalId] = useState("");
  const [purpose, setPurpose] = useState("");
  const [workers, setWorkers] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState("");
  const [status, setStatus] = useState("");
  useEffect(() => { phase6Api("/api/v2/access/users").then((body) => setWorkers((body.users || []).filter((item) => ["vendor_admin", "vendor_worker", "technician", "cleaner"].includes(item.role_name)))).catch(setError).finally(() => setLoading(false)); }, []);
  const propose = async (event) => {
    event.preventDefault();
    try {
      const body = await phase6Api("/api/v2/access/vendor/workers/proposals", { method: "POST", body: JSON.stringify({ ...draft, property_id: draft.property_id || null, starts_at: new Date(draft.starts_at).toISOString(), ends_at: new Date(draft.ends_at).toISOString() }) });
      setProposalId(body.proposal_id); clearDraft();
    } catch (actionError) { setError(actionError); }
  };
  const decide = async (approve) => {
    if (!window.confirm(`${approve ? "Approve and invite" : "Deny"} this worker proposal?`)) return;
    setPending("decision"); setStatus("");
    try { await phase6Api(`/api/v2/access/vendor/workers/proposals/${proposalId}`, { method: "POST", body: JSON.stringify({ approve, purpose }) }); setProposalId(""); setPurpose(""); setStatus(`Worker proposal ${approve ? "approved" : "denied"}.`); } catch (actionError) { setError(actionError); }
    finally { setPending(""); }
  };
  return <div className="space-y-8"><ErrorSummary error={error} /><p role="status" aria-live="polite">{status || (pending ? "Vendor access decision in progress…" : "")}</p><section aria-labelledby="vendor-directory-title"><h2 id="vendor-directory-title" className="text-2xl">Active vendor identities</h2><SectionState loading={loading} items={workers} empty="No vendor workers are visible in the authorized directory." /><ul className="mt-4 space-y-2">{workers.map((worker) => <li className="border border-white/20 p-3" key={worker.membership_id}><strong>{worker.email}</strong> — {worker.role_name}</li>)}</ul><p className="mt-2 text-sm text-linen/70">Assignment details and automatic completion/cancellation expiry are enforced by the backend but are not exposed by a listing API.</p></section>
    <section aria-labelledby="propose-title"><h2 id="propose-title" className="text-2xl">Propose a worker assignment</h2><form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={propose}><label>Vendor relationship ID<input className={inputClass} required value={draft.vendor_relationship_id} onChange={(e) => setDraft({ ...draft, vendor_relationship_id: e.target.value })} /></label><label>Worker email<input className={inputClass} type="email" required value={draft.email} onChange={(e) => setDraft({ ...draft, email: e.target.value })} /></label><label>Role<select className={inputClass} value={draft.role_name} onChange={(e) => setDraft({ ...draft, role_name: e.target.value })}><option value="vendor_worker">Vendor worker</option><option value="technician">Technician</option><option value="cleaner">Cleaner</option></select></label><label>Property ID (optional)<input className={inputClass} value={draft.property_id} onChange={(e) => setDraft({ ...draft, property_id: e.target.value })} /></label><label>Starts at<input className={inputClass} type="datetime-local" required value={draft.starts_at} onChange={(e) => setDraft({ ...draft, starts_at: e.target.value })} /></label><label>Access ends at<input className={inputClass} type="datetime-local" required value={draft.ends_at} onChange={(e) => setDraft({ ...draft, ends_at: e.target.value })} /></label><button className={`${buttonClass} md:col-span-2 md:justify-self-start`} type="submit">Propose worker</button></form></section>
    <section aria-labelledby="proposal-decision-title"><h2 id="proposal-decision-title" className="text-2xl">Approve or deny proposal</h2><p className="mt-2 text-sm text-linen/70">Proposal listing is not exposed by the API. Use the proposal ID from the vendor submission or approval notice.</p><div className="mt-4 grid gap-4 md:grid-cols-2"><label>Proposal ID<input className={inputClass} value={proposalId} onChange={(e) => setProposalId(e.target.value)} /></label><label>Decision purpose<input className={inputClass} value={purpose} onChange={(e) => setPurpose(e.target.value)} /></label></div><div className="mt-3 flex gap-3"><button className={buttonClass} disabled={Boolean(pending) || !proposalId || !purpose} type="button" onClick={() => decide(true)}>Approve and invite</button><button className={buttonClass} disabled={Boolean(pending) || !proposalId || !purpose} type="button" onClick={() => decide(false)}>Deny proposal</button></div></section>
  </div>;
}

function MaintenanceHistory() {
  const [caseId, setCaseId] = useState("");
  const [loadedCaseId, setLoadedCaseId] = useState("");
  const [events, setEvents] = useState([]);
  const [eventType, setEventType] = useState("technician_observation");
  const [content, setContent] = useState("");
  const [error, setError] = useState(null);
  const [pending, setPending] = useState("");
  const load = async () => {
    const requestedCaseId = caseId;
    setPending("load"); setError(null); setEvents([]); setLoadedCaseId("");
    try {
      setEvents((await phase6Api(`/api/v2/maintenance/cases/${requestedCaseId}`)).events || []);
      setLoadedCaseId(requestedCaseId);
    } catch (loadError) { setError(loadError); }
    finally { setPending(""); }
  };
  const append = async (event) => {
    event.preventDefault();
    if (caseId !== loadedCaseId) return;
    if (!window.confirm(`Add this ${eventType.replaceAll("_", " ")} entry to case ${loadedCaseId}?`)) return;
    setPending("append"); setError(null);
    try { await phase6Api(`/api/v2/maintenance/cases/${loadedCaseId}/events`, { method: "POST", body: JSON.stringify({ event_type: eventType, content }) }); setContent(""); await load(); }
    catch (actionError) { setError(actionError); setPending(""); }
  };
  const changeCase = (value) => { setCaseId(value); setLoadedCaseId(""); setEvents([]); };
  return <div className="space-y-8"><section aria-labelledby="history-title"><h2 id="history-title" className="text-2xl">Maintenance case history</h2><p className="mt-2 text-sm text-linen/70">The backend supports case-specific history, but not a case listing. Enter a case ID from an assigned work item.</p><div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"><label className="flex-1">Case ID<input className={inputClass} value={caseId} onChange={(e) => changeCase(e.target.value)} /></label><button className={buttonClass} disabled={!caseId || Boolean(pending)} type="button" onClick={load}>Load history</button></div><ErrorSummary error={error} /><SectionState loading={pending === "load"} items={events} empty={loadedCaseId ? "No history entries are available." : "Enter and load a case ID."} /><ol className="mt-4 space-y-3">{events.map((item) => <li className="border-l-2 border-gold pl-4" key={item.id}><strong>{item.event_type.replaceAll("_", " ")}</strong><p>{item.content}</p><p className="text-sm text-linen/70">{String(item.occurred_at)}</p></li>)}</ol></section>
    <section aria-labelledby="history-entry-title"><h2 id="history-entry-title" className="text-2xl">Add history entry</h2><form className="mt-4 space-y-4" onSubmit={append}><label className="block">Entry type<select className={inputClass} value={eventType} onChange={(e) => setEventType(e.target.value)}><option value="technician_observation">Technician observation</option><option value="technician_recommendation">Technician recommendation</option><option value="manager_decision">Manager decision</option><option value="approved_solution">Approved solution</option><option value="ordered_product">Ordered product</option><option value="installed_solution">Installed solution</option><option value="variance_reason">Variance reason</option></select></label><label className="block">Entry<textarea className={inputClass} required value={content} onChange={(e) => setContent(e.target.value)} /></label><button className={buttonClass} disabled={!loadedCaseId || caseId !== loadedCaseId || Boolean(pending)} type="submit">Add audited entry</button>{!loadedCaseId || caseId !== loadedCaseId ? <p className="text-sm text-linen/70">Load the exact authorized case before adding an entry.</p> : null}<p role="status" aria-live="polite">{pending === "append" ? "Adding history entry…" : ""}</p></form></section>
  </div>;
}

export function Phase6AccessWorkspace({ surface }) {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [contexts, setContexts] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const title = NAV.find(([id]) => id === surface)?.[1] || "Identity and access";
  const loadContext = useCallback(async () => {
    try {
      const current = await phase6Api("/api/v2/auth/me");
      setMe(current);
      sessionStorage.setItem("pp_active_context", JSON.stringify(current));
      try {
        const contextBody = await phase6Api("/api/v2/me/contexts");
        setContexts(contextBody.contexts || [current]);
      } catch { setContexts([current]); }
    } catch (loadError) {
      if (loadError.status === 401) navigate("/session-expired?draft=preserved", { replace: true });
      else setError(loadError);
    }
  }, [navigate]);
  useEffect(() => { loadContext(); }, [loadContext]);
  useEffect(() => {
    const expire = () => {
      setMe(null);
      setContexts([]);
      navigate("/session-expired", { replace: true });
    };
    window.addEventListener("perchpoint:session-expired", expire);
    return () => window.removeEventListener("perchpoint:session-expired", expire);
  }, [navigate]);
  const switchContext = async (membershipId) => {
    setBusy(true);
    try { await phase6Api("/api/v2/me/context", { method: "POST", body: JSON.stringify({ membership_id: membershipId }) }); await loadContext(); }
    catch (switchError) { setError(switchError); }
    finally { setBusy(false); }
  };
  const content = useMemo(() => {
    if (!me) return null;
    if (surface === "onboarding") return <Onboarding me={me} />;
    if (surface === "security") return <SecurityCenter />;
    if (surface === "users-access") return <UsersAccess />;
    if (surface === "delegations") return <Delegations me={me} />;
    if (surface === "access-requests") return <AccessRequests me={me} />;
    if (surface === "access-reviews") return <AccessReviews />;
    if (surface === "vendor-access") return <VendorAccess />;
    if (surface === "maintenance-history") return <MaintenanceHistory />;
    return null;
  }, [me, surface]);
  return <main id="main" className="min-h-screen bg-obsidian text-linen">
    <a className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-obsidian focus:p-3" href="#access-content">Skip to access content</a>
    {me ? <SessionClock role={me.role_name} /> : null}
    <div className="mx-auto max-w-6xl px-5 py-8">
      <nav aria-label="Identity and access" className="flex gap-4 overflow-x-auto border-b border-white/20 pb-4">
        {NAV.map(([id, label]) => <Link key={id} aria-current={id === surface ? "page" : undefined} className={`shrink-0 ${id === surface ? "text-gold underline" : "text-linen"}`} to={`/access/${id}`}>{label}</Link>)}
      </nav>
      <h1 className="mt-8 font-heading text-4xl">{title}</h1>
      <p className="mt-2 text-linen/70">Only current server-authorized data and actions are shown.</p>
      <div className="mt-6">{!me && !error ? <p role="status">Loading current access…</p> : null}<ErrorSummary error={error} retry={loadContext} />{me ? <ContextBar me={me} contexts={contexts} onSwitch={switchContext} busy={busy} /> : null}</div>
      <div id="access-content" tabIndex="-1" className="mt-8">{content}</div>
    </div>
  </main>;
}

export function Phase6BoundaryPage({ kind }) {
  const [params] = useSearchParams();
  const expired = kind === "session-expired";
  const correlationId = params.get("correlation_id");
  const returnTo = params.get("return_to") || "";
  const capability = params.get("capability") || "";
  const requestPath = `/access/access-requests?${new URLSearchParams({ purpose: "Restore required access", scope: returnTo, capability }).toString()}`;
  return <main id="main" className="min-h-screen bg-obsidian px-5 py-20 text-linen"><div className="mx-auto max-w-xl" role="alert">
    <h1 className="font-heading text-4xl">{expired ? "Your session expired" : "Access denied"}</h1>
    <p className="mt-4">{expired ? "Protected work stopped because stale authority cannot continue." : "This record may not exist, or your current access does not allow it."}</p>
    {expired && params.get("draft") === "preserved" ? <p className="mt-3">Safe, non-sensitive form drafts were preserved in this browser tab. Sign in again to resume.</p> : null}
    {!expired ? <p className="mt-3 text-sm">Correlation ID: <code>{correlationId || "Not supplied by the server"}</code></p> : null}
    <div className="mt-6 flex flex-wrap gap-4"><Link className="text-gold underline" tabIndex={0} to={expired ? "/sign-in" : requestPath}>{expired ? "Sign in again" : "Request appropriate access"}</Link>{!expired ? <Link className="text-gold underline" tabIndex={0} to="/access/onboarding">Return to access summary</Link> : null}</div>
  </div></main>;
}
