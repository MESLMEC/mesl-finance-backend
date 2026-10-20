"""An envelope: a virtual wallet. Pure Python; PostgreSQL owns its rules."""

from dataclasses import dataclass

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class Envelope:
    """The treasurer-entered part of an envelope. A cap/priority is data, never a default."""

    name: str
    target_cap: int | None = None
    alloc_priority: int | None = None

    @classmethod
    def create(
        cls, *, name: str, target_cap: int | None = None, alloc_priority: int | None = None
    ) -> "Envelope":
        _require_name(name)
        return cls(name, target_cap, alloc_priority)

    def rename(self, name: str) -> "Envelope":
        _require_name(name)
        return Envelope(name, self.target_cap, self.alloc_priority)

    def with_settings(self, target_cap: int | None, alloc_priority: int | None) -> "Envelope":
        return Envelope(self.name, target_cap, alloc_priority)


@dataclass(frozen=True)
class EnvelopeView:
    """An envelope as stored, for the API's answers."""

    id: int
    name: str
    target_cap: int | None
    alloc_priority: int | None
    is_pool: bool
    active: bool


def _require_name(name: str) -> None:
    if not name.strip():
        raise ValidationFailed("an envelope needs a name")
