"""Unit tests for the tenure read use cases: ListTenures and GetOpenTenure."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

from mesl_finance.tenures.application.read_tenures import GetOpenTenure, ListTenures
from mesl_finance.tenures.domain.tenure import TenureView


class FakeTenures:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.tenure_view = TenureView(
            id=1,
            name="2026",
            opened_on="2026-01-01",  # pyright: ignore[reportArgumentType]
        )

    async def list_all(self) -> list[TenureView]:
        self.calls.append("list_all")
        return [self.tenure_view]

    async def get_open(self) -> TenureView | None:
        self.calls.append("get_open")
        return self.tenure_view


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.tenures = FakeTenures()
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


def _factory(uows: list[FakeUow]) -> Any:
    def factory(actor: str) -> FakeUow:
        uows.append(FakeUow(actor))
        return uows[-1]

    return factory


async def test_list_tenures_uses_one_transaction_and_does_not_commit() -> None:
    uows: list[FakeUow] = []
    use_case = ListTenures(_factory(uows))

    result = await use_case(actor="treasurer")

    assert len(uows) == 1
    uow = uows[0]
    assert uow.actor == "treasurer"
    assert not uow.committed
    assert uow.tenures.calls == ["list_all"]
    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].name == "2026"


async def test_get_open_tenure_uses_one_transaction_and_does_not_commit() -> None:
    uows: list[FakeUow] = []
    use_case = GetOpenTenure(_factory(uows))

    result = await use_case(actor="treasurer")

    assert len(uows) == 1
    uow = uows[0]
    assert uow.actor == "treasurer"
    assert not uow.committed
    assert uow.tenures.calls == ["get_open"]
    assert result is not None
    assert result.id == 1
    assert result.name == "2026"
