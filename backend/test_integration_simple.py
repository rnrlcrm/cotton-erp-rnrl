#!/usr/bin/env python3
"""
Simple Integration Test - Auto-Unit Population & CDPS Validation
Demonstrates the key features implemented in this branch
"""
import asyncio
import sys
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from backend.modules.trade_desk.services.availability_service import AvailabilityService
from backend.modules.settings.commodities.models import Commodity
from backend.modules.settings.locations.models import Location
from backend.modules.partners.models import BusinessPartner

# Database URL
DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/cotton_dev"


async def test_auto_unit_population():
    """Test that quantity_unit and price_unit are auto-populated from commodity master"""
    print("\n" + "="*80)
    print("TEST 1: Auto-Unit Population from Commodity Master")
    print("="*80)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Create test commodity with trade_unit and rate_unit
        commodity = Commodity(
            id=uuid4(),
            name="Test Cotton",
            category="COTTON",
            base_unit="KG",
            trade_unit="CANDY",  # This should auto-populate quantity_unit
            rate_unit="per CANDY",  # This should auto-populate price_unit
            is_active=True
        )
        session.add(commodity)
        
        # 2. Create test location with coordinates for Google Maps
        location = Location(
            id=uuid4(),
            name="Mumbai Warehouse",
            address="Andheri East, Mumbai",
            city="Mumbai",
            state="Maharashtra",
            country="INDIA",
            latitude=19.1136,  # Mumbai coordinates
            longitude=72.8697,
            pincode="400069",
            is_active=True
        )
        session.add(location)
        
        # 3. Create test seller
        seller = BusinessPartner(
            id=uuid4(),
            legal_name="Test Seller",
            entity_class="entity",
            capabilities={
                "domestic_sell_india": True,
                "domestic_buy_india": False
            },
            is_active=True
        )
        session.add(seller)
        
        await session.commit()
        await session.refresh(commodity)
        await session.refresh(location)
        await session.refresh(seller)
        
        print(f"\n✅ Created test data:")
        print(f"   Commodity: {commodity.name}")
        print(f"   - base_unit: {commodity.base_unit}")
        print(f"   - trade_unit: {commodity.trade_unit}")
        print(f"   - rate_unit: {commodity.rate_unit}")
        print(f"   Location: {location.name}")
        print(f"   Seller: {seller.legal_name}")
        
        # 4. Create availability WITHOUT specifying units
        service = AvailabilityService(session)
        
        print(f"\n📝 Creating availability WITHOUT quantity_unit and price_unit...")
        print(f"   (System should auto-populate from commodity master)")
        
        try:
            availability = await service.create_availability(
                seller_id=seller.id,
                commodity_id=commodity.id,
                location_id=location.id,
                total_quantity=Decimal("100.0"),
                # quantity_unit NOT provided - should auto-populate
                base_price=Decimal("8000.0"),
                # price_unit NOT provided - should auto-populate
                quality_params={"length": 29.0, "strength": 26.0},
                auto_approve=True
            )
            
            print(f"\n✅ Availability created successfully!")
            print(f"   ID: {availability.id}")
            print(f"   Total Quantity: {availability.total_quantity}")
            print(f"   quantity_unit: {availability.quantity_unit} (auto-populated from commodity.trade_unit)")
            print(f"   Base Price: {availability.base_price}")
            print(f"   price_unit: {availability.price_unit} (auto-populated from commodity.rate_unit)")
            
            # Verify units match commodity
            assert availability.quantity_unit == commodity.trade_unit, "quantity_unit should match commodity.trade_unit"
            assert availability.price_unit == commodity.rate_unit, "price_unit should match commodity.rate_unit"
            
            print(f"\n✅ AUTO-UNIT POPULATION TEST PASSED!")
            print(f"   ✓ quantity_unit correctly populated: {availability.quantity_unit}")
            print(f"   ✓ price_unit correctly populated: {availability.price_unit}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            await session.rollback()
            await engine.dispose()


async def test_cdps_validation():
    """Test that CDPS capability validation works (not partner_type)"""
    print("\n" + "="*80)
    print("TEST 2: CDPS Capability Validation (Not partner_type)")
    print("="*80)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Create commodity and location
        commodity = Commodity(
            id=uuid4(),
            name="Test Cotton CDPS",
            category="COTTON",
            base_unit="KG",
            trade_unit="BALE",
            rate_unit="per BALE",
            is_active=True
        )
        session.add(commodity)
        
        location = Location(
            id=uuid4(),
            name="Delhi Warehouse",
            address="Connaught Place, New Delhi",
            city="New Delhi",
            state="Delhi",
            country="INDIA",
            latitude=28.6139,  # Delhi coordinates
            longitude=77.2090,
            pincode="110001",
            is_active=True
        )
        session.add(location)
        
        # Create seller WITHOUT sell capability
        seller_no_capability = BusinessPartner(
            id=uuid4(),
            legal_name="Seller Without Sell Capability",
            entity_class="entity",
            capabilities={
                "domestic_sell_india": False,  # NO SELL CAPABILITY
                "domestic_buy_india": True
            },
            is_active=True
        )
        session.add(seller_no_capability)
        
        await session.commit()
        await session.refresh(commodity)
        await session.refresh(location)
        await session.refresh(seller_no_capability)
        
        print(f"\n✅ Created test data:")
        print(f"   Seller: {seller_no_capability.legal_name}")
        print(f"   - capabilities: {seller_no_capability.capabilities}")
        print(f"   - domestic_sell_india: {seller_no_capability.capabilities.get('domestic_sell_india')}")
        
        # Try to create availability (should fail due to missing capability)
        service = AvailabilityService(session)
        
        print(f"\n📝 Attempting to create availability with seller lacking sell capability...")
        
        try:
            availability = await service.create_availability(
                seller_id=seller_no_capability.id,
                commodity_id=commodity.id,
                location_id=location.id,
                total_quantity=Decimal("50.0"),
                base_price=Decimal("5000.0"),
                quality_params={"grade": "A"},
                auto_approve=True
            )
            
            print(f"\n❌ TEST FAILED: Availability should NOT have been created!")
            print(f"   Seller lacks domestic_sell_india capability")
            return False
            
        except Exception as e:
            error_msg = str(e)
            if "capability" in error_msg.lower() or "sell" in error_msg.lower():
                print(f"\n✅ CDPS VALIDATION TEST PASSED!")
                print(f"   ✓ System correctly rejected seller without sell capability")
                print(f"   ✓ Error: {error_msg[:100]}...")
                return True
            else:
                print(f"\n❌ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        finally:
            await session.rollback()
            await engine.dispose()


async def main():
    """Run all integration tests"""
    print("\n" + "="*80)
    print("AVAILABILITY ENGINE - INTEGRATION TESTS")
    print("Features: Auto-Unit Population + CDPS Capability Validation")
    print("="*80)
    
    results = []
    
    # Test 1: Auto-unit population
    try:
        result1 = await test_auto_unit_population()
        results.append(("Auto-Unit Population", result1))
    except Exception as e:
        print(f"\n❌ Test 1 crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Auto-Unit Population", False))
    
    # Test 2: CDPS validation
    try:
        result2 = await test_cdps_validation()
        results.append(("CDPS Capability Validation", result2))
    except Exception as e:
        print(f"\n❌ Test 2 crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("CDPS Capability Validation", False))
    
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
    print("="*80 + "\n")
    
    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
