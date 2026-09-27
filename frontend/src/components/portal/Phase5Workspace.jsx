import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { phase2 } from "@/api/phase2";
import { SkipLink } from "@/design-system/components";

const CENTERS = {
  documents: "Document Center",
  quality: "Data Quality Center",
  imports: "Import Reconciliation",
  audit: "Audit Explorer",
  timeline: "Record Timeline",
  saved: "Saved Searches",
};

const STAFF = {
  leasing: "ann.synthetic@example.com",
  "super-admin": "nathan.synthetic@example.com",
  owner: "ann.synthetic@example.com",
};

export function Phase5Workspace() {
  const { roleId, center } = useParams();
  const title = CENTERS[center] || "Phase 5";
  const [email, setEmail] = useState(STAFF[roleId] || "");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [status, setStatus] = useState("Sign in to load canonical records. The preview role is not authority.");
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState("");
  const [savedName, setSavedName] = useState("Recent canonical search");
  const [batchId, setBatchId] = useState("");
  const [importText, setImportText] = useState("display_name,party_kind\nSynthetic Resident,person\n");
  const [importFormat, setImportFormat] = useState("csv");
  const [resolveReason, setResolveReason] = useState("Reviewed synthetic finding");
  const allowed = roleId === "owner" || roleId === "leasing" || roleId === "super-admin";

  useEffect(() => {
    setToken("");
    setRows([]);
    setBatchId("");
    setStatus(allowed ? "Sign in to load canonical records. The preview role is not authority." : "This role has no Phase 5 workspace.");
  }, [roleId, allowed]);

  const load = useCallback(async (current = token, cancelled = () => false) => {
    setStatus("Loading.");
    const headers = { Authorization: `Bearer ${current}` };
    const path = {
      documents: query.trim().length >= 2 ? `/api/v2/search?q=${encodeURIComponent(query.trim())}` : "/api/v2/documents",
      quality: "/api/v2/quality",
      imports: "/api/v2/imports",
      audit: "/api/v2/audit/events",
      timeline: "/api/v2/audit/events",
      saved: "/api/v2/search/saved",
    }[center];
    if (!path) {
      setStatus("This workspace is not available.");
      return;
    }
    try {
      const { response, body } = await phase2(path, { headers });
      if (cancelled()) return;
      if (response.status === 404 || response.status === 403) {
        setRows([]);
        setStatus("Access denied for this membership.");
        return;
      }
      if (!response.ok) {
        setRows([]);
        setStatus("The canonical service returned an error.");
        return;
      }
      const next = body.documents || body.results || body.findings || body.events || body.saved || body.batches || [];
      setRows(next);
      setStatus(next.length ? `${next.length} records.` : "No records in this view.");
    } catch {
      if (!cancelled()) setStatus("Offline. The canonical service could not be reached.");
    }
  }, [center, query, token]);

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    load(token, () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [load, token]);

  async function signIn(event) {
    event.preventDefault();
    setStatus("Signing in.");
    const { response, body } = await phase2("/api/v2/session", { method: "POST", body: JSON.stringify({ email, password }) });
    if (!response.ok) {
      setStatus(response.status === 403 ? "This membership cannot sign in." : "Sign-in was denied.");
      return;
    }
    setToken(body.token);
    setStatus(`Signed in as ${body.role_name}.`);
    await load(body.token);
  }

  async function saveSearch(event) {
    event.preventDefault();
    const headers = { Authorization: `Bearer ${token}` };
    const { response } = await phase2("/api/v2/search/saved", {
      method: "POST",
      headers,
      body: JSON.stringify({ name: savedName, query, idempotency_key: `ui-${Date.now()}` }),
    });
    setStatus(response.ok ? "Saved search stored." : "Saved search was not stored.");
    if (response.ok) await load();
  }

  if (!allowed || !CENTERS[center]) {
    return (
      <main id="main" className="min-h-screen bg-obsidian px-6 py-24 text-linen" data-testid="phase5-denied">
        <h1 className="font-heading text-4xl">Workspace unavailable</h1>
        <p className="mt-4">Applicants, residents, and vendors do not receive a new Phase 5 workspace.</p>
        <Link className="mt-6 inline-block underline" to="/">Return to HawkVision</Link>
      </main>
    );
  }

  return (
    <main id="main" className="min-h-screen bg-obsidian text-linen" data-testid={`phase5-${center}`}>
      <SkipLink />
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <p className="text-xs text-gold">HawkVision Homes · synthetic canonical records</p>
        <h1 className="mt-3 font-heading text-4xl font-bold" data-testid="phase5-title">{title}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-linen/75" data-testid="phase5-role-note">
          {roleId === "owner" ? "Material exceptions, expiring obligations, and unresolved conflicts. Routine filing stays with operations." : roleId === "super-admin" ? "Taxonomy, mappings, replay, and storage diagnostics stay with the platform administrator." : "Operational records stay inside the signed-in organization. This screen is not production authority."}
        </p>
        <nav className="mt-6 flex flex-wrap gap-3 text-sm" aria-label="Phase 5 workspaces">
          {Object.entries(CENTERS).map(([key, label]) => (
            <Link key={key} className="underline" to={`/perchpoint/${roleId}/phase5/${key}`} data-testid={`phase5-nav-${key}`}>{label}</Link>
          ))}
        </nav>
        <form className="mt-8 grid gap-3 sm:grid-cols-[1fr_1fr_auto]" onSubmit={signIn}>
          <label className="grid gap-1 text-sm">Email
            <input className="h-11 border border-white/40 bg-obsidian px-3" name="phase5-email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label className="grid gap-1 text-sm">Password
            <input className="h-11 border border-white/40 bg-obsidian px-3" name="phase5-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <button className="h-11 self-end border border-gold px-4" type="submit" data-testid="phase5-sign-in">Sign in</button>
        </form>
        <p role="status" className="mt-4 text-sm" data-testid="phase5-status">{status}</p>
        {roleId === "super-admin" && token && (center === "timeline" || center === "audit") ? (
          <button className="mt-4 h-11 border border-gold px-4" type="button" data-testid="phase5-replay" onClick={async () => {
            setStatus("Replay in progress.");
            const { response, body } = await phase2("/api/v2/replay", { method: "POST", headers: { Authorization: `Bearer ${token}` } });
            setStatus(response.ok ? `Replay ${body.status}. Expected ${body.expected}, actual ${body.actual}.` : "Replay was denied.");
          }}>Replay projection</button>
        ) : null}
        {center === "saved" && token ? (
          <form className="mt-6 grid gap-3 sm:grid-cols-[1fr_1fr_auto]" onSubmit={saveSearch}>
            <label className="grid gap-1 text-sm">Name
              <input className="h-11 border border-white/40 bg-obsidian px-3" value={savedName} onChange={(event) => setSavedName(event.target.value)} data-testid="phase5-saved-name" />
            </label>
            <label className="grid gap-1 text-sm">Query
              <input className="h-11 border border-white/40 bg-obsidian px-3" value={query} onChange={(event) => setQuery(event.target.value)} data-testid="phase5-saved-query" />
            </label>
            <button className="h-11 self-end border border-white/40 px-4" type="submit" data-testid="phase5-save-search">Save search</button>
            <button className="h-11 self-end underline" type="button" onClick={() => { setQuery(""); setStatus("Recent search cleared."); }}>Clear recent search</button>
          </form>
        ) : null}
        {center === "documents" && token ? (
          <form className="mt-6 grid gap-3" data-testid="phase5-upload" onSubmit={async (event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            data.set("document_class", "internal-administration");
            data.set("classification", "internal");
            data.set("primary_resource_type", "property");
            data.set("idempotency_key", `ui-doc-${Date.now()}`);
            setStatus("Uploading.");
            const response = await fetch("/api/v2/documents", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: data });
            setStatus(response.ok ? "Upload accepted for scanning." : "Upload was not accepted.");
            if (response.ok) await load();
          }}>
            <label className="grid gap-1 text-sm">Title
              <input className="h-11 border border-white/40 bg-obsidian px-3" name="title" required />
            </label>
            <label className="grid gap-1 text-sm">Property
              <input className="h-11 border border-white/40 bg-obsidian px-3" name="primary_resource_id" required />
            </label>
            <label className="grid gap-1 text-sm">File
              <input className="text-sm" name="upload" type="file" required />
            </label>
            <label className="grid gap-1 text-sm">Search
              <input className="h-11 border border-white/40 bg-obsidian px-3" value={query} onChange={(event) => setQuery(event.target.value)} data-testid="phase5-document-query" />
            </label>
            <button className="h-11 border border-white/40 px-4" type="submit">Upload</button>
          </form>
        ) : null}
        {center === "imports" && token ? (
          <form className="mt-6 grid gap-3" data-testid="phase5-import" onSubmit={async (event) => {
            event.preventDefault();
            setStatus("Staging import.");
            const { response, body } = await phase2("/api/v2/imports", {
              method: "POST",
              headers: { Authorization: `Bearer ${token}` },
              body: JSON.stringify({ content: importText, source_format: importFormat, idempotency_key: `ui-import-${Date.now()}` }),
            });
            if (!response.ok) {
              setStatus("Import was not staged.");
              return;
            }
            setBatchId(body.id);
            setStatus(`Import ${body.id} staged.`);
          }}>
            <label className="grid gap-1 text-sm">Format
              <select className="h-11 border border-white/40 bg-obsidian px-3" value={importFormat} onChange={(event) => setImportFormat(event.target.value)} data-testid="phase5-import-format">
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
                <option value="xlsx">XLSX</option>
                <option value="archive">Manifested archive</option>
              </select>
            </label>
            <label className="grid gap-1 text-sm">Synthetic source
              <textarea className="min-h-28 border border-white/40 bg-obsidian p-3" value={importText} onChange={(event) => setImportText(event.target.value)} />
            </label>
            <button className="h-11 border border-white/40 px-4" type="submit">Stage import</button>
          </form>
        ) : null}
        {center === "imports" && token && batchId ? (
          <div className="mt-4 flex flex-wrap gap-3">
            {["dry-run", "approve", "apply", "rollback"].map((action) => (
              <button key={action} className="h-11 border border-white/40 px-4" type="button" onClick={async () => {
                const { response } = await phase2(`/api/v2/imports/${batchId}/${action}`, {
                  method: "POST",
                  headers: { Authorization: `Bearer ${token}` },
                  body: action === "dry-run" ? undefined : JSON.stringify({ idempotency_key: `ui-${action}-${Date.now()}` }),
                });
                setStatus(response.ok ? `Import ${action} recorded.` : `Import ${action} was refused.`);
              }}>{action}</button>
            ))}
          </div>
        ) : null}
        {center === "quality" && token ? (
          <form className="mt-6 grid gap-3 sm:grid-cols-[1fr_auto]" onSubmit={async (event) => {
            event.preventDefault();
            const finding = rows[0];
            if (!finding) {
              setStatus("No open finding to resolve.");
              return;
            }
            const { response } = await phase2(`/api/v2/quality/${finding.id}/resolve`, {
              method: "POST",
              headers: { Authorization: `Bearer ${token}` },
              body: JSON.stringify({ reason: resolveReason, idempotency_key: `ui-resolve-${Date.now()}` }),
            });
            setStatus(response.ok ? "Finding resolved." : "Finding was not resolved.");
            if (response.ok) await load();
          }}>
            <label className="grid gap-1 text-sm">Resolution reason
              <input className="h-11 border border-white/40 bg-obsidian px-3" value={resolveReason} onChange={(event) => setResolveReason(event.target.value)} />
            </label>
            <button className="h-11 self-end border border-white/40 px-4" type="submit">Resolve first finding</button>
          </form>
        ) : null}
        <div className="mt-8" data-testid="phase5-results">
          {rows.length === 0 ? <p data-testid="phase5-empty">Nothing to show yet.</p> : (
            <ul className="divide-y divide-white/20">
              {rows.map((row) => (
                <li key={row.id} className="py-4 text-sm">
                  <span className="font-semibold">{row.title || row.name || row.detail || row.action}</span>
                  <span className="mt-1 block text-linen/75">{row.lifecycle || row.severity || row.visibility || row.result || row.classification || "Recorded"}</span>
                  {center === "saved" ? (
                    <button className="mt-2 underline" type="button" onClick={async () => {
                      const { response } = await phase2(`/api/v2/search/saved/${row.id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
                      setStatus(response.ok ? "Saved search deleted." : "Saved search was not deleted.");
                      if (response.ok) await load();
                    }}>Delete</button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
        <button className="mt-6 underline" type="button" onClick={() => token && load()} data-testid="phase5-refresh">Refresh</button>
      </div>
    </main>
  );
}
