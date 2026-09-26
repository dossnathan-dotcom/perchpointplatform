import { useEffect, useId, useState } from "react";

export function IconButton({ label, children, ...props }) {
  return <button type="button" aria-label={label} className="portal-icon" {...props}>{children}</button>;
}

export function ButtonGroup({ label, children }) {
  return <div role="group" aria-label={label} className="flex flex-wrap gap-2">{children}</div>;
}

export function ExternalLink({ href, children }) {
  return <a href={href} className="underline" rel="noreferrer">{children}<span className="sr-only"> (opens in a new tab)</span></a>;
}

export function CopyAction({ value, label = "Copy reference" }) {
  const [copied, setCopied] = useState(false);
  return <button type="button" className="min-h-11 underline" onClick={async () => { await navigator.clipboard?.writeText(value); setCopied(true); }}>{copied ? "Copied" : label}</button>;
}

export function DestructiveConfirm({ name, onConfirm }) {
  const [open, setOpen] = useState(false);
  return <div>
    <button type="button" className="min-h-11 underline" onClick={() => setOpen(true)}>Remove {name}</button>
    {open ? <div role="alertdialog" aria-modal="true" aria-labelledby="destroy-title" className="mt-2 border p-3">
      <h3 id="destroy-title">Remove {name}?</h3>
      <p>This preview does not delete a production record. The example can be restored by returning to the seeded view.</p>
      <button type="button" className="min-h-11" onClick={() => { setOpen(false); onConfirm?.(); }}>Confirm removal</button>
      <button type="button" className="min-h-11" onClick={() => setOpen(false)}>Cancel</button>
    </div> : null}
  </div>;
}

export function TextArea({ id, describedBy, ...props }) {
  return <textarea id={id} className="min-h-24 w-full border px-3 py-2" aria-describedby={describedBy} {...props} />;
}

export function SelectField({ id, describedBy, children, ...props }) {
  return <select id={id} className="min-h-11 w-full border px-2" aria-describedby={describedBy} {...props}>{children}</select>;
}

export function CheckboxField({ id, label }) {
  return <label className="flex min-h-11 items-center gap-2" htmlFor={id}><input id={id} type="checkbox" />{label}</label>;
}

export function RadioGroup({ name, legend, options }) {
  return <fieldset className="grid gap-2"><legend>{legend}</legend>{options.map((option) => <label key={option} className="flex min-h-11 items-center gap-2"><input type="radio" name={name} value={option} />{option}</label>)}</fieldset>;
}

export function SwitchField({ id, label }) {
  return <label className="flex min-h-11 items-center gap-2" htmlFor={id}><input id={id} type="checkbox" role="switch" />{label}</label>;
}

export function DateField({ id, label }) {
  return <label className="grid gap-1" htmlFor={id}>{label}<input id={id} type="date" className="min-h-11 border px-3" autoComplete="off" /></label>;
}

export function MoneyField({ id, label }) {
  return <label className="grid gap-1" htmlFor={id}>{label}<input id={id} inputMode="decimal" className="min-h-11 border px-3" aria-describedby={`${id}-unit`} /><span id={`${id}-unit`}>US dollars</span></label>;
}

export function AddressField({ id }) {
  return <fieldset className="grid gap-2"><legend>Address</legend><label htmlFor={`${id}-line`}>Street<input id={`${id}-line`} className="mt-1 min-h-11 w-full border px-3" autoComplete="address-line1" /></label><label htmlFor={`${id}-unit`}>Unit<input id={`${id}-unit`} className="mt-1 min-h-11 w-full border px-3" autoComplete="address-line2" /></label></fieldset>;
}

export function SearchField({ id, label }) {
  return <label className="grid gap-1" htmlFor={id}>{label}<input id={id} type="search" className="min-h-11 border px-3" /></label>;
}

export function FormSection({ title, children }) {
  return <section className="grid gap-3 border p-3"><h3 className="text-lg">{title}</h3>{children}</section>;
}

export function CharacterCount({ id, max, value }) {
  return <p id={id}>{value.length} of {max} characters</p>;
}

export function ReadOnlyValue({ label, value }) {
  return <div><dt className="text-sm">{label}</dt><dd>{value}</dd></div>;
}

export function SavingIndicator({ state = "saved" }) {
  const copy = { saving: "Saving.", saved: "Saved.", failed: "Not saved." };
  return <p role="status">{copy[state] || copy.saved}</p>;
}

export function Breadcrumbs({ items }) {
  return <nav aria-label="Breadcrumb"><ol className="flex flex-wrap gap-2 text-sm">{items.map((item, index) => <li key={item.label}>{index > 0 ? <span aria-hidden="true"> / </span> : null}{item.href ? <a href={item.href}>{item.label}</a> : <span aria-current="page">{item.label}</span>}</li>)}</ol></nav>;
}

export function Tabs({ tabs, active, onChange }) {
  return <div role="tablist" aria-label="Section">{tabs.map((tab) => <button key={tab} type="button" role="tab" aria-selected={tab === active} className="min-h-11 px-3" onClick={() => onChange(tab)}>{tab}</button>)}</div>;
}

export function Pagination({ page, pages, onPage }) {
  return <nav aria-label="Pagination"><button type="button" className="min-h-11 px-3" onClick={() => onPage(Math.max(1, page - 1))} disabled={page === 1}>Previous</button><span>Page {page} of {pages}</span><button type="button" className="min-h-11 px-3" onClick={() => onPage(Math.min(pages, page + 1))} disabled={page === pages}>Next</button></nav>;
}

export function InlineNotice({ children }) {
  return <p className="border-l-4 border-current px-3 py-2" role="status">{children}</p>;
}

export function Spinner({ label = "Loading" }) {
  return <p role="status">{label}</p>;
}

export function Skeleton() {
  return <div className="h-16 animate-pulse border" aria-hidden="true" />;
}

export function StatePanel({ title, children, testId }) {
  return <div className="border p-4" role="status" data-testid={testId}><h3 className="text-lg">{title}</h3><p className="mt-2">{children}</p></div>;
}

export function Drawer({ open, title, onClose, children }) {
  if (!open) return null;
  return <aside role="dialog" aria-modal="true" aria-label={title} className="fixed inset-y-0 right-0 z-50 w-[min(24rem,100vw)] overflow-auto border bg-linen p-4 text-obsidian"><h2>{title}</h2>{children}<button type="button" className="mt-4 min-h-11 underline" onClick={onClose}>Close drawer</button></aside>;
}

export function Popover({ label, children }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return <div><button type="button" className="min-h-11 underline" aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}>{label}</button>{open ? <div id={id} className="border p-3">{children}</div> : null}</div>;
}

export function Menu({ label, items }) {
  const [open, setOpen] = useState(false);
  return <div><button type="button" className="min-h-11 underline" aria-expanded={open} aria-haspopup="menu" onClick={() => setOpen(!open)}>{label}</button>{open ? <ul role="menu" className="border p-2">{items.map((item) => <li key={item} role="none"><button type="button" role="menuitem" className="min-h-11 w-full text-left" onClick={() => setOpen(false)}>{item}</button></li>)}</ul> : null}</div>;
}

export function Tooltip({ label, children }) {
  return <span className="inline-flex items-center gap-2"><span>{children}</span><span className="border px-2 text-xs">{label}</span></span>;
}

export function Metric({ label, value }) {
  return <p><span className="block text-sm">{label}</span><strong className="text-2xl">{value}</strong></p>;
}

export function DescriptionList({ items }) {
  return <dl className="grid gap-2">{items.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}</dl>;
}

export function Timeline({ items }) {
  return <ol className="grid gap-3">{items.map((item) => <li key={item.id} className="border p-3"><p>{item.actor} · {item.authority}</p><p>{item.event}</p><p>{item.timestamp}</p><p>{item.channel}</p><p>{item.change}</p></li>)}</ol>;
}

export function Avatar({ name }) {
  const initials = name.split(" ").map((part) => part[0]).join("").slice(0, 2);
  return <span className="inline-flex h-11 w-11 items-center justify-center border" aria-hidden="true">{initials}</span>;
}

export function RoleMarker({ role }) {
  return <span className="border px-2 py-1 text-xs">{role}</span>;
}

export function PlaceMarker({ kind, name }) {
  return <span className="border px-2 py-1 text-xs">{kind}: {name}</span>;
}

export function KeyValueComparison({ rows }) {
  return <table className="w-full"><caption className="sr-only">Comparison</caption><thead><tr><th scope="col">Field</th><th scope="col">Before</th><th scope="col">After</th></tr></thead><tbody>{rows.map((row) => <tr key={row.field}><th scope="row">{row.field}</th><td>{row.before}</td><td>{row.after}</td></tr>)}</tbody></table>;
}

export function PageHeader({ eyebrow, title, children }) {
  return <header className="grid gap-2"><p>{eyebrow}</p><h1 className="text-3xl">{title}</h1>{children}</header>;
}

export function Section({ title, children }) {
  return <section className="grid gap-3"><h2 className="text-2xl">{title}</h2>{children}</section>;
}

export function FilterBar({ children }) {
  return <div className="flex flex-wrap gap-2" role="search">{children}</div>;
}

export function StickyActionBar({ children }) {
  return <div className="sticky bottom-0 flex flex-wrap gap-2 border-t bg-linen p-3">{children}</div>;
}

export function ResponsiveImage({ name, alt, priority = false, width, height, className = "" }) {
  const base = `/media/${name}`;
  const high = priority === true;
  const eager = priority === true || priority === "eager";
  const defer = priority === "after-paint";
  const [active, setActive] = useState(!defer);
  useEffect(() => { if (defer) setActive(true); }, [defer]);
  if (!active) return <div className={`block overflow-hidden bg-obsidian ${className}`} role="img" aria-label={alt} />;
  return <picture className={`block overflow-hidden ${className}`}>
    <source type="image/avif" srcSet={`${base}.avif`} sizes="100vw" />
    <source type="image/webp" srcSet={`${base}.webp`} sizes="100vw" />
    <img src={`${base}.jpg`} alt={alt} width={width} height={height} sizes="100vw" loading={eager ? "eager" : "lazy"} fetchPriority={high ? "high" : "auto"} decoding="async" className="h-full max-h-full w-full max-w-full object-cover" />
  </picture>;
}

export const COMPONENT_MAP = {
  PublicHeader: "Navbar",
  PublicFooter: "Footer",
  PortalHeader: "PortalToolbar",
  Sidebar: "PerchPointPortal aside",
  MobileNavigation: "Navbar mobile navigation and portal sidebar",
  AccountMenu: "PortalToolbar account panel",
  NotificationCenter: "PortalToolbar notifications panel",
  ContextSwitcher: "portal-context-select",
  Link: "TextLink",
  Input: "TextInput",
  Label: "Field",
  DateTime: "OperationalTime",
  Dialog: "components/ui/dialog",
  AlertDialog: "DestructiveConfirm",
  ErrorBoundary: "AppErrorBoundary",
  Progress: "components/ui/progress",
  Card: "DecisionCard",
  ActivityItem: "Timeline item",
  UserRoleMarker: "RoleMarker",
  PropertyMarker: "PlaceMarker",
  BeforeAfterChange: "KeyValueComparison",
  PublicPage: "PublicLayout",
  PortalPage: "PerchPointPortal",
  OperationsPage: "leasing Operations Console",
  RecordPage: "portal record dialog",
  SplitPane: "portal sidebar plus section",
  DashboardGrid: "Dashboard sections in the portal queue",
  DetailSidebar: "portal record dialog",
  MobileRecordList: "DataTable mobile list",
  AddressPresentation: "Address",
  MoneyPresentation: "Money",
};

export const NOTIFICATION_EXAMPLE = {
  category: "Maintenance",
  priority: "High",
  read: false,
  record: "Example Elm Court condenser",
  timestamp: "2026-09-26T15:00:00Z",
  action: "Review the recommendation. No work is dispatched from this notice.",
  source: "Synthetic preview",
};
