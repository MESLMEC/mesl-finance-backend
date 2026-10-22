"""Guard tests for the single shared error translator (roadmap step 3.3).

Approved brief answers (session 2026-10-21): Q1=b - a NEW domain error class
`Unique` (subclass of RuleViolation) is delivered by /code in
src/mesl_finance/shared/errors.py together with its test in this file
(D-048's "a later step may add a new error only together with its test");
Q2 and Q3 were left unanswered, so their recorded suggestions stand:
Q2=a exposes the server's constraint name in the error detail (but no
per-constraint-name rule table until a consumer needs one) - the roadmap
line's "constraint names" word; Q3=a CODE-WITH-TESTS: the ONLY rule /code
adds is the 23505 branch named in the roadmap line; the P0001/23503
branches already exist in the pre-roadmap tree (D-023) and this step PINS
them, it does not rewrite them.

Coverage map of the ROADMAP 3.3 claims (one bullet per claim, step order):

- "RaiseError ... to typed domain errors" (execute time):
    test_known_raise_fragment_maps_to_its_domain_type
    test_unknown_raise_message_maps_to_a_rule_violation
- "commit-time raises to typed domain errors" (the DEFERRABLE entry-shape
  triggers, db/schema.sql:370-373, fire only at COMMIT):
    test_commit_time_deferred_raise_maps_to_a_domain_error
- "unique and foreign-key violations":
    test_foreign_key_violation_maps_to_unknown_reference
    test_unique_violation_maps_to_the_new_unique_error
- "constraint names" (the translator must carry the server's constraint
  name into the domain error detail; verified live as
  `envelopes_name_key`, the PostgreSQL default <table>_<column>_key):
    test_unique_violation_maps_to_the_new_unique_error
    test_map_db_error_returns_none_for_a_generic_dbapi_error
- untouched pass-through for an error that is none of ours:
    test_unmapped_dbapi_error_passes_through_original
- "Each rule is added with the test that needs it" (AGENTS.md section 5):
  EVERY rule that exists in error_mapping.py today is pinned here
  ('before this tenure opened' -> DateBeforeTenure; unmapped P0001 ->
  RuleViolation; P0001's 23503 -> UnknownReference), plus the one new 23505
  rule the roadmap line names - added together with these tests, /code
  never invents a rule without one.
- ROADMAP 7.1's one new rule (an EXCLUDE violation, SQLSTATE 23P01, ->
  RuleViolation; the membership-period overlap guard, db/schema.sql:101-102):
    test_exclusion_violation_maps_to_a_rule_violation

Library APIs verified in the installed source this session (AGENTS.md section 3):
- sqlalchemy/exc.py:604-690 + 761-786: `DBAPIError(statement, params, orig,
  ...)`; the driver exception stays reachable as `.orig`, which is what
  error_mapping.py unwraps;
- sqlalchemy/exc.py:849/861: IntegrityError and ProgrammingError are
  subclasses of DatabaseError, i.e. of DBAPIError - so both travel through
  the UoW's single `except DBAPIError` clause;
- asyncpg/exceptions/_base.py:29-48: the driver's error fields map 'C' ->
  `sqlstate` and 'n' -> `constraint_name` (db/schema.sql-raised P0001
  errors carry the message and sqlstate, not a constraint name);
- asyncpg/exceptions/_base.py:165-182: `PostgresError` subclasses take a
  plain message (real server errors fill the fields via `.new()`) - the
  fabricated errors in the unit test therefore carry the same class-level
  sqlstate as the real ones;
- asyncpg/exceptions/__init__.py:420-425: ForeignKeyViolationError.sqlstate
  is '23503' and UniqueViolationError.sqlstate is '23505' - as class-level
  attributes, so a fabricated instance reads them the same way;
- asyncpg/exceptions/__init__.py:707: UndefinedTableError (sqlstate 42P01)
  is the "none of ours" pass-through case;
- asyncpg/exceptions/__init__.py:432-433: ExclusionViolationError.sqlstate is
  '23P01' (the membership-period overlap rule, ROADMAP 7.1);
- the DB-backed tests use only the production path already verified in
  step 3.2 (SqlUnitOfWork.execute / .commit over AsyncConnection /
  AsyncTransaction) - no new library API is assumed;
- every test runs on its own clone (tests/conftest.py), so no probe
  committed in one test can be seen by another.
"""

from collections.abc import AsyncIterator
from datetime import date

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine

import mesl_finance.shared.errors as errors_mod
from mesl_finance.shared.errors import (
    DateBeforeTenure,
    DomainError,
    RuleViolation,
    UnknownReference,
)
from mesl_finance.shared.infrastructure.database import SqlUnitOfWork, create_engine
from mesl_finance.shared.infrastructure.error_mapping import map_db_error
from mesl_finance.shared.settings import Settings
from tests.conftest import TestDb

ACTOR = "treasurer-test"

# The open tenure the `lab` fixture opens (tests/conftest.py:117).
TENURE_OPENED_ON = date(2026, 1, 1)


def _unique_class() -> type[RuleViolation]:
    """The Q1=b deliverable. Imported lazily so only THIS test fails while the
    class is still missing (a module-level import error would hide the
    other tests' results and break collection for no good reason)."""
    cls = getattr(errors_mod, "Unique", None)
    if cls is None:
        pytest.fail("the `Unique` domain error (brief Q1=b) does not exist yet")
    assert isinstance(cls, type) and issubclass(cls, RuleViolation)
    return cls


@pytest_asyncio.fixture
async def engine(lab: TestDb, settings: Settings) -> AsyncIterator[AsyncEngine]:
    """The production engine over this test's database clone, as in 3.1's tests.

    `lab` and `settings` both depend on the same cached `db` fixture, so the
    engine and the raw connections alias one database.
    """
    eng = create_engine(settings)
    yield eng
    await eng.dispose()


async def _open_tenure_id(uow: SqlUnitOfWork) -> int:
    return (await uow.execute("SELECT min(id) FROM tenures")).scalar_one()


async def test_known_raise_fragment_maps_to_its_domain_type(engine: AsyncEngine) -> None:
    """schema: a rate/entry dated before the tenure open triggers
    `RAISE EXCEPTION 'date % is before this tenure opened on %'`
    (db/schema.sql:303, 390, 791); it must arrive as DateBeforeTenure."""
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        # schema: labapp may INSERT ledger_transactions (db/schema.sql:1193).
        with pytest.raises(DateBeforeTenure) as exc:
            await uow.execute(
                "INSERT INTO ledger_transactions (tenure_id, kind, occurred_on, recorded_by)"
                " VALUES (:tenure_id, 'expense', :occurred_on, :recorded_by)",
                {
                    "tenure_id": await _open_tenure_id(uow),
                    "occurred_on": date(2025, 12, 25),
                    "recorded_by": ACTOR,
                },
            )
    assert "before this tenure opened" in exc.value.detail


async def test_unknown_raise_message_maps_to_a_rule_violation(engine: AsyncEngine) -> None:
    """schema: changing the pool flag is refused outright,
    `RAISE EXCEPTION 'the pool flag cannot be changed'` (db/schema.sql:148);
    the message matches no fragment -> the generic RuleViolation fallback
    with the database's own message. (A DELETE probe is wrong here on
    purpose: labapp has no DELETE grant anywhere, so the trigger would
    never be reached.)"""
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        with pytest.raises(RuleViolation) as exc:
            await uow.execute("UPDATE envelopes SET is_pool = true WHERE id = 2")
    assert "pool flag cannot be changed" in exc.value.detail


async def test_foreign_key_violation_maps_to_unknown_reference(engine: AsyncEngine) -> None:
    """schema: UPDATE ledger_transactions... cost_center_id is a granted
    label column (db/schema.sql:1196, 398); pointing it at a nonexistent
    cost_centers.id violates the FK (schema.sql:252) -> UnknownReference."""
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        # schema: a deposit needs a source and no negative amounts (checked at
        # COMMIT - this UoW rolls back instead).
        tx_id = (
            await uow.execute(
                "INSERT INTO ledger_transactions"
                " (tenure_id, kind, occurred_on, recorded_by, source)"
                " VALUES (:tenure_id, 'deposit', :occurred_on, :recorded_by, 'admin_grant')"
                " RETURNING id",
                {
                    "tenure_id": await _open_tenure_id(uow),
                    "occurred_on": date(2026, 1, 5),
                    "recorded_by": ACTOR,
                },
            )
        ).scalar_one()
        with pytest.raises(UnknownReference) as exc:
            await uow.execute(
                "UPDATE ledger_transactions SET cost_center_id = 999999 WHERE id = :id",
                {"id": tx_id},
            )
    assert "cost_center_id" in exc.value.detail


async def test_unique_violation_maps_to_the_new_unique_error(engine: AsyncEngine) -> None:
    """schema: `name text NOT NULL UNIQUE` (db/schema.sql:68); a duplicate
    name violates `envelopes_name_key` (verified live today) -> the new
    `Unique` error whose detail carries the constraint name (Q2)."""
    unique = _unique_class()
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        with pytest.raises(DomainError) as exc:
            await uow.execute("INSERT INTO envelopes (name) VALUES ('Unallocated General')")
    err = exc.value
    assert isinstance(err, unique)
    assert isinstance(err, RuleViolation)  # sketch of Q1=b: a RuleViolation subclass
    assert "envelopes_name_key" in err.detail


async def test_commit_time_deferred_raise_maps_to_a_domain_error(engine: AsyncEngine) -> None:
    """schema: the DEFERRABLE entry-shape trigger fires only at COMMIT
    (db/schema.sql:370-373); a deposit with no lines raises
    `entry % has no amounts` (schema.sql:348) inside uow.commit() and must
    surface as a typed domain error, not a raw DBAPIError."""
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        await uow.execute(
            "INSERT INTO ledger_transactions"
            " (tenure_id, kind, occurred_on, recorded_by, source)"
            " VALUES (:tenure_id, 'deposit', :occurred_on, :recorded_by, 'admin_grant')",
            {
                "tenure_id": await _open_tenure_id(uow),
                "occurred_on": date(2026, 1, 5),
                "recorded_by": ACTOR,
            },
        )
        with pytest.raises(RuleViolation) as exc:
            await uow.commit()
    assert "no amounts" in exc.value.detail


async def test_unmapped_dbapi_error_passes_through_original(engine: AsyncEngine) -> None:
    """An error that maps to no rule is re-raised as itself: not any
    DomainError; the SQLAlchemy wrapper the caller would also see without
    the translator."""
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        with pytest.raises(ProgrammingError) as exc:
            await uow.execute("SELECT * FROM slider_pox_gone_missing")
    assert not isinstance(exc.value, DomainError)


def test_map_db_error_returns_none_for_a_generic_dbapi_error() -> None:
    """Pure-function level: the same contract without a database round-trip.

    The fabrication mirrors how the driver delivers real errors
    (`constraint_name` is set from the server's 'n' field,
    asyncpg/exceptions/_base.py:44 - the execute-time test proves the real
    chain)."""
    unique = _unique_class()
    duplicate = asyncpg.UniqueViolationError(
        'duplicate key value violates unique constraint "envelopes_name_key"'
    )
    duplicate.constraint_name = "envelopes_name_key"
    wrapped = DBAPIError("INSERT INTO envelopes (name) VALUES (:name)", None, duplicate)
    mapped = map_db_error(wrapped)
    assert isinstance(mapped, DomainError)
    assert isinstance(mapped, unique)
    assert "envelopes_name_key" in mapped.detail

    unrelated = asyncpg.UndefinedTableError('relation "no_such_table" does not exist')
    assert map_db_error(DBAPIError("SELECT * FROM no_such_table", None, unrelated)) is None


async def test_exclusion_violation_maps_to_a_rule_violation(engine: AsyncEngine) -> None:
    """schema: `membership_periods` forbids overlapping periods with an EXCLUDE
    constraint (db/schema.sql:101-102). The second INSERT raises SQLSTATE 23P01
    (asyncpg/exceptions/__init__.py:432-433); ROADMAP 7.1 (brief Q9=a) adds the
    one translator rule that turns it into a 409 `rule_violation` instead of
    letting a raw DBAPIError escape."""
    async with SqlUnitOfWork(engine, ACTOR) as uow:
        member_id = (
            await uow.execute("INSERT INTO members (name) VALUES ('A') RETURNING id")
        ).scalar_one()
        await uow.execute(
            "INSERT INTO membership_periods (member_id, start_date)"
            " VALUES (:member_id, DATE '2026-02-01')",
            {"member_id": member_id},
        )
        with pytest.raises(RuleViolation) as exc:
            await uow.execute(
                "INSERT INTO membership_periods (member_id, start_date)"
                " VALUES (:member_id, DATE '2026-03-01')",
                {"member_id": member_id},
            )
    assert "exclusion" in exc.value.detail.lower()
