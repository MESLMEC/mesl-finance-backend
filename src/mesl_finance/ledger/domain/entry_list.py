"""The treasurer's entry list (ROADMAP 6.7): a read model, nothing else.

``entries_current`` (db/schema.sql:426-430) is the one source: it already hides
reversals and voided originals, so a corrected amount is one line whose
``corrected_from`` names the entry it replaced. The view carries no amounts, so
neither does this read model (step 6.7 Q3=a).
"""

from dataclasses import dataclass
from datetime import date, datetime

from mesl_finance.ledger.domain.entry import EntryKind, IncomeSource


@dataclass(frozen=True)
class ListEntriesQuery:
    """The list's only filter: the tenure (`None` = every tenure, step 6.7 Q4=a)."""

    tenure_id: int | None = None


@dataclass(frozen=True)
class EntryLine:
    """One signed line of an entry (issue #5). Amount is whole BDT, signed."""

    envelope_id: int
    amount: int


@dataclass(frozen=True)
class EntryView:
    """One row of ``entries_current`` with its lines and totals, as the API
    returns it (step 6.7 Q2=a; amounts added by issue #5).

    ``lines`` arrives sorted by ``envelope_id``; ``net_effect``/``size`` are
    PostgreSQL's ``unverified_entries`` pair (db/schema.sql:1099-1101), so a
    transfer's ``net_effect`` is 0 while ``size`` says how much moved.
    """

    id: int
    tenure_id: int
    kind: EntryKind
    occurred_on: date
    recorded_at: datetime
    recorded_by: str
    note: str
    tag: str | None
    cost_center_id: int | None
    member_id: int | None
    source: IncomeSource | None
    corrected_from: int | None
    lines: tuple[EntryLine, ...]
    net_effect: int
    size: int
