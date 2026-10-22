r"""Contract tests for go-live with members who joined years ago (rate dating rules).

Ported from `db/examples/04_fees_existing_members.sql` (TEST-ONLY step, D-045). The behaviour
already exists in `db/schema.sql`, so the tests pass at once.

Coverage proof - every `EXPECT` / `EXPECT FAIL` line of the example:

  line 2        s0 = sunday_on_or_before(current_date)      start() (every test)
  lines 3-4     tenure opens two weeks before s0            start()
  lines 5-9     pool envelope, a member since 2023-01-01,
                rate 20 BDT                                start()
  lines 10-11   EXPECT 2 weeks owed at s0+7, owed 40        test_existing_member_bills_from_
                                                            the_first_rate
  lines 12-13   EXPECT FAIL rate dated inside the open
                tenure but before the current week          test_backdated_rate_inside_the_
                                                            open_tenure_is_rejected
  lines 14-16   EXPECT ok: a rate this Sunday and a future
                Sunday                                     test_latest_rate_for_the_same_
                                                            week_wins
  lines 17-18   EXPECT latest row for the same week wins:
                s0 = 22, s0+7 = 25 -> owed 47              test_latest_rate_for_the_same_
                                                            week_wins

Only the numbers the script states are asserted: the first EXPECT names weeks and owed (not the
balance), the last names weeks and owed. `member_standing()` is read through `who_id = 1`.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import asyncpg
import pytest

from tests.conftest import TestDb


async def start(db: TestDb) -> date:
    """Lines 2-9: a tenure opened two weeks ago, the pool, one old member, rate 20, its period."""
    s0: date = await db.app.fetchval("SELECT sunday_on_or_before(current_date)")
    await db.owner.execute("INSERT INTO tenures(name, opened_on) VALUES ('T1', $1::date - 14)", s0)
    await db.app.execute(
        "INSERT INTO envelopes(name, is_pool) VALUES ('Unallocated General', true)"
    )
    await db.app.execute("INSERT INTO members(name) VALUES ('Old member')")
    await db.app.execute(
        "INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES ($1, 20, 'treasurer')",
        s0,
    )
    await db.app.execute(
        "INSERT INTO membership_periods(member_id, start_date) VALUES (1, '2023-01-01')"
    )
    return s0


async def member_standing_row(db: TestDb, as_of: date) -> Any:
    """The one member's standing row (the script reads weeks_owed and owed)."""
    row = await db.app.fetchrow(
        "SELECT weeks_owed, owed FROM member_standing($1) WHERE who_id = 1", as_of
    )
    assert row is not None
    return row


async def test_existing_member_bills_from_the_first_rate(db: TestDb) -> None:
    """Lines 10-11: two weeks owed at s0+7, 40 BDT - billing starts at the first rate."""
    s0 = await start(db)
    row = await member_standing_row(db, s0 + timedelta(days=7))
    assert (row["weeks_owed"], row["owed"]) == (2, 40)


async def test_backdated_rate_inside_the_open_tenure_is_rejected(db: TestDb) -> None:
    """Lines 12-13: a rate dated last Sunday errors (rate_guard's current-week wall, P0001)."""
    s0 = await start(db)
    with pytest.raises(asyncpg.RaiseError, match="cannot be backdated before the current week"):
        await db.app.execute(
            "INSERT INTO fee_rates(effective_from, amount, recorded_by)"
            " VALUES ($1::date - 7, 25, 'treasurer')",
            s0,
        )


async def test_latest_rate_for_the_same_week_wins(db: TestDb) -> None:
    """Lines 14-18: rates 22 this Sunday and 25 next Sunday give two weeks owed of 47."""
    s0 = await start(db)
    await db.app.execute(
        "INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES ($1, 22, 'treasurer')",
        s0,
    )
    await db.app.execute(
        "INSERT INTO fee_rates(effective_from, amount, recorded_by)"
        " VALUES ($1::date + 7, 25, 'treasurer')",
        s0,
    )
    row = await member_standing_row(db, s0 + timedelta(days=7))
    assert (row["weeks_owed"], row["owed"]) == (2, 47)
