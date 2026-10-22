r"""Contract tests for members, fee rates, shutdown weeks, payments and dues.

Ported from the worked example `db/examples/03_fees.sql`. The behaviour already exists in
`db/schema.sql`, so every test here passes at once (TEST-ONLY step, D-045).

Coverage proof - every `EXPECT` / `EXPECT FAIL` line of the example, in script order:

  line 2        s0 = sunday_on_or_before(current_date)      start() (every test)
  lines 3-4     tenure T1 opens on s0 (owner only)          start()
  lines 5-7     pool + events envelopes, rate 20 BDT        start()
  lines 9-14    five members, periods for A/B/C/E           start()
  line 15       shutdown for week 3                         start()
  lines 17-25   four lump-sum weekly_fee payments           start()
  lines 27-28   EXPECT A:4wk/80/+20 B:3wk/60/-30            test_standing_at_week_five
                overdue2 oldest=+21 C:2wk/40/-40
                overdue2 oldest=0 D:0/0/+100 E:4wk/80/-30
  lines 30-34   C waiver 40; D refund 60, donation -40      add_adjustments()
  lines 35-36   EXPECT C balance 0, D credits 0 balance 0   test_waiver_and_credit_donation
  lines 38-40   rate 30 from week 4; EXPECT A owed 100
                bal 0; B owed 80 credits 30 bal -50 od 2    test_rate_change_only_affects_
                                                            future_weeks
  lines 42-51   fix B's payment 30 -> 40 (reversal+replace) fix_b_payment()
  line 42       EXPECT B credits 40 balance -40             test_fix_amount_is_a_reversal_
                                                            plus_replacement
  lines 52-53   treasurer list shows one line for B         test_fix_amount_is_a_reversal_
                                                            plus_replacement
  lines 55-59   shutdown undone -> A owes 120, redone 100   test_shutdown_can_be_undone_
                                                            and_redone
  line 62       EXPECT FAIL backdated rate                  test_backdated_rate_is_rejected
  line 63       EXPECT FAIL rate not on a Sunday            test_rate_must_start_on_sunday
  line 64       EXPECT FAIL overlapping membership period   test_overlapping_membership_
                                                            period_is_rejected
  line 65       EXPECT FAIL start-date edit                 test_membership_start_date_is_
                                                            not_editable
  line 66       EXPECT FAIL second end date                 test_membership_can_be_ended_
                                                            only_once
  line 67       EXPECT FAIL delete a period                 test_membership_period_cannot_
                                                            be_deleted
  line 68       EXPECT FAIL negative waiver                 test_waiver_cannot_be_negative
  line 69       EXPECT FAIL waiver without a note           test_waiver_needs_a_note
  lines 70-71   EXPECT FAIL edit/delete an adjustment       test_adjustments_are_append_only
  line 72       EXPECT FAIL weekly_fee deposit, no member   test_weekly_fee_deposit_needs_
                                                            a_member
  line 73       EXPECT FAIL transfer carrying a member      test_transfer_cannot_carry_a_
                                                            member
  lines 74-75   EXPECT FAIL member payment into Events      test_member_payment_must_use_
                                                            the_pool
  line 76       EXPECT FAIL shutdown range not whole weeks  test_shutdown_range_must_be_
                                                            whole_weeks
  lines 77-79   EXPECT FAIL reversal with the wrong member  test_reversal_must_carry_the_
                                                            same_member
  lines 80-81   EXPECT FAIL direct member edit on a payment test_app_role_cannot_edit_a_
                                                            payment_member
  lines 83-84   health: EXPECT 0 rows                       test_healthy_before_close
  lines 86-90   close at s0+34: 5 snapshots, T2 at s0+35    test_close_tenure_snapshots_
                                                            and_next_tenure
  lines 91-92   EXPECT FAIL shutdown in a closed tenure     test_closed_tenure_rejects_
  line 93       EXPECT FAIL rate in a closed tenure            rate_shutdown_and_adjustment
  line 94       EXPECT FAIL end date in a closed tenure     test_closed_tenure_rejects_
  line 95       EXPECT FAIL adjustment in a closed tenure      rate_shutdown_and_adjustment
  line 96       INSERT member F: the section header says
                EXPECT FAIL, but `members` has no tenure
                guard, so it succeeds (approved Q5=a)      test_closed_tenure_rejects_
                                                            rate_shutdown_and_adjustment
  line 97       EXPECT FAIL period starting in the old
                tenure                                      test_closed_tenure_rejects_
                                                            rate_shutdown_and_adjustment
  lines 98-99   ok: F's period from s0+30 in the new tenure test_new_member_billing_starts_
                                                            in_the_new_tenure
  lines 100-101 EXPECT A owed 190 credits 100 bal -90 od 3  test_arrears_carry_over
  lines 103-104 health after close: EXPECT 0 rows           test_healthy_after_close
  lines 105-109 superuser tamper; verify_integrity()        test_tampered_shutdown_of_a_
                                                            closed_tenure_is_detected

Rejected statements run in the state the script has when it reaches them (`script_prefix()`),
so each assertion pins the class PostgreSQL really raises for that line: privilege walls are
SQLSTATE 42501 (`InsufficientPrivilegeError`), trigger refusals P0001 (`RaiseError`), CHECKs
23514 (`CheckViolationError`), the exclusion constraint 23P01 (`ExclusionViolationError`).
Dates follow the script: everything is relative to the current Sunday (`s0`); D-045.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import asyncpg
import pytest

from tests.conftest import TestDb

POOL, EVENTS = 1, 2
ONE_DAY = timedelta(days=1)


@dataclass
class Standing:
    """One `member_standing()` row; only the columns the script states are kept."""

    weeks_owed: int
    owed: int
    credits: int
    balance: int
    weeks_overdue: int
    oldest_unpaid_week: date | None


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


async def standing(conn: asyncpg.Connection, as_of: date) -> dict[str, Standing]:
    """Every member's standing at `as_of`, keyed by member name (the script's ORDER BY 1)."""
    rows: list[Any] = await conn.fetch(
        "SELECT who_name, weeks_owed, owed, credits, balance, weeks_overdue, oldest_unpaid_week"
        " FROM member_standing($1) ORDER BY 1",
        as_of,
    )
    return {
        str(row["who_name"]): Standing(
            weeks_owed=row["weeks_owed"],
            owed=row["owed"],
            credits=row["credits"],
            balance=row["balance"],
            weeks_overdue=row["weeks_overdue"],
            oldest_unpaid_week=row["oldest_unpaid_week"],
        )
        for row in rows
    }


async def start(db: TestDb) -> date:
    """Lines 2-25: tenure, envelopes, rate, members, periods, shutdown week 3, four payments."""
    s0: date = await db.app.fetchval("SELECT sunday_on_or_before(current_date)")
    await db.owner.execute("INSERT INTO tenures(name, opened_on) VALUES ('T1', $1)", s0)
    await db.app.execute(
        "INSERT INTO envelopes(name, is_pool) VALUES ('Unallocated General', true)"
    )
    await db.app.execute("INSERT INTO envelopes(name) VALUES ('Events and Workshops')")
    await db.app.execute(
        "INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES ($1, 20, 'treasurer')",
        s0,
    )
    await db.app.execute("INSERT INTO members(name) VALUES ('A'), ('B'), ('C'), ('D'), ('E')")
    await db.app.execute(
        "INSERT INTO membership_periods(member_id, start_date, end_date) VALUES"
        " (1, $1, NULL), (2, $1::date + 3, NULL), (3, $1, $1::date + 10), (5, $1, NULL)",
        s0,
    )
    await db.app.execute(
        "SELECT set_shutdown($1::date + 14, $1::date + 14, true, 'treasurer', 'campus incident')",
        s0,
    )
    for member_id, amount in ((1, 100), (2, 30), (4, 100), (5, 50)):
        await enter(
            db.app,
            "deposit",
            [(POOL, amount)],
            on=s0 + ONE_DAY,
            source="weekly_fee",
            member_id=member_id,
        )
    return s0


async def add_adjustments(db: TestDb, s0: date) -> None:
    """Lines 30-34: C's waiver, D's refund and D's credit donation."""
    await db.app.execute(
        "INSERT INTO member_adjustments(member_id, kind, amount, occurred_on, recorded_by, note)"
        " VALUES (3, 'waiver', 40, $1::date + 11, 'treasurer', 'left mid-week, forgiven')",
        s0,
    )
    await enter(
        db.app,
        "expense",
        [(POOL, -60)],
        on=s0 + timedelta(days=12),
        member_id=4,
        note="refund of credit",
    )
    await db.app.execute(
        "INSERT INTO member_adjustments(member_id, kind, amount, occurred_on, recorded_by, note)"
        " VALUES (4, 'credit_donation', -40, $1::date + 12, 'treasurer', 'donated to lab')",
        s0,
    )


async def change_rate(db: TestDb, s0: date) -> None:
    """Lines 38-39: the rate becomes 30 BDT from week 4 (s0+21)."""
    await db.app.execute(
        "INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES ($1, 30, 'treasurer')",
        s0 + timedelta(days=21),
    )


async def fix_b_payment(db: TestDb, s0: date) -> int:
    """Lines 42-50: B's 30 payment replaced by 40 (reversal + replacement, ONE transaction)."""
    async with db.app.transaction():
        reversal: int = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by,"
            " reverses_id, member_id, note)"
            " SELECT 1, 'reversal', $1::date + 13, 'treasurer', x.id, 2, 'amount typo'"
            " FROM ledger_transactions x WHERE x.member_id = 2 AND x.kind = 'deposit'"
            " RETURNING id",
            s0,
        )
        await db.app.execute(
            "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1, 1, -30)",
            reversal,
        )
        replacement: int = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, source,"
            " member_id, replaces_id, note)"
            " SELECT 1, 'deposit', $1::date + 1, 'treasurer', 'weekly_fee', 2, x.id,"
            " 'corrected to 40'"
            " FROM ledger_transactions x WHERE x.member_id = 2 AND x.kind = 'deposit'"
            " RETURNING id",
            s0,
        )
        await db.app.execute(
            "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1, 1, 40)",
            replacement,
        )
    return replacement


async def set_week_three(db: TestDb, s0: date, shutdown: bool, reason: str) -> int:
    """Lines 15, 55-59: the shutdown event of week 3 (s0+14)."""
    weeks: int = await db.app.fetchval(
        "SELECT set_shutdown($1::date + 14, $1::date + 14, $2, 'treasurer', $3)",
        s0,
        shutdown,
        reason,
    )
    return weeks


async def close_and_handover(db: TestDb, s0: date) -> int:
    """Lines 88: close T1 at s0+34; the app role opens T2 the next day."""
    next_tenure: int = await db.app.fetchval(
        "SELECT close_tenure($1::date + 34, 'treasurer', 'T2')", s0
    )
    return next_tenure


async def script_prefix(db: TestDb) -> date:
    """Everything the script writes before line 61 (the rejected-mistakes block)."""
    s0 = await start(db)
    await add_adjustments(db, s0)
    await change_rate(db, s0)
    await fix_b_payment(db, s0)
    await set_week_three(db, s0, shutdown=False, reason="was a mistake")
    await set_week_three(db, s0, shutdown=True, reason="confirmed closed")
    return s0


async def test_standing_at_week_five(db: TestDb) -> None:
    """Lines 27-28: the scripted week-5 standings for all five members."""
    s0 = await start(db)
    rows = await standing(db.app, s0 + timedelta(days=28))
    assert set(rows) == {"A", "B", "C", "D", "E"}
    assert (rows["A"].weeks_owed, rows["A"].owed, rows["A"].credits, rows["A"].balance) == (
        4,
        80,
        100,
        20,
    )
    assert (
        rows["B"].weeks_owed,
        rows["B"].owed,
        rows["B"].credits,
        rows["B"].balance,
        rows["B"].weeks_overdue,
        rows["B"].oldest_unpaid_week,
    ) == (3, 60, 30, -30, 2, s0 + timedelta(days=21))
    assert (
        rows["C"].weeks_owed,
        rows["C"].owed,
        rows["C"].credits,
        rows["C"].balance,
        rows["C"].weeks_overdue,
        rows["C"].oldest_unpaid_week,
    ) == (2, 40, 0, -40, 2, s0)
    assert (rows["D"].weeks_owed, rows["D"].owed, rows["D"].credits, rows["D"].balance) == (
        0,
        0,
        100,
        100,
    )
    assert (rows["E"].weeks_owed, rows["E"].owed, rows["E"].credits, rows["E"].balance) == (
        4,
        80,
        50,
        -30,
    )


async def test_waiver_and_credit_donation(db: TestDb) -> None:
    """Lines 35-36: C's balance is 0; D's credits and balance are 0."""
    s0 = await start(db)
    await add_adjustments(db, s0)
    rows = await standing(db.app, s0 + timedelta(days=28))
    assert rows["C"].balance == 0
    assert (rows["D"].credits, rows["D"].balance) == (0, 0)


async def test_rate_change_only_affects_future_weeks(db: TestDb) -> None:
    """Lines 38-40: A owed 100 bal 0; B owed 80 credits 30 bal -50 overdue 2."""
    s0 = await start(db)
    await add_adjustments(db, s0)
    await change_rate(db, s0)
    rows = await standing(db.app, s0 + timedelta(days=28))
    assert (rows["A"].owed, rows["A"].balance) == (100, 0)
    assert (
        rows["B"].owed,
        rows["B"].credits,
        rows["B"].balance,
        rows["B"].weeks_overdue,
    ) == (80, 30, -50, 2)


async def test_fix_amount_is_a_reversal_plus_replacement(db: TestDb) -> None:
    """Lines 42-53: B's credits become 40, and the treasurer's list shows ONE corrected line."""
    s0 = await start(db)
    await add_adjustments(db, s0)
    await change_rate(db, s0)
    original: int = await db.app.fetchval(
        "SELECT id FROM ledger_transactions WHERE member_id = 2 AND kind = 'deposit'"
    )
    await fix_b_payment(db, s0)
    rows = await standing(db.app, s0 + timedelta(days=28))
    assert (rows["B"].credits, rows["B"].balance) == (40, -40)
    entries: list[Any] = await db.app.fetch(
        "SELECT kind, note, corrected_from FROM entries_current WHERE member_id = 2 ORDER BY id"
    )
    assert [tuple(entry) for entry in entries] == [("deposit", "corrected to 40", original)]


async def test_shutdown_can_be_undone_and_redone(db: TestDb) -> None:
    """Lines 55-59: reopening week 3 makes A owe 120; closing it again restores 100."""
    s0 = await start(db)
    await add_adjustments(db, s0)
    await change_rate(db, s0)
    await fix_b_payment(db, s0)
    await set_week_three(db, s0, shutdown=False, reason="was a mistake")
    assert (await standing(db.app, s0 + timedelta(days=28)))["A"].owed == 120
    await set_week_three(db, s0, shutdown=True, reason="confirmed closed")
    assert (await standing(db.app, s0 + timedelta(days=28)))["A"].owed == 100


async def test_backdated_rate_is_rejected(db: TestDb) -> None:
    """Line 62: a rate dated before the current week errors (rate_guard, P0001)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.RaiseError, match="cannot start before this tenure opened"):
        await db.app.execute(
            "INSERT INTO fee_rates(effective_from, amount, recorded_by)"
            " VALUES ($1::date - 7, 25, 'treasurer')",
            s0,
        )


async def test_rate_must_start_on_sunday(db: TestDb) -> None:
    """Line 63: a rate dated on a Thursday errors (the Sunday CHECK, 23514)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.CheckViolationError, match="fee_rates_effective_from_check"):
        await db.app.execute(
            "INSERT INTO fee_rates(effective_from, amount, recorded_by)"
            " VALUES ($1::date + 1, 25, 'treasurer')",
            s0,
        )


async def test_overlapping_membership_period_is_rejected(db: TestDb) -> None:
    """Line 64: a second period for a current member errors (the EXCLUDE constraint, 23P01)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.ExclusionViolationError):
        await db.app.execute(
            "INSERT INTO membership_periods(member_id, start_date) VALUES (1, $1::date + 7)",
            s0,
        )


async def test_membership_start_date_is_not_editable(db: TestDb) -> None:
    """Line 65: the app role has UPDATE only on end_date, so a start-date edit is 42501."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await db.app.execute(
            "UPDATE membership_periods SET start_date = $1::date - 100 WHERE member_id = 2",
            s0,
        )


async def test_membership_can_be_ended_only_once(db: TestDb) -> None:
    """Line 66: moving an already-set end date errors (period_guard, P0001)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.RaiseError, match="can only be ended once"):
        await db.app.execute(
            "UPDATE membership_periods SET end_date = $1::date + 20 WHERE member_id = 3",
            s0,
        )


async def test_membership_period_cannot_be_deleted(db: TestDb) -> None:
    """Line 67: the app role has no DELETE on membership_periods (42501)."""
    await script_prefix(db)
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await db.app.execute("DELETE FROM membership_periods WHERE member_id = 1")


async def test_waiver_cannot_be_negative(db: TestDb) -> None:
    """Line 68: a negative waiver errors (the waiver CHECK, 23514)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.CheckViolationError):
        await db.app.execute(
            "INSERT INTO member_adjustments(member_id, kind, amount, occurred_on, recorded_by,"
            " note) VALUES (1, 'waiver', -5, $1, 'treasurer', 'x')",
            s0,
        )


async def test_waiver_needs_a_note(db: TestDb) -> None:
    """Line 69: a waiver without a note errors (the note CHECK, 23514)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.CheckViolationError):
        await db.app.execute(
            "INSERT INTO member_adjustments(member_id, kind, amount, occurred_on, recorded_by)"
            " VALUES (1, 'waiver', 5, $1, 'treasurer')",
            s0,
        )


async def test_adjustments_are_append_only(db: TestDb) -> None:
    """Lines 70-71: the app role has neither UPDATE nor DELETE here, so both are 42501."""
    await script_prefix(db)
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await db.app.execute("UPDATE member_adjustments SET amount = 1 WHERE id = 1")
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await db.app.execute("DELETE FROM member_adjustments WHERE id = 1")


async def test_weekly_fee_deposit_needs_a_member(db: TestDb) -> None:
    """Line 72: a weekly_fee deposit with no member errors (fee_needs_member, 23514)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.CheckViolationError, match="fee_needs_member"):
        await db.app.execute(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, source)"
            " VALUES (1, 'deposit', $1, 'treasurer', 'weekly_fee')",
            s0,
        )


async def test_transfer_cannot_carry_a_member(db: TestDb) -> None:
    """Line 73: a transfer linked to a member errors (member_link_kinds, 23514)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.CheckViolationError, match="member_link_kinds"):
        await db.app.execute(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, member_id,"
            " note) VALUES (1, 'transfer', $1, 'treasurer', 1, 'x')",
            s0,
        )


async def test_member_payment_must_use_the_pool(db: TestDb) -> None:
    """Lines 74-75: a member-linked deposit into Events errors at COMMIT (P0001)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.RaiseError, match="through the Unallocated General pool"):
        await enter(
            db.app,
            "deposit",
            [(EVENTS, 20)],
            on=s0 + timedelta(days=2),
            source="weekly_fee",
            member_id=1,
        )


async def test_shutdown_range_must_be_whole_weeks(db: TestDb) -> None:
    """Line 76: a shutdown range that is not Sunday-to-Sunday errors (P0001)."""
    s0 = await script_prefix(db)
    with pytest.raises(asyncpg.RaiseError, match="weeks start on Sunday"):
        await db.app.execute(
            "SELECT set_shutdown($1::date + 1, $1::date + 7, true, 'treasurer')", s0
        )


async def test_reversal_must_carry_the_same_member(db: TestDb) -> None:
    """Lines 77-79: reversing A's payment while naming member 2 errors (tx_guard, P0001)."""
    s0 = await script_prefix(db)
    original: int = await db.app.fetchval(
        "SELECT id FROM ledger_transactions WHERE member_id = 1 AND kind = 'deposit'"
    )
    with pytest.raises(asyncpg.RaiseError, match="same member as the original"):
        async with db.app.transaction():
            reversal: int = await db.app.fetchval(
                "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by,"
                " reverses_id, member_id, note)"
                " VALUES (1, 'reversal', $1::date + 5, 'treasurer', $2, 2, 'oops') RETURNING id",
                s0,
                original,
            )
            await db.app.execute(
                "INSERT INTO ledger_lines(transaction_id, envelope_id, amount)"
                " VALUES ($1, 1, -100)",
                reversal,
            )


async def test_app_role_cannot_edit_a_payment_member(db: TestDb) -> None:
    """Lines 80-81: member_id is not in the app role's column grant, so the edit is 42501."""
    await script_prefix(db)
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await db.app.execute(
            "UPDATE ledger_transactions SET member_id = 2 WHERE member_id = 1 AND kind = 'deposit'"
        )


async def test_healthy_before_close(db: TestDb) -> None:
    """Lines 83-84: verify_integrity() finds nothing before the tenure is closed."""
    await script_prefix(db)
    problems: list[Any] = await db.app.fetch("SELECT problem FROM verify_integrity()")
    assert problems == []


async def test_close_tenure_snapshots_and_next_tenure(db: TestDb) -> None:
    """Lines 86-90: closing at s0+34 saves 5 member snapshots and opens T2 on s0+35."""
    s0 = await script_prefix(db)
    next_tenure = await close_and_handover(db, s0)
    assert next_tenure == 2
    snapshots: int = await db.app.fetchval("SELECT count(*) FROM tenure_member_snapshots")
    assert snapshots == 5
    rows: list[Any] = await db.app.fetch(
        "SELECT name, opened_on - $1::date AS opened_day, closed_on - $1::date AS closed_day"
        " FROM tenures ORDER BY id",
        s0,
    )
    assert [tuple(row) for row in rows] == [("T1", 0, 34), ("T2", 35, None)]


async def test_closed_tenure_rejects_rate_shutdown_and_adjustment(db: TestDb) -> None:
    """Lines 91-97: after close, four writes are refused and F's old-tenure period is too."""
    s0 = await script_prefix(db)
    await close_and_handover(db, s0)
    with pytest.raises(asyncpg.RaiseError, match="belongs to a closed tenure"):
        await db.app.execute(
            "SELECT set_shutdown($1::date + 21, $1::date + 21, true, 'treasurer')", s0
        )
    with pytest.raises(asyncpg.RaiseError, match="cannot start before this tenure opened"):
        await db.app.execute(
            "INSERT INTO fee_rates(effective_from, amount, recorded_by)"
            " VALUES ($1::date + 28, 99, 'treasurer')",
            s0,
        )
    with pytest.raises(asyncpg.RaiseError, match="end date is inside a closed tenure"):
        await db.app.execute(
            "UPDATE membership_periods SET end_date = $1::date + 30 WHERE member_id = 1", s0
        )
    with pytest.raises(asyncpg.RaiseError, match="cannot be dated inside a closed tenure"):
        await db.app.execute(
            "INSERT INTO member_adjustments(member_id, kind, amount, occurred_on, recorded_by,"
            " note) VALUES (1, 'waiver', 20, $1::date + 30, 'treasurer', 'late')",
            s0,
        )
    member_f: int = await db.app.fetchval("INSERT INTO members(name) VALUES ('F') RETURNING id")
    assert member_f == 6
    with pytest.raises(asyncpg.RaiseError, match="would owe weeks inside a closed tenure"):
        await db.app.execute(
            "INSERT INTO membership_periods(member_id, start_date) VALUES (6, $1::date + 20)", s0
        )


async def test_new_member_billing_starts_in_the_new_tenure(db: TestDb) -> None:
    """Lines 98-99: F's period dated s0+30 is accepted and bills from the new tenure."""
    s0 = await script_prefix(db)
    await close_and_handover(db, s0)
    await db.app.execute("INSERT INTO members(name) VALUES ('F')")
    await db.app.execute(
        "INSERT INTO membership_periods(member_id, start_date) VALUES (6, $1::date + 30)", s0
    )
    row = await db.app.fetchrow("SELECT start_date FROM membership_periods WHERE member_id = 6")
    assert row is not None
    assert row["start_date"] == s0 + timedelta(days=30)


async def test_arrears_carry_over(db: TestDb) -> None:
    """Lines 100-101: at s0+49 A owes 190, has 100 credit, balance -90, 3 weeks overdue."""
    s0 = await script_prefix(db)
    await close_and_handover(db, s0)
    await db.app.execute("INSERT INTO members(name) VALUES ('F')")
    await db.app.execute(
        "INSERT INTO membership_periods(member_id, start_date) VALUES (6, $1::date + 30)", s0
    )
    member_a = (await standing(db.app, s0 + timedelta(days=49)))["A"]
    assert (member_a.owed, member_a.credits, member_a.balance, member_a.weeks_overdue) == (
        190,
        100,
        -90,
        3,
    )


async def test_healthy_after_close(db: TestDb) -> None:
    """Lines 103-104: verify_integrity() is empty after the close and the new period."""
    s0 = await script_prefix(db)
    await close_and_handover(db, s0)
    await db.app.execute("INSERT INTO members(name) VALUES ('F')")
    await db.app.execute(
        "INSERT INTO membership_periods(member_id, start_date) VALUES (6, $1::date + 30)", s0
    )
    problems: list[Any] = await db.app.fetch("SELECT problem FROM verify_integrity()")
    assert problems == []


async def test_tampered_shutdown_of_a_closed_tenure_is_detected(db: TestDb) -> None:
    """Lines 105-109: a superuser marking a closed week as shutdown changes A, B and E dues."""
    s0 = await script_prefix(db)
    await close_and_handover(db, s0)
    await db.owner.execute("ALTER TABLE shutdown_events DISABLE TRIGGER shutdown_guard")
    await db.owner.execute(
        "INSERT INTO shutdown_events(week_start, is_shutdown, recorded_by)"
        " VALUES ($1::date + 21, true, 'sneaky')",
        s0,
    )
    await db.owner.execute("ALTER TABLE shutdown_events ENABLE TRIGGER shutdown_guard")
    rows: list[Any] = await db.app.fetch("SELECT problem FROM verify_integrity()")
    problems = [row["problem"] for row in rows]
    assert len(problems) == 3
    assert all("dues of" in problem for problem in problems)
    for name in ("A", "B", "E"):
        assert any(f'dues of "{name}"' in problem for problem in problems)
