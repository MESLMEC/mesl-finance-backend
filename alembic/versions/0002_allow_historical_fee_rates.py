"""Allow historical fee rates on or after open tenure start.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION public.rate_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.effective_from < open_tenure_start() THEN
        RAISE EXCEPTION 'a rate cannot start before this tenure opened on %', open_tenure_start();
      END IF;
      RETURN NEW;
    END $$;
    """)


def downgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION public.rate_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.effective_from < open_tenure_start() THEN
        RAISE EXCEPTION 'a rate cannot start before this tenure opened on %', open_tenure_start();
      END IF;
      IF NEW.effective_from < sunday_on_or_before(current_date) THEN
        RAISE EXCEPTION 'a rate cannot be backdated before the current week (%%); '
                        'use a waiver for past weeks',
          sunday_on_or_before(current_date);
      END IF;
      RETURN NEW;
    END $$;
    """)
