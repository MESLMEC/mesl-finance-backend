from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.ledger.api.schemas import (
    DepositRequest,
    EntryCreated,
    ExpenseCreated,
    ExpenseRequest,
)
from mesl_finance.ledger.application.record_deposit import RecordDeposit, RecordDepositCommand
from mesl_finance.ledger.application.record_expense import RecordExpense, RecordExpenseCommand
from mesl_finance.ledger.domain.entry import EntryKind

router = APIRouter(tags=["ledger"])


def get_record_deposit(request: Request) -> RecordDeposit:
    return cast(RecordDeposit, request.app.state.record_deposit)


def get_record_expense(request: Request) -> RecordExpense:
    return cast(RecordExpense, request.app.state.record_expense)


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
