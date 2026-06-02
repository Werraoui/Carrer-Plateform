"""check supabase schema (stub - restored)

Revision ID: 21409087eb19
Revises: f096ce513650
Create Date: 2026-04-25

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "21409087eb19"
down_revision: Union[str, Sequence[str], None] = "f096ce513650"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # This revision was used only to audit schema diffs.
    # It intentionally does not change the database.
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

