"""Remove deprecated partner_type and trade_classification columns

Revision ID: remove_partner_type
Revises: latest
Create Date: 2025-12-03 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_partner_type'
down_revision = None  # Will be set by alembic
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove deprecated columns"""
    # Remove from business_partners table
    op.drop_column('business_partners', 'partner_type')
    op.drop_column('business_partners', 'trade_classification')
    
    # Remove from partner_onboarding_applications table
    op.drop_column('partner_onboarding_applications', 'partner_type')
    op.drop_column('partner_onboarding_applications', 'trade_classification')


def downgrade() -> None:
    """Restore deprecated columns if needed"""
    # Add back to business_partners
    op.add_column('business_partners', 
        sa.Column('partner_type', sa.String(20), nullable=True))
    op.add_column('business_partners',
        sa.Column('trade_classification', sa.String(20), nullable=True))
    
    # Add back to partner_onboarding_applications
    op.add_column('partner_onboarding_applications',
        sa.Column('partner_type', sa.String(20), nullable=True))
    op.add_column('partner_onboarding_applications',
        sa.Column('trade_classification', sa.String(20), nullable=True))
