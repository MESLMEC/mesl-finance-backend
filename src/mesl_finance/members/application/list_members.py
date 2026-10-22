from collections.abc import Callable

from mesl_finance.members.application.ports import MemberUnitOfWork
from mesl_finance.members.domain.member import MemberView


class ListMembers:
    """Business action: the treasurer's member list."""

    def __init__(self, unit_of_work: Callable[[str], MemberUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[MemberView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.members.list_all()
