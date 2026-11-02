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
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Protocol, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_FILE = REPO_ROOT / "db" / "sql" / "0002_asset_purchase_link.sql"
REVISION_FILE = REPO_ROOT / "alembic" / "versions" / "0002_asset_purchase_link.py"


class RevisionModule(Protocol):
    """The attribute of the revision module this guard depends on."""

    PAYLOAD_SHA256: str


def _load_revision() -> RevisionModule:
    """Load the revision module by path (its name is not a valid identifier)."""
    spec = importlib.util.spec_from_file_location("mesl_revision_0002", REVISION_FILE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(RevisionModule, module)


def test_payload_hash_matches_0002() -> None:
    recorded = _load_revision().PAYLOAD_SHA256
    assert isinstance(recorded, str)
    assert hashlib.sha256(PAYLOAD_FILE.read_bytes()).hexdigest() == recorded
