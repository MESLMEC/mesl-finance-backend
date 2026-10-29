"""The health route (ROADMAP 12.1)."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.health.application.check_health import CheckHealth
from mesl_finance.health.domain.health import HealthReport

router = APIRouter(tags=["health"])


def get_check_health(request: Request) -> CheckHealth:
    return cast(CheckHealth, request.app.state.check_health)


@router.get("/health", response_model=list[str])
async def get_health(
    user: Annotated[str, Depends(current_actor)],
    check_health: Annotated[CheckHealth, Depends(get_check_health)],
) -> JSONResponse:
    report = HealthReport(problems=tuple(await check_health(actor=user)))
    return JSONResponse(
        content=list(report.problems),
        status_code=200 if report.healthy else 503,
    )
