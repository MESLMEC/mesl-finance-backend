from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.ledger.api.schemas import (
    DepositRequest,
    EntryCreated,
    EntryLabelsOut,
    EntryOut,
    ExpenseCreated,
    ExpenseRequest,
    FixAmountCreated,
    FixAmountRequest,
    LabelEditRequest,
    RefundCreated,
    RefundRequest,
    TransferCreated,
    TransferRequest,
)
from mesl_finance.ledger.application.edit_labels import EditLabels, EditLabelsCommand
from mesl_finance.ledger.application.fix_amount import FixAmount, FixAmountCommand
from mesl_finance.ledger.application.list_entries import ListEntries
from mesl_finance.ledger.application.record_deposit import RecordDeposit, RecordDepositCommand
from mesl_finance.ledger.application.record_expense import RecordExpense, RecordExpenseCommand
from mesl_finance.ledger.application.record_refund import RecordRefund, RecordRefundCommand
from mesl_finance.ledger.application.record_transfer import RecordTransfer, RecordTransferCommand
from mesl_finance.ledger.domain.entry import EntryKind
from mesl_finance.ledger.domain.entry_list import EntryView, ListEntriesQuery
from mesl_finance.shared.api.responses import problem_responses

router = APIRouter(tags=["ledger"])


def get_record_deposit(request: Request) -> RecordDeposit:
    return cast(RecordDeposit, request.app.state.record_deposit)


def get_record_expense(request: Request) -> RecordExpense:
    return cast(RecordExpense, request.app.state.record_expense)


def get_record_refund(request: Request) -> RecordRefund:
    return cast(RecordRefund, request.app.state.record_refund)


def get_record_transfer(request: Request) -> RecordTransfer:
    return cast(RecordTransfer, request.app.state.record_transfer)


def get_fix_amount(request: Request) -> FixAmount:
    return cast(FixAmount, request.app.state.fix_amount)


def get_edit_labels(request: Request) -> EditLabels:
    return cast(EditLabels, request.app.state.edit_labels)


def get_list_entries(request: Request) -> ListEntries:
    return cast(ListEntries, request.app.state.list_entries)


@router.post(
    "/deposits",
    status_code=201,
    summary="Record money in",
    responses=problem_responses(401, 409, 422),
)
async def post_deposit(
    body: DepositRequest,
    user: Annotated[str, Depends(current_actor)],
    record_deposit: Annotated[RecordDeposit, Depends(get_record_deposit)],
) -> EntryCreated:
    """Money IN: fees, sponsorship, admin grants, anything (B-13/B-14).

    Without `envelope_id` the amount lands in the "Unallocated General" pool;
    naming one puts it there instead (e.g. an event's admin grant). A weekly
    fee needs `source="weekly_fee"` + `member_id` and must NOT name an
    envelope — the pool owns every member payment flow (db/schema.sql:
    check_shape). Returns `{"id"}`; unknown references (member / envelope /
    cost center) answer 422 `unknown_reference`, PostgreSQL's own walls
    (inactive envelope, pre-tenure date, no open tenure) 409.
    """
    entry_id = await record_deposit(RecordDepositCommand(**body.model_dump()), actor=user)
    return EntryCreated(id=entry_id)


@router.post(
    "/expenses",
    status_code=201,
    summary="Record money out",
    responses=problem_responses(401, 409, 422),
)
async def post_expense(
    body: ExpenseRequest,
    user: Annotated[str, Depends(current_actor)],
    record_expense: Annotated[RecordExpense, Depends(get_record_expense)],
) -> ExpenseCreated:
    """Money OUT of one envelope (envelope required — the pool counts too).

    Whole-BDT positive amount; one negative line is written (check_shape,
    db/schema.sql:351-352). Answers `{id, kind: "expense", balance}` with the
    envelope's balance AFTER the write. Overdraw is refused by the database
    (409 `rule_violation`); a wrong amount later gets corrected with
    fix-amount, never edited (B-18).
    """
    entry_id, balance = await record_expense(RecordExpenseCommand(**body.model_dump()), actor=user)
    return ExpenseCreated(id=entry_id, kind=EntryKind.EXPENSE, balance=balance)


@router.post(
    "/refunds",
    status_code=201,
    summary="Refund a member's credit",
    responses=problem_responses(401, 409, 422),
)
async def post_refund(
    body: RefundRequest,
    user: Annotated[str, Depends(current_actor)],
    record_refund: Annotated[RecordRefund, Depends(get_record_refund)],
) -> RefundCreated:
    """Money back to a member — one expense line on the POOL only (D-109).

    No `envelope_id` in the body: the database itself forces member-linked
    flows through the pool (db/schema.sql:364-367). Answers the same shape as
    an expense. There is no cap on a member's credit — only the pool balance
    guards the refund (Q6, D-109).
    """
    entry_id, balance = await record_refund(RecordRefundCommand(**body.model_dump()), actor=user)
    return RefundCreated(id=entry_id, kind=EntryKind.EXPENSE, balance=balance)


@router.post(
    "/transfers",
    status_code=201,
    summary="Move money between envelopes",
    responses=problem_responses(401, 409, 422),
)
async def post_transfer(
    body: TransferRequest,
    user: Annotated[str, Depends(current_actor)],
    record_transfer: Annotated[RecordTransfer, Depends(get_record_transfer)],
) -> TransferCreated:
    """One transfer = two lines (out, in) and a required note.

    Exactly two envelopes per call; both must be live (409 for inactive).
    Same envelope on both sides is refused app-side (422). Returns
    `{id, kind: "transfer", from_balance, to_balance}` — both balances read
    after the write.
    """
    entry_id, from_balance, to_balance = await record_transfer(
        RecordTransferCommand(**body.model_dump()), actor=user
    )
    return TransferCreated(
        id=entry_id,
        kind=EntryKind.TRANSFER,
        from_balance=from_balance,
        to_balance=to_balance,
    )


@router.post(
    "/entries/{entry_id}/fix-amount",
    status_code=201,
    summary="Fix one amount (reversal + replacement)",
    responses=problem_responses(401, 409, 422),
)
async def post_fix_amount(
    entry_id: int,
    body: FixAmountRequest,
    user: Annotated[str, Depends(current_actor)],
    fix_amount: Annotated[FixAmount, Depends(get_fix_amount)],
) -> FixAmountCreated:
    """Correct a WRONG AMOUNT on a deposit or expense — the ONLY way (B-18).

    One transaction writes a reversal mirroring the original plus a
    replacement carrying the new amount, the request's date and note
    (D-088). Returns `{id, kind, reversal_id, corrected_from, balance}`;
    `GET /entries` then shows ONE line. Fixes a transfer/sweep/opening? Not
    here (422 `validation_failed`) — those need their own action. An
    already-fixed entry is 409 `unique` on `reverses_id`.
    """
    replacement_id, reversal_id, kind, balance = await fix_amount(
        FixAmountCommand(entry_id=entry_id, **body.model_dump()), actor=user
    )
    return FixAmountCreated(
        id=replacement_id,
        kind=kind,
        reversal_id=reversal_id,
        corrected_from=entry_id,
        balance=balance,
    )


@router.post(
    "/entries/{entry_id}/edit-labels",
    summary="Correct descriptive labels",
    responses={**problem_responses(401, 409, 422)},
)
async def post_edit_labels(
    entry_id: int,
    body: LabelEditRequest,
    user: Annotated[str, Depends(current_actor)],
    edit_labels: Annotated[EditLabels, Depends(get_edit_labels)],
) -> EntryLabelsOut:
    """Change what an entry SAYS (note, tag, cost center, date, source) — not amounts.

    Partial body: only supplied fields change; explicit `null` clears
    tag/cost_center/source; `note`/`occurred_on` may never be null (D-090 Q3).
    Every change is written by the database's `tx_label_edit` with history
    (old value → new value → who). Refusals: empty body 422, unknown entry
    422 `unknown_reference`, closed tenure / opening / source-on-non-deposit
    409.
    """
    view = await edit_labels(
        EditLabelsCommand(
            entry_id=entry_id,
            fields=frozenset(body.model_fields_set),
            **body.model_dump(),
        ),
        actor=user,
    )
    return EntryLabelsOut(
        id=view.id,
        kind=view.kind,
        note=view.note,
        tag=view.tag,
        cost_center_id=view.cost_center_id,
        occurred_on=view.occurred_on,
        source=view.source,
    )


def _entry_out(view: EntryView) -> EntryOut:
    return EntryOut(
        id=view.id,
        tenure_id=view.tenure_id,
        kind=view.kind,
        occurred_on=view.occurred_on,
        recorded_at=view.recorded_at,
        recorded_by=view.recorded_by,
        note=view.note,
        tag=view.tag,
        cost_center_id=view.cost_center_id,
        member_id=view.member_id,
        source=view.source,
        corrected_from=view.corrected_from,
    )


@router.get(
    "/entries",
    summary="List current entries",
    responses=problem_responses(401, 422),
)
async def get_entries(
    user: Annotated[str, Depends(current_actor)],
    list_entries: Annotated[ListEntries, Depends(get_list_entries)],
    tenure_id: int | None = None,
) -> list[EntryOut]:
    """The treasurer's list: every CURRENT entry, id order, NO amounts (6.7 Q3).

    From `entries_current` (db/schema.sql:426-430): a fixed amount shows as
    ONE line (the replacement, `corrected_from` naming the original);
    reversals and voided originals are hidden. Filter: optional
    `?tenure_id=`; an unknown id is `[]`, not 404.
    """
    views = await list_entries(ListEntriesQuery(tenure_id=tenure_id), actor=user)
    return [_entry_out(view) for view in views]
