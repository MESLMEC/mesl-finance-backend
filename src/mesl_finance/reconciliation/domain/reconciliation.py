"""Reconciliation domain: the screen-vs-notes check result.

This module is pure Python - no fastapi/sqlalchemy/pydantic import.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconciliationView:
    """One recorded check, as read back from the ``reconciliations`` row."""

    id: int
    through_entry_id: int
    system_total: int
    counted_total: int
    difference: int
    matched: bool
