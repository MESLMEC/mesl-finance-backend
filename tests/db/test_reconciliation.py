r"""Contract tests for reconciliation: match the screen to the notes, review
only entries since the last match, and find a typo from the difference.

Ported from the worked example `db/examples/07_reconciliation.sql`. The behaviour already
exists in `db/schema.sql`, so every test here passes at once (TEST-ONLY step, D-045/D-099).

Tests referenced by the coverage table:

  T1  test_before_any_check_the_whole_history_is_unverified
  T2  test_the_first_reconcile_matches_and_records_the_row
  T3  test_after_a_match_the_timer_resets
  T4  test_a_mismatched_reconcile_records_the_difference
  T5  test_the_timer_points_at_the_last_match_and_lists_four_entries
  T6  test_difference_suspects_finds_each_heuristic (5 parametrized cases)
  T7  test_difference_suspects_can_scope_to_one_envelope
  T8  test_an_unrecorded_entry_is_not_found
  T9  test_fixing_the_typo_then_reconciling_matches
  T10 test_per_envelope_counts_mismatch_on_zero_difference
  T11 test_the_rejected_reconciles_raise_their_own_errors (4 parametrized cases)
  T12 test_the_reconciliation_tables_are_append_only
  T13 test_a_late_entry_for_an_old_date_still_shows
  T14 test_the_carry_over_opening_is_not_unverified_after_close
  T15 test_verify_all_is_healthy_then_catches_the_tamper

Coverage proof - every numbered section of the example, in script order. The example has no
machine-readable `EXPECT`/`EXPECT FAIL` lines (D-046), so the sections map by number.

  lines 1-8     header, s0, tenure T1, two envelopes, member A        start()
  lines 9-15    month 1 entries: opening 1000, deposit 200,
                expense -50 -> screen 1150                            start()
  line 17       unverified: 3 entries, last match empty               T1
  line 19-20    reconcile 1150 -> matched; the stored row             T2
  line 22       entries 0, days 0, latest matched                     T3
  lines 24-32   month 2: fee 100, expense -120, transfer 0,
                events expense -45 -> screen 1085                     month2()
  lines 33-35   reconcile 1193 -> mismatched, difference 108          T4
  lines 37-38   timer: last match 1/through 3, 4 unverified,
                latest f, diff 108; the four unverified rows          T5
  lines 40-49   difference_suspects: 108/-9/120/240/-405              T6
  line 51       suspects(-300, envelope 2) -> entry 6 (transfer)      T7
  line 53       suspects(77) -> 0 rows                                T8
  lines 55-65   fix entry 5; reconcile 1193 -> matched; timer resets  T9
  lines 67-75   per-envelope notes: wrong then right -> matched       T10
  line 78       reconcile -5 -> 23514 (counted_total >= 0 CHECK)      T11[negative]
  line 79       reconcile {"99":10} -> P0001 envelope 99              T11[unknown]
  line 80       reconcile {"1":"abc"} -> P0001 bad entry              T11[text]
  line 81       reconcile [1,2] -> P0001 not an object                T11[array]
  lines 82-84   INSERT / UPDATE / DELETE reconciliations -> 42501     T12
  lines 86-89   one entry after the match (tea); unverified = it      T13
  lines 90-95   a late entry (bus fare); unverified = 2;
                suspects(25) -> the bus fare                          T13
  line 98       verify_all() empty                                    T15 (healthy)
  lines 100-110 close tenure; opening NOT unverified; T2 reconcile    T14
  line 113      verify_all() empty                                    T14
  lines 114-118 superuser tamper of check #2 -> 1 problem             T15

Rejected statements run in the state the script has when it reaches them, so each assertion
pins the class PostgreSQL really raises: the negative total is the table CHECK 23514
(`CheckViolationError`, `counted_total >= 0`), the bad JSON inputs are function P0001
(`RaiseError`), and the direct table writes are the missing grants 42501
(`InsufficientPrivilegeError`; `labapp` has only SELECT on `reconciliations`, so the privilege
wall fires before the triggers - the D-100 lesson). Dates are relative to the current Sunday
(`s0`); `reconcile` defaults its check date to `current_date`, so `days_since_last_match` is 0.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import asyncpg
import pytest

from tests.conftest import TestDb

POOL, EVENTS = 1, 2
ONE_DAY = timedelta(days=1)


@dataclass
class Status:
    """One `reconciliation_status` row (db/schema.sql:1110-1116)."""

    last_match_id: int | None
    last_match_date: date | None
    last_match_through_entry: int | None
    days_since_last_match: int | None
    entries_since_last_match: int
    latest_attempt_matched: bool | None
    latest_difference: int | None


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


async def reconcile(
    conn: asyncpg.Connection, total: int, note: str, counted: dict[str, int] | None = None
) -> int:
    """`reconcile('treasurer', total, note[, counted])`; returns the check id."""
    if counted is None:
        return int(await conn.fetchval("SELECT reconcile('treasurer', $1, $2)", total, note))
    return int(
        await conn.fetchval(
            "SELECT reconcile('treasurer', $1, $2, $3::jsonb)",
            total,
            note,
            json.dumps(counted),
        )
    )


async def status(conn: asyncpg.Connection) -> Status:
    row = await conn.fetchrow(
        "SELECT last_match_id, last_match_date, last_match_through_entry,"
        " days_since_last_match, entries_since_last_match, latest_attempt_matched,"
        " latest_difference FROM reconciliation_status"
    )
    assert row is not None
    return Status(
        last_match_id=None if row["last_match_id"] is None else int(row["last_match_id"]),
        last_match_date=row["last_match_date"],
        last_match_through_entry=(
            None
            if row["last_match_through_entry"] is None
            else int(row["last_match_through_entry"])
        ),
        days_since_last_match=(
            None if row["days_since_last_match"] is None else int(row["days_since_last_match"])
        ),
        entries_since_last_match=int(row["entries_since_last_match"]),
        latest_attempt_matched=row["latest_attempt_matched"],
        latest_difference=(
            None if row["latest_difference"] is None else int(row["latest_difference"])
        ),
    )


async def unverified(conn: asyncpg.Connection) -> list[tuple[int, str, int, int, str]]:
    """(id, kind, net_effect, size, tag) for every `unverified_entries` row, in id order."""
    rows: list[Any] = await conn.fetch(
        "SELECT id, kind::text AS kind, net_effect, size, tag FROM unverified_entries"
    )
    return [
        (
            int(row["id"]),
            str(row["kind"]),
            int(row["net_effect"]),
            int(row["size"]),
            row["tag"],
        )
        for row in rows
    ]


async def suspects(
    conn: asyncpg.Connection, diff: int, envelope: int | None = None
) -> list[tuple[int, str, int, str]]:
    """(entry_id, kind, effect, why) for `difference_suspects(diff[, envelope])`."""
    if envelope is None:
        rows: list[Any] = await conn.fetch(
            "SELECT entry_id, kind::text AS kind, effect, why FROM difference_suspects($1)",
            diff,
        )
    else:
        rows = await conn.fetch(
            "SELECT entry_id, kind::text AS kind, effect, why FROM difference_suspects($1, $2)",
            diff,
            envelope,
        )
    return [
        (int(row["entry_id"]), str(row["kind"]), int(row["effect"]), str(row["why"]))
        for row in rows
    ]


async def verify_all(conn: asyncpg.Connection) -> list[str]:
    rows: list[Any] = await conn.fetch("SELECT * FROM verify_all()")
    return [str(row["problem"]) for row in rows]


async def start(db: TestDb) -> date:
    """Lines 2-15: tenure T1, pool + Events envelopes, member A, month-1 entries."""
    s0: date = await db.app.fetchval("SELECT sunday_on_or_before(current_date)")
    await db.owner.execute("INSERT INTO tenures(name, opened_on) VALUES ('T1', $1)", s0)
    await db.app.execute(
        "INSERT INTO envelopes(name, is_pool) VALUES ('Unallocated General', true)"
    )
    await db.app.execute("INSERT INTO envelopes(name) VALUES ('Events and Workshops')")
    await db.app.execute("INSERT INTO members(name) VALUES ('A')")
    await enter(db.app, "opening", [(POOL, 1000)], on=s0, note="go-live")
    await enter(db.app, "deposit", [(POOL, 200)], on=s0, source="other", note="sponsor")
    await enter(db.app, "expense", [(POOL, -50)], on=s0, tag="stationery")
    return s0


async def month2(db: TestDb, s0: date) -> None:
    """Lines 24-32: the four month-2 entries (screen total -> 1085)."""
    await enter(
        db.app, "deposit", [(POOL, 100)], on=s0 + 7 * ONE_DAY, source="weekly_fee", member_id=1
    )
    await enter(db.app, "expense", [(POOL, -120)], on=s0 + 8 * ONE_DAY, tag="printing")
    await enter(
        db.app, "transfer", [(POOL, -300), (EVENTS, 300)], on=s0 + 9 * ONE_DAY, note="events money"
    )
    await enter(db.app, "expense", [(EVENTS, -45)], on=s0 + 10 * ONE_DAY, tag="snacks")


async def fix_entry5(db: TestDb, s0: date) -> None:
    """Lines 55-61: reverse the printing expense (120) and re-enter it as 12."""
    printing = await db.app.fetchval(
        "SELECT id FROM ledger_transactions WHERE tag = 'printing' AND kind = 'expense'"
    )
    async with db.app.transaction():
        reversal = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by,"
            " reverses_id, note) VALUES (1, 'reversal', $1::date + $2::int, 'treasurer', $3,"
            " 'amount typo') RETURNING id",
            s0,
            11,
            printing,
        )
        await db.app.execute(
            "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1, 1, 120)",
            reversal,
        )
        replacement = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, tag,"
            " replaces_id, note) VALUES (1, 'expense', $1::date + $2::int, 'treasurer',"
            " 'printing', $3, 'corrected to 12') RETURNING id",
            s0,
            8,
            printing,
        )
        await db.app.execute(
            "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1, 1, -12)",
            replacement,
        )


async def two_months(db: TestDb, s0: date) -> None:
    """The month-1 match (check #1), then month-2's four entries."""
    await reconcile(db.app, 1150, "month 1 matched")
    await month2(db, s0)


async def mismatch(db: TestDb, s0: date) -> int:
    """The month-2 mismatch (check #2): screen 1085 vs counted 1193."""
    return await reconcile(db.app, 1193, "month 2: does not match")


async def fixed_prefix(db: TestDb, s0: date) -> None:
    """Everything through the matched check #3 (last match through entry 9)."""
    await two_months(db, s0)
    await mismatch(db, s0)
    await fix_entry5(db, s0)
    await reconcile(db.app, 1193, "month 2 matched after fixing entry 5")


# ---- the tests ----------------------------------------------------------------


async def test_before_any_check_the_whole_history_is_unverified(db: TestDb) -> None:
    await start(db)

    s = await status(db.app)

    assert s.entries_since_last_match == 3
    assert s.last_match_id is None
    assert s.last_match_date is None


async def test_the_first_reconcile_matches_and_records_the_row(db: TestDb) -> None:
    await start(db)

    check = await reconcile(db.app, 1150, "month 1 matched")

    assert check == 1
    row = await db.app.fetchrow(
        "SELECT through_entry_id, system_total, counted_total, difference, matched"
        " FROM reconciliations WHERE id = $1",
        check,
    )
    assert row is not None
    assert (int(row["through_entry_id"]), int(row["system_total"]), int(row["counted_total"])) == (
        3,
        1150,
        1150,
    )
    assert (int(row["difference"]), row["matched"]) == (0, True)


async def test_after_a_match_the_timer_resets(db: TestDb) -> None:
    await start(db)
    await reconcile(db.app, 1150, "month 1 matched")

    s = await status(db.app)

    assert s.entries_since_last_match == 0
    assert s.days_since_last_match == 0  # reconcile defaults checked_on to current_date
    assert s.latest_attempt_matched is True
    assert s.last_match_id == 1


async def test_a_mismatched_reconcile_records_the_difference(db: TestDb) -> None:
    s0 = await start(db)
    await two_months(db, s0)

    check = await mismatch(db, s0)

    assert check == 2
    row = await db.app.fetchrow(
        "SELECT system_total, counted_total, difference, matched FROM reconciliations"
        " WHERE id = $1",
        check,
    )
    assert row is not None
    assert (int(row["system_total"]), int(row["counted_total"])) == (1085, 1193)
    assert (int(row["difference"]), row["matched"]) == (108, False)


async def test_the_timer_points_at_the_last_match_and_lists_four_entries(db: TestDb) -> None:
    s0 = await start(db)
    await two_months(db, s0)
    await mismatch(db, s0)

    s = await status(db.app)
    assert (s.last_match_id, s.last_match_through_entry) == (1, 3)
    assert s.entries_since_last_match == 4
    assert s.latest_attempt_matched is False
    assert s.latest_difference == 108

    rows = await unverified(db.app)
    assert [(r[0], r[1], r[2], r[3]) for r in rows] == [
        (4, "deposit", 100, 100),
        (5, "expense", -120, 120),
        (6, "transfer", 0, 300),
        (7, "expense", -45, 45),
    ]


@pytest.mark.parametrize(
    ("diff", "entry_id", "effect", "why"),
    [
        (108, 5, -120, "extra zero"),
        (-9, 7, -45, "swapped"),
        (120, 5, -120, "same amount"),
        (240, 5, -120, "wrong direction"),
        (-405, 7, -45, "zero left out"),
    ],
)
async def test_difference_suspects_finds_each_heuristic(
    db: TestDb, diff: int, entry_id: int, effect: int, why: str
) -> None:
    s0 = await start(db)
    await two_months(db, s0)
    await mismatch(db, s0)

    found = await suspects(db.app, diff)

    assert [(f[0], f[2]) for f in found] == [(entry_id, effect)]
    assert why in found[0][3]


async def test_difference_suspects_can_scope_to_one_envelope(db: TestDb) -> None:
    s0 = await start(db)
    await two_months(db, s0)
    await mismatch(db, s0)

    found = await suspects(db.app, -300, envelope=EVENTS)

    assert [(f[0], f[1], f[2]) for f in found] == [(6, "transfer", 300)]


async def test_an_unrecorded_entry_is_not_found(db: TestDb) -> None:
    s0 = await start(db)
    await two_months(db, s0)
    await mismatch(db, s0)

    assert await suspects(db.app, 77) == []


async def test_fixing_the_typo_then_reconciling_matches(db: TestDb) -> None:
    s0 = await start(db)
    await two_months(db, s0)
    await mismatch(db, s0)
    await fix_entry5(db, s0)

    check = await reconcile(db.app, 1193, "month 2 matched after fixing entry 5")

    assert check == 3
    s = await status(db.app)
    assert s.entries_since_last_match == 0
    assert s.latest_attempt_matched is True


async def test_per_envelope_counts_mismatch_on_zero_difference(db: TestDb) -> None:
    s0 = await start(db)
    await fixed_prefix(db, s0)

    wrong = await reconcile(db.app, 1193, "envelope notes", {"1": 948, "2": 245})
    row = await db.app.fetchrow(
        "SELECT difference, matched FROM reconciliations WHERE id = $1", wrong
    )
    assert row is not None
    assert (int(row["difference"]), row["matched"]) == (0, False)
    envelopes = await db.app.fetch(
        "SELECT envelope_id, system_balance, counted FROM reconciliation_envelopes"
        " WHERE reconciliation_id = $1 ORDER BY envelope_id",
        wrong,
    )
    assert [
        (int(r["envelope_id"]), int(r["system_balance"]), int(r["counted"])) for r in envelopes
    ] == [
        (1, 938, 948),
        (2, 255, 245),
    ]

    right = await reconcile(db.app, 1193, "envelope notes fixed", {"1": 938, "2": 255})
    row = await db.app.fetchrow(
        "SELECT difference, matched FROM reconciliations WHERE id = $1", right
    )
    assert row is not None
    assert (int(row["difference"]), row["matched"]) == (0, True)
    s = await status(db.app)
    assert (s.last_match_id, s.entries_since_last_match) == (right, 0)


@pytest.mark.parametrize(
    ("total", "counted", "error", "match"),
    [
        (-5, None, asyncpg.CheckViolationError, "counted_total"),
        (100, {"99": 10}, asyncpg.RaiseError, "envelope 99 does not exist"),
        (100, {"1": "abc"}, asyncpg.RaiseError, "bad entry"),
        (100, [1, 2], asyncpg.RaiseError, "JSON object"),
    ],
)
async def test_the_rejected_reconciles_raise_their_own_errors(
    db: TestDb, total: int, counted: Any, error: type[BaseException], match: str
) -> None:
    await start(db)

    if counted is None:
        with pytest.raises(error, match=match):
            await reconcile(db.app, total, "negative")
    else:
        with pytest.raises(error, match=match):
            await reconcile(db.app, total, "bad", counted)  # type: ignore[arg-type]


async def test_the_reconciliation_tables_are_append_only(db: TestDb) -> None:
    s0 = await start(db)
    await two_months(db, s0)
    await mismatch(db, s0)

    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await db.app.execute(
            "INSERT INTO reconciliations(tenure_id, through_entry_id, checked_on,"
            " system_total, counted_total, difference, matched, recorded_by)"
            " VALUES (1, 1, current_date, 1, 1, 0, true, 'x')"
        )
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await db.app.execute("UPDATE reconciliations SET matched = true WHERE id = 2")
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await db.app.execute("DELETE FROM reconciliations WHERE id = 1")


async def test_a_late_entry_for_an_old_date_still_shows(db: TestDb) -> None:
    s0 = await start(db)
    await fixed_prefix(db, s0)

    await enter(db.app, "expense", [(POOL, -30)], on=s0 + 14 * ONE_DAY, tag="tea")
    assert [(r[0], r[2], r[4]) for r in await unverified(db.app)] == [(10, -30, "tea")]

    await enter(db.app, "expense", [(POOL, -25)], on=s0 + 1 * ONE_DAY, tag="forgotten bus fare")
    assert [(r[0], r[2], r[4]) for r in await unverified(db.app)] == [
        (10, -30, "tea"),
        (11, -25, "forgotten bus fare"),
    ]

    found = await suspects(db.app, 25)
    assert [(f[0], f[2]) for f in found] == [(11, -25)]


async def test_the_carry_over_opening_is_not_unverified_after_close(db: TestDb) -> None:
    s0 = await start(db)
    await fixed_prefix(db, s0)
    await enter(db.app, "expense", [(POOL, -30)], on=s0 + 14 * ONE_DAY, tag="tea")
    await enter(db.app, "expense", [(POOL, -25)], on=s0 + 1 * ONE_DAY, tag="forgotten bus fare")

    await db.app.execute("SELECT close_tenure($1::date + $2::int, 'treasurer', 'T2')", s0, 20)

    # the T2 carry-over opening is NOT unverified; the tea and bus fare still are
    assert [(r[0], r[2], r[4]) for r in await unverified(db.app)] == [
        (10, -30, "tea"),
        (11, -25, "forgotten bus fare"),
    ]

    await enter(db.app, "deposit", [(POOL, 40)], on=s0 + 21 * ONE_DAY, tenure_id=2, source="other")
    check = await reconcile(db.app, 1178, "first match in the new tenure")
    row = await db.app.fetchrow(
        "SELECT tenure_id, system_total, matched FROM reconciliations WHERE id = $1", check
    )
    assert row is not None
    assert (int(row["tenure_id"]), int(row["system_total"]), row["matched"]) == (2, 1178, True)
    s = await status(db.app)
    assert s.entries_since_last_match == 0


async def test_verify_all_is_healthy_then_catches_the_tamper(db: TestDb) -> None:
    s0 = await start(db)
    await two_months(db, s0)
    await mismatch(db, s0)  # check #2, system_total 1085

    assert await verify_all(db.owner) == []

    await db.owner.execute("ALTER TABLE reconciliations DISABLE TRIGGER no_change_rec")
    await db.owner.execute(
        "UPDATE reconciliations SET system_total = system_total + 5,"
        " difference = difference - 5 WHERE id = 2"
    )
    await db.owner.execute("ALTER TABLE reconciliations ENABLE TRIGGER no_change_rec")

    problems = await verify_all(db.owner)
    assert len(problems) == 1
    assert "reconciliation #2" in problems[0]
