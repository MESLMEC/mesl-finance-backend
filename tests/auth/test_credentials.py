"""Guard tests for the argon2 password check (roadmap step 4.1).

`src/mesl_finance/auth/infrastructure/credentials.py` already existed in the
pre-roadmap tree (D-023) and is accepted as-is (step 4.1 brief, user answered
"go" with the labelled suggestions): these tests pin its behaviour against the
hash that Settings carries, and must pass without any production change.

Installed argon2-cffi 25.1.0: `PasswordHasher.verify` returns True or raises
`VerifyMismatchError` (a `VerificationError` subclass) on a mismatch, and
`InvalidHashError` (a ValueError) when the encoded hash's header is unknown.
"""

from argon2 import PasswordHasher

from mesl_finance.auth.infrastructure.credentials import Argon2CredentialChecker
from mesl_finance.shared.settings import Settings
from tests.conftest import PASSWORD, USERNAME

FAST_HASHER = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)  # fast for tests


def test_correct_username_and_password_verify() -> None:
    checker = Argon2CredentialChecker(USERNAME, FAST_HASHER.hash(PASSWORD))

    assert checker.verify(USERNAME, PASSWORD) is True


def test_wrong_password_does_not_verify() -> None:
    checker = Argon2CredentialChecker(USERNAME, FAST_HASHER.hash(PASSWORD))

    assert checker.verify(USERNAME, "wrong password") is False


def test_garbage_hash_does_not_verify() -> None:
    checker = Argon2CredentialChecker(USERNAME, "not-an-argon2-hash")

    assert checker.verify(USERNAME, PASSWORD) is False


def test_wrong_username_verifies_false_even_with_the_right_password() -> None:
    checker = Argon2CredentialChecker(USERNAME, FAST_HASHER.hash(PASSWORD))

    assert checker.verify("someone-else", PASSWORD) is False


def test_settings_hash_wires_through_the_composition(settings: Settings) -> None:
    checker = Argon2CredentialChecker(
        settings.auth_username, settings.auth_password_hash.get_secret_value()
    )

    assert checker.verify(USERNAME, PASSWORD) is True
