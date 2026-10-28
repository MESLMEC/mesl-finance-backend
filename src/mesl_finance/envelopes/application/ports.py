from typing import Protocol

from mesl_finance.envelopes.domain.allocation_context import AllocationContextView
from mesl_finance.envelopes.domain.allocation_decision import AllocationDecision
from mesl_finance.envelopes.domain.allocation_suggestion import (
    AllocationSuggestionQuery,
    AllocationSuggestionView,
)
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


class AllocationContextRepository(Protocol):
    """What the allocation header read needs; the write slices keep their own port."""

    async def get_allocation_context(self) -> AllocationContextView:
        """The one ``allocation_context`` row."""
        ...


class AllocationContextUnitOfWork(UnitOfWork, Protocol):
    """The allocation header read's transaction scope."""

    @property
    def allocation_context(self) -> AllocationContextRepository: ...


class DraftAllocationRepository(Protocol):
    """What the allocation draft read needs; the write slices keep their own port."""

    async def suggest(self, query: AllocationSuggestionQuery) -> list[AllocationSuggestionView]:
        """The ``allocation_suggestion()`` rows, in the function's own order."""
        ...


class DraftAllocationUnitOfWork(UnitOfWork, Protocol):
    """The allocation draft read's transaction scope."""

    @property
    def allocation_suggestion(self) -> DraftAllocationRepository: ...


class ConfirmAllocationRepository(Protocol):
    """What the allocation confirmation needs; the read slices keep their own port."""

    async def open_tenure_id(self) -> int:
        """The open tenure's id, or ``NoOpenTenure``."""
        ...

    async def confirm(self, decision: AllocationDecision, recorded_by: str) -> tuple[int, int]:
        """Run ``allocate()``; returns the new entry id and the pool balance after it."""
        ...


class ConfirmAllocationUnitOfWork(UnitOfWork, Protocol):
    """The allocation confirmation's transaction scope."""

    @property
    def allocations(self) -> ConfirmAllocationRepository: ...
