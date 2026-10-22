"""The generated API contract: `docs/openapi.json` (roadmap step 6.8, P-003 narrowed).

    PYTHONPATH=src uv run python -m mesl_finance.export_openapi

Writes the document FastAPI builds for `create_app()` - one snapshot of every route the
app mounts today - to `<repo>/docs/openapi.json`. There is no handwritten contract: the
file is a dump of the app's own schema, so it cannot disagree with the routes. It is
UTF-8 with sorted keys and two-space indentation, so a diff means a real contract change.

The app is built from documented SCHEMA-ONLY placeholder settings: the document depends
only on routes and models, and exporting never opens a database connection. That keeps
the artifact reproducible without a server and without the app's secrets.
ROADMAP 12.2 adds the test that the committed file still matches the running app.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import SecretStr

from mesl_finance.main import create_app
from mesl_finance.shared.settings import Settings

DESTINATION = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


def _schema_only_settings() -> Settings:
    """Placeholders that satisfy `Settings`; nothing here is ever used to connect."""
    return Settings(
        database_url="postgresql+asyncpg://labapp:change-me@localhost:5432/mesl",
        admin_database_url=SecretStr("postgresql://postgres:change-me@localhost:5432/mesl"),
        jwt_secret=SecretStr("schema-export-only-" + "x" * 20),
        auth_username="treasurer",
        auth_password_hash=SecretStr("$argon2id$v=19$m=8,t=1,p=1$c2FsdA$aGFzaA"),
        _env_file=None,  # pyright: ignore[reportCallIssue]
    )


def export_openapi(destination: Path) -> None:
    """Write the app's OpenAPI document to `destination`, creating its parents."""
    document = create_app(_schema_only_settings()).openapi()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    export_openapi(DESTINATION)
