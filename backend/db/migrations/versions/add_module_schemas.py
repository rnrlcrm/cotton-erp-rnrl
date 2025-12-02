"""
Add module-specific database schemas

Revision ID: add_module_schemas
Revises: <previous_revision>
Create Date: 2025-12-02

Organizes database into module-specific schemas for better separation.

Schemas:
- partners_schema → Business partners, KYC, onboarding
- trading_schema → Requirements, availabilities, matches
- risk_schema → Risk assessments, alerts
- payments_schema → Invoices, payments, settlements
- settings_schema → Commodities, locations, organizations
- notifications_schema → Email, SMS, WhatsApp logs
- audit_schema → Audit trail, event log
"""

from alembic import op
import sqlalchemy as sa


# Module schemas to create
MODULE_SCHEMAS = [
    "partners_schema",
    "trading_schema",
    "risk_schema",
    "payments_schema",
    "settings_schema",
    "notifications_schema",
    "audit_schema",
    "analytics_schema",
]


def upgrade() -> None:
    """Create module-specific schemas."""
    
    # Create schemas
    for schema in MODULE_SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        print(f"✅ Created schema: {schema}")
    
    # Grant permissions (adjust role name as needed)
    for schema in MODULE_SCHEMAS:
        op.execute(f"GRANT ALL ON SCHEMA {schema} TO commodity_user")
        op.execute(f"GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO commodity_user")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON TABLES TO commodity_user")
    
    print("\n✅ Module schemas created successfully!")
    print("\nNext steps:")
    print("1. Move existing tables to appropriate schemas")
    print("2. Update SQLAlchemy models with schema='schema_name'")
    print("3. Update all queries to use schema-qualified table names")
    print("\nExample:")
    print("  class BusinessPartner(Base):")
    print("      __tablename__ = 'business_partners'")
    print("      __table_args__ = {'schema': 'partners_schema'}")


def downgrade() -> None:
    """Drop module-specific schemas."""
    
    # Drop schemas (CASCADE will drop all tables)
    for schema in reversed(MODULE_SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        print(f"❌ Dropped schema: {schema}")
    
    print("\n⚠️  All module schemas and their tables have been removed!")
