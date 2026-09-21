import { act } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { PORTAL_VIEWS } from "@/data/portalData";
import { slug } from "@/data/siteData";

const ROLE_MATRIX = [
  ["owner", "Owner Command Center"],
  ["super-admin", "Platform Administration"],
  ["leasing", "Leasing Operations"],
  ["accounting", "Accounting"],
  ["maintenance", "Maintenance Operations"],
  ["subcontractor", "Subcontractor Assignments"],
  ["resident", "Resident Portal"],
  ["applicant", "Applicant Portal"],
];

let container;
let root;

const waitForCondition = async (predicate, timeout = 3000) => {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (predicate()) return;
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 25));
    });
  }
  throw new Error("Condition was not met in time");
};

// Radix mounts the real dialog in a body portal, outside the React root container.
const getByTestId = (id) => document.body.querySelector(`[data-testid="${id}"]`);

const renderAt = async (path) => {
  window.history.pushState({}, "", path);
  await act(async () => {
    // A fresh mount models direct URL entry; history navigation is tested separately.
    root.render(<App key={path} />);
  });
};

const click = async (el) => {
  await act(async () => {
    el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
};

const setSelectValue = async (el, value) => {
  await act(async () => {
    el.value = value;
    el.dispatchEvent(new Event("change", { bubbles: true }));
  });
};

const setInputValue = async (el, value) => {
  await act(async () => {
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
};

const historyStep = async (method) => {
  await act(async () => {
    window.history[method]();
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
};

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => {
    root.unmount();
  });
  container.remove();
});

describe("PerchPoint routing remediation", () => {
  test.each(ROLE_MATRIX)(
    "gate->modal entry renders workspace and clears modal for %s",
    async (roleId, workspaceLabel) => {
      await renderAt("/perchpoint");
      await click(getByTestId("portal-gate-login-btn"));
      await waitForCondition(() => !!getByTestId("perchpoint-role-select"));
      await setSelectValue(getByTestId("perchpoint-role-select"), roleId);
      await click(getByTestId("perchpoint-login-submit-btn"));

      await waitForCondition(() => !!getByTestId("perchpoint-portal-page"));
      await waitForCondition(() => window.location.pathname === `/perchpoint/${roleId}`);
      expect(getByTestId("portal-workspace-label").textContent).toContain(workspaceLabel);
      expect(getByTestId("perchpoint-login-dialog")).toBeNull();
      expect(getByTestId("perchpoint-portal-gate")).toBeNull();
    }
  );

  test("role switch clears toolbar panel and route state", async () => {
    await renderAt("/perchpoint/leasing");
    await waitForCondition(() => !!getByTestId("perchpoint-portal-page"));

    await click(getByTestId("portal-notifications-btn"));
    await waitForCondition(() => !!getByTestId("portal-notifications-panel"));

    await setSelectValue(getByTestId("portal-role-switcher"), "owner");
    await waitForCondition(() => window.location.pathname === "/perchpoint/owner");

    expect(getByTestId("portal-notifications-panel")).toBeNull();
    expect(getByTestId("portal-workspace-label").textContent).toContain("Owner Command Center");
  });

  test.each(ROLE_MATRIX)(
    "direct nested route renders expected workspace/tab for %s",
    async (roleId, workspaceLabel) => {
      const firstTab = PORTAL_VIEWS[roleId].tabs[0];
      await renderAt(`/perchpoint/${roleId}/${slug(firstTab)}`);

      await waitForCondition(() => !!getByTestId("perchpoint-portal-page"));
      await waitForCondition(() => window.location.pathname === `/perchpoint/${roleId}/${slug(firstTab)}`);
      expect(getByTestId("portal-workspace-label").textContent).toContain(workspaceLabel);
      expect(getByTestId("portal-active-page-title").textContent).toContain(firstTab);
    }
  );

  test("client nested navigation with history back/forward does not resurrect modal or stale panel", async () => {
    await renderAt("/perchpoint");
    await click(getByTestId("portal-gate-login-btn"));
    await waitForCondition(() => !!getByTestId("perchpoint-role-select"));
    await setSelectValue(getByTestId("perchpoint-role-select"), "leasing");
    await click(getByTestId("perchpoint-login-submit-btn"));
    await waitForCondition(() => window.location.pathname === "/perchpoint/leasing");

    await click(getByTestId("portal-notifications-btn"));
    await waitForCondition(() => !!getByTestId("portal-notifications-panel"));
    await click(getByTestId("portal-tab-leasing-1"));
    await waitForCondition(() => window.location.pathname === "/perchpoint/leasing/operational-inbox");

    await historyStep("back");
    await waitForCondition(() => window.location.pathname === "/perchpoint/leasing");
    expect(getByTestId("perchpoint-login-dialog")).toBeNull();
    expect(getByTestId("perchpoint-portal-gate")).toBeNull();
    expect(getByTestId("portal-notifications-panel")).toBeNull();

    await historyStep("forward");
    await waitForCondition(() => window.location.pathname === "/perchpoint/leasing/operational-inbox");
    expect(getByTestId("portal-active-page-title").textContent).toContain("Operational inbox");
    expect(getByTestId("portal-notifications-panel")).toBeNull();
  });

  test("role switch clears stale search/context/state/policy/account/record views", async () => {
    await renderAt("/perchpoint/owner/delegations");
    await waitForCondition(() => !!getByTestId("perchpoint-portal-page"));

    await setInputValue(getByTestId("portal-global-search"), "owner");
    const contextSelect = getByTestId("portal-context-select");
    const contextOption = Array.from(contextSelect.options).find((option) => option.value !== "all");
    expect(contextOption).toBeTruthy();
    await setSelectValue(contextSelect, contextOption.value);

    await setSelectValue(getByTestId("portal-state-select"), "error");
    await waitForCondition(() => !!getByTestId("portal-state-error"));
    await setSelectValue(getByTestId("portal-state-select"), "seeded");
    await waitForCondition(() => !!getByTestId("portal-work-queue"));

    await click(getByTestId("delegation-policy-trigger-btn"));
    await waitForCondition(() => !!getByTestId("delegation-policy-modal"));
    await click(getByTestId("portal-account-menu-btn"));
    await waitForCondition(() => !!getByTestId("portal-account-panel"));
    await click(getByTestId("portal-task-0"));
    await waitForCondition(() => !!getByTestId("portal-record-dialog"));

    await setSelectValue(getByTestId("portal-role-switcher"), "leasing");
    await waitForCondition(() => window.location.pathname === "/perchpoint/leasing");

    expect(getByTestId("delegation-policy-modal")).toBeNull();
    expect(getByTestId("portal-account-panel")).toBeNull();
    expect(getByTestId("portal-record-dialog")).toBeNull();
    expect(getByTestId("portal-global-search").value).toBe("");
    expect(getByTestId("portal-context-select").value).toBe("all");
    expect(getByTestId("portal-state-select").value).toBe("seeded");
    expect(getByTestId("portal-state-error")).toBeNull();
  });

  test("unknown role/view/path routes are controlled", async () => {
    await renderAt("/perchpoint/not-a-role");
    await waitForCondition(() => !!getByTestId("workspace-unavailable"));

    await renderAt("/perchpoint/leasing/not-a-view");
    await waitForCondition(() => !!getByTestId("workspace-unavailable"));

    await renderAt("/perchpoint/leasing/operations-console/extra");
    await waitForCondition(() => !!getByTestId("not-found-page"));

    await renderAt("/perchpointx");
    await waitForCondition(() => !!getByTestId("not-found-page"));
  });
});
