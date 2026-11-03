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
from mesl_finance.shared.api.responses import catch_all_response, problem_responses

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


def _period_found(view: MembershipPeriodView | None, member_id: int) -> MembershipPeriodView:
    if view is None:
        raise HTTPException(status_code=404, detail=f"member {member_id} does not exist")
    return view


def _found(view: MemberView | None, member_id: int) -> MemberView:
    if view is None:
        raise HTTPException(status_code=404, detail=f"member {member_id} does not exist")
    return view


@router.post(
    "/members",
    status_code=201,
    summary="Add a member",
    responses=problem_responses(401, 422),
)
async def post_member(
    body: CreateMemberRequest,
    user: Annotated[str, Depends(current_actor)],
    create_member: Annotated[CreateMember, Depends(get_create_member)],
) -> MemberOut:
    """A person joined: `name` (+ optional `batch` and note). Blank name => 422.

    Social info only — money starts flowing by itself: the membership period
    (periods/start) is what bills fee weeks (B-06), and the payments route
    via the ledger's deposits. A member who is created but has no period owes
    nothing (D-101's contract).
    """
    view = await create_member(CreateMemberCommand(**body.model_dump()), actor=user)
    return _out(view)


@router.get(
    "/members",
    summary="List members",
    responses=problem_responses(401),
)
async def get_members(
    user: Annotated[str, Depends(current_actor)],
    list_members: Annotated[ListMembers, Depends(get_list_members)],
) -> list[MemberOut]:
    """Every member, id order. Balances never here — `GET /dues` owns standing."""
    views = await list_members(actor=user)
    return [_out(view) for view in views]


@router.post(
    "/members/{member_id}/adjustments",
    status_code=201,
    summary="A signed adjustment to the member's dues account",
    responses=problem_responses(401, 404, 409, 422),
)
async def post_adjustment(
    member_id: int,
    body: CreateAdjustmentRequest,
    user: Annotated[str, Depends(current_actor)],
    record_adjustment: Annotated[RecordAdjustment, Depends(get_record_adjustment)],
) -> AdjustmentOut:
    """`kind: waiver | credit_donation | opening | correction` with a SIGNED whole-BDT amount.

    Sign rules are the database's (db/schema.sql:138-139): a waiver takes
    what it excuses, a credit_donation takes what it donates back, `opening`
    carries over old-sheet arrears/credit, `correction` fixes dues typos.
    The date must belong to the open tenure (409 otherwise); waiver/correction
    NEED a note (422). Unknown member 404.
    """
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


@router.get(
    "/members/{member_id}/adjustments",
    summary="List a member's adjustments",
    responses={
        **problem_responses(401, 404),
        "4XX": catch_all_response(),
    },
)
async def get_adjustments(
    member_id: int,
    user: Annotated[str, Depends(current_actor)],
    list_adjustments: Annotated[ListAdjustments, Depends(get_list_adjustments)],
) -> list[AdjustmentOut]:
    """Their full adjustment history, id order; `[]` when none. Unknown member 404."""
    views = await list_adjustments(member_id, actor=user)
    if views is None:
        raise HTTPException(status_code=404, detail=f"member {member_id} does not exist")
    return [_adjustment_out(view) for view in views]


@router.post(
    "/members/{member_id}/edit",
    summary="Edit member labels",
    responses=problem_responses(401, 404, 422),
)
async def post_edit(
    member_id: int,
    body: EditMemberRequest,
    user: Annotated[str, Depends(current_actor)],
    edit_member: Annotated[EditMember, Depends(get_edit_member)],
) -> MemberOut:
    """Partial body; only named fields change; explicit null clears `batch`.

    Descriptive data only — nothing here touches dues or periods (that is
    the adjustments and periods actions). Empty body 422; unknown member 404.
    """
    command = EditMemberCommand(
        fields=frozenset(body.model_fields_set),
        name=body.name,
        batch=body.batch,
        note=body.note,
    )
    view = await edit_member(member_id, command, actor=user)
    return _out(_found(view, member_id))


@router.post(
    "/members/{member_id}/periods/start",
    status_code=201,
    summary="Start a membership period",
    responses=problem_responses(401, 404, 409, 422),
)
async def post_start_period(
    member_id: int,
    body: StartPeriodRequest,
    user: Annotated[str, Depends(current_actor)],
    start_membership: Annotated[StartMembership, Depends(get_start_membership)],
) -> MembershipPeriodOut:
    """The day the person becomes billable (a Sunday start bills that week, B-06).

    While a period is open a second one cannot open (409 `rule_violation`,
    db/schema.sql:101-102); after you END one (periods/end) a new one may
    start later. The start date belongs to the open tenure — a closed-tenure
    week start is refused db-side when any rate exists. Unknown member 404.
    """
    view = await start_membership(member_id, body.start_date, actor=user)
    return _period_out(_period_found(view, member_id))


@router.post(
    "/members/{member_id}/periods/end",
    summary="End the open membership period",
    responses=problem_responses(401, 404, 409, 422),
)
async def post_end_period(
    member_id: int,
    body: EndPeriodRequest,
    user: Annotated[str, Depends(current_actor)],
    end_membership: Annotated[EndMembership, Depends(get_end_membership)],
) -> MembershipPeriodOut:
    """Ends the member's OPEN period on `end_date` (a one-time action).

    Ending twice is 409 `rule_violation` (`period_guard`: "ended once"),
    as is ending before the start or inside a closed tenure. Unknown member
    or nothing open: 404 (D-103: the detail names both possibilities because
    the adapter cannot tell them apart without a second query). Arrears of
    the leaving member stay due until paid or waived (B-10).
    """
    view = await end_membership(member_id, body.end_date, actor=user)
    if view is None:
        raise HTTPException(
            status_code=404,
            detail=f"member {member_id} does not exist or has no open membership period",
        )
    return _period_out(view)


@router.get(
    "/members/{member_id}/periods",
    summary="List membership periods",
    responses=problem_responses(401, 404, 422),
)
async def get_periods(
    member_id: int,
    user: Annotated[str, Depends(current_actor)],
    list_membership_periods: Annotated[ListMembershipPeriods, Depends(get_list_membership_periods)],
) -> list[MembershipPeriodOut]:
    """Their history, id order — the oldest first. Unknown member 404."""
    views = await list_membership_periods(member_id, actor=user)
    if views is None:
        raise HTTPException(status_code=404, detail=f"member {member_id} does not exist")
    return [_period_out(view) for view in views]
