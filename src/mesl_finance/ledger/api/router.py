from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.ledger.api.schemas import (
    DepositRequest,
    EntryCreated,
    EntryLabelsOut,
    ExpenseCreated,
    ExpenseRequest,
    FixAmountCreated,
    FixAmountRequest,
    LabelEditRequest,
    TransferCreated,
    TransferRequest,
)
from mesl_finance.ledger.application.edit_labels import EditLabels, EditLabelsCommand
from mesl_finance.ledger.application.fix_amount import FixAmount, FixAmountCommand
from mesl_finance.ledger.application.record_deposit import RecordDeposit, RecordDepositCommand
from mesl_finance.ledger.application.record_expense import RecordExpense, RecordExpenseCommand
from mesl_finance.ledger.application.record_transfer import RecordTransfer, RecordTransferCommand
from mesl_finance.ledger.domain.entry import EntryKind

router = APIRouter(tags=["ledger"])


def get_record_deposit(request: Request) -> RecordDeposit:
    return cast(RecordDeposit, request.app.state.record_deposit)


def get_record_expense(request: Request) -> RecordExpense:
    return cast(RecordExpense, request.app.state.record_expense)


def get_record_transfer(request: Request) -> RecordTransfer:
    return cast(RecordTransfer, request.app.state.record_transfer)


def get_fix_amount(request: Request) -> FixAmount:
    return cast(FixAmount, request.app.state.fix_amount)


def get_edit_labels(request: Request) -> EditLabels:
    return cast(EditLabels, request.app.state.edit_labels)


@router.post("/deposits", status_code=201)
async def post_deposit(
    body: DepositRequest,
    user: Annotated[str, Depends(current_actor)],
    record_deposit: Annotated[RecordDeposit, Depends(get_record_deposit)],
) -> EntryCreated:
    entry_id = await record_deposit(RecordDepositCommand(**body.model_dump()), actor=user)
    return EntryCreated(id=entry_id)


@router.post("/expenses", status_code=201)
async def post_expense(
    body: ExpenseRequest,
    user: Annotated[str, Depends(current_actor)],
    record_expense: Annotated[RecordExpense, Depends(get_record_expense)],
) -> ExpenseCreated:
    entry_id, balance = await record_expense(RecordExpenseCommand(**body.model_dump()), actor=user)
    return ExpenseCreated(id=entry_id, kind=EntryKind.EXPENSE, balance=balance)


@router.post("/transfers", status_code=201)
async def post_transfer(
    body: TransferRequest,
    user: Annotated[str, Depends(current_actor)],
    record_transfer: Annotated[RecordTransfer, Depends(get_record_transfer)],
) -> TransferCreated:
    entry_id, from_balance, to_balance = await record_transfer(
        RecordTransferCommand(**body.model_dump()), actor=user
    )
    return TransferCreated(
        id=entry_id,
        kind=EntryKind.TRANSFER,
        from_balance=from_balance,
        to_balance=to_balance,
    )


@router.post("/entries/{entry_id}/fix-amount", status_code=201)
async def post_fix_amount(
    entry_id: int,
    body: FixAmountRequest,
    user: Annotated[str, Depends(current_actor)],
    fix_amount: Annotated[FixAmount, Depends(get_fix_amount)],
) -> FixAmountCreated:
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


@router.post("/entries/{entry_id}/edit-labels")
async def post_edit_labels(
    entry_id: int,
    body: LabelEditRequest,
    user: Annotated[str, Depends(current_actor)],
    edit_labels: Annotated[EditLabels, Depends(get_edit_labels)],
) -> EntryLabelsOut:
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
