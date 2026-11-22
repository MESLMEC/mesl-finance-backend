"""POST /api/v1/assets/{asset_id}/events/{event_id}/fix: fix an asset event
end to end (roadmap step 9.2).

Approved step brief answers this session (all the brief's labelled
suggestions):
- Q1=a the route is ``POST /api/v1/assets/{asset_id}/events/{event_id}/fix``
  (nested under the asset, like every assets operation);
- Q2=a the body is ``{quantity, occurred_on, note}``; the reversal mirrors the
  original (same asset/kind/member/source, negated quantity -
  ``asset_event_guard``, db/schema.sql:742-749) and carries the request's
  note; the replacement carries ``replaces_id``, the new quantity, the
  request's ``occurred_on`` and the ORIGINAL's note (6.5's approved shape,
  D-088 Q3=all adapted); the request's date is written on BOTH rows;
- Q3=a every kind is fixable; whatever ``asset_event_guard`` /
  ``asset_bucket_check`` refuse is 409 ``rule_violation`` with the server's
  own message; the replacement's sign rule (db/schema.sql:677) stays
  PostgreSQL's - a negative replacement on a non-correction kind is 409;
- Q4=a an unknown event - and an event addressed under an asset that is not
  its own - is 404 ``not_found`` naming the id (the URL-addressed-resource
  pattern of 9.1 Q6=a / 7.1 Q3=a), NOT 6.5's 422 ``unknown_reference``;
- Q5=a the response is ``201 {"id","asset_id","kind","quantity","occurred_on",
  "note","reversal_id"}`` - no counts (9.1 Q8=a).

Issue #10 (2026-11-02) decides what 9.2 left unpinned: the reversal AND the
replacement copy the original's ``ledger_transaction_id``, so correcting a
purchase cannot erase the cost trail (this closes D-135 (3)). The fix answer
also carries the link (brief Q4=b), so ``FIX_FIELDS`` has eight keys. A
``source: "purchase"`` acquisition must name the expense that paid for it, so
the seeds below pay for what they buy; an admin-given kit carries no link.

Anti-vacuous 404 tests (the D-108 (1) lesson): a missing route answers the
same framework 404, so every 404 test below first completes a VALID fix and
asserts 201 before probing the unknown reference.

The tenure in the ``lab`` fixture opened on 2026-01-01; the borrower starts a
period on 2026-01-01, which ``asset_event_guard``'s current-member check
(db/schema.sql:737-741) requires for ``lent``.

Library APIs used, all verified in installed source this session:
- ``httpx.AsyncClient.post`` (httpx 0.28.1, _client.py:1838);
- ``asyncpg.Connection.fetchrow/fetchval/fetch`` (asyncpg-stubs 0.32.0,
  connection.pyi:725,746);
- ``pytest.mark.parametrize`` (pytest 9.1.1, _pytest/python.py:1231);
- pydantic 2.14.1 strict ``int`` refuses 1.5/True/"1" and accepts 5
  (probed this session; D-081 (1));
- the real ``client`` / ``lab`` / ``auth`` / ``db`` fixtures from
  tests/conftest.py.
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
FIX_FIELDS = EVENT_FIELDS | {"reversal_id"}
FIX_DAY = "2026-02-01"


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


async def borrower(client: AsyncClient, auth: dict[str, str], name: str = "Basana") -> int:
    member = await client.post("/api/v1/members", json={"name": name}, headers=auth)
    assert member.status_code == 201
    started = await client.post(
        f"/api/v1/members/{member.json()['id']}/periods/start",
        json={"start_date": "2026-01-01"},
        headers=auth,
    )
    assert started.status_code == 201
    return int(member.json()["id"])


async def event(
    client: AsyncClient, auth: dict[str, str], asset_id: int, kind: str, **overrides: Any
) -> Any:
    body: dict[str, Any] = {"kind": kind, "quantity": 10, "occurred_on": FIX_DAY}
    body.update(overrides)
    response = await client.post(f"/api/v1/assets/{asset_id}/events", json=body, headers=auth)
    assert response.status_code == 201
    return response.json()


async def fix_event(
    client: AsyncClient, auth: dict[str, str], asset_id: int, event_id: int, **overrides: Any
) -> Any:
    body: dict[str, Any] = {"quantity": 1, "occurred_on": FIX_DAY, "note": "typo, should be 1"}
    body.update(overrides)
    return await client.post(
        f"/api/v1/assets/{asset_id}/events/{event_id}/fix", json=body, headers=auth
    )


async def stored_event(db: TestDb, event_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        "SELECT id, asset_id, kind::text AS kind, quantity, member_id, occurred_on,"
        " note, source::text AS source, recorded_by, reverses_id, replaces_id,"
        " ledger_transaction_id"
        " FROM asset_events WHERE id = $1",
        event_id,
    )
    assert row is not None
    answer = dict(row)
    answer["occurred_on"] = answer["occurred_on"].isoformat()
    return answer


async def held_by(db: TestDb, asset_id: int, member_id: int) -> Any:
    return await db.owner.fetchval(
        "SELECT coalesce(sum(held_d), 0) FROM asset_event_effects"
        " WHERE asset_id = $1 AND member_id = $2",
        asset_id,
        member_id,
    )


async def event_count(db: TestDb) -> Any:
    return await db.owner.fetchval("SELECT count(*) FROM asset_events")


async def mistaken_lend(
    client: AsyncClient, auth: dict[str, str], *, acquired: int = 4, lent: int = 2
) -> tuple[int, int, int, int]:
    """Seed acquire-`acquired` + lend-`lent` to a member; returns
    (asset_id, member_id, original_event_id, original_quantity)."""
    thing = await asset(client, auth)
    person = await borrower(client, auth)
    expense_id = await purchase_expense(client, auth)
    await event(
        client,
        auth,
        thing["id"],
        "acquired",
        quantity=acquired,
        source="purchase",
        ledger_transaction_id=expense_id,
    )
    mistake = await event(
        client,
        auth,
        thing["id"],
        "lent",
        quantity=lent,
        member_id=person,
        note="robot arm",
    )
    return thing["id"], person, int(mistake["id"]), lent


# ---- 201: the reversal + replacement, ONE transaction ------------------------


async def test_fixing_a_mistaken_lend_reverses_and_replaces_it(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example 05 lines 51-58: lend 2 by mistake, fix to 1; the list shows
    one line."""
    asset_id, person, mistake_id, _ = await mistaken_lend(client, auth)

    response = await fix_event(client, auth, asset_id, mistake_id, quantity=1)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == FIX_FIELDS
    assert body["reversal_id"] not in (mistake_id, body["id"])
    assert (body["id"], body["asset_id"], body["kind"], body["quantity"]) == (
        max(body["id"], body["reversal_id"]),
        asset_id,
        "lent",
        1,
    )
    assert (body["occurred_on"], body["note"]) == (FIX_DAY, "robot arm")
    assert await held_by(lab, asset_id, person) == 1

    reversal = await stored_event(lab, int(body["reversal_id"]))
    assert reversal["note"] == "typo, should be 1"  # the request's note
    assert (reversal["reverses_id"], reversal["replaces_id"]) == (mistake_id, None)
    assert (reversal["kind"], reversal["member_id"], reversal["source"]) == ("lent", person, None)
    replacement = await stored_event(lab, int(body["id"]))
    assert replacement["note"] == "robot arm"  # the original's note
    assert (replacement["replaces_id"], replacement["reverses_id"]) == (mistake_id, None)
    assert replacement["quantity"] == 1
    recorded = await lab.owner.fetch(
        "SELECT recorded_by, occurred_on FROM asset_events WHERE id = ANY($1::bigint[])",
        [body["reversal_id"], body["id"]],
    )
    assert {row["recorded_by"] for row in recorded} == {USERNAME}
    assert all(row["occurred_on"].isoformat() == FIX_DAY for row in recorded)


async def test_fixing_an_acquisition_keeps_the_source(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    asset_id = (await asset(client, auth))["id"]
    expense_id = await purchase_expense(client, auth)
    acquired = await event(
        client,
        auth,
        asset_id,
        "acquired",
        quantity=10,
        source="purchase",
        ledger_transaction_id=expense_id,
    )

    response = await fix_event(client, auth, asset_id, int(acquired["id"]), quantity=8)

    assert response.status_code == 201
    body = response.json()
    assert (body["kind"], body["quantity"], body["note"]) == ("acquired", 8, "")
    reversal = await stored_event(lab, int(body["reversal_id"]))
    assert (reversal["quantity"], reversal["source"], reversal["reverses_id"]) == (
        -10,
        "purchase",
        acquired["id"],
    )
    replacement = await stored_event(lab, int(body["id"]))
    assert (replacement["quantity"], replacement["source"], replacement["replaces_id"]) == (
        8,
        "purchase",
        acquired["id"],
    )


async def test_the_current_view_collapses_the_fix_to_one_line(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example 05 line 59: the mistaken lend is not counted any more."""
    asset_id, _, mistake_id, _ = await mistaken_lend(client, auth)
    first = await fix_event(client, auth, asset_id, mistake_id, quantity=1)
    assert first.status_code == 201

    rows = await lab.owner.fetch(
        "SELECT id, replaces_id AS corrected_from FROM asset_events_current WHERE asset_id = $1",
        asset_id,
    )

    # the un-reversed acquisition stays in the view as well (corrected_from NULL);
    # the acquired event is the row inserted right before the mistake.
    assert {(row["id"], row["corrected_from"]) for row in rows} == {
        (mistake_id - 1, None),
        (int(first.json()["id"]), mistake_id),
    }


async def test_fixing_a_purchase_keeps_the_link_on_both_rows(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Issue #10, brief Q4=b: the reversal AND the replacement carry the
    original's link, so correcting a purchase cannot erase the cost trail
    (this closes the question D-135 (3) left open)."""
    asset_id = (await asset(client, auth))["id"]
    expense_id = await purchase_expense(client, auth)
    acquired = await event(
        client,
        auth,
        asset_id,
        "acquired",
        quantity=10,
        source="purchase",
        ledger_transaction_id=expense_id,
    )

    response = await fix_event(client, auth, asset_id, int(acquired["id"]), quantity=8)

    assert response.status_code == 201
    body = response.json()
    assert body["ledger_transaction_id"] == expense_id
    reversal = await stored_event(lab, int(body["reversal_id"]))
    replacement = await stored_event(lab, int(body["id"]))
    assert reversal["ledger_transaction_id"] == expense_id
    assert replacement["ledger_transaction_id"] == expense_id


async def test_fixing_an_admin_acquisition_leaves_the_link_empty(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """An admin-given item never had a payment, so the fix writes no link."""
    asset_id = (await asset(client, auth))["id"]
    acquired = await event(client, auth, asset_id, "acquired", quantity=1, source="admin")

    response = await fix_event(client, auth, asset_id, int(acquired["id"]), quantity=1)

    assert response.status_code == 201
    body = response.json()
    assert body["ledger_transaction_id"] is None
    assert (await stored_event(lab, int(body["id"])))["ledger_transaction_id"] is None


# ---- PostgreSQL's walls: 409 rule_violation, nothing written -----------------


async def test_an_already_reversed_event_cannot_be_fixed_again(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`reverses_id` is UNIQUE (db/schema.sql:670) and lives on the REVERSAL
    row - the original's own column stays NULL forever (D-128 (2)) - so the
    second fix reaches the UNIQUE and answers 409 `unique`, exactly like the
    ledger fix did (D-088 Q5=a). Nothing is written."""
    asset_id, _, mistake_id, _ = await mistaken_lend(client, auth, acquired=2, lent=1)
    first = await fix_event(client, auth, asset_id, mistake_id, quantity=2)
    assert first.status_code == 201

    response = await fix_event(client, auth, asset_id, mistake_id, quantity=2)

    assert_problem(response, 409, "unique")
    assert "reverses_id" in response.json()["detail"]  # the server text names the constraint
    assert await event_count(lab) == 4


async def test_a_replacement_that_breaks_the_stock_floor_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """``asset_bucket_check`` (:763) refuses the replacement - and the
    rollback takes the ALREADY-INSERTED reversal with it: ONE transaction."""
    asset_id, person, mistake_id, _ = await mistaken_lend(client, auth, acquired=2, lent=2)

    response = await fix_event(client, auth, asset_id, mistake_id, quantity=3)

    assert_problem(response, 409, "rule_violation")
    assert "not enough in stock" in response.json()["detail"]
    assert await event_count(lab) == 2  # only the original acquire + lend
    assert await held_by(lab, asset_id, person) == 2


async def test_a_negative_replacement_reaches_the_schema_check(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """db/schema.sql:677: only a correction may replace with a negative
    quantity; the sign rule is PostgreSQL's, the answer 409."""
    asset_id, person, mistake_id, _ = await mistaken_lend(client, auth, acquired=2, lent=1)

    response = await fix_event(client, auth, asset_id, mistake_id, quantity=-1)

    assert_problem(response, 409, "rule_violation")
    assert "check constraint" in response.json()["detail"]
    assert await event_count(lab) == 2
    assert await held_by(lab, asset_id, person) == 1


# ---- the app's own refusals: 422 ---------------------------------------------


async def test_a_zero_replacement_quantity_is_refused_by_the_app(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    asset_id, _, mistake_id, _ = await mistaken_lend(client, auth, acquired=2, lent=1)

    response = await fix_event(client, auth, asset_id, mistake_id, quantity=0)

    assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 2


async def test_a_blank_fix_note_is_refused_by_the_app(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """The reversal may not carry a blank note (db/schema.sql:680); the domain
    refuses it before SQL."""
    asset_id, _, mistake_id, _ = await mistaken_lend(client, auth, acquired=2, lent=1)

    for note in ["", "   "]:
        response = await fix_event(client, auth, asset_id, mistake_id, note=note)
        assert_problem(response, 422, "validation_failed")
    assert await event_count(lab) == 2


@pytest.mark.parametrize("quantity", [1.5, True, "1"])
async def test_a_non_whole_quantity_is_a_validation_error(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], quantity: Any
) -> None:
    asset_id, _, mistake_id, _ = await mistaken_lend(client, auth, acquired=2, lent=1)

    response = await fix_event(client, auth, asset_id, mistake_id, quantity=quantity)

    assert_problem(response, 422, "validation_error")
    assert await event_count(lab) == 2


async def test_a_non_numeric_event_id_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/assets/1/events/abc/fix", json={"quantity": 1}, headers=auth
    )

    assert_problem(response, 422, "validation_error")


# ---- auth and references -----------------------------------------------------


async def test_fixing_without_a_token_is_401(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post("/api/v1/assets/1/events/1/fix", json={"quantity": 1})

    assert_problem(response, 401, "invalid_token")
    assert await event_count(lab) == 0


async def test_an_unknown_asset_in_the_route_is_404_naming_it(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    asset_id, _, mistake_id, _ = await mistaken_lend(client, auth, acquired=2, lent=1)
    known = await fix_event(client, auth, asset_id, mistake_id, quantity=1)
    assert known.status_code == 201  # the route exists (anti-vacuous 404 proof)

    response = await fix_event(client, auth, 9999, mistake_id, quantity=1)

    assert_problem(response, 404, "not_found")
    assert "9999" in response.json()["detail"]
    assert await event_count(lab) == 4


async def test_an_unknown_event_is_404_naming_it(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    asset_id, _, mistake_id, _ = await mistaken_lend(client, auth, acquired=2, lent=1)
    known = await fix_event(client, auth, asset_id, mistake_id, quantity=1)
    assert known.status_code == 201  # the route exists (anti-vacuous 404 proof)

    response = await fix_event(client, auth, asset_id, 999999, quantity=1)

    assert_problem(response, 404, "not_found")
    assert "999999" in response.json()["detail"]
    assert await event_count(lab) == 4


async def test_an_event_addressed_under_another_asset_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """The URL identifies the resource: the event is not found under an asset
    that is not its own (Q4=a's URL-addressed reading)."""
    asset_id, _, mistake_id, _ = await mistaken_lend(client, auth, acquired=2, lent=1)
    other = await asset(client, auth)
    known = await fix_event(client, auth, asset_id, mistake_id, quantity=1)
    assert known.status_code == 201  # the route exists (anti-vacuous 404 proof)

    response = await fix_event(client, auth, other["id"], mistake_id, quantity=1)

    assert_problem(response, 404, "not_found")
    assert str(mistake_id) in response.json()["detail"]
    assert await event_count(lab) == 4
