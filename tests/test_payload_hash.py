"""Issue #11: every hand-written migration payload must still match its revision's sha256.

Revision 0001 executes `db/schema.sql` in place and records the file's sha256
(D-018, D-031); `tests/test_schema_hash.py` guards that. From migration 0002
onwards every schema change is ONE hand-written payload `db/sql/NNN_<slug>.sql`
plus ONE thin revision `alembic/versions/NNN_<slug>.py` (D-036), and the
per-payload sha256 guard D-036 deferred to the first real migration rides here.

The revision records the payload's sha256 as `PAYLOAD_SHA256`. If the payload
file ever legitimately changes, that constant in the revision must be updated
too; this guard test catches a silent divergence between the two - the same
protection `tests/test_schema_hash.py` gives `db/schema.sql`.

The payload is executed whole by its revision, so a drift between the two files
means the database would receive something other than what the revision claims
to apply.

The table below is the list of hand-written payloads; every migration added
afterwards must get a row (the same tripwire idea as the alembic head in
`tests/db/test_template_alembic.py`).
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Protocol, cast

REPO_ROOT = Path(__file__).resolve().parents[1]

# (revision id, payload slug) of every hand-written migration payload.
PAYLOADS: list[tuple[str, str]] = [
    ("0002", "0002_asset_purchase_link"),
    ("0003", "0003_idempotency_keys"),
]


class RevisionModule(Protocol):
    """The attribute of the revision module this guard depends on."""

    PAYLOAD_SHA256: str


def _load_revision(revision: str, slug: str) -> RevisionModule:
    """Load the revision module by path (its name is not a valid identifier)."""
    path = REPO_ROOT / "alembic" / "versions" / f"{slug}.py"
    spec = importlib.util.spec_from_file_location(f"mesl_revision_{revision}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(RevisionModule, module)


def test_payload_hash_matches_0002() -> None:
    revision, slug = PAYLOADS[0]
    recorded = _load_revision(revision, slug).PAYLOAD_SHA256
    assert isinstance(recorded, str)
    payload = REPO_ROOT / "db" / "sql" / f"{slug}.sql"
    assert hashlib.sha256(payload.read_bytes()).hexdigest() == recorded


def test_payload_hash_matches_0003() -> None:
    """The idempotency-keys payload (issue #4) is guarded like the first one."""
    revision, slug = PAYLOADS[1]
    recorded = _load_revision(revision, slug).PAYLOAD_SHA256
    assert isinstance(recorded, str)
    payload = REPO_ROOT / "db" / "sql" / f"{slug}.sql"
    assert hashlib.sha256(payload.read_bytes()).hexdigest() == recorded


def test_every_hand_written_payload_is_guarded() -> None:
    """A new payload without a guard row would ship unguarded; this fails."""
    on_disk = sorted(p.stem for p in (REPO_ROOT / "db" / "sql").glob("*.sql"))
    guarded = sorted(slug for _revision, slug in PAYLOADS)

    assert on_disk == guarded
