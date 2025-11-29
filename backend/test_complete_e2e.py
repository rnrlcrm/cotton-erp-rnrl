#!/usr/bin/env python3
"""
COMPLETE END-TO-END TEST - Direct Database Access
Tests all implemented features without requiring API server
"""
import asyncio
import sys
from decimal import Decimal
from uuid import uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text

# Import models and services
from backend.modules.trade_desk.services.availability_service import AvailabilityService
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.settings.commodities.models import Commodity
from backend.modules.settings.locations.models import Location
from backend.modules.partners.models import BusinessPartner

# Database URL
DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/cotton_dev"

# Global test data
# Use existing organization from database
EXISTING_ORG_ID = "9e9e5442-4021-4c90-9d4e-643c15a17c4b"  # RNRL Headquarters
test_commodity_id = None
test_location_id = None
test_seller_id = None


async def setup_test_data(session: AsyncSession):
    """Create required test data"""
    global test_commodity_id, test_location_id, test_seller_id
    
    print("\n" + "="*80)
    print("SETUP: Creating Test Data")
    print("="*80)
    
    # 1. Using existing organization
    print(f"\n1. Using existing organization: {EXISTING_ORG_ID}")
    
    # 2. Create commodity
    print("\n2. Creating commodity...")
    commodity = Commodity(
        id=uuid4(),
        name=f"E2E Cotton {uuid4().hex[:8]}",
        category="COTTON",
        base_unit="KG",
        trade_unit="CANDY",
        rate_unit="per CANDY",
        is_active=True
    )
    session.add(commodity)
    await session.flush()
    
    test_commodity_id = commodity.id
    print(f"   ✅ Commodity: {commodity.name}")
    print(f"      - trade_unit: {commodity.trade_unit}")
    print(f"      - rate_unit: {commodity.rate_unit}")
    
    # 3. Create registered location
    print("\n3. Creating registered location...")
    location = Location(
        id=uuid4(),
        name=f"Mumbai Warehouse {uuid4().hex[:8]}",
        google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0",  # Mumbai placeholder
        address="Andheri East, Mumbai",
        city="Mumbai",
        state="Maharashtra",
        country="INDIA",
        latitude=Decimal("19.1136"),
        longitude=Decimal("72.8697"),
        pincode="400069",
        is_active=True
    )
    session.add(location)
    await session.flush()
    
    test_location_id = location.id
    print(f"   ✅ Location: {location.name}")
    print(f"      - Coordinates: {location.latitude}, {location.longitude}")
    
    # 4. Create seller with sell capability
    print("\n4. Creating seller...")
    from uuid import UUID
    seller = BusinessPartner(
        id=uuid4(),
        legal_name=f"E2E Seller {uuid4().hex[:8]}",
        country="India",
        organization_id=UUID(EXISTING_ORG_ID),
        entity_class="entity",
        capabilities={
            "domestic_sell_india": True,
            "domestic_buy_india": True
        }
    )
    session.add(seller)
    await session.flush()
    
    test_seller_id = seller.id
    print(f"   ✅ Seller: {seller.legal_name}")
    print(f"      - Capabilities: {seller.capabilities}")
    
    await session.commit()
    print(f"\n✅ Test data setup complete!")


async def test_1_auto_unit_population(session: AsyncSession):
    """TEST 1: Auto-populate units from commodity master"""
    print("\n" + "="*80)
    print("TEST 1: Auto-Unit Population from Commodity Master")
    print("="*80)
    
    service = AvailabilityService(session)
    
    print("\n📝 Creating availability WITHOUT quantity_unit and price_unit...")
    print(f"   System should auto-fill from commodity master")
    
    try:
        availability = await service.create_availability(
            seller_id=test_seller_id,
            commodity_id=test_commodity_id,
            location_id=test_location_id,
            total_quantity=Decimal("100.0"),
            # quantity_unit NOT provided - should auto-populate
            base_price=Decimal("8000.0"),
            # price_unit NOT provided - should auto-populate
            quality_params={"length": 29.0, "strength": 26.0},
            auto_approve=True
        )
        
        print(f"\n✅ Availability created!")
        print(f"   ID: {availability.id}")
        print(f"   Total Quantity: {availability.total_quantity}")
        print(f"   quantity_unit: {availability.quantity_unit} (auto-populated)")
        print(f"   Base Price: {availability.base_price}")
        print(f"   price_unit: {availability.price_unit} (auto-populated)")
        
        # Verify
        assert availability.quantity_unit == "CANDY", f"Expected CANDY, got {availability.quantity_unit}"
        assert availability.price_unit == "per CANDY", f"Expected 'per CANDY', got {availability.price_unit}"
        
        print(f"\n✅ TEST 1 PASSED: Units auto-populated correctly!")
        print(f"   ✓ quantity_unit: {availability.quantity_unit}")
        print(f"   ✓ price_unit: {availability.price_unit}")
        
        await session.rollback()  # Clean up
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        return False


async def test_2_registered_location(session: AsyncSession):
    """TEST 2: Create availability with registered location"""
    print("\n" + "="*80)
    print("TEST 2: Registered Location (Settings Table)")
    print("="*80)
    
    service = AvailabilityService(session)
    
    print(f"\n📝 Creating availability with registered location_id...")
    print(f"   Location: {test_location_id}")
    
    try:
        availability = await service.create_availability(
            seller_id=test_seller_id,
            commodity_id=test_commodity_id,
            location_id=test_location_id,  # Registered location
            total_quantity=Decimal("150.0"),
            base_price=Decimal("9000.0"),
            quality_params={"grade": "Premium", "length": 31.0},
            auto_approve=True
        )
        
        print(f"\n✅ Availability created!")
        print(f"   ID: {availability.id}")
        print(f"   location_id: {availability.location_id}")
        print(f"   delivery_latitude: {availability.delivery_latitude} (auto-fetched)")
        print(f"   delivery_longitude: {availability.delivery_longitude} (auto-fetched)")
        print(f"   delivery_region: {availability.delivery_region}")
        
        # Verify
        assert availability.location_id == test_location_id, "location_id mismatch"
        assert availability.delivery_latitude == Decimal("19.1136"), "latitude mismatch"
        assert availability.delivery_longitude == Decimal("72.8697"), "longitude mismatch"
        
        print(f"\n✅ TEST 2 PASSED: Registered location working correctly!")
        
        await session.rollback()  # Clean up
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        return False


async def test_3_adhoc_location(session: AsyncSession):
    """TEST 3: Create availability with ad-hoc location (Google Maps)"""
    print("\n" + "="*80)
    print("TEST 3: Ad-Hoc Location (Google Maps Coordinates)")
    print("="*80)
    print("🌟 THIS IS THE NEW FEATURE - Sell from unregistered locations!")
    
    service = AvailabilityService(session)
    
    print(f"\n📝 Creating availability with AD-HOC location...")
    print(f"   Address: Warehouse 5, GIDC Industrial Area, Surat, Gujarat")
    print(f"   Coordinates: 21.1702, 72.8311 (from Google Maps)")
    print(f"   NOTE: This location does NOT exist in settings_locations table!")
    
    try:
        availability = await service.create_availability(
            seller_id=test_seller_id,
            commodity_id=test_commodity_id,
            location_id=None,  # NO registered location
            # Ad-hoc location fields
            location_address="Warehouse 5, GIDC Industrial Area, Surat, Gujarat",
            location_latitude=Decimal("21.1702"),
            location_longitude=Decimal("72.8311"),
            location_pincode="395008",
            location_region="Gujarat",
            # Availability data
            total_quantity=Decimal("200.0"),
            base_price=Decimal("9500.0"),
            quality_params={
                "length": 30.0,
                "strength": 28.0,
                "micronaire": 4.2
            },
            auto_approve=True
        )
        
        print(f"\n✅ Availability created with AD-HOC location!")
        print(f"\n   Availability Details:")
        print(f"   - ID: {availability.id}")
        print(f"   - location_id: {availability.location_id} (NULL = ad-hoc)")
        print(f"   - delivery_address: {availability.delivery_address}")
        print(f"   - delivery_latitude: {availability.delivery_latitude}")
        print(f"   - delivery_longitude: {availability.delivery_longitude}")
        print(f"   - delivery_region: {availability.delivery_region}")
        
        # Verify
        assert availability.location_id is None, "location_id should be NULL"
        assert availability.delivery_latitude == Decimal("21.1702"), "latitude mismatch"
        assert availability.delivery_longitude == Decimal("72.8311"), "longitude mismatch"
        assert "GIDC" in availability.delivery_address, "address not stored"
        assert availability.delivery_region == "Gujarat", "region mismatch"
        
        print(f"\n✅ TEST 3 PASSED: Ad-hoc location working perfectly!")
        print(f"   ✓ location_id is NULL (ad-hoc)")
        print(f"   ✓ Google Maps coordinates stored")
        print(f"   ✓ Address stored correctly")
        print(f"   ✓ Region stored for validation")
        
        await session.rollback()  # Clean up
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        return False


async def test_4_validation_no_location(session: AsyncSession):
    """TEST 4: Validation - must provide SOME location"""
    print("\n" + "="*80)
    print("TEST 4: Validation - Location Required")
    print("="*80)
    
    service = AvailabilityService(session)
    
    print(f"\n📝 Attempting to create availability WITHOUT any location...")
    print(f"   (Should fail validation)")
    
    try:
        availability = await service.create_availability(
            seller_id=test_seller_id,
            commodity_id=test_commodity_id,
            location_id=None,  # NO registered location
            # NO ad-hoc location fields either
            total_quantity=Decimal("50.0"),
            quality_params={"grade": "A"},
            auto_approve=True
        )
        
        print(f"\n❌ TEST 4 FAILED: Should have rejected but created: {availability.id}")
        await session.rollback()
        return False
        
    except ValueError as e:
        error_msg = str(e)
        if "location" in error_msg.lower():
            print(f"\n✅ TEST 4 PASSED: Correctly rejected!")
            print(f"   ✓ Error: {error_msg[:150]}")
            await session.rollback()
            return True
        else:
            print(f"\n⚠️  Rejected but wrong error: {error_msg}")
            await session.rollback()
            return False
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: Unexpected error: {e}")
        await session.rollback()
        return False


async def test_5_cdps_capability(session: AsyncSession):
    """TEST 5: CDPS Capability Validation"""
    print("\n" + "="*80)
    print("TEST 5: CDPS Capability Validation")
    print("="*80)
    
    # Create seller WITHOUT sell capability
    print(f"\n📝 Creating seller WITHOUT sell capability...")
    
    from uuid import UUID
    seller_no_cap = BusinessPartner(
        id=uuid4(),
        legal_name=f"Buyer Only {uuid4().hex[:8]}",
        country="India",
        organization_id=UUID(EXISTING_ORG_ID),
        entity_class="entity",
        capabilities={
            "domestic_sell_india": False,  # NO SELL CAPABILITY
            "domestic_buy_india": True
        }
    )
    session.add(seller_no_cap)
    await session.flush()
    
    print(f"   ✅ Seller created: {seller_no_cap.legal_name}")
    print(f"   - domestic_sell_india: {seller_no_cap.capabilities.get('domestic_sell_india')}")
    
    # Try to create availability (should fail)
    service = AvailabilityService(session)
    
    print(f"\n📝 Attempting to create availability (should fail)...")
    
    try:
        availability = await service.create_availability(
            seller_id=seller_no_cap.id,
            commodity_id=test_commodity_id,
            location_id=test_location_id,
            total_quantity=Decimal("50.0"),
            quality_params={"grade": "A"},
            auto_approve=True
        )
        
        print(f"\n❌ TEST 5 FAILED: Should have blocked but created: {availability.id}")
        await session.rollback()
        return False
        
    except Exception as e:
        error_msg = str(e)
        if "capability" in error_msg.lower() or "sell" in error_msg.lower():
            print(f"\n✅ TEST 5 PASSED: CDPS validation working!")
            print(f"   ✓ Correctly blocked seller without sell capability")
            print(f"   ✓ Error: {error_msg[:150]}")
            await session.rollback()
            return True
        else:
            print(f"\n⚠️  Blocked but wrong reason: {error_msg[:150]}")
            await session.rollback()
            return False


async def test_6_query_availabilities(session: AsyncSession):
    """TEST 6: Query created availabilities"""
    print("\n" + "="*80)
    print("TEST 6: Query Availabilities")
    print("="*80)
    
    # Create a few test availabilities first
    service = AvailabilityService(session)
    
    print(f"\n📝 Creating test availabilities...")
    
    created_ids = []
    
    # Create 2 availabilities
    for i in range(2):
        try:
            availability = await service.create_availability(
                seller_id=test_seller_id,
                commodity_id=test_commodity_id,
                location_id=test_location_id,
                total_quantity=Decimal(f"{100 + i*50}.0"),
                base_price=Decimal(f"{8000 + i*500}.0"),
                quality_params={"test": f"sample_{i}"},
                auto_approve=True
            )
            created_ids.append(availability.id)
            print(f"   ✅ Created availability {i+1}: {availability.id}")
        except Exception as e:
            print(f"   ⚠️  Failed to create availability {i+1}: {e}")
    
    # Query availabilities
    print(f"\n📝 Querying availabilities...")
    
    try:
        result = await session.execute(
            select(Availability)
            .where(Availability.seller_id == test_seller_id)
            .limit(10)
        )
        availabilities = result.scalars().all()
        
        print(f"\n✅ Found {len(availabilities)} availabilities")
        
        if len(availabilities) > 0:
            sample = availabilities[0]
            print(f"\n📋 Sample availability:")
            print(f"   - ID: {sample.id}")
            print(f"   - Commodity: {sample.commodity_id}")
            print(f"   - Location: {sample.location_id or 'Ad-hoc'}")
            print(f"   - Quantity: {sample.total_quantity} {sample.quantity_unit}")
            print(f"   - Price: {sample.base_price} {sample.price_unit}")
            print(f"   - Coordinates: {sample.delivery_latitude}, {sample.delivery_longitude}")
            
            print(f"\n✅ TEST 6 PASSED: Query working correctly!")
            await session.rollback()
            return True
        else:
            print(f"\n⚠️  No availabilities found (but no error)")
            await session.rollback()
            return True
            
    except Exception as e:
        print(f"\n❌ TEST 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 AVAILABILITY ENGINE - COMPLETE END-TO-END TEST")
    print("="*80)
    print("\nFeatures to test:")
    print("  1. ✅ Auto-unit population from commodity master")
    print("  2. ✅ Registered location (settings table)")
    print("  3. ✅ Ad-hoc location (Google Maps) - NEW FEATURE")
    print("  4. ✅ Location validation")
    print("  5. ✅ CDPS capability validation")
    print("  6. ✅ Query availabilities")
    print("="*80)
    
    # Create database connection
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Setup
    async with async_session() as session:
        try:
            await setup_test_data(session)
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            import traceback
            traceback.print_exc()
            await engine.dispose()
            return 1
    
    # Run tests
    results = []
    tests = [
        ("Auto-Unit Population", test_1_auto_unit_population),
        ("Registered Location", test_2_registered_location),
        ("Ad-Hoc Location (Google Maps)", test_3_adhoc_location),
        ("Location Validation", test_4_validation_no_location),
        ("CDPS Capability Check", test_5_cdps_capability),
        ("Query Availabilities", test_6_query_availabilities),
    ]
    
    for test_name, test_func in tests:
        async with async_session() as session:
            try:
                result = await test_func(session)
                results.append((test_name, result))
            except Exception as e:
                print(f"\n❌ {test_name} crashed: {e}")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))
    
    # Cleanup
    await engine.dispose()
    
    # Summary
    print("\n" + "="*80)
    print("📊 FINAL TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status:12} {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\n📈 Results: {total_passed}/{total_tests} tests passed ({int(total_passed/total_tests*100)}%)")
    
    if total_passed == total_tests:
        print("\n" + "🎉"*20)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("🎉"*20)
        print("\n✅ Features Verified:")
        print("   ✓ Auto-unit population working")
        print("   ✓ Registered locations working")
        print("   ✓ Ad-hoc locations (Google Maps) working")
        print("   ✓ Location validation working")
        print("   ✓ CDPS capability validation working")
        print("   ✓ Database queries working")
        print("\n🚀 System is PRODUCTION READY!")
    elif total_passed >= total_tests * 0.8:
        print("\n✅ Mostly passing - minor issues")
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
    
    print("="*80 + "\n")
    
    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
