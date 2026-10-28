"""POST /api/v1/allocations: confirm an allocation end to end (ROADMAP 8.2).

Approved brief this session ("go with your suggestions", so every labelled
suggestion stands):

- Q1=a ``POST /api/v1/allocations``, answers 201.
- Q2=a body ``{"occurred_on": <date>, "note": <str>, "amounts": {"<envelope_id>": <int>}}``,
  every field required; ``p_by``/``recorded_by`` is the JWT actor, never the client.
- Q3=b response ``201 {"id", "kind": "transfer", "pool_balance"}``.
- Q4=a a THIN app: pydantic strict whole numbers only (a non-integer is FastAPI's
  422 ``validation_error``). Zero, a negative entry, a non-digit key, an empty
  map, a blank note, an unknown or inactive envelope and an over-allocation all
  reach ``allocate`` and answer 409 with that function's own message
  (db/schema.sql:507-534, AGENTS.md section 5).
- Q5=a the adapter pre-checks the open tenure, so no open tenure answers 409
  ``no_open_tenure`` (the ledger write-slice pattern); ``allocate``'s own check
  stays the backstop.
- Q6=a the slice lives in ``envelopes`` with its own port (D-085).
- Q7=a the confirm write only; no allocation-session read route.
- Q8=a an unknown or inactive envelope answers 409 ``rule_violation`` naming the
  id, exactly as the function raises it.

Behaviour the tests pin, from ``allocate``: one ``transfer`` header
(``tag='allocation'``), one negative pool line, one positive line per amount and
one ``allocation_sessions`` row, all in the caller's transaction (:505-534).
The expected balances are the worked example's
(db/examples/06_allocation_and_sweeps.sql lines 27-34), replayed through the
app in the ``lab`` fixture's id order. No ``db/examples`` EXPECT table is mapped
here: step 8.0 already ports every line of example 06 at the database level
(D-115); this file covers the new HTTP slice.

Library APIs used, verified in installed source this session:
- ``httpx.AsyncClient.post`` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1838);
- ``pydantic`` 2.14.1 strict ``dict[str, int]`` (a live probe this session:
  ``10.5``, ``true`` and ``"20"`` raise ``int_type``, ``3`` is accepted, and a
  list or string raises ``dict_type``);
- ``asyncpg.Connection.fetch/fetchrow/fetchval`` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:213,236,244);
- pytest auto asyncio mode (pyproject.toml:25) and the real ``client`` / ``lab`` /
  ``auth`` / ``db`` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import USERNAME, TestDb

POOL, EVENTS, ADMIN = 1, 2, 3


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
    balances are identical, which is all ``allocate`` and the draft read.
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


def suggestion_shares(ids: dict[str, int]) -> dict[str, int]:
    """Example line 20's 3:2:1 over the three uncapped envelopes."""
    return {str(ids["projects"]): 3, str(EVENTS): 2, str(ids["research"]): 1}


async def draft(
    client: AsyncClient, auth: dict[str, str], amount: int, shares: dict[str, int] | None = None
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"amount": amount}
    if shares is not None:
        body["shares"] = shares
    response = await client.post("/api/v1/allocation-suggestion", json=body, headers=auth)
    assert response.status_code == 200, response.text
    rows: list[dict[str, Any]] = response.json()
    return rows


async def drafted_amounts(
    client: AsyncClient, auth: dict[str, str], ids: dict[str, int]
) -> dict[str, int]:
    """Example line 28: every positive suggestion, the two cap fills included."""
    rows = await draft(client, auth, 1000, suggestion_shares(ids))
    return {str(row["envelope_id"]): int(row["suggested"]) for row in rows if row["suggested"] > 0}


async def confirm(
    client: AsyncClient,
    auth: dict[str, str],
    amounts: dict[str, Any],
    occurred_on: date,
    *,
    note: str = "first monthly allocation",
) -> Any:
    return await client.post(
        "/api/v1/allocations",
        json={"occurred_on": occurred_on.isoformat(), "note": note, "amounts": amounts},
        headers=auth,
    )


async def confirmed(
    client: AsyncClient,
    auth: dict[str, str],
    amounts: dict[str, Any],
    occurred_on: date,
    *,
    note: str = "first monthly allocation",
) -> dict[str, Any]:
    response = await confirm(client, auth, amounts, occurred_on, note=note)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def balances(db: TestDb) -> dict[str, int]:
    rows = await db.owner.fetch("SELECT name, balance FROM envelope_balances")
    return {str(row["name"]): int(row["balance"]) for row in rows}


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


async def test_the_confirmation_requires_a_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/allocations",
        json={"occurred_on": "2026-02-02", "note": "x", "amounts": {str(EVENTS): 10}},
    )

    assert_problem(response, 401, "invalid_token")


async def test_the_confirmed_session_reproduces_the_example(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example lines 27-31: the drafted 1000 moves; every balance matches."""
    s0, ids = await script_prefix(client, lab, auth)
    amounts = await drafted_amounts(client, auth, ids)

    body = await confirmed(client, auth, amounts, s0 + timedelta(days=1))

    assert body["kind"] == "transfer"
    assert await balances(lab) == {
        "Unallocated General": 1560,
        "Admin and Misc": 100,
        "Components and Equipment": 500,
        "Member Projects": 445,
        "Events and Workshops": 297,
        "Research": 148,
    }


async def test_the_response_carries_the_entry_the_kind_and_the_pool_balance(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0, _ = await script_prefix(client, lab, auth)

    body = await confirmed(client, auth, {str(EVENTS): 100}, s0 + timedelta(days=1))

    assert set(body) == {"id", "kind", "pool_balance"}
    assert type(body["id"]) is int
    assert body["kind"] == "transfer"
    assert body["pool_balance"] == 2460


async def test_one_transfer_header_one_pool_line_and_one_session_row(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0, ids = await script_prefix(client, lab, auth)
    occurred_on = s0 + timedelta(days=1)

    body = await confirmed(
        client,
        auth,
        {str(ids["projects"]): 300, str(EVENTS): 200},
        occurred_on,
        note="second allocation",
    )

    header = await lab.owner.fetchrow(
        """
        SELECT kind, occurred_on, recorded_by, note, tag
        FROM ledger_transactions WHERE id = $1
        """,
        body["id"],
    )
    assert header is not None
    assert dict(header) == {
        "kind": "transfer",
        "occurred_on": occurred_on,
        "recorded_by": USERNAME,
        "note": "second allocation",
        "tag": "allocation",
    }
    lines = await lab.owner.fetch(
        "SELECT envelope_id, amount FROM ledger_lines WHERE transaction_id = $1", body["id"]
    )
    assert {int(row["envelope_id"]): int(row["amount"]) for row in lines} == {
        POOL: -500,
        ids["projects"]: 300,
        EVENTS: 200,
    }
    sessions = await lab.owner.fetch(
        "SELECT ledger_transaction_id, recorded_by FROM allocation_sessions"
    )
    assert [(int(row["ledger_transaction_id"]), str(row["recorded_by"])) for row in sessions] == [
        (body["id"], USERNAME)
    ]


async def test_the_next_draft_reuses_the_confirmed_proportions(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example lines 33-34: after the session, no shares reuses its proportions."""
    s0, ids = await script_prefix(client, lab, auth)
    await confirmed(client, auth, await drafted_amounts(client, auth, ids), s0 + timedelta(days=1))

    by_name = {row["envelope_name"]: row["suggested"] for row in await draft(client, auth, 600)}

    assert by_name["Member Projects"] == 300
    assert by_name["Events and Workshops"] == 200
    assert by_name["Research"] == 100
    assert by_name["Admin and Misc"] == 0
    assert by_name["Components and Equipment"] == 0


async def test_the_pool_cannot_be_allocated_to_itself(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0, _ = await script_prefix(client, lab, auth)

    response = await confirm(client, auth, {str(POOL): 10}, s0 + timedelta(days=1))

    assert_problem(response, 409, "rule_violation")
    assert "pool" in response.json()["detail"]


async def test_an_unknown_envelope_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0, _ = await script_prefix(client, lab, auth)

    response = await confirm(client, auth, {"9999": 10}, s0 + timedelta(days=1))

    assert_problem(response, 409, "rule_violation")
    assert "9999" in response.json()["detail"]


async def test_an_inactive_envelope_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0, _ = await script_prefix(client, lab, auth)
    old = await create_envelope(client, auth, "Old idea")
    await deactivate(client, auth, old)

    response = await confirm(client, auth, {str(old): 10}, s0 + timedelta(days=1))

    assert_problem(response, 409, "rule_violation")
    assert str(old) in response.json()["detail"]
    assert "inactive" in response.json()["detail"]


async def test_an_amount_above_the_pool_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0, ids = await script_prefix(client, lab, auth)
    before = await counts(lab)

    response = await confirm(client, auth, {str(ids["components"]): 999999}, s0 + timedelta(days=1))

    assert_problem(response, 409, "rule_violation")
    assert "would drop below zero" in response.json()["detail"]
    assert await counts(lab) == before


@pytest.mark.parametrize("amount", [10.5, True, "20"])
async def test_a_non_integer_amount_value_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amount: Any
) -> None:
    s0, _ = await script_prefix(client, lab, auth)

    response = await confirm(client, auth, {str(EVENTS): amount}, s0 + timedelta(days=1))

    assert_problem(response, 422, "validation_error")


@pytest.mark.parametrize(
    ("envelope_key", "amount", "fragment"),
    [
        (str(EVENTS), 0, "zero amount"),
        (str(EVENTS), -5, "bad entry"),
        ("abc", 10, "bad entry"),
    ],
)
async def test_the_database_owns_the_per_entry_amount_rules(
    client: AsyncClient,
    lab: TestDb,
    auth: dict[str, str],
    envelope_key: str,
    amount: Any,
    fragment: str,
) -> None:
    """Q4=a: these are ``allocate``'s own rejections, so they answer 409."""
    s0, _ = await script_prefix(client, lab, auth)

    response = await confirm(client, auth, {envelope_key: amount}, s0 + timedelta(days=1))

    assert_problem(response, 409, "rule_violation")
    assert fragment in response.json()["detail"]


async def test_a_blank_note_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0, _ = await script_prefix(client, lab, auth)

    response = await confirm(client, auth, {str(EVENTS): 10}, s0 + timedelta(days=1), note="")

    assert_problem(response, 409, "rule_violation")
    assert "ledger_transactions_check" in response.json()["detail"]


async def test_an_empty_amounts_object_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0, _ = await script_prefix(client, lab, auth)

    response = await confirm(client, auth, {}, s0 + timedelta(days=1))

    assert_problem(response, 409, "rule_violation")
    assert "nothing to allocate" in response.json()["detail"]


@pytest.mark.parametrize("amounts", [[1, 2], "abc"])
async def test_amounts_that_are_not_an_object_are_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], amounts: Any
) -> None:
    s0, _ = await script_prefix(client, lab, auth)

    response = await confirm(client, auth, amounts, s0 + timedelta(days=1))

    assert_problem(response, 422, "validation_error")


async def test_no_open_tenure_is_refused(
    client: AsyncClient, db: TestDb, auth: dict[str, str]
) -> None:
    response = await confirm(client, auth, {str(EVENTS): 10}, date(2026, 2, 2))

    assert_problem(response, 409, "no_open_tenure")


async def test_a_date_before_the_tenure_opened_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await confirm(client, auth, {str(EVENTS): 10}, date(2025, 12, 31))

    assert_problem(response, 409, "date_before_tenure")
    assert "before this tenure opened" in response.json()["detail"]


async def test_a_failed_confirmation_writes_nothing(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    s0, _ = await script_prefix(client, lab, auth)
    before = await counts(lab)

    response = await confirm(client, auth, {str(POOL): 10}, s0 + timedelta(days=1))

    assert_problem(response, 409, "rule_violation")
    assert await counts(lab) == before
