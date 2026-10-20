"""Tests for src/mesl_finance/shared/ports.py (roadmap step 2.2).

Approved in the step 2.2 brief (2026-10-20, user: all suggestions accepted):
- `Clock` port: `now() -> datetime`, timezone-aware UTC (brief Q4=a);
- `UnitOfWork` Protocol: transaction scope (`__aenter__`/`__aexit__`, `commit`)
  plus an `actor` property only; repository accessors stay feature-level
  (brief Q3=a);
- both ports are `@runtime_checkable`, so the guard tests assert structural
  conformance via isinstance. Verified in the installed stdlib source this
  session (cpython 3.15.0 typing.py): `runtime_checkable` (line 2324) enables
  isinstance/issubclass presence checks; `ProtocolMeta.__subclasscheck__`
  raises TypeError for non-method members, but `__instancecheck__`
  (line ~2093) does not -- it walks `__protocol_attrs__` with
  `getattr_static`, so a property member like `actor` is safe.
"""

from datetime import UTC, datetime
from types import TracebackType

from mesl_finance.shared.ports import Clock, UnitOfWork


def test_clock_is_satisfied_structurally() -> None:
    class FakeClock:
        def now(self) -> datetime:
            return datetime.now(UTC)

    assert isinstance(FakeClock(), Clock)


def test_clock_rejects_nonconforming_object() -> None:
    assert not isinstance(object(), Clock)


def test_unit_of_work_fake_satisfies_protocol() -> None:
    class FakeUnitOfWork:
        @property
        def actor(self) -> str:
            return "treasurer"

        async def __aenter__(self) -> "FakeUnitOfWork":
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        async def commit(self) -> None:
            return None

    assert isinstance(FakeUnitOfWork(), UnitOfWork)


def test_unit_of_work_rejects_missing_transaction_methods() -> None:
    class NotAUnitOfWork:
        @property
        def actor(self) -> str:
            return "treasurer"

    assert not isinstance(NotAUnitOfWork(), UnitOfWork)
