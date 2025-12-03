#!/usr/bin/env python3
"""
Direct migration script to add international commodity fields
Bypasses Alembic's slow import chain
"""
import os
import psycopg
from psycopg import sql

# Database connection (psycopg format, not SQLAlchemy format)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/cotton_dev"

def run_migration():
    """Execute the international commodity fields migration"""
    
    # Connect to database
    conn = psycopg.connect(DATABASE_URL)
    conn.autocommit = False
    
    try:
        with conn.cursor() as cur:
            print("🚀 Starting international commodity migration...")
            
            # ============================================================
            # COMMODITIES TABLE - Add 25 international fields
            # ============================================================
            print("📦 Adding international fields to commodities table...")
            
            commodity_fields = [
                # Currency & Pricing
                ("default_currency", "VARCHAR(3)"),
                ("alternate_currencies", "TEXT"),
                ("price_unit", "VARCHAR(50)"),
                ("pricing_basis", "VARCHAR(100)"),
                
                # Tax & Compliance
                ("customs_tariff_code", "VARCHAR(20)"),
                ("export_tariff_code", "VARCHAR(20)"),
                ("tax_classification", "VARCHAR(100)"),
                
                # International Standards
                ("quality_standard", "VARCHAR(100)"),
                ("certification_required", "TEXT"),
                ("international_grade", "VARCHAR(50)"),
                
                # Geography
                ("origin_country", "VARCHAR(100)"),
                ("destination_restrictions", "TEXT"),
                ("free_trade_agreements", "TEXT"),
                
                # Trading Infrastructure
                ("commodity_exchange", "VARCHAR(100)"),
                ("exchange_symbol", "VARCHAR(20)"),
                ("trading_hours", "VARCHAR(100)"),
                
                # Compliance & Documentation
                ("phytosanitary_required", "BOOLEAN DEFAULT FALSE"),
                ("fumigation_required", "BOOLEAN DEFAULT FALSE"),
                ("inspection_agency", "VARCHAR(100)"),
                ("document_requirements", "TEXT"),
                
                # Seasonal & Market
                ("harvest_season", "VARCHAR(100)"),
                ("peak_trading_months", "VARCHAR(100)"),
                ("price_volatility", "VARCHAR(20)"),
                
                # Contract Terms
                ("min_contract_quantity", "NUMERIC(15,3)"),
                ("max_contract_quantity", "NUMERIC(15,3)"),
                ("standard_lot_size", "NUMERIC(15,3)"),
            ]
            
            for field_name, field_type in commodity_fields:
                try:
                    cur.execute(
                        sql.SQL("ALTER TABLE commodities ADD COLUMN IF NOT EXISTS {} {}").format(
                            sql.Identifier(field_name),
                            sql.SQL(field_type)
                        )
                    )
                    print(f"  ✅ Added: {field_name}")
                except Exception as e:
                    print(f"  ⚠️  Warning for {field_name}: {e}")
            
            # ============================================================
            # PAYMENT_TERMS TABLE - Add 8 LC/International fields
            # ============================================================
            print("\n💳 Adding LC fields to payment_terms table...")
            
            payment_fields = [
                ("lc_type", "VARCHAR(50)"),
                ("lc_tenure_days", "INTEGER"),
                ("usance_days", "INTEGER"),
                ("currency_support", "TEXT"),
                ("bank_charges_borne_by", "VARCHAR(20)"),
                ("reimbursement_bank", "VARCHAR(200)"),
                ("advising_bank_required", "BOOLEAN DEFAULT FALSE"),
                ("swift_charges", "VARCHAR(50)"),
            ]
            
            for field_name, field_type in payment_fields:
                try:
                    cur.execute(
                        sql.SQL("ALTER TABLE payment_terms ADD COLUMN IF NOT EXISTS {} {}").format(
                            sql.Identifier(field_name),
                            sql.SQL(field_type)
                        )
                    )
                    print(f"  ✅ Added: {field_name}")
                except Exception as e:
                    print(f"  ⚠️  Warning for {field_name}: {e}")
            
            # ============================================================
            # COMMISSION_STRUCTURES TABLE - Add 5 multi-currency fields
            # ============================================================
            print("\n💰 Adding multi-currency fields to commission_structures table...")
            
            commission_fields = [
                ("currency_code", "VARCHAR(3)"),
                ("country_specific_rates", "JSONB"),
                ("forex_adjustment_allowed", "BOOLEAN DEFAULT FALSE"),
                ("min_commission_amount", "NUMERIC(15,2)"),
                ("tier_rates", "JSONB"),
            ]
            
            for field_name, field_type in commission_fields:
                try:
                    cur.execute(
                        sql.SQL("ALTER TABLE commission_structures ADD COLUMN IF NOT EXISTS {} {}").format(
                            sql.Identifier(field_name),
                            sql.SQL(field_type)
                        )
                    )
                    print(f"  ✅ Added: {field_name}")
                except Exception as e:
                    print(f"  ⚠️  Warning for {field_name}: {e}")
            
            # ============================================================
            # Create indexes for performance
            # ============================================================
            print("\n🔍 Creating indexes...")
            
            indexes = [
                ("idx_commodities_default_currency", "commodities", "default_currency"),
                ("idx_commodities_origin_country", "commodities", "origin_country"),
                ("idx_commodities_commodity_exchange", "commodities", "commodity_exchange"),
                ("idx_payment_terms_lc_type", "payment_terms", "lc_type"),
                ("idx_commission_currency", "commission_structures", "currency_code"),
            ]
            
            for idx_name, table_name, column_name in indexes:
                try:
                    cur.execute(
                        sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} ({})").format(
                            sql.Identifier(idx_name),
                            sql.Identifier(table_name),
                            sql.Identifier(column_name)
                        )
                    )
                    print(f"  ✅ Index: {idx_name}")
                except Exception as e:
                    print(f"  ⚠️  Warning for {idx_name}: {e}")
            
            # ============================================================
            # Update Alembic version
            # ============================================================
            print("\n📝 Updating Alembic version...")
            cur.execute(
                "UPDATE alembic_version SET version_num = '20251204110000'"
            )
            print("  ✅ Version updated to: 20251204110000")
            
            # Commit all changes
            conn.commit()
            print("\n✅ Migration completed successfully!")
            
            # Verify changes
            print("\n📊 Verification:")
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'commodities' 
                AND column_name IN ('default_currency', 'origin_country', 'commodity_exchange')
            """)
            found_columns = [row[0] for row in cur.fetchall()]
            print(f"  Sample new commodity fields: {found_columns}")
            
            cur.execute("SELECT version_num FROM alembic_version")
            version = cur.fetchone()[0]
            print(f"  Current Alembic version: {version}")
            
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
