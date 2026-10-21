"""POST /api/v1/entries/{entry_id}/fix-amount: fix an entry's amount end to end.

Approved contract (step 6.5 brief):
- Q2=a: the route is ``POST /api/v1/entries/{entry_id}/fix-amount``.
- Q1=a: only ``deposit`` and ``expense`` entries are fixable; anything else is
  refused (422 ``validation_failed`` for a non-fixable kind, 409
  ``rule_violation`` for what PostgreSQL itself refuses).
- Q3=c: the body is ``{amount, occurred_on, note}`` and BOTH the reversal and
  the replacement carry the request's ``occurred_on`` (no date is copied from
  the original).
- Q4=c: the response is ``201 {"id": <replacement>, "kind": <original kind>,
  "reversal_id": n, "corrected_from": <original id>, "balance": <envelope
  balance after the write>}``.
- Q5=a: an unknown entry id is 422 ``unknown_reference``; an already-reversed
  entry reaches PostgreSQL's ``reverses_id`` UNIQUE and answers 409 ``unique``.
- Q6=a: the replacement copies the original's tag, cost center, source and
  member; the reversal keeps the request's note, the replacement keeps the
  original's note.

Reverse-and-replace is ONE transaction: the whole entry set is rolled back if
PostgreSQL refuses (the schema's deferred ``check_shape``, db/schema.sql:
340-373, fires at COMMIT).
"""

from datetime import date
from typing import Any

from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

POOL, EVENTS, ADMIN = 1, 2, 3
FIX_DAY = "2026-10-20"


def fix(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"amount": 600, "occurred_on": FIX_DAY, "note": "typo in amount"}
    body.update(overrides)
    return body


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def balances(db: TestDb) -> dict[int, int]:
    rows = await db.owner.fetch("SELECT id, balance FROM envelope_balances")
    return {r["id"]: int(r["balance"]) for r in rows}


async def entry_count(db: TestDb) -> int:
    return int(await db.owner.fetchval("SELECT count(*) FROM ledger_transactions"))


async def fund(client: AsyncClient, auth: dict[str, str], *, envelope_id: int, amount: int) -> int:
    """Put money in through the deposit action (step 6.2); returns the entry id."""
    response = await client.post(
        "/api/v1/deposits",
        json={
            "amount": amount,
            "occurred_on": "2026-02-01",
            "source": "sponsorship",
            "envelope_id": envelope_id,
        },
        headers=auth,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def spend(client: AsyncClient, auth: dict[str, str], *, envelope_id: int, amount: int) -> int:
    """Take money out through the expense action (step 6.3); returns the entry id."""
    response = await client.post(
        "/api/v1/expenses",
        json={"amount": amount, "occurred_on": "2026-02-02", "envelope_id": envelope_id},
        headers=auth,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def fix_entry(
    client: AsyncClient, auth: dict[str, str], entry_id: int, **overrides: Any
) -> Any:
    return await client.post(
        f"/api/v1/entries/{entry_id}/fix-amount", json=fix(**overrides), headers=auth
    )


async def test_fixing_a_deposit_amount_reverses_and_replaces_it(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)

    response = await fix_entry(client, auth, deposit_id, amount=600)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "kind", "reversal_id", "corrected_from", "balance"}
    assert (body["kind"], body["corrected_from"], body["balance"]) == ("deposit", deposit_id, 600)
    assert body["reversal_id"] not in (deposit_id, body["id"])
    assert (await balances(lab)) == {POOL: 600, EVENTS: 0, ADMIN: 0}

    reversal = await lab.owner.fetchrow(
        "SELECT * FROM ledger_transactions WHERE id = $1", body["reversal_id"]
    )
    assert reversal is not None
    assert (reversal["kind"], reversal["reverses_id"], reversal["occurred_on"]) == (
        "reversal",
        deposit_id,
        date(2026, 10, 20),
    )
    assert reversal["note"] == "typo in amount"
    replacement = await lab.owner.fetchrow(
        "SELECT * FROM ledger_transactions WHERE id = $1", body["id"]
    )
    assert replacement is not None
    assert (replacement["kind"], replacement["replaces_id"], replacement["occurred_on"]) == (
        "deposit",
        deposit_id,
        date(2026, 10, 20),
    )
    lines = await lab.owner.fetch(
        "SELECT x.reverses_id, l.envelope_id, l.amount FROM ledger_lines l"
        " JOIN ledger_transactions x ON x.id = l.transaction_id"
        " WHERE x.id IN ($1, $2) ORDER BY x.id",
        body["reversal_id"],
        body["id"],
    )
    assert [(r["reverses_id"], r["envelope_id"], int(r["amount"])) for r in lines] == [
        (deposit_id, POOL, -500),
        (None, POOL, 600),
    ]


async def test_fixing_an_expense_amount_returns_the_difference(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=300)
    expense_id = await spend(client, auth, envelope_id=EVENTS, amount=150)

    response = await fix_entry(client, auth, expense_id, amount=120)

    assert response.status_code == 201
    body = response.json()
    assert (body["kind"], body["corrected_from"], body["balance"]) == (
        "expense",
        expense_id,
        180,
    )
    assert (await balances(lab)) == {POOL: 0, EVENTS: 180, ADMIN: 0}


async def test_the_reversal_mirrors_the_original_lines_exactly(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=300)
    expense_id = await spend(client, auth, envelope_id=EVENTS, amount=150)

    response = await fix_entry(client, auth, expense_id, amount=120)

    assert response.status_code == 201
    row = await lab.owner.fetchrow(
        "SELECT l.envelope_id, l.amount FROM ledger_lines l"
        " JOIN ledger_transactions x ON x.id = l.transaction_id WHERE x.reverses_id = $1",
        expense_id,
    )
    assert row is not None
    assert (row["envelope_id"], int(row["amount"])) == (EVENTS, 150)


async def test_the_replacement_points_at_the_original_and_carries_the_new_amount(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=EVENTS, amount=300)
    expense_id = await spend(client, auth, envelope_id=EVENTS, amount=150)

    response = await fix_entry(client, auth, expense_id, amount=120)

    assert response.status_code == 201
    replacement_id = int(response.json()["id"])
    row = await lab.owner.fetchrow(
        "SELECT x.kind, x.replaces_id, x.occurred_on, l.envelope_id, l.amount"
        " FROM ledger_transactions x JOIN ledger_lines l ON l.transaction_id = x.id"
        " WHERE x.id = $1",
        replacement_id,
    )
    assert row is not None
    assert (row["kind"], row["replaces_id"], row["occurred_on"]) == (
        "expense",
        expense_id,
        date(2026, 10, 20),
    )
    assert (row["envelope_id"], int(row["amount"])) == (EVENTS, -120)


async def test_the_original_and_the_reversal_leave_the_current_list(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)

    response = await fix_entry(client, auth, deposit_id, amount=600)

    assert response.status_code == 201
    body = response.json()
    entries = await lab.owner.fetch("SELECT id, kind, is_voided FROM entries ORDER BY id")
    assert [(r["id"], r["kind"], r["is_voided"]) for r in entries] == [
        (deposit_id, "deposit", True),
        (body["reversal_id"], "reversal", False),
        (body["id"], "deposit", False),
    ]
    current = await lab.owner.fetch("SELECT id, corrected_from FROM entries_current")
    assert [(r["id"], r["corrected_from"]) for r in current] == [(body["id"], deposit_id)]


async def test_the_replacement_keeps_the_originals_labels(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await lab.app.fetchval(
        "INSERT INTO cost_centers (name, kind) VALUES ('Workshop 1', 'event') RETURNING id"
    )
    deposit = await client.post(
        "/api/v1/deposits",
        json={
            "amount": 500,
            "occurred_on": "2026-02-01",
            "source": "sponsorship",
            "note": "sponsor cash",
            "tag": "sponsor",
            "cost_center_id": cost_center,
            "envelope_id": POOL,
        },
        headers=auth,
    )
    assert deposit.status_code == 201
    deposit_id = int(deposit.json()["id"])

    response = await fix_entry(client, auth, deposit_id)

    assert response.status_code == 201
    reversal_id, replacement_id = (
        int(response.json()["reversal_id"]),
        int(response.json()["id"]),
    )
    reversal = await lab.owner.fetchrow(
        "SELECT note, tag, cost_center_id, occurred_on FROM ledger_transactions WHERE id = $1",
        reversal_id,
    )
    assert reversal is not None
    assert (reversal["note"], reversal["tag"], reversal["cost_center_id"]) == (
        "typo in amount",
        "sponsor",
        cost_center,
    )
    replacement = await lab.owner.fetchrow(
        "SELECT note, tag, cost_center_id, source, occurred_on FROM ledger_transactions"
        " WHERE id = $1",
        replacement_id,
    )
    assert replacement is not None
    assert (replacement["note"], replacement["tag"], replacement["cost_center_id"]) == (
        "sponsor cash",
        "sponsor",
        cost_center,
    )
    assert (replacement["source"], replacement["occurred_on"]) == (
        "sponsorship",
        date(2026, 10, 20),
    )


async def test_a_fix_is_recorded_by_the_authenticated_treasurer(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)

    response = await fix_entry(client, auth, deposit_id)

    assert response.status_code == 201
    body = response.json()
    rows = await lab.owner.fetch(
        "SELECT recorded_by FROM ledger_transactions WHERE id = ANY($1::bigint[])",
        [body["reversal_id"], body["id"]],
    )
    assert {r["recorded_by"] for r in rows} == {USERNAME}


async def test_an_unknown_entry_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)

    response = await fix_entry(client, auth, 999999)

    assert_problem(response, 422, "unknown_reference")
    assert "999999" in response.json()["detail"]
    assert await entry_count(lab) == 1  # only the funding deposit
    assert (await balances(lab))[POOL] == 500


async def test_fixing_the_same_entry_twice_is_a_409_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)
    first = await fix_entry(client, auth, deposit_id, amount=600)
    assert first.status_code == 201

    response = await fix_entry(client, auth, deposit_id, amount=700)

    assert_problem(response, 409, "unique")
    assert "reverses_id" in response.json()["detail"]  # the server text names the constraint
    assert await entry_count(lab) == 3
    assert (await balances(lab)) == {POOL: 600, EVENTS: 0, ADMIN: 0}


async def test_fixing_a_transfer_entry_is_a_422_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await fund(client, auth, envelope_id=POOL, amount=500)
    transfer = await client.post(
        "/api/v1/transfers",
        json={
            "amount": 200,
            "occurred_on": "2026-02-02",
            "from_envelope_id": POOL,
            "to_envelope_id": EVENTS,
            "note": "for workshop",
        },
        headers=auth,
    )
    assert transfer.status_code == 201
    transfer_id = int(transfer.json()["id"])

    response = await fix_entry(client, auth, transfer_id, amount=100)

    assert_problem(response, 422, "validation_failed")
    assert await entry_count(lab) == 2
    assert (await balances(lab)) == {POOL: 300, EVENTS: 200, ADMIN: 0}


async def test_a_reversal_that_would_overdraw_is_a_409_and_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    deposit_id = await fund(client, auth, envelope_id=POOL, amount=500)
    moved = await client.post(
        "/api/v1/transfers",
        json={
            "amount": 200,
            "occurred_on": "2026-02-02",
            "from_envelope_id": POOL,
            "to_envelope_id": EVENTS,
            "note": "for workshop",
        },
        headers=auth,
    )
    assert moved.status_code == 201  # the pool now holds 300; reversing 500 would drop it

    response = await fix_entry(client, auth, deposit_id, amount=400)

    assert_problem(response, 409, "rule_violation")
    assert "below zero" in response.json()["detail"].lower()
    assert await entry_count(lab) == 2
    assert (await balances(lab)) == {POOL: 300, EVENTS: 200, ADMIN: 0}


async def test_a_weekly_fee_fix_keeps_the_member_and_moves_the_credits(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await lab.app.fetchval("INSERT INTO members(name) VALUES ('A') RETURNING id")
    sunday = await lab.app.fetchval("SELECT sunday_on_or_before(current_date)")
    await lab.app.execute(
        "INSERT INTO fee_rates (effective_from, amount, recorded_by) VALUES ($1, 20, 'treasurer')",
        sunday,
    )
    await lab.app.execute(
        "INSERT INTO membership_periods (member_id, start_date) VALUES ($1, $2)", member, sunday
    )
    payment = await client.post(
        "/api/v1/deposits",
        json={
            "amount": 100,
            "occurred_on": sunday.isoformat(),
            "source": "weekly_fee",
            "member_id": member,
        },
        headers=auth,
    )
    assert payment.status_code == 201
    deposit_id = int(payment.json()["id"])

    response = await fix_entry(client, auth, deposit_id, amount=60)

    assert response.status_code == 201
    body = response.json()
    assert (body["kind"], body["corrected_from"], body["balance"]) == ("deposit", deposit_id, 60)
    headers = await lab.owner.fetch(
        "SELECT kind, member_id, source FROM ledger_transactions"
        " WHERE id = ANY($1::bigint[]) ORDER BY id",
        [body["reversal_id"], body["id"]],
    )
    assert [(r["kind"], r["member_id"], r["source"]) for r in headers] == [
        ("reversal", member, None),
        ("deposit", member, "weekly_fee"),
    ]
    standing = await lab.owner.fetchrow(
        "SELECT owed, credits, balance FROM member_standing() WHERE who_id = $1", member
    )
    assert standing is not None
    assert (standing["owed"], standing["credits"], standing["balance"]) == (20, 60, 40)


async def test_the_fix_route_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post("/api/v1/entries/1/fix-amount", json=fix())

    assert_problem(response, 401, "invalid_token")
    assert await entry_count(lab) == 0
