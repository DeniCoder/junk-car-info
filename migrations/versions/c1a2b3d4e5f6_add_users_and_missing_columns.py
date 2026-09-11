"""add users, notifications, appeals, audit_logs tables and missing columns

Revision ID: c1a2b3d4e5f6
Revises: fab849aae88f
Create Date: 2026-09-10

"""
from alembic import op
import sqlalchemy as sa

revision = 'c1a2b3d4e5f6'
down_revision = 'fab849aae88f'
branch_labels = None
depends_on = None


def upgrade():
    # users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_trusted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    # findings: add missing columns
    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('removal_proof_photo', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.create_index(batch_op.f('ix_findings_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key('fk_findings_user_id', 'users', ['user_id'], ['id'], ondelete='SET NULL')

    # votes: add is_trusted column and index (ix_votes_finding_fingerprint already exists)
    with op.batch_alter_table('votes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_trusted', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.create_index('ix_votes_trusted', ['is_trusted', 'vote_type'], unique=False)

    # notifications table
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=32), nullable=False, server_default='info'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('related_finding_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_finding_id'], ['findings.id'], ondelete='SET NULL'),
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notifications_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_is_read'), ['is_read'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_created_at'), ['created_at'], unique=False)

    # appeals table
    op.create_table('appeals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('finding_id', sa.String(length=36), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='pending'),
        sa.Column('admin_comment', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
    )
    with op.batch_alter_table('appeals', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_appeals_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_appeals_finding_id'), ['finding_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_appeals_status'), ['status'], unique=False)

    # audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=32), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_admin_user_id'), ['admin_user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_entity_type'), ['entity_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_entity_id'), ['entity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_created_at'), ['created_at'], unique=False)


def downgrade():
    op.drop_table('audit_logs')
    op.drop_table('appeals')
    op.drop_table('notifications')

    with op.batch_alter_table('votes', schema=None) as batch_op:
        batch_op.drop_index('ix_votes_trusted')
        batch_op.drop_index('ix_votes_finding_fingerprint')
        batch_op.drop_column('is_trusted')

    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.drop_constraint('fk_findings_user_id', type_='foreignkey')
        batch_op.drop_index('ix_findings_user_id')
        batch_op.drop_column('is_archived')
        batch_op.drop_column('removal_proof_photo')
        batch_op.drop_column('user_id')

    op.drop_table('users')
