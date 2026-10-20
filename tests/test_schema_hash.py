"""Roadmap 1.5: db/schema.sql must still match revision 0001's recorded sha256.

Revision 0001 executes db/schema.sql in place and records the file's sha256
(D-018, D-031). If the schema file ever legitimately changes, that constant in
`alembic/versions/0001_initial.py` must be updated too; this guard test catches a
silent divergence between the two.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Protocol, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = REPO_ROOT / "db" / "schema.sql"
REVISION_FILE = REPO_ROOT / "alembic" / "versions" / "0001_initial.py"


class RevisionModule(Protocol):
    """The attribute of the revision module this guard depends on."""

    SCHEMA_SHA256: str


def _load_revision() -> RevisionModule:
    """Load the revision module by path (its name is not a valid identifier)."""
    spec = importlib.util.spec_from_file_location("mesl_revision_0001", REVISION_FILE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(RevisionModule, module)


def test_schema_hash_matches_0001() -> None:
    recorded = _load_revision().SCHEMA_SHA256
    assert isinstance(recorded, str)
    assert hashlib.sha256(SCHEMA_FILE.read_bytes()).hexdigest() == recorded
