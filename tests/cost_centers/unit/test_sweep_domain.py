"""Domain tests for the sweep value object (ROADMAP 8.3).

Approved brief this session ("go with your suggestions", so every labelled
suggestion stands):

- Q3=a ``POST /api/v1/sweeps`` with body ``{cost_center_id, from_envelope_id,
  occurred_on, note}``; ``note`` is required and non-blank in the app
  (D-090 Q7=b pattern: db/schema.sql:259 requires a note on a sweep, but the
  app refuses a blank one first as 422 ``validation_failed``).
- Q5=a the app is THIN: the leftover rules (leftover <= 0, from-envelope is
  the pool, unknown ids, tenure dates) are ``sweep_leftover``'s own
  (db/schema.sql:560-574) and answer 409 - the value object pins none of them.

What these tests pin (the domain API /code must provide): ``Sweep(...)`` keeps
its four fields and refuses a blank note with ``ValidationFailed``.

The module is imported lazily, so this file collects before /code creates it
(D-069).

Library APIs used, verified in installed source this session:
- ``pytest.raises`` / ``pytest.mark.parametrize`` (pytest 9.1.1,
  .venv/lib/python3.15/site-packages/_pytest/python.py:1231);
- ``mesl_finance.shared.errors.ValidationFailed`` (repo source, read this session).
"""

from __future__ import annotations

from datetime import date
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed

DOMAIN_MODULE = "mesl_finance.cost_centers.domain.sweep"


def _module(name: str) -> ModuleType:
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} does not exist yet")


def _sweep_class() -> Any:
    return vars(_module(DOMAIN_MODULE))["Sweep"]


def _sweep(**overrides: object) -> Any:
    fields: dict[str, object] = {
        "cost_center_id": 1,
        "from_envelope_id": 2,
        "occurred_on": date(2026, 2, 8),
        "note": "event over; leftover back to pool",
    }
    fields.update(overrides)
    return _sweep_class()(**fields)


def test_a_sweep_keeps_its_cost_center_envelope_date_and_note() -> None:
    sweep = _sweep()

    assert sweep.cost_center_id == 1
    assert sweep.from_envelope_id == 2
    assert sweep.occurred_on == date(2026, 2, 8)
    assert sweep.note == "event over; leftover back to pool"


@pytest.mark.parametrize("note", ["", "   ", "\t\n"])
def test_a_blank_note_is_refused(note: str) -> None:
    with pytest.raises(ValidationFailed):
        _sweep(note=note)


def test_the_sweep_leaves_the_leftover_rules_to_the_database() -> None:
    """Q5=a: unknown ids, the pool, dates and the leftover are sweep_leftover's business."""
    sweep = _sweep(cost_center_id=9999, from_envelope_id=1, occurred_on=date(2020, 1, 1))

    assert (sweep.cost_center_id, sweep.from_envelope_id) == (9999, 1)
