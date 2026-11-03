from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.cost_centers.api.schemas import (
    CostCenterOut,
    CostCenterSummaryOut,
    CreateCostCenterRequest,
    RenameCostCenterRequest,
    SetCostCenterStatusRequest,
    SweepCreated,
    SweepRequest,
)
from mesl_finance.cost_centers.application.create_cost_center import (
    CreateCostCenter,
    CreateCostCenterCommand,
)
from mesl_finance.cost_centers.application.get_cost_center_summary import (
    GetCostCenterSummary,
)
from mesl_finance.cost_centers.application.list_cost_centers import ListCostCenters
from mesl_finance.cost_centers.application.rename_cost_center import RenameCostCenter
from mesl_finance.cost_centers.application.set_cost_center_status import SetCostCenterStatus
from mesl_finance.cost_centers.application.sweep_leftover import SweepCommand, SweepLeftover
from mesl_finance.cost_centers.domain.cost_center import CostCenterView
from mesl_finance.ledger.domain.entry import EntryKind
from mesl_finance.shared.api.responses import catch_all_response, problem_responses

router = APIRouter(tags=["cost-centers"])


def get_create_cost_center(request: Request) -> CreateCostCenter:
    return cast(CreateCostCenter, request.app.state.create_cost_center)


def get_list_cost_centers(request: Request) -> ListCostCenters:
    return cast(ListCostCenters, request.app.state.list_cost_centers)


def get_rename_cost_center(request: Request) -> RenameCostCenter:
    return cast(RenameCostCenter, request.app.state.rename_cost_center)


def get_set_cost_center_status(request: Request) -> SetCostCenterStatus:
    return cast(SetCostCenterStatus, request.app.state.set_cost_center_status)


def get_sweep_leftover(request: Request) -> SweepLeftover:
    return cast(SweepLeftover, request.app.state.sweep_leftover)


def get_get_cost_center_summary(request: Request) -> GetCostCenterSummary:
    return cast(GetCostCenterSummary, request.app.state.get_cost_center_summary)


def _out(view: CostCenterView) -> CostCenterOut:
    return CostCenterOut(
        id=view.id,
        name=view.name,
        kind=view.kind,
        status=view.status,
    )


def _found(view: CostCenterView | None, cost_center_id: int) -> CostCenterView:
    if view is None:
        raise HTTPException(status_code=404, detail=f"cost center {cost_center_id} does not exist")
    return view


@router.post(
    "/cost-centers",
    status_code=201,
    summary="Register a cost center",
    responses=problem_responses(401, 409, 422),
)
async def post_cost_center(
    body: CreateCostCenterRequest,
    user: Annotated[str, Depends(current_actor)],
    create_cost_center: Annotated[CreateCostCenter, Depends(get_create_cost_center)],
) -> CostCenterOut:
    """Name a thing money flows through: event, member_project, lab_project, competition.

    Kind is fixed at create (D-070 Q6); names are unique PER KIND (D-070:
    `cost_centers_kind_name_key`), statuses start `active`. Unknown kinds hit
    the CHECK as 409 `rule_violation`. Tag the money with `cost_center_id`
    while it moves, then an event's summary/sweep live here.
    """
    view = await create_cost_center(CreateCostCenterCommand(**body.model_dump()), actor=user)
    return _out(view)


@router.get(
    "/cost-centers",
    summary="List cost centers",
    responses={
        **problem_responses(401),
        "4XX": catch_all_response(
            "Another 4xx: an unknown optional ?kind= or ?status= filter simply matches"
            " nothing (answer 200 []; it never errors) — see D-071."
        ),
    },
)
async def get_cost_centers(
    user: Annotated[str, Depends(current_actor)],
    list_cost_centers: Annotated[ListCostCenters, Depends(get_list_cost_centers)],
    kind: str | None = None,
    status: str | None = None,
) -> list[CostCenterOut]:
    """Every cost center, id order; optional filters combine: `?kind=`,
    `?status=`."""
    views = await list_cost_centers(actor=user, kind=kind, status=status)
    return [_out(view) for view in views]


@router.post(
    "/cost-centers/{cost_center_id}/rename",
    summary="Rename a cost center",
    responses=problem_responses(401, 404, 409, 422),
)
async def post_rename(
    cost_center_id: int,
    body: RenameCostCenterRequest,
    user: Annotated[str, Depends(current_actor)],
    rename_cost_center: Annotated[RenameCostCenter, Depends(get_rename_cost_center)],
) -> CostCenterOut:
    """A new label; kind stays. Same-kind name conflicts are 409 `unique`."""
    view = await rename_cost_center(cost_center_id, body.name, actor=user)
    return _out(_found(view, cost_center_id))


@router.post(
    "/cost-centers/{cost_center_id}/status",
    summary="Set a cost center's status",
    responses=problem_responses(401, 404, 409, 422),
)
async def post_status(
    cost_center_id: int,
    body: SetCostCenterStatusRequest,
    user: Annotated[str, Depends(current_actor)],
    set_cost_center_status: Annotated[SetCostCenterStatus, Depends(get_set_cost_center_status)],
) -> CostCenterOut:
    """Whatever value the schema allows, whenever (D-070 Q7): planned, active,
    completed, cancelled. No transition rules are enforced."""
    view = await set_cost_center_status(cost_center_id, body.status, actor=user)
    return _out(_found(view, cost_center_id))


@router.get(
    "/cost-centers/{cost_center_id}/summary",
    summary="One cost center's money in/out",
    responses={
        **problem_responses(401, 404),
        "4XX": catch_all_response(),
    },
)
async def get_cost_center_summary(
    cost_center_id: int,
    user: Annotated[str, Depends(current_actor)],
    get_summary: Annotated[GetCostCenterSummary, Depends(get_get_cost_center_summary)],
) -> CostCenterSummaryOut:
    """The `cost_center_summary` view's own 8 columns (db/schema.sql:537-557).

    `money_in`/`money_out` = ledger movements tagged `cost_center_id`
    (reversals count through their original's cost center), `swept` = what
    went back to the pool, `leftover` = in - out - swept. A center without
    entries is all zeros, not NULL.
    """
    view = await get_summary(cost_center_id, actor=user)
    if view is None:
        raise HTTPException(status_code=404, detail=f"cost center {cost_center_id} does not exist")
    return CostCenterSummaryOut(
        cost_center_id=view.cost_center_id,
        name=view.name,
        kind=view.kind,
        status=view.status,
        money_in=view.money_in,
        money_out=view.money_out,
        swept=view.swept,
        leftover=view.leftover,
    )


@router.post(
    "/sweeps",
    status_code=201,
    summary="Sweep an event's leftover to the pool",
    responses=problem_responses(401, 409, 422),
)
async def post_sweep(
    body: SweepRequest,
    user: Annotated[str, Depends(current_actor)],
    sweep_leftover: Annotated[SweepLeftover, Depends(get_sweep_leftover)],
) -> SweepCreated:
    """Give an event's unspent money back to "Unallocated General" (B-16/B-17).

    Thin by design: everything except a blank note reaches `sweep_leftover`
    and answers 409 with its own message — nothing to sweep (already swept,
    unknown cost center), wrong source envelope (not the pool side), overdraw
    — db/schema.sql:560-574. Answers `{id, kind: "sweep", from_balance,
    pool_balance}`.
    """
    entry_id, from_balance, pool_balance = await sweep_leftover(
        SweepCommand(**body.model_dump()), actor=user
    )
    return SweepCreated(
        id=entry_id,
        kind=EntryKind.SWEEP,
        from_balance=from_balance,
        pool_balance=pool_balance,
    )
