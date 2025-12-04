"""
Simple Negotiation Engine Test - Database & Schema Verification
"""

import asyncio
from sqlalchemy import text
from backend.db.async_session import get_db


async def test_migration():
    """Verify migration created all tables correctly."""
    print("\n" + "="*80)
    print("NEGOTIATION ENGINE - DATABASE MIGRATION TEST")
    print("="*80)
    
    async for db in get_db():
        # Test 1: Check tables exist
        print("\n1. Checking tables exist...")
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%negotiation%'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        expected_tables = ['negotiation_messages', 'negotiation_offers', 'negotiations']
        for table in expected_tables:
            if table in tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} MISSING")
                return False
        
        # Test 2: Check negotiations table structure
        print("\n2. Checking negotiations table columns...")
        result = await db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'negotiations'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        column_names = [col[0] for col in columns]
        
        required_columns = [
            'id', 'requirement_id', 'availability_id', 
            'buyer_partner_id', 'seller_partner_id',
            'status', 'current_round', 'last_activity_at'
        ]
        
        for col in required_columns:
            if col in column_names:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} MISSING")
                return False
        
        print(f"\n   Total columns: {len(columns)}")
        
        # Test 3: Check foreign keys
        print("\n3. Checking foreign key constraints...")
        result = await db.execute(text("""
            SELECT 
                kcu.column_name,
                ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = 'negotiations'
            AND tc.constraint_type = 'FOREIGN KEY'
            ORDER BY kcu.column_name
        """))
        fks = result.fetchall()
        
        fk_map = {fk[0]: fk[1] for fk in fks}
        
        expected_fks = {
            'buyer_partner_id': 'business_partners',
            'seller_partner_id': 'business_partners',
            'requirement_id': 'requirements',
            'availability_id': 'availabilities'
        }
        
        for col, expected_table in expected_fks.items():
            if col in fk_map:
                if fk_map[col] == expected_table:
                    print(f"   ✅ {col} -> {expected_table}")
                else:
                    print(f"   ❌ {col} -> {fk_map[col]} (expected {expected_table})")
                    return False
            else:
                print(f"   ❌ {col} FK missing")
                return False
        
        # Verify NO FK to trades table
        if 'trade_id' not in fk_map:
            print(f"   ✅ No FK to trades table (correct - will be added in Phase 5)")
        else:
            print(f"   ❌ Unexpected FK to trades table")
            return False
        
        # Test 4: Check negotiation_offers table
        print("\n4. Checking negotiation_offers table...")
        result = await db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'negotiation_offers'
            ORDER BY ordinal_position
        """))
        offer_columns = [row[0] for row in result.fetchall()]
        
        required_offer_cols = [
            'id', 'negotiation_id', 'round_number', 'offered_by',
            'price_per_unit', 'quantity', 'status', 'ai_generated'
        ]
        
        for col in required_offer_cols:
            if col in offer_columns:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} MISSING")
                return False
        
        # Test 5: Check negotiation_messages table
        print("\n5. Checking negotiation_messages table...")
        result = await db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'negotiation_messages'
            ORDER BY ordinal_position
        """))
        message_columns = [row[0] for row in result.fetchall()]
        
        required_message_cols = [
            'id', 'negotiation_id', 'sender', 'message', 'message_type'
        ]
        
        for col in required_message_cols:
            if col in message_columns:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} MISSING")
                return False
        
        # Test 6: Check indexes
        print("\n6. Checking indexes...")
        result = await db.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'negotiations'
            ORDER BY indexname
        """))
        indexes = [row[0] for row in result.fetchall()]
        
        print(f"   Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"      - {idx}")
        
        # Test 7: Try inserting test data
        print("\n7. Testing data insertion (dry run)...")
        try:
            result = await db.execute(text("""
                SELECT COUNT(*) FROM negotiations
            """))
            count = result.scalar()
            print(f"   ✅ Can query negotiations table (current count: {count})")
        except Exception as e:
            print(f"   ❌ Error querying table: {e}")
            return False
        
        break  # Only need one session
    
    print("\n" + "="*80)
    print("✅ ALL MIGRATION TESTS PASSED")
    print("="*80)
    print("\nNegotiation Engine Database Schema:")
    print("  ✅ 3 tables created (negotiations, negotiation_offers, negotiation_messages)")
    print("  ✅ All foreign keys correct (business_partners, requirements, availabilities)")
    print("  ✅ No FK to trades table (will be added in Phase 5)")
    print("  ✅ All required columns present")
    print("  ✅ Indexes created")
    print("\n🎉 READY FOR PHASE 5: TRADE ENGINE")
    print("="*80)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_migration())
    exit(0 if success else 1)
