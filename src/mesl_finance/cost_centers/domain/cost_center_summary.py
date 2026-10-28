"""The event-leftover read model (ROADMAP 8.3): ``cost_center_summary``.

The view (db/schema.sql:537-557) computes all four numbers itself: money in
(deposits), money out (expenses), swept (net of reversed sweeps) and their
difference, the leftover. This module carries no rule.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CostCenterSummary:
    """One row of ``cost_center_summary``, as the API returns it."""

    cost_center_id: int
    name: str
    kind: str
    status: str
    money_in: int
    money_out: int
    swept: int
    leftover: int
