from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import PASSWORD, USERNAME, TestDb


async def test_login_returns_a_bearer_token_valid_for_72_hours(
    client: AsyncClient, db: TestDb
) -> None:
    response = await client.post("/auth/login", json={"username": USERNAME, "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    lifetime = datetime.fromisoformat(body["expires_at"]) - datetime.now(UTC)
    assert timedelta(hours=71, minutes=58) < lifetime <= timedelta(hours=72)


@pytest.mark.parametrize(
    ("username", "password"), [(USERNAME, "wrong password"), ("someone-else", PASSWORD)]
)
async def test_wrong_credentials_get_a_problem_json_401(
    client: AsyncClient, db: TestDb, username: str, password: str
) -> None:
    response = await client.post("/auth/login", json={"username": username, "password": password})

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_credentials"


async def test_a_protected_route_needs_a_token(client: AsyncClient, db: TestDb) -> None:
    deposit = {"amount": 100, "occurred_on": "2026-02-01", "source": "other"}
    response = await client.post("/deposits", json=deposit)

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


async def test_a_protected_route_rejects_a_garbage_token(client: AsyncClient, db: TestDb) -> None:
    deposit = {"amount": 100, "occurred_on": "2026-02-01", "source": "other"}
    response = await client.post(
        "/deposits", json=deposit, headers={"Authorization": "Bearer nope"}
    )

    assert response.status_code == 401
