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


@router.post("/cost-centers", status_code=201)
async def post_cost_center(
    body: CreateCostCenterRequest,
    user: Annotated[str, Depends(current_actor)],
    create_cost_center: Annotated[CreateCostCenter, Depends(get_create_cost_center)],
) -> CostCenterOut:
    view = await create_cost_center(CreateCostCenterCommand(**body.model_dump()), actor=user)
    return _out(view)


@router.get("/cost-centers")
async def get_cost_centers(
    user: Annotated[str, Depends(current_actor)],
    list_cost_centers: Annotated[ListCostCenters, Depends(get_list_cost_centers)],
    kind: str | None = None,
    status: str | None = None,
) -> list[CostCenterOut]:
    views = await list_cost_centers(actor=user, kind=kind, status=status)
    return [_out(view) for view in views]


@router.post("/cost-centers/{cost_center_id}/rename")
async def post_rename(
    cost_center_id: int,
    body: RenameCostCenterRequest,
    user: Annotated[str, Depends(current_actor)],
    rename_cost_center: Annotated[RenameCostCenter, Depends(get_rename_cost_center)],
) -> CostCenterOut:
    view = await rename_cost_center(cost_center_id, body.name, actor=user)
    return _out(_found(view, cost_center_id))


@router.post("/cost-centers/{cost_center_id}/status")
async def post_status(
    cost_center_id: int,
    body: SetCostCenterStatusRequest,
    user: Annotated[str, Depends(current_actor)],
    set_cost_center_status: Annotated[SetCostCenterStatus, Depends(get_set_cost_center_status)],
) -> CostCenterOut:
    view = await set_cost_center_status(cost_center_id, body.status, actor=user)
    return _out(_found(view, cost_center_id))


@router.get("/cost-centers/{cost_center_id}/summary")
async def get_cost_center_summary(
    cost_center_id: int,
    user: Annotated[str, Depends(current_actor)],
    get_summary: Annotated[GetCostCenterSummary, Depends(get_get_cost_center_summary)],
) -> CostCenterSummaryOut:
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


@router.post("/sweeps", status_code=201)
async def post_sweep(
    body: SweepRequest,
    user: Annotated[str, Depends(current_actor)],
    sweep_leftover: Annotated[SweepLeftover, Depends(get_sweep_leftover)],
) -> SweepCreated:
    entry_id, from_balance, pool_balance = await sweep_leftover(
        SweepCommand(**body.model_dump()), actor=user
    )
    return SweepCreated(
        id=entry_id,
        kind=EntryKind.SWEEP,
        from_balance=from_balance,
        pool_balance=pool_balance,
    )
