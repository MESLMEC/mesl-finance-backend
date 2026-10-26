"""The allocation screen header read model (ROADMAP 7.5): ``allocation_context``.

The view (db/schema.sql:630-634) computes all three numbers itself: the open
tenure's pool balance (``envelope_balances``, :413-420), the sum of the POSITIVE
``member_standing()`` balances, and their difference. This module carries no rule.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationContextView:
    """The one row of ``allocation_context``, as the API returns it."""

    pool_balance: int
    member_credit_held: int
    pool_after_member_credit: int
