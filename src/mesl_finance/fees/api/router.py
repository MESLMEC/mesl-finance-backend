from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.fees.api.schemas import (
    CreateFeeRateRequest,
    FeeRateOut,
    SetShutdownRequest,
    ShutdownEventOut,
    ShutdownResult,
    StandingOut,
)
from mesl_finance.fees.application.create_fee_rate import CreateFeeRate, CreateFeeRateCommand
from mesl_finance.fees.application.list_dues import ListDues
from mesl_finance.fees.application.list_fee_rates import ListFeeRates
from mesl_finance.fees.application.list_shutdown_events import ListShutdownEvents
from mesl_finance.fees.application.set_shutdown import SetShutdown, SetShutdownCommand
from mesl_finance.fees.domain.dues import StandingView
from mesl_finance.fees.domain.fee_rate import FeeRateView
from mesl_finance.fees.domain.shutdown import ShutdownEventView
from mesl_finance.shared.api.responses import problem_responses

router = APIRouter(tags=["fees"])


def get_create_fee_rate(request: Request) -> CreateFeeRate:
    return cast(CreateFeeRate, request.app.state.create_fee_rate)


def get_list_fee_rates(request: Request) -> ListFeeRates:
    return cast(ListFeeRates, request.app.state.list_fee_rates)


def get_list_dues(request: Request) -> ListDues:
    return cast(ListDues, request.app.state.list_dues)


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


def _standing_out(view: StandingView) -> StandingOut:
    return StandingOut(
        member_id=view.member_id,
        member_name=view.member_name,
        is_member_now=view.is_member_now,
        weeks_owed=view.weeks_owed,
        owed=view.owed,
        credits=view.credits,
        balance=view.balance,
        weeks_overdue=view.weeks_overdue,
        oldest_unpaid_week=view.oldest_unpaid_week,
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


@router.post(
    "/fee-rates",
    status_code=201,
    summary="Set the weekly fee",
    responses=problem_responses(401, 409, 422),
)
async def post_fee_rate(
    body: CreateFeeRateRequest,
    user: Annotated[str, Depends(current_actor)],
    create_fee_rate: Annotated[CreateFeeRate, Depends(get_create_fee_rate)],
) -> FeeRateOut:
    """The rate is GLOBAL and starts on a SUNDAY; billing from that Sunday on (B-05/B-06).

    Members pay random lump sums, not a fixed weekly amount (B-07): the rate
    only computes what each period owes. Two rates on one Sunday are both
    kept — the newest id wins (`rate_on`, D-104). Non-Sunday or backdated
    start → the database converts to refusal 409 (rate_guard).
    """
    command = CreateFeeRateCommand(effective_from=body.effective_from, amount=body.amount)
    view = await create_fee_rate(command, actor=user)
    return _rate_out(view)


@router.get(
    "/fee-rates",
    summary="List fee rates",
    responses=problem_responses(401),
)
async def get_fee_rates(
    user: Annotated[str, Depends(current_actor)],
    list_fee_rates: Annotated[ListFeeRates, Depends(get_list_fee_rates)],
) -> list[FeeRateOut]:
    """The rate history, `effective_from` then id order — append-only (B-05)."""
    views = await list_fee_rates(actor=user)
    return [_rate_out(view) for view in views]


@router.post(
    "/shutdown-weeks",
    status_code=201,
    summary="Forgive weeks (shutdown)",
    responses=problem_responses(401, 409, 422),
)
async def post_shutdown_weeks(
    body: SetShutdownRequest,
    user: Annotated[str, Depends(current_actor)],
    set_shutdown: Annotated[SetShutdown, Depends(get_set_shutdown)],
) -> ShutdownResult:
    """Mark whole weeks as closed-for-camp; nobody owes a fee for them (B-08).

    ONE row per week written by the schema's `set_shutdown()`; weeks run
    Sunday→Sunday. UNDO a wrong range by calling again with
    `is_shutdown=false` (newest row wins — nothing is ever deleted, append-only,
    D-104). Sunday/order/already-shutdown-in-closed-tenure violations 409.
    """
    command = SetShutdownCommand(
        from_week=body.from_week,
        to_week=body.to_week,
        is_shutdown=body.is_shutdown,
        reason=body.reason,
    )
    weeks = await set_shutdown(command, actor=user)
    return ShutdownResult(weeks=weeks)


@router.get(
    "/shutdown-weeks",
    summary="List shutdown events",
    responses=problem_responses(401),
)
async def get_shutdown_weeks(
    user: Annotated[str, Depends(current_actor)],
    list_shutdown_events: Annotated[ListShutdownEvents, Depends(get_list_shutdown_events)],
) -> list[ShutdownEventOut]:
    """The raw event rows in `week_start`, id order — value received, not interpreted:
    billing computes the per-week latest-wins state itself (7.2 Q6, D-104)."""
    views = await list_shutdown_events(actor=user)
    return [_event_out(view) for view in views]


@router.get("/dues", summary="Who owes what", responses=problem_responses(401))
async def get_dues(
    user: Annotated[str, Depends(current_actor)],
    list_dues: Annotated[ListDues, Depends(get_list_dues)],
) -> list[StandingOut]:
    """EVERY member's standing as of today (B-09): what they owe, their credits,
    where unpaid weeks started.

    Straight from `dues_overview` (db/schema.sql:627-628): `weeks_owed` counts
    the billable Sundays of each membership period, `owed` is those weeks at
    the rates, `credits` = weekly-fee payments - refunds + adjustments,
    `balance` = credits - owed; `weeks_overdue` and `oldest_unpaid_week`
    appear while unpaid weeks exist. The list is in the view's own order
    (most overdue first). No automatic review state — you decide what to do
    with the numbers (B-09). Payments: ledger deposit `source="weekly_fee"`;
    refunds, waivers, donations and corrections go to their own tags.
    """
    views = await list_dues(actor=user)
    return [_standing_out(view) for view in views]
