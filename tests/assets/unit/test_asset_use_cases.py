"""The CreateAsset and RecordAssetEvent use cases: one transaction each.

Approved brief this session (tests 7 and 8 of the step brief): each write use
case commits once in its own transaction and passes the JWT actor down, the
same shape as the ledger and member write use cases. The slices declare their
own ports (D-085 pattern): ``AssetRepository`` with ``create_asset`` and
``add_event``, and an ``AssetUnitOfWork`` exposing it as ``.assets``.
"""

from datetime import date
from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _create_class() -> Any:
    return vars(_module("mesl_finance.assets.application.create_asset"))["CreateAsset"]


def _create_command() -> Any:
    return vars(_module("mesl_finance.assets.application.create_asset"))["CreateAssetCommand"]


def _event_use_case() -> Any:
    return vars(_module("mesl_finance.assets.application.record_event"))["RecordAssetEvent"]


def _event_command() -> Any:
    return vars(_module("mesl_finance.assets.application.record_event"))["RecordEventCommand"]


def asset_command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "name": "ESP32 DevKit",
        "mode": "counted",
        "ownership": "lab",
    }
    fields.update(overrides)
    return _create_command()(**fields)


def event_command(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "asset_id": 5,
        "kind": "acquired",
        "quantity": 10,
        "occurred_on": date(2026, 2, 1),
        "source": "purchase",
    }
    fields.update(overrides)
    return _event_command()(**fields)


class FakeAssets:
    def __init__(self) -> None:
        self.created: list[tuple[Any, str]] = []
        self.events: list[tuple[int, Any, str]] = []
        self.next_id = 42

    async def create_asset(self, asset: Any, recorded_by: str) -> Any:
        self.created.append((asset, recorded_by))
        return self.next_id

    async def add_event(self, asset_id: int, event: Any, recorded_by: str) -> int:
        self.events.append((asset_id, event, recorded_by))
        return self.next_id


class FakeUow:
    def __init__(self, actor: str, assets: FakeAssets | None = None) -> None:
        self.actor = actor
        self.assets = FakeAssets() if assets is None else assets
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


async def test_create_asset_commits_once_in_one_transaction() -> None:
    uows: list[FakeUow] = []

    view = await _create_class()(_factory(uows))(asset_command(), actor="treasurer")

    uow = uows[0]
    assert uow.actor == "treasurer"
    assert uow.committed
    asset, recorded_by = uow.assets.created[0]
    assert (asset.name, recorded_by) == ("ESP32 DevKit", "treasurer")
    assert view.id == 42


async def test_record_event_commits_once_in_one_transaction() -> None:
    uows: list[FakeUow] = []

    view = await _event_use_case()(_factory(uows))(event_command(member_id=3), actor="treasurer")

    uow = uows[0]
    assert uow.actor == "treasurer"
    assert uow.committed
    asset_id, event, recorded_by = uow.assets.events[0]
    assert (asset_id, event.kind, event.quantity, recorded_by) == (5, "acquired", 10, "treasurer")
    assert (view.id, view.asset_id, view.kind, view.quantity) == (42, 5, "acquired", 10)
