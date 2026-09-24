import { useEffect, useState } from "react";
import { phase2 } from "@/api/phase2";

const staffEmail = {
  leasing: "ann.synthetic@example.com",
  "super-admin": "nathan.synthetic@example.com",
};

export function Phase2Kernel({ previewRole }) {
  const email = staffEmail[previewRole];
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [roleName, setRoleName] = useState("");
  const [status, setStatus] = useState("Development sign-in uses the backend. The preview role above is not authority.");
  const [properties, setProperties] = useState([]);
  const [inquiries, setInquiries] = useState([]);
  const [name, setName] = useState("");
  const [selected, setSelected] = useState("");
  const [version, setVersion] = useState(1);
  const [activity, setActivity] = useState([]);
  const canWrite = roleName === "leasing" || roleName === "platform_admin";
  const canOperate = roleName === "platform_admin";

  useEffect(() => { setToken(""); setRoleName(""); setProperties([]); setInquiries([]); }, [previewRole]);

  async function signIn(event) {
    event.preventDefault();
    if (!email) { setStatus("This preview role has no development principal."); return; }
    setStatus("Signing in.");
    const { response, body } = await phase2("/api/v2/session", { method: "POST", body: JSON.stringify({ email, password }) });
    if (!response.ok) { setStatus(response.status === 403 ? "This membership cannot sign in." : "Sign-in was denied."); return; }
    setToken(body.token);
    setRoleName(body.role_name);
    setStatus(`Signed in as ${body.role_name}. Preview role ${previewRole} did not grant this.`);
    await refresh(body.token);
  }

  async function refresh(current = token) {
    const headers = { Authorization: `Bearer ${current}` };
    const propertiesResponse = await phase2("/api/v2/properties", { headers });
    const inquiryResponse = await phase2("/api/v2/inquiries", { headers });
    setProperties(propertiesResponse.body.properties || []);
    setInquiries(inquiryResponse.body.inquiries || []);
  }

  async function createProperty(event) {
    event.preventDefault();
    if (name.trim().length < 2) { setStatus("Enter a property name."); return; }
    const { response, body } = await phase2("/api/v2/properties", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ name, property_type: "multifamily", idempotency_key: `ui-${Date.now()}` }) });
    if (response.status === 409) { setStatus(body.detail?.message || "The property changed."); return; }
    if (!response.ok) { setStatus(body.detail?.message || "The property was not created."); return; }
    setSelected(body.id);
    setVersion(body.version);
    setStatus("Property saved.");
    await refresh();
  }

  async function rename(event) {
    event.preventDefault();
    const { response, body } = await phase2(`/api/v2/properties/${selected}`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ name, expected_version: version, idempotency_key: `rename-${selected}-${Date.now()}` }) });
    if (response.status === 409) { setStatus("This property changed. Reload it and try again."); return; }
    if (!response.ok) { setStatus(body.detail?.message || "The name was not saved."); return; }
    setVersion(body.version);
    setStatus("Property name saved.");
  }

  async function loadActivity() {
    const { body } = await phase2(`/api/v2/activity?resource_id=${selected}`, { headers: { Authorization: `Bearer ${token}` } });
    setActivity(body.activity || []);
  }

  async function triage(inquiry) {
    const { response, body } = await phase2(`/api/v2/inquiries/${inquiry.id}/triage`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ decision: "assigned", expected_version: inquiry.version, idempotency_key: `queue-${inquiry.id}-${Date.now()}` }) });
    setStatus(response.ok ? "Inquiry assigned." : (body.detail?.message || "Triage was not saved."));
    if (response.ok) await refresh();
  }

  if (!email && previewRole !== "owner") return null;
  return <section className="mb-10 border border-white/20 p-5" aria-label="Phase 2 operations">
    <h2 className="font-heading text-2xl">Live portfolio</h2>
    <p className="mt-2 max-w-3xl text-sm text-linen/75">{status}</p>
    {!token && email && <form className="mt-4 flex flex-wrap gap-3" onSubmit={signIn}>
      <label className="text-sm">Development password
        <input className="ml-2 border border-white/30 bg-transparent px-3 py-2" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
      </label>
      <button className="bg-copper px-4 py-2 text-white" type="submit">Sign in for this workspace</button>
    </form>}
    {previewRole === "owner" && !token && <p className="mt-4 text-sm">Owner preview does not authenticate. Sign in through leasing or platform administration for a backend session.</p>}
    {token && <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <div>
        <h3 className="text-sm text-gold">Properties</h3>
        <ul className="mt-3 divide-y divide-white/10">{properties.length === 0 ? <li>No properties are visible to this session.</li> : properties.map((item) => <li key={item.id} className="py-2"><button type="button" className="underline" onClick={() => { setSelected(item.id); setVersion(item.version); setName(item.name); }}>{item.name}</button></li>)}</ul>
        {canWrite && <form className="mt-4 space-y-2" onSubmit={selected ? rename : createProperty}>
          <label className="block text-sm">Property name<input className="mt-1 w-full border border-white/30 bg-transparent px-3 py-2" value={name} onChange={(event) => setName(event.target.value)} /></label>
          <button className="bg-white px-3 py-2 text-obsidian" type="submit">{selected ? "Save name" : "Create property"}</button>
          {selected && <button className="ml-3 underline" type="button" onClick={loadActivity}>Activity</button>}
        </form>}
        <ul className="mt-3 text-sm">{activity.map((item) => <li key={item.id}>{item.summary}</li>)}</ul>
      </div>
      <div>
        <h3 className="text-sm text-gold">Inquiries</h3>
        <ul className="mt-3 divide-y divide-white/10">{inquiries.length === 0 ? <li>No inquiries are visible to this session.</li> : inquiries.map((item) => <li key={item.id} className="py-3 text-sm">{item.name} · {item.status}{canWrite && <button className="ml-3 underline" type="button" onClick={() => triage(item)}>Assign</button>}</li>)}</ul>
        {canOperate && <button className="mt-4 underline" type="button" onClick={async () => { const { body } = await phase2("/api/v2/worker/once", { method: "POST", headers: { Authorization: `Bearer ${token}` } }); setStatus(body.claimed ? `Synthetic delivery ${body.status}` : "No pending synthetic delivery."); }}>Run synthetic delivery</button>}
      </div>
    </div>}
  </section>;
}
