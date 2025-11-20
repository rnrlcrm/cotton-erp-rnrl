"""create organization settings

Revision ID: 20251120_1400
Revises: eaf12a4e04a0
Create Date: 2025-11-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251120_1400'
down_revision = 'eaf12a4e04a0'
branch_labels = None
depends_on = None


def upgrade():
    # Create organizations table (extended version)
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('legal_name', sa.String(255), nullable=True),
        sa.Column('type', sa.String(64), nullable=True),
        sa.Column('CIN', sa.String(21), nullable=True),
        sa.Column('PAN', sa.String(10), nullable=True),
        sa.Column('base_currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(128), nullable=True),
        sa.Column('state', sa.String(128), nullable=True),
        sa.Column('pincode', sa.String(16), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(32), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('threshold_limit', sa.Integer(), nullable=True),
        sa.Column('einvoice_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_block_if_einvoice_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('fx_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('logo_url', sa.String(255), nullable=True),
        sa.Column('theme_color', sa.String(64), nullable=True),
        sa.Column('invoice_footer', sa.String(1024), nullable=True),
        sa.Column('digital_signature_url', sa.String(255), nullable=True),
        sa.Column('tds_rate', sa.Integer(), nullable=True),
        sa.Column('tcs_rate', sa.Integer(), nullable=True),
        sa.Column('audit_firm_name', sa.String(255), nullable=True),
        sa.Column('audit_firm_email', sa.String(255), nullable=True),
        sa.Column('audit_firm_phone', sa.String(32), nullable=True),
        sa.Column('gst_audit_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_invoice', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_contract_number', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('extra_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'])
    op.create_index('ix_organizations_is_active', 'organizations', ['is_active'])

    # Create organization_gst table
    op.create_table(
        'organization_gst',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('gstin', sa.String(15), nullable=False, unique=True),
        sa.Column('legal_name', sa.String(255), nullable=True),
        sa.Column('address', sa.String(255), nullable=True),
        sa.Column('state', sa.String(128), nullable=True),
        sa.Column('branch_code', sa.String(32), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_organization_gst_gstin', 'organization_gst', ['gstin'])
    op.create_index('ix_organization_gst_organization_id', 'organization_gst', ['organization_id'])
    op.create_index('ix_organization_gst_is_primary', 'organization_gst', ['is_primary'])

    # Create organization_bank_accounts table
    op.create_table(
        'organization_bank_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('account_holder', sa.String(255), nullable=False),
        sa.Column('bank_name', sa.String(255), nullable=False),
        sa.Column('account_number', sa.String(64), nullable=False),
        sa.Column('ifsc', sa.String(11), nullable=True),
        sa.Column('branch', sa.String(255), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_organization_bank_accounts_organization_id', 'organization_bank_accounts', ['organization_id'])
    op.create_index('ix_organization_bank_accounts_is_default', 'organization_bank_accounts', ['is_default'])

    # Create organization_financial_years table
    op.create_table(
        'organization_financial_years',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allow_year_split', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_organization_financial_years_organization_id', 'organization_financial_years', ['organization_id'])
    op.create_index('ix_organization_financial_years_start_date', 'organization_financial_years', ['start_date'])
    op.create_index('ix_organization_financial_years_end_date', 'organization_financial_years', ['end_date'])
    op.create_index('ix_organization_financial_years_is_active', 'organization_financial_years', ['is_active'])

    # Create organization_document_series table
    op.create_table(
        'organization_document_series',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('financial_year_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization_financial_years.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_type', sa.String(64), nullable=False),
        sa.Column('prefix', sa.String(32), nullable=True),
        sa.Column('current_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('reset_annually', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('extra_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('organization_id', 'document_type', 'financial_year_id', name='uq_org_doc_series'),
    )
    op.create_index('ix_organization_document_series_organization_id', 'organization_document_series', ['organization_id'])
    op.create_index('ix_organization_document_series_financial_year_id', 'organization_document_series', ['financial_year_id'])
    op.create_index('ix_organization_document_series_document_type', 'organization_document_series', ['document_type'])


def downgrade():
    op.drop_index('ix_organization_document_series_document_type', table_name='organization_document_series')
    op.drop_index('ix_organization_document_series_financial_year_id', table_name='organization_document_series')
    op.drop_index('ix_organization_document_series_organization_id', table_name='organization_document_series')
    op.drop_table('organization_document_series')

    op.drop_index('ix_organization_financial_years_is_active', table_name='organization_financial_years')
    op.drop_index('ix_organization_financial_years_end_date', table_name='organization_financial_years')
    op.drop_index('ix_organization_financial_years_start_date', table_name='organization_financial_years')
    op.drop_index('ix_organization_financial_years_organization_id', table_name='organization_financial_years')
    op.drop_table('organization_financial_years')

    op.drop_index('ix_organization_bank_accounts_is_default', table_name='organization_bank_accounts')
    op.drop_index('ix_organization_bank_accounts_organization_id', table_name='organization_bank_accounts')
    op.drop_table('organization_bank_accounts')

    op.drop_index('ix_organization_gst_is_primary', table_name='organization_gst')
    op.drop_index('ix_organization_gst_organization_id', table_name='organization_gst')
    op.drop_index('ix_organization_gst_gstin', table_name='organization_gst')
    op.drop_table('organization_gst')

    op.drop_index('ix_organizations_is_active', table_name='organizations')
    op.drop_index('ix_organizations_name', table_name='organizations')
    op.drop_table('organizations')


# Do not assume or invent anything. Only implement EXACTLY what is written here and in the models.
