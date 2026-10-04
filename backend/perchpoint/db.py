"""Runtime and privileged connections. Application traffic uses the runtime role."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from .settings import Settings


@dataclass(frozen=True)
class AuthorityContext:
    actor_id: UUID
    identity_id: UUID | None
    organization_id: UUID
    membership_id: UUID | None
    assurance: str
    delegation_id: UUID | None = None


_authority_context: ContextVar[AuthorityContext | None] = ContextVar(
    "perchpoint_authority_context", default=None
)


def set_authority_context(context: AuthorityContext | None):
    return _authority_context.set(context)


def reset_authority_context(token) -> None:
    _authority_context.reset(token)


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
def runtime_transaction(
    settings: Settings,
    actor_id: UUID | None,
    organization_id: UUID | None,
    request_id: UUID,
    *,
    identity_id: UUID | None = None,
    membership_id: UUID | None = None,
    assurance: str | None = None,
    delegation_id: UUID | None = None,
):
    inherited = _authority_context.get()
    if inherited is not None and inherited.actor_id == actor_id and inherited.organization_id == organization_id:
        identity_id = identity_id or inherited.identity_id
        membership_id = membership_id or inherited.membership_id
        assurance = assurance or inherited.assurance
        delegation_id = delegation_id or inherited.delegation_id
    engine = engine_for(settings.runtime_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            _set_context(
                connection,
                actor_id,
                organization_id,
                request_id,
                identity_id=identity_id,
                membership_id=membership_id,
                assurance=assurance,
                delegation_id=delegation_id,
            )
            if actor_id is not None and organization_id is not None:
                resolved = connection.execute(
                    text(
                        """
                        SELECT * FROM perchpoint.resolve_authority_context(
                          :actor, :organization, :membership
                        )
                        """
                    ),
                    {
                        "actor": actor_id,
                        "organization": organization_id,
                        "membership": membership_id,
                    },
                ).mappings().first()
                if resolved is not None:
                    identity_id = identity_id or resolved["identity_id"]
                    membership_id = membership_id or resolved["membership_id"]
                _set_context(
                    connection,
                    actor_id,
                    organization_id,
                    request_id,
                    identity_id=identity_id,
                    membership_id=membership_id,
                    assurance=assurance,
                    delegation_id=delegation_id,
                )
            yield connection
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise
        finally:
            connection.close()
    engine.dispose()


def _set_context(
    connection: Connection,
    actor_id: UUID | None,
    organization_id: UUID | None,
    request_id: UUID,
    *,
    identity_id: UUID | None = None,
    membership_id: UUID | None = None,
    assurance: str | None = None,
    delegation_id: UUID | None = None,
) -> None:
    connection.execute(
        text(
            """
            SELECT set_config('app.actor_id', :actor, true),
                   set_config('app.identity_id', :identity, true),
                   set_config('app.organization_id', :organization, true),
                   set_config('app.membership_id', :membership, true),
                   set_config('app.request_id', :request, true),
                   set_config('app.aal', :assurance, true),
                   set_config('app.delegation_id', :delegation, true)
            """
        ),
        {
            "actor": "" if actor_id is None else str(actor_id),
            "identity": "" if identity_id is None else str(identity_id),
            "organization": "" if organization_id is None else str(organization_id),
            "membership": "" if membership_id is None else str(membership_id),
            "request": str(request_id),
            "assurance": assurance or "",
            "delegation": "" if delegation_id is None else str(delegation_id),
        },
    )
