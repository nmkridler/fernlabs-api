"""merge heads 006 and 8724d12db287

Revision ID: b85a31e1f63e
Revises: 006, 8724d12db287
Create Date: 2025-08-28 20:22:39.075967

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b85a31e1f63e'
down_revision = ('006', '8724d12db287')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
