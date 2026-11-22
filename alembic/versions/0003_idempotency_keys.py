"""Schema 0003: the server-side idempotency key store (issue #4, slice 1).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-22

Executes db/sql/0003_idempotency_keys.sql in place as ONE hand-written
payload (D-036). The payload is the `idempotency_keys` table and its grants;
PostgreSQL owns the uniqueness so a retried write can never be recorded twice.
"""

from collections.abc import Sequence
from pathlib import Path

import asyncpg
from alembic import op
from sqlalchemy.util import await_

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# sha256 of db/sql/0003_idempotency_keys.sql at the time this revision was
# written. tests/test_payload_hash.py compares the file's current hash against
# this constant (the per-payload guard D-036 established at 0002).
PAYLOAD_SHA256: str = "6d19eb37bee62be36e5bcf7c581de32cceab9d0c1fc473734a2c214afe9e95a2"

_PAYLOAD_PATH = Path(__file__).resolve().parents[2] / "db" / "sql" / "0003_idempotency_keys.sql"


def _raw_connection() -> asyncpg.Connection:
    """The raw asyncpg connection Alembic owns.

    The payload must run whole on the raw connection (D-031); the adapter cursor
    path always prepares and cannot carry a multi-statement file.
    """
    return op.get_bind().connection.driver_connection


async def _execute_whole_file(raw: asyncpg.Connection) -> None:
    """Execute the payload whole inside the revision's own server-side transaction.

    Raw simple-protocol writes do NOT reliably join Alembic's per-migration
    transaction, so the revision must own one (D-030 probe C/D, confirmed D-031).
    """
    async with raw.transaction():
        await raw.execute(_PAYLOAD_PATH.read_text(encoding="utf-8"))


def upgrade() -> None:
    """Apply the hand-written 0003 payload in place (never copied)."""
    await_(_execute_whole_file(_raw_connection()))


def downgrade() -> None:
    """Reject downgrades: the migration chain is the append-only truth (D-018)."""
    raise NotImplementedError(
        "0003 has no downgrade; correct it with a new revision instead (D-018). "
        "Rebuild the database from scratch if needed."
    )
