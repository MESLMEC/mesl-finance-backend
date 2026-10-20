from datetime import UTC, datetime, timedelta

import jwt
import pytest

from mesl_finance.auth.infrastructure.tokens import JwtTokenService
from mesl_finance.shared.errors import InvalidToken

SECRET = "unit-test-secret-" + "y" * 32


def test_a_token_roundtrips_to_its_subject() -> None:
    service = JwtTokenService(SECRET, ttl=timedelta(hours=72))
    assert service.verify(service.issue("treasurer").token) == "treasurer"


def test_the_token_expires_after_the_ttl() -> None:
    now = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
    token = JwtTokenService(SECRET, ttl=timedelta(hours=72), now=lambda: now).issue("treasurer")
    assert token.expires_at == now + timedelta(hours=72)


def test_an_expired_token_is_rejected() -> None:
    long_ago = datetime.now(UTC) - timedelta(hours=100)
    old = JwtTokenService(SECRET, ttl=timedelta(hours=72), now=lambda: long_ago).issue("treasurer")
    with pytest.raises(InvalidToken):
        JwtTokenService(SECRET, ttl=timedelta(hours=72)).verify(old.token)


def test_a_token_signed_with_another_secret_is_rejected() -> None:
    forged = JwtTokenService("another-secret-" + "z" * 32, ttl=timedelta(hours=1)).issue(
        "treasurer"
    )
    with pytest.raises(InvalidToken):
        JwtTokenService(SECRET, ttl=timedelta(hours=72)).verify(forged.token)


def test_garbage_is_rejected() -> None:
    with pytest.raises(InvalidToken):
        JwtTokenService(SECRET, ttl=timedelta(hours=72)).verify("not-a-jwt")


def test_a_token_without_a_subject_is_rejected() -> None:
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    token = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
        {"exp": expires_at}, SECRET, algorithm="HS256"
    )
    with pytest.raises(InvalidToken):
        JwtTokenService(SECRET, ttl=timedelta(hours=72)).verify(token)


def test_a_token_without_an_expiry_is_rejected() -> None:
    token = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
        {"sub": "treasurer"}, SECRET, algorithm="HS256"
    )
    with pytest.raises(InvalidToken):
        JwtTokenService(SECRET, ttl=timedelta(hours=72)).verify(token)


def test_a_token_signed_with_another_algorithm_is_rejected() -> None:
    long_secret = SECRET + "y" * 32  # 81 bytes: long enough for HS512 without a PyJWT warning
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    token = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
        {"sub": "treasurer", "exp": expires_at}, long_secret, algorithm="HS512"
    )
    with pytest.raises(InvalidToken):
        JwtTokenService(long_secret, ttl=timedelta(hours=72)).verify(token)


def test_an_access_token_carries_only_sub_iat_exp() -> None:
    token = JwtTokenService(SECRET, ttl=timedelta(hours=72)).issue("treasurer").token
    claims = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
        token, options={"verify_signature": False}
    )
    assert set(claims) == {"sub", "iat", "exp"}
