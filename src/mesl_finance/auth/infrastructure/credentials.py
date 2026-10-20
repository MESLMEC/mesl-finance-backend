import hmac

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2CredentialChecker:
    """The single treasurer login: one username and its argon2 hash, from configuration."""

    def __init__(self, username: str, password_hash: str) -> None:
        self._username = username
        self._hash = password_hash
        self._hasher = PasswordHasher()

    def verify(self, username: str, password: str) -> bool:
        # always verify the password, so a wrong username costs the same time as a wrong password
        try:
            password_ok = self._hasher.verify(self._hash, password)
        except (VerificationError, InvalidHashError):
            password_ok = False
        username_ok = hmac.compare_digest(username.encode(), self._username.encode())
        return password_ok and username_ok
