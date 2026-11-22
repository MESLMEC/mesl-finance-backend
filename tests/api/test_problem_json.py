"""Every API error is an RFC 9457 problem+json body (step 4.3).

The framework's own HTTP errors (404, 405) are translated too: the `code` member comes
from a status map, `title` is the standard phrase (http.client.responses), `detail` is
the exception's detail, and the exception's headers (Allow, ...) are forwarded.
"""

from datetime import timedelta

from httpx import AsyncClient

from mesl_finance.auth.infrastructure.tokens import JwtTokenService
from tests.conftest import JWT_SECRET, USERNAME, TestDb, idempotent

DEPOSIT = {"amount": 100, "occurred_on": "2026-02-01", "source": "other"}


def _authorization() -> dict[str, str]:
    """A token issued by the same service the factory wires, with the test secret."""
    token = JwtTokenService(JWT_SECRET, ttl=timedelta(hours=72)).issue(USERNAME).token
    return {"Authorization": f"Bearer {token}"}


async def test_a_domain_error_is_problem_json_with_code_and_type(
    client: AsyncClient, db: TestDb
) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"username": USERNAME, "password": "wrong password"}
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["www-authenticate"] == "Bearer"
    body = response.json()
    assert body["type"] == "urn:mesl:problem:invalid_credentials"
    assert body["code"] == "invalid_credentials"
    assert body["title"] == "Wrong username or password"
    assert body["status"] == 401


async def test_a_request_validation_error_is_problem_json_with_the_field_errors(
    client: AsyncClient, db: TestDb
) -> None:
    response = await client.post("/api/v1/auth/login", json={"username": USERNAME})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["status"] == 422
    assert any(error["loc"] == ["body", "password"] for error in body["errors"])


async def test_an_unknown_route_is_a_problem_json_404(client: AsyncClient, db: TestDb) -> None:
    response = await client.get("/api/v1/no-such-route")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "urn:mesl:problem:not_found"
    assert body["code"] == "not_found"
    assert body["title"] == "Not Found"
    assert body["status"] == 404


async def test_a_wrong_method_is_a_problem_json_405(client: AsyncClient, db: TestDb) -> None:
    response = await client.delete("/api/v1/auth/login")

    assert response.status_code == 405
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["allow"] == "POST"
    body = response.json()
    assert body["type"] == "urn:mesl:problem:method_not_allowed"
    assert body["code"] == "method_not_allowed"
    assert body["title"] == "Method Not Allowed"
    assert body["status"] == 405


async def test_a_rule_violation_is_a_problem_json_409(client: AsyncClient, lab: TestDb) -> None:
    response = await client.post(
        "/api/v1/deposits",
        json={**DEPOSIT, "occurred_on": "2025-12-31"},
        headers=idempotent(_authorization(), "deposit-1"),
    )

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "urn:mesl:problem:date_before_tenure"
    assert body["code"] == "date_before_tenure"
    assert body["status"] == 409
