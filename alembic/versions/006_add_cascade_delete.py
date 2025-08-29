"""Add CASCADE DELETE to foreign key constraints

Revision ID: 006
Revises: 005
Create Date: 2024-01-01 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing foreign key constraints and recreate with CASCADE
    # This will allow deleting projects and automatically delete related records
    
    # Drop and recreate plans.project_id foreign key with CASCADE
    op.drop_constraint('plans_project_id_fkey', 'plans', type_='foreignkey')
    op.create_foreign_key(
        'plans_project_id_fkey', 'plans', 'projects', 
        ['project_id'], ['id'], ondelete='CASCADE'
    )
    
    # Drop and recreate workflows.project_id foreign key with CASCADE
    op.drop_constraint('workflows_project_id_fkey', 'workflows', type_='foreignkey')
    op.create_foreign_key(
        'workflows_project_id_fkey', 'workflows', 'projects', 
        ['project_id'], ['id'], ondelete='CASCADE'
    )
    
    # Drop and recreate agent_calls.project_id foreign key with CASCADE
    op.drop_constraint('agent_calls_project_id_fkey', 'agent_calls', type_='foreignkey')
    op.create_foreign_key(
        'agent_calls_project_id_fkey', 'agent_calls', 'projects', 
        ['project_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    # Revert to original foreign key constraints without CASCADE
    
    # Revert plans.project_id foreign key
    op.drop_constraint('plans_project_id_fkey', 'plans', type_='foreignkey')
    op.create_foreign_key(
        'plans_project_id_fkey', 'plans', 'projects', 
        ['project_id'], ['id']
    )
    
    # Revert workflows.project_id foreign key
    op.drop_constraint('workflows_project_id_fkey', 'workflows', type_='foreignkey')
    op.create_foreign_key(
        'workflows_project_id_fkey', 'workflows', 'projects', 
        ['project_id'], ['id']
    )
    
    # Revert agent_calls.project_id foreign key
    op.drop_constraint('agent_calls_project_id_fkey', 'agent_calls', type_='foreignkey')
    op.create_foreign_key(
        'agent_calls_project_id_fkey', 'agent_calls', 'projects', 
        ['project_id'], ['id']
    )
