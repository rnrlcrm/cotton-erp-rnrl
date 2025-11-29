"""add_unit_conversion_test_reports_media

Revision ID: 20251129112546
Revises: previous_revision
Create Date: 2024-11-29 11:25:46

CRITICAL INTEGRATION UPGRADE:
- Adds unit conversion fields to integrate with Commodity Master
- Adds test report fields for AI-powered parameter extraction
- Adds media fields for AI quality detection from photos/videos
- Auto-converts seller's trade_unit → commodity's base_unit for matching

Business Rules:
- quantity_unit: BALE, BAG, KG, MT, CANDY, QTL (from commodity.trade_unit)
- quantity_in_base_unit: Auto-calculated via UnitConverter (CANDY → 355.6222 KG)
- price_unit: per KG, per CANDY, per MT (seller's preference)
- price_per_base_unit: Auto-calculated for consistent matching
- test_report_url: PDF/Image URL of lab test report
- media_urls: Photo/video URLs for AI quality detection
- ai_detected_params: AI-extracted quality from media
- manual_override_params: Flag if seller manually edited AI results

Integration Points:
- Commodity Master: base_unit, trade_unit, rate_unit fields
- UnitConverter: CANDY = 355.6222 KG, BALE = varies by region
- CommodityParameter: min_value, max_value validation
- AI Services: OCR test reports, CV quality detection

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20251129112546'
down_revision = ('a6db02cd68b3', 'b6d57334a17e')  # Merge both heads
branch_labels = None
depends_on = None


def upgrade():
    """Add unit conversion, test report, and media fields to availabilities table"""
    
    # 1. Unit Conversion Fields (integrate with Commodity Master)
    op.add_column(
        'availabilities',
        sa.Column(
            'quantity_unit',
            sa.String(20),
            nullable=True,  # Nullable initially for existing rows
            comment='Unit of quantity: BALE, BAG, KG, MT, CANDY, QTL, etc.'
        )
    )
    
    op.add_column(
        'availabilities',
        sa.Column(
            'quantity_in_base_unit',
            sa.Numeric(18, 6),
            nullable=True,
            comment='Auto-calculated quantity in commodity base_unit (KG/METER/LITER)'
        )
    )
    
    # 2. Price Unit Conversion Fields
    op.add_column(
        'availabilities',
        sa.Column(
            'price_unit',
            sa.String(20),
            nullable=True,
            comment='Unit for pricing: per KG, per CANDY, per MT, per BALE'
        )
    )
    
    op.add_column(
        'availabilities',
        sa.Column(
            'price_per_base_unit',
            sa.Numeric(15, 2),
            nullable=True,
            comment='Auto-calculated price per commodity base_unit'
        )
    )
    
    # 3. Test Report Fields (AI-powered parameter extraction)
    op.add_column(
        'availabilities',
        sa.Column(
            'test_report_url',
            sa.String(500),
            nullable=True,
            comment='PDF/Image URL of lab test report'
        )
    )
    
    op.add_column(
        'availabilities',
        sa.Column(
            'test_report_verified',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True if test report verified by admin'
        )
    )
    
    op.add_column(
        'availabilities',
        sa.Column(
            'test_report_data',
            JSONB,
            nullable=True,
            comment='AI-extracted parameters from test report: {"length": 29.0, "source": "OCR"}'
        )
    )
    
    # 4. Media Fields (AI quality detection)
    op.add_column(
        'availabilities',
        sa.Column(
            'media_urls',
            JSONB,
            nullable=True,
            comment='Photo/video URLs for AI quality detection: {"photos": [url1, url2], "videos": [url3]}'
        )
    )
    
    op.add_column(
        'availabilities',
        sa.Column(
            'ai_detected_params',
            JSONB,
            nullable=True,
            comment='AI-detected quality from photos/videos: {"color": "white", "trash": 2.5, "confidence": 0.85}'
        )
    )
    
    op.add_column(
        'availabilities',
        sa.Column(
            'manual_override_params',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True if seller manually overrode AI-detected parameters'
        )
    )
    
    # 5. Set default values for existing rows (backfill)
    # Note: This will be run BEFORE making quantity_unit NOT NULL
    op.execute("""
        UPDATE availabilities 
        SET quantity_unit = 'KG'
        WHERE quantity_unit IS NULL
    """)
    
    # 6. Make quantity_unit NOT NULL after backfill
    op.alter_column(
        'availabilities',
        'quantity_unit',
        nullable=False
    )
    
    # 7. Create indexes for unit conversion (matching engine needs fast lookup)
    op.create_index(
        'idx_availabilities_quantity_unit',
        'availabilities',
        ['quantity_unit']
    )
    
    op.create_index(
        'idx_availabilities_quantity_in_base_unit',
        'availabilities',
        ['quantity_in_base_unit']
    )
    
    # 8. Create GIN index for test_report_data (AI parameter search)
    op.execute("""
        CREATE INDEX idx_availabilities_test_report_data 
        ON availabilities USING gin (test_report_data)
    """)
    
    # 9. Create GIN index for ai_detected_params (AI quality search)
    op.execute("""
        CREATE INDEX idx_availabilities_ai_detected_params 
        ON availabilities USING gin (ai_detected_params)
    """)
    
    # 10. Add check constraint for valid quantity_unit
    op.create_check_constraint(
        'chk_quantity_unit_valid',
        'availabilities',
        sa.text(
            "quantity_unit IN ('BALE', 'BAG', 'KG', 'MT', 'CANDY', 'QTL', 'QUINTAL', "
            "'TONNE', 'METRIC_TON', 'GRAM', 'POUND', 'LITRE', 'LITER', 'GALLON', "
            "'METER', 'YARD', 'FEET', 'INCH', 'PIECE', 'UNIT', 'BOX', 'CARTON')"
        )
    )
    
    # 11. Add check constraint for quantity_in_base_unit > 0
    op.create_check_constraint(
        'chk_quantity_in_base_unit_positive',
        'availabilities',
        sa.text('quantity_in_base_unit IS NULL OR quantity_in_base_unit > 0')
    )


def downgrade():
    """Remove unit conversion, test report, and media fields"""
    
    # Drop indexes
    op.drop_index('idx_availabilities_ai_detected_params', 'availabilities')
    op.drop_index('idx_availabilities_test_report_data', 'availabilities')
    op.drop_index('idx_availabilities_quantity_in_base_unit', 'availabilities')
    op.drop_index('idx_availabilities_quantity_unit', 'availabilities')
    
    # Drop check constraints
    op.drop_constraint('chk_quantity_in_base_unit_positive', 'availabilities', type_='check')
    op.drop_constraint('chk_quantity_unit_valid', 'availabilities', type_='check')
    
    # Drop columns
    op.drop_column('availabilities', 'manual_override_params')
    op.drop_column('availabilities', 'ai_detected_params')
    op.drop_column('availabilities', 'media_urls')
    op.drop_column('availabilities', 'test_report_data')
    op.drop_column('availabilities', 'test_report_verified')
    op.drop_column('availabilities', 'test_report_url')
    op.drop_column('availabilities', 'price_per_base_unit')
    op.drop_column('availabilities', 'price_unit')
    op.drop_column('availabilities', 'quantity_in_base_unit')
    op.drop_column('availabilities', 'quantity_unit')
