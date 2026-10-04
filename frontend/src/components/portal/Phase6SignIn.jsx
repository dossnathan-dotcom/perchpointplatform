import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export function Phase6SignIn() {
  const navigate = useNavigate();
  const errorRef = useRef(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/v2/auth/sign-in", {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const body = await response.json();
      if (!response.ok) {
        setMessage(body.detail?.message || "The email or password is incorrect.");
        requestAnimationFrame(() => errorRef.current?.focus());
        return;
      }
      const now = String(Date.now());
      sessionStorage.setItem("pp_session_started_at", now);
      sessionStorage.setItem("pp_session_last_authorized_at", now);
      sessionStorage.setItem("pp_active_context", JSON.stringify({
        organization_id: body.organization_id,
        role_name: body.role_name,
        assurance: body.assurance,
      }));
      navigate(body.mfa_required && body.assurance !== "aal2" ? "/mfa?next=%2Faccess%2Fonboarding" : "/access/onboarding", {
        replace: true,
      });
    } catch {
      setMessage("The identity service is unavailable. Try again.");
      requestAnimationFrame(() => errorRef.current?.focus());
    } finally {
      setBusy(false);
    }
  }

  return (
    <main id="main" className="min-h-screen bg-obsidian px-6 py-16 text-linen">
      <div className="mx-auto max-w-md">
      <h1 className="font-heading text-4xl">Sign in</h1>
      <p className="mt-3 text-linen/80">One sign-in routes you from your current membership. A preview role or URL never grants access.</p>
      {message ? <div ref={errorRef} tabIndex="-1" role="alert" className="mt-6 border border-rose-300 bg-rose-950/40 p-4">{message}</div> : null}
      <form className="mt-8 space-y-4" onSubmit={submit} aria-busy={busy}>
        <label className="block">
          Email
          <input className="mt-1 w-full rounded border border-linen/30 bg-transparent px-3 py-2" type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="block">
          Password
          <input className="mt-1 w-full rounded border border-linen/30 bg-transparent px-3 py-2" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <button className="rounded bg-brass px-4 py-2 text-obsidian disabled:opacity-60" type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
      <div className="mt-6 flex flex-wrap gap-4 text-sm">
        <Link className="text-gold underline" to="/password-reset">Reset password</Link>
        <Link className="text-gold underline" to="/">Return to HawkVision</Link>
      </div>
      </div>
    </main>
  );
}
