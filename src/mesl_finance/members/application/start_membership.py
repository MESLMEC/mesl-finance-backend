from collections.abc import Callable
from datetime import date

from mesl_finance.members.application.ports import MemberUnitOfWork
from mesl_finance.members.domain.member import MembershipPeriod, MembershipPeriodView


class StartMembership:
    """Business action: open one membership period, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], MemberUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, member_id: int, start_date: date, actor: str
    ) -> MembershipPeriodView | None:
        period = MembershipPeriod(member_id=member_id, start_date=start_date)
        async with self._unit_of_work(actor) as uow:
            view = await uow.members.start(period)
            await uow.commit()
        return view
