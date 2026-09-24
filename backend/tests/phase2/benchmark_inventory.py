"""Measure a 1,000-property list on the disposable empty database, then remove those rows."""
import statistics
import time
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()
from foundation.seeds import sid
from perchpoint.db import engine_for
from perchpoint.settings import Settings


def main():
    settings = Settings.load()
    admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    runtime = engine_for(settings.runtime_url)
    org = sid("organization-demo")
    actor = sid("account-phase2-ann")
    with admin.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO properties (organization_id, id, name, property_type)
                SELECT :org, gen_random_uuid(), 'Bench ' || g, 'multifamily'
                FROM generate_series(1, 1000) AS g
                """
            ),
            {"org": org},
        )
    samples = []
    rows = []
    try:
        with runtime.connect() as connection:
            for _ in range(21):
                started = time.perf_counter()
                transaction = connection.begin()
                connection.execute(
                    text("SELECT set_config('app.actor_id', :actor, true), set_config('app.organization_id', :org, true), set_config('app.request_id', :request, true)"),
                    {"actor": str(actor), "org": str(org), "request": str(uuid4())},
                )
                rows = connection.execute(text("SELECT id, name FROM properties WHERE name LIKE 'Bench %' ORDER BY id LIMIT 50")).all()
                transaction.rollback()
                samples.append((time.perf_counter() - started) * 1000)
    finally:
        with admin.begin() as connection:
            connection.execute(text("DELETE FROM properties WHERE name LIKE 'Bench %'"))
            remaining = connection.execute(text("SELECT count(*) FROM properties WHERE name LIKE 'Bench %'")).scalar()
    admin.dispose()
    runtime.dispose()
    ordered = sorted(samples[1:])
    print(
        f"dataset_properties 1000 returned {len(rows)} warmup 1 measured {len(ordered)} "
        f"p50_ms {statistics.median(ordered):.2f} p95_ms {ordered[max(int(len(ordered) * 0.95) - 1, 0)]:.2f} max_ms {max(ordered):.2f} leftover {remaining}"
    )


if __name__ == "__main__":
    main()
