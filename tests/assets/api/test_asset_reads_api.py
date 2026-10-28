"""The three asset reads end to end (roadmap step 9.3): asset state,
who-has-what, admin replacement queue.

Approved step brief answers this session (all the brief's labelled
suggestions):
- Q1=a `GET /api/v1/assets/state`, `GET /api/v1/assets/holdings`,
  `GET /api/v1/assets/replacement-queue` - nested under the assets router
  (no `GET /api/v1/assets/{asset_id}` route exists, so nothing is shadowed);
- Q2=a no `as_of` parameter - the views call the functions with the default
  `infinity` date (db/schema.sql:844-847), the 7.5 Q2=a pattern;
- Q3=a the state row keeps the function's own column names - `with_members`
  included (the 8.1 Q2=a rule), 11 keys;
- Q4=a all three reads live in `assets`;
- Q5=a each read in its view's own order - `asset_state` orders by name
  (db/schema.sql:829), `who_has_what` by member_name, asset_name (:845);
  no adapter ORDER BY (D-112 (1)).

Database rules these tests rely on (db/schema.sql, read this session):
- `asset_state()` (:819-830): every asset with its six counts, zero-filled
  (coalesce), GROUP BY a.id, ORDER BY a.name;
- `who_has_what` (:845): `asset_holdings()` rows - only NON-ZERO holdings
  (HAVING sum(held_d) <> 0, :841);
- `admin_replacement_queue` (:846-847): asset_state rows WHERE
  ownership = 'admin' AND damaged > 0.

Seeding goes through the 9.1 API routes (assets, members, events); counts
are asserted from the response rows, mirroring example 05's EXPECT lines
37-39/47-49 (ported DB-level at tests/db/test_assets.py).

Library APIs used, all verified in installed source this session:
- `httpx.AsyncClient.get` (httpx 0.28.1, _client.py:1751) and
  `.post` (:1838);
- `pytest.mark.parametrize` (pytest 9.1.1, _pytest/python.py:1231);
- the real `client` / `lab` / `auth` / `db` fixtures from tests/conftest.py.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import TestDb

STATE_FIELDS = {
    "asset_id",
    "asset_name",
    "ownership",
    "mode",
    "tag",
    "stock",
    "damaged",
    "with_members",
    "lost",
    "scrapped",
    "exchanged",
}
HOLDING_FIELDS = {"asset_id", "asset_name", "member_id", "member_name", "quantity"}


def assert_problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


async def asset(
    client: AsyncClient, auth: dict[str, str], name: str, ownership: str = "lab"
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/assets",
        json={"name": name, "mode": "counted", "ownership": ownership},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()


async def borrower(client: AsyncClient, auth: dict[str, str], name: str = "Ayesha") -> int:
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
) -> None:
    body: dict[str, Any] = {"kind": kind, "quantity": 10, "occurred_on": "2026-02-01"}
    body.update(overrides)
    response = await client.post(f"/api/v1/assets/{asset_id}/events", json=body, headers=auth)
    assert response.status_code == 201


async def damaged(client: AsyncClient, auth: dict[str, str], asset_id: int) -> None:
    await event(client, auth, asset_id, "damaged", quantity=1, note="burnt, reverse polarity")


async def read(client: AsyncClient, auth: dict[str, str], path: str) -> Any:
    return await client.get(f"/api/v1/assets/{path}", headers=auth)


# ---- asset state -------------------------------------------------------------


async def test_asset_state_returns_every_asset_with_its_counts(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example 05 lines 37-38: counts per asset, name order."""
    alpha = await asset(client, auth, "Alpha Kit")
    beta = await asset(client, auth, "Beta Kit")
    person = await borrower(client, auth)
    await event(client, auth, alpha["id"], "acquired", quantity=4, source="purchase")
    await event(client, auth, alpha["id"], "lent", quantity=2, member_id=person)
    await damaged(client, auth, alpha["id"])

    response = await read(client, auth, "state")

    assert response.status_code == 200
    rows = response.json()
    assert [row["asset_name"] for row in rows] == ["Alpha Kit", "Beta Kit"]
    assert all(set(row) == STATE_FIELDS for row in rows)
    alpha_row = rows[0]
    assert (alpha_row["asset_id"], alpha_row["ownership"], alpha_row["mode"], alpha_row["tag"]) == (
        alpha["id"],
        "lab",
        "counted",
        None,
    )
    assert (
        alpha_row["stock"],
        alpha_row["damaged"],
        alpha_row["with_members"],
        alpha_row["lost"],
        alpha_row["scrapped"],
        alpha_row["exchanged"],
    ) == (1, 1, 2, 0, 0, 0)  # the member-less damaged drops stock, not held (:701)
    assert beta["id"] == rows[1]["asset_id"]


async def test_asset_state_includes_a_zero_count_asset(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`asset_state` LEFT JOINs the effects and coalesces to zero (:824-827):
    an asset with no events is listed with all counts 0."""
    thing = await asset(client, auth, "Dust Collector")

    response = await read(client, auth, "state")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert (rows[0]["asset_id"], rows[0]["asset_name"]) == (thing["id"], "Dust Collector")
    assert all(
        rows[0][key] == 0
        for key in ("stock", "damaged", "with_members", "lost", "scrapped", "exchanged")
    )


# ---- who-has-what --------------------------------------------------------------


async def test_who_has_what_lists_what_members_hold(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example 05 line 49: (member, asset, quantity), member_name/asset_name
    order."""
    first = await asset(client, auth, "Alpha Kit")
    second = await asset(client, auth, "Zebra Kit")
    person = await borrower(client, auth, name="Ayesha")
    await event(client, auth, first["id"], "acquired", quantity=2, source="purchase")
    await event(client, auth, second["id"], "acquired", quantity=3, source="purchase")
    await event(client, auth, first["id"], "lent", quantity=2, member_id=person)
    await event(client, auth, second["id"], "lent", quantity=1, member_id=person)

    response = await read(client, auth, "holdings")

    assert response.status_code == 200
    rows = response.json()
    assert [(row["asset_name"], row["member_name"], row["quantity"]) for row in rows] == [
        ("Alpha Kit", "Ayesha", 2),
        ("Zebra Kit", "Ayesha", 1),
    ]
    assert all(set(row) == HOLDING_FIELDS for row in rows)
    assert all(row["member_id"] == person for row in rows)


async def test_who_has_what_drops_a_net_zero_holding(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """`asset_holdings` HAVING sum(held_d) <> 0 (db/schema.sql:841): a fully
    returned lend leaves the list."""
    thing = await asset(client, auth, "Alpha Kit")
    person = await borrower(client, auth)
    await event(client, auth, thing["id"], "acquired", quantity=2, source="purchase")
    await event(client, auth, thing["id"], "lent", quantity=1, member_id=person)
    await event(client, auth, thing["id"], "returned", quantity=1, member_id=person)

    response = await read(client, auth, "holdings")

    assert response.status_code == 200
    assert response.json() == []


# ---- admin replacement queue ---------------------------------------------------


async def test_the_replacement_queue_lists_only_admin_items_with_damage(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Example 05 lines 39/47: admin-owned damaged items await replacement;
    the lab's own damaged kit and undamaged admin kit do not
    (db/schema.sql:846-847)."""
    lab_kit = await asset(client, auth, "Alpha Kit", ownership="lab")
    admin_kit = await asset(client, auth, "Beta Kit", ownership="admin")
    healthy_admin = await asset(client, auth, "Gamma Kit", ownership="admin")
    await event(client, auth, lab_kit["id"], "acquired", quantity=1, source="purchase")
    await event(client, auth, admin_kit["id"], "acquired", quantity=1, source="purchase")
    await damaged(client, auth, lab_kit["id"])
    await damaged(client, auth, admin_kit["id"])

    response = await read(client, auth, "replacement-queue")

    assert response.status_code == 200
    rows = response.json()
    assert [row["asset_name"] for row in rows] == ["Beta Kit"]
    assert set(rows[0]) == STATE_FIELDS
    assert (rows[0]["asset_id"], rows[0]["ownership"], rows[0]["damaged"]) == (
        admin_kit["id"],
        "admin",
        1,
    )
    assert healthy_admin["id"] not in {row["asset_id"] for row in rows}


# ---- framework answers ---------------------------------------------------------


async def test_the_reads_are_bare_empty_arrays_when_nothing_exists(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    for path in ("state", "holdings", "replacement-queue"):
        response = await read(client, auth, path)
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.parametrize("path", ["state", "holdings", "replacement-queue"])
async def test_the_reads_require_a_token(client: AsyncClient, lab: TestDb, path: str) -> None:
    response = await client.get(f"/api/v1/assets/{path}")

    assert_problem(response, 401, "invalid_token")
