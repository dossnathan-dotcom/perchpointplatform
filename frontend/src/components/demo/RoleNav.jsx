import { Link, useNavigate } from "react-router-dom";

function csrfToken() {
  const item = document.cookie.split("; ").find((value) => value.startsWith("pp_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

export const staffLinks = [["Overview", "/owner"], ["Homes", "/rentals"], ["Work", "/leasing-desk"], ["Maintenance", "/maintenance"], ["My jobs", "/maintenance/jobs"], ["Accounts", "/ledger"], ["Payments", "/ledger#payments"], ["Access", "/access/onboarding"]];
export const residentLinks = [["Home", "/portal"], ["Lease and account", "/portal#lease"], ["Payments", "/portal#payments"], ["Report a problem", "/portal/report"], ["My requests", "/portal/requests"]];

export function Workspace({ links, children }) {
  const navigate = useNavigate();
  async function signOut() {
    await fetch("/api/v2/auth/sign-out", {
      method: "POST",
      credentials: "include",
      headers: { "x-perchpoint-csrf": csrfToken() },
    }).catch(() => {});
    sessionStorage.clear();
    navigate("/sign-in", { replace: true });
  }
  return (
    <div className="min-h-screen bg-[#F3F6FB] text-[#172B4D] lg:grid lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="bg-[#142538] text-white">
        <p className="px-4 py-4 text-xs font-semibold uppercase tracking-wide text-[#9fd3d8]">Local synthetic</p>
        <nav aria-label="Workspace" className="flex gap-2 overflow-x-auto px-3 pb-4 lg:block lg:space-y-1">
          {links.map(([label, href]) => (
            <Link key={href} to={href} className="block whitespace-nowrap rounded px-3 py-2 text-sm hover:bg-white/10">{label}</Link>
          ))}
          <button className="block rounded px-3 py-2 text-left text-sm hover:bg-white/10" type="button" onClick={signOut}>Sign out</button>
        </nav>
      </aside>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
