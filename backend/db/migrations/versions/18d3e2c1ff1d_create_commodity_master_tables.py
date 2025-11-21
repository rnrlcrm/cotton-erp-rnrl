"""create_commodity_master_tables

Revision ID: 18d3e2c1ff1d
Revises: bc14937b8b59
Create Date: 2025-11-21 08:27:57.385138

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '18d3e2c1ff1d'
down_revision = 'bc14937b8b59'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all commodity master tables"""
    
    # 1. Commodities table (core entity)
    op.create_table(
        'commodities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('hsn_code', sa.String(length=20), nullable=True),
        sa.Column('gst_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('uom', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_commodities_name', 'commodities', ['name'])
    op.create_index('ix_commodities_category', 'commodities', ['category'])
    op.create_index('ix_commodities_hsn_code', 'commodities', ['hsn_code'])
    op.create_index('ix_commodities_is_active', 'commodities', ['is_active'])
    
    # 2. Commodity varieties
    op.create_table(
        'commodity_varieties',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('commodity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_standard', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_commodity_varieties_commodity_id', 'commodity_varieties', ['commodity_id'])
    op.create_index('ix_commodity_varieties_code', 'commodity_varieties', ['code'])
    
    # 3. Commodity parameters
    op.create_table(
        'commodity_parameters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('commodity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parameter_name', sa.String(length=100), nullable=False),
        sa.Column('parameter_type', sa.String(length=50), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('min_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('max_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('default_value', sa.String(length=100), nullable=True),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('display_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_commodity_parameters_commodity_id', 'commodity_parameters', ['commodity_id'])
    
    # 4. System commodity parameters (AI reference data)
    op.create_table(
        'system_commodity_parameters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('commodity_category', sa.String(length=100), nullable=False),
        sa.Column('parameter_name', sa.String(length=100), nullable=False),
        sa.Column('parameter_type', sa.String(length=50), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('typical_range_min', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('typical_range_max', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_system_parameters_category', 'system_commodity_parameters', ['commodity_category'])
    
    # 5. Trade types
    op.create_table(
        'trade_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_trade_types_is_active', 'trade_types', ['is_active'])
    
    # 6. Bargain types
    op.create_table(
        'bargain_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_bargain_types_is_active', 'bargain_types', ['is_active'])
    
    # 7. Passing terms
    op.create_table(
        'passing_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requires_quality_test', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_passing_terms_is_active', 'passing_terms', ['is_active'])
    
    # 8. Weightment terms
    op.create_table(
        'weightment_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weight_deduction_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_weightment_terms_is_active', 'weightment_terms', ['is_active'])
    
    # 9. Delivery terms
    op.create_table(
        'delivery_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('includes_freight', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('includes_insurance', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_delivery_terms_is_active', 'delivery_terms', ['is_active'])
    
    # 10. Payment terms
    op.create_table(
        'payment_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('days', sa.Integer(), nullable=True),
        sa.Column('payment_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_payment_terms_is_active', 'payment_terms', ['is_active'])
    
    # 11. Commission structures
    op.create_table(
        'commission_structures',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('commodity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('trade_type_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('commission_type', sa.String(length=50), nullable=False),
        sa.Column('rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('min_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('max_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('applies_to', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trade_type_id'], ['trade_types.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_commission_commodity_id', 'commission_structures', ['commodity_id'])
    op.create_index('ix_commission_trade_type_id', 'commission_structures', ['trade_type_id'])
    op.create_index('ix_commission_is_active', 'commission_structures', ['is_active'])


def downgrade() -> None:
    """Drop all commodity master tables"""
    op.drop_index('ix_commission_is_active', table_name='commission_structures')
    op.drop_index('ix_commission_trade_type_id', table_name='commission_structures')
    op.drop_index('ix_commission_commodity_id', table_name='commission_structures')
    op.drop_table('commission_structures')
    
    op.drop_index('ix_payment_terms_is_active', table_name='payment_terms')
    op.drop_table('payment_terms')
    
    op.drop_index('ix_delivery_terms_is_active', table_name='delivery_terms')
    op.drop_table('delivery_terms')
    
    op.drop_index('ix_weightment_terms_is_active', table_name='weightment_terms')
    op.drop_table('weightment_terms')
    
    op.drop_index('ix_passing_terms_is_active', table_name='passing_terms')
    op.drop_table('passing_terms')
    
    op.drop_index('ix_bargain_types_is_active', table_name='bargain_types')
    op.drop_table('bargain_types')
    
    op.drop_index('ix_trade_types_is_active', table_name='trade_types')
    op.drop_table('trade_types')
    
    op.drop_index('ix_system_parameters_category', table_name='system_commodity_parameters')
    op.drop_table('system_commodity_parameters')
    
    op.drop_index('ix_commodity_parameters_commodity_id', table_name='commodity_parameters')
    op.drop_table('commodity_parameters')
    
    op.drop_index('ix_commodity_varieties_code', table_name='commodity_varieties')
    op.drop_index('ix_commodity_varieties_commodity_id', table_name='commodity_varieties')
    op.drop_table('commodity_varieties')
    
    op.drop_index('ix_commodities_is_active', table_name='commodities')
    op.drop_index('ix_commodities_hsn_code', table_name='commodities')
    op.drop_index('ix_commodities_category', table_name='commodities')
    op.drop_index('ix_commodities_name', table_name='commodities')
    op.drop_table('commodities')
