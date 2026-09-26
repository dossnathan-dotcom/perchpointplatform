import { useEffect, useId, useRef, useState } from "react";

export function SkipLink({ href = "#main" }) {
  return <a className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-linen focus:px-3 focus:py-2 focus:text-obsidian" href={href}>Skip to content</a>;
}

export function Button({ children, variant = "primary", type = "button", ...props }) {
  const styles = {
    primary: "bg-copper text-linen",
    secondary: "border border-current bg-transparent",
    tertiary: "underline",
    destructive: "bg-red-800 text-linen",
    icon: "portal-icon",
  };
  return <button type={type} className={`inline-flex min-h-11 items-center justify-center gap-2 px-4 py-2 text-sm ${styles[variant] || styles.primary}`} {...props}>{children}</button>;
}

export function TextLink({ href, children, external = false }) {
  return <a href={href} className="underline" {...(external ? { rel: "noreferrer", target: "_blank" } : {})}>{children}{external ? <span className="sr-only"> (opens in a new tab)</span> : null}</a>;
}

export function Field({ id, label, help, error, required = false, children }) {
  const helpId = help ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(" ") || undefined;
  return <div className="grid gap-1">
    <label htmlFor={id}>{label}{required ? <span> (required)</span> : null}</label>
    {help ? <p id={helpId}>{help}</p> : null}
    {children(describedBy)}
    {error ? <p id={errorId} role="alert">{error}</p> : null}
  </div>;
}

export function TextInput({ id, describedBy, ...props }) {
  return <input id={id} className="min-h-11 border px-3" aria-describedby={describedBy} {...props} />;
}

export function ErrorSummary({ errors = [] }) {
  if (errors.length === 0) return null;
  return <div role="alert" tabIndex={-1} className="border border-current p-4">
    <h2 className="text-lg">Correct the following</h2>
    <ul className="mt-2 list-disc pl-5">{errors.map((item) => <li key={item.id}><a href={`#${item.id}`}>{item.message}</a></li>)}</ul>
  </div>;
}

export function StatusBadge({ children, tone = "neutral" }) {
  return <span className="inline-flex items-center gap-2 border px-2 py-1 text-xs"><span aria-hidden="true">{tone === "danger" ? "!" : "•"}</span>{children}</span>;
}

export function Money({ minor = 0 }) {
  const formatted = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(minor / 100);
  return <data value={minor}>{formatted}</data>;
}

export function OperationalTime({ value }) {
  const formatted = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  return <time dateTime={value}>{formatted} ET</time>;
}

export function Address({ line1, unit, municipality, state, postal }) {
  const unitText = unit ? `, ${unit}` : "";
  return <address className="not-italic">{line1}{unitText}, {municipality}, {state} {postal}</address>;
}

export function EmptyState({ title, children }) {
  return <div className="border p-6" role="status"><h2 className="text-xl">{title}</h2><p className="mt-2">{children}</p></div>;
}

export function Alert({ title, children }) {
  return <div role="status" className="border-l-4 border-current p-4"><h2 className="text-lg">{title}</h2><p className="mt-2">{children}</p></div>;
}

export function DataTable({ caption, columns, rows }) {
  const [sort, setSort] = useState({ key: columns[0]?.key, direction: "asc" });
  const sorted = [...rows].sort((left, right) => {
    const result = String(left[sort.key] ?? "").localeCompare(String(right[sort.key] ?? ""));
    return sort.direction === "asc" ? result : -result;
  });
  return <div>
    <table className="hidden w-full border-collapse md:table">
      <caption className="sr-only">{caption}</caption>
      <thead><tr>{columns.map((column) => <th key={column.key} scope="col" aria-sort={sort.key === column.key ? (sort.direction === "asc" ? "ascending" : "descending") : "none"} className="border-b p-2 text-left"><button type="button" onClick={() => setSort({ key: column.key, direction: sort.key === column.key && sort.direction === "asc" ? "desc" : "asc" })}>{column.label}</button></th>)}</tr></thead>
      <tbody>{sorted.map((row) => <tr key={row.id}>{columns.map((column) => <td key={column.key} className="border-b p-2">{row[column.key]}</td>)}</tr>)}</tbody>
    </table>
    <ul className="grid gap-3 md:hidden" aria-label={caption}>{sorted.map((row) => <li key={row.id} className="border p-3"><p className="font-semibold">{row[columns[0].key]}</p>{columns.slice(1).map((column) => <p key={column.key}>{column.label}: {row[column.key]}</p>)}</li>)}</ul>
  </div>;
}

export function DecisionCard({ item }) {
  return <article className="border p-4" data-testid="owner-decision-card">
    <p className="text-xs">Synthetic owner decision · not an approval</p>
    <h3 className="mt-2 text-xl">{item.requested}</h3>
    <p className="mt-2">Why it reached Faruk: {item.why}</p>
    <p>Impact: {item.impact}</p>
    <p>Property: {item.property}</p>
    <p>Responsible manager: {item.manager}</p>
    <p>Recommendation: {item.recommendation}</p>
    <p>Deadline: {item.deadline}</p>
    <p>If no decision: {item.inaction}</p>
    <p>Delegation: {item.delegation}</p>
    <button type="button" disabled>Decision workflow unavailable</button>
  </article>;
}

export function MaintenanceRecommendation({ item }) {
  return <article className="border p-4" data-testid="maintenance-recommendation-card">
    <h2 className="text-xl">Worker recommendation</h2>
    <p>Recommended by {item.worker}</p>
    <p>{item.recommendation}</p>
    <p><OperationalTime value={item.at} /></p>
    <p>Evidence: {item.evidence}</p>
    <p>Urgency: {item.urgency}</p>
    <p>Delay consequence: {item.delay}</p>
    <h2 className="mt-4 text-xl">Management decision</h2>
    <p>{item.decision}</p>
    <p>Ordered item: {item.ordered}</p>
    <p>Variance: {item.variance}</p>
    <p>Final result: {item.result}</p>
  </article>;
}

export function ChartFrame({ title, conclusion, rows }) {
  return <figure className="border p-4">
    <figcaption><strong>{title}</strong><p>{conclusion}</p></figcaption>
    <table className="mt-3 w-full"><thead><tr><th scope="col">Label</th><th scope="col">Value</th></tr></thead><tbody>{rows.map((row) => <tr key={row.label}><td>{row.label}</td><td>{row.value}</td></tr>)}</tbody></table>
  </figure>;
}

export function OverlayDialog({ open, title, onClose, children }) {
  const titleId = useId();
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    ref.current?.focus();
    const onKey = (event) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, [open, onClose]);
  if (!open) return null;
  return <div role="dialog" aria-modal="true" aria-labelledby={titleId} ref={ref} tabIndex={-1} className="fixed inset-4 z-50 overflow-auto border bg-linen p-4 text-obsidian">
    <h2 id={titleId} className="text-2xl">{title}</h2>
    {children}
    <button type="button" className="mt-4 min-h-11 underline" onClick={onClose}>Close</button>
  </div>;
}

export function CommandPalette({ open, onClose }) {
  return <OverlayDialog open={open} title="Search" onClose={onClose}>
    <p>Canonical search is unavailable until Phase 5. This palette does not query records.</p>
  </OverlayDialog>;
}

export const SAMPLE_DECISION = {
  requested: "Replace the Elm Court rooftop condenser",
  why: "The repair exceeds the delegated maintenance threshold.",
  impact: "$4,800 estimate · occupied duplex · heat risk",
  property: "Example Elm Court",
  manager: "Ann Springer",
  recommendation: "Approve the quoted replacement.",
  deadline: "Friday, operational close",
  inaction: "The occupied home can lose cooling.",
  delegation: "Not delegated. No approval was recorded.",
};

export const SAMPLE_RECOMMENDATION = {
  worker: "Alex Nguyen, maintenance",
  recommendation: "Replace the condenser. Do not recharge the failed unit again.",
  at: "2026-09-26T15:00:00Z",
  evidence: "Synthetic photo reference. No file was uploaded.",
  urgency: "High for occupied cooling",
  delay: "Another recharge would not restore reliable cooling.",
  decision: "No management decision has been recorded.",
  ordered: "Nothing has been ordered.",
  variance: "Not applicable until a decision exists.",
  result: "Work is not complete.",
};
