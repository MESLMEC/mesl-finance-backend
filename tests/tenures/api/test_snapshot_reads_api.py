"""The three handover snapshot reads end to end (roadmap step 11.1): member,
asset and holding snapshots saved by `close_tenure`.

Approved step brief answers this session (all the brief's labelled
suggestions): Q1=a `GET /api/v1/tenures/{tenure_id}/member-snapshots`,
`/asset-snapshots` and `/holding-snapshots`; Q3=a bare arrays with every
stored table column, `tenure_id` included, in each table's primary-key order;
Q4=a an unknown tenure answers 404 naming the id while an existing tenure with
no snapshot rows answers `[]`.

Database rules these tests rely on (db/schema.sql, read this session):
`close_tenure` writes `tenure_member_snapshots` (from `member_standing`),
`tenure_asset_snapshots` and `tenure_holding_snapshots` (from the
`snapshot_assets` trigger, :896-908). The snapshot tables are append-only, so
the reads just return what was saved.

Seeding goes through direct SQL on the `lab` fixture: a member with a
membership period, an asset with an `acquired` then `lent` event (which puts a
non-zero holding on the register). `member_standing` returns one row per
member even without fee rates, so a bare member produces a zero snapshot row.

Library APIs used, all verified in installed source this session:
- asyncpg 0.32.0 `Connection.execute` / `fetch` / `transaction`
  (connection.py:285,320,689);
- httpx `AsyncClient.get` (0.28.1, _client.py:1751) and `.post` (:1838);
- pytest.mark.parametrize (pytest 9.1.1);
- the real `client` / `lab` / `auth` fixtures from tests/conftest.py.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb

SNAPSHOT_ROUTES = ("member-snapshots", "asset-snapshots", "holding-snapshots")


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def close_tenure(client: AsyncClient, auth: dict[str, str]) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/tenures/close",
        json={"close_on": "2026-01-31", "next_name": "2026"},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()


async def seed_handover(db: TestDb) -> None:
    """member 1 + asset 1 (acquired 5, lent 1 to member 1) -> one snapshot row each."""
    async with db.app.transaction():
        await db.app.execute("INSERT INTO members(name) VALUES ('Ayesha')")
        await db.app.execute(
            "INSERT INTO membership_periods(member_id, start_date) VALUES (1, '2026-01-01')"
        )
        await db.app.execute(
            "INSERT INTO assets(name, mode, ownership) VALUES ('Laptop', 'counted', 'lab')"
        )
        await db.app.execute(
            "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source)"
            " VALUES (1, 'acquired', 5, '2026-01-02', 'treasurer', 'admin')"
        )
        await db.app.execute(
            "INSERT INTO asset_events"
            "(asset_id, kind, quantity, occurred_on, recorded_by, member_id)"
            " VALUES (1, 'lent', 1, '2026-01-03', 'treasurer', 1)"
        )


async def seed_order(db: TestDb) -> None:
    """Two members and two assets, both lent to member 1, to pin primary-key order."""
    async with db.app.transaction():
        await db.app.execute("INSERT INTO members(name) VALUES ('Zara'), ('Adam')")
        await db.app.execute(
            "INSERT INTO membership_periods(member_id, start_date)"
            " VALUES (1, '2026-01-01'), (2, '2026-01-01')"
        )
        await db.app.execute(
            "INSERT INTO assets(name, mode, ownership)"
            " VALUES ('Beta', 'counted', 'lab'), ('Alpha', 'counted', 'lab')"
        )
        await db.app.execute(
            "INSERT INTO asset_events(asset_id, kind, quantity, occurred_on, recorded_by, source)"
            " VALUES (1, 'acquired', 5, '2026-01-02', 'treasurer', 'admin'),"
            " (2, 'acquired', 5, '2026-01-02', 'treasurer', 'admin')"
        )
        await db.app.execute(
            "INSERT INTO asset_events"
            "(asset_id, kind, quantity, occurred_on, recorded_by, member_id)"
            " VALUES (1, 'lent', 1, '2026-01-03', 'treasurer', 1),"
            " (2, 'lent', 1, '2026-01-03', 'treasurer', 1)"
        )


# ---- the saved rows ----------------------------------------------------------


async def test_member_snapshots_return_the_saved_rows(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_handover(lab)
    await close_tenure(client, auth)

    response = await client.get("/api/v1/tenures/1/member-snapshots", headers=auth)

    assert response.status_code == 200
    saved = await lab.app.fetch(
        "SELECT tenure_id, member_id, as_of, weeks_owed, owed, credits, balance, weeks_overdue"
        " FROM tenure_member_snapshots ORDER BY tenure_id, member_id"
    )
    assert len(saved) == 1
    assert response.json() == [
        {
            "tenure_id": int(r["tenure_id"]),
            "member_id": int(r["member_id"]),
            "as_of": r["as_of"].isoformat(),
            "weeks_owed": int(r["weeks_owed"]),
            "owed": int(r["owed"]),
            "credits": int(r["credits"]),
            "balance": int(r["balance"]),
            "weeks_overdue": int(r["weeks_overdue"]),
        }
        for r in saved
    ]


async def test_asset_snapshots_return_the_saved_rows(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_handover(lab)
    await close_tenure(client, auth)

    response = await client.get("/api/v1/tenures/1/asset-snapshots", headers=auth)

    assert response.status_code == 200
    saved = await lab.app.fetch(
        "SELECT tenure_id, asset_id, as_of, stock, damaged, held, lost, scrapped, exchanged"
        " FROM tenure_asset_snapshots ORDER BY tenure_id, asset_id"
    )
    assert len(saved) == 1
    assert response.json() == [
        {
            "tenure_id": int(r["tenure_id"]),
            "asset_id": int(r["asset_id"]),
            "as_of": r["as_of"].isoformat(),
            "stock": int(r["stock"]),
            "damaged": int(r["damaged"]),
            "held": int(r["held"]),
            "lost": int(r["lost"]),
            "scrapped": int(r["scrapped"]),
            "exchanged": int(r["exchanged"]),
        }
        for r in saved
    ]


async def test_holding_snapshots_return_the_saved_rows(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_handover(lab)
    await close_tenure(client, auth)

    response = await client.get("/api/v1/tenures/1/holding-snapshots", headers=auth)

    assert response.status_code == 200
    saved = await lab.app.fetch(
        "SELECT tenure_id, asset_id, member_id, quantity FROM tenure_holding_snapshots"
        " ORDER BY tenure_id, asset_id, member_id"
    )
    assert len(saved) == 1
    assert response.json() == [
        {
            "tenure_id": int(r["tenure_id"]),
            "asset_id": int(r["asset_id"]),
            "member_id": int(r["member_id"]),
            "quantity": int(r["quantity"]),
        }
        for r in saved
    ]


# ---- empty and ordering ------------------------------------------------------


async def test_empty_snapshots_return_empty_arrays(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await close_tenure(client, auth)

    for route in SNAPSHOT_ROUTES:
        response = await client.get(f"/api/v1/tenures/1/{route}", headers=auth)
        assert response.status_code == 200
        assert response.json() == []


async def test_snapshot_rows_use_primary_key_order(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    await seed_order(lab)
    await close_tenure(client, auth)

    members = (await client.get("/api/v1/tenures/1/member-snapshots", headers=auth)).json()
    assert [row["member_id"] for row in members] == [1, 2]

    assets = (await client.get("/api/v1/tenures/1/asset-snapshots", headers=auth)).json()
    assert [row["asset_id"] for row in assets] == [1, 2]

    holdings = (await client.get("/api/v1/tenures/1/holding-snapshots", headers=auth)).json()
    assert [(row["asset_id"], row["member_id"]) for row in holdings] == [(1, 1), (2, 1)]


# ---- 401 / 404 / 422 ---------------------------------------------------------


@pytest.mark.parametrize("route", SNAPSHOT_ROUTES)
async def test_snapshot_reads_require_authentication(
    route: str, client: AsyncClient, lab: TestDb
) -> None:
    response = await client.get(f"/api/v1/tenures/1/{route}")

    assert_problem(response, 401, "invalid_token")


@pytest.mark.parametrize("route", SNAPSHOT_ROUTES)
async def test_unknown_tenure_snapshot_read_is_404(
    route: str, client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.get(f"/api/v1/tenures/999/{route}", headers=auth)

    assert_problem(response, 404, "not_found")
    assert "999" in response.json()["detail"]


@pytest.mark.parametrize("route", SNAPSHOT_ROUTES)
async def test_non_numeric_tenure_id_is_422(
    route: str, client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    response = await client.get(f"/api/v1/tenures/abc/{route}", headers=auth)

    assert_problem(response, 422, "validation_error")
