from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from mesl_finance.auth.api.dependencies import current_actor
from mesl_finance.ledger.api.schemas import DepositRequest, EntryCreated
from mesl_finance.ledger.application.record_deposit import RecordDeposit, RecordDepositCommand

router = APIRouter(tags=["ledger"])


def get_record_deposit(request: Request) -> RecordDeposit:
    return cast(RecordDeposit, request.app.state.record_deposit)


@router.post("/deposits", status_code=201)
async def post_deposit(
    body: DepositRequest,
    user: Annotated[str, Depends(current_actor)],
    record_deposit: Annotated[RecordDeposit, Depends(get_record_deposit)],
) -> EntryCreated:
    entry_id = await record_deposit(RecordDepositCommand(**body.model_dump()), actor=user)
    return EntryCreated(id=entry_id)
