"""fix_schema_bugs_remove_organization_id_from_partners

Revision ID: 58286af88f2e
Revises: 9c041691742c
Create Date: 2025-11-25 14:36:17.081604

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '58286af88f2e'
down_revision = '9c041691742c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    CRITICAL SCHEMA FIXES - Remove organization_id from partner-related tables
    and fix FK references in trade desk module.
    
    Business Logic:
    - Organization = Internal companies (main company + commission billing entities)
    - BusinessPartners = External entities (buyers/sellers/brokers)
    - ALL partners onboard to main company (no multi-tenant for partners)
    """
    
    # Step 1: Drop foreign key constraints first (before dropping columns)
    op.drop_constraint('partner_employees_organization_id_fkey', 'partner_employees', type_='foreignkey')
    op.drop_constraint('partner_documents_organization_id_fkey', 'partner_documents', type_='foreignkey')
    op.drop_constraint('partner_vehicles_organization_id_fkey', 'partner_vehicles', type_='foreignkey')
    op.drop_constraint('partner_amendments_organization_id_fkey', 'partner_amendments', type_='foreignkey')
    op.drop_constraint('partner_kyc_renewals_organization_id_fkey', 'partner_kyc_renewals', type_='foreignkey')
    
    # Step 2: Drop indexes on organization_id columns
    op.drop_index('ix_partner_employees_organization_id', table_name='partner_employees')
    op.drop_index('ix_partner_documents_organization_id', table_name='partner_documents')
    op.drop_index('ix_partner_vehicles_organization_id', table_name='partner_vehicles')
    op.drop_index('ix_partner_onboarding_applications_organization_id', table_name='partner_onboarding_applications')
    op.drop_index('ix_partner_amendments_organization_id', table_name='partner_amendments')
    op.drop_index('ix_partner_kyc_renewals_organization_id', table_name='partner_kyc_renewals')
    
    # Step 3: Drop organization_id columns from partner tables
    op.drop_column('partner_employees', 'organization_id')
    op.drop_column('partner_documents', 'organization_id')
    op.drop_column('partner_vehicles', 'organization_id')
    op.drop_column('partner_amendments', 'organization_id')
    op.drop_column('partner_kyc_renewals', 'organization_id')
    
    # Step 4: Make partner_onboarding_applications.organization_id nullable (keep for tracking)
    op.alter_column('partner_onboarding_applications', 'organization_id',
                   existing_type=sa.UUID(),
                   nullable=True,
                   comment='Auto-defaults to main company - tracks which company processed onboarding')
    
    # Step 5: Make business_partners.created_by nullable (audit field, optional in tests)
    op.alter_column('business_partners', 'created_by',
                   existing_type=sa.UUID(),
                   nullable=True,
                   comment='User who created the partner - optional')
    
    # Step 6: Fix FK references in trade_desk module (if they exist)
    # Note: These might not have explicit constraint names, so we'll use try/except in SQL
    op.execute("""
        DO $$
        BEGIN
            -- Fix requirements.buyer_branch_id FK (branches.id -> partner_locations.id)
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'requirements_buyer_branch_id_fkey' 
                AND table_name = 'requirements'
            ) THEN
                ALTER TABLE requirements DROP CONSTRAINT requirements_buyer_branch_id_fkey;
                ALTER TABLE requirements ADD CONSTRAINT requirements_buyer_branch_id_fkey 
                    FOREIGN KEY (buyer_branch_id) REFERENCES partner_locations(id) ON DELETE SET NULL;
            END IF;
            
            -- Fix availabilities.seller_branch_id FK (branches.id -> partner_locations.id)
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'availabilities_seller_branch_id_fkey' 
                AND table_name = 'availabilities'
            ) THEN
                ALTER TABLE availabilities DROP CONSTRAINT availabilities_seller_branch_id_fkey;
                ALTER TABLE availabilities ADD CONSTRAINT availabilities_seller_branch_id_fkey 
                    FOREIGN KEY (seller_branch_id) REFERENCES partner_locations(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """
    Rollback schema fixes - restore organization_id columns and old FK references.
    WARNING: This will require re-associating partners with organizations!
    """
    
    # Step 1: Add organization_id columns back to partner tables
    op.add_column('partner_employees', sa.Column('organization_id', sa.UUID(), nullable=False))
    op.add_column('partner_documents', sa.Column('organization_id', sa.UUID(), nullable=False))
    op.add_column('partner_vehicles', sa.Column('organization_id', sa.UUID(), nullable=False))
    op.add_column('partner_amendments', sa.Column('organization_id', sa.UUID(), nullable=False))
    op.add_column('partner_kyc_renewals', sa.Column('organization_id', sa.UUID(), nullable=False))
    
    # Step 2: Recreate indexes
    op.create_index('ix_partner_employees_organization_id', 'partner_employees', ['organization_id'])
    op.create_index('ix_partner_documents_organization_id', 'partner_documents', ['organization_id'])
    op.create_index('ix_partner_vehicles_organization_id', 'partner_vehicles', ['organization_id'])
    op.create_index('ix_partner_onboarding_applications_organization_id', 'partner_onboarding_applications', ['organization_id'])
    op.create_index('ix_partner_amendments_organization_id', 'partner_amendments', ['organization_id'])
    op.create_index('ix_partner_kyc_renewals_organization_id', 'partner_kyc_renewals', ['organization_id'])
    
    # Step 3: Recreate foreign key constraints
    op.create_foreign_key('partner_employees_organization_id_fkey', 'partner_employees', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('partner_documents_organization_id_fkey', 'partner_documents', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('partner_vehicles_organization_id_fkey', 'partner_vehicles', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('partner_amendments_organization_id_fkey', 'partner_amendments', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('partner_kyc_renewals_organization_id_fkey', 'partner_kyc_renewals', 'organizations', ['organization_id'], ['id'])
    
    # Step 4: Make partner_onboarding_applications.organization_id non-nullable again
    op.alter_column('partner_onboarding_applications', 'organization_id',
                   existing_type=sa.UUID(),
                   nullable=False)
    
    # Step 5: Make business_partners.created_by non-nullable again
    op.alter_column('business_partners', 'created_by',
                   existing_type=sa.UUID(),
                   nullable=False)
    
    # Step 6: Rollback FK references in trade_desk module
    op.execute("""
        DO $$
        BEGIN
            -- Rollback requirements.buyer_branch_id FK (partner_locations.id -> branches.id)
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'requirements_buyer_branch_id_fkey' 
                AND table_name = 'requirements'
            ) THEN
                ALTER TABLE requirements DROP CONSTRAINT requirements_buyer_branch_id_fkey;
                ALTER TABLE requirements ADD CONSTRAINT requirements_buyer_branch_id_fkey 
                    FOREIGN KEY (buyer_branch_id) REFERENCES branches(id) ON DELETE SET NULL;
            END IF;
            
            -- Rollback availabilities.seller_branch_id FK (partner_locations.id -> branches.id)
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'availabilities_seller_branch_id_fkey' 
                AND table_name = 'availabilities'
            ) THEN
                ALTER TABLE availabilities DROP CONSTRAINT availabilities_seller_branch_id_fkey;
                ALTER TABLE availabilities ADD CONSTRAINT availabilities_seller_branch_id_fkey 
                    FOREIGN KEY (seller_branch_id) REFERENCES branches(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

