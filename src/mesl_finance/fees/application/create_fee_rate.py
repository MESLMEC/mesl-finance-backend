from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from mesl_finance.fees.application.ports import FeeUnitOfWork
from mesl_finance.fees.domain.fee_rate import FeeRate, FeeRateView


@dataclass(frozen=True)
class CreateFeeRateCommand:
    effective_from: date
    amount: int


class CreateFeeRate:
    """Business action: set a weekly rate, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], FeeUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: CreateFeeRateCommand, actor: str) -> FeeRateView:
        rate = FeeRate(effective_from=command.effective_from, amount=command.amount)
        async with self._unit_of_work(actor) as uow:
            view = await uow.fees.add_rate(rate, recorded_by=actor)
            await uow.commit()
        return view
