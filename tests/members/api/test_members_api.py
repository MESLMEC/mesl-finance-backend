"""API tests for the member actions (roadmap step 7.1).

Approved brief answers this session: Q6=b - a blank member name is refused by
the APP with 422 `validation_failed`, like cost centers (D-070 Q4), although
`db/schema.sql:89` also carries `CHECK (length(btrim(name)) > 0)`. Every other
question took the brief's labelled suggestion: Q1=a member edit is part of the
step, Q2=a the period read is part of it, Q3=a an unknown member addressed in
the URL is 404 `not_found` (adapter pre-check), Q4=a ending with nothing open
is 404, Q5=a the end action picks the single open period, Q7=a `MemberOut` is
`{id,name,batch,note}`, Q8=a the routes listed here, Q9=a the shared
translator gains one 23P01 rule (pinned in
tests/shared/test_error_translator.py), Q10=a a partial edit where only the
supplied fields change and an explicit null clears `batch`, Q11=a create takes
`name` plus optional `batch`/`note`.

Contract this file pins:
    POST /api/v1/members                 201  MemberOut
    GET  /api/v1/members                 200  [MemberOut]  id order
    POST /api/v1/members/{id}/edit       200  MemberOut    partial body

MemberOut = {"id","name","batch","note"}.

Database rules these tests rely on (db/schema.sql, read this session):
- `members`: `name text NOT NULL CHECK (length(btrim(name)) > 0)`, `batch`
  text, `note text NOT NULL DEFAULT ''` (:87-93);
- `labapp` may INSERT members and UPDATE (name, batch, note) (:1193, :1197);
- `members` carries no guard trigger, so it is not tied to a tenure.

Library APIs used, all verified in installed source this session:
- `httpx.AsyncClient.get/post/request` (httpx 0.28.1,
  .venv/lib/python3.15/site-packages/httpx/_client.py:1485,1751,1838);
- `asyncpg.Connection.fetchrow/fetchval` (asyncpg-stubs 0.32.0,
  .venv/lib/python3.15/site-packages/asyncpg-stubs/connection.pyi:236-266);
- `pytest.mark.parametrize` (pytest 9.1.1,
  .venv/lib/python3.15/site-packages/_pytest/python.py:1231);
- pydantic 2.14.1 turns an ISO `"YYYY-MM-DD"` string into a `date` and a bad
  string into a `ValidationError` (verified live this session; the app's
  `RequestValidationError` handler answers 422 `validation_error`);
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb

FIELDS = {"id", "name", "batch", "note"}


def member_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"name": "Ayesha"}
    body.update(overrides)
    return body


async def stored(db: TestDb, member_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        "SELECT id, name, batch, note FROM members WHERE id = $1", member_id
    )
    assert row is not None
    return dict(row)


async def member_count(db: TestDb) -> Any:
    return await db.owner.fetchval("SELECT count(*) FROM members")


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def created(client: AsyncClient, auth: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/members", json=member_body(**overrides), headers=auth)
    assert response.status_code == 201
    return response.json()


# ---- create -----------------------------------------------------------------


async def test_create_member_returns_201_and_it_is_stored(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post("/api/v1/members", json=member_body(), headers=auth)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == FIELDS
    assert (body["name"], body["batch"], body["note"]) == ("Ayesha", None, "")
    assert await stored(lab, body["id"]) == body


async def test_create_member_with_batch_and_note(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/members",
        json=member_body(batch="2024", note="joined in January"),
        headers=auth,
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["batch"], body["note"]) == ("2024", "joined in January")
    assert await stored(lab, body["id"]) == body


@pytest.mark.parametrize("name", ["", "   ", "\t\n "])
async def test_blank_name_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], name: str
) -> None:
    """Q6=b: the app refuses it before SQL, on create and on edit."""
    response = await client.post("/api/v1/members", json=member_body(name=name), headers=auth)

    assert_problem(response, 422, "validation_failed")
    assert await member_count(lab) == 0

    member = await created(client, auth)
    response = await client.post(
        f"/api/v1/members/{member['id']}/edit", json={"name": name}, headers=auth
    )

    assert_problem(response, 422, "validation_failed")
    assert (await stored(lab, member["id"]))["name"] == "Ayesha"


async def test_extra_field_is_422(client: AsyncClient, lab: TestDb, auth: dict[str, str]) -> None:
    response = await client.post("/api/v1/members", json=member_body(colour="red"), headers=auth)

    assert_problem(response, 422, "validation_error")
    assert await member_count(lab) == 0


# ---- list -------------------------------------------------------------------


async def test_list_members_is_id_ordered(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    first = await created(client, auth)
    second = await created(client, auth, name="Bashir")

    response = await client.get("/api/v1/members", headers=auth)

    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [first["id"], second["id"]]
    assert all(set(row) == FIELDS for row in rows)  # no extra keys


# ---- edit (Q10=a: partial, explicit null clears batch) -----------------------


async def test_edit_member_partial(client: AsyncClient, lab: TestDb, auth: dict[str, str]) -> None:
    member = await created(client, auth, batch="2024", note="joined")

    response = await client.post(
        f"/api/v1/members/{member['id']}/edit",
        json={"note": "left the lab"},
        headers=auth,
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == FIELDS
    assert (body["name"], body["batch"], body["note"]) == (
        "Ayesha",
        "2024",
        "left the lab",
    )
    assert await stored(lab, member["id"]) == body


async def test_edit_member_explicit_null_clears_batch(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await created(client, auth, batch="2024")

    response = await client.post(
        f"/api/v1/members/{member['id']}/edit", json={"batch": None}, headers=auth
    )

    assert response.status_code == 200
    assert response.json()["batch"] is None
    assert (await stored(lab, member["id"]))["batch"] is None


async def test_edit_with_empty_body_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    member = await created(client, auth)

    response = await client.post(f"/api/v1/members/{member['id']}/edit", json={}, headers=auth)

    assert_problem(response, 422, "validation_failed")
    assert (await stored(lab, member["id"]))["note"] == ""


async def test_edit_unknown_member_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # Prove the route exists first: an unmatched path is a framework 404 too.
    member = await created(client, auth)
    known = await client.post(
        f"/api/v1/members/{member['id']}/edit", json={"note": "known"}, headers=auth
    )
    assert known.status_code == 200

    response = await client.post("/api/v1/members/999/edit", json={"note": "nowhere"}, headers=auth)

    assert_problem(response, 404, "not_found")


# ---- auth -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/api/v1/members", {"name": "Ayesha"}),
        ("GET", "/api/v1/members", None),
        ("POST", "/api/v1/members/1/edit", {"note": "x"}),
        ("POST", "/api/v1/members/1/periods/start", {"start_date": "2026-02-01"}),
        ("POST", "/api/v1/members/1/periods/end", {"end_date": "2026-06-30"}),
        ("GET", "/api/v1/members/1/periods", None),
    ],
)
async def test_members_without_token_is_401(
    client: AsyncClient,
    lab: TestDb,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    request: dict[str, Any] = {"json": body} if body is not None else {}
    response = await client.request(method, path, **request)

    assert_problem(response, 401, "invalid_token")
    assert await member_count(lab) == 0  # nothing written
