"""
Comprehensive Negotiation Engine Test

Tests:
1. Database schema verification
2. Data isolation (external users)
3. Admin monitoring access
4. Service layer business logic
5. End-to-end negotiation flow
"""

import asyncio
import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.async_session import get_db
from backend.modules.trade_desk.models.negotiation import Negotiation
from backend.modules.trade_desk.models.negotiation_offer import NegotiationOffer
from backend.modules.trade_desk.models.negotiation_message import NegotiationMessage
from backend.modules.trade_desk.services.negotiation_service import NegotiationService
from backend.core.errors.exceptions import AuthorizationException, NotFoundException


# ============================================================================
# TEST 1: Database Schema Verification
# ============================================================================

async def test_database_schema():
    """Verify all negotiation tables exist with correct structure."""
    print("\n" + "="*80)
    print("TEST 1: Database Schema Verification")
    print("="*80)
    
    async for db in get_db():
        # Check tables exist
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%negotiation%'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        assert 'negotiations' in tables, "negotiations table missing"
        assert 'negotiation_offers' in tables, "negotiation_offers table missing"
        assert 'negotiation_messages' in tables, "negotiation_messages table missing"
        
        print("✅ All 3 tables exist:")
        for table in tables:
            print(f"   - {table}")
        
        # Check negotiations table columns
        result = await db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'negotiations'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        
        column_names = [col[0] for col in columns]
        assert 'id' in column_names
        assert 'requirement_id' in column_names
        assert 'availability_id' in column_names
        assert 'buyer_partner_id' in column_names
        assert 'seller_partner_id' in column_names
        assert 'status' in column_names
        assert 'current_round' in column_names
        
        print(f"✅ negotiations table has {len(columns)} columns")
        
        # Check foreign keys
        result = await db.execute(text("""
            SELECT 
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = 'negotiations'
            AND tc.constraint_type = 'FOREIGN KEY'
        """))
        fks = result.fetchall()
        
        fk_tables = [fk[2] for fk in fks]
        assert 'business_partners' in fk_tables, "Missing FK to business_partners"
        assert 'requirements' in fk_tables, "Missing FK to requirements"
        assert 'availabilities' in fk_tables, "Missing FK to availabilities"
        assert 'trades' not in fk_tables, "Should NOT have FK to trades yet"
        
        print(f"✅ Foreign keys correct (no trades FK)")
        
        break  # Only need one session
    
    print("✅ TEST 1 PASSED: Schema verified")
    return True


# ============================================================================
# TEST 2: Data Isolation (External Users)
# ============================================================================

async def test_data_isolation():
    """Verify external users can only see their own negotiations."""
    print("\n" + "="*80)
    print("TEST 2: Data Isolation (External Users)")
    print("="*80)
    
    # Create test partners
    buyer1_id = uuid4()
    buyer2_id = uuid4()
    seller1_id = uuid4()
    
    async for db in get_db():
        service = NegotiationService(db)
        
        # Create negotiations
        req1_id = uuid4()
        avail1_id = uuid4()
        
        req2_id = uuid4()
        avail2_id = uuid4()
        
        # Negotiation 1: Buyer1 <-> Seller1
        neg1 = Negotiation(
            id=uuid4(),
            requirement_id=req1_id,
            availability_id=avail1_id,
            buyer_partner_id=buyer1_id,
            seller_partner_id=seller1_id,
            status="IN_PROGRESS",
            current_round=1,
            last_activity_at=datetime.utcnow()
        )
        db.add(neg1)
        
        # Negotiation 2: Buyer2 <-> Seller1
        neg2 = Negotiation(
            id=uuid4(),
            requirement_id=req2_id,
            availability_id=avail2_id,
            buyer_partner_id=buyer2_id,
            seller_partner_id=seller1_id,
            status="IN_PROGRESS",
            current_round=1,
            last_activity_at=datetime.utcnow()
        )
        db.add(neg2)
        
        await db.commit()
        await db.refresh(neg1)
        await db.refresh(neg2)
        
        print(f"Created 2 test negotiations:")
        print(f"  Neg1: Buyer1 <-> Seller1")
        print(f"  Neg2: Buyer2 <-> Seller1")
        
        # Test 1: Buyer1 queries - should see only Neg1
        buyer1_negotiations = await service.get_user_negotiations(buyer1_id)
        assert len(buyer1_negotiations) == 1, "Buyer1 should see only 1 negotiation"
        assert buyer1_negotiations[0].id == neg1.id
        print(f"✅ Buyer1 sees only their negotiation (1 out of 2)")
        
        # Test 2: Buyer2 queries - should see only Neg2
        buyer2_negotiations = await service.get_user_negotiations(buyer2_id)
        assert len(buyer2_negotiations) == 1, "Buyer2 should see only 1 negotiation"
        assert buyer2_negotiations[0].id == neg2.id
        print(f"✅ Buyer2 sees only their negotiation (1 out of 2)")
        
        # Test 3: Seller1 queries - should see BOTH (they're seller in both)
        seller1_negotiations = await service.get_user_negotiations(seller1_id)
        assert len(seller1_negotiations) == 2, "Seller1 should see 2 negotiations"
        print(f"✅ Seller1 sees both negotiations (they're party to both)")
        
        # Test 4: Buyer1 tries to access Buyer2's negotiation
        try:
            await service.get_negotiation_by_id(neg2.id, buyer1_id)
            assert False, "Should have raised AuthorizationException"
        except AuthorizationException as e:
            print(f"✅ Authorization blocked cross-user access: {str(e)[:50]}...")
        
        # Test 5: Buyer2 can access their own negotiation
        retrieved = await service.get_negotiation_by_id(neg2.id, buyer2_id)
        assert retrieved.id == neg2.id
        print(f"✅ Users can access their own negotiations")
        
        # Cleanup
        await db.delete(neg1)
        await db.delete(neg2)
        await db.commit()
        
        break
    
    print("✅ TEST 2 PASSED: Data isolation working")
    return True


# ============================================================================
# TEST 3: Admin Monitoring Access
# ============================================================================

async def test_admin_monitoring():
    """Verify admin can see all negotiations without authorization."""
    print("\n" + "="*80)
    print("TEST 3: Admin Monitoring Access")
    print("="*80)
    
    buyer1_id = uuid4()
    buyer2_id = uuid4()
    seller1_id = uuid4()
    
    async for db in get_db():
        service = NegotiationService(db)
        
        # Create 3 negotiations across different users
        negotiations = []
        for i in range(3):
            neg = Negotiation(
                id=uuid4(),
                requirement_id=uuid4(),
                availability_id=uuid4(),
                buyer_partner_id=buyer1_id if i < 2 else buyer2_id,
                seller_partner_id=seller1_id,
                status="IN_PROGRESS",
                current_round=1,
                last_activity_at=datetime.utcnow()
            )
            db.add(neg)
            negotiations.append(neg)
        
        await db.commit()
        
        print(f"Created 3 negotiations (2 for Buyer1, 1 for Buyer2)")
        
        # Test 1: Admin can see ALL negotiations
        all_negotiations = await service.admin_get_all_negotiations()
        assert len(all_negotiations) >= 3, "Admin should see at least 3 negotiations"
        print(f"✅ Admin sees ALL negotiations: {len(all_negotiations)}")
        
        # Test 2: Admin can access any specific negotiation
        for neg in negotiations:
            retrieved = await service.admin_get_negotiation_by_id(neg.id)
            assert retrieved.id == neg.id
        print(f"✅ Admin can access any negotiation by ID")
        
        # Test 3: Verify admin method doesn't filter by user
        # Regular user sees only their own
        buyer1_user_view = await service.get_user_negotiations(buyer1_id)
        assert len(buyer1_user_view) == 2, "Buyer1 should see 2"
        
        # Admin sees all (no user filter)
        admin_view = await service.admin_get_all_negotiations(status="IN_PROGRESS")
        assert len(admin_view) >= 3, "Admin should see all IN_PROGRESS"
        print(f"✅ Admin view: {len(admin_view)} vs User view: {len(buyer1_user_view)}")
        
        # Cleanup
        for neg in negotiations:
            await db.delete(neg)
        await db.commit()
        
        break
    
    print("✅ TEST 3 PASSED: Admin monitoring working")
    return True


# ============================================================================
# TEST 4: Service Layer Business Logic
# ============================================================================

async def test_service_business_logic():
    """Test negotiation lifecycle methods."""
    print("\n" + "="*80)
    print("TEST 4: Service Layer Business Logic")
    print("="*80)
    
    buyer_id = uuid4()
    seller_id = uuid4()
    req_id = uuid4()
    avail_id = uuid4()
    
    async for db in get_db():
        service = NegotiationService(db)
        
        # Create negotiation
        negotiation = await service.start_negotiation(
            requirement_id=req_id,
            availability_id=avail_id,
            buyer_partner_id=buyer_id,
            seller_partner_id=seller_id,
            initial_price=Decimal("7000.00"),
            quantity=Decimal("50.000"),
            delivery_terms={"location": "Surat", "days": 7},
            payment_terms={"advance": 30, "days": 15},
            user_partner_id=buyer_id  # Buyer starting negotiation
        )
        
        print(f"✅ Created negotiation: {negotiation.id}")
        assert negotiation.status == "IN_PROGRESS"
        assert negotiation.current_round == 1
        assert len(negotiation.offers) == 1  # Initial offer
        
        # Make counter-offer (seller)
        counter_offer = await service.make_offer(
            negotiation_id=negotiation.id,
            user_partner_id=seller_id,
            price_per_unit=Decimal("7200.00"),
            quantity=Decimal("50.000"),
            message="Counter offer - premium quality",
            ai_generated=False
        )
        
        print(f"✅ Seller made counter-offer: Round {counter_offer.round_number}")
        assert counter_offer.round_number == 2
        assert counter_offer.offered_by == "SELLER"
        
        # Refresh and check
        await db.refresh(negotiation)
        assert negotiation.current_round == 2
        
        # Send message
        message = await service.send_message(
            negotiation_id=negotiation.id,
            user_partner_id=buyer_id,
            message="Let me check with my team",
            message_type="CHAT"
        )
        
        print(f"✅ Buyer sent message: {message.message[:30]}...")
        assert message.sender == "BUYER"
        
        # Get messages
        messages = await service.get_negotiation_messages(
            negotiation_id=negotiation.id,
            user_partner_id=buyer_id
        )
        
        assert len(messages) >= 1
        print(f"✅ Retrieved {len(messages)} messages")
        
        # Accept offer (buyer accepts seller's counter)
        accepted = await service.accept_offer(
            negotiation_id=negotiation.id,
            offer_id=counter_offer.id,
            user_partner_id=buyer_id
        )
        
        print(f"✅ Buyer accepted offer")
        assert accepted.status == "ACCEPTED"
        
        # Check negotiation status
        await db.refresh(negotiation)
        assert negotiation.status == "COMPLETED"
        assert negotiation.closed_at is not None
        print(f"✅ Negotiation completed and closed")
        
        # Cleanup
        await db.delete(negotiation)
        await db.commit()
        
        break
    
    print("✅ TEST 4 PASSED: Business logic working")
    return True


# ============================================================================
# RUN ALL TESTS
# ============================================================================

async def run_all_tests():
    """Execute all tests."""
    print("\n" + "="*80)
    print("NEGOTIATION ENGINE - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    results = []
    
    try:
        result = await test_database_schema()
        results.append(("Database Schema", result))
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results.append(("Database Schema", False))
    
    try:
        result = await test_data_isolation()
        results.append(("Data Isolation", result))
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results.append(("Data Isolation", False))
    
    try:
        result = await test_admin_monitoring()
        results.append(("Admin Monitoring", result))
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results.append(("Admin Monitoring", False))
    
    try:
        result = await test_service_business_logic()
        results.append(("Service Business Logic", result))
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results.append(("Service Business Logic", False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - NEGOTIATION ENGINE READY!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
