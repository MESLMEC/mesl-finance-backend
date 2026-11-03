"""Standard RFC 9457 problem-JSON response declarations for the OpenAPI document
(issue #12).

Two FastAPI facts, read in installed source this session, decide the shape:

- a `responses` entry carrying a pydantic ``model`` is documented under the
  hard-coded media type ``application/json`` (fastapi/openapi/utils.py:499),
  while the wire actually speaks ``application/problem+json``
  (shared/api/problems.py:50) — so the problem schema is carried INLINE in the
  wire media type instead;
- putting any "422"/"4XX"/"default" key into ``responses`` suppresses
  FastAPI's automatic 422 ``HTTPValidationError`` (:517-521), so a ``4XX`` key
  also documents the catch-all client-error shape where the exact status set
  does not enumerate one.
"""

from typing import Any

_PROPERTIES: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "type",
        {
            "type": "string",
            "description": "The problem type URN, e.g. urn:mesl:problem:rule_violation",
        },
    ),
    (
        "title",
        {"type": "string", "description": "Short human title of the problem class"},
    ),
    (
        "status",
        {"type": "integer", "description": "The HTTP status of the answer"},
    ),
    (
        "detail",
        {
            "type": "string",
            "description": "What happened and what to do; names the offending id or constraint",
        },
    ),
    (
        "code",
        {
            "type": "string",
            "description": "Machine name of the problem class: invalid_token, not_found, unique,"
            " rule_violation, unknown_reference, validation_failed, validation_error,"
            " date_before_tenure, no_open_tenure, invalid_credentials, http_error",
        },
    ),
)

_ERRORS_PROPERTY: tuple[str, dict[str, Any]] = (
    "errors",
    {
        "type": "array",
        "description": "The pydantic validation errors, one {loc, msg} each",
        "items": {
            "type": "object",
            "properties": {
                "loc": {
                    "type": "array",
                    "description": "Where in the request the value sits",
                    "items": {"type": "string"},
                },
                "msg": {"type": "string", "description": "Why the value was refused"},
            },
        },
    },
)

_DESCRIPTION_AT: dict[int, str] = {
    401: "Unauthenticated: the bearer JWT is missing, expired or forged.",
    404: "Nothing here: the id in the URL is unknown to the lab (the detail names it).",
    409: "PostgreSQL owns the lab's rules and refused: money history is immutable, closed"
    " tenures are locked, balances have floors. A wrong amount is corrected with the"
    " fix/correction action, never edited in place.",
    422: "The request shape is refused: non-whole BDT numbers, blank notes, unknown"
    " references, unknown fields, malformed ids.",
}

CATCH_ALL_AT: str = "The lab refused for a reason below the op's own list; the problem body"
" still names its code and what to do."


def _problem_schema(with_errors: bool) -> dict[str, Any]:
    """One RFC 9457 problem body, as an OpenAPI object schema."""
    properties = {name: dict(schema) for name, schema in _PROPERTIES}
    required = list(properties)
    if with_errors:
        name, schema = _ERRORS_PROPERTY
        properties[name] = schema
        required.append(name)
    return {
        "type": "object",
        "description": "RFC 9457 problem+json: what failed, its machine code, what to do",
        "properties": properties,
        "required": required,
    }


def problem_response(status: int) -> dict[str, Any]:
    """One error declaration: description + the inline problem+json schema."""
    return {
        "description": _DESCRIPTION_AT[status],
        "content": {"application/problem+json": {"schema": _problem_schema(status == 422)}},
    }


def problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """The exact error set for an operation, as the decorator wants it."""
    return {status: problem_response(status) for status in statuses}


def catch_all_response(description: str = CATCH_ALL_AT) -> dict[str, Any]:
    """The `4XX` block: one problem+json shape for any other client error."""
    return {
        "description": description,
        "content": {"application/problem+json": {"schema": _problem_schema(True)}},
    }
