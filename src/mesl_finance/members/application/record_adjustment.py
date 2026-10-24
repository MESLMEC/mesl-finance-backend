from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.members.application.ports import AdjustmentUnitOfWork
from mesl_finance.members.domain.adjustment import AdjustmentKind, AdjustmentView, MemberAdjustment


@dataclass(frozen=True)
class RecordAdjustmentCommand:
    kind: AdjustmentKind
    amount: int
    occurred_on: date
    note: str = ""


class RecordAdjustment:
    """Business action: write one member adjustment, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], AdjustmentUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, member_id: int, command: RecordAdjustmentCommand, actor: str
    ) -> AdjustmentView | None:
        adjustment = MemberAdjustment(
            member_id=member_id,
            kind=command.kind,
            amount=command.amount,
            occurred_on=command.occurred_on,
            note=command.note,
        )
        async with self._unit_of_work(actor) as uow:
            view = await uow.adjustments.add(adjustment, recorded_by=actor)
            await uow.commit()
        return view
