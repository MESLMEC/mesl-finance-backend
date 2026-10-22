"""LabelEdit value object (ROADMAP 6.6): fix one entry's descriptive fields.

The schema owns the rest. ``tx_label_edit`` (db/schema.sql:376-410) writes the
history rows, refuses opening entries and closed tenures, and refuses a date
before the tenure opened; the column grant (:1196) is exactly these five
fields. The app judges only what the request itself must know: whole-number
ids, supplied values of the right type, an edit that names at least one field,
and a blank note for a kind that needs one (db/schema.sql:259, step 6.6 Q7=b).
"""

from dataclasses import dataclass
from datetime import date

from mesl_finance.ledger.domain.entry import EntryKind, IncomeSource
from mesl_finance.shared.errors import ValidationFailed

EDITABLE_FIELDS = frozenset({"note", "tag", "cost_center_id", "occurred_on", "source"})

# kinds whose note the schema requires to be non-blank (db/schema.sql:259)
_NOTE_REQUIRED_KINDS = frozenset({EntryKind.TRANSFER, EntryKind.SWEEP, EntryKind.REVERSAL})


@dataclass(frozen=True)
class LabelEdit:
    """The labels the treasurer asked to change, and only those."""

    entry_id: int
    fields: frozenset[str]
    note: str | None = None
    tag: str | None = None
    cost_center_id: int | None = None
    occurred_on: date | None = None
    source: IncomeSource | None = None

    @classmethod
    def create(
        cls,
        *,
        entry_id: int,
        fields: frozenset[str],
        note: str | None = None,
        tag: str | None = None,
        cost_center_id: int | None = None,
        occurred_on: date | None = None,
        source: IncomeSource | None = None,
    ) -> "LabelEdit":
        if type(entry_id) is not int:
            raise ValidationFailed("the entry to relabel must be named by a whole-number id")
        if not fields:
            raise ValidationFailed("a label edit must name at least one field")
        unknown = fields - EDITABLE_FIELDS
        if unknown:
            raise ValidationFailed(f"these fields are not labels: {', '.join(sorted(unknown))}")
        if "note" in fields and type(note) is not str:
            raise ValidationFailed("a note must be text")
        if "tag" in fields and tag is not None and type(tag) is not str:
            raise ValidationFailed("a tag must be text or empty")
        if (
            "cost_center_id" in fields
            and cost_center_id is not None
            and type(cost_center_id) is not int
        ):
            raise ValidationFailed("a cost center must be named by a whole-number id")
        if "occurred_on" in fields and type(occurred_on) is not date:
            raise ValidationFailed("the date must be a date")
        if "source" in fields and source is not None and type(source) is not IncomeSource:
            raise ValidationFailed("the source must be an income source")
        return cls(entry_id, fields, note, tag, cost_center_id, occurred_on, source)

    def validate_for(self, kind: EntryKind) -> None:
        """Refuse a blank note for a kind the schema requires one for (Q7=b)."""
        if "note" in self.fields and kind in _NOTE_REQUIRED_KINDS and not (self.note or "").strip():
            raise ValidationFailed(f"a {kind.value} needs a note")


@dataclass(frozen=True)
class LabelView:
    """An entry's labels after the edit (the response body, Q5=a)."""

    id: int
    kind: EntryKind
    note: str
    tag: str | None
    cost_center_id: int | None
    occurred_on: date
    source: IncomeSource | None
