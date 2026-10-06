"""Prove an empty-database migration reached the current Alembic head.

Phase 6 remains accepted at ``0031_phase6_authz_remediation``. Later additive
revisions are valid when that revision is still in the single linear ancestry
of the repository head. The proof is the Alembic revision graph, not a
substring of migration stdout.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE6_REVISION = "0031_phase6_authz_remediation"
CONFIRMED = "phase6_ancestry=confirmed"


class LineageError(Exception):
    pass


def assess(
    revisions: dict[str, str | tuple[str, ...] | list[str] | None],
    reached: str,
    required: str = PHASE6_REVISION,
) -> dict[str, str | int]:
    """Return the reached head and confirmed historical ancestry.

    ``revisions`` maps each revision id to its ``down_revision``. A tuple or
    list parent is an unexpected branch. More than one revision that nothing
    else points at is an unexpected multi-head graph.
    """
    if not revisions:
        raise LineageError("revision graph is empty")
    if not reached:
        raise LineageError("database revision is empty")
    referenced: set[str] = set()
    for revision, parent in revisions.items():
        if isinstance(parent, (tuple, list)):
            raise LineageError(f"unexpected branch at {revision}")
        if parent is None:
            continue
        if not isinstance(parent, str):
            raise LineageError(f"unexpected parent at {revision}")
        referenced.add(parent)
    heads = sorted(revision for revision in revisions if revision not in referenced)
    if len(heads) != 1:
        raise LineageError(f"expected exactly one head, found {heads}")
    head = heads[0]
    if reached != head:
        raise LineageError(f"database reached {reached}, repository head is {head}")
    lineage: list[str] = []
    seen: set[str] = set()
    current: str | None = head
    while current is not None:
        if current in seen:
            raise LineageError(f"revision cycle at {current}")
        if current not in revisions:
            raise LineageError(f"{current} is not in the revision graph")
        seen.add(current)
        lineage.append(current)
        parent = revisions[current]
        if isinstance(parent, (tuple, list)):
            raise LineageError(f"unexpected branch at {current}")
        current = parent
    if required not in seen:
        raise LineageError(f"{required} is absent from the lineage of {head}")
    return {
        "reached_head": reached,
        "current_head": head,
        "required_revision": required,
        "ancestry": "confirmed",
        "lineage_length": len(lineage),
    }


def load_repository_graph(root: Path = ROOT) -> dict[str, str | None]:
    """Load the repository's Alembic script graph without connecting to a database."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend = root / "backend"
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    script = ScriptDirectory.from_config(config)
    revisions: dict[str, str | None] = {}
    for revision in script.walk_revisions():
        parent = revision.down_revision
        if parent is not None and not isinstance(parent, str):
            raise LineageError(f"unexpected branch at {revision.revision}: {parent!r}")
        revisions[revision.revision] = parent
    return revisions


def read_database_revision(container: str, database: str) -> str:
    completed = subprocess.run(
        [
            "docker", "exec", container, "psql", "-v", "ON_ERROR_STOP=1",
            "-U", "postgres", "-d", database, "-At",
            "-c", "SELECT version_num FROM alembic_version;",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise LineageError(detail or "alembic_version query failed")
    rows = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(rows) != 1:
        raise LineageError(f"expected one alembic_version row, found {rows}")
    return rows[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", help="revision already read from the migrated database")
    parser.add_argument("--container", help="disposable Postgres container to query")
    parser.add_argument("--database", help="database name inside that container")
    args = parser.parse_args(argv)
    if bool(args.revision) == bool(args.container):
        parser.error("pass exactly one of --revision or --container")
    if args.container and not args.database:
        parser.error("--container requires --database")
    try:
        reached = args.revision or read_database_revision(args.container, args.database)
        result = assess(load_repository_graph(), reached)
    except LineageError as exc:
        print(f"phase6 lineage failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    print(CONFIRMED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
