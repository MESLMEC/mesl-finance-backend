"""POST /api/v1/allocation-suggestion: the allocation draft end to end (ROADMAP 8.1).

Approved brief this session ("go", so every labelled suggestion stands, the
D-062/D-064/D-066/D-070/D-076/D-079/D-082/D-086/D-088/D-090/D-093/D-096/D-101/
D-104/D-106/D-109/D-111 pattern):

- Q1=a ``POST /api/v1/allocation-suggestion`` with body
  ``{"amount": <int>, "shares": {"<envelope_id>": <int>, ...}}``; ``shares`` is
  optional, exactly the JSON object ``allocation_suggestion(p_amount, p_shares)``
  documents (db/schema.sql:454-456). A READ: it writes nothing.
- Q2=a every row the function returns, in the function's own order, with the
  function's own column names - ``envelope_id, envelope_name, balance,
  target_cap, alloc_priority, gap, phase, suggested`` (db/schema.sql:458-459).
- Q3=a ``amount`` is a strict whole number and the app refuses ``amount <= 0`` as
  422 ``validation_failed``; a non-integer is FastAPI's 422 ``validation_error``
  (D-081 (1)). The database function itself rejects nothing (``STABLE``).
- Q4=a ``shares`` is accepted as-is: string-keyed, strict-int values; no key or
  sign rule is invented (PostgreSQL ignores keys that name no eligible envelope,
  db/schema.sql:478-489).
- Q6=a no open-tenure call: a read only (7.5's Q9=a precedent).
- Q7=a raw rows only; the client sums them.

The expected numbers are the worked example's (db/examples/06_allocation_and_sweeps.sql
lines 19-25, 33-34), replayed here in the ``lab`` fixture's id order (the pool is 1,
Events 2, Admin 3; Components, Member Projects and Research are created, so their ids
depend on this order and are read from the responses). Every response is also compared
field for field with a direct call of the database function, so the API cannot drift.

No ``db/examples`` EXPECT table is mapped here: step 8.0 already ports every EXPECT
line of example 06 at the database level (D-115); this file covers the new HTTP slice.

Library APIs used, verified in installed source this session:
- ``httpx.AsyncClient.post`` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1838);
- ``pydantic`` 2.14.1 ``Field(strict=True)``, including nested
  ``dict[str, Annotated[int, Field(strict=True)]]``: a live probe this session showed
  ``1.5``, ``true`` and ``"3"`` all raise ``int_type`` while ``3`` is accepted;
- ``asyncpg.Connection.fetch/fetchval/fetchrow`` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:213,236,244);
- ``pytest`` auto asyncio mode (pyproject.toml:25) and the real
  ``client`` / ``lab`` / ``auth`` / ``db`` fixtures from tests/conftest.py.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb

POOL, EVENTS, ADMIN = 1, 2, 3
SUGGESTION_FIELDS = {
    "envelope_id",
    "envelope_name",
    "balance",
    "target_cap",
    "alloc_priority",
    "gap",
    "phase",
    "suggested",
}
SUGGESTION_COLUMNS = (
    "envelope_id, envelope_name, balance, target_cap, alloc_priority, gap, phase, suggested"
)


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def sunday(db: TestDb) -> date:
    s0: date = await db.owner.fetchval("SELECT sunday_on_or_before(current_date)")
    return s0


async def create_envelope(
    client: AsyncClient,
    auth: dict[str, str],
    name: str,
    *,
    target_cap: int | None = None,
    alloc_priority: int | None = None,
) -> int:
    response = await client.post(
        "/api/v1/envelopes",
        json={"name": name, "target_cap": target_cap, "alloc_priority": alloc_priority},
        headers=auth,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def set_settings(
    client: AsyncClient,
    auth: dict[str, str],
    envelope_id: int,
    target_cap: int | None,
    alloc_priority: int | None,
) -> None:
    response = await client.post(
        f"/api/v1/envelopes/{envelope_id}/settings",
        json={"target_cap": target_cap, "alloc_priority": alloc_priority},
        headers=auth,
    )
    assert response.status_code == 200


async def deactivate(client: AsyncClient, auth: dict[str, str], envelope_id: int) -> None:
    response = await client.post(f"/api/v1/envelopes/{envelope_id}/deactivate", headers=auth)
    assert response.status_code == 200


async def deposit(
    client: AsyncClient,
    auth: dict[str, str],
    amount: int,
    occurred_on: date,
    *,
    source: str = "sponsorship",
    member_id: int | None = None,
) -> None:
    body: dict[str, Any] = {
        "amount": amount,
        "occurred_on": occurred_on.isoformat(),
        "source": source,
    }
    if member_id is not None:
        body["member_id"] = member_id
    response = await client.post("/api/v1/deposits", json=body, headers=auth)
    assert response.status_code == 201


async def transfer(
    client: AsyncClient,
    auth: dict[str, str],
    from_envelope_id: int,
    to_envelope_id: int,
    amount: int,
    occurred_on: date,
    note: str,
) -> None:
    response = await client.post(
        "/api/v1/transfers",
        json={
            "amount": amount,
            "occurred_on": occurred_on.isoformat(),
            "from_envelope_id": from_envelope_id,
            "to_envelope_id": to_envelope_id,
            "note": note,
        },
        headers=auth,
    )
    assert response.status_code == 201


async def seed_member(db: TestDb, name: str) -> int:
    member_id: int = await db.owner.fetchval(
        "INSERT INTO members (name) VALUES ($1) RETURNING id", name
    )
    return member_id


async def script_prefix(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> tuple[date, dict[str, int]]:
    """Example 06 lines 5-15, in the ``lab`` fixture's id order.

    The example's one three-line transfer is written as two two-envelope transfers
    (the app's transfer action moves between exactly two envelopes, D-086 Q1=a); the
    balances are identical, which is all ``allocation_suggestion`` reads.
    """
    s0 = await sunday(lab)
    await set_settings(client, auth, ADMIN, 100, 1)
    components = await create_envelope(
        client, auth, "Components and Equipment", target_cap=500, alloc_priority=2
    )
    projects = await create_envelope(client, auth, "Member Projects")
    research = await create_envelope(client, auth, "Research")
    member = await seed_member(lab, "X")
    await deposit(client, auth, 3000, s0, source="other")
    await deposit(client, auth, 50, s0, source="weekly_fee", member_id=member)
    await transfer(client, auth, POOL, ADMIN, 40, s0, "opening split")
    await transfer(client, auth, POOL, components, 450, s0, "opening split")
    return s0, {"components": components, "projects": projects, "research": research}


async def suggestion(
    db: TestDb, amount: int, shares: dict[str, int] | None = None
) -> list[dict[str, Any]]:
    """The database function directly, in its own order (it carries no ORDER BY gap)."""
    rows: list[Any] = await db.app.fetch(
        "SELECT " + SUGGESTION_COLUMNS + " FROM allocation_suggestion($1, $2::jsonb)",
        amount,
        None if shares is None else json.dumps(shares),
    )
    return [
        {
            "envelope_id": int(row["envelope_id"]),
            "envelope_name": str(row["envelope_name"]),
            "balance": int(row["balance"]),
            "target_cap": None if row["target_cap"] is None else int(row["target_cap"]),
            "alloc_priority": (
                None if row["alloc_priority"] is None else int(row["alloc_priority"])
            ),
            "gap": None if row["gap"] is None else int(row["gap"]),
            "phase": str(row["phase"]),
            "suggested": int(row["suggested"]),
        }
        for row in rows
    ]


async def draft(
    client: AsyncClient,
    auth: dict[str, str],
    amount: Any,
    shares: dict[str, Any] | None = None,
) -> Any:
    body: dict[str, Any] = {"amount": amount}
    if shares is not None:
        body["shares"] = shares
    response = await client.post("/api/v1/allocation-suggestion", json=body, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


async def counts(db: TestDb) -> dict[str, int]:
    row = await db.owner.fetchrow(
        """
        SELECT (SELECT count(*) FROM ledger_transactions) AS tx,
               (SELECT count(*) FROM ledger_lines) AS lines,
               (SELECT count(*) FROM allocation_sessions) AS sessions
        """
    )
    assert row is not None
    return {"tx": int(row["tx"]), "lines": int(row["lines"]), "sessions": int(row["sessions"])}


async def test_the_draft_requires_a_token(client: AsyncClient) -> None:
    response = await client.post("/api/v1/allocation-suggestion", json={"amount": 1000})

    assert_problem(response, 401, "invalid_token")


async def test_the_draft_with_shares_matches_the_function(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example lines 19-21: caps first (priority order), then 3:2:1; the sum is 1000."""
    _, ids = await script_prefix(client, lab, auth)
    shares = {str(ids["projects"]): 3, str(EVENTS): 2, str(ids["research"]): 1}

    body = await draft(client, auth, 1000, shares)

    assert body == await suggestion(lab, 1000, shares)
    assert {frozenset(row) for row in body} == {frozenset(SUGGESTION_FIELDS)}
    by_name = {row["envelope_name"]: (row["phase"], row["suggested"]) for row in body}
    assert by_name == {
        "Admin and Misc": ("cap_fill", 60),
        "Components and Equipment": ("cap_fill", 50),
        "Member Projects": ("share", 445),
        "Events and Workshops": ("share", 297),
        "Research": ("share", 148),
    }
    assert sum(row["suggested"] for row in body) == 1000


async def test_the_draft_without_shares_only_fills_caps(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example lines 22-23: no shares and no history -> only the 110 of cap fills."""
    await script_prefix(client, lab, auth)

    body = await draft(client, auth, 1000)

    assert body == await suggestion(lab, 1000)
    positive = {
        row["envelope_name"]: (row["phase"], row["suggested"])
        for row in body
        if row["suggested"] > 0
    }
    assert positive == {
        "Admin and Misc": ("cap_fill", 60),
        "Components and Equipment": ("cap_fill", 50),
    }
    assert sum(row["suggested"] for row in body) == 110


async def test_a_small_amount_follows_priority(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example lines 24-25: 30 fills the lowest-priority-number gap first."""
    await script_prefix(client, lab, auth)

    body = await draft(client, auth, 30)

    amounts = {row["envelope_name"]: row["suggested"] for row in body}
    assert amounts["Admin and Misc"] == 30
    assert amounts["Components and Equipment"] == 0
    assert body == await suggestion(lab, 30)


async def test_the_draft_reuses_the_last_session_proportions(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example lines 27-34: after one confirmed session, no shares reuses its proportions."""
    s0, ids = await script_prefix(client, lab, auth)
    # Lines 28-29: every positive suggestion, the two cap fills included (Admin 60,
    # Components 50), so the session is the full 1000 and both caps are then full.
    amounts = {
        str(ADMIN): 60,
        str(ids["components"]): 50,
        str(ids["projects"]): 445,
        str(EVENTS): 297,
        str(ids["research"]): 148,
    }
    session_tx = await lab.app.fetchval(
        "SELECT allocate($1, $2::date, $3, $4::jsonb)",
        "treasurer",
        s0,
        "first monthly allocation",
        json.dumps(amounts),
    )
    assert session_tx is not None

    body = await draft(client, auth, 600)

    by_name = {row["envelope_name"]: row["suggested"] for row in body}
    assert by_name["Member Projects"] == 300
    assert by_name["Events and Workshops"] == 200
    assert by_name["Research"] == 100
    assert by_name["Admin and Misc"] == 0
    assert by_name["Components and Equipment"] == 0
    assert body == await suggestion(lab, 600)


async def test_the_draft_lists_every_eligible_envelope(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Every ACTIVE, NON-POOL envelope is listed, even when its suggestion is 0."""
    old = await create_envelope(client, auth, "Old idea")
    await deactivate(client, auth, old)

    body = await draft(client, auth, 100)

    eligible = await lab.owner.fetch(
        """
        SELECT id FROM envelopes
        WHERE active AND NOT is_pool
        ORDER BY coalesce(alloc_priority, 2147483647), id
        """
    )
    assert [row["envelope_id"] for row in body] == [int(row["id"]) for row in eligible]
    assert {row["phase"] for row in body} == {"none"}
    assert {row["suggested"] for row in body} == {0}
    assert POOL not in [row["envelope_id"] for row in body]


async def test_the_draft_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    _, ids = await script_prefix(client, lab, auth)
    before = await counts(lab)

    await draft(
        client, auth, 1000, {str(ids["projects"]): 3, str(EVENTS): 2, str(ids["research"]): 1}
    )

    assert await counts(lab) == before


@pytest.mark.parametrize(
    ("amount", "code"),
    [
        (0, "validation_failed"),
        (-5, "validation_failed"),
        (10.5, "validation_error"),
        ("100", "validation_error"),
        (True, "validation_error"),
    ],
)
async def test_an_amount_that_is_not_a_positive_whole_number_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amount: Any, code: str
) -> None:
    response = await client.post(
        "/api/v1/allocation-suggestion", json={"amount": amount}, headers=auth
    )

    assert_problem(response, 422, code)


@pytest.mark.parametrize(
    "shares",
    [{"4": 1.5}, {"4": True}, {"4": "3"}],
)
async def test_non_integer_share_values_are_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], shares: dict[str, Any]
) -> None:
    response = await client.post(
        "/api/v1/allocation-suggestion",
        json={"amount": 1000, "shares": shares},
        headers=auth,
    )

    assert_problem(response, 422, "validation_error")


async def test_unknown_share_keys_are_ignored(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Database behaviour (db/schema.sql:478-489): a key naming no eligible envelope is 0."""
    await script_prefix(client, lab, auth)

    body = await draft(client, auth, 1000, {"999": 5})

    assert body == await draft(client, auth, 1000)
