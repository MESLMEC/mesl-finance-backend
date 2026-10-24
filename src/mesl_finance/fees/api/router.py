from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.fees.api.schemas import (
    CreateFeeRateRequest,
    FeeRateOut,
    SetShutdownRequest,
    ShutdownEventOut,
    ShutdownResult,
)
from mesl_finance.fees.application.create_fee_rate import CreateFeeRate, CreateFeeRateCommand
from mesl_finance.fees.application.list_fee_rates import ListFeeRates
from mesl_finance.fees.application.list_shutdown_events import ListShutdownEvents
from mesl_finance.fees.application.set_shutdown import SetShutdown, SetShutdownCommand
from mesl_finance.fees.domain.fee_rate import FeeRateView
from mesl_finance.fees.domain.shutdown import ShutdownEventView

router = APIRouter(tags=["fees"])


def get_create_fee_rate(request: Request) -> CreateFeeRate:
    return cast(CreateFeeRate, request.app.state.create_fee_rate)


def get_list_fee_rates(request: Request) -> ListFeeRates:
    return cast(ListFeeRates, request.app.state.list_fee_rates)


def get_set_shutdown(request: Request) -> SetShutdown:
    return cast(SetShutdown, request.app.state.set_shutdown)


def get_list_shutdown_events(request: Request) -> ListShutdownEvents:
    return cast(ListShutdownEvents, request.app.state.list_shutdown_events)


def _rate_out(view: FeeRateView) -> FeeRateOut:
    return FeeRateOut(
        id=view.id,
        effective_from=view.effective_from,
        amount=view.amount,
        recorded_at=view.recorded_at,
        recorded_by=view.recorded_by,
    )


def _event_out(view: ShutdownEventView) -> ShutdownEventOut:
    return ShutdownEventOut(
        id=view.id,
        week_start=view.week_start,
        is_shutdown=view.is_shutdown,
        reason=view.reason,
        recorded_at=view.recorded_at,
        recorded_by=view.recorded_by,
    )


@router.post("/fee-rates", status_code=201)
async def post_fee_rate(
    body: CreateFeeRateRequest,
    user: Annotated[str, Depends(current_actor)],
    create_fee_rate: Annotated[CreateFeeRate, Depends(get_create_fee_rate)],
) -> FeeRateOut:
    command = CreateFeeRateCommand(effective_from=body.effective_from, amount=body.amount)
    view = await create_fee_rate(command, actor=user)
    return _rate_out(view)


@router.get("/fee-rates")
async def get_fee_rates(
    user: Annotated[str, Depends(current_actor)],
    list_fee_rates: Annotated[ListFeeRates, Depends(get_list_fee_rates)],
) -> list[FeeRateOut]:
    views = await list_fee_rates(actor=user)
    return [_rate_out(view) for view in views]


@router.post("/shutdown-weeks", status_code=201)
async def post_shutdown_weeks(
    body: SetShutdownRequest,
    user: Annotated[str, Depends(current_actor)],
    set_shutdown: Annotated[SetShutdown, Depends(get_set_shutdown)],
) -> ShutdownResult:
    command = SetShutdownCommand(
        from_week=body.from_week,
        to_week=body.to_week,
        is_shutdown=body.is_shutdown,
        reason=body.reason,
    )
    weeks = await set_shutdown(command, actor=user)
    return ShutdownResult(weeks=weeks)


@router.get("/shutdown-weeks")
async def get_shutdown_weeks(
    user: Annotated[str, Depends(current_actor)],
    list_shutdown_events: Annotated[ListShutdownEvents, Depends(get_list_shutdown_events)],
) -> list[ShutdownEventOut]:
    views = await list_shutdown_events(actor=user)
    return [_event_out(view) for view in views]
