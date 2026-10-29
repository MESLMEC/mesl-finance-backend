"""The CheckHealth use case and HealthReport value object (roadmap step 12.1).

Approved step brief this session (the brief's labelled suggestions, since the
user answered "go"): Q1=a the route is `GET /api/v1/health`; Q2=a it requires
the bearer JWT like every other read; Q3=a the body is a bare JSON array of
problem strings, `[]` = healthy; Q4=a 200 when the report is empty, 503 with
the SAME body shape when it has problems; Q5=a a new `health` feature package
with its own port pair and a tiny `HealthReport` domain object; Q6=a a normal
documented route (operation inventory 52 -> 53); Q7=a a unit fake plus one real
tamper API test.

What these tests pin (the use case /code must provide):
- `CheckHealth` in `mesl_finance.health.application.check_health`, built from a
  `Callable[[str], HealthUnitOfWork]`, callable as `use_case(actor=...)` and
  returning the repository's problem list, in order, WITHOUT sorting and
  WITHOUT committing (the 7.5 Q9=a read pattern);
- the slice declares its own port pair: a `HealthRepository` exposing
  `problems() -> list[str]` and a `HealthUnitOfWork` exposing it as `.health`
  (the D-085 pattern);
- `HealthReport` in `mesl_finance.health.domain.health`, holding the problems
  and answering `healthy` (True iff there are none).

The modules are imported lazily (D-069): nothing under test exists yet, and a
module-level import of a not-yet-existing module is classified third-party by
ruff, so each test fails on its own ("does not exist yet") instead of the whole
file failing to collect.
"""

from importlib import import_module
from types import ModuleType, TracebackType
from typing import Any, Self

import pytest


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _use_case() -> Any:
    return vars(_module("mesl_finance.health.application.check_health"))["CheckHealth"]


def _report_class() -> Any:
    return vars(_module("mesl_finance.health.domain.health"))["HealthReport"]


class FakeHealth:
    def __init__(self) -> None:
        self.calls = 0
        self.answer: list[str] = ["zebra", "apple", "Mango"]

    async def problems(self) -> list[str]:
        self.calls += 1
        return self.answer


class FakeUow:
    def __init__(self, actor: str) -> None:
        self.actor = actor
        self.health = FakeHealth()
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


async def test_the_use_case_returns_the_repository_problems_in_order() -> None:
    uows: list[FakeUow] = []

    problems = await _use_case()(_factory(uows))(actor="treasurer")

    assert problems == ["zebra", "apple", "Mango"]  # the repository's own order, not sorted
    assert uows[0].health.calls == 1


async def test_the_use_case_opens_one_transaction_and_passes_the_actor() -> None:
    uows: list[FakeUow] = []

    await _use_case()(_factory(uows))(actor="treasurer")

    assert len(uows) == 1
    assert uows[0].actor == "treasurer"


async def test_the_use_case_never_commits() -> None:
    uows: list[FakeUow] = []

    await _use_case()(_factory(uows))(actor="treasurer")

    assert uows[0].committed is False  # a read never commits (7.5 Q9=a)


def test_a_report_with_no_problems_is_healthy() -> None:
    report = _report_class()(problems=())

    assert report.healthy is True
    assert report.problems == ()


def test_a_report_with_a_problem_is_unhealthy() -> None:
    report = _report_class()(problems=("a problem",))

    assert report.healthy is False
    assert report.problems == ("a problem",)
