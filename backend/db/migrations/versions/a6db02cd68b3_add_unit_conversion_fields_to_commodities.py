"""add_unit_conversion_fields_to_commodities

Revision ID: a6db02cd68b3
Revises: 58286af88f2e
Create Date: 2025-12-19 10:30:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a6db02cd68b3'
down_revision = '58286af88f2e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add unit conversion fields to commodities table.
    
    These fields support automatic unit conversion for Trade Desk:
    - base_unit: Base measurement unit (KG, METER, LITER, PIECE, SQ_METER)
    - trade_unit: Unit used in trade quantity (BALE, BAG, MT, QTL, etc.)
    - rate_unit: Unit used in rate pricing (CANDY, QTL, KGS, MT, etc.)
    - standard_weight_per_unit: Custom weight for non-catalog units
    
    Example: Cotton traded in BALES priced per CANDY
    - trade_unit = "BALE" (170 KG)
    - rate_unit = "CANDY" (355.6222 KG)
    - base_unit = "KG"
    - Conversion: 600 BALES × 170 KG/BALE × 0.002812 CANDY/KG × ₹50,000/CANDY
    """
    
    # Add base_unit column (required, default to KG for backward compatibility)
    op.add_column(
        'commodities',
        sa.Column(
            'base_unit',
            sa.String(length=50),
            nullable=False,
            server_default='KG',
            comment='Base measurement unit: KG, METER, LITER, PIECE, SQ_METER'
        )
    )
    
    # Add trade_unit column (optional)
    op.add_column(
        'commodities',
        sa.Column(
            'trade_unit',
            sa.String(length=50),
            nullable=True,
            comment='Unit used in trade quantity (BALE, BAG, MT, QTL, PIECE, etc.)'
        )
    )
    
    # Add rate_unit column (optional)
    op.add_column(
        'commodities',
        sa.Column(
            'rate_unit',
            sa.String(length=50),
            nullable=True,
            comment='Unit used in rate pricing (CANDY, QTL, KG, MT, etc.)'
        )
    )
    
    # Add standard_weight_per_unit column (optional, for custom units)
    op.add_column(
        'commodities',
        sa.Column(
            'standard_weight_per_unit',
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment='Custom weight per unit if not in catalog (in base_unit)'
        )
    )
    
    # Create indexes for performance
    op.create_index(
        'ix_commodities_base_unit',
        'commodities',
        ['base_unit']
    )
    
    op.create_index(
        'ix_commodities_trade_unit',
        'commodities',
        ['trade_unit']
    )
    
    op.create_index(
        'ix_commodities_rate_unit',
        'commodities',
        ['rate_unit']
    )


def downgrade() -> None:
    """Remove unit conversion fields"""
    
    # Drop indexes first
    op.drop_index('ix_commodities_rate_unit', table_name='commodities')
    op.drop_index('ix_commodities_trade_unit', table_name='commodities')
    op.drop_index('ix_commodities_base_unit', table_name='commodities')
    
    # Drop columns
    op.drop_column('commodities', 'standard_weight_per_unit')
    op.drop_column('commodities', 'rate_unit')
    op.drop_column('commodities', 'trade_unit')
    op.drop_column('commodities', 'base_unit')
