from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.cost_centers.api.schemas import (
    CostCenterOut,
    CreateCostCenterRequest,
    RenameCostCenterRequest,
    SetCostCenterStatusRequest,
)
from mesl_finance.cost_centers.application.create_cost_center import (
    CreateCostCenter,
    CreateCostCenterCommand,
)
from mesl_finance.cost_centers.application.list_cost_centers import ListCostCenters
from mesl_finance.cost_centers.application.rename_cost_center import RenameCostCenter
from mesl_finance.cost_centers.application.set_cost_center_status import SetCostCenterStatus
from mesl_finance.cost_centers.domain.cost_center import CostCenterView

router = APIRouter(tags=["cost-centers"])


def get_create_cost_center(request: Request) -> CreateCostCenter:
    return cast(CreateCostCenter, request.app.state.create_cost_center)


def get_list_cost_centers(request: Request) -> ListCostCenters:
    return cast(ListCostCenters, request.app.state.list_cost_centers)


def get_rename_cost_center(request: Request) -> RenameCostCenter:
    return cast(RenameCostCenter, request.app.state.rename_cost_center)


def get_set_cost_center_status(request: Request) -> SetCostCenterStatus:
    return cast(SetCostCenterStatus, request.app.state.set_cost_center_status)


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
