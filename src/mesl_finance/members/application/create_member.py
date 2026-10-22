from collections.abc import Callable
from dataclasses import dataclass

from mesl_finance.members.application.ports import MemberUnitOfWork
from mesl_finance.members.domain.member import Member, MemberView


@dataclass(frozen=True)
class CreateMemberCommand:
    name: str
    batch: str | None = None
    note: str = ""


class CreateMember:
    """Business action: add a member, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], MemberUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: CreateMemberCommand, actor: str) -> MemberView:
        member = Member.create(name=command.name, batch=command.batch, note=command.note)
        async with self._unit_of_work(actor) as uow:
            view = await uow.members.add(member)
            await uow.commit()
        return view
