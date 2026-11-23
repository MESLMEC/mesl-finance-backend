from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeeRateOut(BaseModel):
    id: int = Field(description="The rate row")
    effective_from: date = Field(description="The Sunday it starts billing from")
    amount: int = Field(description="Whole BDT per member per week (B-05)")
    recorded_at: datetime = Field(description="When it was recorded")
    recorded_by: str = Field(description="Investing treasurer — the JWT subject")


class CreateFeeRateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effective_from: date = Field(description="A Sunday; not backdated; in the open tenure")
    amount: int = Field(strict=True, description="Whole BDT > 0; the CHECK guards the rest")


class ShutdownEventOut(BaseModel):
    id: int = Field(description="The event row")
    week_start: date = Field(description="The Sunday the week starts on")
    is_shutdown: bool = Field(description="True = closed; false = a mistake being undone")
    reason: str = Field(description="Why ('campus incident'); free text")
    recorded_at: datetime = Field(description="When it was recorded")
    recorded_by: str = Field(description="Investing treasurer — the JWT subject")


class SetShutdownRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weeks: list[date] = Field(
        min_length=1,
        description="The Sundays to mark (or reopen); one row each, in this order",
    )
    is_shutdown: bool = Field(
        default=True,
        description="False = undo a mistake with the latest-wins rule",
    )
    reason: str = Field(default="", description="Free text, stored on every row")

    @field_validator("weeks")
    @classmethod
    def _unique_weeks(cls, weeks: list[date]) -> list[date]:
        if len(set(weeks)) != len(weeks):
            raise ValueError("a Sunday may appear only once")
        return weeks


class ShutdownResult(BaseModel):
    weeks: int = Field(description="Rows written (one per named Sunday)")


class StandingOut(BaseModel):
    member_id: int = Field(description="The member")
    member_name: str = Field(description="Shown in the report")
    is_member_now: bool = Field(description="True while a membership period is open")
    weeks_owed: int = Field(description="Billable Sundays of their periods")
    owed: int = Field(description="Whole BDT those weeks amount to")
    credits: int = Field(description="Payments - refunds + adjustments")
    balance: int = Field(description="credits - owed (negative = behind)")
    weeks_overdue: int = Field(description="Weeks still unpaid after their credits")
    oldest_unpaid_week: date | None = Field(description="First unpaid Sunday; null = settled")
