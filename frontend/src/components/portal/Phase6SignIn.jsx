import { useState } from "react";

export function Phase6SignIn() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [session, setSession] = useState(null);
  const [sessions, setSessions] = useState([]);
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
        setSession(null);
        setMessage(body.detail?.message || "The email or password is incorrect.");
        return;
      }
      setSession(body);
      const current = await fetch("/api/v2/me/sessions", { credentials: "include" });
      const listed = await current.json();
      setSessions(current.ok ? listed.sessions : []);
      setMessage("Signed in.");
    } catch {
      setMessage("The identity service is unavailable. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    if (!session) return;
    const response = await fetch("/api/v2/auth/sign-out", {
      method: "POST",
      credentials: "include",
      headers: { "x-perchpoint-csrf": session.csrf },
    });
    if (response.ok) {
      setSession(null);
      setMessage("Signed out.");
    }
  }

  return (
    <main id="main" className="min-h-screen bg-obsidian px-6 py-16 text-linen">
      <h1 className="font-display text-4xl">Sign in</h1>
      <p className="mt-3 max-w-xl text-linen/80">One sign-in for HawkVision staff, residents, and vendors. A preview role does not grant access.</p>
      <form className="mt-8 max-w-md space-y-4" onSubmit={submit}>
        <label className="block">
          Email
          <input className="mt-1 w-full rounded border border-linen/30 bg-transparent px-3 py-2" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="block">
          Password
          <input className="mt-1 w-full rounded border border-linen/30 bg-transparent px-3 py-2" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <button className="rounded bg-brass px-4 py-2 text-obsidian" type="submit" disabled={busy}>{busy ? "Signing in" : "Sign in"}</button>
      </form>
      {message ? <p role="status" className="mt-4">{message}</p> : null}
      {session ? (
        <section className="mt-6" aria-label="Current access">
          <p>Organization context is active. Role: {session.role_name}. Assurance: {session.assurance}.</p>
          <p>{sessions.length} session{sessions.length === 1 ? "" : "s"} on this account.</p>
          <button className="mt-3 rounded border border-linen/40 px-4 py-2" type="button" onClick={signOut}>Sign out</button>
        </section>
      ) : null}
    </main>
  );
}
