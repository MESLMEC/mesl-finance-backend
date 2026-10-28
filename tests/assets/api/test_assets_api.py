"""API tests for asset records: create, list, edit (roadmap step 9.1).

Approved brief answers this session: Q1=a create, edit and the nine event
kinds are all part of the step; Q2=a a plain `GET /api/v1/assets` list in id
order with no counts (the counts are 9.3's `asset_state`); Q6=a an unknown
asset in the URL is 404 `not_found` naming the id (D-108's pattern).

Contract this file pins:
    POST /api/v1/assets              201  AssetOut
    GET  /api/v1/assets              200  [AssetOut]  id order
    POST /api/v1/assets/{id}/edit    200  AssetOut    partial body

AssetOut = {"id","name","mode","ownership","tag","note"}.

Database rules these tests rely on (db/schema.sql, read this session):
- `assets`: blank-name CHECK (:644), `note text NOT NULL DEFAULT ''` (:648),
  partial unique index on lower(tag) named `assets_tag_unique` (:651);
- `asset_guard` (:716-724): mode/ownership cannot change once the asset has
  events (P0001 -> 409 `rule_violation`; the 23505 on the tag is 409
  `unique`, D-059/D-068);
- `labapp` may INSERT assets and UPDATE (name, tag, note, mode, ownership)
  (:1194, :1199); asset records are not tenure-tied.

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

from tests.conftest import TestDb

FIELDS = {"id", "name", "mode", "ownership", "tag", "note"}


def asset_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"name": "ESP32 DevKit", "mode": "counted", "ownership": "lab"}
    body.update(overrides)
    return body


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def stored(db: TestDb, asset_id: int) -> dict[str, Any]:
    row = await db.owner.fetchrow(
        "SELECT id, name, mode::text AS mode, ownership::text AS ownership,"
        " tag, note FROM assets WHERE id = $1",
        asset_id,
    )
    assert row is not None
    return dict(row)


async def asset_count(db: TestDb) -> Any:
    return await db.owner.fetchval("SELECT count(*) FROM assets")


async def created(client: AsyncClient, auth: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/assets", json=asset_body(**overrides), headers=auth)
    assert response.status_code == 201
    return response.json()


async def acquired(client: AsyncClient, auth: dict[str, str], asset_id: int) -> Any:
    """Seed one event so `asset_guard` locks mode/ownership (Q1=a creates it)."""
    body = {"kind": "acquired", "quantity": 5, "occurred_on": "2026-02-01", "source": "purchase"}
    return await client.post(f"/api/v1/assets/{asset_id}/events", json=body, headers=auth)


# ---- create -----------------------------------------------------------------


async def test_create_asset_returns_201_and_it_is_stored(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/assets",
        json=asset_body(tag="ADM-001", note="main bench"),
        headers=auth,
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == FIELDS
    assert (body["name"], body["mode"], body["ownership"], body["tag"], body["note"]) == (
        "ESP32 DevKit",
        "counted",
        "lab",
        "ADM-001",
        "main bench",
    )
    assert await stored(lab, body["id"]) == body


async def test_create_asset_without_tag_defaults_to_null(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    body = await created(client, auth)

    assert body["tag"] is None
    assert body["note"] == ""
    assert await stored(lab, body["id"]) == body


@pytest.mark.parametrize("name", ["", "   "])
async def test_blank_name_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str], name: str
) -> None:
    """The app refuses it before SQL, on create and on edit (D-070 Q4 pattern)."""
    response = await client.post("/api/v1/assets", json=asset_body(name=name), headers=auth)

    assert_problem(response, 422, "validation_failed")
    assert await asset_count(lab) == 0

    thing = await created(client, auth)
    response = await client.post(
        f"/api/v1/assets/{thing['id']}/edit", json={"name": name}, headers=auth
    )

    assert_problem(response, 422, "validation_failed")
    assert (await stored(lab, thing["id"]))["name"] == "ESP32 DevKit"


async def test_extra_field_is_422(client: AsyncClient, lab: TestDb, auth: dict[str, str]) -> None:
    response = await client.post("/api/v1/assets", json=asset_body(colour="red"), headers=auth)

    assert_problem(response, 422, "validation_error")
    assert await asset_count(lab) == 0


async def test_duplicate_tag_is_409_unique(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """The partial unique index is case-insensitive (db/schema.sql:651)."""
    first = await created(client, auth, tag="ADM-001")
    assert first["tag"] == "ADM-001"

    response = await client.post(
        "/api/v1/assets", json=asset_body(name="Copy", tag="adm-001"), headers=auth
    )

    assert_problem(response, 409, "unique")
    assert "assets_tag_unique" in response.json()["detail"]
    assert await asset_count(lab) == 1


# ---- list -------------------------------------------------------------------


async def test_list_assets_is_id_ordered(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    empty = await client.get("/api/v1/assets", headers=auth)
    assert empty.status_code == 200
    assert empty.json() == []

    first = await created(client, auth)
    second = await created(client, auth, name="Multimeter", ownership="admin")

    response = await client.get("/api/v1/assets", headers=auth)

    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [first["id"], second["id"]]
    assert all(set(row) == FIELDS for row in rows)
    assert rows[1]["ownership"] == "admin"


# ---- edit -------------------------------------------------------------------


async def test_edit_changes_only_the_supplied_fields(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    thing = await created(client, auth, note="bench unit")

    response = await client.post(
        f"/api/v1/assets/{thing['id']}/edit",
        json={"name": "Oscilloscope (Rigol)", "tag": "LAB-9"},
        headers=auth,
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == FIELDS
    assert (body["name"], body["tag"], body["note"]) == (
        "Oscilloscope (Rigol)",
        "LAB-9",
        "bench unit",
    )
    assert await stored(lab, thing["id"]) == body


async def test_edit_unknown_asset_is_404(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    # Prove the route exists first: an unmatched path is a framework 404 too.
    thing = await created(client, auth)
    known = await client.post(
        f"/api/v1/assets/{thing['id']}/edit", json={"note": "x"}, headers=auth
    )
    assert known.status_code == 200

    response = await client.post("/api/v1/assets/9999/edit", json={"note": "x"}, headers=auth)

    assert_problem(response, 404, "not_found")
    assert "9999" in response.json()["detail"]


async def test_edit_mode_after_events_is_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`asset_guard` (:719-722): "mode and ownership cannot change once an
    asset has events; create a new asset"."""
    thing = await created(client, auth)
    seeded = await acquired(client, auth, thing["id"])
    assert seeded.status_code == 201

    response = await client.post(
        f"/api/v1/assets/{thing['id']}/edit", json={"mode": "individual"}, headers=auth
    )

    assert_problem(response, 409, "rule_violation")
    assert "cannot change" in response.json()["detail"]
    assert (await stored(lab, thing["id"]))["mode"] == "counted"


# ---- auth -------------------------------------------------------------------


async def test_creating_an_asset_without_a_token_is_401(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post("/api/v1/assets", json=asset_body())

    assert_problem(response, 401, "invalid_token")
    assert await asset_count(lab) == 0
