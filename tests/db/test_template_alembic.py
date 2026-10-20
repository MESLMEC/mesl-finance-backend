"""Roadmap 1.4: the session template database is built by the Alembic chain.

The template must carry the alembic_version stamp (proving it came from the real
migration chain, revision 0001 executing db/schema.sql, not from a raw file
execution) and must be healthy by the database's own verify_all(). Both are
asserted on a fresh clone of the template: the clone inherits everything from the
template, and the db fixture does nothing but clone it.
"""

from __future__ import annotations

from tests.conftest import TestDb


async def test_template_clone_is_stamped_and_healthy(db: TestDb) -> None:
    versions = await db.owner.fetch("SELECT version_num FROM alembic_version")
    assert [row["version_num"] for row in versions] == ["0001"]

    problems = await db.owner.fetch("SELECT * FROM verify_all()")
    assert problems == []
