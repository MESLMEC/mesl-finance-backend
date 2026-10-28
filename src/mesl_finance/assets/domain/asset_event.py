"""One asset event and its API answer. Pure Python; the stock rules are PostgreSQL's."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from mesl_finance.shared.errors import ValidationFailed


class AssetEventKind(Enum):
    """The nine event kinds (db/schema.sql:653-654)."""

    ACQUIRED = "acquired"
    LENT = "lent"
    RETURNED = "returned"
    DAMAGED = "damaged"
    LOST = "lost"
    REPAIRED = "repaired"
    SCRAPPED = "scrapped"
    EXCHANGED = "exchanged"
    CORRECTION = "correction"


class AcquireSource(Enum):
    """Where an acquisition came from (db/schema.sql:655)."""

    PURCHASE = "purchase"
    ADMIN = "admin"
    PROJECT_RETURN = "project_return"
    DONATION = "donation"
    REPLACEMENT = "replacement"
    OTHER = "other"


_MEMBER_KINDS = ("lent", "returned")
_MEMBER_OPTIONAL_KINDS = ("damaged", "lost")
_NOTE_REQUIRED_KINDS = ("damaged", "lost", "scrapped", "exchanged", "correction")


@dataclass(frozen=True)
class AssetEvent:
    """The treasurer-entered fields of one event (db/schema.sql:657-681).

    The quantity sign, the kind shapes and the bucket arithmetic stay
    PostgreSQL's (asset_event_guard / asset_bucket_check); the app pre-refuses
    only what the approved step chose to stop before SQL (422
    `validation_failed`): a non-positive or non-`int` quantity, the kind
    pairing of `source`, `member_id` and the required note.
    """

    kind: str
    quantity: int
    occurred_on: date
    member_id: int | None = None
    source: str | None = None
    ledger_transaction_id: int | None = None
    note: str = ""

    @classmethod
    def create(
        cls,
        *,
        kind: str,
        quantity: int,
        occurred_on: date,
        member_id: int | None = None,
        source: str | None = None,
        ledger_transaction_id: int | None = None,
        note: str = "",
    ) -> "AssetEvent":
        if type(quantity) is not int:  # bool refused too (the D-047 strictness)
            raise ValidationFailed("an event quantity must be a whole number")
        if quantity == 0:
            raise ValidationFailed("a quantity cannot be zero")
        if quantity < 0 and kind != "correction":
            raise ValidationFailed("only a correction may have a negative quantity")
        if kind in _MEMBER_KINDS and member_id is None:
            raise ValidationFailed("lending and returning need a member")
        if kind not in (*_MEMBER_KINDS, *_MEMBER_OPTIONAL_KINDS) and member_id is not None:
            raise ValidationFailed(f"a {kind} event cannot name a member")
        if (kind == "acquired") != (source is not None):
            raise ValidationFailed("a source is required on acquired and forbidden elsewhere")
        if kind in _NOTE_REQUIRED_KINDS and not note.strip():
            raise ValidationFailed(f"a {kind} event needs a note")
        return cls(kind, quantity, occurred_on, member_id, source, ledger_transaction_id, note)


@dataclass(frozen=True)
class AssetEventView:
    """An event as stored, for the API's answers (no counts; 9.3 owns reads)."""

    id: int
    asset_id: int
    kind: str
    quantity: int
    occurred_on: date
    note: str
