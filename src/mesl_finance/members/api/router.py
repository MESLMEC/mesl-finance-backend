from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.members.api.schemas import (
    AdjustmentOut,
    CreateAdjustmentRequest,
    CreateMemberRequest,
    EditMemberRequest,
    EndPeriodRequest,
    MemberOut,
    MembershipPeriodOut,
    StartPeriodRequest,
)
from mesl_finance.members.application.create_member import CreateMember, CreateMemberCommand
from mesl_finance.members.application.edit_member import EditMember, EditMemberCommand
from mesl_finance.members.application.end_membership import EndMembership
from mesl_finance.members.application.list_adjustments import ListAdjustments
from mesl_finance.members.application.list_members import ListMembers
from mesl_finance.members.application.list_membership_periods import ListMembershipPeriods
from mesl_finance.members.application.record_adjustment import (
    RecordAdjustment,
    RecordAdjustmentCommand,
)
from mesl_finance.members.application.start_membership import StartMembership
from mesl_finance.members.domain.adjustment import AdjustmentView
from mesl_finance.members.domain.member import MembershipPeriodView, MemberView

router = APIRouter(tags=["members"])


def get_create_member(request: Request) -> CreateMember:
    return cast(CreateMember, request.app.state.create_member)


def get_list_members(request: Request) -> ListMembers:
    return cast(ListMembers, request.app.state.list_members)


def get_record_adjustment(request: Request) -> RecordAdjustment:
    return cast(RecordAdjustment, request.app.state.record_adjustment)


def get_list_adjustments(request: Request) -> ListAdjustments:
    return cast(ListAdjustments, request.app.state.list_adjustments)


def get_edit_member(request: Request) -> EditMember:
    return cast(EditMember, request.app.state.edit_member)


def get_start_membership(request: Request) -> StartMembership:
    return cast(StartMembership, request.app.state.start_membership)


def get_end_membership(request: Request) -> EndMembership:
    return cast(EndMembership, request.app.state.end_membership)


def get_list_membership_periods(request: Request) -> ListMembershipPeriods:
    return cast(ListMembershipPeriods, request.app.state.list_membership_periods)


def _out(view: MemberView) -> MemberOut:
    return MemberOut(
        id=view.id,
        name=view.name,
        batch=view.batch,
        note=view.note,
    )


def _adjustment_out(view: AdjustmentView) -> AdjustmentOut:
    return AdjustmentOut(
        id=view.id,
        member_id=view.member_id,
        kind=view.kind,
        amount=view.amount,
        occurred_on=view.occurred_on,
        note=view.note,
        recorded_at=view.recorded_at,
        recorded_by=view.recorded_by,
    )


def _period_out(view: MembershipPeriodView) -> MembershipPeriodOut:
    return MembershipPeriodOut(
        id=view.id,
        member_id=view.member_id,
        start_date=view.start_date,
        end_date=view.end_date,
    )


def _found(view: MemberView | None, member_id: int) -> MemberView:
    if view is None:
        raise HTTPException(status_code=404, detail=f"member {member_id} does not exist")
    return view


def _period_found(view: MembershipPeriodView | None, member_id: int) -> MembershipPeriodView:
    if view is None:
        raise HTTPException(status_code=404, detail=f"member {member_id} does not exist")
    return view


@router.post("/members", status_code=201)
async def post_member(
    body: CreateMemberRequest,
    user: Annotated[str, Depends(current_actor)],
    create_member: Annotated[CreateMember, Depends(get_create_member)],
) -> MemberOut:
    view = await create_member(CreateMemberCommand(**body.model_dump()), actor=user)
    return _out(view)


@router.get("/members")
async def get_members(
    user: Annotated[str, Depends(current_actor)],
    list_members: Annotated[ListMembers, Depends(get_list_members)],
) -> list[MemberOut]:
    views = await list_members(actor=user)
    return [_out(view) for view in views]


@router.post("/members/{member_id}/adjustments", status_code=201)
async def post_adjustment(
    member_id: int,
    body: CreateAdjustmentRequest,
    user: Annotated[str, Depends(current_actor)],
    record_adjustment: Annotated[RecordAdjustment, Depends(get_record_adjustment)],
) -> AdjustmentOut:
    command = RecordAdjustmentCommand(
        kind=body.kind,
        amount=body.amount,
        occurred_on=body.occurred_on,
        note=body.note,
    )
    view = await record_adjustment(member_id, command, actor=user)
    if view is None:
        raise HTTPException(status_code=404, detail=f"member {member_id} does not exist")
    return _adjustment_out(view)


@router.get("/members/{member_id}/adjustments")
async def get_adjustments(
    member_id: int,
    user: Annotated[str, Depends(current_actor)],
    list_adjustments: Annotated[ListAdjustments, Depends(get_list_adjustments)],
) -> list[AdjustmentOut]:
    views = await list_adjustments(member_id, actor=user)
    if views is None:
        raise HTTPException(status_code=404, detail=f"member {member_id} does not exist")
    return [_adjustment_out(view) for view in views]


@router.post("/members/{member_id}/edit")
async def post_edit(
    member_id: int,
    body: EditMemberRequest,
    user: Annotated[str, Depends(current_actor)],
    edit_member: Annotated[EditMember, Depends(get_edit_member)],
) -> MemberOut:
    command = EditMemberCommand(
        fields=frozenset(body.model_fields_set),
        name=body.name,
        batch=body.batch,
        note=body.note,
    )
    view = await edit_member(member_id, command, actor=user)
    return _out(_found(view, member_id))


@router.post("/members/{member_id}/periods/start", status_code=201)
async def post_start_period(
    member_id: int,
    body: StartPeriodRequest,
    user: Annotated[str, Depends(current_actor)],
    start_membership: Annotated[StartMembership, Depends(get_start_membership)],
) -> MembershipPeriodOut:
    view = await start_membership(member_id, body.start_date, actor=user)
    return _period_out(_period_found(view, member_id))


@router.post("/members/{member_id}/periods/end")
async def post_end_period(
    member_id: int,
    body: EndPeriodRequest,
    user: Annotated[str, Depends(current_actor)],
    end_membership: Annotated[EndMembership, Depends(get_end_membership)],
) -> MembershipPeriodOut:
    view = await end_membership(member_id, body.end_date, actor=user)
    if view is None:
        raise HTTPException(
            status_code=404,
            detail=f"member {member_id} does not exist or has no open membership period",
        )
    return _period_out(view)


@router.get("/members/{member_id}/periods")
async def get_periods(
    member_id: int,
    user: Annotated[str, Depends(current_actor)],
    list_membership_periods: Annotated[ListMembershipPeriods, Depends(get_list_membership_periods)],
) -> list[MembershipPeriodOut]:
    views = await list_membership_periods(member_id, actor=user)
    if views is None:
        raise HTTPException(status_code=404, detail=f"member {member_id} does not exist")
    return [_period_out(view) for view in views]
