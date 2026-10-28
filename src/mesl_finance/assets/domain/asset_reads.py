"""Read models for the three asset reads (ROADMAP 9.3). Pure Python.

The rows mirror the schema's own columns (the 8.1 Q2=a rule): `asset_state`'s
eleven names - `with_members` included - and `asset_holdings`' five
(db/schema.sql:819-842).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetStateRow:
    """One asset's counts (asset_state, db/schema.sql:819-830)."""

    asset_id: int
    asset_name: str
    ownership: str
    mode: str
    tag: str | None
    stock: int
    damaged: int
    with_members: int
    lost: int
    scrapped: int
    exchanged: int


@dataclass(frozen=True)
class WhoHasWhatRow:
    """One member's non-zero holding (asset_holdings, db/schema.sql:832-842)."""

    asset_id: int
    asset_name: str
    member_id: int
    member_name: str
    quantity: int
