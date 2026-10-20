"""Tests for the frozen domain error taxonomy (roadmap step 2.1, errors half).

`src/mesl_finance/shared/errors.py` is FROZEN as-is (step 2.1 brief, user
answer 2.a): these tests document its behaviour and guard it against drift.
If a later step needs a new error, that step adds it together with its test.
"""

import pytest

from mesl_finance.shared.errors import (
    DateBeforeTenure,
    DomainError,
    InvalidCredentials,
    InvalidToken,
    NoOpenTenure,
    RuleViolation,
    Unauthorized,
    UnknownReference,
    ValidationFailed,
)

FROZEN = [
    (DomainError, "domain_error", "Domain error"),
    (ValidationFailed, "validation_failed", "Validation failed"),
    (UnknownReference, "unknown_reference", "Unknown reference"),
    (RuleViolation, "rule_violation", "A lab rule refused this change"),
    (NoOpenTenure, "no_open_tenure", "There is no open tenure"),
    (DateBeforeTenure, "date_before_tenure", "Date is before the tenure opened"),
    (Unauthorized, "unauthorized", "Authentication required"),
    (InvalidCredentials, "invalid_credentials", "Wrong username or password"),
    (InvalidToken, "invalid_token", "Missing, expired or invalid token"),
]


@pytest.mark.parametrize(
    ("exc_type", "code", "title"), FROZEN, ids=[cls.__name__ for cls, _, _ in FROZEN]
)
def test_code_and_title_are_as_frozen(exc_type: type[DomainError], code: str, title: str) -> None:
    assert exc_type.code == code
    assert exc_type.title == title


@pytest.mark.parametrize(
    ("exc_type", "code", "title"), FROZEN, ids=[cls.__name__ for cls, _, _ in FROZEN]
)
def test_the_default_detail_is_the_title(
    exc_type: type[DomainError], code: str, title: str
) -> None:
    exc = exc_type()
    assert exc.title == title
    assert exc.detail == title
    assert str(exc) == title


@pytest.mark.parametrize(
    ("exc_type", "code", "title"), FROZEN, ids=[cls.__name__ for cls, _, _ in FROZEN]
)
def test_an_explicit_detail_replaces_the_title(
    exc_type: type[DomainError], code: str, title: str
) -> None:
    exc = exc_type("boom")
    assert exc.detail == "boom"
    assert str(exc) == "boom"


def test_the_subclass_tree_holds() -> None:
    assert issubclass(ValidationFailed, DomainError)
    assert issubclass(UnknownReference, DomainError)
    assert issubclass(RuleViolation, DomainError)
    assert issubclass(NoOpenTenure, RuleViolation)
    assert issubclass(DateBeforeTenure, RuleViolation)
    assert issubclass(Unauthorized, DomainError)
    assert issubclass(InvalidCredentials, Unauthorized)
    assert issubclass(InvalidToken, Unauthorized)


def test_every_error_is_catchable_as_domain_error() -> None:
    with pytest.raises(DomainError):
        raise NoOpenTenure("no tenure is open")
