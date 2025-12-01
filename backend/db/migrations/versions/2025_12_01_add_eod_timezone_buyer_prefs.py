"""Add eod_cutoff, timezone, and buyer_preferences

Revision ID: 2025_12_01_eod_tz
Revises: 5ac2637fb0dd
Create Date: 2025-12-01 15:10:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_12_01_eod_tz'
down_revision = '5ac2637fb0dd'
branch_labels = None
depends_on = None


def upgrade():
    # Add eod_cutoff to availabilities table
    op.add_column('availabilities', sa.Column('eod_cutoff', sa.Time(timezone=True), nullable=True, comment='End-of-day cutoff time for expiry (timezone-aware)'))
    
    # Add eod_cutoff to requirements table
    op.add_column('requirements', sa.Column('eod_cutoff', sa.Time(timezone=True), nullable=True, comment='End-of-day cutoff time for expiry (timezone-aware)'))
    
    # Add timezone to settings_locations table
    op.add_column('settings_locations', sa.Column('timezone', sa.String(length=50), nullable=True, comment='IANA timezone (e.g., Asia/Kolkata, America/New_York)'))
    
    # Create buyer_preferences table
    op.create_table('buyer_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('buyer_partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_terms', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Preferred payment terms configuration'),
        sa.Column('delivery_terms', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Preferred delivery terms configuration'),
        sa.Column('weighment_terms', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Preferred weighment terms configuration'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['buyer_partner_id'], ['business_partners.id'], name=op.f('fk_buyer_preferences_buyer_partner_id_business_partners'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_buyer_preferences_created_by_users')),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_buyer_preferences_updated_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_buyer_preferences'))
    )
    op.create_index(op.f('ix_buyer_preferences_buyer_partner_id'), 'buyer_preferences', ['buyer_partner_id'], unique=True)


def downgrade():
    # Drop buyer_preferences table
    op.drop_index(op.f('ix_buyer_preferences_buyer_partner_id'), table_name='buyer_preferences')
    op.drop_table('buyer_preferences')
    
    # Remove timezone from settings_locations table
    op.drop_column('settings_locations', 'timezone')
    
    # Remove eod_cutoff from requirements table
    op.drop_column('requirements', 'eod_cutoff')
    
    # Remove eod_cutoff from availabilities table
    op.drop_column('availabilities', 'eod_cutoff')
