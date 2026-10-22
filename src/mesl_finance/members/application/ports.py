from datetime import date
from typing import Protocol

from mesl_finance.members.domain.member import (
    Member,
    MembershipPeriod,
    MembershipPeriodView,
    MemberView,
)
from mesl_finance.shared.ports import UnitOfWork


class MemberRepository(Protocol):
    async def list_all(self) -> list[MemberView]:
        """Every member, in id order."""
        ...

    async def add(self, member: Member) -> MemberView:
        """Write a new member; returns the stored row."""
        ...

    async def get(self, member_id: int) -> MemberView | None:
        """One member; None when the id does not exist."""
        ...

    async def save(self, member_id: int, member: Member) -> MemberView | None:
        """Write a member's labels; None when the id does not exist."""
        ...

    async def start(self, period: MembershipPeriod) -> MembershipPeriodView | None:
        """Open one period; None when the member does not exist."""
        ...

    async def end(self, member_id: int, end_date: date) -> MembershipPeriodView | None:
        """End the open period; None when the member has none."""
        ...

    async def periods_for(self, member_id: int) -> list[MembershipPeriodView] | None:
        """One member's periods in id order; None when the member does not exist."""
        ...


class MemberUnitOfWork(UnitOfWork, Protocol):
    """The members' transaction scope: the shared scope plus its repository."""

    @property
    def members(self) -> MemberRepository: ...
