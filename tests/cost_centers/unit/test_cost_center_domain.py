"""Domain tests for the cost-center object (roadmap step 5.2).

Approved brief answers this session: Q8=b (the list also filters on `kind` and
`status`); every other question was left unanswered, so the brief's labelled
suggestions stand (same pattern as D-062/D-064/D-066):
Q1=a four action routes, Q2=a `POST /cost-centers/{id}/status`,
Q3=a create takes `name` + `kind` only and the database default makes it
`active`, Q4=a blank names are refused by the app, Q5=a PostgreSQL owns the
kind/status CHECKs (no Python enum duplication), Q6=a `kind` is fixed at
create, Q7=a the database allows any status at any time (no transition rules
invented), Q9=a the test pins the 23505 constraint name.

What these tests pin (the domain API /code must provide):
- `CostCenter.create(name=..., kind=...)`; the status is `active`
  (db/schema.sql:81-82 `DEFAULT 'active'`)
- `CostCenter.rename(name)` and `CostCenter.with_status(status)` return the
  updated object (the domain object is treated as immutable)
- a blank name is a `ValidationFailed` (Q4=a; db/schema.sql:79 says only
  NOT NULL, so the blank rule lives in the app)
- `kind` and `status` values are NOT validated here (Q5=a): the four allowed
  kinds and statuses are the table's CHECKs, pinned end to end in
  tests/cost_centers/api/test_cost_centers_api.py, never duplicated in Python.

The domain class is imported lazily, like the envelope object in step 5.1:
ruff classifies an import of a module that does not exist yet as third-party,
so a module-level import would have to be re-sorted the moment /code adds the
package. The lazy import also keeps each test's failure individual ("module
does not exist yet") instead of one collection error for the whole file.
"""

from importlib import import_module
from typing import Any

import pytest

from mesl_finance.shared.errors import ValidationFailed


def _cost_center_class() -> Any:
    try:
        module = import_module("mesl_finance.cost_centers.domain.cost_center")
    except ModuleNotFoundError:
        pytest.fail("src/mesl_finance/cost_centers/domain/cost_center.py does not exist yet")
    return vars(module)["CostCenter"]


def make(**overrides: Any) -> Any:
    fields: dict[str, Any] = {"name": "Robotics Workshop", "kind": "event"}
    fields.update(overrides)
    return _cost_center_class().create(**fields)


def test_create_defaults_status_to_active() -> None:
    cost_center = make(kind="member_project")

    assert (cost_center.name, cost_center.kind, cost_center.status) == (
        "Robotics Workshop",
        "member_project",
        "active",
    )


@pytest.mark.parametrize("name", ["", "   ", "\t\n "])
def test_create_rejects_a_blank_name(name: str) -> None:
    with pytest.raises(ValidationFailed, match="name"):
        make(name=name)


def test_rename_keeps_kind_and_status() -> None:
    renamed = make(kind="competition").with_status("completed").rename("Robotics Cup")

    assert (renamed.name, renamed.kind, renamed.status) == (
        "Robotics Cup",
        "competition",
        "completed",
    )


def test_with_status_changes_only_the_status() -> None:
    updated = make(kind="lab_project").with_status("cancelled")

    assert (updated.name, updated.kind, updated.status) == (
        "Robotics Workshop",
        "lab_project",
        "cancelled",
    )
