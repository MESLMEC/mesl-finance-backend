from typing import Protocol

from mesl_finance.envelopes.domain.envelope import Envelope, EnvelopeView
from mesl_finance.shared.ports import UnitOfWork


class EnvelopeRepository(Protocol):
    async def list_all(self) -> list[EnvelopeView]:
        """Every envelope, active or not, in id order."""
        ...

    async def add(self, envelope: Envelope) -> EnvelopeView:
        """Write a new envelope; returns the stored row."""
        ...

    async def rename(self, envelope_id: int, name: str) -> EnvelopeView | None:
        """Rename one envelope; None when the id does not exist."""
        ...

    async def update_settings(
        self, envelope_id: int, target_cap: int | None, alloc_priority: int | None
    ) -> EnvelopeView | None:
        """Replace cap and priority; None when the id does not exist."""
        ...

    async def deactivate(self, envelope_id: int) -> EnvelopeView | None:
        """Deactivate one envelope; None when the id does not exist."""
        ...


class EnvelopeUnitOfWork(UnitOfWork, Protocol):
    """The envelopes' transaction scope: the shared scope plus its repository."""

    @property
    def envelopes(self) -> EnvelopeRepository: ...
