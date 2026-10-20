"""RFC 9457 problem+json responses for every error the API returns."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from mesl_finance.shared.errors import (
    DomainError,
    RuleViolation,
    Unauthorized,
    UnknownReference,
    ValidationFailed,
)

_STATUS: list[tuple[type[DomainError], int]] = [
    (Unauthorized, 401),
    (ValidationFailed, 422),
    (UnknownReference, 422),
    (RuleViolation, 409),
]


def problem(status: int, code: str, title: str, detail: str, **extra: Any) -> JSONResponse:
    body = {
        "type": f"urn:mesl:problem:{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
    }
    body.update(extra)
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(
        body, status_code=status, media_type="application/problem+json", headers=headers
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status = next((code for cls, code in _STATUS if isinstance(exc, cls)), 400)
        return problem(status, exc.code, exc.title, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _request_invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": [str(part) for part in e["loc"]], "msg": e["msg"]} for e in exc.errors()]
        return problem(
            422,
            "validation_error",
            "Request validation failed",
            "The request body is invalid",
            errors=errors,
        )
