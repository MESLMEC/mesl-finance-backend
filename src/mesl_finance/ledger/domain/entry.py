"""Ledger value objects: entry kinds, income sources and lines. Pure Python.

The per-kind shapes and the non-zero amount rule stay in PostgreSQL
(`check_shape()` at db/schema.sql:340-369 and `ledger_lines.amount` at
db/schema.sql:270); they are never duplicated here (AGENTS.md section 5).
"""

from dataclasses import dataclass
from enum import StrEnum

from mesl_finance.shared.errors import ValidationFailed


class EntryKind(StrEnum):
    """The `entry_kind` enum (db/schema.sql:240)."""

    DEPOSIT = "deposit"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    SWEEP = "sweep"
    OPENING = "opening"
    REVERSAL = "reversal"


class IncomeSource(StrEnum):
    """The `income_source` enum (db/schema.sql:241)."""

    WEEKLY_FEE = "weekly_fee"
    REGISTRATION = "registration"
    SPONSORSHIP = "sponsorship"
    ADMIN_GRANT = "admin_grant"
    DONATION = "donation"
    OTHER = "other"


@dataclass(frozen=True)
class LedgerLine:
    """One signed whole-BDT amount on one envelope (db/schema.sql:266-272)."""

    envelope_id: int
    amount: int

    def __post_init__(self) -> None:
        if type(self.envelope_id) is not int:
            raise ValidationFailed("an envelope id must be a whole number")
        if type(self.amount) is not int:
            raise ValidationFailed("a line amount must be a whole number of taka")
