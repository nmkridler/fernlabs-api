"""merge heads 003 and 005

Revision ID: 8724d12db287
Revises: 003, 005
Create Date: 2025-08-28 17:36:01.564650

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8724d12db287'
down_revision = ('003', '005')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
