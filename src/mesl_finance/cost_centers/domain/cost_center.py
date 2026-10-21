"""A cost center: an event, project or competition. Pure Python; PostgreSQL owns its rules."""

from dataclasses import dataclass

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class CostCenter:
    """The treasurer-entered part of a cost center. `kind` is fixed at create (5.2 Q6=a)."""

    name: str
    kind: str
    status: str = "active"

    @classmethod
    def create(cls, *, name: str, kind: str) -> "CostCenter":
        require_name(name)
        return cls(name, kind)

    def rename(self, name: str) -> "CostCenter":
        require_name(name)
        return CostCenter(name, self.kind, self.status)

    def with_status(self, status: str) -> "CostCenter":
        return CostCenter(self.name, self.kind, status)


@dataclass(frozen=True)
class CostCenterView:
    """A cost center as stored, for the API's answers."""

    id: int
    name: str
    kind: str
    status: str


def require_name(name: str) -> None:
    """The app's own rule (db/schema.sql:79 says NOT NULL only): a name is not blank."""
    if not name.strip():
        raise ValidationFailed("a cost center needs a name")
