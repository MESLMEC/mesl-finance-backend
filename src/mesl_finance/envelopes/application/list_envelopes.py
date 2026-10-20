from collections.abc import Callable

from mesl_finance.envelopes.application.ports import EnvelopeUnitOfWork
from mesl_finance.envelopes.domain.envelope import EnvelopeView


class ListEnvelopes:
    """Business action: the treasurer's envelope list, every entry, in id order."""

    def __init__(self, unit_of_work: Callable[[str], EnvelopeUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, actor: str) -> list[EnvelopeView]:
        async with self._unit_of_work(actor) as uow:
            return await uow.envelopes.list_all()
