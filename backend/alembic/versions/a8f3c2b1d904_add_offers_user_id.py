"""add offers.user_id for user-pasted offers

Revision ID: a8f3c2b1d904
Revises: 4dc47435b125
Create Date: 2026-06-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a8f3c2b1d904"
down_revision: Union[str, Sequence[str], None] = "4dc47435b125"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.offers
        ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_offers_user_id ON public.offers (user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_offers_user_id")
    op.execute("ALTER TABLE public.offers DROP COLUMN IF EXISTS user_id")
