from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.envelopes.api.schemas import (
    AllocationConfirmedOut,
    AllocationContextOut,
    AllocationSuggestionOut,
    AllocationSuggestionRequest,
    ConfirmAllocationRequest,
    CreateEnvelopeRequest,
    EnvelopeOut,
    EnvelopeSettingsRequest,
    RenameEnvelopeRequest,
)
from mesl_finance.envelopes.application.confirm_allocation import (
    ConfirmAllocation,
    ConfirmAllocationCommand,
)
from mesl_finance.envelopes.application.create_envelope import (
    CreateEnvelope,
    CreateEnvelopeCommand,
)
from mesl_finance.envelopes.application.deactivate_envelope import DeactivateEnvelope
from mesl_finance.envelopes.application.draft_allocation import DraftAllocation
from mesl_finance.envelopes.application.get_allocation_context import GetAllocationContext
from mesl_finance.envelopes.application.list_envelopes import ListEnvelopes
from mesl_finance.envelopes.application.rename_envelope import RenameEnvelope
from mesl_finance.envelopes.application.update_envelope_settings import UpdateEnvelopeSettings
from mesl_finance.envelopes.domain.allocation_context import AllocationContextView
from mesl_finance.envelopes.domain.allocation_suggestion import (
    AllocationSuggestionQuery,
    AllocationSuggestionView,
)
from mesl_finance.envelopes.domain.envelope import EnvelopeView
from mesl_finance.shared.api.responses import catch_all_response, problem_responses

router = APIRouter(tags=["envelopes"])


def get_create_envelope(request: Request) -> CreateEnvelope:
    return cast(CreateEnvelope, request.app.state.create_envelope)


def get_list_envelopes(request: Request) -> ListEnvelopes:
    return cast(ListEnvelopes, request.app.state.list_envelopes)


def get_allocation_context(request: Request) -> GetAllocationContext:
    return cast(GetAllocationContext, request.app.state.get_allocation_context)


def get_draft_allocation(request: Request) -> DraftAllocation:
    return cast(DraftAllocation, request.app.state.draft_allocation)


def get_confirm_allocation(request: Request) -> ConfirmAllocation:
    return cast(ConfirmAllocation, request.app.state.confirm_allocation)


def get_rename_envelope(request: Request) -> RenameEnvelope:
    return cast(RenameEnvelope, request.app.state.rename_envelope)


def get_update_envelope_settings(request: Request) -> UpdateEnvelopeSettings:
    return cast(UpdateEnvelopeSettings, request.app.state.update_envelope_settings)


def get_deactivate_envelope(request: Request) -> DeactivateEnvelope:
    return cast(DeactivateEnvelope, request.app.state.deactivate_envelope)


def _out(view: EnvelopeView) -> EnvelopeOut:
    return EnvelopeOut(
        id=view.id,
        name=view.name,
        target_cap=view.target_cap,
        alloc_priority=view.alloc_priority,
        is_pool=view.is_pool,
        active=view.active,
    )


def _context_out(view: AllocationContextView) -> AllocationContextOut:
    return AllocationContextOut(
        pool_balance=view.pool_balance,
        member_credit_held=view.member_credit_held,
        pool_after_member_credit=view.pool_after_member_credit,
    )


def _suggestion_out(view: AllocationSuggestionView) -> AllocationSuggestionOut:
    return AllocationSuggestionOut(
        envelope_id=view.envelope_id,
        envelope_name=view.envelope_name,
        balance=view.balance,
        target_cap=view.target_cap,
        alloc_priority=view.alloc_priority,
        gap=view.gap,
        phase=view.phase,
        suggested=view.suggested,
    )


def _found(view: EnvelopeView | None, envelope_id: int) -> EnvelopeView:
    if view is None:
        raise HTTPException(status_code=404, detail=f"envelope {envelope_id} does not exist")
    return view


@router.post(
    "/envelopes",
    status_code=201,
    summary="Create an envelope",
    responses=problem_responses(401, 409, 422),
)
async def post_envelope(
    body: CreateEnvelopeRequest,
    user: Annotated[str, Depends(current_actor)],
    create_envelope: Annotated[CreateEnvelope, Depends(get_create_envelope)],
) -> EnvelopeOut:
    """One purpose, one envelope: start with `name` (+ optional cap/priority).

    The POOL ("Unallocated General") is created by the first-start bootstrap
    and cannot be created here (D-041); names are unique per table, so a taken
    name is 409 `unique` naming `envelopes_name_key` and a negative cap hits
    the schema's CHECK as 409 `rule_violation`; blank names are refused
    app-side as 422 (D-066 Q7). Cap and priority are the allocation inputs
    (D-021); settings are replaced wholesale via the settings action.
    """
    view = await create_envelope(CreateEnvelopeCommand(**body.model_dump()), actor=user)
    return _out(view)


@router.get("/envelopes", summary="List envelopes", responses=problem_responses(401))
async def get_envelopes(
    user: Annotated[str, Depends(current_actor)],
    list_envelopes: Annotated[ListEnvelopes, Depends(get_list_envelopes)],
) -> list[EnvelopeOut]:
    """Every envelope, id order — including deactivated ones (`active: false`).

    NO balances here on purpose (5.1 Q4): balances are ledger reads; the
    pool's money is on `GET /allocation-context`.
    """
    return [_out(view) for view in await list_envelopes(actor=user)]


@router.post(
    "/envelopes/{envelope_id}/rename",
    summary="Rename an envelope",
    responses=problem_responses(401, 404, 409, 422),
)
async def post_rename(
    envelope_id: int,
    body: RenameEnvelopeRequest,
    user: Annotated[str, Depends(current_actor)],
    rename_envelope: Annotated[RenameEnvelope, Depends(get_rename_envelope)],
) -> EnvelopeOut:
    """A new label for an envelope — the pool included (renaming is allowed;
    only its `is_pool` flag is not changeable, D-066 Q8).

    History of the name is kept by the trigger. A taken name → 409 `unique`;
    blank → 422 `validation_failed`; unknown id → 404 naming it.
    """
    view = await rename_envelope(envelope_id, body.name, actor=user)
    return _out(_found(view, envelope_id))


@router.post(
    "/envelopes/{envelope_id}/settings",
    summary="Set an envelope's cap and priority",
    responses=problem_responses(401, 404, 409, 422),
)
async def post_settings(
    envelope_id: int,
    body: EnvelopeSettingsRequest,
    user: Annotated[str, Depends(current_actor)],
    update_settings: Annotated[UpdateEnvelopeSettings, Depends(get_update_envelope_settings)],
) -> EnvelopeOut:
    """Replace BOTH `target_cap` and `alloc_priority` (D-067).

    The body is required-complete even to clear: `null` clears the value; an
    omitted field is a 422 `validation_error`. These two numbers drive the
    allocation waterfall: capped envelopes fill first, by priority gap
    (db/schema.sql:457-503). A negative cap hits the table CHECK → 409.
    """
    view = await update_settings(envelope_id, body.target_cap, body.alloc_priority, actor=user)
    return _out(_found(view, envelope_id))


@router.post(
    "/envelopes/{envelope_id}/deactivate",
    summary="Retire an envelope",
    responses={
        **problem_responses(401, 404, 409),
        "4XX": catch_all_response(),
    },
)
async def post_deactivate(
    envelope_id: int,
    user: Annotated[str, Depends(current_actor)],
    deactivate_envelope: Annotated[DeactivateEnvelope, Depends(get_deactivate_envelope)],
) -> EnvelopeOut:
    """Retire an envelope from allocation — only when it holds NOTHING.

    The database guard refuses the pool itself and any envelope whose balance
    is not zero (409 naming the balance, db/schema.sql:144-157); unknown id
    404. Deactivated envelopes still show on the list (`active: false`);
    ledger lines naming them stay fully readable. Reactivation is not an
    exposed action — create a fresh envelope instead (D-021).
    """
    view = await deactivate_envelope(envelope_id, actor=user)
    return _out(_found(view, envelope_id))


@router.get(
    "/allocation-context",
    summary="The allocation screen header",
    responses=problem_responses(401),
)
async def get_allocation_context_view(
    user: Annotated[str, Depends(current_actor)],
    get_context: Annotated[GetAllocationContext, Depends(get_allocation_context)],
) -> AllocationContextOut:
    """Three numbers: `pool_balance`, `member_credit_held`, `pool_after_member_credit`.

    Straight from the `allocation_context` view (db/schema.sql:630-634) —
    what the committee can actually allocate is the third number: pool money
    minus the credit members hold in advance (B-12).
    """
    view = await get_context(actor=user)
    return _context_out(view)


@router.post(
    "/allocation-suggestion",
    summary="Draft how to split an amount",
    responses=problem_responses(401, 422),
)
async def post_allocation_suggestion(
    body: AllocationSuggestionRequest,
    user: Annotated[str, Depends(current_actor)],
    draft_allocation: Annotated[DraftAllocation, Depends(get_draft_allocation)],
) -> list[AllocationSuggestionOut]:
    """A DRY-RUN of `POST /allocations`: one row per envelope, nothing written.

    `amount` fills capped envelopes first (by priority and gap), then splits
    by the shares the body names — or by the previous ALLOCATION session's
    proportions when `shares` is omitted. In the draft's answer, read the
    rows BEFORE confirming (the context updates when allocate runs too, D-046).
    """
    query = AllocationSuggestionQuery(amount=body.amount, shares=body.shares)
    views = await draft_allocation(query, actor=user)
    return [_suggestion_out(view) for view in views]


@router.post(
    "/allocations",
    status_code=201,
    summary="Confirm a split of pool money",
    responses=problem_responses(401, 409, 422),
)
async def post_allocation(
    body: ConfirmAllocationRequest,
    user: Annotated[str, Depends(current_actor)],
    confirm_allocation: Annotated[ConfirmAllocation, Depends(get_confirm_allocation)],
) -> AllocationConfirmedOut:
    """Move hard numbers out of the pool, one transfer (`kind: "transfer"`).

    Body: `{occurred_on, note, amounts: {"<envelope_id>": whole BDT}}`. The
    DATABASE enforces everything that is not typing: positive entries only,
    the pool cannot be a target, envelopes must exist and be live, and no
    over-allocation — each violation is a 409 with the rule's own message
    (db/schema.sql's allocate()). Returns `{id, kind, pool_balance}` — the
    new id is the session's transfer id, so provisioning a later draft
    reuses these proportions (D-121).
    """
    command = ConfirmAllocationCommand(**body.model_dump())
    entry_id, pool_balance = await confirm_allocation(command, actor=user)
    return AllocationConfirmedOut(id=entry_id, kind="transfer", pool_balance=pool_balance)
