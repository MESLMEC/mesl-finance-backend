from collections.abc import Callable
from dataclasses import dataclass

from mesl_finance.envelopes.application.ports import EnvelopeUnitOfWork
from mesl_finance.envelopes.domain.envelope import Envelope, EnvelopeView


@dataclass(frozen=True)
class CreateEnvelopeCommand:
    name: str
    target_cap: int | None = None
    alloc_priority: int | None = None


class CreateEnvelope:
    """Business action: add an envelope, in ONE transaction."""

    def __init__(self, unit_of_work: Callable[[str], EnvelopeUnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self, command: CreateEnvelopeCommand, actor: str) -> EnvelopeView:
        envelope = Envelope.create(
            name=command.name,
            target_cap=command.target_cap,
            alloc_priority=command.alloc_priority,
        )
        async with self._unit_of_work(actor) as uow:
            view = await uow.envelopes.add(envelope)
            await uow.commit()
        return view
