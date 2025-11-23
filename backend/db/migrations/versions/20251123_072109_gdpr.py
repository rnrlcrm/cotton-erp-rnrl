"""Add GDPR consent and data retention tables

Revision ID: 20251123_072109_gdpr
Revises: 
Create Date: 2025-01-23 07:21:09

Implements:
- Consent management (GDPR Article 7)
- Data retention policies (GDPR Article 5)
- User rights requests (GDPR Articles 15, 17)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251123_072109_gdpr'
down_revision = None  # TODO: Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create consent_versions table
    op.create_table(
        'consent_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('consent_type', sa.Enum(
            'ESSENTIAL', 'FUNCTIONAL', 'ANALYTICS', 'MARKETING', 'DATA_SHARING', 'PROFILING',
            name='consenttype'
        ), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('consent_type', 'version', name='uq_consent_type_version'),
    )
    op.create_index('ix_consent_versions_consent_type', 'consent_versions', ['consent_type'])
    op.create_index('ix_consent_versions_is_active', 'consent_versions', ['is_active'])

    # Create user_consents table
    op.create_table(
        'user_consents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('consent_type', sa.Enum(
            'ESSENTIAL', 'FUNCTIONAL', 'ANALYTICS', 'MARKETING', 'DATA_SHARING', 'PROFILING',
            name='consenttype'
        ), nullable=False),
        sa.Column('consent_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('given', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('given_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('method', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['consent_version_id'], ['consent_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_consents_user_id', 'user_consents', ['user_id'])
    op.create_index('ix_user_consents_consent_type', 'user_consents', ['consent_type'])
    op.create_index('ix_user_consents_given', 'user_consents', ['given'])

    # Create data_retention_policies table
    op.create_table(
        'data_retention_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_category', sa.Enum(
            'USER_ACCOUNT', 'TRANSACTION', 'AUDIT_LOG', 'SESSION', 'CONSENT', 
            'COMMUNICATION', 'ANALYTICS', 'BACKUP',
            name='datacategory'
        ), nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('legal_basis', sa.Text(), nullable=True),
        sa.Column('auto_delete', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('data_category', name='uq_data_category'),
    )
    op.create_index('ix_data_retention_policies_data_category', 'data_retention_policies', ['data_category'])

    # Create user_right_requests table
    op.create_table(
        'user_right_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_type', sa.Enum(
            'ACCESS', 'RECTIFICATION', 'ERASURE', 'RESTRICTION', 'PORTABILITY', 'OBJECTION',
            name='userrighttype'
        ), nullable=False),
        sa.Column('status', sa.Enum(
            'PENDING', 'IN_PROGRESS', 'COMPLETED', 'REJECTED',
            name='requeststatus'
        ), nullable=False, server_default='PENDING'),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_reason', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_right_requests_user_id', 'user_right_requests', ['user_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_user_right_requests_user_id', table_name='user_right_requests')
    op.drop_table('user_right_requests')
    
    op.drop_index('ix_data_retention_policies_data_category', table_name='data_retention_policies')
    op.drop_table('data_retention_policies')
    
    op.drop_index('ix_user_consents_given', table_name='user_consents')
    op.drop_index('ix_user_consents_consent_type', table_name='user_consents')
    op.drop_index('ix_user_consents_user_id', table_name='user_consents')
    op.drop_table('user_consents')
    
    op.drop_index('ix_consent_versions_is_active', table_name='consent_versions')
    op.drop_index('ix_consent_versions_consent_type', table_name='consent_versions')
    op.drop_table('consent_versions')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS requeststatus')
    op.execute('DROP TYPE IF EXISTS userrighttype')
    op.execute('DROP TYPE IF EXISTS datacategory')
    op.execute('DROP TYPE IF EXISTS consenttype')
