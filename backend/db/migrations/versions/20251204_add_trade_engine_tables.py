"""Add Trade Engine tables: trades, partner_branches, trade_signatures, trade_amendments

Revision ID: 20251204_trade_engine
Revises: 829002a353b4
Create Date: 2025-12-04 12:00:00.000000

Trade Engine Phase 5:
- Instant binding contracts on negotiation acceptance
- Multi-branch address management
- Digital signature integration
- Amendment workflow
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251204_trade_engine'
down_revision = '829002a353b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add Trade Engine tables in correct dependency order:
    1. Update business_partners (add signature fields)
    2. Create partner_branches
    3. Create trades
    4. Create trade_signatures
    5. Create trade_amendments
    """
    
    # ==================================================
    # 1. UPDATE business_partners - Add signature fields
    # ==================================================
    op.add_column('business_partners',
        sa.Column('digital_signature_url', sa.String(500), nullable=True,
                  comment='URL to uploaded digital signature image')
    )
    op.add_column('business_partners',
        sa.Column('signature_tier', sa.String(20), nullable=True, server_default='BASIC',
                  comment='Signature tier: BASIC, AADHAAR_ESIGN, DSC')
    )
    op.add_column('business_partners',
        sa.Column('signature_uploaded_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Timestamp when signature was uploaded')
    )
    op.add_column('business_partners',
        sa.Column('signature_uploaded_by', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='User ID who uploaded the signature')
    )
    op.add_column('business_partners',
        sa.Column('aadhaar_number_encrypted', sa.String(255), nullable=True,
                  comment='Encrypted Aadhaar number for eSign')
    )
    op.add_column('business_partners',
        sa.Column('aadhaar_esign_enabled', sa.Boolean, nullable=False, server_default='false',
                  comment='Whether Aadhaar eSign is enabled')
    )
    op.add_column('business_partners',
        sa.Column('dsc_certificate_serial', sa.String(100), nullable=True,
                  comment='Digital Signature Certificate serial number')
    )
    op.add_column('business_partners',
        sa.Column('dsc_certificate_url', sa.String(500), nullable=True,
                  comment='URL to DSC certificate file')
    )
    
    # Add check constraint for signature tier
    op.create_check_constraint(
        'ck_business_partners_signature_tier',
        'business_partners',
        "signature_tier IN ('BASIC', 'AADHAAR_ESIGN', 'DSC') OR signature_tier IS NULL"
    )
    
    # Add foreign key for signature uploader
    op.create_foreign_key(
        'fk_business_partners_signature_uploaded_by',
        'business_partners', 'users',
        ['signature_uploaded_by'], ['id'],
        ondelete='SET NULL'
    )
    
    # ==================================================
    # 2. CREATE partner_branches table
    # ==================================================
    op.create_table(
        'partner_branches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Business partner who owns this branch'),
        
        # Branch Identification
        sa.Column('branch_code', sa.String(50), nullable=False,
                  comment='Unique branch code within partner'),
        sa.Column('branch_name', sa.String(200), nullable=False,
                  comment='Branch name/title'),
        sa.Column('branch_type', sa.String(50), nullable=True,
                  comment='HEAD_OFFICE, FACTORY, WAREHOUSE, SALES_OFFICE, REGIONAL_OFFICE'),
        
        # Address
        sa.Column('address_line1', sa.String(200), nullable=False),
        sa.Column('address_line2', sa.String(200), nullable=True),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(100), nullable=False),
        sa.Column('pincode', sa.String(10), nullable=False),
        sa.Column('country', sa.String(100), nullable=False, server_default='India'),
        
        # Geolocation (for distance calculation)
        sa.Column('latitude', sa.Numeric(10, 8), nullable=True,
                  comment='Latitude for distance calculation'),
        sa.Column('longitude', sa.Numeric(11, 8), nullable=True,
                  comment='Longitude for distance calculation'),
        
        # Tax
        sa.Column('branch_gstin', sa.String(15), nullable=True,
                  comment='Branch-specific GSTIN (if different from main)'),
        
        # Capabilities
        sa.Column('can_receive_shipments', sa.Boolean, nullable=False, server_default='true',
                  comment='Can be used as ship-to address'),
        sa.Column('can_send_shipments', sa.Boolean, nullable=False, server_default='true',
                  comment='Can be used as ship-from address'),
        sa.Column('warehouse_capacity_qtls', sa.Numeric(15, 2), nullable=True,
                  comment='Warehouse capacity in quintals'),
        
        # Commodity handling
        sa.Column('supported_commodities', postgresql.JSONB, nullable=True,
                  comment='Array of commodity types this branch can handle'),
        
        # Flags
        sa.Column('is_head_office', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_default_ship_to', sa.Boolean, nullable=False, server_default='false',
                  comment='Use as default for receiving shipments'),
        sa.Column('is_default_ship_from', sa.Boolean, nullable=False, server_default='false',
                  comment='Use as default for sending shipments'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        
        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['partner_id'], ['business_partners.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Constraints
        sa.UniqueConstraint('partner_id', 'branch_code', name='uq_partner_branch_code'),
        sa.CheckConstraint(
            "branch_type IN ('HEAD_OFFICE', 'FACTORY', 'WAREHOUSE', 'SALES_OFFICE', 'REGIONAL_OFFICE') OR branch_type IS NULL",
            name='ck_partner_branches_branch_type'
        ),
        sa.CheckConstraint('warehouse_capacity_qtls >= 0 OR warehouse_capacity_qtls IS NULL',
                           name='ck_partner_branches_positive_capacity'),
    )
    
    # Indexes for partner_branches
    op.create_index('ix_partner_branches_partner_id', 'partner_branches', ['partner_id'])
    op.create_index('ix_partner_branches_city_state', 'partner_branches', ['city', 'state'])
    op.create_index('ix_partner_branches_gstin', 'partner_branches', ['branch_gstin'])
    op.create_index('ix_partner_branches_active', 'partner_branches', ['is_active'])
    op.create_index('ix_partner_branches_branch_type', 'partner_branches', ['branch_type'])
    
    # ==================================================
    # 3. CREATE trades table
    # ==================================================
    op.create_table(
        'trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('trade_number', sa.String(50), nullable=False, unique=True,
                  comment='Unique trade number (TR-YYYY-XXXXX)'),
        
        # Link to negotiation
        sa.Column('negotiation_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Negotiation that created this trade'),
        
        # Parties (main partner IDs)
        sa.Column('buyer_partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seller_partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Selected Branches (NULL if no branches)
        sa.Column('ship_to_branch_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Buyer branch for delivery'),
        sa.Column('bill_to_branch_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Buyer branch for billing'),
        sa.Column('ship_from_branch_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Seller branch for shipment'),
        
        # Frozen Address Snapshots (JSON)
        sa.Column('ship_to_address', postgresql.JSONB, nullable=False,
                  comment='Ship-to address snapshot (frozen at trade creation)'),
        sa.Column('bill_to_address', postgresql.JSONB, nullable=False,
                  comment='Bill-to address snapshot'),
        sa.Column('ship_from_address', postgresql.JSONB, nullable=False,
                  comment='Ship-from address snapshot'),
        
        # Address Selection Metadata
        sa.Column('ship_to_address_source', sa.String(50), nullable=True,
                  comment='AUTO_PRIMARY, AUTO_SINGLE_BRANCH, USER_SELECTED, DEFAULT_BRANCH'),
        sa.Column('ship_from_address_source', sa.String(50), nullable=True),
        
        # Commodity & Pricing (from negotiation)
        sa.Column('commodity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('commodity_variety_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('quantity', sa.Numeric(15, 3), nullable=False,
                  comment='Quantity in units'),
        sa.Column('unit', sa.String(20), nullable=False, server_default='QUINTALS'),
        sa.Column('price_per_unit', sa.Numeric(15, 2), nullable=False),
        sa.Column('total_amount', sa.Numeric(15, 2), nullable=False,
                  comment='Total trade value (quantity * price)'),
        
        # GST Calculation
        sa.Column('gst_type', sa.String(20), nullable=True,
                  comment='INTRA_STATE, INTER_STATE'),
        sa.Column('cgst_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('sgst_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('igst_rate', sa.Numeric(5, 2), nullable=True),
        
        # Terms (from negotiation)
        sa.Column('delivery_terms', sa.Text, nullable=True),
        sa.Column('payment_terms', sa.Text, nullable=True),
        sa.Column('quality_parameters', postgresql.JSONB, nullable=True),
        sa.Column('delivery_timeline', sa.String(100), nullable=True),
        sa.Column('delivery_city', sa.String(100), nullable=True),
        sa.Column('delivery_state', sa.String(100), nullable=True),
        
        # Contract Document
        sa.Column('contract_pdf_url', sa.Text, nullable=True,
                  comment='S3 URL to generated contract PDF'),
        sa.Column('contract_html', sa.Text, nullable=True,
                  comment='Rendered HTML before PDF conversion'),
        sa.Column('contract_hash', sa.String(64), nullable=True,
                  comment='SHA-256 hash for contract integrity'),
        sa.Column('contract_generated_at', sa.DateTime(timezone=True), nullable=True),
        
        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING_BRANCH_SELECTION',
                  comment='Trade status'),
        
        # Dates
        sa.Column('trade_date', sa.Date, nullable=False, server_default=sa.func.current_date()),
        sa.Column('expected_delivery_date', sa.Date, nullable=True),
        sa.Column('actual_delivery_date', sa.Date, nullable=True),
        
        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['negotiation_id'], ['negotiations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['buyer_partner_id'], ['business_partners.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['seller_partner_id'], ['business_partners.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['ship_to_branch_id'], ['partner_branches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['bill_to_branch_id'], ['partner_branches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ship_from_branch_id'], ['partner_branches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['commodity_id'], ['commodities.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['commodity_variety_id'], ['commodity_varieties.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Constraints
        sa.CheckConstraint(
            """status IN (
                'PENDING_BRANCH_SELECTION',
                'ACTIVE',
                'IN_TRANSIT',
                'DELIVERED',
                'COMPLETED',
                'CANCELLED',
                'DISPUTED'
            )""",
            name='ck_trades_status'
        ),
        sa.CheckConstraint("gst_type IN ('INTRA_STATE', 'INTER_STATE') OR gst_type IS NULL",
                           name='ck_trades_gst_type'),
        sa.CheckConstraint('quantity > 0', name='ck_trades_positive_quantity'),
        sa.CheckConstraint('price_per_unit > 0', name='ck_trades_positive_price'),
        sa.CheckConstraint('total_amount > 0', name='ck_trades_positive_total'),
    )
    
    # Indexes for trades
    op.create_index('ix_trades_trade_number', 'trades', ['trade_number'], unique=True)
    op.create_index('ix_trades_negotiation_id', 'trades', ['negotiation_id'])
    op.create_index('ix_trades_buyer_partner_id', 'trades', ['buyer_partner_id'])
    op.create_index('ix_trades_seller_partner_id', 'trades', ['seller_partner_id'])
    op.create_index('ix_trades_status', 'trades', ['status'])
    op.create_index('ix_trades_trade_date', 'trades', ['trade_date'])
    op.create_index('ix_trades_commodity_id', 'trades', ['commodity_id'])
    
    # ==================================================
    # 4. CREATE trade_signatures table
    # ==================================================
    op.create_table(
        'trade_signatures',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Signer
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Business partner who signed'),
        sa.Column('signed_by_user_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='User who performed the signature'),
        sa.Column('party_type', sa.String(20), nullable=False,
                  comment='BUYER or SELLER'),
        
        # Signature Tier
        sa.Column('signature_tier', sa.String(20), nullable=False,
                  comment='BASIC, AADHAAR_ESIGN, DSC'),
        
        # Signature Data
        sa.Column('signature_image_url', sa.String(500), nullable=True,
                  comment='For BASIC tier - uploaded/drawn signature'),
        
        # Aadhaar eSign Data
        sa.Column('aadhaar_reference_id', sa.String(100), nullable=True,
                  comment='NSDL/CDAC reference ID'),
        sa.Column('aadhaar_transaction_id', sa.String(100), nullable=True),
        
        # DSC Data
        sa.Column('dsc_signature_value', sa.Text, nullable=True,
                  comment='Encrypted digital signature value'),
        sa.Column('dsc_certificate_serial', sa.String(100), nullable=True),
        
        # Document Hash (what was signed)
        sa.Column('document_hash', sa.String(64), nullable=False,
                  comment='SHA-256 hash of contract PDF that was signed'),
        
        # Metadata
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('geolocation', sa.String(200), nullable=True),
        
        # Timestamp
        sa.Column('signed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['partner_id'], ['business_partners.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['signed_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        
        # Constraints
        sa.UniqueConstraint('trade_id', 'partner_id', name='uq_trade_signature_per_partner'),
        sa.CheckConstraint("signature_tier IN ('BASIC', 'AADHAAR_ESIGN', 'DSC')",
                           name='ck_trade_signatures_tier'),
        sa.CheckConstraint("party_type IN ('BUYER', 'SELLER')",
                           name='ck_trade_signatures_party_type'),
    )
    
    # Indexes for trade_signatures
    op.create_index('ix_trade_signatures_trade_id', 'trade_signatures', ['trade_id'])
    op.create_index('ix_trade_signatures_partner_id', 'trade_signatures', ['partner_id'])
    
    # ==================================================
    # 5. CREATE trade_amendments table
    # ==================================================
    op.create_table(
        'trade_amendments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Amendment Type
        sa.Column('amendment_type', sa.String(50), nullable=False,
                  comment='ADDRESS_CHANGE, QUANTITY_CHANGE, PRICE_CHANGE, DELIVERY_DATE_CHANGE'),
        
        # What changed
        sa.Column('field_name', sa.String(100), nullable=False,
                  comment='Field that was amended (e.g., ship_to_address)'),
        sa.Column('old_value', postgresql.JSONB, nullable=False,
                  comment='Original value before amendment'),
        sa.Column('new_value', postgresql.JSONB, nullable=False,
                  comment='New value after amendment'),
        
        # Reason
        sa.Column('reason', sa.Text, nullable=True,
                  comment='Reason for amendment'),
        
        # Approval Workflow
        sa.Column('requires_counterparty_approval', sa.Boolean, nullable=False, server_default='true',
                  comment='Whether counterparty approval is needed'),
        sa.Column('requested_by_party', sa.String(20), nullable=False,
                  comment='BUYER or SELLER'),
        sa.Column('requested_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Status
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING',
                  comment='PENDING, APPROVED, REJECTED'),
        
        # Approval
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        
        # Constraints
        sa.CheckConstraint(
            "amendment_type IN ('ADDRESS_CHANGE', 'QUANTITY_CHANGE', 'PRICE_CHANGE', 'DELIVERY_DATE_CHANGE')",
            name='ck_trade_amendments_type'
        ),
        sa.CheckConstraint("requested_by_party IN ('BUYER', 'SELLER')",
                           name='ck_trade_amendments_party'),
        sa.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED')",
                           name='ck_trade_amendments_status'),
    )
    
    # Indexes for trade_amendments
    op.create_index('ix_trade_amendments_trade_id', 'trade_amendments', ['trade_id'])
    op.create_index('ix_trade_amendments_status', 'trade_amendments', ['status'])
    
    # ==================================================
    # 6. Update negotiations table - add accepted_at column
    # ==================================================
    op.add_column('negotiations',
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Timestamp when negotiation was accepted')
    )


def downgrade() -> None:
    """
    Rollback Trade Engine tables in reverse dependency order
    """
    # Drop tables
    op.drop_table('trade_amendments')
    op.drop_table('trade_signatures')
    op.drop_table('trades')
    op.drop_table('partner_branches')
    
    # Remove negotiation column
    op.drop_column('negotiations', 'accepted_at')
    
    # Remove business_partners columns
    op.drop_constraint('fk_business_partners_signature_uploaded_by', 'business_partners', type_='foreignkey')
    op.drop_constraint('ck_business_partners_signature_tier', 'business_partners', type_='check')
    op.drop_column('business_partners', 'dsc_certificate_url')
    op.drop_column('business_partners', 'dsc_certificate_serial')
    op.drop_column('business_partners', 'aadhaar_esign_enabled')
    op.drop_column('business_partners', 'aadhaar_number_encrypted')
    op.drop_column('business_partners', 'signature_uploaded_by')
    op.drop_column('business_partners', 'signature_uploaded_at')
    op.drop_column('business_partners', 'signature_tier')
    op.drop_column('business_partners', 'digital_signature_url')
