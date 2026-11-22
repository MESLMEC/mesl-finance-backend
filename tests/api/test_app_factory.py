"""The app factory serves the API under /api/v1 (step 4.3, P-002 confirmed)."""

from datetime import timedelta

from httpx import AsyncClient

from mesl_finance.auth.infrastructure.tokens import JwtTokenService
from tests.conftest import JWT_SECRET, PASSWORD, USERNAME, TestDb, idempotent

LOGIN = {"username": USERNAME, "password": PASSWORD}
DEPOSIT = {"amount": 100, "occurred_on": "2026-02-01", "source": "other"}


def _authorization() -> dict[str, str]:
    """A token issued by the same service the factory wires, with the test secret."""
    token = JwtTokenService(JWT_SECRET, ttl=timedelta(hours=72)).issue(USERNAME).token
    return {"Authorization": f"Bearer {token}"}


async def test_the_login_route_lives_under_the_api_prefix(client: AsyncClient, db: TestDb) -> None:
    response = await client.post("/api/v1/auth/login", json=LOGIN)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


async def test_the_ledger_route_lives_under_the_api_prefix(
    client: AsyncClient, lab: TestDb
) -> None:
    response = await client.post(
        "/api/v1/deposits", json=DEPOSIT, headers=idempotent(_authorization(), "deposit-1")
    )

    assert response.status_code == 201
    assert response.json()["id"] > 0


async def test_the_unprefixed_legacy_path_is_gone(client: AsyncClient, db: TestDb) -> None:
    response = await client.post("/auth/login", json=LOGIN)

    assert response.status_code == 404
