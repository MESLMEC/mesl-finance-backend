"""A weekly fee rate. Pure Python; PostgreSQL owns every week and Sunday rule."""

from dataclasses import dataclass
from datetime import date, datetime

from mesl_finance.shared.errors import ValidationFailed


@dataclass(frozen=True)
class FeeRate:
    """One rate as the treasurer enters it (db/schema.sql:106-112)."""

    effective_from: date
    amount: int

    def __post_init__(self) -> None:
        if type(self.amount) is not int:
            raise ValidationFailed("a fee rate must be a whole number of taka")


@dataclass(frozen=True)
class FeeRateView:
    """A fee rate as stored, for the API's answers."""

    id: int
    effective_from: date
    amount: int
    recorded_at: datetime
    recorded_by: str
