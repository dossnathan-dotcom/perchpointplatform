import { useState } from "react";

const api = (path, options = {}) => fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });

export function ReferenceOperations() {
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [status, setStatus] = useState("Enter the local synthetic password from backend/.env. This page is not production sign-in.");
  const [listings, setListings] = useState([]);
  const [properties, setProperties] = useState([]);
  const [inquiryId, setInquiryId] = useState("");

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
    </main>
  );
}
