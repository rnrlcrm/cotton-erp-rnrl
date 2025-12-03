#!/usr/bin/env python3
"""
Ad-Hoc Location Test - Google Maps Coordinates
Demonstrates selling from locations NOT in settings_locations table
"""
import asyncio
import sys
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.modules.trade_desk.services.availability_service import AvailabilityService
from backend.modules.settings.commodities.models import Commodity
from backend.modules.partners.models import BusinessPartner

# NOTE: BusinessPartner requires organization_id (schema mismatch with model comment)
# Using a default UUID for testing
DEFAULT_ORG_ID = uuid4()  # In real app, this would be fetched from organizations table

# Database URL
DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/commodity_dev"


async def test_adhoc_location():
    """Test creating availability with ad-hoc location (Google Maps coordinates)"""
    print("\n" + "="*80)
    print("TEST: Ad-Hoc Location Support (Google Maps Coordinates)")
    print("="*80)
    print("\nScenario: Seller wants to sell from GIDC Surat (NOT in settings table)")
    print("Solution: Provide address + Google Maps lat/lng directly")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Create test commodity
        commodity = Commodity(
            id=uuid4(),
            name="BCI Cotton",
            category="COTTON",
            base_unit="KG",
            trade_unit="CANDY",
            rate_unit="per CANDY",
            is_active=True
        )
        session.add(commodity)
        
        # 2. Create test seller
        seller = BusinessPartner(
            id=uuid4(),
            legal_name="Surat Commodity Trader",
            country="India",
            organization_id=DEFAULT_ORG_ID,
            entity_class="entity",
            capabilities={
                "domestic_sell_india": True,
                "domestic_buy_india": True
            }
        )
        session.add(seller)
        
        await session.commit()
        await session.refresh(commodity)
        await session.refresh(seller)
        
        print(f"\n✅ Created test data:")
        print(f"   Commodity: {commodity.name}")
        print(f"   Seller: {seller.legal_name}")
        
        # 3. Create availability with AD-HOC location (Google Maps)
        service = AvailabilityService(session)
        
        print(f"\n📍 Creating availability with AD-HOC LOCATION:")
        print(f"   Address: Warehouse 5, GIDC Industrial Area, Surat, Gujarat")
        print(f"   Coordinates: 21.1702, 72.8311 (from Google Maps)")
        print(f"   Pincode: 395008")
        print(f"   Region: Gujarat")
        print(f"\n   NOTE: This location does NOT exist in settings_locations table!")
        
        try:
            availability = await service.create_availability(
                seller_id=seller.id,
                commodity_id=commodity.id,
                # NO location_id - using ad-hoc location instead
                location_id=None,
                # Ad-hoc location data
                location_address="Warehouse 5, GIDC Industrial Area, Surat, Gujarat",
                location_latitude=Decimal("21.1702"),  # Google Maps
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
            
            print(f"\n✅ Availability created successfully with AD-HOC location!")
            print(f"\n   Availability Details:")
            print(f"   - ID: {availability.id}")
            print(f"   - Seller: {seller.legal_name}")
            print(f"   - Commodity: {commodity.name}")
            print(f"   - Quantity: {availability.total_quantity} {availability.quantity_unit}")
            print(f"   - Price: ₹{availability.base_price} {availability.price_unit}")
            
            print(f"\n   Location Details:")
            print(f"   - location_id: {availability.location_id} (NULL = ad-hoc)")
            print(f"   - delivery_address: {availability.delivery_address}")
            print(f"   - delivery_latitude: {availability.delivery_latitude}")
            print(f"   - delivery_longitude: {availability.delivery_longitude}")
            print(f"   - delivery_region: {availability.delivery_region}")
            
            # Verify ad-hoc location
            assert availability.location_id is None, "location_id should be NULL for ad-hoc"
            assert availability.delivery_latitude == Decimal("21.1702"), "Latitude should match"
            assert availability.delivery_longitude == Decimal("72.8311"), "Longitude should match"
            assert availability.delivery_region == "Gujarat", "Region should match"
            assert "GIDC" in availability.delivery_address, "Address should be stored"
            
            print(f"\n✅ AD-HOC LOCATION TEST PASSED!")
            print(f"   ✓ location_id is NULL (ad-hoc location)")
            print(f"   ✓ Google Maps coordinates stored correctly")
            print(f"   ✓ Address stored in delivery_address")
            print(f"   ✓ Region stored for capability validation")
            
            print(f"\n💡 Use Case:")
            print(f"   - Settings table has only 4 registered locations")
            print(f"   - Seller wants to sell from 5th location (Surat GIDC)")
            print(f"   - System accepts Google Maps coordinates directly")
            print(f"   - No need to add location to settings table first!")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            await session.rollback()
            await engine.dispose()


async def test_registered_location():
    """Test creating availability with registered location (traditional way)"""
    print("\n" + "="*80)
    print("TEST: Registered Location (Traditional)")
    print("="*80)
    print("\nScenario: Seller wants to sell from Mumbai (exists in settings table)")
    print("Solution: Provide location_id, system fetches coordinates")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Import Location model
        from backend.modules.settings.locations.models import Location
        
        # 1. Create registered location
        location = Location(
            id=uuid4(),
            name="Mumbai Warehouse",
            address="Andheri East, Mumbai",
            city="Mumbai",
            state="Maharashtra",
            country="INDIA",
            latitude=19.1136,
            longitude=72.8697,
            pincode="400069",
            is_active=True
        )
        session.add(location)
        
        # 2. Create commodity and seller
        commodity = Commodity(
            id=uuid4(),
            name="Organic Cotton",
            category="COTTON",
            base_unit="KG",
            trade_unit="BALE",
            rate_unit="per BALE",
            is_active=True
        )
        session.add(commodity)
        
        seller = BusinessPartner(
            id=uuid4(),
            legal_name="Mumbai Cotton Mills",
            country="India",
            organization_id=DEFAULT_ORG_ID,
            entity_class="entity",
            capabilities={
                "domestic_sell_india": True,
                "domestic_buy_india": False
            }
        )
        session.add(seller)
        
        await session.commit()
        await session.refresh(location)
        await session.refresh(commodity)
        await session.refresh(seller)
        
        print(f"\n✅ Created test data:")
        print(f"   Location: {location.name} (registered in settings table)")
        print(f"   Commodity: {commodity.name}")
        print(f"   Seller: {seller.legal_name}")
        
        # 3. Create availability with REGISTERED location
        service = AvailabilityService(session)
        
        print(f"\n📍 Creating availability with REGISTERED LOCATION:")
        print(f"   Location ID: {location.id}")
        print(f"   Location Name: {location.name}")
        print(f"   System will auto-fetch coordinates from settings table")
        
        try:
            availability = await service.create_availability(
                seller_id=seller.id,
                commodity_id=commodity.id,
                location_id=location.id,  # Using registered location
                # No ad-hoc location data needed
                total_quantity=Decimal("150.0"),
                base_price=Decimal("10000.0"),
                quality_params={
                    "grade": "Premium",
                    "length": 31.0
                },
                auto_approve=True
            )
            
            print(f"\n✅ Availability created successfully with REGISTERED location!")
            print(f"\n   Availability Details:")
            print(f"   - ID: {availability.id}")
            print(f"   - location_id: {availability.location_id} (registered)")
            print(f"   - delivery_latitude: {availability.delivery_latitude} (auto-fetched)")
            print(f"   - delivery_longitude: {availability.delivery_longitude} (auto-fetched)")
            print(f"   - delivery_region: {availability.delivery_region} (auto-fetched)")
            
            # Verify registered location
            assert availability.location_id == location.id, "location_id should match"
            assert availability.delivery_latitude == location.latitude, "Lat should match"
            assert availability.delivery_longitude == location.longitude, "Lng should match"
            
            print(f"\n✅ REGISTERED LOCATION TEST PASSED!")
            print(f"   ✓ location_id stored correctly")
            print(f"   ✓ Coordinates auto-fetched from settings table")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            await session.rollback()
            await engine.dispose()


async def main():
    """Run all location tests"""
    print("\n" + "="*80)
    print("LOCATION FLEXIBILITY TESTS")
    print("Dual Support: Registered Locations + Ad-Hoc Google Maps")
    print("="*80)
    
    results = []
    
    # Test 1: Ad-hoc location
    try:
        result1 = await test_adhoc_location()
        results.append(("Ad-Hoc Location (Google Maps)", result1))
    except Exception as e:
        print(f"\n❌ Test 1 crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Ad-Hoc Location", False))
    
    # Test 2: Registered location
    try:
        result2 = await test_registered_location()
        results.append(("Registered Location (Settings Table)", result2))
    except Exception as e:
        print(f"\n❌ Test 2 crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Registered Location", False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status:12} {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 SUCCESS: System supports BOTH registered and ad-hoc locations!")
        print("   - Registered: Use location_id (traditional)")
        print("   - Ad-Hoc: Use address + Google Maps lat/lng (new)")
    
    print("="*80 + "\n")
    
    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
