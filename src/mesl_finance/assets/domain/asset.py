"""An asset record and its API answer. Pure Python; PostgreSQL owns the rest."""

from dataclasses import dataclass
from enum import Enum

from mesl_finance.shared.errors import ValidationFailed


class AssetMode(Enum):
    """The two tracking modes (db/schema.sql:639)."""

    INDIVIDUAL = "individual"
    COUNTED = "counted"


class AssetOwner(Enum):
    """Who the asset belongs to (db/schema.sql:640)."""

    LAB = "lab"
    ADMIN = "admin"


@dataclass(frozen=True)
class Asset:
    """The treasurer-entered labels of an asset (db/schema.sql:642-650)."""

    name: str
    mode: str
    ownership: str
    tag: str | None = None
    note: str = ""

    @classmethod
    def create(
        cls, *, name: str, mode: str, ownership: str, tag: str | None = None, note: str = ""
    ) -> "Asset":
        require_name(name)
        return cls(name, mode, ownership, tag, note)

    def edit(
        self,
        *,
        fields: frozenset[str],
        name: str | None = None,
        tag: str | None = None,
        note: str | None = None,
        mode: str | None = None,
        ownership: str | None = None,
    ) -> "Asset":
        """Change only the fields named; an explicit None clears `tag` only."""
        if not fields:
            raise ValidationFailed("an asset edit must name at least one field")
        new_name, new_tag, new_note = self.name, self.tag, self.note
        new_mode, new_ownership = self.mode, self.ownership
        if "name" in fields:
            if name is None:
                raise ValidationFailed("an asset needs a name")
            require_name(name)
            new_name = name
        if "tag" in fields:
            new_tag = tag
        if "note" in fields:
            if note is None:
                raise ValidationFailed("an asset note must be text")
            new_note = note
        if "mode" in fields:
            if mode is None:
                raise ValidationFailed("an asset needs a mode")
            new_mode = mode
        if "ownership" in fields:
            if ownership is None:
                raise ValidationFailed("an asset needs an ownership")
            new_ownership = ownership
        return Asset(new_name, new_mode, new_ownership, new_tag, new_note)


@dataclass(frozen=True)
class AssetView:
    """An asset as stored, for the API's answers."""

    id: int
    name: str
    mode: str
    ownership: str
    tag: str | None
    note: str


def require_name(name: str) -> None:
    """The app's own rule (D-070 Q4 pattern): an asset needs a non-blank name."""
    if not name.strip():
        raise ValidationFailed("an asset needs a name")
