"""Issue #4, slice 1: the shared idempotency mechanism (the key store).

The approved brief (issue #4 triage ACCEPT-MODIFIED, user's answers):
- storage = a PostgreSQL table `idempotency_keys` (strategy B), permanent
  (no TTL), migration 0003 (Q1=b);
- the key is scoped to the ACTOR: `(actor, key)` is the identity (Q6=a), so two
  actors may use the same key independently;
- the store CLAIMS the key first and only records the result when the write
  succeeded (Q2=a, claim-first): a failed write must not consume the key;
- the stored "response" is the use case's RESULT VALUES, and the caller replays
  them verbatim (Q6=a "full 201 replay");
- the same key with a DIFFERENT request is a conflict -> 409 (Q4=a);
- a blank key or one longer than 255 characters is refused by the app (Q5=a).

These tests pin the STORE, against a real PostgreSQL (no mocked database,
AGENTS.md section 6). The store is a shared, database-backed component, so the
tests exercise it directly through the shared unit of work; the HTTP face of
the same behaviour is pinned in tests/ledger/api/test_deposits_idempotency.py.

The store is reached through the shared unit of work's `.idempotency`
accessor, the way every other repository is reached
(shared/infrastructure/database.py). The accessor does not exist yet, so this
file is red until /code adds it; the access is done through one typed helper
so the file fails for exactly ONE reason (the accessor is missing) and not
also on pyright's "unknown attribute" rule.

Library APIs verified in installed source this session (AGENTS.md section 3):
- sqlalchemy/ext/asyncio/engine.py: AsyncConnection.execute(text, dict) takes
  bound parameters; the same UoW wrapper the repositories use
  (shared/infrastructure/database.py:61-69);
- asyncpg: `fetchrow`/`fetchval` on the test connection (tests/conftest.py);
- the SQL names `idempotency_keys`, its columns and its constraint are the
  approved DDL of this step (brief section h); the schema itself is the
  source of truth for SQL names (AGENTS.md section 3), and every test runs
  against a real clone of the migrated template, which is the final check.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from importlib import import_module
from types import ModuleType
from typing import Any, Protocol, cast

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from mesl_finance.shared.infrastructure.database import SqlUnitOfWork, create_engine
from mesl_finance.shared.settings import Settings

ACTOR = "treasurer"
OTHER_ACTOR = "second-treasurer"
KEY = "key-alpha"
OTHER_KEY = "key-beta"


class IdempotencyStore(Protocol):
    """What the shared unit of work must expose as `.idempotency`.

    The methods are the approved contract of this slice:
    - `claim(key, fingerprint)` returns the STORED result when this actor and
      key already succeeded, or None when the key is free; a stored result
      whose fingerprint differs from the incoming one is a conflict (409);
    - `remember(key, result)` records the result of a succeeded write;
    - `result_for(key)` reads the stored result back (None when there is none).
    """

    async def claim(self, key: str, fingerprint: str) -> Any: ...

    async def remember(self, key: str, result: Any) -> None: ...

    async def result_for(self, key: str) -> Any: ...


@pytest_asyncio.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """The production engine over this test's database clone."""
    eng = create_engine(settings)
    yield eng
    await eng.dispose()


def _store_module() -> ModuleType:
    try:
        return import_module("mesl_finance.shared.infrastructure.idempotency")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/shared/infrastructure/idempotency.py does not exist yet")


def _conflict_error() -> Any:
    """The domain error a reused key with a different request must raise."""
    module = _store_module()
    for name in ("IdempotencyConflict", "IdempotencyKeyReused", "KeyReused"):
        if hasattr(module, name):
            return vars(module)[name]
    # The conflict may also be one of the shared domain errors.
    errors = import_module("mesl_finance.shared.errors")
    for name in ("IdempotencyConflict", "IdempotencyKeyReused"):
        if hasattr(errors, name):
            return vars(errors)[name]
    pytest.fail(
        "no domain error for a reused idempotency key exists yet (expected IdempotencyConflict)"
    )


def _store(uow: SqlUnitOfWork) -> IdempotencyStore:
    """The shared unit of work's idempotency accessor, typed as the port.

    The accessor is what /code adds; until then this raises AttributeError,
    which is the one and only reason this file is red.
    """
    accessor = getattr(uow, "idempotency", None)
    if accessor is None:
        pytest.fail("SqlUnitOfWork has no `idempotency` accessor yet")
    return cast(IdempotencyStore, accessor)


async def _claim(engine: AsyncEngine, key: str, fingerprint: str, *, actor: str = ACTOR) -> Any:
    """Claim a key through the shared unit of work; returns the store's answer."""
    async with SqlUnitOfWork(engine, actor) as uow:
        store = _store(uow)
        claimed: Any = await store.claim(key, fingerprint)
        return claimed


async def _remember(
    engine: AsyncEngine,
    key: str,
    result: Any,
    *,
    actor: str = ACTOR,
    fingerprint: str = "fingerprint-1",
) -> None:
    """Claim the key, then record the result of the succeeded write.

    The claim is what stores the request's FINGERPRINT; `remember` only fills
    in the result. A key that was never claimed cannot be remembered, because
    the store would have no fingerprint to compare a later claim against.
    """
    async with SqlUnitOfWork(engine, actor) as uow:
        store = _store(uow)
        await store.claim(key, fingerprint)
        await store.remember(key, result)
        await uow.commit()


async def _result_for(engine: AsyncEngine, key: str, *, actor: str = ACTOR) -> Any:
    """Read the stored result of a key back, in its own transaction."""
    async with SqlUnitOfWork(engine, actor) as uow:
        return await _store(uow).result_for(key)


async def test_a_fresh_key_claims_the_write(engine: AsyncEngine) -> None:
    """A key nobody has used is free: the claim succeeds and stores nothing yet."""
    claim = await _claim(engine, KEY, "fingerprint-1")

    assert claim is None
    assert await _result_for(engine, KEY) is None


async def test_a_replayed_key_returns_the_stored_result(engine: AsyncEngine) -> None:
    """After the write succeeded, the same key replays the stored result."""
    await _remember(engine, KEY, {"id": 42})

    claim = await _claim(engine, KEY, "fingerprint-1")

    assert claim == {"id": 42}


async def test_a_reused_key_with_a_different_request_is_a_conflict(engine: AsyncEngine) -> None:
    """The same key with a different request is refused, not silently replayed."""
    await _remember(engine, KEY, {"id": 42})

    with pytest.raises(_conflict_error()):
        await _claim(engine, KEY, "fingerprint-2")


async def test_another_actor_may_reuse_the_key(engine: AsyncEngine) -> None:
    """The key is scoped to the actor: another actor's claim is free."""
    await _remember(engine, KEY, {"id": 42})

    claim = await _claim(engine, KEY, "fingerprint-2", actor=OTHER_ACTOR)

    assert claim is None


async def test_a_different_key_is_independent(engine: AsyncEngine) -> None:
    """Two different keys never see each other's result."""
    await _remember(engine, KEY, {"id": 42})

    claim = await _claim(engine, OTHER_KEY, "fingerprint-1")

    assert claim is None


async def test_a_failed_write_does_not_consume_the_key(engine: AsyncEngine) -> None:
    """A rolled-back transaction leaves the key free for the next attempt."""
    with pytest.raises(RuntimeError, match="write failed"):
        async with SqlUnitOfWork(engine, ACTOR) as uow:
            await _store(uow).claim(KEY, "fingerprint-1")
            await _store(uow).remember(KEY, {"id": 42})
            raise RuntimeError("write failed")

    claim = await _claim(engine, KEY, "fingerprint-1")

    assert claim is None


async def test_the_key_row_commits_with_the_write(engine: AsyncEngine) -> None:
    """The key and its result are committed together, or not at all."""
    await _remember(engine, KEY, {"id": 42})

    assert await _result_for(engine, KEY) == {"id": 42}

    with pytest.raises(RuntimeError, match="write failed"):
        async with SqlUnitOfWork(engine, ACTOR) as uow:
            await _store(uow).claim(OTHER_KEY, "fingerprint-1")
            await _store(uow).remember(OTHER_KEY, {"id": 7})
            raise RuntimeError("write failed")

    assert await _result_for(engine, OTHER_KEY) is None


async def test_two_same_key_claims_in_one_transaction_write_once(engine: AsyncEngine) -> None:
    """Two claims of the same key in ONE transaction see a single write."""
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        first = await _store(uow).claim(KEY, "fingerprint-1")
        second = await _store(uow).claim(KEY, "fingerprint-1")

    assert first is None
    assert second is None
