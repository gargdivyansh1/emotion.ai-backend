"""Add READ and URGENT to notificationstatus enum

Revision ID: 5531df76a5ca
Revises: eb235f3f02c7
Create Date: 2025-06-22 18:42:55.431363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5531df76a5ca'
down_revision: Union[str, None] = 'eb235f3f02c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add 'read' and 'urgent' to the notificationstatus enum
    op.execute("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'READ';")
    op.execute("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'URGENT';")

def downgrade():
    # PostgreSQL does not support removing enum values easily.
    # You'd need to create a new type and migrate data for full rollback.
    pass