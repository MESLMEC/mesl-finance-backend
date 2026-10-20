"""API tests for the envelope actions (roadmap step 5.1).

Approved brief answers this session: Q3=b - cap/priority are set on create AND
through a separate `settings` action; the unanswered questions keep the
brief's labelled suggestions: Q1=a (P-009 confirmed), Q2=a (action-style
routes), Q4=a (the list is every envelope in id order, no balance), Q5=a
(unknown id = 404 `not_found`), Q6=a (a CHECK violation = 409
`rule_violation` through the shared translator), Q7=a (blank names = 422
`validation_failed`), Q8=a (the pool may be renamed, the schema is the only
rule), Q9=a (one session).

Contract this file pins:
    POST /api/v1/envelopes                  201  EnvelopeOut
    GET  /api/v1/envelopes                  200  [EnvelopeOut] ordered by id
    POST /api/v1/envelopes/{id}/rename      200  EnvelopeOut   {"name"}
    POST /api/v1/envelopes/{id}/settings    200  EnvelopeOut   {"target_cap","alloc_priority"}
    POST /api/v1/envelopes/{id}/deactivate  200  EnvelopeOut

EnvelopeOut = {"id","name","target_cap","alloc_priority","is_pool","active"}.

`settings` is the Q3=b operation's smallest faithful shape: both fields are
required and nullable (a full replacement - null clears, an omitted field is
a 422). This is a contract choice, reviewed with these tests.

Database rules these tests rely on (db/schema.sql, read this session):
- `envelopes.name` is NOT NULL UNIQUE (:68) -> duplicate is 23505
  `envelopes_name_key` (D-059);
- `target_cap` has `CHECK (target_cap >= 0)` (:69) -> 23514 (Q6=a);
- `envelope_guard()` (:144-157) refuses a pool-flag change, the pool's
  deactivation and a non-empty envelope's deactivation, and names the
  balance in its message;
- `labapp` holds SELECT + INSERT/UPDATE on `envelopes` (:1191-1195), no DELETE;
- `db/examples/06_allocation_and_sweeps.sql:59` states the same guard outcome.

Library APIs used: only the ones this repo already exercises -
httpx.AsyncClient over ASGITransport (tests/conftest.py `client`), the real
`lab` fixture, pytest.mark.parametrize, and asyncpg Record access via
dict(row) (asyncpg-stubs/protocol/record.pyi:4-26 has keys() + __getitem__).
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb

POOL, EVENTS, ADMIN = 1, 2, 3
FIELDS = {"id", "name", "target_cap", "alloc_priority", "is_pool", "active"}


def envelope_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"name": "Research"}
    body.update(overrides)
    return body


async def stored(db: TestDb, envelope_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        "SELECT id, name, target_cap, alloc_priority, is_pool, active FROM envelopes WHERE id = $1",
        envelope_id,
    )
    assert row is not None
    return dict(row)


async def envelope_count(db: TestDb) -> Any:
    return await db.owner.fetchval("SELECT count(*) FROM envelopes")


async def deposit_into(db: TestDb, envelope_id: int, amount: int) -> None:
    """Put money in an envelope so the zero-balance rule has something to refuse."""
    tenure_id = await db.owner.fetchval("SELECT id FROM tenures WHERE closed_on IS NULL")
    # One explicit transaction: the entry-shape trigger is DEFERRABLE and
    # fires at COMMIT, as in db/examples/06_allocation_and_sweeps.sql:69-70.
    async with db.owner.transaction():
        transaction_id = await db.owner.fetchval(
            "INSERT INTO ledger_transactions"
            " (tenure_id, kind, occurred_on, recorded_by, source)"
            " VALUES ($1, 'deposit', '2026-02-01', 'treasurer', 'donation')"
            " RETURNING id",
            tenure_id,
        )
        await db.owner.execute(
            "INSERT INTO ledger_lines (transaction_id, envelope_id, amount) VALUES ($1, $2, $3)",
            transaction_id,
            envelope_id,
            amount,
        )


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


# ---- create -----------------------------------------------------------------


async def test_create_returns_201_and_the_stored_row(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/envelopes", json=envelope_body(), headers=auth)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == FIELDS
    assert (body["name"], body["target_cap"], body["alloc_priority"]) == ("Research", None, None)
    assert (body["is_pool"], body["active"]) == (False, True)
    assert await stored(lab, body["id"]) == body


async def test_create_with_cap_and_priority_stores_them(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/envelopes",
        json=envelope_body(target_cap=1000, alloc_priority=1),
        headers=auth,
    )

    assert response.status_code == 201
    row = await stored(lab, response.json()["id"])
    assert (row["target_cap"], row["alloc_priority"]) == (1000, 1)


async def test_create_with_a_taken_name_is_409_unique(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/envelopes", json=envelope_body(name="Events and Workshops"), headers=auth
    )

    assert_problem(response, 409, "unique")
    assert "envelopes_name_key" in response.json()["detail"]
    assert await envelope_count(lab) == 3


@pytest.mark.parametrize("name", ["", "   "])
async def test_create_with_a_blank_name_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], name: str
) -> None:
    response = await client.post("/api/v1/envelopes", json=envelope_body(name=name), headers=auth)

    assert_problem(response, 422, "validation_failed")
    assert await envelope_count(lab) == 3


async def test_create_with_a_negative_cap_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Q6=a: the schema's CHECK owns the rule; the translator maps 23514."""
    response = await client.post(
        "/api/v1/envelopes", json=envelope_body(target_cap=-5), headers=auth
    )

    assert_problem(response, 409, "rule_violation")
    assert await envelope_count(lab) == 3


# ---- list -------------------------------------------------------------------


async def test_list_returns_all_envelopes_in_id_order(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    created = await client.post("/api/v1/envelopes", json=envelope_body(), headers=auth)
    deactivated = await client.post(f"/api/v1/envelopes/{ADMIN}/deactivate", headers=auth)
    assert (created.status_code, deactivated.status_code) == (201, 200)

    response = await client.get("/api/v1/envelopes", headers=auth)

    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [POOL, EVENTS, ADMIN, created.json()["id"]]
    assert all(set(row) == FIELDS for row in rows)  # no balance, no extra keys
    assert (rows[0]["name"], rows[0]["is_pool"], rows[0]["active"]) == (
        "Unallocated General",
        True,
        True,
    )
    assert rows[2]["active"] is False  # inactive envelopes are still listed


# ---- rename -----------------------------------------------------------------


async def test_rename_changes_the_name(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        f"/api/v1/envelopes/{EVENTS}/rename", json={"name": "Events"}, headers=auth
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["name"], body["active"]) == (EVENTS, "Events", True)
    assert (await stored(lab, EVENTS))["name"] == "Events"


async def test_the_pool_may_be_renamed(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Q8=a: the schema forbids changing `is_pool`, not renaming the pool."""
    response = await client.post(
        f"/api/v1/envelopes/{POOL}/rename", json={"name": "General Pool"}, headers=auth
    )

    assert response.status_code == 200
    row = await stored(lab, POOL)
    assert (row["name"], row["is_pool"]) == ("General Pool", True)


async def test_rename_to_a_taken_name_is_409_unique(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        f"/api/v1/envelopes/{EVENTS}/rename", json={"name": "Admin and Misc"}, headers=auth
    )

    assert_problem(response, 409, "unique")
    assert "envelopes_name_key" in response.json()["detail"]
    assert (await stored(lab, EVENTS))["name"] == "Events and Workshops"


async def test_rename_a_blank_name_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        f"/api/v1/envelopes/{EVENTS}/rename", json={"name": "  "}, headers=auth
    )

    assert_problem(response, 422, "validation_failed")
    assert (await stored(lab, EVENTS))["name"] == "Events and Workshops"


async def test_rename_unknown_id_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # Prove the route exists first: an unmatched path is a framework 404 too.
    known = await client.post(
        f"/api/v1/envelopes/{EVENTS}/rename", json={"name": "Events"}, headers=auth
    )
    assert known.status_code == 200

    response = await client.post(
        "/api/v1/envelopes/999/rename", json={"name": "Nowhere"}, headers=auth
    )

    assert_problem(response, 404, "not_found")


# ---- settings (Q3=b) --------------------------------------------------------


async def test_settings_updates_cap_and_priority(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        f"/api/v1/envelopes/{EVENTS}/settings",
        json={"target_cap": 500, "alloc_priority": 2},
        headers=auth,
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["target_cap"], body["alloc_priority"]) == (500, 2)
    row = await stored(lab, EVENTS)
    assert (row["target_cap"], row["alloc_priority"], row["name"]) == (
        500,
        2,
        "Events and Workshops",
    )


async def test_settings_clears_cap_and_priority_with_null(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    set_response = await client.post(
        f"/api/v1/envelopes/{EVENTS}/settings",
        json={"target_cap": 500, "alloc_priority": 2},
        headers=auth,
    )
    assert set_response.status_code == 200

    response = await client.post(
        f"/api/v1/envelopes/{EVENTS}/settings",
        json={"target_cap": None, "alloc_priority": None},
        headers=auth,
    )

    assert response.status_code == 200
    assert (response.json()["target_cap"], response.json()["alloc_priority"]) == (None, None)
    row = await stored(lab, EVENTS)
    assert (row["target_cap"], row["alloc_priority"]) == (None, None)


async def test_settings_with_a_negative_cap_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        f"/api/v1/envelopes/{EVENTS}/settings",
        json={"target_cap": -1, "alloc_priority": 2},
        headers=auth,
    )

    assert_problem(response, 409, "rule_violation")
    assert (await stored(lab, EVENTS))["target_cap"] is None


async def test_settings_without_both_fields_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`settings` replaces both values; a partial body is refused."""
    response = await client.post(
        f"/api/v1/envelopes/{EVENTS}/settings", json={"target_cap": 500}, headers=auth
    )

    assert_problem(response, 422, "validation_error")
    assert (await stored(lab, EVENTS))["target_cap"] is None


async def test_settings_unknown_id_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    known = await client.post(
        f"/api/v1/envelopes/{EVENTS}/settings",
        json={"target_cap": 500, "alloc_priority": 2},
        headers=auth,
    )
    assert known.status_code == 200

    response = await client.post(
        "/api/v1/envelopes/999/settings",
        json={"target_cap": 500, "alloc_priority": 1},
        headers=auth,
    )

    assert_problem(response, 404, "not_found")


# ---- deactivate -------------------------------------------------------------


async def test_deactivate_an_empty_envelope_marks_it_inactive(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(f"/api/v1/envelopes/{ADMIN}/deactivate", headers=auth)

    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["active"]) == (ADMIN, False)
    row = await stored(lab, ADMIN)
    assert (row["active"], row["name"]) == (False, "Admin and Misc")


async def test_deactivate_a_non_empty_envelope_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await deposit_into(lab, EVENTS, 100)

    response = await client.post(f"/api/v1/envelopes/{EVENTS}/deactivate", headers=auth)

    assert_problem(response, 409, "rule_violation")
    assert "still holds 100" in response.json()["detail"]
    assert (await stored(lab, EVENTS))["active"] is True


async def test_deactivate_the_pool_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(f"/api/v1/envelopes/{POOL}/deactivate", headers=auth)

    assert_problem(response, 409, "rule_violation")
    assert "pool cannot be deactivated" in response.json()["detail"]
    assert (await stored(lab, POOL))["active"] is True


async def test_deactivate_unknown_id_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    known = await client.post(f"/api/v1/envelopes/{ADMIN}/deactivate", headers=auth)
    assert known.status_code == 200

    response = await client.post("/api/v1/envelopes/999/deactivate", headers=auth)

    assert_problem(response, 404, "not_found")


# ---- auth -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/api/v1/envelopes", {"name": "Research"}),
        ("GET", "/api/v1/envelopes", None),
        ("POST", f"/api/v1/envelopes/{EVENTS}/rename", {"name": "Events"}),
        ("POST", f"/api/v1/envelopes/{EVENTS}/settings", {"target_cap": 1, "alloc_priority": 1}),
        ("POST", f"/api/v1/envelopes/{ADMIN}/deactivate", None),
    ],
)
async def test_every_envelope_route_requires_a_token(
    client: AsyncClient,
    lab: TestDb,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    request: dict[str, Any] = {"json": body} if body is not None else {}
    response = await client.request(method, path, **request)

    assert_problem(response, 401, "invalid_token")
    assert await envelope_count(lab) == 3  # nothing written
