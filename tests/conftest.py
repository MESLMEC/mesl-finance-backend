"""Real-PostgreSQL test harness.

The ledger depends on triggers that fire at COMMIT, so tests run against a real database.
A template database is built ONCE per test session by the Alembic chain (revision 0001
executes db/schema.sql); every test gets its own fast clone of it
(CREATE DATABASE ... TEMPLATE) and drops it afterwards.

Needs a PostgreSQL superuser DSN (the schema creates roles/extensions and the tamper tests
disable triggers). Point TEST_ADMIN_DSN at your dev server, e.g. the Docker one:
    export TEST_ADMIN_DSN=postgresql://postgres:<password>@localhost:5432/postgres
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest
import pytest_asyncio
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from mesl_finance.main import create_app
from mesl_finance.shared.settings import Settings

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN", "postgresql://postgres:postgres@localhost:5432/postgres"
)
APP_ROLE_PASSWORD = "change-me"  # must match the labapp role created by db/schema.sql
ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"
OWNER_DSN_ENV_VAR = "MESL_ADMIN_DATABASE_URL"  # the only source alembic/env.py accepts
TEMPLATE_DB = "mesl_test_template"
TIMEZONE = "Asia/Dhaka"


def dsn_for(database: str, user: str | None = None, password: str | None = None) -> str:
    """The admin DSN pointed at another database, optionally as another login."""
    parts = urlsplit(ADMIN_DSN)
    host = parts.hostname or "localhost"
    port = f":{parts.port}" if parts.port else ""
    if user:
        creds = f"{user}:{password}@"
    elif parts.username:
        creds = f"{parts.username}:{parts.password}@"
    else:
        creds = ""
    return urlunsplit((parts.scheme, f"{creds}{host}{port}", f"/{database}", "", ""))


def _build_template() -> None:
    """Create the template database and stamp it with the real Alembic chain."""

    async def recreate() -> None:
        admin = await asyncpg.connect(ADMIN_DSN)
        try:
            await admin.execute(f'DROP DATABASE IF EXISTS "{TEMPLATE_DB}" WITH (FORCE)')
            await admin.execute(f'CREATE DATABASE "{TEMPLATE_DB}"')
        finally:
            await admin.close()

    asyncio.run(recreate())
    # alembic/env.py reads the owner DSN from this env var only (step 1.1); point it at
    # the template database for the upgrade, then restore whatever was there before.
    previous = os.environ.get(OWNER_DSN_ENV_VAR)
    os.environ[OWNER_DSN_ENV_VAR] = dsn_for(TEMPLATE_DB)
    try:
        alembic_command.upgrade(AlembicConfig(ALEMBIC_INI), "head")
    finally:
        if previous is None:
            os.environ.pop(OWNER_DSN_ENV_VAR, None)
        else:
            os.environ[OWNER_DSN_ENV_VAR] = previous


@pytest.fixture(scope="session", autouse=True)
def template_database() -> None:
    _build_template()


@dataclass
class TestDb:
    __test__ = False  # not a pytest test class

    name: str
    owner: asyncpg.Connection  # superuser: first tenure, tamper tests
    app: asyncpg.Connection  # the limited 'labapp' login, exactly what the web app will use
    app_dsn: str


@pytest_asyncio.fixture
async def db() -> AsyncIterator[TestDb]:
    name = f"mesl_test_{uuid.uuid4().hex[:12]}"
    admin = await asyncpg.connect(ADMIN_DSN)
    await admin.execute(f'CREATE DATABASE "{name}" TEMPLATE "{TEMPLATE_DB}"')
    await admin.execute(f"ALTER DATABASE \"{name}\" SET timezone = '{TIMEZONE}'")
    app_dsn = dsn_for(name, "labapp", APP_ROLE_PASSWORD)
    owner = await asyncpg.connect(dsn_for(name))
    app = await asyncpg.connect(app_dsn)
    try:
        yield TestDb(name=name, owner=owner, app=app, app_dsn=app_dsn)
    finally:
        await app.close()
        await owner.close()
        await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await admin.close()


@pytest_asyncio.fixture
async def lab(db: TestDb) -> TestDb:
    """Tenure 1 opened by the owner; envelopes made by the app role (pool=1, events=2, admin=3)."""
    await db.owner.execute("INSERT INTO tenures(name, opened_on) VALUES ('2026', '2026-01-01')")
    await db.app.execute(
        "INSERT INTO envelopes(name, is_pool) VALUES ('Unallocated General', true)"
    )
    await db.app.execute(
        "INSERT INTO envelopes(name) VALUES ('Events and Workshops'), ('Admin and Misc')"
    )
    return db


# ---- application-level fixtures: the real FastAPI app on top of the real test database ----

USERNAME = "treasurer"
PASSWORD = "correct horse battery staple"
JWT_SECRET = "test-secret-" + "x" * 32


@pytest.fixture
def settings(db: TestDb) -> Settings:
    low_cost_hasher = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)  # fast for tests
    return Settings(
        database_url=db.app_dsn.replace("postgresql://", "postgresql+asyncpg://", 1),
        jwt_secret=SecretStr(JWT_SECRET),
        auth_username=USERNAME,
        auth_password_hash=SecretStr(low_cost_hasher.hash(PASSWORD)),
        admin_database_url=SecretStr(ADMIN_DSN),
        _env_file=None,  # pyright: ignore[reportCallIssue]
    )


@pytest_asyncio.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    await app.state.engine.dispose()


@pytest_asyncio.fixture
async def auth(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
