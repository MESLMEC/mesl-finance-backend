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
class EntryView:
    """One row of ``entries_current``, as the API returns it (step 6.7 Q2=a)."""

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


@dataclass(frozen=True)
class LedgerLineView:
    """One row of ledger_lines."""

    id: int
    transaction_id: int
    envelope_id: int
    amount: int

