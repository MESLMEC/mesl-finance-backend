from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt

from mesl_finance.auth.application.ports import AccessToken
from mesl_finance.shared.errors import InvalidToken

_ALGORITHM = "HS256"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class JwtTokenService:
    """Access tokens only (no refresh): subject + expiry, signed HS256."""

    def __init__(self, secret: str, ttl: timedelta, now: Callable[[], datetime] = _utc_now) -> None:
        self._secret = secret
        self._ttl = ttl
        self._now = now

    def issue(self, subject: str) -> AccessToken:
        issued_at = self._now()
        expires_at = issued_at + self._ttl
        claims = {"sub": subject, "iat": issued_at, "exp": expires_at}
        # ignored: PyJWT's key alias unions optional `cryptography` key types
        # (jwt/algorithms.py:38, 96-101); cryptography is not installed, so
        # pyright sees the jwt.encode member type as "partially unknown".
        encoded = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
            claims, self._secret, algorithm=_ALGORITHM
        )
        return AccessToken(encoded, expires_at)

    def verify(self, token: str) -> str:
        try:
            # ignored: see the note in issue(); same alias, jwt.decode.
            claims = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
                token, self._secret, algorithms=[_ALGORITHM], options={"require": ["exp", "sub"]}
            )
        except jwt.PyJWTError as exc:
            raise InvalidToken from exc
        return str(claims["sub"])
