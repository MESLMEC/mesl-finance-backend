"""Contract tests for the ledger rules that live INSIDE PostgreSQL.

Ported from the worked example 01_ledger_basics.sql. They pin down what the database guarantees,
so the application layer can rely on it and only has to translate errors. Run these first on a
new Postgres major version (the schema was originally tested on 16; the dev server is 18).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import asyncpg
import pytest

from tests.conftest import TestDb

POOL, EVENTS, ADMIN = 1, 2, 3


async def enter(
    conn: asyncpg.Connection,
    kind: str,
    lines: list[tuple[int, int]],
    *,
    on: date = date(2026, 2, 1),
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


async def balances(conn: asyncpg.Connection) -> dict[int, int]:
    rows = await conn.fetch("SELECT id, balance FROM envelope_balances")
    return {r["id"]: int(r["balance"]) for r in rows}


async def test_deposit_lands_in_the_pool(lab: TestDb) -> None:
    await enter(lab.app, "deposit", [(POOL, 500)], source="other", note="fees")
    assert (await balances(lab.app))[POOL] == 500


async def test_transfer_moves_money_between_envelopes(lab: TestDb) -> None:
    await enter(lab.app, "deposit", [(POOL, 500)], source="other")
    await enter(lab.app, "transfer", [(POOL, -200), (EVENTS, 200)], note="for workshop")
    assert await balances(lab.app) == {POOL: 300, EVENTS: 200, ADMIN: 0}


async def test_an_envelope_can_never_be_overdrawn(lab: TestDb) -> None:
    await enter(lab.app, "deposit", [(POOL, 500)], source="other")
    await enter(lab.app, "transfer", [(POOL, -200), (EVENTS, 200)], note="for workshop")
    await enter(lab.app, "expense", [(EVENTS, -150)])  # events now 50
    with pytest.raises(asyncpg.exceptions.RaiseError, match="below zero"):
        await enter(lab.app, "expense", [(EVENTS, -100)])
    assert (await balances(lab.app))[EVENTS] == 50


async def test_ledger_rows_cannot_be_updated_or_deleted(lab: TestDb) -> None:
    await enter(lab.app, "deposit", [(POOL, 500)], source="other")
    with pytest.raises(asyncpg.PostgresError, match=r"append-only|permission denied"):
        await lab.app.execute("UPDATE ledger_lines SET amount = 999")
    with pytest.raises(asyncpg.PostgresError, match=r"append-only|permission denied"):
        await lab.app.execute("DELETE FROM ledger_transactions")


@pytest.mark.parametrize(
    ("kind", "lines", "cols"),
    [
        ("deposit", [(POOL, -5)], {"source": "other"}),  # a deposit is one positive amount
        ("transfer", [(POOL, -5), (EVENTS, 4)], {"note": "x"}),  # a transfer sums to zero
    ],
)
async def test_badly_shaped_entries_are_rejected_at_commit(
    lab: TestDb, kind: str, lines: list[tuple[int, int]], cols: dict[str, Any]
) -> None:
    await enter(lab.app, "deposit", [(POOL, 500)], source="other")
    with pytest.raises(asyncpg.PostgresError):
        await enter(lab.app, kind, lines, **cols)


async def test_reversal_undoes_an_entry_and_cannot_be_repeated(lab: TestDb) -> None:
    await enter(lab.app, "deposit", [(POOL, 500)], source="other")
    await enter(lab.app, "transfer", [(POOL, -200), (EVENTS, 200)], note="for workshop")
    expense = await enter(lab.app, "expense", [(EVENTS, -150)], tag="catering")

    await enter(lab.app, "reversal", [(EVENTS, 150)], reverses_id=expense, note="typo in amount")
    assert (await balances(lab.app))[EVENTS] == 200

    with pytest.raises(asyncpg.exceptions.UniqueViolationError):
        await enter(lab.app, "reversal", [(EVENTS, 150)], reverses_id=expense, note="again")


async def test_reversal_must_mirror_the_original_exactly(lab: TestDb) -> None:
    deposit = await enter(lab.app, "deposit", [(POOL, 500)], source="other")
    with pytest.raises(asyncpg.exceptions.RaiseError, match="mirror"):
        await enter(lab.app, "reversal", [(POOL, -499)], reverses_id=deposit, note="wrong amount")


async def test_closing_a_tenure_locks_it_and_carries_balances_over(lab: TestDb) -> None:
    await enter(lab.app, "deposit", [(POOL, 500)], source="other")
    new_tenure = await lab.app.fetchval(
        "SELECT close_tenure($1, 'tres', '2026-27')", date(2026, 6, 30)
    )

    assert new_tenure == 2
    assert (await balances(lab.app))[POOL] == 500  # carried over as tenure 2's opening entry
    with pytest.raises(asyncpg.exceptions.RaiseError, match="closed"):
        await enter(
            lab.app, "deposit", [(POOL, 10)], source="other", on=date(2026, 3, 1), tenure_id=1
        )
    assert await lab.owner.fetch("SELECT * FROM verify_all()") == []


async def test_database_clock_runs_on_dhaka_time(db: TestDb) -> None:
    # sunday_on_or_before(current_date) drives fee weeks; a UTC server is wrong 18:00-24:00 BDT
    assert await db.app.fetchval("SHOW timezone") == "Asia/Dhaka"
