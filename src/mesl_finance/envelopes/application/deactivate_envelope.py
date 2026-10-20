from collections.abc import Callable

from mesl_finance.envelopes.application.ports import EnvelopeUnitOfWork
from mesl_finance.envelopes.domain.envelope import EnvelopeView


class DeactivateEnvelope:
    """Business action: deactivate one envelope, in ONE transaction.

    The zero-balance, not-the-pool rules live in the database's envelope_guard().
    """

    def __init__(self, unit_of_work: Callable[[str], EnvelopeUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, envelope_id: int, actor: str) -> EnvelopeView | None:
        async with self._unit_of_work(actor) as uow:
            view = await uow.envelopes.deactivate(envelope_id)
            await uow.commit()
        return view
