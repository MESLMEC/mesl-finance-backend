"""Routes for the tenure handover slice (ROADMAP 11.1)."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.tenures.api.schemas import (
    AssetSnapshotOut,
    CloseTenureOut,
    CloseTenureRequest,
    HoldingSnapshotOut,
    MemberSnapshotOut,
)
from mesl_finance.tenures.application.close_tenure import CloseTenure, CloseTenureCommand
from mesl_finance.tenures.application.read_snapshots import (
    ListAssetSnapshots,
    ListHoldingSnapshots,
    ListMemberSnapshots,
)
from mesl_finance.tenures.domain.snapshots import (
    AssetSnapshotView,
    HoldingSnapshotView,
    MemberSnapshotView,
)
from mesl_finance.tenures.domain.tenure import TenureView

router = APIRouter(tags=["tenures"])


def get_close_tenure(request: Request) -> CloseTenure:
    return cast(CloseTenure, request.app.state.close_tenure)


def get_list_member_snapshots(request: Request) -> ListMemberSnapshots:
    return cast(ListMemberSnapshots, request.app.state.list_member_snapshots)


def get_list_asset_snapshots(request: Request) -> ListAssetSnapshots:
    return cast(ListAssetSnapshots, request.app.state.list_asset_snapshots)


def get_list_holding_snapshots(request: Request) -> ListHoldingSnapshots:
    return cast(ListHoldingSnapshots, request.app.state.list_holding_snapshots)


def _close_out(view: TenureView) -> CloseTenureOut:
    return CloseTenureOut(
        id=view.id,
        name=view.name,
        opened_on=view.opened_on,
    )


def _member_out(view: MemberSnapshotView) -> MemberSnapshotOut:
    return MemberSnapshotOut(
        tenure_id=view.tenure_id,
        member_id=view.member_id,
        as_of=view.as_of,
        weeks_owed=view.weeks_owed,
        owed=view.owed,
        credits=view.credits,
        balance=view.balance,
        weeks_overdue=view.weeks_overdue,
    )


def _asset_out(view: AssetSnapshotView) -> AssetSnapshotOut:
    return AssetSnapshotOut(
        tenure_id=view.tenure_id,
        asset_id=view.asset_id,
        as_of=view.as_of,
        stock=view.stock,
        damaged=view.damaged,
        held=view.held,
        lost=view.lost,
        scrapped=view.scrapped,
        exchanged=view.exchanged,
    )


def _holding_out(view: HoldingSnapshotView) -> HoldingSnapshotOut:
    return HoldingSnapshotOut(
        tenure_id=view.tenure_id,
        asset_id=view.asset_id,
        member_id=view.member_id,
        quantity=view.quantity,
    )


@router.post("/tenures/close", status_code=201)
async def post_close_tenure(
    body: CloseTenureRequest,
    user: Annotated[str, Depends(current_actor)],
    close_tenure: Annotated[CloseTenure, Depends(get_close_tenure)],
) -> CloseTenureOut:
    command = CloseTenureCommand(
        close_on=body.close_on,
        next_name=body.next_name,
    )
    view = await close_tenure(command, actor=user)
    return _close_out(view)


@router.get("/tenures/{tenure_id}/member-snapshots")
async def get_member_snapshots(
    tenure_id: int,
    user: Annotated[str, Depends(current_actor)],
    list_snapshots: Annotated[ListMemberSnapshots, Depends(get_list_member_snapshots)],
) -> list[MemberSnapshotOut]:
    views = await list_snapshots(tenure_id, actor=user)
    if views is None:
        raise HTTPException(status_code=404, detail=f"tenure {tenure_id} does not exist")
    return [_member_out(view) for view in views]


@router.get("/tenures/{tenure_id}/asset-snapshots")
async def get_asset_snapshots(
    tenure_id: int,
    user: Annotated[str, Depends(current_actor)],
    list_snapshots: Annotated[ListAssetSnapshots, Depends(get_list_asset_snapshots)],
) -> list[AssetSnapshotOut]:
    views = await list_snapshots(tenure_id, actor=user)
    if views is None:
        raise HTTPException(status_code=404, detail=f"tenure {tenure_id} does not exist")
    return [_asset_out(view) for view in views]


@router.get("/tenures/{tenure_id}/holding-snapshots")
async def get_holding_snapshots(
    tenure_id: int,
    user: Annotated[str, Depends(current_actor)],
    list_snapshots: Annotated[ListHoldingSnapshots, Depends(get_list_holding_snapshots)],
) -> list[HoldingSnapshotOut]:
    views = await list_snapshots(tenure_id, actor=user)
    if views is None:
        raise HTTPException(status_code=404, detail=f"tenure {tenure_id} does not exist")
    return [_holding_out(view) for view in views]
