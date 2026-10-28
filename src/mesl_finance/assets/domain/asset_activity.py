"""The admin report's activity row (ROADMAP 9.4). Pure Python.

The six names are `asset_activity`'s own (db/schema.sql:849-858): one row per
(asset_name, ownership, kind, source) of `asset_events_current`, with `units`
the summed quantity and `events` the count.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetActivityRow:
    asset_name: str
    ownership: str
    kind: str
    source: str | None
    units: int
    events: int
