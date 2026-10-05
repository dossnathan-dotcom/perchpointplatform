import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { SessionClock } from "./Phase6Access";

const surfaces = [
  ["security", "Security Center"],
  ["users-access", "Users and Access"],
  ["delegations", "Delegation Center"],
  ["access-reviews", "Access Reviews"],
  ["vendor-access", "Vendor worker access"],
];

function csrf() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

async function api(path, options = {}) {
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
    const error = new Error(body.detail?.message || "The request could not be completed.");
    error.code = body.detail?.code || `http_${response.status}`;
    error.status = response.status;
    throw error;
  }
  return body;
}

function Status({ state, message, retry }) {
  if (state === "loading") return <p role="status">Loading current access.</p>;
  if (state === "empty") return <p role="status">There are no records in this view.</p>;
  if (state === "denied") return <p role="alert">You do not have access to this view. No protected record details were disclosed.</p>;
  if (state === "expired") return <p role="alert">Your session expired. Sign in again to continue.</p>;
  if (state === "error") return <div role="alert"><p>{message}</p><button type="button" className="mt-3 underline" onClick={retry}>Try again</button></div>;
  return null;
}

export function Phase6IdentityFlow({ mode }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const messageRef = useRef(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(params.get("token") || "");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [factor, setFactor] = useState(null);
  const [code, setCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [factorState, setFactorState] = useState("idle");
  const [factorError, setFactorError] = useState("");
  let activeRole = "";
  try {
    activeRole = JSON.parse(sessionStorage.getItem("pp_active_context") || "{}").role_name || "";
  } catch {
    activeRole = "";
  }

  useEffect(() => {
    if (message) messageRef.current?.focus();
  }, [message]);

  const loadFactors = useCallback(() => {
    if (mode !== "mfa") return undefined;
    let current = true;
    setFactorState("loading");
    setFactorError("");
    api("/api/v2/auth/mfa/factors").then((body) => {
      const existing = (body.factors || []).find((item) => item.confirmed_at);
      if (current && existing) {
        setFactor({ factor_id: existing.provider_factor_id, existing: true });
        setMessage("Enter a code from your enrolled authenticator.");
      }
      if (current) setFactorState(existing ? "success" : "empty");
    }).catch((error) => {
      if (current) {
        setFactorError(error.message);
        setFactorState(error.status === 401 ? "expired" : "error");
      }
    });
    return () => { current = false; };
  }, [mode]);

  useEffect(() => loadFactors(), [loadFactors]);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      if (mode === "invitation") {
        await api("/api/v2/auth/invitations/accept", {
          method: "POST",
          body: JSON.stringify({ token, email, password }),
        });
        setMessage("Invitation accepted. Sign in with this password and complete MFA when required.");
      } else if (mode === "password-reset") {
        if (token) {
          await api("/api/v2/auth/password/reset", {
            method: "POST",
            body: JSON.stringify({ token, password }),
          });
          setMessage("Password changed. For your security, sign in again.");
        } else {
          await api("/api/v2/auth/password/reset-request", {
            method: "POST",
            body: JSON.stringify({ email }),
          });
          setMessage("If an account exists, a reset message will be sent.");
        }
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function enroll() {
    setBusy(true);
    try {
      setFactor(await api("/api/v2/auth/mfa/enroll", { method: "POST" }));
      setMessage("Scan the authenticator URI or enter the manual key, then confirm a code.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    try {
      await api("/api/v2/auth/mfa/confirm", {
        method: "POST",
        body: JSON.stringify({ factor_id: factor.factor_id, code }),
      });
      if (factor.existing) {
        setMessage("Multi-factor authentication verified. Your current session is now elevated.");
        window.setTimeout(() => navigate(params.get("next") || "/access/onboarding", { replace: true }), 300);
      } else {
        const generated = await api("/api/v2/auth/recovery-codes", { method: "POST" });
        setRecoveryCodes(generated.codes);
        setMessage("Multi-factor authentication is active. Save the recovery codes now; they will not be shown again.");
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  const title = mode === "invitation" ? "Accept invitation" : mode === "mfa" ? "Set up authenticator MFA" : "Reset password";
  return <main id="main" className="min-h-screen bg-obsidian text-linen">
    {activeRole ? <SessionClock role={activeRole} /> : null}
    <div className="mx-auto max-w-xl px-5 py-16">
      <Link className="text-gold underline" to="/sign-in">Back to sign in</Link>
      <h1 className="mt-6 font-heading text-4xl">{title}</h1>
      {mode === "mfa" ? <div className="mt-8 space-y-5">
        {factorState === "loading" ? <p role="status">Checking current factors…</p> : null}
        {factorState === "error" || factorState === "expired" ? <div role="alert"><p>{factorError}</p><button className="mt-2 underline" type="button" onClick={loadFactors}>Try again</button></div> : null}
        {!factor ? <button type="button" className="rounded bg-brass px-4 py-3 text-obsidian" disabled={busy || !["empty", "success"].includes(factorState)} onClick={enroll}>Begin MFA setup</button> : <>
          {!factor.existing ? <>
            <p className="break-all"><strong>Authenticator URI:</strong> {factor.otpauth}</p>
            <p className="break-all"><strong>Manual key:</strong> {factor.secret}</p>
          </> : null}
          <label className="block">Six-digit code<input className="mt-1 w-full border bg-transparent px-3 py-2" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} /></label>
          <button type="button" className="rounded bg-brass px-4 py-3 text-obsidian" disabled={busy || code.length !== 6} onClick={confirm}>Confirm MFA</button>
        </>}
        {recoveryCodes.length ? <section aria-labelledby="recovery-title">
          <h2 id="recovery-title" className="text-2xl">Recovery codes</h2>
          <ul className="mt-3 grid grid-cols-2 gap-2 font-mono">{recoveryCodes.map((item) => <li key={item}>{item}</li>)}</ul>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" className="underline" onClick={() => navigator.clipboard.writeText(recoveryCodes.join("\n"))}>Copy codes</button>
            <a className="underline" download="perchpoint-recovery-codes.txt" href={`data:text/plain;charset=utf-8,${encodeURIComponent(recoveryCodes.join("\n"))}`}>Download codes</a>
            <button type="button" className="underline" onClick={() => window.print()}>Print codes</button>
          </div>
        </section> : null}
      </div> : <form className="mt-8 space-y-4" onSubmit={submit}>
        {mode === "invitation" || !token ? <label className="block">Email<input className="mt-1 w-full border bg-transparent px-3 py-2" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label> : null}
        {mode === "invitation" ? <label className="block">Invitation token<input className="mt-1 w-full border bg-transparent px-3 py-2" value={token} onChange={(event) => setToken(event.target.value)} required /></label> : null}
        {mode === "invitation" ? <label className="block">Create password<input className="mt-1 w-full border bg-transparent px-3 py-2" type="password" autoComplete="new-password" minLength={15} maxLength={64} value={password} onChange={(event) => setPassword(event.target.value)} required /></label> : null}
        {mode === "password-reset" && token ? <label className="block">New password<input className="mt-1 w-full border bg-transparent px-3 py-2" type="password" autoComplete="new-password" minLength={15} maxLength={64} value={password} onChange={(event) => setPassword(event.target.value)} required /></label> : null}
        <button className="rounded bg-brass px-4 py-3 text-obsidian" disabled={busy}>{busy ? "Working…" : mode === "invitation" ? "Accept invitation" : token ? "Change password" : "Send reset message"}</button>
      </form>}
      {message ? <p ref={messageRef} tabIndex="-1" className="mt-5" role="status" aria-live="polite">{message}</p> : null}
    </div>
  </main>;
}

export function Phase6AccessWorkspace({ surface }) {
  const endpoint = useMemo(() => ({
    security: "/api/v2/me/sessions",
    "users-access": "/api/v2/access/users",
    delegations: "/api/v2/access/delegations",
    "access-reviews": "/api/v2/access/reviews",
    "vendor-access": "/api/v2/access/users",
  }[surface]), [surface]);
  const [state, setState] = useState("loading");
  const [records, setRecords] = useState([]);
  const [message, setMessage] = useState("");
  const [version, setVersion] = useState(0);
  const title = surfaces.find(([id]) => id === surface)?.[1] || "Access";

  useEffect(() => {
    let current = true;
    setState("loading");
    api(endpoint).then((body) => {
      if (!current) return;
      const values = body.sessions || body.users || body.delegations || body.reviews || [];
      const filtered = surface === "vendor-access" ? values.filter((item) => ["vendor_admin", "vendor_worker", "technician", "cleaner"].includes(item.role_name)) : values;
      setRecords(filtered);
      setState(filtered.length ? "success" : "empty");
    }).catch((error) => {
      if (!current) return;
      setMessage(error.message);
      setState(error.status === 401 ? "expired" : error.status === 403 || error.status === 404 ? "denied" : "error");
    });
    return () => { current = false; };
  }, [endpoint, surface, version]);

  async function revokeOthers() {
    try {
      await api("/api/v2/me/sessions/revoke-others", { method: "POST" });
      setVersion((value) => value + 1);
    } catch (error) {
      setMessage(error.message);
      setState(error.status === 403 ? "denied" : "error");
    }
  }

  return <main id="main" className="min-h-screen bg-obsidian px-5 py-10 text-linen">
    <div className="mx-auto max-w-6xl">
      <nav aria-label="Identity and access" className="flex flex-wrap gap-4 border-b border-white/20 pb-4">
        {surfaces.map(([id, label]) => <Link key={id} className={id === surface ? "text-gold underline" : "text-linen"} to={`/access/${id}`}>{label}</Link>)}
        <Link className="text-linen" to="/mfa">MFA</Link>
      </nav>
      <h1 className="mt-8 font-heading text-4xl">{title}</h1>
      <p className="mt-2 text-linen/70">Current server-authorized access only. Preview roles and URL values cannot grant authority.</p>
      <div className="mt-8">
        <Status state={state} message={message} retry={() => setVersion((value) => value + 1)} />
        {state === "success" ? <ul className="space-y-3">
          {records.map((item, index) => <li className="border border-white/20 p-4" key={item.id || item.account_id || index}>
            <strong>{item.email || item.title || item.device_label || item.capability || "Authorized record"}</strong>
            <p className="mt-1 text-sm text-linen/70">{item.role_name || item.status || (item.revoked ? "Revoked" : "Active")}</p>
          </li>)}
        </ul> : null}
        {surface === "security" && state !== "expired" ? <button type="button" className="mt-5 rounded border px-4 py-2" onClick={revokeOthers}>Sign out all other sessions</button> : null}
      </div>
    </div>
  </main>;
}

export function Phase6BoundaryPage({ kind }) {
  const expired = kind === "session-expired";
  return <main id="main" className="min-h-screen bg-obsidian px-5 py-20 text-linen">
    <div className="mx-auto max-w-xl" role="alert">
      <h1 className="font-heading text-4xl">{expired ? "Your session expired" : "Access denied"}</h1>
      <p className="mt-4">{expired ? "Sign in again. Protected work cannot continue with stale authority." : "This record may not exist, or your current access does not allow it."}</p>
      <p className="mt-3 text-sm">Correlation ID is available in the response headers for support.</p>
      <Link className="mt-6 inline-block text-gold underline" tabIndex={0} to={expired ? "/sign-in" : "/access/users-access"}>{expired ? "Sign in" : "Return to access center"}</Link>
    </div>
  </main>;
}
