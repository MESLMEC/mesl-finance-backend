"""API tests for the nine asset event kinds (roadmap step 9.1).

Approved brief answers this session: Q3=a ONE route
`POST /api/v1/assets/{asset_id}/events` with `kind` in the body; Q4=a the app
requires a strict positive whole `quantity` for every kind except
`correction`, which may be negative or positive; Q5=a the kind-shape rules are
refused by the APP as 422 `validation_failed` before SQL (a deviation from the
brief's earlier item 30, which had predicted 409 for a correction with a
member - Q5=a, approved after the test list, supersedes it); Q6=a an unknown
asset in the URL is 404 `not_found` naming the id (D-108); Q7=a an unknown
member or ledger transaction in the body answers 422 `unknown_reference`
through the foreign key (D-110); Q8=a 201
`{"id","asset_id","kind","quantity","occurred_on","note"}` - no counts, 9.3
owns the reads; Q9=a `ledger_transaction_id` is an optional body field.

Issue #10 (2026-11-02) changes two of those answers:
- Q9=a becomes: `ledger_transaction_id` is optional in general, but a
  `source: "purchase"` REQUIRES it - the lab keeps no taka value for an item,
  so the link to the expense is the only cost trail. The refusals and the
  other link rules live in tests/assets/api/test_asset_purchase_link_api.py;
- Q8=a becomes: the event answer also carries `ledger_transaction_id`, so
  EVENT_FIELDS below has seven keys.

The purchase seeds in this file now name a real expense (the `purchase_expense`
helper: a deposit, then an expense on the pool) instead of pretending a
purchase happened without a payment. The refusal tests use `source: "admin"`
where money is not the subject of the test, so they still fail for their own
reason.

Database rules these tests rely on (db/schema.sql, read this session):
- `asset_event_guard` (:726-752): no event before the tenure opened ("events
  cannot be dated inside a closed tenure", P0001 -> 409 `rule_violation`; the
  message does NOT contain "before this tenure opened", so it is NOT the
  DateBeforeTenure rule at error_mapping.py:23); an individual asset moves one
  unit at a time; lending needs a member who currently holds a period;
  reversal mirroring is 9.2's;
- `asset_bucket_check` (:754-775): the stock/damaged/lost/scrapped/exchanged
  and per-member held floors, and "an individually tracked asset can only
  exist once" (all P0001 -> 409 `rule_violation`);
- `asset_event_effects` (:696-714) is what the count assertions read:
  acquired/returned/repaired/correction add to stock, lent/damaged-with-
  member/lost-with-member move held, damaged/lost move stock (no member),
  repaired moves damaged back, scrapped/exchanged never touch stock;
- `labapp` may INSERT asset_events (:1194) and UPDATE only note,
  cost_center_id, occurred_on (:1200).

The tenure in the `lab` fixture opened on 2026-01-01, so every date below is
on or after it; the borrower starts a period on 2026-01-01, which
`asset_event_guard`'s current-member check requires for `lent`.

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

from tests.conftest import USERNAME, TestDb, idempotent

EVENT_FIELDS = {
    "id",
    "asset_id",
    "kind",
    "quantity",
    "occurred_on",
    "note",
    "ledger_transaction_id",
}
BUCKET_KEYS = ("stock", "damaged", "lost", "scrapped", "exchanged", "held")


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


async def purchase_expense(client: AsyncClient, auth: dict[str, str], amount: int = 300) -> int:
    """Spend money on a component (the expense action, step 6.3); returns the
    expense's id. Issue #10: a purchase acquisition names this payment."""
    await client.post(
        "/api/v1/deposits",
        json={"amount": amount + 100, "occurred_on": "2026-02-01", "source": "sponsorship"},
        headers=idempotent(auth, "seed-1-1"),
    )
    response = await client.post(
        "/api/v1/expenses",
        json={"amount": amount, "occurred_on": "2026-02-01", "envelope_id": 1},
        headers=auth,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def borrower(
    client: AsyncClient, auth: dict[str, str], name: str = "Ayesha"
) -> dict[str, Any]:
    member = await client.post("/api/v1/members", json={"name": name}, headers=auth)
    assert member.status_code == 201
    started = await client.post(
        f"/api/v1/members/{member.json()['id']}/periods/start",
        json={"start_date": "2026-01-01"},
        headers=auth,
    )
    assert started.status_code == 201
    return member.json()


def event_body(kind: str, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "kind": kind,
        "quantity": 10,
        "occurred_on": "2026-02-01",
    }
    body.update(overrides)
    return body


async def event(
    client: AsyncClient, auth: dict[str, str], asset_id: int, kind: str, **overrides: Any
) -> Any:
    return await client.post(
        f"/api/v1/assets/{asset_id}/events", json=event_body(kind, **overrides), headers=auth
    )


async def buckets(db: TestDb, asset_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        "SELECT coalesce(sum(stock_d), 0) AS stock, coalesce(sum(damaged_d), 0) AS damaged,"
        " coalesce(sum(lost_d), 0) AS lost, coalesce(sum(scrapped_d), 0) AS scrapped,"
        " coalesce(sum(exchanged_d), 0) AS exchanged, coalesce(sum(held_d), 0) AS held"
        " FROM asset_event_effects WHERE asset_id = $1",
        asset_id,
    )
    assert row is not None
    return {key: row[key] for key in BUCKET_KEYS}


async def held_by(db: TestDb, asset_id: int, member_id: int) -> Any:
    return await db.owner.fetchval(
        "SELECT coalesce(sum(held_d), 0) FROM asset_event_effects"
        " WHERE asset_id = $1 AND member_id = $2",
        asset_id,
        member_id,
    )


async def stored_event(db: TestDb, event_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        "SELECT id, asset_id, kind::text AS kind, quantity, occurred_on, note,"
        " source::text AS source, member_id, ledger_transaction_id, recorded_by"
        " FROM asset_events WHERE id = $1",
        event_id,
    )
    assert row is not None
    answer = dict(row)
    answer["occurred_on"] = answer["occurred_on"].isoformat()
    return answer


async def event_count(db: TestDb) -> Any:
    return await db.owner.fetchval("SELECT count(*) FROM asset_events")


# ---- 201 lifecycles (one test per kind; counts read from the DB) -------------


async def test_acquired_with_source_and_its_purchase_link_is_stored(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Issue #10: a purchase names the EXPENSE that paid for it (the 9.1
    version of this test linked a deposit and expected 201; that is now a
    refusal - see tests/assets/api/test_asset_purchase_link_api.py)."""
    thing = await asset(client, auth)
    expense_id = await purchase_expense(client, auth)

    linked = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    assert linked.status_code == 201
    body = linked.json()
    assert set(body) == EVENT_FIELDS
    assert (
        body["asset_id"],
        body["kind"],
        body["quantity"],
        body["occurred_on"],
        body["note"],
    ) == (
        thing["id"],
        "acquired",
        10,
        "2026-02-01",
        "",
    )
    row = await stored_event(lab, body["id"])
    assert (row["kind"], row["source"], row["member_id"], row["recorded_by"]) == (
        "acquired",
        "purchase",
        None,
        USERNAME,
    )
    assert row["ledger_transaction_id"] == expense_id

    plain = await event(client, auth, thing["id"], "acquired", source="admin", quantity=1)
    assert plain.status_code == 201
    row = await stored_event(lab, plain.json()["id"])
    assert row["ledger_transaction_id"] is None


async def test_lend_then_return_moves_the_held_count(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)
    person = await borrower(client, auth)
    expense_id = await purchase_expense(client, auth)
    acquired = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        quantity=4,
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    assert acquired.status_code == 201

    lent = await event(client, auth, thing["id"], "lent", quantity=2, member_id=person["id"])
    assert lent.status_code == 201
    assert set(lent.json()) == EVENT_FIELDS
    assert lent.json()["kind"] == "lent"
    assert await buckets(lab, thing["id"]) == {
        "stock": 2,
        "damaged": 0,
        "lost": 0,
        "scrapped": 0,
        "exchanged": 0,
        "held": 2,
    }
    assert await held_by(lab, thing["id"], person["id"]) == 2

    returned = await event(
        client, auth, thing["id"], "returned", quantity=1, member_id=person["id"]
    )
    assert returned.status_code == 201
    assert (await buckets(lab, thing["id"]))["held"] == 1
    assert await held_by(lab, thing["id"], person["id"]) == 1


async def test_damaged_by_a_member_moves_held_to_damaged(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)
    person = await borrower(client, auth)
    expense_id = await purchase_expense(client, auth)
    await event(
        client,
        auth,
        thing["id"],
        "acquired",
        quantity=4,
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    lent = await event(client, auth, thing["id"], "lent", quantity=2, member_id=person["id"])
    assert lent.status_code == 201

    response = await event(
        client,
        auth,
        thing["id"],
        "damaged",
        quantity=1,
        member_id=person["id"],
        note="burnt, reverse polarity",
    )

    assert response.status_code == 201
    assert await buckets(lab, thing["id"]) == {
        "stock": 2,
        "damaged": 1,
        "lost": 0,
        "scrapped": 0,
        "exchanged": 0,
        "held": 1,
    }
    assert await held_by(lab, thing["id"], person["id"]) == 1


async def test_lost_from_stock_and_scrapped_from_damaged(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)
    expense_id = await purchase_expense(client, auth)
    await event(
        client,
        auth,
        thing["id"],
        "acquired",
        quantity=5,
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    lost = await event(client, auth, thing["id"], "lost", quantity=1, note="missing after workshop")
    assert lost.status_code == 201
    damaged = await event(client, auth, thing["id"], "damaged", quantity=1, note="dead display")
    assert damaged.status_code == 201

    scrapped = await event(client, auth, thing["id"], "scrapped", quantity=1, note="not repairable")

    assert scrapped.status_code == 201
    assert await buckets(lab, thing["id"]) == {
        "stock": 3,
        "damaged": 0,
        "lost": 1,
        "scrapped": 1,
        "exchanged": 0,
        "held": 0,
    }


async def test_repaired_moves_damaged_back_to_stock(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)
    expense_id = await purchase_expense(client, auth)
    await event(
        client,
        auth,
        thing["id"],
        "acquired",
        quantity=4,
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    damaged = await event(client, auth, thing["id"], "damaged", quantity=1, note="overheated")
    assert damaged.status_code == 201
    assert await buckets(lab, thing["id"]) == {
        "stock": 3,
        "damaged": 1,
        "lost": 0,
        "scrapped": 0,
        "exchanged": 0,
        "held": 0,
    }

    response = await event(client, auth, thing["id"], "repaired", quantity=1)

    assert response.status_code == 201
    assert await buckets(lab, thing["id"]) == {
        "stock": 4,
        "damaged": 0,
        "lost": 0,
        "scrapped": 0,
        "exchanged": 0,
        "held": 0,
    }


async def test_exchanged_never_touches_stock(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`asset_event_effects` (:696-714): scrapped and exchanged add 0 to stock."""
    thing = await asset(client, auth)
    expense_id = await purchase_expense(client, auth)
    await event(
        client,
        auth,
        thing["id"],
        "acquired",
        quantity=2,
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    damaged = await event(client, auth, thing["id"], "damaged", quantity=1, note="dead display")
    assert damaged.status_code == 201

    response = await event(
        client,
        auth,
        thing["id"],
        "exchanged",
        quantity=1,
        note="sent to admin for replacement",
    )

    assert response.status_code == 201
    assert await buckets(lab, thing["id"]) == {
        "stock": 1,
        "damaged": 0,
        "lost": 0,
        "scrapped": 0,
        "exchanged": 1,
        "held": 0,
    }


async def test_a_correction_counts_the_physical_count_difference(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)
    expense_id = await purchase_expense(client, auth)
    await event(
        client,
        auth,
        thing["id"],
        "acquired",
        quantity=5,
        source="purchase",
        ledger_transaction_id=expense_id,
    )

    down = await event(
        client, auth, thing["id"], "correction", quantity=-1, note="physical count found 5"
    )
    assert down.status_code == 201
    assert (await buckets(lab, thing["id"]))["stock"] == 4

    up = await event(
        client, auth, thing["id"], "correction", quantity=2, note="two units resurfaced"
    )
    assert up.status_code == 201
    assert (await buckets(lab, thing["id"]))["stock"] == 6


# ---- app refusals: 422 validation_failed (Q4=a / Q5=a) -----------------------


@pytest.mark.parametrize("kind", ["lent", "returned"])
async def test_lending_and_returning_need_a_member(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], kind: str
) -> None:
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], kind, quantity=1)

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


@pytest.mark.parametrize(
    ("kind", "extra"),
    [
        ("acquired", {"source": "admin"}),
        ("repaired", {}),
        ("scrapped", {"note": "not repairable"}),
        ("exchanged", {"note": "sent to admin"}),
        ("correction", {"note": "count 5"}),
    ],
)
async def test_the_other_kinds_take_no_member(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], kind: str, extra: dict[str, Any]
) -> None:
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], kind, quantity=1, member_id=1, **extra)

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


async def test_acquired_needs_a_source(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], "acquired", quantity=1)

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


@pytest.mark.parametrize("kind", ["repaired", "damaged"])
async def test_the_other_kinds_take_no_source(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], kind: str
) -> None:
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], kind, quantity=1, source="purchase", note="n")

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


@pytest.mark.parametrize("kind", ["damaged", "lost", "scrapped", "exchanged", "correction"])
@pytest.mark.parametrize("note", ["", "   "])
async def test_a_blank_note_is_refused_on_the_kinds_that_need_one(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], kind: str, note: str
) -> None:
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], kind, quantity=1, note=note)

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


async def test_a_zero_quantity_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], "acquired", quantity=0, source="admin")

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


@pytest.mark.parametrize("kind", ["acquired", "lent"])
async def test_a_negative_quantity_is_only_for_a_correction(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], kind: str
) -> None:
    thing = await asset(client, auth)

    body: dict[str, Any] = {"kind": kind, "quantity": -1, "occurred_on": "2026-02-01"}
    if kind == "acquired":
        body["source"] = "admin"
    else:
        body["member_id"] = 1
    response = await client.post(f"/api/v1/assets/{thing['id']}/events", json=body, headers=auth)

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 0


# ---- framework answers -------------------------------------------------------


@pytest.mark.parametrize("quantity", [10.5, True, "10"])
async def test_a_non_whole_quantity_is_a_validation_error(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], quantity: Any
) -> None:
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], "acquired", quantity=quantity, source="admin")

    assert_problem(response, 422, "validation_error")
    assert await event_count(lab) == 0


async def test_a_non_numeric_asset_id_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/assets/abc/events",
        json=event_body("acquired", source="admin"),
        headers=auth,
    )

    assert_problem(response, 422, "validation_error")


async def test_recording_an_event_without_a_token_is_401(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post(
        "/api/v1/assets/1/events", json=event_body("acquired", source="admin")
    )

    assert_problem(response, 401, "invalid_token")
    assert await event_count(lab) == 0


# ---- database rules: 409 rule_violation --------------------------------------


async def test_lending_beyond_stock_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`asset_bucket_check` (:763): "not enough in stock: short by N"."""
    thing = await asset(client, auth)
    person = await borrower(client, auth)
    expense_id = await purchase_expense(client, auth)
    seeded = await event(
        client,
        auth,
        thing["id"],
        "acquired",
        quantity=2,
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    assert seeded.status_code == 201

    response = await event(client, auth, thing["id"], "lent", quantity=3, member_id=person["id"])

    assert_problem(response, 409, "rule_violation")
    assert "not enough in stock" in response.json()["detail"]
    assert (await buckets(lab, thing["id"]))["stock"] == 2


async def test_returning_more_than_the_member_holds_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`asset_bucket_check` (:767-770): "that member holds fewer units than
    that"."""
    thing = await asset(client, auth)
    person = await borrower(client, auth)
    expense_id = await purchase_expense(client, auth)
    await event(
        client,
        auth,
        thing["id"],
        "acquired",
        quantity=2,
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    lent = await event(client, auth, thing["id"], "lent", quantity=1, member_id=person["id"])
    assert lent.status_code == 201

    response = await event(
        client, auth, thing["id"], "returned", quantity=2, member_id=person["id"]
    )

    assert_problem(response, 409, "rule_violation")
    assert "fewer units" in response.json()["detail"]
    assert await held_by(lab, thing["id"], person["id"]) == 1


async def test_an_individual_asset_cannot_exist_twice(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`asset_bucket_check` (:772-773): "an individually tracked asset can
    only exist once"."""
    thing = await asset(client, auth, mode="individual")
    first = await event(client, auth, thing["id"], "acquired", quantity=1, source="admin")
    assert first.status_code == 201

    response = await event(client, auth, thing["id"], "acquired", quantity=1, source="admin")

    assert_problem(response, 409, "rule_violation")
    assert "only exist once" in response.json()["detail"]


async def test_an_individual_asset_moves_one_unit_at_a_time(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`asset_event_guard` (:733-734): "an individually tracked asset moves
    one unit at a time"."""
    thing = await asset(client, auth, mode="individual")
    person = await borrower(client, auth)

    response = await event(client, auth, thing["id"], "lent", quantity=2, member_id=person["id"])

    assert_problem(response, 409, "rule_violation")
    assert "one unit at a time" in response.json()["detail"]


async def test_an_event_before_the_tenure_opened_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`asset_event_guard` (:730-731); the message says "closed tenure", so it
    falls through P0001 -> `rule_violation` (not DateBeforeTenure)."""
    thing = await asset(client, auth)

    response = await event(
        client, auth, thing["id"], "acquired", occurred_on="2025-12-31", source="admin"
    )

    assert_problem(response, 409, "rule_violation")
    assert "closed tenure" in response.json()["detail"]
    assert await event_count(lab) == 0


# ---- references --------------------------------------------------------------


async def test_an_event_for_an_unknown_asset_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # Prove the route exists first: an unmatched path is a framework 404 too.
    thing = await asset(client, auth)
    known = await event(client, auth, thing["id"], "acquired", source="admin")
    assert known.status_code == 201

    response = await event(client, auth, 9999, "acquired", source="admin")

    assert_problem(response, 404, "not_found")
    assert "9999" in response.json()["detail"]
    assert await event_count(lab) == 1


async def test_an_unknown_member_is_unknown_reference(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Q7=a: the foreign key answers (D-110). The current-member check in
    `asset_event_guard` (:737-741) only bites on `lent`, so a `returned` event
    reaches the FK with an unknown member."""
    thing = await asset(client, auth)

    response = await event(client, auth, thing["id"], "returned", quantity=1, member_id=9999)

    assert_problem(response, 422, "unknown_reference")
    assert await event_count(lab) == 0


async def test_an_unknown_ledger_transaction_is_unknown_reference(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth)

    response = await event(
        client, auth, thing["id"], "acquired", source="purchase", ledger_transaction_id=999999
    )

    assert_problem(response, 422, "unknown_reference")
    assert await event_count(lab) == 0
