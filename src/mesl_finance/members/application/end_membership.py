from collections.abc import Callable
from datetime import date

from mesl_finance.members.application.ports import MemberUnitOfWork
from mesl_finance.members.domain.member import MembershipPeriodView


class EndMembership:
    """Business action: end the member's open period, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], MemberUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, member_id: int, end_date: date, actor: str
    ) -> MembershipPeriodView | None:
        async with self._unit_of_work(actor) as uow:
            view = await uow.members.end(member_id, end_date)
            await uow.commit()
        return view
