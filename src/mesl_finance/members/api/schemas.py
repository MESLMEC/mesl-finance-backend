from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from mesl_finance.members.domain.adjustment import AdjustmentKind


class MemberOut(BaseModel):
    id: int = Field(description="The member")
    name: str = Field(description="The label on dues and holdings")
    batch: str | None = Field(description="Free batch label ('2024'), null allowed")
    note: str = Field(description="Free notes; NOT the money story")


class CreateMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Blank refused app-side (422)")
    batch: str | None = Field(default=None, description="Optional free label")
    note: str = Field(default="", description="Optional note")


class EditMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Omit = unchanged; blank refused")
    batch: str | None = Field(default=None, description="Omit = unchanged; explicit null CLEARS")
    note: str | None = Field(default=None, description="Omit = unchanged; explicit null clears")


class MembershipPeriodOut(BaseModel):
    id: int = Field(description="The period row")
    member_id: int = Field(description="The member it belongs to")
    start_date: date = Field(description="The day they became billable")
    end_date: date | None = Field(description="Null while the membership is OPEN")


class StartPeriodRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date = Field(description="Inside the OPEN tenure; billable from then (B-06)")


class EndPeriodRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    end_date: date = Field(description="Not before start_date; inside an open tenure")


class AdjustmentOut(BaseModel):
    id: int = Field(description="The adjustment")
    member_id: int = Field(description="The member's dues account it touched")
    kind: str = Field(description="waiver | credit_donation | opening | correction")
    amount: int = Field(description="SIGNED whole BDT per the kind's sign rule")
    occurred_on: date = Field(description="The day it took effect (open tenure only)")
    note: str = Field(description="REQUIRED for waiver and correction")
    recorded_at: datetime = Field(description="When it was recorded")
    recorded_by: str = Field(description="Investing treasurer — the JWT subject")


class CreateAdjustmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: AdjustmentKind = Field(description="One of the four; unknown → 422")
    amount: int = Field(strict=True, description="Signed whole BDT; positive adds credit")
    occurred_on: date = Field(description="Not before the open tenure; no invented default")
    note: str = Field(default="", description="Waiver/correction REQUIRE it (422)")
