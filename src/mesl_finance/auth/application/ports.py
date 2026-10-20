from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class AccessToken:
    token: str
    expires_at: datetime


class CredentialChecker(Protocol):
    def verify(self, username: str, password: str) -> bool: ...


class TokenIssuer(Protocol):
    def issue(self, subject: str) -> AccessToken: ...


class TokenVerifier(Protocol):
    def verify(self, token: str) -> str:
        """Return the subject, or raise InvalidToken."""
        ...
