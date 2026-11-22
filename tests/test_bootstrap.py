"""Roadmap 1.7: the bootstrap CLI.

Black-box contract over the one documented command (approved in the step brief):

    PYTHONPATH=src python -m mesl_finance.bootstrap \
        --tenure-name <name> --opened-on YYYY-MM-DD

It must: run `alembic upgrade head` as the owner over the database named in
MESL_ADMIN_DATABASE_URL, set the password of the login role named in
MESL_DATABASE_URL to that DSN's password, read the rest of the config through
Settings, and open the first tenure. Re-running on a database that already has
an open tenure skips it and exits 0. The pool envelope (and nothing else) is
created. `--help` must exit 0 before any Settings validation.

Each test drives a FRESH EMPTY scratch database (created as the superuser from
TEST_ADMIN_DSN, the same source as tests/conftest.py): the bootstrap must work
from an empty database, so cloning the session template would prove nothing.
ALTER ROLE is cluster-wide, so the tests use a throwaway login role instead of
'labapp' (role and password both derived from the app DSN, as approved).
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlsplit

import asyncpg
import pytest
import pytest_asyncio
from asyncpg import Record
from asyncpg.exceptions import InvalidPasswordError

from tests.conftest import ADMIN_DSN, dsn_for

REPO_ROOT = Path(__file__).resolve().parents[1]
TENURE_NAME = "Boot Tenure"
OPENED_ON = "2031-03-02"
BOOT_ARGS = ("--tenure-name", TENURE_NAME, "--opened-on", OPENED_ON)
AppRole = tuple[str, str, str]  # role, old password, new password


@pytest_asyncio.fixture
async def fresh_db() -> AsyncIterator[str]:
    """An EMPTY scratch database (conftest's db clones the template; here it must not)."""
    name = f"mesl_boot_{uuid.uuid4().hex[:10]}"
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        yield name
    finally:
        await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await admin.close()


@pytest_asyncio.fixture
async def app_role() -> AsyncIterator[AppRole]:
    """A throwaway login role plus its old password; the new one comes from the DSN."""
    role = f"boot_role_{uuid.uuid4().hex[:8]}"
    old_password = "old-" + uuid.uuid4().hex
    new_password = "new-" + uuid.uuid4().hex
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        ddl = await admin.fetchval(
            "SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', $1::text, $2::text)",
            role,
            old_password,
        )
        assert ddl is not None  # quoting happens inside PostgreSQL; never interpolated
        await admin.execute(ddl)
        yield role, old_password, new_password
    finally:
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = $1", role
        )
        ddl = await admin.fetchval("SELECT format('DROP ROLE IF EXISTS %I', $1::text)", role)
        assert ddl is not None
        await admin.execute(ddl)
        await admin.close()


def _app_dsn(role: str, password: str, database: str) -> str:
    """The postgresql+asyncpg DSN the app role is given, matching Settings."""
    parts = urlsplit(ADMIN_DSN)
    host = parts.hostname or "localhost"
    port = parts.port or 5432
    return f"postgresql+asyncpg://{quote(role, '')}:{quote(password, '')}@{host}:{port}/{database}"


def _boot_env(
    database: str, role: str, new_password: str, *, with_admin: bool = True
) -> dict[str, str]:
    env = {
        "MESL_AUTH_PASSWORD_HASH": "$argon2id$stub-passes-settings-validation",
        "MESL_AUTH_USERNAME": "treasurer",
        "MESL_DATABASE_URL": _app_dsn(role, new_password, database),
        "MESL_JWT_SECRET": "z" * 32,
    }
    if with_admin:
        env["MESL_ADMIN_DATABASE_URL"] = dsn_for(database)
    return env


def _login_dsn(role: str, password: str, database: str) -> str:
    """The plain scheme asyncpg.connect requires; +asyncpg stays in the env-var value."""
    return _app_dsn(role, password, database).replace("+asyncpg", "", 1)


def _clean_env() -> dict[str, str]:
    """The ambient environment without any MESL_* (no local .env can leak either)."""
    return {key: value for key, value in os.environ.items() if not key.startswith("MESL_")}


def _bootstrap(
    tmp_path: Path, extra_env: dict[str, str], *args: str
) -> subprocess.CompletedProcess[str]:
    """Run the documented bootstrap command; cwd=tmp_path hides any repo-local .env."""
    env = _clean_env()
    env.update(extra_env)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "mesl_finance.bootstrap", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


async def _query(database: str, sql: str) -> list[Record]:
    conn = await asyncpg.connect(dsn_for(database))
    try:
        return await conn.fetch(sql)
    finally:
        await conn.close()


async def test_migrations_reach_head(fresh_db: str, app_role: AppRole, tmp_path: Path) -> None:
    role, _, new_password = app_role
    result = _bootstrap(tmp_path, _boot_env(fresh_db, role, new_password), *BOOT_ARGS)
    assert result.returncode == 0, result.stderr
    versions = await _query(fresh_db, "SELECT version_num FROM alembic_version")
    assert [row["version_num"] for row in versions] == ["0003"]


async def test_first_tenure_opened_with_passed_name_and_date(
    fresh_db: str, app_role: AppRole, tmp_path: Path
) -> None:
    role, _, new_password = app_role
    result = _bootstrap(tmp_path, _boot_env(fresh_db, role, new_password), *BOOT_ARGS)
    assert result.returncode == 0, result.stderr
    tenures = await _query(
        fresh_db, "SELECT id, name, opened_on, closed_on FROM tenures ORDER BY id"
    )
    assert len(tenures) == 1
    assert tenures[0]["name"] == TENURE_NAME
    assert tenures[0]["opened_on"] == date(2031, 3, 2)
    assert tenures[0]["closed_on"] is None


async def test_rerun_keeps_one_open_tenure(
    fresh_db: str, app_role: AppRole, tmp_path: Path
) -> None:
    role, _, new_password = app_role
    env = _boot_env(fresh_db, role, new_password)
    for _ in range(2):
        result = _bootstrap(tmp_path, env, *BOOT_ARGS)
        assert result.returncode == 0, result.stderr
    tenures = await _query(fresh_db, "SELECT id, name, closed_on FROM tenures ORDER BY id")
    assert [(row["name"], row["closed_on"]) for row in tenures] == [(TENURE_NAME, None)]


async def test_app_role_password_comes_from_the_app_dsn(
    fresh_db: str, app_role: AppRole, tmp_path: Path
) -> None:
    role, old_password, new_password = app_role
    result = _bootstrap(tmp_path, _boot_env(fresh_db, role, new_password), *BOOT_ARGS)
    assert result.returncode == 0, result.stderr
    conn = await asyncpg.connect(_login_dsn(role, new_password, fresh_db))
    try:
        assert await conn.fetchval("SELECT 1") == 1  # the new password from the DSN works
    finally:
        await conn.close()
    with pytest.raises(InvalidPasswordError):
        await asyncpg.connect(_login_dsn(role, old_password, fresh_db))


async def test_bootstrap_creates_the_pool_envelope_only(
    fresh_db: str, app_role: AppRole, tmp_path: Path
) -> None:
    role, _, new_password = app_role
    result = _bootstrap(tmp_path, _boot_env(fresh_db, role, new_password), *BOOT_ARGS)
    assert result.returncode == 0, result.stderr
    envelopes = await _query(fresh_db, "SELECT name, is_pool FROM envelopes ORDER BY id")
    assert [(row["name"], row["is_pool"]) for row in envelopes] == [("Unallocated General", True)]


async def test_missing_admin_dsn_fails_loud_without_touching_the_db(
    fresh_db: str, app_role: AppRole, tmp_path: Path
) -> None:
    role, _, new_password = app_role
    result = _bootstrap(
        tmp_path, _boot_env(fresh_db, role, new_password, with_admin=False), *BOOT_ARGS
    )
    assert result.returncode != 0, result.stdout
    assert "admin_database_url" in (result.stdout + result.stderr).lower()
    tables = await _query(
        fresh_db, "SELECT to_regclass('public.tenures') AS t, to_regclass('alembic_version') AS v"
    )
    assert tables[0]["t"] is None and tables[0]["v"] is None


def test_help_lists_the_tenure_options(tmp_path: Path) -> None:
    result = _bootstrap(tmp_path, {}, "--help")
    assert result.returncode == 0, result.stderr
    assert "--tenure-name" in result.stdout and "--opened-on" in result.stdout
