"""Add URGENT to notification type

Revision ID: 8c18531917bb
Revises: 5531df76a5ca
Create Date: 2025-06-22 22:28:07.601533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c18531917bb'
down_revision: Union[str, None] = '5531df76a5ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'URGENT';")
    


def downgrade() -> None:
    """Downgrade schema."""
    pass
