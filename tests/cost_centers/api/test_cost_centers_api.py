"""API tests for the cost-center actions (roadmap step 5.2).

Approved brief answers this session: Q8=b - the list also filters on `kind`
and `status`. Q1-Q7 and Q9 were left unanswered, so the brief's labelled
suggestions stand (same pattern as D-062/D-064/D-066):
Q1=a four action routes, Q2=a `POST /cost-centers/{id}/status`,
Q3=a create takes `name` + `kind` only (status starts `active`),
Q4=a blank names are 422 `validation_failed`, Q5=a unknown kinds/statuses are
409 `rule_violation` through the shared translator (PostgreSQL's CHECKs stay
the only rule), Q6=a `kind` is fixed at create, Q7=a any status may be set at
any time, Q9=a the unique test pins the 23505 constraint name.

Contract this file pins:
    POST /api/v1/cost-centers                  201  CostCenterOut
    GET  /api/v1/cost-centers                  200  [CostCenterOut] id order
         optional filters: ?kind=...  ?status=...
    POST /api/v1/cost-centers/{id}/rename      200  CostCenterOut   {"name"}
    POST /api/v1/cost-centers/{id}/status      200  CostCenterOut   {"status"}

CostCenterOut = {"id","name","kind","status"}.

Database rules these tests rely on (db/schema.sql:77-84, read this session):
- `kind` CHECK IN ('event','member_project','lab_project','competition')
  -> 23514 `cost_centers_kind_check` (verified live against the session
  template: pg_get_constraintdef, 2026-10-21);
- `status` CHECK IN ('planned','active','completed','cancelled') DEFAULT
  'active' -> 23514 `cost_centers_status_check` (verified the same way);
- `UNIQUE (kind, name)` -> 23505 `cost_centers_kind_name_key` (verified the
  same way), so the same name is legal under another kind;
- no guard trigger on the table: any status transition is allowed;
- `labapp` holds SELECT + INSERT/UPDATE on cost_centers (db/schema.sql:1195),
  no DELETE.

Library APIs used, all verified in installed source this session:
- `httpx.AsyncClient.get(..., params=...)` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1751-1762);
- `AsyncClient.request(method, url, **kwargs)` (same file);
- `asyncpg.Connection.fetchrow/fetchval` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:236-260);
- `pytest.mark.parametrize` (pytest 9.1.1,
  .venv/lib/python3.15/site-packages/_pytest/python.py:1231);
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb

FIELDS = {"id", "name", "kind", "status"}
KINDS = ["event", "member_project", "lab_project", "competition"]
STATUSES = ["planned", "active", "completed", "cancelled"]
UNIQUE_KEY = "cost_centers_kind_name_key"
KIND_CHECK = "cost_centers_kind_check"
STATUS_CHECK = "cost_centers_status_check"


def cc_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"name": "Robotics Workshop", "kind": "event"}
    body.update(overrides)
    return body


async def stored(db: TestDb, cost_center_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        "SELECT id, name, kind, status FROM cost_centers WHERE id = $1", cost_center_id
    )
    assert row is not None
    return dict(row)


async def cost_center_count(db: TestDb) -> Any:
    return await db.owner.fetchval("SELECT count(*) FROM cost_centers")


async def created(client: AsyncClient, auth: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/cost-centers", json=cc_body(**overrides), headers=auth)
    assert response.status_code == 201
    return response.json()


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


# ---- create -----------------------------------------------------------------


async def test_create_returns_201_and_the_stored_row(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/cost-centers", json=cc_body(kind="lab_project"), headers=auth
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == FIELDS
    assert (body["name"], body["kind"], body["status"]) == (
        "Robotics Workshop",
        "lab_project",
        "active",
    )
    assert await stored(lab, body["id"]) == body


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "event"},
        {"name": "Robotics Workshop"},
        {},
    ],
)
async def test_create_without_a_field_is_422_validation_error(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], body: dict[str, Any]
) -> None:
    response = await client.post("/api/v1/cost-centers", json=body, headers=auth)

    assert_problem(response, 422, "validation_error")
    assert await cost_center_count(lab) == 0


@pytest.mark.parametrize("kind", KINDS)
async def test_create_accepts_every_kind_the_schema_allows(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], kind: str
) -> None:
    response = await client.post("/api/v1/cost-centers", json=cc_body(kind=kind), headers=auth)

    assert response.status_code == 201
    assert response.json()["kind"] == kind


async def test_create_a_taken_name_in_the_same_kind_is_409_unique(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await created(client, auth)

    response = await client.post("/api/v1/cost-centers", json=cc_body(), headers=auth)

    assert_problem(response, 409, "unique")
    assert UNIQUE_KEY in response.json()["detail"]  # Q9=a
    assert await cost_center_count(lab) == 1


async def test_create_the_same_name_under_another_kind_is_201(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await created(client, auth, name="Robotics", kind="event")

    response = await client.post(
        "/api/v1/cost-centers", json=cc_body(name="Robotics", kind="competition"), headers=auth
    )

    assert response.status_code == 201
    assert await cost_center_count(lab) == 2


@pytest.mark.parametrize("name", ["", "   ", "\t\n "])
async def test_create_with_a_blank_name_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], name: str
) -> None:
    response = await client.post("/api/v1/cost-centers", json=cc_body(name=name), headers=auth)

    assert_problem(response, 422, "validation_failed")
    assert await cost_center_count(lab) == 0


async def test_create_with_an_unknown_kind_is_409_rule_violation(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Q5=a: the schema's CHECK owns the four kinds; the app does not duplicate it."""
    response = await client.post(
        "/api/v1/cost-centers", json=cc_body(kind="workshop"), headers=auth
    )

    assert_problem(response, 409, "rule_violation")
    assert KIND_CHECK in response.json()["detail"]
    assert await cost_center_count(lab) == 0


# ---- list (Q8=b: the list filters on kind and status) ------------------------


async def test_list_returns_every_cost_center_in_id_order(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    first = await created(client, auth, name="Robotics", kind="event")
    second = await created(client, auth, name="Line Follower", kind="lab_project")

    response = await client.get("/api/v1/cost-centers", headers=auth)

    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [first["id"], second["id"]]
    assert all(set(row) == FIELDS for row in rows)  # no money, no extra keys


async def test_list_filters_by_kind(client: AsyncClient, lab: TestDb, auth: dict[str, str]) -> None:
    event = await created(client, auth, name="Robotics", kind="event")
    await created(client, auth, name="Line Follower", kind="lab_project")

    response = await client.get("/api/v1/cost-centers", params={"kind": "event"}, headers=auth)

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [event["id"]]


async def test_list_filters_by_status(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await created(client, auth, name="Robotics", kind="event")
    completed = await created(client, auth, name="Line Follower", kind="lab_project")
    moved = await client.post(
        f"/api/v1/cost-centers/{completed['id']}/status",
        json={"status": "completed"},
        headers=auth,
    )
    assert moved.status_code == 200

    response = await client.get(
        "/api/v1/cost-centers", params={"status": "completed"}, headers=auth
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [completed["id"]]


# ---- rename -----------------------------------------------------------------


async def test_rename_changes_the_name(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await created(client, auth, kind="member_project")

    response = await client.post(
        f"/api/v1/cost-centers/{cost_center['id']}/rename",
        json={"name": "Robotics Project"},
        headers=auth,
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["kind"], body["status"]) == (
        "Robotics Project",
        "member_project",
        "active",
    )
    assert (await stored(lab, cost_center["id"]))["name"] == "Robotics Project"


async def test_rename_to_a_name_taken_in_the_same_kind_is_409_unique(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await created(client, auth, name="Robotics", kind="event")
    other = await created(client, auth, name="Workshop", kind="event")

    response = await client.post(
        f"/api/v1/cost-centers/{other['id']}/rename", json={"name": "Robotics"}, headers=auth
    )

    assert_problem(response, 409, "unique")
    assert UNIQUE_KEY in response.json()["detail"]
    assert (await stored(lab, other["id"]))["name"] == "Workshop"


async def test_rename_to_a_name_taken_in_another_kind_is_200(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await created(client, auth, name="Robotics", kind="event")
    other = await created(client, auth, name="Robotics", kind="competition")

    response = await client.post(
        f"/api/v1/cost-centers/{other['id']}/rename",
        json={"name": "Robotics Cup"},
        headers=auth,
    )

    assert response.status_code == 200
    assert (response.json()["name"], response.json()["kind"]) == ("Robotics Cup", "competition")


async def test_rename_a_blank_name_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await created(client, auth)

    response = await client.post(
        f"/api/v1/cost-centers/{cost_center['id']}/rename", json={"name": "  "}, headers=auth
    )

    assert_problem(response, 422, "validation_failed")
    assert (await stored(lab, cost_center["id"]))["name"] == "Robotics Workshop"


async def test_rename_unknown_id_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # Prove the route exists first: an unmatched path is a framework 404 too.
    cost_center = await created(client, auth)
    known = await client.post(
        f"/api/v1/cost-centers/{cost_center['id']}/rename",
        json={"name": "Robotics Project"},
        headers=auth,
    )
    assert known.status_code == 200

    response = await client.post(
        "/api/v1/cost-centers/999/rename", json={"name": "Nowhere"}, headers=auth
    )

    assert_problem(response, 404, "not_found")


# ---- status (Q7=a: the schema allows any value at any time) ------------------


async def test_status_moves_through_every_value(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await created(client, auth, kind="event")

    for status in STATUSES:
        response = await client.post(
            f"/api/v1/cost-centers/{cost_center['id']}/status",
            json={"status": status},
            headers=auth,
        )

        assert response.status_code == 200
        body = response.json()
        assert set(body) == FIELDS
        assert (body["status"], body["name"], body["kind"]) == (
            status,
            "Robotics Workshop",
            "event",
        )
        assert (await stored(lab, cost_center["id"]))["status"] == status


async def test_status_with_an_unknown_value_is_409_rule_violation(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await created(client, auth)

    response = await client.post(
        f"/api/v1/cost-centers/{cost_center['id']}/status",
        json={"status": "paused"},
        headers=auth,
    )

    assert_problem(response, 409, "rule_violation")
    assert STATUS_CHECK in response.json()["detail"]
    assert (await stored(lab, cost_center["id"]))["status"] == "active"


async def test_status_unknown_id_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    cost_center = await created(client, auth)
    known = await client.post(
        f"/api/v1/cost-centers/{cost_center['id']}/status",
        json={"status": "completed"},
        headers=auth,
    )
    assert known.status_code == 200

    response = await client.post(
        "/api/v1/cost-centers/999/status", json={"status": "completed"}, headers=auth
    )

    assert_problem(response, 404, "not_found")


# ---- auth -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/api/v1/cost-centers", {"name": "Robotics", "kind": "event"}),
        ("GET", "/api/v1/cost-centers", None),
        ("POST", "/api/v1/cost-centers/1/rename", {"name": "Robotics"}),
        ("POST", "/api/v1/cost-centers/1/status", {"status": "completed"}),
    ],
)
async def test_every_cost_center_route_requires_a_token(
    client: AsyncClient,
    lab: TestDb,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    request: dict[str, Any] = {"json": body} if body is not None else {}
    response = await client.request(method, path, **request)

    assert_problem(response, 401, "invalid_token")
    assert await cost_center_count(lab) == 0  # nothing written
