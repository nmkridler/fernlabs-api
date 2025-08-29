"""Add plan connections table and update plan table

Revision ID: 005
Revises: 004_remove_artifacts_and_executions
Create Date: 2024-01-01 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to plans table
    op.add_column(
        "plans",
        sa.Column("step_type", sa.String(100), nullable=True, server_default="task"),
    )
    op.add_column("plans", sa.Column("condition", sa.Text(), nullable=True))

    # Create plan_connections table
    op.create_table(
        "plan_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "connection_type", sa.String(100), nullable=False, server_default="next"
        ),
        sa.Column("condition", sa.Text(), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_step_id"], ["plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_step_id"], ["plans.id"], ondelete="CASCADE"),
    )

    # Add index for better performance
    op.create_index(
        "ix_plan_connections_project_id", "plan_connections", ["project_id"]
    )
    op.create_index(
        "ix_plan_connections_source_step_id", "plan_connections", ["source_step_id"]
    )
    op.create_index(
        "ix_plan_connections_target_step_id", "plan_connections", ["target_step_id"]
    )


def downgrade():
    # Drop plan_connections table
    op.drop_index("ix_plan_connections_target_step_id", "plan_connections")
    op.drop_index("ix_plan_connections_source_step_id", "plan_connections")
    op.drop_index("ix_plan_connections_project_id", "plan_connections")
    op.drop_table("plan_connections")

    # Remove columns from plans table
    op.drop_column("plans", "condition")
    op.drop_column("plans", "step_type")
