"""Schema 0002: a purchase acquisition must name its ledger entry.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03

Executes db/sql/0002_asset_purchase_link.sql in place as ONE hand-written
payload (D-036). The payload is exactly one statement: the
`asset_purchase_needs_link` CHECK on asset_events. PostgreSQL owns the rule so
every writer is bound by it (direct SQL, the future Go backend), not only the
app (D-163, issue #11).
"""

from collections.abc import Sequence
from pathlib import Path

import asyncpg
from alembic import op
from sqlalchemy.util import await_

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# sha256 of db/sql/0002_asset_purchase_link.sql at the time this revision was
# written. tests/test_payload_hash.py compares the file's current hash against
# this constant (the per-payload guard D-036 deferred to the first real
# migration).
PAYLOAD_SHA256: str = "34935c5a25ce4fbe88d386821fd1f573745dd49497d9db267e573abda274606a"

_PAYLOAD_PATH = Path(__file__).resolve().parents[2] / "db" / "sql" / "0002_asset_purchase_link.sql"


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
    """Apply the hand-written 0002 payload in place (never copied)."""
    await_(_execute_whole_file(_raw_connection()))


def downgrade() -> None:
    """Reject downgrades: the migration chain is the append-only truth (D-018)."""
    raise NotImplementedError(
        "0002 has no downgrade; correct it with a new revision instead (D-018). "
        "Rebuild the database from scratch if needed."
    )
