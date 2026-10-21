r"""Contract tests for label edits, the limited app role and tamper detection.

Ported from the worked example `db/examples/02_ledger_edits_and_roles.sql`, which says it must run
"in the SAME database right after example 1": every test first replays example 1's successful
steps (helper `example_01`) and then the lines of example 2 that it covers.

Coverage proof for this TEST-ONLY step (the script has no machine-readable `EXPECT` value lines,
so every expectation and every `EXPECT FAIL` marker is mapped here):

  line 2       tenure-2 deposit lookup (\gset)      -> example_01 (returns deposit_2_tx)
  lines 3-4    healthy DB: EXPECT 0 rows             -> test_healthy_database_has_no_problems
  line 5       ledger_checksum(2) as chk_before      -> test_label_edit_keeps_the_checksum
  lines 6-11   A. label edit as app role, logged     -> test_label_edit_is_logged_with_the_actor
  line 13      checksum unchanged by the edit        -> test_label_edit_keeps_the_checksum
  lines 15-19  EXPECT FAIL recorded_by / kind / amount / delete
               -> test_app_role_cannot_change_immutable_fields_or_lines
  lines 20-21  EXPECT FAIL disable triggers / replica mode
               -> test_app_role_cannot_disable_triggers_or_switch_replica_mode
  lines 22-23  EXPECT FAIL label edit in a closed tenure
               -> test_label_edit_in_a_closed_tenure_is_rejected
  lines 24-30  fix amount = reversal + replacement, one transaction
               -> test_fix_amount_is_a_reversal_plus_replacement
  lines 31-33  entries_current and envelope_balances
               -> test_fix_amount_is_a_reversal_plus_replacement
  lines 34-35  app role may close tenure via function
               -> test_tamper_restore_and_close_as_app_role
  lines 36-37  healthy again: EXPECT 0 rows          -> test_tamper_restore_and_close_as_app_role
  lines 38-42  superuser tamper, then verify_integrity()
               -> test_tampering_with_a_closed_tenure_is_detected
  lines 43-49  restore the amount, then close as the app role
               -> test_tamper_restore_and_close_as_app_role
  lines 50-51  envelope_balances and verify_integrity()
               -> test_tamper_restore_and_close_as_app_role

Dates and amounts come from the scripts themselves (example 1 uses fixed 2026 dates), so the
expected balances below are derived from the scripted amounts, not read back from the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import asyncpg
import pytest

from tests.conftest import TestDb

POOL, EVENTS, ADMIN = 1, 2, 3

TENURE_ONE = "2026"
NEXT_TENURE = "2026-27"


@dataclass
class Example01:
    """The state example 1 leaves behind, carrying the ids example 2 needs."""

    deposit_tx: int  # tenure 1: deposit 500 into the pool
    deposit_line: int  # that entry's only ledger line
    expense_tx: int  # tenure 1: expense 150 from events (reversed in the example)
    tenure_2: int  # opened by close_tenure
    carry_over_tx: int  # tenure 2's opening entry
    deposit_2_tx: int  # tenure 2: the deposit the script edits
    deposit_2_line: int  # that entry's only ledger line


async def enter(
    conn: asyncpg.Connection,
    kind: str,
    lines: list[tuple[int, int]],
    *,
    on: date,
    tenure_id: int = 1,
    **cols: Any,
) -> int:
    """Write one ledger entry (header + lines) in ONE database transaction; returns its id."""
    keys = ["tenure_id", "kind", "occurred_on", "recorded_by", *cols]
    values = [tenure_id, kind, on, "tres", *cols.values()]
    placeholders = ",".join(f"${i + 1}" for i in range(len(keys)))
    async with conn.transaction():
        columns = ",".join(keys)
        tx = await conn.fetchval(
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


async def only_line(conn: asyncpg.Connection, tx: int) -> int:
    line: int = await conn.fetchval("SELECT id FROM ledger_lines WHERE transaction_id = $1", tx)
    return line


async def example_01(db: TestDb) -> Example01:
    """Replay example 1's successful steps: the database example 2 expects to run in."""
    await db.owner.execute(
        "INSERT INTO tenures(name, opened_on) VALUES ($1, $2)", TENURE_ONE, date(2026, 1, 1)
    )
    await db.app.execute(
        "INSERT INTO envelopes(name, is_pool) VALUES ('Unallocated General', true)"
    )
    await db.app.execute(
        "INSERT INTO envelopes(name) VALUES ('Events and Workshops'), ('Admin and Misc')"
    )
    await db.app.execute("INSERT INTO cost_centers(name, kind) VALUES ('Workshop 1','event')")

    deposit = await enter(
        db.app, "deposit", [(POOL, 500)], on=date(2026, 2, 1), source="other", note="fees"
    )
    await enter(
        db.app, "transfer", [(POOL, -200), (EVENTS, 200)], on=date(2026, 2, 2), note="for workshop"
    )
    expense = await enter(
        db.app, "expense", [(EVENTS, -150)], on=date(2026, 2, 3), cost_center_id=1, tag="catering"
    )
    await enter(
        db.app,
        "reversal",
        [(EVENTS, 150)],
        on=date(2026, 2, 6),
        cost_center_id=1,
        reverses_id=expense,
        note="typo in amount",
    )

    tenure_2: int = await db.app.fetchval(
        "SELECT close_tenure($1, $2, $3)", date(2026, 6, 30), "tres", NEXT_TENURE
    )
    carry_over: int = await db.app.fetchval(
        "SELECT id FROM ledger_transactions WHERE tenure_id = $1 AND kind = 'opening'", tenure_2
    )
    deposit_2 = await enter(
        db.app, "deposit", [(POOL, 60)], on=date(2026, 7, 5), tenure_id=tenure_2, source="other"
    )
    return Example01(
        deposit_tx=deposit,
        deposit_line=await only_line(db.app, deposit),
        expense_tx=expense,
        tenure_2=tenure_2,
        carry_over_tx=carry_over,
        deposit_2_tx=deposit_2,
        deposit_2_line=await only_line(db.app, deposit_2),
    )


async def fix_amount(db: TestDb, live: Example01) -> tuple[int, int]:
    """The script's fix amount: reversal plus replacement in ONE database transaction."""
    async with db.app.transaction():
        reversal: int = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by,"
            " reverses_id, note) VALUES ($1, 'reversal', $2, $3, $4, $5) RETURNING id",
            live.tenure_2,
            date(2026, 7, 8),
            "treasurer",
            live.deposit_2_tx,
            "amount typo",
        )
        await db.app.execute(
            "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1,$2,$3)",
            reversal,
            POOL,
            -60,
        )
        replacement: int = await db.app.fetchval(
            "INSERT INTO ledger_transactions(tenure_id, kind, occurred_on, recorded_by, source,"
            " replaces_id, note) VALUES ($1, 'deposit', $2, $3, 'other', $4, $5) RETURNING id",
            live.tenure_2,
            date(2026, 7, 5),
            "treasurer",
            live.deposit_2_tx,
            "fees wk 27",
        )
        await db.app.execute(
            "INSERT INTO ledger_lines(transaction_id, envelope_id, amount) VALUES ($1,$2,$3)",
            replacement,
            POOL,
            80,
        )
    return reversal, replacement


async def balances(conn: asyncpg.Connection) -> list[tuple[str, int]]:
    rows: list[Any] = await conn.fetch("SELECT name, balance FROM envelope_balances ORDER BY id")
    return [(r["name"], r["balance"]) for r in rows]


async def problems(conn: asyncpg.Connection) -> list[str]:
    rows: list[Any] = await conn.fetch("SELECT problem FROM verify_integrity()")
    return [r["problem"] for r in rows]


async def test_healthy_database_has_no_problems(db: TestDb) -> None:
    """Lines 3-4: right after example 1 the health check prints 0 rows."""
    await example_01(db)
    assert await problems(db.owner) == []


async def test_label_edit_is_logged_with_the_actor(db: TestDb) -> None:
    """Lines 6-11: the app role fixes note and tag; history names the treasurer, not labapp."""
    live = await example_01(db)
    async with db.app.transaction():
        await db.app.execute("SELECT set_config('app.actor', $1, true)", "treasurer")
        await db.app.execute(
            "UPDATE ledger_transactions SET note = 'fees wk 27', tag = 'fees' WHERE id = $1",
            live.deposit_2_tx,
        )

    header = await db.app.fetchrow(
        "SELECT note, tag FROM ledger_transactions WHERE id = $1", live.deposit_2_tx
    )
    assert header is not None
    assert tuple(header) == ("fees wk 27", "fees")

    rows: list[Any] = await db.app.fetch(
        "SELECT field, old_value, new_value, edited_by FROM ledger_label_edits ORDER BY id"
    )
    assert [tuple(r) for r in rows] == [
        ("note", "", "fees wk 27", "treasurer"),  # example 1 left the note empty
        ("tag", None, "fees", "treasurer"),
    ]


async def test_label_edit_keeps_the_checksum(db: TestDb) -> None:
    """Lines 5 and 13: a label fix never touches the money checksum."""
    live = await example_01(db)
    before = await db.app.fetchval("SELECT ledger_checksum($1)", live.tenure_2)
    await db.app.execute(
        "UPDATE ledger_transactions SET note = 'fees wk 27', tag = 'fees' WHERE id = $1",
        live.deposit_2_tx,
    )
    after = await db.app.fetchval("SELECT ledger_checksum($1)", live.tenure_2)
    assert after == before


IMMUTABLE_ATTEMPTS = [
    ("UPDATE ledger_transactions SET recorded_by = 'someone else' WHERE id = $1", "tx"),
    ("UPDATE ledger_transactions SET kind = 'expense' WHERE id = $1", "tx"),
    ("UPDATE ledger_lines SET amount = 1 WHERE id = $1", "line"),
    ("DELETE FROM ledger_lines WHERE id = $1", "line"),
]


@pytest.mark.parametrize(("statement", "target"), IMMUTABLE_ATTEMPTS)
async def test_app_role_cannot_change_immutable_fields_or_lines(
    db: TestDb, statement: str, target: str
) -> None:
    """Lines 15-19: recorded_by, kind, an amount and a delete are all refused for labapp."""
    live = await example_01(db)
    entry_id = {"tx": live.deposit_2_tx, "line": live.deposit_2_line}[target]
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await db.app.execute(statement, entry_id)

    header = await db.app.fetchrow(
        "SELECT kind, recorded_by FROM ledger_transactions WHERE id = $1", live.deposit_2_tx
    )
    assert header is not None
    assert tuple(header) == ("deposit", "tres")
    assert await only_line(db.app, live.deposit_2_tx) == live.deposit_2_line


TRIGGER_BYPASS_ATTEMPTS = [
    "ALTER TABLE ledger_lines DISABLE TRIGGER ALL",
    "SET session_replication_role = replica",
]


@pytest.mark.parametrize("statement", TRIGGER_BYPASS_ATTEMPTS)
async def test_app_role_cannot_disable_triggers_or_switch_replica_mode(
    db: TestDb, statement: str
) -> None:
    """Lines 20-21: bypassing the guards is refused, and the append-only trigger still fires."""
    live = await example_01(db)
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await db.app.execute(statement)

    # the owner MAY write the rows, so this proves no_change_ln was never switched off
    with pytest.raises(asyncpg.RaiseError, match="append-only"):
        await db.owner.execute(
            "UPDATE ledger_lines SET amount = amount WHERE id = $1", live.deposit_2_line
        )


async def test_label_edit_in_a_closed_tenure_is_rejected(db: TestDb) -> None:
    """Line 23: an entry of the closed tenure 1 cannot be relabelled, and nothing is logged."""
    live = await example_01(db)
    with pytest.raises(asyncpg.RaiseError, match="is closed"):
        async with db.app.transaction():
            await db.app.execute("SELECT set_config('app.actor', $1, true)", "treasurer")
            await db.app.execute(
                "UPDATE ledger_transactions SET note = 'sneaky' WHERE id = $1", live.deposit_tx
            )

    assert await db.app.fetchval("SELECT count(*) FROM ledger_label_edits") == 0
    note = await db.app.fetchval(
        "SELECT note FROM ledger_transactions WHERE id = $1", live.deposit_tx
    )
    assert note == "fees"


async def test_fix_amount_is_a_reversal_plus_replacement(db: TestDb) -> None:
    """Lines 24-33: 60 becomes 80 as one transaction; the list shows one corrected line."""
    live = await example_01(db)
    reversal, replacement = await fix_amount(db, live)

    original = await db.app.fetchrow(
        "SELECT is_voided FROM entries WHERE id = $1", live.deposit_2_tx
    )
    assert original is not None
    assert original["is_voided"] is True
    reversal_row = await db.app.fetchrow(
        "SELECT kind, reverses_id FROM ledger_transactions WHERE id = $1", reversal
    )
    assert reversal_row is not None
    assert tuple(reversal_row) == ("reversal", live.deposit_2_tx)

    rows: list[Any] = await db.app.fetch(
        "SELECT id, kind, note, corrected_from FROM entries_current"
        " WHERE tenure_id = $1 ORDER BY id",
        live.tenure_2,
    )
    assert [tuple(r) for r in rows] == [
        (live.carry_over_tx, "opening", "Carry-over from 2026", None),
        (replacement, "deposit", "fees wk 27", live.deposit_2_tx),
    ]
    assert await balances(db.app) == [
        ("Unallocated General", 380),  # 300 carried over + 60, then -60 + 80
        ("Events and Workshops", 200),
        ("Admin and Misc", 0),
    ]


async def test_tampering_with_a_closed_tenure_is_detected(db: TestDb) -> None:
    """Lines 38-42: the owner edits a closed tenure behind the trigger; two problems show up."""
    live = await example_01(db)
    await fix_amount(db, live)
    await db.owner.execute("ALTER TABLE ledger_lines DISABLE TRIGGER no_change_ln")
    await db.owner.execute(
        "UPDATE ledger_lines SET amount = amount + 1 WHERE id = $1", live.deposit_line
    )
    await db.owner.execute("ALTER TABLE ledger_lines ENABLE TRIGGER no_change_ln")

    assert sorted(await problems(db.owner)) == sorted(
        [
            'tenure "2026": money data differs from the checksum saved at close',
            'tenure "2026-27": opening for "Unallocated General" is 300'
            " but the previous tenure closed with 301",
        ]
    )


async def test_tamper_restore_and_close_as_app_role(db: TestDb) -> None:
    """Lines 34-51: restoring the amount heals the database and labapp may close the tenure."""
    live = await example_01(db)
    await fix_amount(db, live)
    await db.owner.execute("ALTER TABLE ledger_lines DISABLE TRIGGER no_change_ln")
    await db.owner.execute(
        "UPDATE ledger_lines SET amount = amount + 1 WHERE id = $1", live.deposit_line
    )
    await db.owner.execute("ALTER TABLE ledger_lines ENABLE TRIGGER no_change_ln")
    await db.owner.execute("ALTER TABLE ledger_lines DISABLE TRIGGER no_change_ln")
    await db.owner.execute(
        "UPDATE ledger_lines SET amount = amount - 1 WHERE id = $1", live.deposit_line
    )
    await db.owner.execute("ALTER TABLE ledger_lines ENABLE TRIGGER no_change_ln")
    assert await problems(db.owner) == []  # "healthy again", before the close

    new_tenure: int = await db.app.fetchval(
        "SELECT close_tenure($1, $2, $3)", date(2026, 12, 31), "treasurer", "2027"
    )
    assert new_tenure == 3
    assert await balances(db.app) == [
        ("Unallocated General", 380),
        ("Events and Workshops", 200),
        ("Admin and Misc", 0),
    ]
    assert await problems(db.owner) == []
