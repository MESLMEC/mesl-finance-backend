"""The ONE place that turns database errors into domain errors."""

from typing import Any

from sqlalchemy.exc import DBAPIError

from mesl_finance.shared.errors import (
    DateBeforeTenure,
    DomainError,
    RuleViolation,
    UnknownReference,
)

_RAISE_EXCEPTION = "P0001"  # RAISE EXCEPTION inside the schema's triggers and functions
_FOREIGN_KEY_VIOLATION = "23503"

# message fragment (from db/schema.sql) -> domain error. Add a rule only together with its test.
_RAISE_RULES: list[tuple[str, type[DomainError]]] = [
    ("before this tenure opened", DateBeforeTenure),
]


def map_db_error(exc: DBAPIError) -> DomainError | None:
    """Return the domain error for a known database error, or None if it is not one of ours."""
    original: Any = exc.orig
    cause: Any = getattr(original, "__cause__", None) or original
    sqlstate = getattr(cause, "sqlstate", None) or getattr(original, "sqlstate", None)
    message = str(getattr(cause, "message", None) or cause)

    if sqlstate == _RAISE_EXCEPTION:
        for fragment, error in _RAISE_RULES:
            if fragment in message:
                return error(message)
        return RuleViolation(message)
    if sqlstate == _FOREIGN_KEY_VIOLATION:
        return UnknownReference(str(getattr(cause, "detail", None) or message))
    return None
