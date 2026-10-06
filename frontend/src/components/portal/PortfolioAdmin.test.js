import { act } from "react";
import { createRoot } from "react-dom/client";
import { PortfolioAdmin } from "./PortfolioAdmin";

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
  global.fetch = jest.fn();
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  jest.restoreAllMocks();
});

test("portfolio inventory renders records and a denied state", async () => {
  fetch.mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: async () => ({ records: [{ property_id: "p1", space_id: "s1", name: "Synthetic Court", label: "Home 1", lifecycle: "active", publication: "unpublished" }] }),
  });
  await act(async () => root.render(<PortfolioAdmin />));
  await waitFor(() => container.textContent.includes("Synthetic Court"));
  expect(container.querySelector("table")).not.toBeNull();
  expect(container.textContent).toContain("does not syndicate");
});

test("portfolio inventory exposes an error when the service is unavailable", async () => {
  fetch.mockRejectedValueOnce(new Error("offline"));
  await act(async () => root.render(<PortfolioAdmin />));
  await waitFor(() => container.textContent.includes("could not be loaded"));
  expect(container.querySelector("[role=alert]")).not.toBeNull();
});
