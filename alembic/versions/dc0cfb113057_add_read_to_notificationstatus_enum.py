"""add read to notificationstatus enum

Revision ID: dc0cfb113057
Revises: d228f1559d62
Create Date: 2025-06-22 18:38:08.932314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc0cfb113057'
down_revision: Union[str, None] = 'd228f1559d62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'READ';")

def downgrade():
    # Downgrade not supported directly for removing enum values
    pass
