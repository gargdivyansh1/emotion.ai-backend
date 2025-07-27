"""add urgent to notificationtype enum

Revision ID: 61dbe5933e8e
Revises: 8c18531917bb
Create Date: 2025-06-22 22:33:51.335043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61dbe5933e8e'
down_revision: Union[str, None] = '8c18531917bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'urgent'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
