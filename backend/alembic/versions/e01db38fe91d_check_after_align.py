"""check after align (stub - restored)

Revision ID: e01db38fe91d
Revises: 1d11800ca9ea
Create Date: 2026-04-25

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e01db38fe91d"
down_revision: Union[str, Sequence[str], None] = "1d11800ca9ea"
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

