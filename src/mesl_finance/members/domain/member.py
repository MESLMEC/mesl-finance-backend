"""A member and one membership period. Pure Python; PostgreSQL owns the period rules."""

from dataclasses import dataclass
from datetime import date

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class Member:
    """The treasurer-entered labels of a member (db/schema.sql:87-93)."""

    name: str
    batch: str | None = None
    note: str = ""

    @classmethod
    def create(cls, *, name: str, batch: str | None = None, note: str = "") -> "Member":
        require_name(name)
        return cls(name, batch, note)

    def edit(
        self,
        *,
        fields: frozenset[str],
        name: str | None = None,
        batch: str | None = None,
        note: str | None = None,
    ) -> "Member":
        """Change only the fields named; an explicit None clears `batch` only."""
        if not fields:
            raise ValidationFailed("a member edit must name at least one field")
        new_name, new_batch, new_note = self.name, self.batch, self.note
        if "name" in fields:
            if name is None:
                raise ValidationFailed("a member needs a name")
            require_name(name)
            new_name = name
        if "batch" in fields:
            new_batch = batch
        if "note" in fields:
            if note is None:
                raise ValidationFailed("a member note must be text")
            new_note = note
        return Member(new_name, new_batch, new_note)


@dataclass(frozen=True)
class MembershipPeriod:
    """One membership period; `end_date` stays NULL until the membership ends."""

    member_id: int
    start_date: date
    end_date: date | None = None

    def __post_init__(self) -> None:
        if type(self.member_id) is not int:
            raise ValidationFailed("a membership period must name its member by a whole-number id")


@dataclass(frozen=True)
class MemberView:
    """A member as stored, for the API's answers."""

    id: int
    name: str
    batch: str | None
    note: str


@dataclass(frozen=True)
class MembershipPeriodView:
    """A membership period as stored, for the API's answers."""

    id: int
    member_id: int
    start_date: date
    end_date: date | None


def require_name(name: str) -> None:
    """The app's own rule (step 7.1 Q6=b): a member needs a non-blank name."""
    if not name.strip():
        raise ValidationFailed("a member needs a name")
