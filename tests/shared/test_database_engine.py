"""Guard tests for the async engine (roadmap step 3.1).

The engine already exists (src/mesl_finance/shared/infrastructure/database.py, from the
pre-roadmap guide tree, D-023); the step brief approved it as TEST-ONLY: the behaviour
exists, so the tests are expected to pass at once, and the coverage proof is the
roadmap claim -> test table below (precedent D-033/D-045: no db/examples script covers
this step).

Coverage map of the ROADMAP 3.1 claims (one bullet per claim, step order):

- "labapp DSN":
    test_engine_connects_as_app_role -- current_user over the engine is labapp only.
- SQLAlchemy 2.x Core + asyncpg:
    test_engine_can_run_select -- SELECT 1 round-trips over the engine.
- Asia/Dhaka server setting (D-005; brief Q3=a):
    test_engine_sets_timezone_server_setting -- SHOW timezone == settings.timezone.
- "pool pre-ping":
    test_engine_uses_pool_pre_ping -- config-level: pool._pre_ping is True.
- "no ORM models for the ledger":
    test_no_orm_models_in_source -- zero ORM markers anywhere under src/.

Library APIs verified in the installed source this session (AGENTS.md section 3):
- sqlalchemy/engine/create.py:649-667 + sqlalchemy/pool/base.py:282: create_engine's
  pool_pre_ping kwarg is popped from the kwargs and handed to the Pool as pre_ping,
  stored as pool._pre_ping (so a config-level assert is the direct contract);
- sqlalchemy/ext/asyncio/engine.py:1251: AsyncEngine.pool is the public property
  reaching the pool;
- sqlalchemy/ext/asyncio/engine.py:705: AsyncConnection.scalar(statement) exists and
  returns Any;
- asyncpg/connect_utils.py:834-839: server_settings must be dict[str, str] - the
  engine's connect_args {"timezone": ...} is exactly that shape.
"""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.shared.infrastructure.database import create_engine
from mesl_finance.shared.settings import Settings

APP_ROLE = "labapp"  # db/schema.sql's limited login role; the app DSN must never run as owner
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
ORM_MARKERS = (
    "sqlalchemy.orm",
    "declarative_base",
    "declarative",
    "mapped_column",
    "InstrumentedAttribute",
)


@pytest_asyncio.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """The production engine over this test's database clone, built from real Settings."""
    eng = create_engine(settings)
    yield eng
    await eng.dispose()


async def test_engine_connects_as_app_role(engine: AsyncEngine) -> None:
    """Every connection the engine makes identifies as the limited app role, not the owner."""
    async with engine.connect() as connection:
        current_user = await connection.scalar(text("SELECT current_user"))
    assert current_user == APP_ROLE


async def test_engine_can_run_select(engine: AsyncEngine) -> None:
    """The engine runs real SQL end to end (Core + asyncpg, no other driver involved)."""
    async with engine.connect() as connection:
        one = await connection.scalar(text("SELECT 1"))
    assert one == 1


async def test_engine_sets_timezone_server_setting(engine: AsyncEngine, settings: Settings) -> None:
    """The engine pins the database time zone with asyncpg server_settings."""
    async with engine.connect() as connection:
        shown = await connection.scalar(text("SHOW timezone"))
    assert shown == settings.timezone == "Asia/Dhaka"


def test_engine_uses_pool_pre_ping(engine: AsyncEngine) -> None:
    """pool_pre_ping is switched on for the engine's pool (config-level, no DB access)."""
    assert engine.pool._pre_ping is True  # pyright: ignore[reportPrivateUsage]
    # Pool exposes pre-ping only as _pre_ping (sqlalchemy/pool/base.py:282; create.py:667).


def test_no_orm_models_in_source() -> None:
    """The codebase stays Core-only: no ORM classes or markers anywhere under src/."""
    hits: list[str] = []
    for path in sorted(SRC_DIR.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(marker in line for marker in ORM_MARKERS):
                hits.append(f"{path.relative_to(SRC_DIR)}:{lineno}: {line.strip()}")
    assert hits == []
