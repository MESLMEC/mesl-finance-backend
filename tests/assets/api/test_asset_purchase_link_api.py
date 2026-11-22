"""Issue #10: a lab-money purchase must name the payment that bought it.

The rule the user approved on 2026-11-02 (issue #10 and its triage report):

- a purchase is one expense + one acquisition + a link between them, entered
  expense first; the lab keeps no taka value for an item, so the link to the
  expense is the only cost trail;
- `source: "purchase"` with no `ledger_transaction_id` is refused by the APP as
  422 `validation_failed` before any SQL (brief Q1=a/Q2=a);
- a link must name a LIVE expense of the open tenure: a missing id answers 422
  `unknown_reference`, and a link that names a deposit, a voided (corrected
  away) expense or an expense of another tenure answers 422
  `validation_failed` (brief Q1=a);
- the event answer returns the link, resolved to the expense that currently
  stands (brief Q2=b);
- a fix keeps the link on BOTH the reversal and the replacement, and the fix
  answer returns it too (brief Q4=b).

Database rules these tests rely on (db/schema.sql, read this session):
- `asset_events.ledger_transaction_id` REFERENCES `ledger_transactions(id)`
  (:669) and may only sit on an `acquired` row (:673);
- `line_guard` (:319-337) refuses a negative line that would drop an envelope
  below zero, so every expense seed needs money in the envelope first;
- `tx_guard` (:294-315) refuses an entry dated before its tenure opened;
- `close_tenure` (:910-938) closes the open tenure and opens the next one on
  close_on + 1; a carry-over `opening` entry is written when the closing
  tenure has lines;
- `fix-amount` writes a reversal plus a replacement; the original becomes
  voided (`entries.is_voided`, :422-424) and leaves `entries_current`
  (:426-430), so the original id names a DEAD expense afterwards.

Anti-vacuous 404 tests (the D-108 (1) lesson): a missing route answers the
same framework 404, so the 404 test below first completes a VALID purchase and
asserts 201 before probing the unknown reference.

The tenure in the `lab` fixture opened on 2026-01-01, so every date below is
on or after it.

Library APIs used, all verified in installed source this session:
- `httpx.AsyncClient.get/post` (httpx 0.28.1, _client.py:1751,1838);
- `asyncpg.Connection.fetchrow/fetchval` (asyncpg-stubs 0.32.0,
  connection.pyi:725,746);
- `pytest.mark.parametrize` (pytest 9.1.1, _pytest/python.py:1231);
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb, idempotent

POOL = 1
EVENT_FIELDS = {
    "id",
    "asset_id",
    "kind",
    "quantity",
    "occurred_on",
    "note",
    "ledger_transaction_id",
}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def asset(client: AsyncClient, auth: dict[str, str], mode: str = "counted") -> dict[str, Any]:
    response = await client.post(
        "/api/v1/assets",
        json={"name": "ESP32 DevKit", "mode": mode, "ownership": "lab"},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()


async def fund(client: AsyncClient, auth: dict[str, str], amount: int = 500) -> int:
    """Put money in the pool (the deposit action, step 6.2); returns the id."""
    response = await client.post(
        "/api/v1/deposits",
        json={"amount": amount, "occurred_on": "2026-02-01", "source": "sponsorship"},
        headers=idempotent(auth, "fund-1-1"),
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def purchase_expense(client: AsyncClient, auth: dict[str, str], amount: int = 300) -> int:
    """Spend money on a component (the expense action, step 6.3); returns the
    expense's id. This is the payment a purchase acquisition must name."""
    await fund(client, auth, amount=amount + 100)
    response = await client.post(
        "/api/v1/expenses",
        json={"amount": amount, "occurred_on": "2026-02-01", "envelope_id": POOL},
        headers=auth,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def event(
    client: AsyncClient, auth: dict[str, str], asset_id: int, kind: str, **overrides: Any
) -> Any:
    body: dict[str, Any] = {"kind": kind, "quantity": 10, "occurred_on": "2026-02-01"}
    body.update(overrides)
    return await client.post(f"/api/v1/assets/{asset_id}/events", json=body, headers=auth)


async def event_count(db: TestDb) -> Any:
    return await db.owner.fetchval("SELECT count(*) FROM asset_events")


async def stored_event(db: TestDb, event_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        "SELECT id, asset_id, kind::text AS kind, quantity, source::text AS source,"
        " ledger_transaction_id FROM asset_events WHERE id = $1",
        event_id,
    )
    assert row is not None
    return dict(row)


# ---- the rule: a purchase names its payment ---------------------------------


async def test_a_purchase_without_a_link_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Brief Q1=a: the app refuses it before any SQL."""
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], "acquired", source="purchase")

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


async def test_a_purchase_with_a_link_is_accepted(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    expense_id = await purchase_expense(client, auth)
    thing = await asset(client, auth)

    response = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        source="purchase",
        ledger_transaction_id=expense_id,
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == EVENT_FIELDS
    assert body["ledger_transaction_id"] == expense_id
    row = await stored_event(lab, int(body["id"]))
    assert row["ledger_transaction_id"] == expense_id


async def test_a_non_purchase_may_omit_the_link(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """An admin-given item has no payment, so it needs no link."""
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], "acquired", source="admin")

    assert response.status_code == 201
    assert response.json()["ledger_transaction_id"] is None


# ---- the link must name a live expense of the open tenure --------------------


async def test_a_link_that_names_a_deposit_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Brief Q1=a: only an expense pays for an item; a deposit is money coming
    IN. (The 9.1 test that linked a deposit and expected 201 is replaced by
    this one - see the issue's triage report.)"""
    deposit_id = await fund(client, auth)
    thing = await asset(client, auth)

    response = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        source="purchase",
        ledger_transaction_id=deposit_id,
    )

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


async def test_a_link_that_names_a_missing_entry_is_unknown_reference(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)

    response = await event(
        client, auth, thing["id"], "acquired", source="purchase", ledger_transaction_id=999999
    )

    assert_problem(response, 422, "unknown_reference")
    assert await event_count(lab) == 0


async def test_a_link_that_names_a_voided_expense_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """A corrected expense leaves the treasurer's list (`entries_current`,
    db/schema.sql:426-430), so its id names a DEAD payment."""
    expense_id = await purchase_expense(client, auth)
    fixed = await client.post(
        f"/api/v1/entries/{expense_id}/fix-amount",
        json={"amount": 250, "occurred_on": "2026-02-01", "note": "typo in the amount"},
        headers=auth,
    )
    assert fixed.status_code == 201
    thing = await asset(client, auth)

    response = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        source="purchase",
        ledger_transaction_id=expense_id,
    )

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


async def test_a_link_to_the_replacement_of_a_fixed_expense_is_accepted(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """The replacement IS the live payment after a correction."""
    expense_id = await purchase_expense(client, auth)
    fixed = await client.post(
        f"/api/v1/entries/{expense_id}/fix-amount",
        json={"amount": 250, "occurred_on": "2026-02-01", "note": "typo in the amount"},
        headers=auth,
    )
    assert fixed.status_code == 201
    replacement_id = int(fixed.json()["id"])
    thing = await asset(client, auth)

    response = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        source="purchase",
        ledger_transaction_id=replacement_id,
    )

    assert response.status_code == 201
    assert response.json()["ledger_transaction_id"] == replacement_id


async def test_a_link_to_an_expense_of_a_closed_tenure_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Brief Q5=a: the payment must belong to the OPEN tenure.

    The event is dated inside the NEW tenure, so the only thing wrong with it
    is the link: `asset_event_guard` (:730-731) would otherwise refuse the
    date first and the answer would be 409 for the wrong reason.
    """
    expense_id = await purchase_expense(client, auth)
    closed = await client.post(
        "/api/v1/tenures/close",
        json={"close_on": "2026-03-01", "next_name": "2026B"},
        headers=auth,
    )
    assert closed.status_code == 201
    thing = await asset(client, auth)

    response = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        occurred_on="2026-03-02",
        source="purchase",
        ledger_transaction_id=expense_id,
    )

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


# ---- the answer carries the link ---------------------------------------------


async def test_the_event_answer_shows_the_link(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    expense_id = await purchase_expense(client, auth)
    thing = await asset(client, auth)

    response = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        source="purchase",
        ledger_transaction_id=expense_id,
    )

    assert response.status_code == 201
    body = response.json()
    assert "ledger_transaction_id" in body
    assert body["ledger_transaction_id"] == expense_id


async def test_the_event_answer_of_a_non_purchase_shows_no_link(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], "acquired", source="admin")

    assert response.status_code == 201
    assert response.json()["ledger_transaction_id"] is None


# ---- a fix keeps the link ----------------------------------------------------


async def test_fixing_a_purchase_keeps_the_link_on_both_rows(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Brief Q4=b / D-135 (3): the reversal AND the replacement carry the
    original's link, so a correction cannot erase the cost trail."""
    expense_id = await purchase_expense(client, auth)
    thing = await asset(client, auth)
    acquired = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    assert acquired.status_code == 201

    fixed = await client.post(
        f"/api/v1/assets/{thing['id']}/events/{acquired.json()['id']}/fix",
        json={"quantity": 8, "occurred_on": "2026-02-01", "note": "typo, should be 8"},
        headers=auth,
    )

    assert fixed.status_code == 201
    body = fixed.json()
    assert body["ledger_transaction_id"] == expense_id
    reversal = await stored_event(lab, int(body["reversal_id"]))
    replacement = await stored_event(lab, int(body["id"]))
    assert reversal["ledger_transaction_id"] == expense_id
    assert replacement["ledger_transaction_id"] == expense_id


async def test_fixing_a_non_purchase_leaves_the_link_empty(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)
    acquired = await event(client, auth, thing["id"], "acquired", source="admin")
    assert acquired.status_code == 201

    fixed = await client.post(
        f"/api/v1/assets/{thing['id']}/events/{acquired.json()['id']}/fix",
        json={"quantity": 1, "occurred_on": "2026-02-01", "note": "typo"},
        headers=auth,
    )

    assert fixed.status_code == 201
    body = fixed.json()
    assert body["ledger_transaction_id"] is None
    assert (await stored_event(lab, int(body["id"])))["ledger_transaction_id"] is None


# ---- the app's refusals do not touch the database ----------------------------


@pytest.mark.parametrize("source", ["admin", "donation", "project_return", "replacement", "other"])
async def test_a_non_purchase_still_needs_no_payment(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], source: str
) -> None:
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], "acquired", source=source)

    assert response.status_code == 201
    assert await event_count(lab) == 1
