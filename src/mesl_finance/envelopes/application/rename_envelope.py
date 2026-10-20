from collections.abc import Callable

from mesl_finance.envelopes.application.ports import EnvelopeUnitOfWork
from mesl_finance.envelopes.domain.envelope import Envelope, EnvelopeView


class RenameEnvelope:
    """Business action: rename one envelope, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], EnvelopeUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, envelope_id: int, name: str, actor: str) -> EnvelopeView | None:
        envelope = Envelope.create(name=name)  # the blank-name rule lives here
        async with self._unit_of_work(actor) as uow:
            view = await uow.envelopes.rename(envelope_id, envelope.name)
            await uow.commit()
        return view
