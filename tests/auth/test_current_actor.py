"""The route dependency: a bearer access token names the actor, or the request is a 401."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from mesl_finance.auth.infrastructure.tokens import JwtTokenService
from tests.conftest import JWT_SECRET, USERNAME

DEPOSIT = {"amount": 100, "occurred_on": "2026-02-01", "source": "other"}


def _expired_token() -> str:
    """A token issued 73 hours ago with the app's 72-hour TTL."""
    issued_at = datetime.now(UTC) - timedelta(hours=73)
    return (
        JwtTokenService(JWT_SECRET, ttl=timedelta(hours=72), now=lambda: issued_at)
        .issue(USERNAME)
        .token
    )


async def test_an_expired_token_is_a_401_problem(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/deposits", json=DEPOSIT, headers={"Authorization": f"Bearer {_expired_token()}"}
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_token"


async def test_a_token_signed_with_another_secret_is_a_401_problem(client: AsyncClient) -> None:
    forged = JwtTokenService("another-secret-" + "z" * 32, ttl=timedelta(hours=72)).issue(USERNAME)
    response = await client.post(
        "/api/v1/deposits", json=DEPOSIT, headers={"Authorization": f"Bearer {forged.token}"}
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_token"


async def test_a_non_bearer_authorization_header_is_a_401_problem(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/deposits", json=DEPOSIT, headers={"Authorization": "Basic abc"}
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_token"
