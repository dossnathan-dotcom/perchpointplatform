"""Runtime and privileged connections. Application traffic uses the runtime role."""
from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from .settings import Settings


def engine_for(url: str) -> Engine:
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return create_engine(url, pool_pre_ping=True)


@contextmanager
def admin_connection(settings: Settings):
    engine = engine_for(settings.admin_url)
    with engine.connect() as connection:
        yield connection
        connection.commit()
    engine.dispose()


@contextmanager
def runtime_transaction(settings: Settings, actor_id: UUID | None, organization_id: UUID | None, request_id: UUID):
    engine = engine_for(settings.runtime_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            _set_context(connection, actor_id, organization_id, request_id)
            yield connection
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise
        finally:
            connection.close()
    engine.dispose()


def _set_context(connection: Connection, actor_id: UUID | None, organization_id: UUID | None, request_id: UUID) -> None:
    connection.execute(
        text(
            """
            SELECT set_config('app.actor_id', :actor, true),
                   set_config('app.organization_id', :organization, true),
                   set_config('app.request_id', :request, true)
            """
        ),
        {
            "actor": "" if actor_id is None else str(actor_id),
            "organization": "" if organization_id is None else str(organization_id),
            "request": str(request_id),
        },
    )
