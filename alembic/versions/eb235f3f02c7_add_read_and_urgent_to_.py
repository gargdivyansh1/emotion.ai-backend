"""Add READ and URGENT to notificationstatus enum

Revision ID: eb235f3f02c7
Revises: dc0cfb113057
Create Date: 2025-06-22 18:41:55.423814

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb235f3f02c7'
down_revision: Union[str, None] = 'dc0cfb113057'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add 'read' and 'urgent' to the notificationstatus enum
    op.execute("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'read';")
    op.execute("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'urgent';")

def downgrade():
    # PostgreSQL does not support removing enum values easily.
    # You'd need to create a new type and migrate data for full rollback.
    pass