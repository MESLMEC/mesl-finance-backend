"""`docs/openapi.json` is GENERATED from the app, never handwritten (roadmap step 6.8).

Approved brief this session (P-003 must be settled first, and it was): the questions were
answered by the generic approval, so the brief's labelled suggestions stand (same pattern
as D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093):
- Q1=a P-003 confirmed in its narrowed form: only the generated `docs/openapi.json`;
  no handwritten `docs/api-contract.md`, as ROADMAP 6.8 says.
- Q2=a CODE-WITH-TESTS with the three tests below; the check that the COMMITTED file
  still matches a fresh export is ROADMAP 12.2's job and is not written here.
- Q3=a the generator is `src/mesl_finance/export_openapi.py`, run as
  `PYTHONPATH=src uv run python -m mesl_finance.export_openapi`.
- Q4=a the generator builds documented schema-only placeholder settings and opens no
  database connection, so exporting needs neither a server nor the app's secrets.
- Q5=a the file is UTF-8 JSON with `indent=2`, `sort_keys=True` and exactly one trailing
  newline; `info.version` stays FastAPI's default "0.1.0" (no step defines an app version).

What these tests pin (the API /code must provide): a callable
`export_openapi(destination: pathlib.Path) -> None` in `mesl_finance.export_openapi` that
writes FastAPI's OWN document for `create_app(...)`:
- the parsed document equals the document the app factory produces, it is OpenAPI
  "3.1.0", its `info` is `{"title": "MESL Finance", "version": "0.1.0"}`, and its
  operations are exactly the ones the routes built so far define (the inventory below;
  an API step that adds a route must extend it);
- two runs produce byte-identical output, with `components` first and two-space
  indentation (what makes a future diff a real contract change);
- a destination whose parent directory does not exist is created, so `docs/` comes
  from the generator rather than from a manual `mkdir`.

Not tested here, on purpose: the generated document contains only what FastAPI knows
(the success responses plus its own 422 `HTTPValidationError`); the RFC 9457 problem-JSON
bodies (D-013, D-064) are not in it and no step authorises adding `responses=` metadata.

The module is imported lazily: ruff classifies an import of a module that does not exist
yet as third-party, so a module-level import would have to be re-sorted the moment /code
adds it (D-069), and each test then fails on its own ("module does not exist yet") instead
of the whole file failing to collect. No `db/examples` script covers this step.
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pydantic import SecretStr

from mesl_finance.main import create_app
from mesl_finance.shared.settings import Settings

TITLE = "MESL Finance"
VERSION = "0.1.0"
OPENAPI_VERSION = "3.1.0"

# The operations of the features built so far, in sorted order. Extend it with each API step.
EXPECTED_OPERATIONS: list[tuple[str, str]] = [
    ("GET", "/api/v1/allocation-context"),
    ("GET", "/api/v1/cost-centers"),
    ("GET", "/api/v1/dues"),
    ("GET", "/api/v1/entries"),
    ("GET", "/api/v1/envelopes"),
    ("GET", "/api/v1/fee-rates"),
    ("GET", "/api/v1/members"),
    ("GET", "/api/v1/members/{member_id}/adjustments"),
    ("GET", "/api/v1/members/{member_id}/periods"),
    ("GET", "/api/v1/shutdown-weeks"),
    ("POST", "/api/v1/allocation-suggestion"),
    ("POST", "/api/v1/allocations"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/cost-centers"),
    ("POST", "/api/v1/cost-centers/{cost_center_id}/rename"),
    ("POST", "/api/v1/cost-centers/{cost_center_id}/status"),
    ("POST", "/api/v1/deposits"),
    ("POST", "/api/v1/entries/{entry_id}/edit-labels"),
    ("POST", "/api/v1/entries/{entry_id}/fix-amount"),
    ("POST", "/api/v1/envelopes"),
    ("POST", "/api/v1/envelopes/{envelope_id}/deactivate"),
    ("POST", "/api/v1/envelopes/{envelope_id}/rename"),
    ("POST", "/api/v1/envelopes/{envelope_id}/settings"),
    ("POST", "/api/v1/expenses"),
    ("POST", "/api/v1/fee-rates"),
    ("POST", "/api/v1/members"),
    ("POST", "/api/v1/members/{member_id}/adjustments"),
    ("POST", "/api/v1/members/{member_id}/edit"),
    ("POST", "/api/v1/members/{member_id}/periods/end"),
    ("POST", "/api/v1/members/{member_id}/periods/start"),
    ("POST", "/api/v1/refunds"),
    ("POST", "/api/v1/shutdown-weeks"),
    ("POST", "/api/v1/transfers"),
]


def _exporter_module() -> ModuleType:
    try:
        return import_module("mesl_finance.export_openapi")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/export_openapi.py does not exist yet")


def _export_openapi() -> Any:
    return vars(_exporter_module())["export_openapi"]


def _schema_only_settings() -> Settings:
    """Settings good enough to construct the app: exporting never opens a connection."""
    return Settings(
        database_url="postgresql+asyncpg://labapp:change-me@localhost:5432/mesl",
        admin_database_url=SecretStr("postgresql://postgres:change-me@localhost:5432/mesl"),
        jwt_secret=SecretStr("schema-export-only-" + "x" * 20),
        auth_username="treasurer",
        auth_password_hash=SecretStr("$argon2id$v=19$m=8,t=1,p=1$c2FsdA$aGFzaA"),
        _env_file=None,  # pyright: ignore[reportCallIssue]
    )


def _operations(document: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (method.upper(), path)
        for path, operations in document["paths"].items()
        for method in operations
    ]


def test_export_writes_the_documents_fastapi_builds(tmp_path: Path) -> None:
    destination = tmp_path / "openapi.json"

    _export_openapi()(destination)

    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document == create_app(_schema_only_settings()).openapi()
    assert document["openapi"] == OPENAPI_VERSION
    assert document["info"] == {"title": TITLE, "version": VERSION}
    assert sorted(_operations(document)) == EXPECTED_OPERATIONS


def test_export_is_byte_stable(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    _export_openapi()(first)
    _export_openapi()(second)

    body = first.read_bytes()
    assert body == second.read_bytes()
    assert body.endswith(b"\n")
    assert not body.endswith(b"\n\n")
    assert body.splitlines()[1] == b'  "components": {'


def test_export_creates_the_destination_directory(tmp_path: Path) -> None:
    destination = tmp_path / "docs" / "openapi.json"

    _export_openapi()(destination)

    assert destination.is_file()
