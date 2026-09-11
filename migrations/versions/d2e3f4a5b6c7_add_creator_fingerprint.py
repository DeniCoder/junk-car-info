"""add creator fingerprint to findings

Revision ID: d2e3f4a5b6c7
Revises: c1a2b3d4e5f6
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa


revision = "d2e3f4a5b6c7"
down_revision = "c1a2b3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("findings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("creator_fingerprint", sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table("findings", schema=None) as batch_op:
        batch_op.drop_column("creator_fingerprint")
