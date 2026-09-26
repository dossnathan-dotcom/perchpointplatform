"""Generate versioned artifacts from executable contracts: python -m foundation.export [--check]."""
import csv
import inspect
import io
import json
import sys
from pathlib import Path

from . import (
    base,
    delegation,
    governance,
    integrations,
    migration,
    people,
    permissions,
    property,
    reference,
    workflows,
)
from .catalog import foundation_bundle, migration_fixture
from .seeds import portfolio, reference_slice

ROOT = Path(__file__).resolve().parents[2]


def artifacts():
    bundle = foundation_bundle()
    schemas = {}
    for module in [base, property, people, permissions, delegation, integrations, workflows, governance, migration, reference]:
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, base.Contract) and cls.__module__ == module.__name__:
                schemas[name] = cls.model_json_schema()
    def json_text(value):
        return json.dumps(value, indent=2, sort_keys=True)+"\n"
    output = {ROOT / "contracts/generated/schema-index.json": json_text({"version":"0.1.0", "schemas":list(schemas)}), ROOT / "frontend/src/data/generated/foundation.json": json_text(bundle), ROOT / "contracts/fixtures/portfolio.json": json_text(bundle["portfolio"]), ROOT / "contracts/fixtures/people.json": json_text(bundle["people"]), ROOT / "contracts/fixtures/migration-report.json":json_text(bundle["migration"]), ROOT / "contracts/fixtures/reference-slice.json": json_text(reference_slice().model_dump(mode="json")), ROOT / "contracts/fixtures/synthetic-innago.csv":migration_fixture(portfolio()), ROOT / "contracts/fixtures/import-template.csv":",".join(migration.CSV_COLUMNS)+"\n"}
    for name, schema in schemas.items():
        output[ROOT / f"contracts/generated/{name}.schema.json"] = json_text(schema)
    matrix = bundle["permissions"]
    stream = io.StringIO()
    fields = list(matrix["allow_rules"][0]) + ["effect", "version"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    grants = {(r["role"],r["resource"],r["action"]):r for r in matrix["allow_rules"]}
    for role in matrix["roles"]:
        for resource in matrix["resources"]:
            for action in matrix["actions"]:
                grant = grants.get((role,resource,action))
                writer.writerow({**(grant or {"role":role,"resource":resource,"action":action}),"effect":"conditional_allow" if grant else "deny","version":matrix["version"]})
    output[ROOT / "contracts/generated/permission-matrix.csv"] = stream.getvalue()
    return output


def main():
    check = "--check" in sys.argv
    mismatches = []
    output = artifacts()
    for path, text in output.items():
        if check:
            if not path.exists() or path.read_text() != text:
                mismatches.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    if mismatches:
        raise SystemExit("Stale artifacts: " + ", ".join(mismatches))
    print(f"{'Verified' if check else 'Generated'} {len(output)} deterministic artifacts; no database writes.")


if __name__ == "__main__":
    main()