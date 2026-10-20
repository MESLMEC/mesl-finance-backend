"""The first-start bootstrap as the OWNER (D-019; D-024 for the owner DSN).

    PYTHONPATH=src uv run python -m mesl_finance.bootstrap \
        --tenure-name "Tenure 2026-27" --opened-on YYYY-MM-DD

Idempotent on a database that already has an open tenure (skips, exits 0):

1. `alembic upgrade head` (alembic/env.py reads MESL_ADMIN_DATABASE_URL only, step 1.1).
2. ALTERs the password of the login role named in MESL_DATABASE_URL to that DSN's
   password (Q-005): ALTER ROLE takes a string constant, so PostgreSQL quotes the
   pair server-side with format(%I/%L); no value is formatted into SQL.
3. Opens the first tenure and creates exactly the pool envelope (Q-007). The other
   envelope names, caps and priorities are data the treasurer enters later (D-021).
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import date
from pathlib import Path

import asyncpg
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import make_url

from mesl_finance.shared.settings import Settings

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"
_ALEMBIC_SCRIPTS = _REPO_ROOT / "alembic"
_ALEMBIC_VERSIONS = _REPO_ROOT / "alembic" / "versions"
OWNER_DSN_ENV_VAR = "MESL_ADMIN_DATABASE_URL"  # the only source alembic/env.py accepts
POOL_ENVELOPE = "Unallocated General"

OPEN_TENURE = "SELECT id FROM tenures WHERE closed_on IS NULL"
POOL_EXISTS = "SELECT true FROM envelopes WHERE is_pool"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="first-start bootstrap: migrations, the app role's password, the first tenure"
    )
    parser.add_argument("--tenure-name", required=True, help="name of the first tenure")
    parser.add_argument("--opened-on", required=True, type=date.fromisoformat, metavar="YYYY-MM-DD")
    return parser


def _run_migrations(settings: Settings) -> None:
    """Point alembic/env.py at the owner DSN and upgrade to head (same pattern as conftest)."""
    os.environ[OWNER_DSN_ENV_VAR] = settings.admin_database_url.get_secret_value()
    config = Config(_ALEMBIC_INI)
    # alembic.ini records script_location and version_locations relative to the cwd;
    # the CLI must run from any cwd, so both are replaced by absolute paths here.
    config.set_main_option("script_location", str(_ALEMBIC_SCRIPTS))
    config.set_main_option("version_locations", str(_ALEMBIC_VERSIONS))
    alembic_command.upgrade(config, "head")


async def _set_role_password(admin: asyncpg.Connection, role: str, password: str) -> None:
    """ALTER ROLE ... PASSWORD ref a constant, so PostgreSQL does the quoting: %I/%L."""
    statement = await admin.fetchval(
        "SELECT format('ALTER ROLE %I PASSWORD %L', $1::text, $2::text)", role, password
    )
    if statement is None:  # unreachable: format() over two strings cannot yield NULL
        raise RuntimeError("server-side quoting of ALTER ROLE failed")
    await admin.execute(statement)


async def _first_tenure(admin: asyncpg.Connection, name: str, opened_on: date) -> None:
    """The first tenure plus the pool envelope, or a skip if one is already open."""
    if await admin.fetchval(OPEN_TENURE) is not None:
        print("An open tenure already exists; the first tenure is left untouched.")
        return
    async with admin.transaction():
        pool = await admin.fetchval(POOL_EXISTS)
        await admin.execute("INSERT INTO tenures(name, opened_on) VALUES ($1, $2)", name, opened_on)
        if pool is None:
            await admin.execute(
                "INSERT INTO envelopes(name, is_pool) VALUES ($1, true)", POOL_ENVELOPE
            )
    print(f"Tenure '{name}' opened on {opened_on.isoformat()}; pool envelope ensured.")


async def _set_up(settings: Settings, name: str, opened_on: date) -> None:
    url = make_url(settings.database_url)  # role and password come from the app DSN (Q-005)
    role, password = url.username, url.password
    if role is None or password is None:
        raise SystemExit(
            "MESL_DATABASE_URL must name the app login role and its password, "
            "as user:password in the DSN"
        )
    dsn = settings.admin_database_url.get_secret_value().replace("+asyncpg", "", 1)
    admin = await asyncpg.connect(dsn)
    try:
        await _set_role_password(admin, role, password)
        await _first_tenure(admin, name, opened_on)
    finally:
        await admin.close()


def main() -> None:
    """--help exits 0 before Settings validation; missing MESL_* fails in Settings()."""
    args = _parser().parse_args()
    settings = Settings()  # pyright: ignore[reportCallIssue]
    _run_migrations(settings)
    asyncio.run(_set_up(settings, args.tenure_name, args.opened_on))


if __name__ == "__main__":
    main()
