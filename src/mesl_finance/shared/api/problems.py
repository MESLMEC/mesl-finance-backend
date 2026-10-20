"""RFC 9457 problem+json responses for every error the API returns."""

import http.client
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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


_HTTP_CODES: dict[int, str] = {404: "not_found", 405: "method_not_allowed"}


def problem(
    status: int,
    code: str,
    title: str,
    detail: str,
    headers: Mapping[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body = {
        "type": f"urn:mesl:problem:{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
    }
    body.update(extra)
    if status == 401 and headers is None:
        headers = {"WWW-Authenticate": "Bearer"}
    return JSONResponse(
        body, status_code=status, media_type="application/problem+json", headers=headers
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status = next((code for cls, code in _STATUS if isinstance(exc, cls)), 400)
        return problem(status, exc.code, exc.title, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        title = http.client.responses.get(exc.status_code, "HTTP error")
        return problem(
            exc.status_code,
            _HTTP_CODES.get(exc.status_code, "http_error"),
            title,
            exc.detail or title,
            headers=exc.headers,
        )

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
