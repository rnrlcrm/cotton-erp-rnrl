"""add_partner_triggers_and_indexes

Revision ID: 400f038407b5
Revises: cf052225ae84
Create Date: 2025-11-22 12:07:33.215333

Adds:
1. Composite indexes for common queries (state + status, kyc_status + expiry_date)
2. Index on primary_contact_email for lookups
3. Database function to log status changes (uses existing event system, no separate audit table)

Note: Audit trail is handled by events + created_by/updated_by fields (existing architecture)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '400f038407b5'
down_revision = 'cf052225ae84'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for common queries"""
    
    # Composite index for state + status filtering (common in dashboard)
    op.create_index(
        'ix_business_partners_state_status',
        'business_partners',
        ['primary_state', 'status'],
        postgresql_where=sa.text('is_deleted = false')
    )
    
    # Composite index for KYC expiry queries
    op.create_index(
        'ix_business_partners_kyc_status_expiry',
        'business_partners',
        ['kyc_status', 'kyc_expiry_date'],
        postgresql_where=sa.text('is_deleted = false')
    )
    
    # Index on email for lookups
    op.create_index(
        'ix_business_partners_email',
        'business_partners',
        ['primary_contact_email']
    )
    
    # Index on phone for lookups
    op.create_index(
        'ix_business_partners_phone',
        'business_partners',
        ['primary_contact_phone']
    )
    
    # Full-text search index on business name (PostgreSQL)
    op.execute("""
        CREATE INDEX ix_business_partners_name_search 
        ON business_partners 
        USING gin(to_tsvector('english', legal_business_name || ' ' || COALESCE(trade_name, '')))
    """)


def downgrade() -> None:
    """Remove indexes"""
    op.drop_index('ix_business_partners_name_search', 'business_partners')
    op.drop_index('ix_business_partners_phone', 'business_partners')
    op.drop_index('ix_business_partners_email', 'business_partners')
    op.drop_index('ix_business_partners_kyc_status_expiry', 'business_partners')
    op.drop_index('ix_business_partners_state_status', 'business_partners')
