"""Ensure ON DELETE CASCADE on cv_id foreign keys

Revision ID: b2c4e8f1a903
Revises: a8f3c2b1d904
Create Date: 2026-06-02

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b2c4e8f1a903"
down_revision: Union[str, Sequence[str], None] = "a8f3c2b1d904"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'career_gap_analyses'
              AND c.contype = 'f'
              AND pg_get_constraintdef(c.oid) LIKE '%cv_id%'
          LOOP
            EXECUTE format('ALTER TABLE career_gap_analyses DROP CONSTRAINT %I', r.conname);
          END LOOP;
        END $$;
        """
    )
    op.execute(
        """
        ALTER TABLE career_gap_analyses
        ADD CONSTRAINT career_gap_analyses_cv_id_fkey
        FOREIGN KEY (cv_id) REFERENCES cvs(id) ON DELETE CASCADE
        """
    )

    op.execute(
        """
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'cv_optimizations'
              AND c.contype = 'f'
              AND pg_get_constraintdef(c.oid) LIKE '%cv_id%'
          LOOP
            EXECUTE format('ALTER TABLE cv_optimizations DROP CONSTRAINT %I', r.conname);
          END LOOP;
        END $$;
        """
    )
    op.execute(
        """
        ALTER TABLE cv_optimizations
        ADD CONSTRAINT cv_optimizations_cv_id_fkey
        FOREIGN KEY (cv_id) REFERENCES cvs(id) ON DELETE CASCADE
        """
    )


def downgrade() -> None:
    pass
