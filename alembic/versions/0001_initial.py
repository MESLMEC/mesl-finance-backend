"""Initial schema: executes db/schema.sql in place.

Revision ID: 0001
Revises:
Create Date: 2026-10-20

"""

from collections.abc import Sequence
from pathlib import Path

import asyncpg
from alembic import op
from sqlalchemy.util import await_

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# sha256 of db/schema.sql at the time this revision was written. Step 1.5 adds the
# guard test comparing the file's current hash against this constant (roadmap 1.5).
SCHEMA_SHA256: str = "d4248697612e3b41e0b34d4c49293bccfa8f5b8d202dac52a5fd803f0f6c286f"

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def _raw_connection() -> asyncpg.Connection:
    """The raw asyncpg connection Alembic owns.

    The whole file cannot go through the adapter cursor path (it always prepares,
    and one prepared statement is one statement): raw access is required (D-031).
    """
    return op.get_bind().connection.driver_connection


async def _execute_whole_file(raw: asyncpg.Connection) -> None:
    """Execute the schema file whole inside the revision's own server-side transaction.

    The raw simple-protocol writes do NOT reliably join Alembic's per-migration
    transaction, so the revision must own one (D-030 probe C/D, confirmed as D-031).
    """
    async with raw.transaction():
        await raw.execute(_SCHEMA_PATH.read_text(encoding="utf-8"))


def upgrade() -> None:
    """Execute db/schema.sql in place (never copied) as the whole initial schema."""
    await_(_execute_whole_file(_raw_connection()))


def downgrade() -> None:
    """Reject downgrades: the initial schema is the hand-written truth (D-018)."""
    raise NotImplementedError(
        "0001 has no downgrade; db/schema.sql is the schema truth (D-018). "
        "Rebuild the database from scratch instead."
    )
