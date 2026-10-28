r"""Contract tests for allocation sessions, event leftovers and sweeps.

Ported from the worked example `db/examples/06_allocation_and_sweeps.sql`. The behaviour already
exists in `db/schema.sql`, so every test here passes at once (TEST-ONLY step, D-045).

Tests referenced by the coverage table:

  T1  test_allocation_context_header
  T2  test_allocation_suggestion_splits_by_shares
  T3  test_allocation_suggestion_without_shares_only_fills_caps
  T4  test_allocation_suggestion_small_amount_follows_priority
  T5  test_allocate_writes_one_transfer_and_a_session
  T6  test_suggestion_reuses_the_last_session_proportions
  T7  test_a_voided_session_is_ignored
  T8  test_the_committee_may_override_a_cap
  T9  test_bad_allocations_are_refused (9 parametrized cases)
  T10 test_the_app_role_cannot_delete_allocation_sessions
  T11 test_envelope_guards_refuse_unsafe_changes
  T12 test_an_empty_envelope_can_be_deactivated
  T13 test_allocation_to_an_inactive_envelope_is_refused
  T14 test_event_leftovers_before_any_sweep
  T15 test_voiding_an_expense_restores_the_leftover
  T16 test_sweep_moves_the_leftover_to_the_pool
  T17 test_sweep_refusals
  T18 test_a_reversed_sweep_restores_the_leftover_and_can_be_repeated
  T19 test_the_database_stays_healthy
  T20 test_close_tenure_keeps_sessions_and_balances

Coverage proof - every `EXPECT` / `EXPECT FAIL` line of the example, in script order. The file
header (line 1) only explains the marker convention, so it is not a row (D-100 (5) precedent).

  line 2        s0 = sunday_on_or_before(current_date)     start()
  line 3        tenure T1 opens on s0 (owner only)         start()
  line 4        SET ROLE labapp                            start() uses the app connection
  lines 5-8     six envelopes, pool first                  start()
  line 9        member X                                   start()
  lines 10-15   pool 3000, fee 50, opening split           start()
  line 17       EXPECT pool 2560, credit 50, after 2510    T1
  line 18       allocation_context                          T1
  line 19       EXPECT Admin 60, Components 50, Projects
                445, Events 297, Research 148               T2
  line 20       suggestion with shares 3:2:1                T2
  line 21       sum(suggested) = 1000                       T2
  line 22       EXPECT only the 110 cap fills               T3
  line 23       suggestion with no shares                   T3
  line 24       EXPECT Admin 30, Components 0               T4
  line 25       suggestion(30) for the capped envelopes     T4
  line 27       confirm the first session                   T5
  line 28       amounts = suggestion(...) where > 0         T5 (setup)
  line 29       allocate(...) returns the session transfer  T5
  line 30       EXPECT pool 1560, 100/500/445/297/148       T5
  line 31       envelope_balances                           T5
  line 33       EXPECT Projects 300, Events 200,
                Research 100, caps 0                        T6
  line 34       suggestion(600)                             T6
  line 36       EXPECT the voided session is ignored        T7
  line 37       allocate session 2 (Research 100)           T7 (setup)
  line 38       max(allocation_sessions ledger_transaction) T7 (setup)
  lines 39-42   reversal voiding session 2                  T7 (setup)
  line 43       suggestion(600) still 300/200/100           T7
  line 45       EXPECT a cap override is accepted           T8
  line 46       allocate 400 into a cap-100 envelope        T8
  line 47       EXPECT FAIL x N: bad allocations            T9
  line 48       too much (999999 into Projects)             T9[too-much]
  line 49       to the pool itself                          T9[to-itself]
  line 50       negative amount                             T9[negative]
  line 51       zero amount                                 T9[zero]
  line 52       unknown envelope                            T9[unknown]
  line 53       non-numeric amount                          T9[text]
  line 54       a JSON array instead of an object           T9[array]
  line 55       an empty object                             T9[empty]
  line 56       a blank note                                T9[blank-note]
  line 57       DELETE FROM allocation_sessions (unmarked;
                `labapp` has INSERT only)                   T10
  line 59       EXPECT FAIL: pool flag, non-empty
                deactivate, delete; ok: empty deactivate    T11, T10 and T12
  line 60       change the pool flag                        T11
  line 61       deactivate a non-empty envelope             T11
  line 62       deactivate the pool                         T11
  line 63       create 'Old idea'                           T12
  line 64       deactivate the empty envelope (ok)          T12
  line 65       allocate to an inactive envelope            T13
  line 67       EXPECT in 1000, out 500, swept 0, left 500  T14
  line 68       cost center 'Robotics Workshop' (event)     T14 (setup)
  lines 69-74   grant 1000, two expenses 400 + 100          T14 (setup)
  line 75       EXPECT in/out/swept/leftover                 T14
  line 76       cost_center_summary                         T14
  line 77       EXPECT out 400, leftover 600                 T15
  line 78       the decorations entry id                    T15 (setup)
  lines 79-80   reversal with no event label                 T15
  line 81       cost_center_summary                         T15
  line 82       EXPECT swept 600, leftover 0,
                Events 297, pool +600                       T16
  line 83       pool_before                                 T16
  line 84       sweep_leftover(...)                         T16
  line 85       cost_center_summary                         T16
  line 86       Events envelope balance                     T16
  line 87       pool gain                                   T16
  line 88       EXPECT FAIL: nothing left, no event, pool   T17
  line 89       sweep again (nothing left)                  T17
  line 90       sweep header with no cost center            T17
  line 91       sweep from the pool                         T17
  line 92       EXPECT swept 0, leftover 600, then sweep    T18
  line 93       the sweep entry id                          T18 (setup)
  lines 94-95   reversal of the sweep                       T18
  line 96       swept 0, leftover 600                       T18
  line 97       sweep again                                 T18
  line 98       swept 600, leftover 0                       T18
  line 99       RESET ROLE                                  no statement; conftest swaps connections
  line 100      EXPECT health: 0 rows                       T19
  line 101      verify_all()                                T19
  line 102      EXPECT health 0 after close; sessions kept  T20
  line 103      SET ROLE labapp                             T20
  line 104      close_tenure(s0+20, 'treasurer', 'T2')      T20
  line 105      RESET ROLE                                  no statement
  line 106      verify_all() after close                    T20
  line 107      allocation_sessions count (3)               T20
  line 108      final envelope_balances                     T20

Two script oddities are pinned rather than smoothed over (approved in the step brief): line 57's
DELETE is not marked `EXPECT FAIL` although `labapp` has only INSERT on the table, so it is covered
as `InsufficientPrivilegeError`; and line 59's "delete" has no envelope DELETE statement, so the
three refusal labels map to lines 60-62 and the unmarked session DELETE is line 57.

Rejected statements run in the state the script has when it reaches them (`script_prefix` + setup),
so each assertion pins the class PostgreSQL really raises: trigger and function refusals are P0001
(`RaiseError`), CHECKs are 23514 (`CheckViolationError`), the missing DELETE grant is 42501
(`InsufficientPrivilegeError`). Dates are relative to the current Sunday (`s0`; D-045/D-099).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import asyncpg
import pytest

from tests.conftest import TestDb

POOL, ADMIN, COMPONENTS, PROJECTS, EVENTS, RESEARCH = 1, 2, 3, 4, 5, 6
ONE_DAY = timedelta(days=1)


@dataclass
class Context:
    """One `allocation_context` row: the allocation screen's header."""

    pool_balance: int
    member_credit_held: int
    pool_after_member_credit: int


@dataclass
class Suggestion:
    """One `allocation_suggestion()` row."""

    envelope_id: int
    name: str
    balance: int
    cap: int | None
    gap: int | None
    phase: str
    suggested: int


@dataclass
class Summary:
    """One `cost_center_summary` row."""

    money_in: int
    money_out: int
    swept: int
    leftover: int


async def enter(
    conn: asyncpg.Connection,
    kind: str,
    lines: list[tuple[int, int]],
    *,
    on: date,
    tenure_id: int = 1,
    **cols: Any,
) -> int:
    """Write one ledger entry (header + lines) in ONE transaction; returns its id."""
    keys = ["tenure_id", "kind", "occurred_on", "recorded_by", *cols]
    values = [tenure_id, kind, on, "treasurer", *cols.values()]
    placeholders = ",".join(f"${i + 1}" for i in range(len(keys)))
    async with conn.transaction():
        columns = ",".join(keys)
        tx: int = await conn.fetchval(
            f"INSERT INTO ledger_transactions({columns}) VALUES ({placeholders}) RETURNING id",
            *values,
        )
        for envelope_id, amount in lines:
            await conn.execute(
                "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1,$2,$3)",
                tx,
                envelope_id,
                amount,
            )
    return tx


async def allocate(
    conn: asyncpg.Connection,
    s0: date,
    amounts: Any,
    *,
    day: int,
    note: str,
) -> int:
    """Call `allocate()` with the script's `s0`-relative date and a JSON amounts object."""
    tx: int = await conn.fetchval(
        "SELECT allocate('treasurer', $1::date + $2::int, $3, $4::jsonb)",
        s0,
        day,
        note,
        json.dumps(amounts),
    )
    return tx


async def suggestion(
    conn: asyncpg.Connection,
    amount: int,
    shares: dict[str, int] | None = None,
) -> list[Suggestion]:
    """`allocation_suggestion()` in the function's own order (priority, then envelope id)."""
    rows: list[Any] = await conn.fetch(
        "SELECT envelope_id, envelope_name, balance, target_cap, gap, phase, suggested"
        " FROM allocation_suggestion($1, $2::jsonb)",
        amount,
        None if shares is None else json.dumps(shares),
    )
    return [
        Suggestion(
            envelope_id=int(row["envelope_id"]),
            name=str(row["envelope_name"]),
            balance=int(row["balance"]),
            cap=None if row["target_cap"] is None else int(row["target_cap"]),
            gap=None if row["gap"] is None else int(row["gap"]),
            phase=str(row["phase"]),
            suggested=int(row["suggested"]),
        )
        for row in rows
    ]


async def context(conn: asyncpg.Connection) -> Context:
    """The single `allocation_context` row."""
    row = await conn.fetchrow(
        "SELECT pool_balance, member_credit_held, pool_after_member_credit FROM allocation_context"
    )
    assert row is not None
    return Context(
        pool_balance=int(row["pool_balance"]),
        member_credit_held=int(row["member_credit_held"]),
        pool_after_member_credit=int(row["pool_after_member_credit"]),
    )


async def balances(conn: asyncpg.Connection) -> dict[str, int]:
    """Every envelope's current-tenure balance, keyed by name (id order)."""
    rows: list[Any] = await conn.fetch("SELECT name, balance FROM envelope_balances ORDER BY id")
    return {str(row["name"]): int(row["balance"]) for row in rows}


async def summary(conn: asyncpg.Connection, cost_center_id: int = 1) -> Summary:
    """The single `cost_center_summary` row for the script's event."""
    row = await conn.fetchrow(
        "SELECT money_in, money_out, swept, leftover FROM cost_center_summary"
        " WHERE cost_center_id = $1",
        cost_center_id,
    )
    assert row is not None
    return Summary(
        money_in=int(row["money_in"]),
        money_out=int(row["money_out"]),
        swept=int(row["swept"]),
        leftover=int(row["leftover"]),
    )


async def start(db: TestDb) -> date:
    """Lines 2-15: tenure T1, six envelopes, member X and the three opening entries."""
    s0: date = await db.app.fetchval("SELECT sunday_on_or_before(current_date)")
    await db.owner.execute("INSERT INTO tenures(name, opened_on) VALUES ('T1', $1)", s0)
    await db.app.execute(
        "INSERT INTO envelopes(name, is_pool) VALUES ('Unallocated General', true)"
    )
    await db.app.execute(
        "INSERT INTO envelopes(name, target_cap, alloc_priority) VALUES ('Admin and Misc', 100, 1)"
    )
    await db.app.execute(
        "INSERT INTO envelopes(name, target_cap, alloc_priority)"
        " VALUES ('Components and Equipment', 500, 2)"
    )
    await db.app.execute(
        "INSERT INTO envelopes(name) VALUES ('Member Projects'), ('Events and Workshops'),"
        " ('Research')"
    )
    await db.app.execute("INSERT INTO members(name) VALUES ('X')")
    await enter(db.app, "deposit", [(POOL, 3000)], on=s0, source="other")
    await enter(db.app, "deposit", [(POOL, 50)], on=s0, source="weekly_fee", member_id=1)
    await enter(
        db.app,
        "transfer",
        [(POOL, -490), (ADMIN, 40), (COMPONENTS, 450)],
        on=s0,
        note="opening split",
    )
    return s0


async def confirm_first_session(db: TestDb, s0: date) -> int:
    """Lines 27-29: allocate exactly the drafted suggestion (only rows with a positive amount)."""
    draft = await suggestion(db.app, 1000, {"4": 3, "5": 2, "6": 1})
    amounts = {str(row.envelope_id): row.suggested for row in draft if row.suggested > 0}
    return await allocate(db.app, s0, amounts, day=1, note="first monthly allocation")


async def void_second_session(db: TestDb, s0: date) -> int:
    """Lines 36-42: a second session, then a reversal that voids it."""
    session: int = await allocate(db.app, s0, {"6": 100}, day=2, note="research top-up")
    await enter(
        db.app,
        "reversal",
        [(POOL, 100), (RESEARCH, -100)],
        on=s0 + 2 * ONE_DAY,
        reverses_id=session,
        note="wrong envelope",
    )
    return session


async def override_admin(db: TestDb, s0: date) -> int:
    """Lines 45-46: 400 into the cap-100 envelope; caps are guidance only."""
    return await allocate(db.app, s0, {"2": 400}, day=3, note="emergency admin spend")


async def event_block(db: TestDb, s0: date) -> None:
    """Lines 67-74: one event cost center, a 1000 grant and expenses of 400 and 100."""
    await db.app.execute(
        "INSERT INTO cost_centers(name, kind) VALUES ('Robotics Workshop', 'event')"
    )
    await enter(
        db.app,
        "deposit",
        [(EVENTS, 1000)],
        on=s0 + 4 * ONE_DAY,
        source="admin_grant",
        cost_center_id=1,
        note="admin event grant",
    )
    await enter(
        db.app,
        "expense",
        [(EVENTS, -400)],
        on=s0 + 5 * ONE_DAY,
        cost_center_id=1,
        tag="catering",
    )
    await enter(
        db.app,
        "expense",
        [(EVENTS, -100)],
        on=s0 + 5 * ONE_DAY,
        cost_center_id=1,
        tag="decorations",
    )


async def void_decorations(db: TestDb, s0: date) -> int:
    """Lines 77-80: reverse the 100 expense; the reversal carries no event label."""
    dec: int = await db.app.fetchval("SELECT id FROM ledger_transactions WHERE tag = 'decorations'")
    await enter(
        db.app,
        "reversal",
        [(EVENTS, 100)],
        on=s0 + 6 * ONE_DAY,
        reverses_id=dec,
        note="not bought",
    )
    return dec


async def sweep(
    db: TestDb,
    s0: date,
    *,
    day: int = 7,
    note: str = "event over; leftover back to pool",
) -> int:
    """Line 84 (and 97): move the event's leftover from its envelope back to the pool."""
    tx: int = await db.app.fetchval(
        "SELECT sweep_leftover($1, $2, 'treasurer', $3::date + $4::int, $5)",
        1,
        EVENTS,
        s0,
        day,
        note,
    )
    return tx


async def reverse_sweep(db: TestDb, s0: date, sweep_tx: int) -> int:
    """Lines 92-95: undo the sweep with a reversal."""
    return await enter(
        db.app,
        "reversal",
        [(EVENTS, 600), (POOL, -600)],
        on=s0 + 8 * ONE_DAY,
        reverses_id=sweep_tx,
        note="swept too early",
    )


async def allocation_prefix(db: TestDb) -> date:
    """Lines 2-46: the three sessions (the second voided) and the cap override."""
    s0 = await start(db)
    await confirm_first_session(db, s0)
    await void_second_session(db, s0)
    await override_admin(db, s0)
    return s0


async def event_prefix(db: TestDb) -> date:
    """Lines 2-81: allocation prefix, inert 'Old idea', event block, voided expense."""
    s0 = await allocation_prefix(db)
    await db.app.execute("INSERT INTO envelopes(name) VALUES ('Old idea')")
    await db.app.execute("UPDATE envelopes SET active = false WHERE name = 'Old idea'")
    await event_block(db, s0)
    await void_decorations(db, s0)
    return s0


async def script_prefix(db: TestDb, *, second_sweep: bool = True) -> date:
    """Everything up to the second sweep (line 97); failed guard attempts change nothing."""
    s0 = await event_prefix(db)
    first = await sweep(db, s0)
    await reverse_sweep(db, s0, first)
    if second_sweep:
        await sweep(db, s0, day=9, note="event really over")
    return s0


async def test_allocation_context_header(db: TestDb) -> None:
    """Lines 17-18: the pool and member-credit header of the allocation screen."""
    await start(db)
    header = await context(db.app)
    assert (header.pool_balance, header.member_credit_held, header.pool_after_member_credit) == (
        2560,
        50,
        2510,
    )


async def test_allocation_suggestion_splits_by_shares(db: TestDb) -> None:
    """Lines 19-21: caps first (priority order), then the shares 3:2:1; the sum is 1000."""
    await start(db)
    rows = await suggestion(db.app, 1000, {"4": 3, "5": 2, "6": 1})
    assert [
        (row.name, row.balance, row.cap, row.gap, row.phase, row.suggested) for row in rows
    ] == [
        ("Admin and Misc", 40, 100, 60, "cap_fill", 60),
        ("Components and Equipment", 450, 500, 50, "cap_fill", 50),
        ("Member Projects", 0, None, None, "share", 445),
        ("Events and Workshops", 0, None, None, "share", 297),
        ("Research", 0, None, None, "share", 148),
    ]
    assert sum(row.suggested for row in rows) == 1000


async def test_allocation_suggestion_without_shares_only_fills_caps(db: TestDb) -> None:
    """Lines 22-23: with no shares and no history only the 110 of cap fills is suggested."""
    await start(db)
    rows = await suggestion(db.app, 1000)
    positive = {row.name: (row.phase, row.suggested) for row in rows if row.suggested > 0}
    assert positive == {
        "Admin and Misc": ("cap_fill", 60),
        "Components and Equipment": ("cap_fill", 50),
    }
    assert sum(row.suggested for row in rows) == 110


async def test_allocation_suggestion_small_amount_follows_priority(db: TestDb) -> None:
    """Lines 24-25: 30 fills the lowest-priority-number gap first and leaves Components at zero."""
    await start(db)
    amounts = {row.name: row.suggested for row in await suggestion(db.app, 30)}
    assert amounts["Admin and Misc"] == 30
    assert amounts["Components and Equipment"] == 0


async def test_allocate_writes_one_transfer_and_a_session(db: TestDb) -> None:
    """Lines 27-31: the confirmed draft becomes one tagged transfer plus a session row."""
    s0 = await start(db)
    tx = await confirm_first_session(db, s0)
    assert await balances(db.app) == {
        "Unallocated General": 1560,
        "Admin and Misc": 100,
        "Components and Equipment": 500,
        "Member Projects": 445,
        "Events and Workshops": 297,
        "Research": 148,
    }
    header = await db.app.fetchrow(
        "SELECT kind, tag, note, occurred_on FROM ledger_transactions WHERE id = $1",
        tx,
    )
    assert header is not None
    assert (
        header["kind"],
        header["tag"],
        header["note"],
        header["occurred_on"],
    ) == ("transfer", "allocation", "first monthly allocation", s0 + ONE_DAY)
    assert await db.app.fetchval("SELECT count(*) FROM allocation_sessions") == 1


async def test_suggestion_reuses_the_last_session_proportions(db: TestDb) -> None:
    """Lines 33-34: with no shares the last session's uncapped proportions are reused."""
    s0 = await start(db)
    await confirm_first_session(db, s0)
    rows = {row.name: row for row in await suggestion(db.app, 600)}
    assert (rows["Member Projects"].phase, rows["Member Projects"].suggested) == ("share", 300)
    assert (rows["Events and Workshops"].phase, rows["Events and Workshops"].suggested) == (
        "share",
        200,
    )
    assert (rows["Research"].phase, rows["Research"].suggested) == ("share", 100)
    assert rows["Admin and Misc"].suggested == 0
    assert rows["Components and Equipment"].suggested == 0


async def test_a_voided_session_is_ignored(db: TestDb) -> None:
    """Lines 36-43: after the second session is voided, its 100 no longer drives the shares."""
    s0 = await start(db)
    await confirm_first_session(db, s0)
    await void_second_session(db, s0)
    amounts = {row.name: row.suggested for row in await suggestion(db.app, 600)}
    assert (
        amounts["Member Projects"],
        amounts["Events and Workshops"],
        amounts["Research"],
    ) == (300, 200, 100)


async def test_the_committee_may_override_a_cap(db: TestDb) -> None:
    """Lines 45-46: 400 into a cap-100 envelope is accepted; caps are guidance only."""
    s0 = await start(db)
    await confirm_first_session(db, s0)
    await override_admin(db, s0)
    envelope_balances = await balances(db.app)
    assert envelope_balances["Admin and Misc"] == 500
    assert envelope_balances["Unallocated General"] == 1160


BAD_ALLOCATION_IDS = [
    "too-much",
    "to-itself",
    "negative",
    "zero",
    "unknown",
    "text",
    "array",
    "empty",
    "blank-note",
]

BAD_ALLOCATIONS: list[tuple[str, Any, type[Exception], str]] = [
    ("too much", {"4": 999999}, asyncpg.RaiseError, "below zero"),
    ("to itself", {"1": 10}, asyncpg.RaiseError, "pool cannot be allocated to itself"),
    ("negative", {"4": -5}, asyncpg.RaiseError, "bad entry"),
    ("zero", {"4": 0}, asyncpg.RaiseError, "zero amount"),
    ("unknown", {"99": 10}, asyncpg.RaiseError, "does not exist or is inactive"),
    ("text", {"4": "abc"}, asyncpg.RaiseError, "bad entry"),
    ("array", [1, 2], asyncpg.RaiseError, "amounts must be a JSON object"),
    ("empty", {}, asyncpg.RaiseError, "nothing to allocate"),
    ("", {"4": 10}, asyncpg.CheckViolationError, "ledger_transactions_check"),
]


@pytest.mark.parametrize(
    ("note", "amounts", "error", "match"), BAD_ALLOCATIONS, ids=BAD_ALLOCATION_IDS
)
async def test_bad_allocations_are_refused(
    db: TestDb,
    note: str,
    amounts: Any,
    error: type[Exception],
    match: str,
) -> None:
    """Lines 48-56: every malformed or overdrawing allocation is refused by PostgreSQL."""
    s0 = await allocation_prefix(db)
    with pytest.raises(error, match=match):
        await allocate(db.app, s0, amounts, day=3, note=note)


async def test_the_app_role_cannot_delete_allocation_sessions(db: TestDb) -> None:
    """Line 57: `labapp` has only INSERT, so the sessions survive the DELETE attempt."""
    await allocation_prefix(db)
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await db.app.execute("DELETE FROM allocation_sessions")
    assert await db.app.fetchval("SELECT count(*) FROM allocation_sessions") == 3


async def test_envelope_guards_refuse_unsafe_changes(db: TestDb) -> None:
    """Lines 60-62: the pool flag, a non-empty deactivation and the pool itself are guarded."""
    await allocation_prefix(db)
    with pytest.raises(asyncpg.RaiseError, match="pool flag cannot be changed"):
        await db.app.execute("UPDATE envelopes SET is_pool = false WHERE is_pool")
    with pytest.raises(asyncpg.RaiseError, match="still holds 148"):
        await db.app.execute("UPDATE envelopes SET active = false WHERE name = 'Research'")
    with pytest.raises(asyncpg.RaiseError, match="pool cannot be deactivated"):
        await db.app.execute("UPDATE envelopes SET active = false WHERE is_pool")


async def test_an_empty_envelope_can_be_deactivated(db: TestDb) -> None:
    """Lines 63-64: a freshly created, empty envelope may be deactivated."""
    await allocation_prefix(db)
    await db.app.execute("INSERT INTO envelopes(name) VALUES ('Old idea')")
    await db.app.execute("UPDATE envelopes SET active = false WHERE name = 'Old idea'")
    row = await db.app.fetchrow("SELECT active FROM envelopes WHERE name = 'Old idea'")
    assert row is not None and row["active"] is False
    assert (await balances(db.app))["Old idea"] == 0


async def test_allocation_to_an_inactive_envelope_is_refused(db: TestDb) -> None:
    """Line 65: allocate() refuses an envelope that is inactive."""
    s0 = await allocation_prefix(db)
    await db.app.execute("INSERT INTO envelopes(name) VALUES ('Old idea')")
    await db.app.execute("UPDATE envelopes SET active = false WHERE name = 'Old idea'")
    old: int = await db.app.fetchval("SELECT id FROM envelopes WHERE name = 'Old idea'")
    with pytest.raises(asyncpg.RaiseError, match="does not exist or is inactive"):
        await allocate(db.app, s0, {str(old): 10}, day=3, note="to inactive")


async def test_event_leftovers_before_any_sweep(db: TestDb) -> None:
    """Lines 67-76: the event's grant and expenses leave 500 to sweep."""
    s0 = await allocation_prefix(db)
    await event_block(db, s0)
    assert await summary(db.app) == Summary(money_in=1000, money_out=500, swept=0, leftover=500)


async def test_voiding_an_expense_restores_the_leftover(db: TestDb) -> None:
    """Lines 77-81: a reversal with no event label is attributed to the original's event."""
    await event_prefix(db)
    dec: int = await db.app.fetchval("SELECT id FROM ledger_transactions WHERE tag = 'decorations'")
    assert await summary(db.app) == Summary(money_in=1000, money_out=400, swept=0, leftover=600)
    row = await db.app.fetchrow(
        "SELECT cost_center_id FROM ledger_transactions WHERE reverses_id = $1",
        dec,
    )
    assert row is not None and row["cost_center_id"] is None


async def test_sweep_moves_the_leftover_to_the_pool(db: TestDb) -> None:
    """Lines 82-87: the sweep empties the event's envelope and adds the same amount to the pool."""
    s0 = await event_prefix(db)
    before = (await context(db.app)).pool_balance
    tx = await sweep(db, s0)
    assert await summary(db.app) == Summary(money_in=1000, money_out=400, swept=600, leftover=0)
    assert (await balances(db.app))["Events and Workshops"] == 297
    assert (await context(db.app)).pool_balance - before == 600
    header = await db.app.fetchrow(
        "SELECT kind, cost_center_id, note FROM ledger_transactions WHERE id = $1",
        tx,
    )
    assert header is not None
    assert (header["kind"], header["cost_center_id"], header["note"]) == (
        "sweep",
        1,
        "event over; leftover back to pool",
    )


async def test_sweep_refusals(db: TestDb) -> None:
    """Lines 88-91: nothing left, a sweep with no event, and a sweep out of the pool."""
    s0 = await event_prefix(db)
    await sweep(db, s0)
    with pytest.raises(asyncpg.RaiseError, match="nothing to sweep"):
        await sweep(db, s0)
    with pytest.raises(asyncpg.CheckViolationError, match="sweep_needs_cc"):
        await db.app.execute(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, note)"
            " VALUES (1, 'sweep', $1::date + 7, 'treasurer', 'no event named')",
            s0,
        )
    with pytest.raises(asyncpg.RaiseError, match="sweep from an envelope other than the pool"):
        await db.app.execute(
            "SELECT sweep_leftover(1, $1, 'treasurer', $2::date + 7, 'from pool')",
            POOL,
            s0,
        )


async def test_a_reversed_sweep_restores_the_leftover_and_can_be_repeated(db: TestDb) -> None:
    """Lines 92-98: the reversal restores the 600, then a second sweep is accepted."""
    s0 = await event_prefix(db)
    first = await sweep(db, s0)
    await reverse_sweep(db, s0, first)
    assert await summary(db.app) == Summary(money_in=1000, money_out=400, swept=0, leftover=600)
    second = await sweep(db, s0, day=9, note="event really over")
    assert second > first
    assert await summary(db.app) == Summary(money_in=1000, money_out=400, swept=600, leftover=0)


async def test_the_database_stays_healthy(db: TestDb) -> None:
    """Lines 100-101: the whole lifecycle leaves a healthy database."""
    await script_prefix(db)
    problems: list[Any] = await db.app.fetch("SELECT * FROM verify_all()")
    assert problems == []


async def test_close_tenure_keeps_sessions_and_balances(db: TestDb) -> None:
    """Lines 102-108: close the tenure, stay healthy, keep the sessions and the balances."""
    s0 = await script_prefix(db)
    next_tenure: int = await db.app.fetchval(
        "SELECT close_tenure($1::date + 20, 'treasurer', 'T2')", s0
    )
    assert next_tenure > 0
    problems: list[Any] = await db.app.fetch("SELECT * FROM verify_all()")
    assert problems == []
    assert await db.app.fetchval("SELECT count(*) FROM allocation_sessions") == 3
    assert await balances(db.app) == {
        "Unallocated General": 1760,
        "Admin and Misc": 500,
        "Components and Equipment": 500,
        "Member Projects": 445,
        "Events and Workshops": 297,
        "Research": 148,
        "Old idea": 0,
    }
