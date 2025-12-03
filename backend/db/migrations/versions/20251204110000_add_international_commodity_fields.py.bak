"""add_international_commodity_fields

Revision ID: 20251204110000
Revises: 20251203101518
Create Date: 2024-12-04 11:00:00.000000

Adds comprehensive international commodity support:
- Multi-currency pricing fields
- International tax codes (HS 6-digit, country-specific)
- Quality standards and certifications
- Geographic and trading data
- Exchange and market information
- Import/export compliance
- Seasonal and storage data
- Contract terms and tolerances
- International payment term fields (LC support)
- Multi-currency commission structure
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251204110000'
down_revision = '20251203101518'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==================== COMMODITIES TABLE ====================
    
    # Multi-Currency Pricing
    op.add_column('commodities', sa.Column('default_currency', sa.String(3), server_default='USD'))
    op.add_column('commodities', sa.Column('supported_currencies', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('international_pricing_unit', sa.String(50), nullable=True))
    
    # International Tax & Compliance Codes
    op.add_column('commodities', sa.Column('hs_code_6digit', sa.String(6), nullable=True))
    op.create_index('ix_commodities_hs_code_6digit', 'commodities', ['hs_code_6digit'])
    op.add_column('commodities', sa.Column('country_tax_codes', postgresql.JSON, nullable=True))
    
    # Quality Standards & Certifications
    op.add_column('commodities', sa.Column('quality_standards', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('international_grades', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('certification_required', postgresql.JSON, nullable=True))
    
    # Origin & Trading Geography
    op.add_column('commodities', sa.Column('major_producing_countries', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('major_consuming_countries', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('trading_hubs', postgresql.JSON, nullable=True))
    
    # Exchange & Market Data
    op.add_column('commodities', sa.Column('traded_on_exchanges', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('contract_specifications', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('price_volatility', sa.String(20), nullable=True))
    
    # Import/Export Controls
    op.add_column('commodities', sa.Column('export_regulations', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('import_regulations', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('phytosanitary_required', sa.Boolean, server_default='false', nullable=False))
    op.add_column('commodities', sa.Column('fumigation_required', sa.Boolean, server_default='false', nullable=False))
    
    # Seasonal & Storage
    op.add_column('commodities', sa.Column('seasonal_commodity', sa.Boolean, server_default='false', nullable=False))
    op.add_column('commodities', sa.Column('harvest_season', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('shelf_life_days', sa.Integer, nullable=True))
    op.add_column('commodities', sa.Column('storage_conditions', postgresql.JSON, nullable=True))
    
    # Contract Terms
    op.add_column('commodities', sa.Column('standard_lot_size', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('min_order_quantity', postgresql.JSON, nullable=True))
    op.add_column('commodities', sa.Column('delivery_tolerance_pct', sa.Numeric(5, 2), nullable=True))
    op.add_column('commodities', sa.Column('weight_tolerance_pct', sa.Numeric(5, 2), nullable=True))
    
    # ==================== PAYMENT TERMS TABLE ====================
    
    # Multi-Currency Support
    op.add_column('payment_terms', sa.Column('currency', sa.String(3), nullable=True))
    op.add_column('payment_terms', sa.Column('supports_multi_currency', sa.Boolean, server_default='false', nullable=False))
    
    # Letter of Credit (LC) Support
    op.add_column('payment_terms', sa.Column('supports_letter_of_credit', sa.Boolean, server_default='false', nullable=False))
    op.add_column('payment_terms', sa.Column('lc_types_supported', postgresql.JSON, nullable=True))
    op.add_column('payment_terms', sa.Column('lc_confirmation_required', sa.Boolean, server_default='false', nullable=False))
    
    # Bank Charges & Fees
    op.add_column('payment_terms', sa.Column('bank_charges_borne_by', sa.String(20), nullable=True))
    op.add_column('payment_terms', sa.Column('forex_adjustment_applicable', sa.Boolean, server_default='false', nullable=False))
    
    # International Payment Methods
    op.add_column('payment_terms', sa.Column('payment_methods_supported', postgresql.JSON, nullable=True))
    op.add_column('payment_terms', sa.Column('swift_required', sa.Boolean, server_default='false', nullable=False))
    
    # ==================== COMMISSION STRUCTURES TABLE ====================
    
    # Multi-Currency Commission
    op.add_column('commission_structures', sa.Column('currency', sa.String(3), server_default='INR'))
    op.add_column('commission_structures', sa.Column('rate_per_country', postgresql.JSON, nullable=True))
    
    # Foreign Exchange Adjustments
    op.add_column('commission_structures', sa.Column('forex_adjustment', sa.Numeric(5, 2), nullable=True))
    op.add_column('commission_structures', sa.Column('apply_forex_on_cross_border', sa.Boolean, server_default='false', nullable=False))
    
    # Volume-based International Tiers
    op.add_column('commission_structures', sa.Column('international_tier_rates', postgresql.JSON, nullable=True))


def downgrade() -> None:
    # ==================== COMMISSION STRUCTURES TABLE ====================
    op.drop_column('commission_structures', 'international_tier_rates')
    op.drop_column('commission_structures', 'apply_forex_on_cross_border')
    op.drop_column('commission_structures', 'forex_adjustment')
    op.drop_column('commission_structures', 'rate_per_country')
    op.drop_column('commission_structures', 'currency')
    
    # ==================== PAYMENT TERMS TABLE ====================
    op.drop_column('payment_terms', 'swift_required')
    op.drop_column('payment_terms', 'payment_methods_supported')
    op.drop_column('payment_terms', 'forex_adjustment_applicable')
    op.drop_column('payment_terms', 'bank_charges_borne_by')
    op.drop_column('payment_terms', 'lc_confirmation_required')
    op.drop_column('payment_terms', 'lc_types_supported')
    op.drop_column('payment_terms', 'supports_letter_of_credit')
    op.drop_column('payment_terms', 'supports_multi_currency')
    op.drop_column('payment_terms', 'currency')
    
    # ==================== COMMODITIES TABLE ====================
    op.drop_column('commodities', 'weight_tolerance_pct')
    op.drop_column('commodities', 'delivery_tolerance_pct')
    op.drop_column('commodities', 'min_order_quantity')
    op.drop_column('commodities', 'standard_lot_size')
    op.drop_column('commodities', 'storage_conditions')
    op.drop_column('commodities', 'shelf_life_days')
    op.drop_column('commodities', 'harvest_season')
    op.drop_column('commodities', 'seasonal_commodity')
    op.drop_column('commodities', 'fumigation_required')
    op.drop_column('commodities', 'phytosanitary_required')
    op.drop_column('commodities', 'import_regulations')
    op.drop_column('commodities', 'export_regulations')
    op.drop_column('commodities', 'price_volatility')
    op.drop_column('commodities', 'contract_specifications')
    op.drop_column('commodities', 'traded_on_exchanges')
    op.drop_column('commodities', 'trading_hubs')
    op.drop_column('commodities', 'major_consuming_countries')
    op.drop_column('commodities', 'major_producing_countries')
    op.drop_column('commodities', 'certification_required')
    op.drop_column('commodities', 'international_grades')
    op.drop_column('commodities', 'quality_standards')
    op.drop_column('commodities', 'country_tax_codes')
    op.drop_index('ix_commodities_hs_code_6digit', table_name='commodities')
    op.drop_column('commodities', 'hs_code_6digit')
    op.drop_column('commodities', 'international_pricing_unit')
    op.drop_column('commodities', 'supported_currencies')
    op.drop_column('commodities', 'default_currency')
