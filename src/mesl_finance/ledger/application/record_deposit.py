"""Record money coming in, in ONE transaction, idempotently (issue #4).

The client sends an `Idempotency-Key`; the use case claims it before the write.
A replay (the same actor + key + request already succeeded) returns the stored
entry id without writing; a reused key with a DIFFERENT request is a conflict
(409). A failed write rolls the claim back, so the key stays free.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.ledger.application.ports import LedgerUnitOfWork
from mesl_finance.ledger.domain.deposit import Deposit
from mesl_finance.ledger.domain.entry import IncomeSource

_OPERATION = "deposit"


@dataclass(frozen=True)
class RecordDepositCommand:
    amount: int
    occurred_on: date
    source: IncomeSource
    idempotency_key: str
    note: str = ""
    tag: str | None = None
    cost_center_id: int | None = None
    member_id: int | None = None
    envelope_id: int | None = None


def _fingerprint(command: RecordDepositCommand) -> str:
    """A stable hash of the request itself (the key is the identity, not the request).

    Two requests with the same fields share a fingerprint; any changed field
    (amount, date, envelope, member, tag...) changes it, so reusing a key with
    different content is detected as a conflict (issue #4 Q4=a).
    """
    request = {
        "operation": _OPERATION,
        "amount": command.amount,
        "occurred_on": command.occurred_on.isoformat(),
        "source": command.source.value,
        "note": command.note,
        "tag": command.tag,
        "cost_center_id": command.cost_center_id,
        "member_id": command.member_id,
        "envelope_id": command.envelope_id,
    }
    encoded = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class RecordDeposit:
    """Business action: record money coming in, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], LedgerUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: RecordDepositCommand, actor: str) -> int:
        deposit = Deposit.create(
            amount=command.amount,
            occurred_on=command.occurred_on,
            source=command.source,
            note=command.note,
            tag=command.tag,
            cost_center_id=command.cost_center_id,
            member_id=command.member_id,
            envelope_id=command.envelope_id,
        )
        async with self._unit_of_work(actor) as uow:
            replay = await uow.idempotency.claim(command.idempotency_key, _fingerprint(command))
            if replay is not None:
                return int(replay)
            tenure_id = await uow.ledger.open_tenure_id()
            entry_id = await uow.ledger.add_deposit(tenure_id, deposit, recorded_by=actor)
            await uow.idempotency.remember(command.idempotency_key, entry_id)
            await uow.commit()
        return entry_id
