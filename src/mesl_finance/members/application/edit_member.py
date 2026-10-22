from collections.abc import Callable
from dataclasses import dataclass

from mesl_finance.members.application.ports import MemberUnitOfWork
from mesl_finance.members.domain.member import Member, MemberView


@dataclass(frozen=True)
class EditMemberCommand:
    fields: frozenset[str]
    name: str | None = None
    batch: str | None = None
    note: str | None = None


class EditMember:
    """Business action: change a member's labels, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], MemberUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, member_id: int, command: EditMemberCommand, actor: str
    ) -> MemberView | None:
        async with self._unit_of_work(actor) as uow:
            stored = await uow.members.get(member_id)
            if stored is None:
                return None
            member = Member(name=stored.name, batch=stored.batch, note=stored.note).edit(
                fields=command.fields,
                name=command.name,
                batch=command.batch,
                note=command.note,
            )
            view = await uow.members.save(member_id, member)
            await uow.commit()
        return view
