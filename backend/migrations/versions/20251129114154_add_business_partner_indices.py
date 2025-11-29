"""add_business_partner_indices

Revision ID: 20251129114154
Revises: 20251129112546
Create Date: 2024-11-29 11:41:54

CRITICAL PERFORMANCE INDICES FOR INSIDER TRADING VALIDATION:
- Adds indices on business_partners for master-branch, corporate group, GST lookups
- Adds indices on availabilities.seller_id for insider trading pre-filter
- Adds indices on requirements.buyer_id for insider trading pre-filter
- Adds indices on partner_locations for branch lookups

INSIDER TRADING VALIDATION QUERIES (must be fast):
1. get_all_insider_relationships(partner_id) - finds all blocked trading partners
2. search_availabilities(buyer_id) - pre-filters to exclude insiders
3. validate_trade_parties(buyer_id, seller_id) - validates at reservation time

Without these indices, InsiderTradingValidator would cause:
- Slow search (full table scans on business_partners)
- Slow reservation (slow GST/corporate group lookups)
- Poor UX (2-3 second search delays)

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251129114154'
down_revision = '20251129112546'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indices for insider trading validation"""
    
    # ========================================================================
    # BUSINESS_PARTNERS INDICES (for InsiderTradingValidator)
    # ========================================================================
    
    # 1. Master-Branch Relationship Lookups
    # Query: "Find all branches of this master" (get_branches)
    # Query: "Is this partner a branch? If so, get master" (check_master_branch_relationship)
    op.create_index(
        'idx_business_partners_master_entity_id',
        'business_partners',
        ['master_entity_id'],
        unique=False,
        postgresql_where=sa.text('master_entity_id IS NOT NULL')
    )
    
    # 2. Master Entity Flag Lookups
    # Query: "Is this partner a master entity?" (check_master_branch_relationship)
    op.create_index(
        'idx_business_partners_is_master_entity',
        'business_partners',
        ['is_master_entity'],
        unique=False,
        postgresql_where=sa.text('is_master_entity = true')
    )
    
    # 3. Corporate Group Lookups
    # Query: "Find all partners in this corporate group" (get_corporate_group_members)
    op.create_index(
        'idx_business_partners_corporate_group_id',
        'business_partners',
        ['corporate_group_id'],
        unique=False,
        postgresql_where=sa.text('corporate_group_id IS NOT NULL')
    )
    
    # 4. GST Number Lookups (CRITICAL for same-GST detection)
    # Query: "Find all partners with this GST number" (get_partners_by_gst)
    op.create_index(
        'idx_business_partners_gst_number',
        'business_partners',
        ['gst_number'],
        unique=False,
        postgresql_where=sa.text("gst_number IS NOT NULL AND gst_number != ''")
    )
    
    # ========================================================================
    # AVAILABILITIES INDICES (for insider trading pre-filter in search)
    # ========================================================================
    
    # 5. Seller ID Lookup (CRITICAL for search pre-filter)
    # Query: "Find all availabilities NOT FROM these seller_ids" (search_availabilities)
    # Note: This index may already exist, check before creating
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_availabilities_seller_id'
            ) THEN
                CREATE INDEX idx_availabilities_seller_id 
                ON availabilities (seller_id);
            END IF;
        END $$;
    """)
    
    # 6. Seller + Status Composite Index (for seller dashboard)
    # Query: "Get all my availabilities with status=ACTIVE" (get_seller_availabilities)
    op.create_index(
        'idx_availabilities_seller_status',
        'availabilities',
        ['seller_id', 'status'],
        unique=False
    )
    
    # ========================================================================
    # REQUIREMENTS INDICES (for buyer-side insider trading)
    # ========================================================================
    
    # 7. Buyer ID Lookup
    # Query: "Find all requirements FROM buyer_id" (future: buyer-side insider check)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_requirements_buyer_id'
            ) THEN
                CREATE INDEX idx_requirements_buyer_id 
                ON requirements (buyer_id);
            END IF;
        END $$;
    """)
    
    # 8. Buyer + Status Composite Index
    # Query: "Get all my requirements with status=ACTIVE" (get_buyer_requirements)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_requirements_buyer_status'
            ) THEN
                CREATE INDEX idx_requirements_buyer_status 
                ON requirements (buyer_id, status);
            END IF;
        END $$;
    """)
    
    # ========================================================================
    # PARTNER_LOCATIONS INDICES (for branch location validation)
    # ========================================================================
    
    # 9. Partner ID Lookup (if table exists)
    # Query: "Find all locations for this partner" (get_partner_locations)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'partner_locations'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_partner_locations_partner_id'
                ) THEN
                    CREATE INDEX idx_partner_locations_partner_id 
                    ON partner_locations (partner_id);
                END IF;
            END IF;
        END $$;
    """)
    
    # 10. Composite Index: Partner + Location (for location validation)
    # Query: "Does this partner have this location registered?" (validate_seller_location)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'partner_locations'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'idx_partner_locations_partner_location'
                ) THEN
                    CREATE INDEX idx_partner_locations_partner_location 
                    ON partner_locations (partner_id, location_id);
                END IF;
            END IF;
        END $$;
    """)


def downgrade():
    """Remove insider trading validation indices"""
    
    # Drop availabilities indices
    op.execute("DROP INDEX IF EXISTS idx_availabilities_seller_status")
    op.execute("DROP INDEX IF EXISTS idx_availabilities_seller_id")
    
    # Drop requirements indices
    op.execute("DROP INDEX IF EXISTS idx_requirements_buyer_status")
    op.execute("DROP INDEX IF EXISTS idx_requirements_buyer_id")
    
    # Drop business_partners indices
    op.drop_index('idx_business_partners_gst_number', 'business_partners')
    op.drop_index('idx_business_partners_corporate_group_id', 'business_partners')
    op.drop_index('idx_business_partners_is_master_entity', 'business_partners')
    op.drop_index('idx_business_partners_master_entity_id', 'business_partners')
    
    # Drop partner_locations indices (if they exist)
    op.execute("DROP INDEX IF EXISTS idx_partner_locations_partner_location")
    op.execute("DROP INDEX IF EXISTS idx_partner_locations_partner_id")
