"""Request/response schemas for POST /api/v1/reconciliations (ROADMAP 10.1)."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ReconcileRequest(BaseModel):
    """What the treasurer counted against the screen."""

    model_config = ConfigDict(extra="forbid")

    counted_total: int = Field(strict=True, description="Whole BDT actually held / in notes")
    note: str = ""
    counted: dict[str, Annotated[int, Field(strict=True)]] | None = Field(
        default=None, description='Optional {"<envelope_id>": whole BDT} per-envelope counts'
    )


class ReconcileOut(BaseModel):
    """The recorded reconciliation, read back from the stored row."""

    id: int
    through_entry_id: int
    system_total: int
    counted_total: int
    difference: int
    matched: bool


class ReconciliationStatusOut(BaseModel):
    """The `reconciliation_status` row (ROADMAP 10.2)."""

    last_match_id: int | None
    last_match_date: date | None
    last_match_through_entry: int | None
    days_since_last_match: int | None
    entries_since_last_match: int
    latest_attempt_matched: bool | None
    latest_difference: int | None


class UnverifiedEntryOut(BaseModel):
    """One `unverified_entries` row, in the view's own column names (ROADMAP 10.2)."""

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


class DifferenceSuspectOut(BaseModel):
    """One `difference_suspects()` row (ROADMAP 10.2)."""

    entry_id: int
    kind: str
    occurred_on: date
    effect: int
    note: str
    why: str
