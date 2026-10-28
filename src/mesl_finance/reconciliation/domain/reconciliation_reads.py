"""Reconciliation read models (ROADMAP 10.2): pure Python, no framework imports.

Each class mirrors one database object: `reconciliation_status` (db/schema.sql:1110-1116),
`unverified_entries` (:1095-1108) and `difference_suspects()` (:1122-1157).
"""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ReconciliationStatusView:
    last_match_id: int | None
    last_match_date: date | None
    last_match_through_entry: int | None
    days_since_last_match: int | None
    entries_since_last_match: int
    latest_attempt_matched: bool | None
    latest_difference: int | None


@dataclass(frozen=True)
class UnverifiedEntryView:
    id: int
    tenure_id: int
    kind: str
    occurred_on: date
    recorded_at: datetime
    recorded_by: str
    note: str
    tag: str | None
    cost_center_id: int | None
    member_id: int | None
    reverses_id: int | None
    is_voided: bool
    net_effect: int
    size: int


@dataclass(frozen=True)
class DifferenceSuspectView:
    entry_id: int
    kind: str
    occurred_on: date
    effect: int
    note: str
    why: str
