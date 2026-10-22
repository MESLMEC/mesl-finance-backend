from collections.abc import Callable

from mesl_finance.members.application.ports import MemberUnitOfWork
from mesl_finance.members.domain.member import MembershipPeriodView


class ListMembershipPeriods:
    """Business action: one member's membership periods."""

    def __init__(self, unit_of_work: Callable[[str], MemberUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, member_id: int, actor: str) -> list[MembershipPeriodView] | None:
        async with self._unit_of_work(actor) as uow:
            return await uow.members.periods_for(member_id)
