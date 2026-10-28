"""Request/response schemas for POST /api/v1/reconciliations (ROADMAP 10.1)."""

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
