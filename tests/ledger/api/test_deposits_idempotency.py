"""Issue #4, slice 1: the HTTP face of the idempotency mechanism, on deposits.

The approved brief (issue #4 triage ACCEPT-MODIFIED, user's answers):
- the `Idempotency-Key` header is REQUIRED on the write endpoints (Q3=b);
- a missing key is FastAPI's own 422 `validation_error` (Q1=a: it is a
  request-shape error, exactly like a missing required body field);
- the same actor + the same key + the same request replays the ORIGINAL 201
  body and writes nothing the second time (Q6=a, "full 201 replay");
- the same actor + the same key + a DIFFERENT request is a 409 conflict
  (Q4=a);
- a FAILED write does not consume the key: the retry after the cause is fixed
  writes normally;
- a blank key, or one longer than 255 characters, is refused by the app
  (Q5=a).

Only `POST /api/v1/deposits` is in scope for this slice (the other six money
endpoints are slice 2), so these tests exercise the deposits route only.

Library APIs verified in installed source this session (AGENTS.md section 3):
- fastapi/param_functions.py:701 `Header(...)` is the header parameter
  factory; fastapi/params.py:303 `class Header` carries `alias` and
  `convert_underscores`;
- fastapi/dependencies/utils.py:524-525: a header parameter's alias is the
  parameter name with underscores replaced by dashes, so the Python name
  `idempotency_key` is read from the `Idempotency-Key` header;
- fastapi/exceptions.py `RequestValidationError` is translated by the app's
  own handler into 422 `validation_error` problem+json
  (shared/api/problems.py:71-80) — the same code a bad body field answers;
- httpx `AsyncClient.post(..., headers=...)` sends the header verbatim;
  header names are case-insensitive on the wire.
"""

from typing import Any

from httpx import AsyncClient

from tests.conftest import TestDb

POOL = 1
KEY = "deposit-key-1"
OTHER_KEY = "deposit-key-2"


def deposit(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"amount": 500, "occurred_on": "2026-02-01", "source": "sponsorship"}
    body.update(overrides)
    return body


async def entry_count(db: TestDb) -> int:
    return int(await db.app.fetchval("SELECT count(*) FROM ledger_transactions"))


async def pool_balance(db: TestDb) -> int:
    value = await db.app.fetchval("SELECT balance FROM envelope_balances WHERE id = $1", POOL)
    return int(value)


async def test_a_deposit_without_a_key_is_422(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """The header is required: a deposit with no Idempotency-Key is refused."""
    response = await client.post("/api/v1/deposits", json=deposit(), headers=auth)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"
    assert await entry_count(lab) == 0


async def test_a_duplicate_key_replays_the_original_201(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """The same key with the same body answers the same 201 and writes once."""
    headers = {**auth, "Idempotency-Key": KEY}

    first = await client.post("/api/v1/deposits", json=deposit(), headers=headers)
    second = await client.post("/api/v1/deposits", json=deposit(), headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()
    assert await entry_count(lab) == 1
    assert await pool_balance(lab) == 500


async def test_the_same_key_with_a_different_body_is_a_409(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """The same key with a DIFFERENT body is refused: the client reused a key."""
    headers = {**auth, "Idempotency-Key": KEY}

    first = await client.post("/api/v1/deposits", json=deposit(amount=500), headers=headers)
    second = await client.post("/api/v1/deposits", json=deposit(amount=900), headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.headers["content-type"].startswith("application/problem+json")
    assert await entry_count(lab) == 1
    assert await pool_balance(lab) == 500


async def test_a_different_key_writes_again(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """Two different keys are two different deposits: nothing is deduplicated."""
    first = await client.post(
        "/api/v1/deposits", json=deposit(), headers={**auth, "Idempotency-Key": KEY}
    )
    second = await client.post(
        "/api/v1/deposits", json=deposit(), headers={**auth, "Idempotency-Key": OTHER_KEY}
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert await entry_count(lab) == 2
    assert await pool_balance(lab) == 1000


async def test_a_failed_write_does_not_consume_the_key(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """A refused deposit leaves the key free: the retry after the fix writes."""
    headers = {**auth, "Idempotency-Key": KEY}

    refused = await client.post(
        "/api/v1/deposits", json=deposit(occurred_on="2025-12-31"), headers=headers
    )
    assert refused.status_code == 409
    assert await entry_count(lab) == 0

    retried = await client.post("/api/v1/deposits", json=deposit(), headers=headers)

    assert retried.status_code == 201
    assert await entry_count(lab) == 1
    assert await pool_balance(lab) == 500


async def test_a_blank_key_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """A blank key is refused by the app, before any write."""
    response = await client.post(
        "/api/v1/deposits", json=deposit(), headers={**auth, "Idempotency-Key": "   "}
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert await entry_count(lab) == 0


async def test_a_key_longer_than_255_characters_is_refused(
    client: AsyncClient, lab: TestDb, auth: dict[str, str]
) -> None:
    """A key longer than 255 characters is refused by the app."""
    response = await client.post(
        "/api/v1/deposits", json=deposit(), headers={**auth, "Idempotency-Key": "k" * 256}
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert await entry_count(lab) == 0
