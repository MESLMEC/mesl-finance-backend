"""Guard tests for the shared unit of work (roadmap step 3.2).

The transaction-scoped unit of work already exists
(src/mesl_finance/shared/infrastructure/database.py::SqlUnitOfWork, from the
pre-roadmap guide tree, D-023). Per the approved brief the step is TEST-ONLY,
so the tests are expected to PASS at once, and the coverage proof is the
roadmap claim -> test table below (precedent D-033/D-045/D-053: no
db/examples script covers this step).

Approved brief answers: naming stays `SqlUnitOfWork` (brief Q1=b, resolving
D-052; ROADMAP 3.2's `SqlAlchemyUnitOfWork` wording is amended at wrapup);
error mapping is OUT of this step's scope and is pinned by step 3.3 (Q3=a).

Coverage map of the ROADMAP 3.2 claims (one bullet per claim, step order):

- "one transaction per use case":
    test_uow_writes_visible_inside_scope_only_before_commit -- a write done
    in the scope is visible to the same UoW connection before commit() and
    to nobody else; it appears to a second connection only after commit;
    test_uow_rollback_discards_writes -- leaving the scope by exception
    rolls the transaction back (the write is gone);
    test_uow_commit_persists_writes -- commit() followed by scope exit keeps
    the write.
- "sets app.actor with set_config inside it":
    test_uow_sets_actor_transaction_local -- current_setting('app.actor')
    inside the scope equals the actor the UoW was constructed with;
    test_uow_actor_not_leaked_outside_transaction -- on a brand-new pool
    after engine.dispose() the setting is gone: set_config(..., true) is
    transaction-local (AGENTS.md section 5), so it cannot leak session-wide.
- Shape (brief test 1): the concrete class satisfies the shared
  `shared/ports.UnitOfWork` protocol added in step 2.2 (D-051).

Library APIs verified in the installed source this session (AGENTS.md
section 3):
- sqlalchemy/ext/asyncio/engine.py:629: AsyncConnection.execute(statement,
  parameters-dict) accepts a dict of bound parameters;
- sqlalchemy/ext/asyncio/engine.py:338: AsyncConnection.begin() returns an
  AsyncTransaction; engine.py:1395/1411/1415: it exposes is_active,
  rollback() and commit();
- buffered-result usage `(await ...).scalar_one()` is the repository's own
  established pattern (repository.py:11, 37) and is SQLAlchemy's documented
  buffered CursorResult path behind AsyncConnection.execute
  (engine.py:649-651, _ensure_sync_result);
- sqlalchemy/ext/asyncio/engine.py:1090/1145: AsyncEngine.connect()/dispose()
  for the out-of-scope witness engine;
- typing.runtime_checkable (installed stdlib source): isinstance() against
  the step-2.2 Protocol checks its members structurally;
- SQL names `set_config` / `current_setting('app.actor', true)`: the schema
  itself uses the same spelling (db/schema.sql:379, 780) and so does
  AGENTS.md section 5; every test runs against a real clone (per-test
  database, tests/conftest.py), which is the final check.

Isolation: probe envelopes use fixed names but every test runs on its own
cloned database (tests/conftest.py), so committed probes never cross tests;
the rollback test cleans up after itself by construction.
"""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.shared.infrastructure.database import SqlUnitOfWork, create_engine
from mesl_finance.shared.ports import UnitOfWork
from mesl_finance.shared.settings import Settings

PROBE_ROLLBACK = "UoW Probe Rollback"
PROBE_COMMIT = "UoW Probe Commit"
ACTOR = "treasurer-test"
PROBE_INSERT = "INSERT INTO envelopes (name) VALUES (:name)"
COUNT_SQL = "SELECT count(*) FROM envelopes WHERE name = :name"
# envelopes is an app table labapp may INSERT/UPDATE freely (schema.sql:1195).


@pytest_asyncio.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """The production engine over this test's database clone, as in 3.1's tests."""
    eng = create_engine(settings)
    yield eng
    await eng.dispose()


async def test_uow_satisfies_shared_unit_of_work_protocol(engine: AsyncEngine) -> None:
    """The concrete UoW structurally fulfils the shared UnitOfWork protocol."""
    assert isinstance(SqlUnitOfWork(engine, ACTOR), UnitOfWork)


async def test_uow_sets_actor_transaction_local(engine: AsyncEngine) -> None:
    """Inside the scope the transaction-local `app.actor` is the UoW's actor."""
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        shown = (await uow.execute("SELECT current_setting('app.actor')")).scalar_one()
    assert shown == ACTOR


async def test_uow_actor_not_leaked_outside_transaction(
    engine: AsyncEngine, settings: Settings
) -> None:
    """`set_config(..., true)` is transaction-local: nothing survives scope exit."""
    async with SqlUnitOfWork(engine, ACTOR):
        pass
    await engine.dispose()  # proof on a brand-new pool, never a reused connection
    fresh_engine = create_engine(settings)
    try:
        async with fresh_engine.connect() as connection:
            leaked = await connection.scalar(text("SELECT current_setting('app.actor', true)"))
        assert leaked is None
    finally:
        await fresh_engine.dispose()


async def test_uow_rollback_discards_writes(engine: AsyncEngine) -> None:
    """Leaving the scope by exception rolls the transaction back."""
    with pytest.raises(RuntimeError, match="scope failed"):
        async with SqlUnitOfWork(engine, ACTOR) as uow:
            await uow.execute(PROBE_INSERT, {"name": PROBE_ROLLBACK})
            raise RuntimeError("scope failed")
    async with engine.connect() as connection:
        count = await connection.scalar(text(COUNT_SQL), {"name": PROBE_ROLLBACK})
    assert count == 0


async def test_uow_commit_persists_writes(engine: AsyncEngine) -> None:
    """A committed write survives the scope."""
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        await uow.execute(PROBE_INSERT, {"name": PROBE_COMMIT})
        await uow.commit()
    async with engine.connect() as connection:
        count = await connection.scalar(text(COUNT_SQL), {"name": PROBE_COMMIT})
    assert count == 1


async def test_uow_writes_visible_inside_scope_only_before_commit(engine: AsyncEngine) -> None:
    """One transaction per use case: invisible to others until commit()."""
    async with engine.connect() as outsider:
        async with SqlUnitOfWork(engine, ACTOR) as uow:
            await uow.execute(PROBE_INSERT, {"name": PROBE_COMMIT})
            inside = (await uow.execute(COUNT_SQL, {"name": PROBE_COMMIT})).scalar_one()
            outside = await outsider.scalar(text(COUNT_SQL), {"name": PROBE_COMMIT})
            assert inside == 1
            assert outside == 0
            await uow.commit()
        committed = await outsider.scalar(text(COUNT_SQL), {"name": PROBE_COMMIT})
        assert committed == 1
