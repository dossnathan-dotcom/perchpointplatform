import { useState } from "react";

const api = (path, options = {}) => fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });

export function ReferenceOperations() {
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [status, setStatus] = useState("Enter the local synthetic password from backend/.env. This page is not production sign-in.");
  const [listings, setListings] = useState([]);
  const [properties, setProperties] = useState([]);
  const [inquiryId, setInquiryId] = useState("");
  const [propertyName, setPropertyName] = useState("");
  const [propertyId, setPropertyId] = useState("");
  const [propertyVersion, setPropertyVersion] = useState(1);
  const [buildingName, setBuildingName] = useState("");
  const [buildingId, setBuildingId] = useState("");
  const [spaceLabel, setSpaceLabel] = useState("");
  const [spaceUse, setSpaceUse] = useState("residential");
  const [spaceId, setSpaceId] = useState("");
  const [spaceVersion, setSpaceVersion] = useState(1);
  const [activity, setActivity] = useState([]);
  const [delivery, setDelivery] = useState("");

  async function loadListings() {
    setStatus("Loading published listings…");
    const response = await api("/api/v2/listings");
    const body = await response.json();
    setListings(body.listings || []);
    setStatus(response.ok ? "Published listings loaded." : "Listings are unavailable.");
  }

  async function login(event) {
    event.preventDefault();
    setStatus("Signing in…");
    const response = await api("/api/v2/session", { method: "POST", body: JSON.stringify({ email: "ann.synthetic@example.com", password }) });
    const body = await response.json();
    if (!response.ok) {
      setStatus("Sign-in was denied.");
      return;
    }
    setToken(body.token);
    setStatus("Signed in as the synthetic leasing account.");
    const propertiesResponse = await api("/api/v2/properties", { headers: { Authorization: `Bearer ${body.token}` } });
    const propertyBody = await propertiesResponse.json();
    setProperties(propertyBody.properties || []);
  }

  async function inquire(listingId) {
    setStatus("Submitting inquiry…");
    const response = await api("/api/v2/inquiries", {
      method: "POST",
      body: JSON.stringify({ listing_id: listingId, name: "Synthetic Guest", email: "guest@example.com", intent: "showing", message: "Example only", idempotency_key: `ui-${listingId}-${Date.now()}` }),
    });
    const body = await response.json();
    if (!response.ok) {
      setStatus(body.detail?.message || "Inquiry was not accepted.");
      return;
    }
    setInquiryId(body.inquiry_id);
    setStatus("Inquiry received. Staff can triage it.");
  }

  async function staff(path, body) {
    const response = await api(path, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(body) });
    const payload = await response.json();
    if (response.status === 409) setStatus(payload.detail?.message || "The record changed. Reload and try again.");
    else if (response.status === 403) setStatus("This account cannot change that record.");
    else if (!response.ok) setStatus(payload.detail?.message || "The change was not saved.");
    return { response, payload };
  }

  async function createProperty(event) {
    event.preventDefault();
    if (propertyName.trim().length < 2) {
      setStatus("Enter a property name of at least 2 characters.");
      return;
    }
    setStatus("Creating property…");
    const { response, payload } = await staff("/api/v2/properties", { name: propertyName, property_type: "multifamily", idempotency_key: `ui-prop-${Date.now()}` });
    if (!response.ok) return;
    setPropertyId(payload.id);
    setPropertyVersion(payload.version);
    setStatus("Property saved. It remains after refresh.");
    const propertiesResponse = await api("/api/v2/properties", { headers: { Authorization: `Bearer ${token}` } });
    const propertyBody = await propertiesResponse.json();
    setProperties(propertyBody.properties || []);
  }

  async function renameProperty(event) {
    event.preventDefault();
    setStatus("Saving property name…");
    const { response, payload } = await staff(`/api/v2/properties/${propertyId}`, { name: propertyName, expected_version: propertyVersion, idempotency_key: `ui-edit-${propertyId}-${Date.now()}` });
    if (!response.ok) return;
    setPropertyVersion(payload.version);
    setStatus("Property name saved.");
  }

  async function createBuilding(event) {
    event.preventDefault();
    setStatus("Creating building…");
    const { response, payload } = await staff("/api/v2/buildings", { property_id: propertyId, name: buildingName, allowed_uses: ["residential", "commercial"], idempotency_key: `ui-bldg-${Date.now()}` });
    if (!response.ok) return;
    setBuildingId(payload.id);
    setStatus("Building saved.");
  }

  async function createSpace(event) {
    event.preventDefault();
    setStatus("Creating space…");
    const { response, payload } = await staff("/api/v2/spaces", {
      property_id: propertyId, building_id: buildingId, label: spaceLabel, use: spaceUse, square_feet: 700, idempotency_key: `ui-space-${Date.now()}`,
    });
    if (!response.ok) return;
    setSpaceId(payload.id);
    setSpaceVersion(payload.version);
    setStatus(`${spaceUse} space saved.`);
  }

  async function offerSpace() {
    setStatus("Updating availability…");
    const { response, payload } = await staff(`/api/v2/spaces/${spaceId}/transition`, {
      dimension: "availability", value: "offerable", expected_version: spaceVersion, idempotency_key: `ui-tr-${spaceId}-${Date.now()}`,
    });
    if (!response.ok) return;
    setSpaceVersion(payload.version);
    setStatus("Space is offerable. Publication stays independent.");
  }

  async function loadActivity() {
    setStatus("Loading activity…");
    const response = await api(`/api/v2/activity?resource_id=${propertyId}`, { headers: { Authorization: `Bearer ${token}` } });
    const body = await response.json();
    setActivity(body.activity || []);
    setStatus(response.ok ? "Activity is limited to this account's organization." : "Activity is unavailable.");
  }

  async function runDelivery() {
    setStatus("Running synthetic delivery…");
    const response = await api("/api/v2/worker/once", { method: "POST" });
    const body = await response.json();
    setDelivery(body.claimed ? `${body.status} (${body.id})` : "No pending delivery.");
    setStatus("Synthetic delivery does not claim exactly-once external delivery.");
  }

  async function triage() {
    setStatus("Saving triage…");
    const response = await api(`/api/v2/inquiries/${inquiryId}/triage`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ decision: "assigned", expected_version: 1, idempotency_key: `ui-triage-${inquiryId}` }),
    });
    const body = await response.json();
    setStatus(response.ok ? "Inquiry assigned. Refresh keeps the database row." : (body.detail?.message || "Triage was not saved."));
  }

  return (
    <main className="min-h-screen bg-linen px-5 py-16 text-obsidian">
      <h1 className="font-heading text-4xl">Reference operations</h1>
      <p className="mt-3 max-w-2xl">{status}</p>
      <button className="mt-6 underline" type="button" onClick={loadListings}>Load published listings</button>
      <ul className="mt-4 space-y-3">
        {listings.length === 0 ? <li>No listings loaded.</li> : listings.map((listing) => (
          <li key={listing.listing_id}>
            {listing.property_name} · {listing.label}
            <button className="ml-3 underline" type="button" onClick={() => inquire(listing.listing_id)}>Submit inquiry</button>
          </li>
        ))}
      </ul>
      <form className="mt-8 max-w-md space-y-3" onSubmit={login}>
        <label className="block">Local synthetic password
          <input className="mt-1 w-full border px-3 py-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" />
        </label>
        <button className="bg-obsidian px-4 py-2 text-linen" type="submit">Sign in as leasing</button>
      </form>
      <p className="mt-4">{properties.length ? `${properties.length} properties visible to this account.` : "No staff properties loaded."}</p>
      <button className="mt-4 underline" type="button" disabled={!token || !inquiryId} onClick={triage}>Triage the inquiry</button>
      <form className="mt-8 max-w-md space-y-3" onSubmit={propertyId ? renameProperty : createProperty}>
        <label className="block">Property name
          <input className="mt-1 w-full border px-3 py-2" value={propertyName} onChange={(event) => setPropertyName(event.target.value)} />
        </label>
        <button className="bg-obsidian px-4 py-2 text-linen" type="submit" disabled={!token}>{propertyId ? "Save property name" : "Create property"}</button>
      </form>
      <form className="mt-6 max-w-md space-y-3" onSubmit={createBuilding}>
        <label className="block">Building name
          <input className="mt-1 w-full border px-3 py-2" value={buildingName} onChange={(event) => setBuildingName(event.target.value)} />
        </label>
        <button className="bg-obsidian px-4 py-2 text-linen" type="submit" disabled={!token || !propertyId}>Create building</button>
      </form>
      <form className="mt-6 max-w-md space-y-3" onSubmit={createSpace}>
        <label className="block">Space label
          <input className="mt-1 w-full border px-3 py-2" value={spaceLabel} onChange={(event) => setSpaceLabel(event.target.value)} />
        </label>
        <label className="block">Use
          <select className="mt-1 w-full border px-3 py-2" value={spaceUse} onChange={(event) => setSpaceUse(event.target.value)}>
            <option value="residential">Residential</option>
            <option value="commercial">Commercial</option>
          </select>
        </label>
        <button className="bg-obsidian px-4 py-2 text-linen" type="submit" disabled={!token || !buildingId}>Create space</button>
      </form>
      <button className="mt-4 underline" type="button" disabled={!spaceId} onClick={offerSpace}>Mark space offerable</button>
      <button className="ml-4 underline" type="button" disabled={!propertyId} onClick={loadActivity}>Show activity</button>
      <button className="ml-4 underline" type="button" onClick={runDelivery}>Run synthetic delivery</button>
      <p className="mt-3">{delivery}</p>
      <ul className="mt-3">{activity.length === 0 ? <li>No activity loaded.</li> : activity.map((item) => <li key={item.id}>{item.summary}</li>)}</ul>
    </main>
  );
}
