"""add_capability_tables

Revision ID: 002_capabilities
Revises: 001_outbox
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_capabilities'
down_revision = '001_outbox'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create capability tables"""
    
    # Create capabilities table
    op.create_table(
        'capabilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('is_system', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Create user_capabilities table
    op.create_table(
        'user_capabilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('capability_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reason', sa.Text, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['capability_id'], ['capabilities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('user_id', 'capability_id', name='uq_user_capability'),
    )
    
    # Create role_capabilities table
    op.create_table(
        'role_capabilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('capability_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['capability_id'], ['capabilities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('role_id', 'capability_id', name='uq_role_capability'),
    )
    
    # Create indexes
    op.create_index('idx_user_capabilities_active', 'user_capabilities', ['user_id', 'capability_id', 'revoked_at', 'expires_at'])


def downgrade() -> None:
    """Drop capability tables"""
    op.drop_index('idx_user_capabilities_active', table_name='user_capabilities')
    op.drop_table('role_capabilities')
    op.drop_table('user_capabilities')
    op.drop_table('capabilities')
