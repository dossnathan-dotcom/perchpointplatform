import { useState } from "react";
import { Alert, Button, ChartFrame, CommandPalette, DataTable, DecisionCard, EmptyState, ErrorSummary, Field, MaintenanceRecommendation, Money, OperationalTime, SAMPLE_DECISION, SAMPLE_RECOMMENDATION, StatusBadge, TextInput } from "./components";
import { STATE_CATALOGUE } from "./states";

const columns = [
  { key: "property", label: "Property" },
  { key: "status", label: "Status" },
  { key: "owner", label: "Waiting on" },
];
const rows = [
  { id: "elm", property: "Example Elm Court", status: "Synthetic vacancy", owner: "Ann Springer" },
  { id: "oak", property: "Example Oak Mixed Use", status: "Commercial shell", owner: "Leasing" },
];

export default function Laboratory() {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState("light");
  const [density, setDensity] = useState("comfortable");
  return <main id="main" className="min-h-screen bg-linen p-4 text-obsidian" data-theme={theme} data-density={density} data-testid="component-laboratory">
    <h1 className="font-heading text-4xl">Component laboratory</h1>
    <p className="mt-2 max-w-3xl">Local and CI only. These examples are synthetic Greater Cincinnati residential, duplex, and mixed-use records. Nothing here writes an application, payment, lease, or work order.</p>
    <div className="mt-4 flex flex-wrap gap-3">
      <label>Theme<select className="ml-2 min-h-11 border px-2" value={theme} onChange={(event) => setTheme(event.target.value)}><option value="light">Light</option><option value="dark">Dark</option></select></label>
      <label>Density<select className="ml-2 min-h-11 border px-2" value={density} onChange={(event) => setDensity(event.target.value)}><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></label>
    </div>
    <section className="mt-8 grid gap-4">
      <h2 className="text-2xl">Actions and status</h2>
      <Button>Primary action</Button>
      <StatusBadge tone="danger">Exception</StatusBadge>
      <Money minor={148000} />
      <OperationalTime value="2026-09-26T15:00:00Z" />
      <Alert title="Synthetic preview">Providers are disconnected.</Alert>
      <EmptyState title="No live inventory">Published listings appear here only when the reference service returns them.</EmptyState>
      <ErrorSummary errors={[{ id: "lab-name", message: "Enter a name." }]} />
      <Field id="lab-name" label="Name" required help="Used only in this laboratory." error="">
        {(describedBy) => <TextInput id="lab-name" describedBy={describedBy} autoComplete="name" />}
      </Field>
    </section>
    <section className="mt-8">
      <h2 className="text-2xl">Table, decision, and recommendation</h2>
      <DataTable caption="Synthetic property list" columns={columns} rows={rows} />
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <DecisionCard item={SAMPLE_DECISION} />
        <MaintenanceRecommendation item={SAMPLE_RECOMMENDATION} />
      </div>
      <ChartFrame title="Synthetic vacancy" conclusion="One of two example properties is vacant. This is not a portfolio forecast." rows={[{ label: "Vacant", value: "1" }, { label: "Occupied", value: "1" }]} />
    </section>
    <section className="mt-8">
      <h2 className="text-2xl">States</h2>
      <ul className="grid gap-3">{STATE_CATALOGUE.map((item) => <li key={item.id} className="border p-3"><h3>{item.id}</h3><p>{item.happened}</p><p>Saved: {item.saved}</p><p>{item.next}</p></li>)}</ul>
    </section>
    <Button onClick={() => setOpen(true)}>Open command palette</Button>
    <CommandPalette open={open} onClose={() => setOpen(false)} />
  </main>;
}
