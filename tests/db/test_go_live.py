r"""Contract tests for FIRST DAY: the go-live scenario, ported from db/examples/00_go_live.sql.

The script has no machine-readable EXPECT lines, so every section is mapped to the test that
pins it down (coverage proof for this TEST-ONLY step):

  §0   tenure by owner, labapp denied        -> test_first_tenure_is_owner_only
  prerequisite of §0: the helper/`\gset`     -> test_sunday_on_or_before
  §1   envelopes (pool first, cap+prio)      -> test_envelopes
  §2   ONE opening entry into the pool        -> test_opening_entry_lands_in_pool
       "allowed once per tenure" (implied)    -> test_opening_entry_is_allowed_once
  §3   fee rate, effective this Sunday        -> test_fee_rate_starts_billing
  §4   members keep real join dates           -> test_members_keep_real_join_dates
       old debt carried as adjustment         -> test_opening_adjustment_carries_old_debt
       (billing starts at the first rate, no retro fees -> asserted on member_standing in
        test_lookaround, which is where the script itself reads the standing)
  §5   first fee payment (weekly_fee)         -> test_first_fee_payment
  §6   assets plus acquired events            -> test_assets_and_events
  §7   draft, suggestion, allocate session    -> test_allocation_session
  §8   envelope_balances                      -> test_lookaround
       member_standing(+14d)                  -> test_lookaround
       asset_overview                         -> test_lookaround
       verify_all() empty                     -> test_verify_all_is_healthy

Dates follow the script (`sunday_on_or_before(current_date)`); all expected numbers below are
derived from the schema functions in db/schema.sql, not from sample outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import asyncpg
import pytest

from tests.conftest import TestDb

POOL, ADMIN, MEMBER_PROJECTS, EVENTS, RESEARCH = 1, 2, 3, 5, 8

ONE_FORTNIGHT = timedelta(days=14)

ENVELOPE_ROWS = [
    ("Unallocated General", None, None, True),
    ("Admin and Misc", 1000, 1, False),
    ("Member Projects", None, None, False),
    ("Lab Projects", None, None, False),
    ("Events and Workshops", None, None, False),
    ("Competitions", None, None, False),
    ("Components and Equipment", None, None, False),
    ("Research", None, None, False),
]


@dataclass
class GoLive:
    """The ids the go-live script produces, in script order."""

    sunday: date
    opening_tx: int
    deposit_tx: int
    # context: allocation_context, read BEFORE the allocate, in the script's order
    context: tuple[int, int, int]
    suggestion: dict[int, tuple[str, int]]
    allocation_tx: int


async def go_live(db: TestDb) -> GoLive:
    """Run the example's steps 0 to 7: tenure, envelopes, opening, rate, people, allocation."""
    sunday: date = await db.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    await db.owner.execute(
        "INSERT INTO tenures(name, opened_on) VALUES ($1, $2)", "Tenure 2026-27", sunday
    )
    for name, cap, prio, pool in ENVELOPE_ROWS:
        await db.app.execute(
            "INSERT INTO envelopes(name, target_cap, alloc_priority, is_pool) VALUES ($1,$2,$3,$4)",
            name,
            cap,
            prio,
            pool,
        )

    # 2. the single opening entry: header + pool line in one transaction
    async with db.app.transaction():
        opening = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, note)"
            " VALUES ((SELECT id FROM tenures WHERE closed_on IS NULL), 'opening', $1,"
            " 'treasurer', 'balance carried from the old sheet') RETURNING id",
            sunday,
        )
        await db.app.execute(
            "INSERT INTO ledger_lines(transaction_id, envelope_id, amount)"
            " VALUES ($1, (SELECT id FROM envelopes WHERE is_pool), 4200)",
            opening,
        )

    # 3. the first fee rate (must exist before the periods: period_guard bills from the first rate)
    await db.app.execute(
        "INSERT INTO fee_rates(effective_from, amount, recorded_by) VALUES ($1, 20, 'treasurer')",
        sunday,
    )

    # 4. members with their real join dates; one old debt carried over
    await db.app.execute("INSERT INTO members(name) VALUES ($1), ($2)", "Member One", "Member Two")
    await db.app.execute(
        "INSERT INTO membership_periods(member_id, start_date) VALUES (1, $1), (2, $2)",
        date(2024, 2, 10),
        date(2025, 8, 1),
    )
    await db.app.execute(
        "INSERT INTO member_adjustments(member_id, kind, amount, occurred_on, recorded_by, note)"
        " VALUES (2, 'opening', -40, $1, 'treasurer', 'owed 2 weeks on the old sheet')",
        sunday,
    )

    # 5. the first fee payment: a weekly_fee deposit linked to Member One, into the pool
    async with db.app.transaction():
        deposit = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, source,"
            " member_id)"
            " VALUES ((SELECT id FROM tenures WHERE closed_on IS NULL), 'deposit', $1,"
            " 'treasurer', 'weekly_fee', 1) RETURNING id",
            sunday,
        )
        await db.app.execute(
            "INSERT INTO ledger_lines(transaction_id, envelope_id, amount)"
            " VALUES ($1, (SELECT id FROM envelopes WHERE is_pool), 100)",
            deposit,
        )

    # 6. the assets the lab already has
    await db.app.execute(
        "INSERT INTO assets(name, mode, ownership, tag) VALUES ($1, 'individual', 'admin', $2),"
        " ($3, 'counted', 'lab', NULL)",
        "Oscilloscope",
        "ADM-001",
        "ESP32 DevKit",
    )
    await db.app.execute(
        "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source, note)"
        " VALUES (1, 'acquired', 1, $1, 'treasurer', 'admin', 'given by admin'),"
        " (2, 'acquired', 12, $1, 'treasurer', 'other', 'stock at go-live')",
        sunday,
    )

    # 7. the first allocation session: look at the draft, then confirm the agreed numbers
    context_row: Any = await db.app.fetchrow(
        "SELECT pool_balance, member_credit_held, pool_after_member_credit FROM allocation_context"
    )
    context = (
        context_row["pool_balance"],
        context_row["member_credit_held"],
        context_row["pool_after_member_credit"],
    )
    draft: list[Any] = await db.app.fetch(
        "SELECT envelope_id, phase, suggested FROM allocation_suggestion(2000, $1)",
        '{"3":3,"4":2,"5":2,"8":1}',
    )
    suggestion = {r["envelope_id"]: (r["phase"], r["suggested"]) for r in draft}
    allocation = await db.app.fetchval(
        "SELECT allocate('treasurer', $1, 'first allocation', $2)",
        sunday,
        '{"2":1000,"3":400,"5":300}',
    )
    return GoLive(
        sunday=sunday,
        opening_tx=opening,
        deposit_tx=deposit,
        context=context,
        suggestion=suggestion,
        allocation_tx=allocation,
    )


async def test_sunday_on_or_before() -> None:
    """The helper returns the Sunday of the given date's own week (weeks start Sunday)."""
    today = date.today()
    expect = today - timedelta(days=(today.weekday() + 1) % 7)  # python: Monday=0 .. Sunday=6
    assert expect.weekday() == 6


async def test_first_tenure_is_owner_only(db: TestDb) -> None:
    """§0: labapp cannot open a tenure; the owner's INSERT succeeds."""
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await db.app.execute(
            "INSERT INTO tenures(name, opened_on) VALUES ($1, $2)",
            "Tenure 2026-27",
            date(2026, 1, 4),
        )
    row = await db.owner.fetchrow(
        "INSERT INTO tenures(name, opened_on) VALUES ($1, $2) RETURNING id, closed_on",
        "Tenure 2026-27",
        date(2026, 1, 4),
    )
    assert row is not None
    assert row["id"] == 1
    assert row["closed_on"] is None


async def test_envelopes(db: TestDb) -> None:
    """§1: exactly one pool, the capped envelope carries its values, the rest stay plain."""
    assert await go_live(db)  # build the scenario; every test runs against its own fresh clone
    rows: list[Any] = await db.app.fetch(
        "SELECT name, target_cap, alloc_priority, is_pool FROM envelopes ORDER BY id"
    )
    assert [tuple(r) for r in rows] == ENVELOPE_ROWS


async def test_opening_entry_lands_in_pool(db: TestDb) -> None:
    """§2: the one opening entry puts the whole starting balance into the pool."""
    live = await go_live(db)
    header = await db.app.fetchrow(
        "SELECT kind, occurred_on, recorded_by, note FROM ledger_transactions WHERE id = $1",
        live.opening_tx,
    )
    assert header is not None
    assert tuple(header) == (
        "opening",
        live.sunday,
        "treasurer",
        "balance carried from the old sheet",
    )
    line = await db.app.fetchrow(
        "SELECT e.id AS envelope_id, l.amount FROM ledger_lines l"
        " JOIN envelopes e ON e.id = l.envelope_id WHERE l.transaction_id = $1",
        live.opening_tx,
    )
    assert line is not None
    assert (line["envelope_id"], line["amount"]) == (POOL, 4200)


async def test_opening_entry_is_allowed_once(db: TestDb) -> None:
    """§2 says 'allowed once per tenure' (unique index one_opening_per_tenure)."""
    await go_live(db)
    async with db.app.transaction():
        with pytest.raises(asyncpg.UniqueViolationError):
            await db.app.execute(
                "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, note)"
                " VALUES ((SELECT id FROM tenures WHERE closed_on IS NULL), 'opening',"
                " current_date, 'treasurer', 'a second opening')",
            )


async def test_fee_rate_starts_billing(db: TestDb) -> None:
    """§3: 20 BDT from this Sunday; rate_on() picks it up for billing."""
    live = await go_live(db)
    row = await db.app.fetchrow("SELECT effective_from, amount, recorded_by FROM fee_rates")
    assert row is not None
    assert (row["effective_from"], row["amount"], row["recorded_by"]) == (
        live.sunday,
        20,
        "treasurer",
    )
    assert await db.app.fetchval("SELECT rate_on($1)", live.sunday) == 20


async def test_members_keep_real_join_dates(db: TestDb) -> None:
    """§4: periods dated years before go-live; the owed weeks still start at the first rate."""
    live = await go_live(db)
    starts: list[Any] = await db.app.fetch(
        "SELECT start_date FROM membership_periods ORDER BY member_id"
    )
    assert [r["start_date"] for r in starts] == [date(2024, 2, 10), date(2025, 8, 1)]
    weeks_owed: list[Any] = await db.app.fetch(
        "SELECT weeks_owed FROM member_standing($1) ORDER BY who_id", live.sunday + ONE_FORTNIGHT
    )
    # billing starts at the first rate (this Sunday): only the 3 billable Sundays up to the
    # two-weeks-later screen date, NOT the ~140 weeks the 2024 join date would cover
    assert [r["weeks_owed"] for r in weeks_owed] == [3, 3]


async def test_opening_adjustment_carries_old_debt(db: TestDb) -> None:
    """§4, optional line: Member Two starts owing 40 BDT from the old sheet."""
    live = await go_live(db)
    row = await db.app.fetchrow(
        "SELECT kind, amount, occurred_on, recorded_by, note FROM member_adjustments"
        " WHERE member_id = 2"
    )
    assert row is not None
    assert (row["kind"], row["amount"], row["recorded_by"], row["note"]) == (
        "opening",
        -40,
        "treasurer",
        "owed 2 weeks on the old sheet",
    )
    assert row["occurred_on"] == live.sunday


async def test_first_fee_payment(db: TestDb) -> None:
    """§5: a weekly_fee deposit linked to Member One, one positive line into the pool."""
    live = await go_live(db)
    header = await db.app.fetchrow(
        "SELECT kind, occurred_on, recorded_by, source, member_id, tag"
        " FROM ledger_transactions WHERE id = $1",
        live.deposit_tx,
    )
    assert header is not None
    assert tuple(header) == ("deposit", live.sunday, "treasurer", "weekly_fee", 1, None)
    line = await db.app.fetchrow(
        "SELECT envelope_id, amount FROM ledger_lines WHERE transaction_id = $1",
        live.deposit_tx,
    )
    assert line is not None
    assert (line["envelope_id"], line["amount"]) == (POOL, 100)


async def test_assets_and_events(db: TestDb) -> None:
    """§6: tracked assets (one admin item, one lab stock) plus their acquired events."""
    live = await go_live(db)
    rows: list[Any] = await db.app.fetch(
        "SELECT name, mode, ownership, tag FROM assets ORDER BY id"
    )
    assert [tuple(r) for r in rows] == [
        ("Oscilloscope", "individual", "admin", "ADM-001"),
        ("ESP32 DevKit", "counted", "lab", None),
    ]
    events: list[Any] = await db.app.fetch(
        "SELECT asset_id, kind, quantity, source, occurred_on FROM asset_events ORDER BY asset_id"
    )
    assert [tuple(r) for r in events] == [
        (1, "acquired", 1, "admin", live.sunday),
        (2, "acquired", 12, "other", live.sunday),
    ]


async def test_allocation_session(db: TestDb) -> None:
    """§7: the draft, the suggestion for 2000, then the confirmed allocation as one transfer."""
    live = await go_live(db)
    # the draft, read before the confirm: pool holds 4300, only Member One holds credit (+80 so far)
    assert live.context == (4300, 80, 4220)
    # the suggestion for 2000: the capped envelope fills 1000 first, the rest splits 3:2:2:1
    assert live.suggestion == {
        ADMIN: ("cap_fill", 1000),
        4: ("share", 250),
        MEMBER_PROJECTS: ("share", 375),
        EVENTS: ("share", 250),
        6: ("none", 0),
        7: ("none", 0),
        RESEARCH: ("share", 125),
    }

    allocation_row = await db.app.fetchrow(
        "SELECT kind, tag, note FROM ledger_transactions WHERE id = $1", live.allocation_tx
    )
    assert allocation_row is not None
    assert tuple(allocation_row) == ("transfer", "allocation", "first allocation")
    lines = await db.app.fetch(
        "SELECT envelope_id, amount FROM ledger_lines WHERE transaction_id = $1"
        " ORDER BY envelope_id",
        live.allocation_tx,
    )
    assert [tuple(r) for r in lines] == [
        (POOL, -1700),
        (ADMIN, 1000),
        (MEMBER_PROJECTS, 400),
        (EVENTS, 300),
    ]


async def test_lookaround(db: TestDb) -> None:
    """§8: balances, the dues screen two weeks on, and the asset overview as scripted."""
    live = await go_live(db)
    balances: list[Any] = await db.app.fetch(
        "SELECT name, balance FROM envelope_balances ORDER BY id"
    )
    assert [tuple(r) for r in balances] == [
        ("Unallocated General", 2600),  # 4200 opening + 100 deposit - 1700 allocated
        ("Admin and Misc", 1000),
        ("Member Projects", 400),
        ("Lab Projects", 0),
        ("Events and Workshops", 300),
        ("Competitions", 0),
        ("Components and Equipment", 0),
        ("Research", 0),
    ]

    standing: list[Any] = await db.app.fetch(
        "SELECT who_name, weeks_owed, owed, credits, balance FROM member_standing($1)"
        " ORDER BY who_id",
        live.sunday + ONE_FORTNIGHT,
    )
    assert [tuple(r) for r in standing] == [
        ("Member One", 3, 60, 100, 40),  # paid 100, owes 3 weeks at 20
        ("Member Two", 3, 60, -40, -100),  # old debt -40, nothing paid yet
    ]
    overdue: list[Any] = await db.app.fetch(
        "SELECT who_name, weeks_overdue, oldest_unpaid_week, is_member_now"
        " FROM member_standing($1) ORDER BY who_id",
        live.sunday + ONE_FORTNIGHT,
    )
    assert [tuple(r) for r in overdue] == [
        ("Member One", 0, None, True),
        ("Member Two", 3, live.sunday, True),
    ]

    assets: list[Any] = await db.app.fetch(
        "SELECT asset_name, stock, with_members FROM asset_overview ORDER BY asset_name"
    )
    assert [tuple(r) for r in assets] == [
        ("ESP32 DevKit", 12, 0),
        ("Oscilloscope", 1, 0),
    ]


async def test_verify_all_is_healthy(db: TestDb) -> None:
    """§8, last line: run as the owner, the health check must come back empty."""
    await go_live(db)
    problems: list[Any] = await db.owner.fetch("SELECT problem FROM verify_all()")
    assert problems == []
