import { useEffect, useState } from "react";
import { phase2 } from "@/api/phase2";

const staffEmail = {
  leasing: "ann.synthetic@example.com",
  "super-admin": "nathan.synthetic@example.com",
};

export function Phase2Kernel({ previewRole }) {
  const preset = staffEmail[previewRole] || "";
  const [email, setEmail] = useState(preset);
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [roleName, setRoleName] = useState("");
  const [status, setStatus] = useState("Development sign-in uses the backend. The preview role above is not authority.");
  const [properties, setProperties] = useState([]);
  const [buildings, setBuildings] = useState([]);
  const [spaces, setSpaces] = useState([]);
  const [inquiries, setInquiries] = useState([]);
  const [name, setName] = useState("");
  const [buildingName, setBuildingName] = useState("");
  const [spaceLabel, setSpaceLabel] = useState("");
  const [spaceUse, setSpaceUse] = useState("residential");
  const [selected, setSelected] = useState("");
  const [buildingId, setBuildingId] = useState("");
  const [spaceId, setSpaceId] = useState("");
  const [spaceVersion, setSpaceVersion] = useState(1);
  const [listingId, setListingId] = useState("");
  const [listingVersion, setListingVersion] = useState(1);
  const [version, setVersion] = useState(1);
  const [expectedVersion, setExpectedVersion] = useState("1");
  const [activity, setActivity] = useState([]);
  const [openInquiry, setOpenInquiry] = useState(null);
  const [note, setNote] = useState("");
  const canWrite = roleName === "leasing" || roleName === "platform_admin";
  const canOperate = roleName === "platform_admin";
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    setToken("");
    setRoleName("");
    setEmail(preset);
    setProperties([]);
    setInquiries([]);
    setOpenInquiry(null);
  }, [previewRole, preset]);

  async function signIn(event) {
    event.preventDefault();
    setStatus("Signing in.");
    const { response, body } = await phase2("/api/v2/session", { method: "POST", body: JSON.stringify({ email, password }) });
    if (!response.ok) {
      setToken("");
      setStatus(response.status === 403 ? "This membership cannot sign in." : "Sign-in was denied.");
      return;
    }
    setToken(body.token);
    setRoleName(body.role_name);
    setStatus(`Signed in as ${body.role_name}. Preview role ${previewRole} did not grant this.`);
    await refresh(body.token);
  }

  async function refresh(current = token) {
    const auth = { Authorization: `Bearer ${current}` };
    const propertiesResponse = await phase2("/api/v2/properties", { headers: auth });
    const inquiryResponse = await phase2("/api/v2/inquiries", { headers: auth });
    if (propertiesResponse.response.status === 403) setStatus("This session cannot read the portfolio.");
    setProperties(propertiesResponse.body.properties || []);
    setInquiries(inquiryResponse.body.inquiries || []);
  }

  async function chooseProperty(item) {
    setSelected(item.id);
    setVersion(item.version);
    setExpectedVersion(String(item.version));
    setName(item.name);
    const { body } = await phase2(`/api/v2/buildings?property_id=${item.id}`, { headers });
    setBuildings(body.buildings || []);
    setSpaces([]);
    const activityResponse = await phase2(`/api/v2/activity?resource_id=${item.id}`, { headers });
    setActivity(activityResponse.body.activity || []);
  }

  async function createProperty(event) {
    event.preventDefault();
    if (name.trim().length < 2) { setStatus("Enter a property name."); return; }
    const { response, body } = await phase2("/api/v2/properties", { method: "POST", headers, body: JSON.stringify({ name, property_type: "multifamily", idempotency_key: `ui-${Date.now()}` }) });
    if (!response.ok) { setStatus(body.detail?.message || "The property was not created."); return; }
    setSelected(body.id);
    setVersion(body.version);
    setExpectedVersion(String(body.version));
    setStatus("Property saved.");
    const activityResponse = await phase2(`/api/v2/activity?resource_id=${body.id}`, { headers });
    setActivity(activityResponse.body.activity || []);
    await refresh();
  }

  async function rename(event) {
    event.preventDefault();
    const { response, body } = await phase2(`/api/v2/properties/${selected}`, { method: "POST", headers, body: JSON.stringify({ name, expected_version: Number(expectedVersion), idempotency_key: `rename-${selected}-${Date.now()}` }) });
    if (response.status === 409) { setStatus("This property changed. Reload it and try again."); return; }
    if (!response.ok) { setStatus(body.detail?.message || "The name was not saved."); return; }
    setVersion(body.version);
    setExpectedVersion(String(body.version));
    setStatus("Property name saved.");
    await refresh();
  }

  async function createBuilding(event) {
    event.preventDefault();
    const { response, body } = await phase2("/api/v2/buildings", { method: "POST", headers, body: JSON.stringify({ property_id: selected, name: buildingName, allowed_uses: ["residential", "commercial"], idempotency_key: `b-${Date.now()}` }) });
    if (!response.ok) { setStatus(body.detail?.message || "The building was not created."); return; }
    setBuildingId(body.id);
    setStatus("Building saved.");
    const listed = await phase2(`/api/v2/buildings?property_id=${selected}`, { headers });
    setBuildings(listed.body.buildings || []);
  }

  async function chooseBuilding(id) {
    setBuildingId(id);
    const { body } = await phase2(`/api/v2/spaces?building_id=${id}`, { headers });
    setSpaces(body.spaces || []);
  }

  async function createSpace(event) {
    event.preventDefault();
    const { response, body } = await phase2("/api/v2/spaces", { method: "POST", headers, body: JSON.stringify({ property_id: selected, building_id: buildingId, label: spaceLabel, use: spaceUse, square_feet: 720, idempotency_key: `s-${Date.now()}` }) });
    if (!response.ok) { setStatus(body.detail?.message || "The space was not created."); return; }
    setSpaceId(body.id);
    setSpaceVersion(body.version);
    setStatus(`${spaceUse} space saved.`);
    await chooseBuilding(buildingId);
  }

  async function offerSpace() {
    const { response, body } = await phase2(`/api/v2/spaces/${spaceId}/transition`, { method: "POST", headers, body: JSON.stringify({ dimension: "availability", value: "offerable", expected_version: spaceVersion, idempotency_key: `t-${Date.now()}` }) });
    if (response.status === 409) { setStatus("This space changed. Reload it and try again."); return; }
    if (!response.ok) { setStatus(body.detail?.message || "The space was not updated."); return; }
    setSpaceVersion(body.version);
    setStatus("Space is offerable.");
  }

  async function createListing() {
    const property = properties.find((item) => item.id === selected);
    const { response, body } = await phase2("/api/v2/listings", { method: "POST", headers, body: JSON.stringify({ space_id: spaceId, property_name: property?.name || name, label: spaceLabel, use: spaceUse, municipality: "Cincinnati", state: "OH", amount_minor: 150000, currency: "USD", idempotency_key: `l-${Date.now()}` }) });
    if (!response.ok) { setStatus(body.detail?.message || "The listing was not created."); return; }
    setListingId(body.id);
    setListingVersion(body.version || 1);
    setStatus("Listing saved as unpublished.");
  }

  async function publish(publication) {
    const { response, body } = await phase2(`/api/v2/listings/${listingId}/publication`, { method: "POST", headers, body: JSON.stringify({ publication, expected_version: listingVersion, idempotency_key: `p-${publication}-${Date.now()}` }) });
    if (response.status === 409) { setStatus("This listing changed. Reload it and try again."); return; }
    if (!response.ok) { setStatus(body.detail?.message || "Publication was not changed."); return; }
    setListingVersion(body.version);
    setStatus(`Listing is ${publication}.`);
  }

  async function openInquiryDetail(inquiry) {
    const { response, body } = await phase2(`/api/v2/inquiries/${inquiry.id}`, { headers });
    if (response.status === 404) { setStatus("That inquiry was not found."); return; }
    if (!response.ok) { setStatus("That inquiry is not available to this session."); return; }
    setOpenInquiry(body);
    const activityResponse = await phase2(`/api/v2/activity?resource_id=${inquiry.id}`, { headers });
    setActivity(activityResponse.body.activity || []);
  }

  async function triage(decision) {
    const inquiry = openInquiry.inquiry;
    const { response, body } = await phase2(`/api/v2/inquiries/${inquiry.id}/triage`, { method: "POST", headers, body: JSON.stringify({ decision, expected_version: inquiry.version, idempotency_key: `q-${decision}-${inquiry.id}-${Date.now()}` }) });
    if (response.status === 409) { setStatus("This inquiry changed. Reload it and try again."); return; }
    if (!response.ok) { setStatus(body.detail?.message || "Triage was not saved."); return; }
    await refresh();
    await openInquiryDetail({ id: inquiry.id });
    setStatus(`Inquiry is ${decision}.`);
  }

  async function addNote(event) {
    event.preventDefault();
    const { response, body } = await phase2(`/api/v2/inquiries/${openInquiry.inquiry.id}/notes`, { method: "POST", headers, body: JSON.stringify({ body: note, idempotency_key: `n-${Date.now()}` }) });
    if (!response.ok) { setStatus(body.detail?.message || "The note was not saved."); return; }
    setNote("");
    setStatus("Internal note saved.");
    await openInquiryDetail(openInquiry.inquiry);
  }

  async function deliver() {
    const { body } = await phase2("/api/v2/worker/once", { method: "POST", headers });
    setStatus(body.claimed ? `Synthetic delivery ${body.status}. This is not exactly-once external delivery.` : "No pending synthetic delivery.");
  }

  if (previewRole === "owner") {
    return <section className="mb-10 border border-white/20 p-5" aria-label="Phase 2 operations" data-testid="phase2-kernel"><h2 className="font-heading text-2xl">Live portfolio</h2><p data-testid="owner-preview-boundary">Owner preview does not authenticate and cannot change records.</p></section>;
  }
  if (!preset && previewRole !== "leasing" && previewRole !== "super-admin") return null;

  return <section className="mb-10 border border-white/20 p-5" aria-label="Phase 2 operations" data-testid="phase2-kernel">
    <h2 className="font-heading text-2xl">Live portfolio</h2>
    <p className="mt-2 max-w-3xl text-sm text-linen/75" role="status" data-testid="phase2-status">{status}</p>
    {!token && <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={signIn}>
      <label className="text-sm">Development email<input className="mt-1 block border border-white/30 bg-transparent px-3 py-2" name="dev-email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label className="text-sm">Development password<input className="mt-1 block border border-white/30 bg-transparent px-3 py-2" name="dev-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      <button className="bg-copper px-4 py-2 text-white" type="submit" data-testid="phase2-sign-in">Sign in for this workspace</button>
    </form>}
    {token && <div className="mt-6 grid gap-8">
      <div>
        <h3 className="text-sm text-gold">Properties</h3>
        <ul className="mt-3" data-testid="phase2-property-list">{properties.length === 0 ? <li>No properties are visible to this session.</li> : properties.map((item) => <li key={item.id}><button type="button" className="underline" onClick={() => chooseProperty(item)}>{item.name}</button></li>)}</ul>
        {canWrite && <form className="mt-4 grid gap-2" onSubmit={selected ? rename : createProperty}>
          <label>Property name<input className="mt-1 w-full border border-white/30 bg-transparent px-3 py-2" name="property-name" value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label>Expected version<input className="mt-1 w-24 border border-white/30 bg-transparent px-3 py-2" name="expected-version" value={expectedVersion} onChange={(event) => setExpectedVersion(event.target.value)} /></label>
          <button className="w-fit bg-white px-3 py-2 text-obsidian" type="submit" data-testid="phase2-save-property">{selected ? "Save property name" : "Create property"}</button>
        </form>}
        {selected && <p className="mt-2 text-xs">Selected property version {version}</p>}
      </div>
      {canWrite && selected && <form className="grid gap-2" onSubmit={createBuilding}>
        <h3 className="text-sm text-gold">Building</h3>
        <ul>{buildings.map((item) => <li key={item.id}><button type="button" className="underline" onClick={() => chooseBuilding(item.id)}>{item.name}</button></li>)}</ul>
        <label>Building name<input className="mt-1 w-full border border-white/30 bg-transparent px-3 py-2" name="building-name" value={buildingName} onChange={(event) => setBuildingName(event.target.value)} /></label>
        <button className="w-fit bg-white px-3 py-2 text-obsidian" type="submit" data-testid="phase2-create-building">Create building</button>
      </form>}
      {canWrite && buildingId && <form className="grid gap-2" onSubmit={createSpace}>
        <h3 className="text-sm text-gold">Space</h3>
        <ul data-testid="phase2-space-list">{spaces.map((item) => <li key={item.id}>{item.label} · {item.use} · {item.availability}</li>)}</ul>
        <label>Label<input className="mt-1 w-full border border-white/30 bg-transparent px-3 py-2" name="space-label" value={spaceLabel} onChange={(event) => setSpaceLabel(event.target.value)} /></label>
        <label>Use<select className="mt-1 border border-white/30 bg-obsidian px-3 py-2" name="space-use" value={spaceUse} onChange={(event) => setSpaceUse(event.target.value)}><option value="residential">Residential</option><option value="commercial">Commercial</option></select></label>
        <button className="w-fit bg-white px-3 py-2 text-obsidian" type="submit" data-testid="phase2-create-space">Create space</button>
        {spaceId && <button className="w-fit underline" type="button" onClick={offerSpace} data-testid="phase2-offer-space">Mark offerable</button>}
      </form>}
      {canWrite && spaceId && <div className="flex flex-wrap gap-3">
        <button className="underline" type="button" onClick={createListing} data-testid="phase2-create-listing">Create listing</button>
        {listingId && <>
          <button className="underline" type="button" onClick={() => publish("published")} data-testid="phase2-publish">Publish</button>
          <button className="underline" type="button" onClick={() => publish("unpublished")} data-testid="phase2-unpublish">Unpublish</button>
          <button className="underline" type="button" onClick={() => publish("restricted")} data-testid="phase2-restrict">Restrict</button>
        </>}
      </div>}
      <div>
        <h3 className="text-sm text-gold">Inquiries</h3>
        <ul className="mt-3" data-testid="phase2-inquiry-list">{inquiries.length === 0 ? <li>No inquiries are visible to this session.</li> : inquiries.map((item) => <li key={item.id}><button type="button" className="underline" onClick={() => openInquiryDetail(item)}>{item.name} · {item.status}</button></li>)}</ul>
        {openInquiry && <article className="mt-4 border border-white/20 p-4" data-testid="phase2-inquiry-detail">
          <h4 className="font-heading text-xl">{openInquiry.inquiry.name}</h4>
          <p>{openInquiry.inquiry.message}</p>
          <p className="text-sm text-gold">{openInquiry.inquiry.status} · version {openInquiry.inquiry.version}</p>
          {canWrite && <div className="mt-3 flex flex-wrap gap-3">
            <button type="button" className="underline" onClick={() => triage("assigned")} data-testid="phase2-assign">Assign</button>
            <button type="button" className="underline" onClick={() => triage("contacted")} data-testid="phase2-triage">Mark contacted</button>
          </div>}
          <h5 className="mt-4 text-sm">Internal notes</h5>
          <ul data-testid="phase2-notes">{openInquiry.notes.length === 0 ? <li>No internal notes.</li> : openInquiry.notes.map((item) => <li key={item.id}>{item.body}</li>)}</ul>
          {canWrite && <form className="mt-3" onSubmit={addNote}>
            <label>Note<textarea className="mt-1 w-full border border-white/30 bg-transparent px-3 py-2" name="inquiry-note" value={note} onChange={(event) => setNote(event.target.value)} /></label>
            <button className="mt-2 bg-white px-3 py-2 text-obsidian" type="submit" data-testid="phase2-add-note">Save note</button>
          </form>}
        </article>}
      </div>
      <div>
        <h3 className="text-sm text-gold">Activity</h3>
        <ul data-testid="phase2-activity">{activity.length === 0 ? <li>No activity loaded.</li> : activity.map((item) => <li key={item.id}>{item.summary}</li>)}</ul>
        {canOperate && <button className="mt-3 underline" type="button" onClick={deliver} data-testid="phase2-deliver">Run synthetic delivery</button>}
      </div>
    </div>}
  </section>;
}
