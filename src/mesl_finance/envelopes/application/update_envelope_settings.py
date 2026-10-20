from collections.abc import Callable

from mesl_finance.envelopes.application.ports import EnvelopeUnitOfWork
from mesl_finance.envelopes.domain.envelope import EnvelopeView


class UpdateEnvelopeSettings:
    """Business action: replace an envelope's cap and priority, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], EnvelopeUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(
        self, envelope_id: int, target_cap: int | None, alloc_priority: int | None, actor: str
    ) -> EnvelopeView | None:
        async with self._unit_of_work(actor) as uow:
            view = await uow.envelopes.update_settings(envelope_id, target_cap, alloc_priority)
            await uow.commit()
        return view
