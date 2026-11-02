"""GET /api/v1/assets/activity: the admin report's raw numbers end to end
(roadmap step 9.4).

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a the route is `GET /api/v1/assets/activity`; Q2=a the query
parameters are `from_date`/`to_date`, both required; Q3=a JSON rows only -
"CSV-ready" is B-22's raw numbers, no CSV endpoint (D-012 defers report
output); Q4=a the function's own six column names and its own ORDER BY
(name, kind ENUM ORDINAL - `lent` sorts before `damaged`, D-128 (4));
Q5=a a reversed window passes through and answers `[]`.

Database rules these tests rely on (db/schema.sql, read this session):
- `asset_activity(p_from, p_to)` (:849-858): one row per (asset_name,
  ownership, kind, source) of `asset_events_current` - fixes collapsed -
  with `units` = sum(quantity) and `events` = count(*), ordered by 1, 3;
- the row's asset name is the asset's CURRENT name (the join is on `assets`,
  and 9.0 established a rename is allowed and visible, D-128 (4)).

Seeding goes through the 9.1/9.2 API routes; the tenure in the `lab` fixture
opened on 2026-01-01, so every date is on or after it.

Issue #10 (2026-11-02): a `source: "purchase"` acquisition must name the
expense that paid for it, so the report's own source column is exercised with
a real purchase (the `purchase_expense` helper); the seeds whose subject is
the report's window or ordering use `source: "admin"`, where no payment is
part of the story.

Library APIs used, all verified in installed source this session:
- `httpx.AsyncClient.get` with `params=` (httpx 0.28.1, _client.py:1751);
- FastAPI parses ISO date query params; a malformed or missing one answers
  422 without reaching the route (probed this session with a throwaway app:
  200 / 422 / 422);
- `pytest.mark.parametrize` (pytest 9.1.1, _pytest/python.py:1231);
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb

FIELDS = {"asset_name", "ownership", "kind", "source", "units", "events"}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def asset(client: AsyncClient, auth: dict[str, str], name: str) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/assets",
        json={"name": name, "mode": "counted", "ownership": "lab"},
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
        headers=auth,
    )
    response = await client.post(
        "/api/v1/expenses",
        json={"amount": amount, "occurred_on": "2026-02-01", "envelope_id": 1},
        headers=auth,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def borrower(client: AsyncClient, auth: dict[str, str]) -> int:
    member = await client.post("/api/v1/members", json={"name": "Ayesha"}, headers=auth)
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
) -> dict[str, Any]:
    body: dict[str, Any] = {"kind": kind, "quantity": 10, "occurred_on": "2026-02-01"}
    body.update(overrides)
    response = await client.post(f"/api/v1/assets/{asset_id}/events", json=body, headers=auth)
    assert response.status_code == 201
    return response.json()


async def activity(client: AsyncClient, auth: dict[str, str], **overrides: Any) -> Any:
    params: dict[str, str] = {"from_date": "2026-02-01", "to_date": "2026-02-28"}
    params.update(overrides)
    return await client.get("/api/v1/assets/activity", params=params, headers=auth)


# ---- the rows ----------------------------------------------------------------


async def test_activity_rows_carry_the_functions_six_columns(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth, "Alpha Kit")
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
    await event(client, auth, thing["id"], "damaged", quantity=1, note="burnt")

    response = await activity(client, auth)

    assert response.status_code == 200
    rows = response.json()
    assert [row["kind"] for row in rows] == ["acquired", "damaged"]
    assert all(set(row) == FIELDS for row in rows)
    assert (rows[0]["asset_name"], rows[0]["ownership"], rows[0]["source"]) == (
        "Alpha Kit",
        "lab",
        "purchase",
    )
    assert (rows[0]["units"], rows[0]["events"]) == (4, 1)
    assert rows[1]["source"] is None  # only an acquired row carries a source
    assert (rows[1]["units"], rows[1]["events"]) == (1, 1)


async def test_rows_are_ordered_by_name_then_kind_ordinal(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`ORDER BY 1, 3` (:857) is the kind ENUM ORDINAL (D-128 (4)): `lent`
    (2nd) before `damaged` (4th), although `damaged` sorts first as text."""
    thing = await asset(client, auth, "Alpha Kit")
    person = await borrower(client, auth)
    await event(client, auth, thing["id"], "acquired", quantity=4, source="admin")
    await event(client, auth, thing["id"], "lent", quantity=2, member_id=person)
    await event(client, auth, thing["id"], "damaged", quantity=1, note="burnt")

    response = await activity(client, auth)

    assert response.status_code == 200
    assert [row["kind"] for row in response.json()] == ["acquired", "lent", "damaged"]


async def test_the_window_excludes_events_outside_it(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await asset(client, auth, "Alpha Kit")
    await event(client, auth, thing["id"], "acquired", quantity=3, source="admin")
    await event(
        client, auth, thing["id"], "damaged", quantity=1, note="burnt", occurred_on="2026-01-31"
    )
    await event(
        client, auth, thing["id"], "lost", quantity=1, note="gone", occurred_on="2026-03-01"
    )

    response = await activity(client, auth)

    assert response.status_code == 200
    rows = response.json()
    assert [row["kind"] for row in rows] == ["acquired"]
    assert (rows[0]["units"], rows[0]["events"]) == (3, 1)  # the seed acquires 3


async def test_a_fixed_event_counts_once_as_its_replacement(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example 05 lines 87-88: `asset_events_current` collapses a fix - the
    mistaken lend is not counted, the replacement is."""
    thing = await asset(client, auth, "Alpha Kit")
    person = await borrower(client, auth)
    await event(client, auth, thing["id"], "acquired", quantity=4, source="admin")
    mistake = await event(
        client, auth, thing["id"], "lent", quantity=2, member_id=person, note="robot arm"
    )
    fixed = await client.post(
        f"/api/v1/assets/{thing['id']}/events/{mistake['id']}/fix",
        json={"quantity": 1, "occurred_on": "2026-02-01", "note": "typo, should be 1"},
        headers=auth,
    )
    assert fixed.status_code == 201

    response = await activity(client, auth)

    assert response.status_code == 200
    rows = response.json()
    assert [row["kind"] for row in rows] == ["acquired", "lent"]
    assert (rows[1]["units"], rows[1]["events"]) == (1, 1)


# ---- framework answers ---------------------------------------------------------


async def test_an_empty_window_is_a_bare_empty_array(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await activity(client, auth, from_date="2026-03-01", to_date="2026-03-31")

    assert response.status_code == 200
    assert response.json() == []


async def test_a_reversed_window_is_empty_not_an_error(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Q5=a: no rule refuses from > to; the function answers no rows."""
    thing = await asset(client, auth, "Alpha Kit")
    await event(client, auth, thing["id"], "acquired", quantity=1, source="admin")

    response = await activity(client, auth, from_date="2026-03-01", to_date="2026-02-01")

    assert response.status_code == 200
    assert response.json() == []


async def test_the_read_requires_a_token(client: AsyncClient, lab: TestDb) -> None:
    response = await client.get(
        "/api/v1/assets/activity",
        params={"from_date": "2026-02-01", "to_date": "2026-02-28"},
    )

    assert_problem(response, 401, "invalid_token")


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"from_date": "2026-02-01"},
        {"to_date": "2026-02-28"},
        {"from_date": "nope", "to_date": "2026-02-28"},
    ],
)
async def test_a_missing_or_malformed_window_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], params: dict[str, str]
) -> None:
    response = await client.get("/api/v1/assets/activity", params=params, headers=auth)

    assert_problem(response, 422, "validation_error")
