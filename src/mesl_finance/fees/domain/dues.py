"""The dues overview read model (ROADMAP 7.5): ``dues_overview``, nothing else.

``dues_overview`` (db/schema.sql:627-628) is ``SELECT * FROM member_standing()
ORDER BY weeks_overdue DESC, who_name``, and every number in it is computed by
``member_standing(p_as_of date DEFAULT current_date)`` (:582-625). This module
carries no rule: PostgreSQL owns the billing, the shutdown weeks, the credits and
the overdue count.

Step 7.5 Q3=a: the function's ``who_id``/``who_name`` are exposed as
``member_id``/``member_name``; the other seven columns keep the schema's names.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class StandingView:
    """One row of ``dues_overview``, as the API returns it."""

    member_id: int
    member_name: str
    is_member_now: bool
    weeks_owed: int
    owed: int
    credits: int
    balance: int
    weeks_overdue: int
    oldest_unpaid_week: date | None
