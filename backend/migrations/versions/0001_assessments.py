"""Create the assessments table.

Revision ID: 0001_assessments
Revises:
Create Date: 2026-10-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_assessments"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("assessments")
