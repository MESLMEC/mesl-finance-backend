"""GET /api/v1/cost-centers/{cost_center_id}/summary: the event leftover (ROADMAP 8.3).

Approved brief this session ("go with your suggestions", so every labelled
suggestion stands):

- Q2=a ONE row: the ``cost_center_summary`` view's own 8 columns in the view's
  names (db/schema.sql:537-557): ``{cost_center_id, name, kind, status,
  money_in, money_out, swept, leftover}``.
- Q1=a the read lives in ``cost_centers`` with its own port (D-085).
- A read commits nothing and never calls ``open_tenure_id()`` (the D-093 Q12 /
  D-105 (4) precedent).
- An unknown cost center is 404 ``not_found`` and the detail names the id, so
  the test cannot pass against the framework's own "Not Found" 404 of a route
  that does not exist yet (D-108 (1)).

Expected numbers are the worked example's (db/examples/06_allocation_and_sweeps.sql
lines 69-81: in 1000, out 400, swept 0, leftover 600), seeded through the app's
own deposit and expense actions in the ``lab`` fixture's id order. No EXPECT
table is mapped here: step 8.0 already ports every line of example 06 at the
database level (D-115); this file covers the new HTTP read.

Library APIs used, verified in installed source this session:
- ``httpx.AsyncClient.get`` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1751);
- ``asyncpg.Connection.fetchval`` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:236);
- pytest-asyncio auto mode (pyproject.toml:25) and the real ``client`` / ``lab``
  / ``auth`` / ``db`` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from httpx import AsyncClient

from tests.conftest import TestDb, idempotent

POOL, EVENTS = 1, 2
SUMMARY_KEYS = {
    "cost_center_id",
    "name",
    "kind",
    "status",
    "money_in",
    "money_out",
    "swept",
    "leftover",
}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def sunday(db: TestDb) -> date:
    s0: date = await db.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    return s0


async def create_event(client: AsyncClient, auth: dict[str, str], name: str) -> int:
    response = await client.post(
        "/api/v1/cost-centers", json={"name": name, "kind": "event"}, headers=auth
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


async def seed_event_spending(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], cost_center_id: int
) -> date:
    """Example lines 69-76: in 1000, out 400, both on the Events envelope."""
    s0 = await sunday(lab)
    deposit = await client.post(
        "/api/v1/deposits",
        json={
            "amount": 1000,
            "occurred_on": (s0 + timedelta(days=4)).isoformat(),
            "source": "admin_grant",
            "envelope_id": EVENTS,
            "cost_center_id": cost_center_id,
        },
        headers=idempotent(auth, "seed-1"),
    )
    assert deposit.status_code == 201, deposit.text
    expense = await client.post(
        "/api/v1/expenses",
        json={
            "amount": 400,
            "occurred_on": (s0 + timedelta(days=5)).isoformat(),
            "envelope_id": EVENTS,
            "tag": "catering",
            "cost_center_id": cost_center_id,
        },
        headers=auth,
    )
    assert expense.status_code == 201, expense.text
    return s0


async def sweep(
    client: AsyncClient, auth: dict[str, str], cost_center_id: int, occurred_on: date
) -> Any:
    response = await client.post(
        "/api/v1/sweeps",
        json={
            "cost_center_id": cost_center_id,
            "from_envelope_id": EVENTS,
            "occurred_on": occurred_on.isoformat(),
            "note": "event over; leftover back to pool",
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def summary(client: AsyncClient, auth: dict[str, str], cost_center_id: int) -> Any:
    response = await client.get(f"/api/v1/cost-centers/{cost_center_id}/summary", headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


async def test_the_summary_requires_a_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/cost-centers/1/summary")

    assert_problem(response, 401, "invalid_token")


async def test_the_summary_returns_the_view_row(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    await seed_event_spending(client, lab, auth, cost_center_id)

    body = await summary(client, auth, cost_center_id)

    assert set(body) == SUMMARY_KEYS
    assert body["cost_center_id"] == cost_center_id
    assert (body["name"], body["kind"], body["status"]) == (
        "Robotics Workshop",
        "event",
        "active",
    )
    assert (body["money_in"], body["money_out"], body["swept"], body["leftover"]) == (
        1000,
        400,
        0,
        600,
    )


async def test_the_summary_reflects_a_sweep(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example lines 82-86: swept 600, leftover 0 after the sweep."""
    cost_center_id = await create_event(client, auth, "Robotics Workshop")
    s0 = await seed_event_spending(client, lab, auth, cost_center_id)

    await sweep(client, auth, cost_center_id, s0 + timedelta(days=7))

    body = await summary(client, auth, cost_center_id)
    assert (body["money_in"], body["money_out"], body["swept"], body["leftover"]) == (
        1000,
        400,
        600,
        0,
    )


async def test_the_summary_of_a_cost_center_without_entries_is_all_zero(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """The view LEFT JOINs, so a cost center with no lines is zeros, not NULL."""
    cost_center_id = await create_event(client, auth, "Unused Event")

    body = await summary(client, auth, cost_center_id)

    assert (body["money_in"], body["money_out"], body["swept"], body["leftover"]) == (
        0,
        0,
        0,
        0,
    )


async def test_the_summary_for_an_unknown_cost_center_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.get("/api/v1/cost-centers/9999/summary", headers=auth)

    assert_problem(response, 404, "not_found")
    assert "9999" in response.json()["detail"]
