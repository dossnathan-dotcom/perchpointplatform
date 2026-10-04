import { act } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Phase6AccessWorkspace, Phase6BoundaryPage, phase6Api } from "./Phase6Access";

let container;
let root;

async function waitFor(predicate) {
  const started = Date.now();
  while (Date.now() - started < 2000) {
    if (predicate()) return;
    await act(async () => new Promise((resolve) => setTimeout(resolve, 10)));
  }
  throw new Error("Condition was not met");
}

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  sessionStorage.clear();
  global.fetch = jest.fn();
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  jest.restoreAllMocks();
});

test("API failures retain the server correlation ID", async () => {
  fetch.mockResolvedValue({
    ok: false,
    status: 403,
    headers: new Headers({ "x-request-id": "request-123" }),
    json: async () => ({ detail: { code: "denied", message: "Access denied." } }),
  });
  await expect(phase6Api("/api/v2/access/users")).rejects.toMatchObject({
    message: "Access denied.",
    status: 403,
    correlationId: "request-123",
  });
});

test("access denial exposes correlation and request path", async () => {
  window.history.pushState({}, "", "/access-denied?correlation_id=request-456&return_to=%2Fdocuments&capability=document.read");
  await act(async () => root.render(<BrowserRouter><Phase6BoundaryPage kind="access-denied" /></BrowserRouter>));
  expect(container.textContent).toContain("request-456");
  const requestLink = container.querySelector('a[href^="/access/access-requests"]');
  expect(requestLink).not.toBeNull();
  expect(decodeURIComponent(requestLink.getAttribute("href"))).toContain("document.read");
});

test("onboarding shows current server membership and unavailable states", async () => {
  fetch.mockImplementation(async (path) => {
    if (path === "/api/v2/auth/me") return { ok: true, headers: new Headers(), json: async () => ({ account_id: "account-1", organization_id: "org-1", membership_id: "membership-1", role_name: "leasing", assurance: "aal1" }) };
    if (path === "/api/v2/access/users") return { ok: false, status: 403, headers: new Headers(), json: async () => ({ detail: { message: "Denied" } }) };
    if (path === "/api/v2/auth/mfa/factors") return { ok: true, headers: new Headers(), json: async () => ({ factors: [] }) };
    throw new Error(`Unexpected request ${path}`);
  });
  window.history.pushState({}, "", "/access/onboarding");
  await act(async () => root.render(<BrowserRouter><Phase6AccessWorkspace surface="onboarding" /></BrowserRouter>));
  await waitFor(() => container.textContent.includes("First access checklist"));
  expect(container.textContent).toContain("leasing");
  expect(container.textContent).toContain("Policy acceptance state is unavailable");
  expect(container.textContent).toContain("Setup still required");
});
