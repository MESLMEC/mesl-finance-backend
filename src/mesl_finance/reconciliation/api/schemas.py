"""Request/response schemas for POST /api/v1/reconciliations (ROADMAP 10.1)."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ReconcileRequest(BaseModel):
    """What the treasurer counted against the screen."""

    model_config = ConfigDict(extra="forbid")

    counted_total: int = Field(strict=True, description="Whole BDT actually held / in notes")
    note: str = Field(default="", description="Worth keeping — the check's story")
    counted: dict[str, Annotated[int, Field(strict=True)]] | None = Field(
        default=None, description='Optional {"<envelope_id>": whole BDT} per-envelope counts'
    )


class ReconcileOut(BaseModel):
    """The recorded reconciliation, read back from the stored row."""

    id: int = Field(description="The stored check")
    through_entry_id: int = Field(description="The entry id the check reached")
    system_total: int = Field(description="What the ledger says the lab holds")
    counted_total: int = Field(description="What the treasurer counted")
    difference: int = Field(description="counted - system (0 = a match)")
    matched: bool = Field(description="True = everything agrees")


class ReconciliationStatusOut(BaseModel):
    """The `reconciliation_status` row (ROADMAP 10.2)."""

    last_match_id: int | None = Field(description="The latest MATCHING check; null before any")
    last_match_date: date | None = Field(description="When it was made; null before any")
    last_match_through_entry: int | None = Field(description="Its window end; null before any")
    days_since_last_match: int | None = Field(description="Whole days since it; null before any")
    entries_since_last_match: int = Field(description="How many entries need review now")
    latest_attempt_matched: bool | None = Field(
        description="What the newest check said (even a mismatch); null if none yet"
    )
    latest_difference: int | None = Field(description="Its difference, if any")


class UnverifiedEntryOut(BaseModel):
    """One `unverified_entries` row, in the view's own column names (ROADMAP 10.2)."""

    id: int = Field(description="The entry")
    tenure_id: int = Field(description="The tenure recorded into")
    kind: str = Field(description="The entry's kind")
    occurred_on: date = Field(description="Its business date (may be older — ID window)")
    recorded_at: datetime = Field(description="When it was recorded")
    recorded_by: str = Field(description="Which treasurer recorded it")
    note: str = Field(description="Its note")
    tag: str | None = Field(description="Its tag, if any")
    cost_center_id: int | None = Field(description="Its cost center, if any")
    member_id: int | None = Field(description="Its member, if linked")
    reverses_id: int | None = Field(description="Set on reversal entries")
    is_voided: bool = Field(description="True once fixed away (then never listed as current)")
    net_effect: int = Field(description="The envelope sum of its lines")
    size: int = Field(description="Line count")


class DifferenceSuspectOut(BaseModel):
    """One `difference_suspects()` row (ROADMAP 10.2)."""

    entry_id: int = Field(description="The candidate entry")
    kind: str = Field(description="Its kind")
    occurred_on: date = Field(description="Its date")
    effect: int = Field(description="Its matched envelope's effect")
    note: str = Field(description="Its note")
    why: str = Field(description="Which heuristic matched (extra zero / swapped / same amount)")
