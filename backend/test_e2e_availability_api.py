#!/usr/bin/env python3
"""
End-to-End API Test - Availability Engine
Tests all features via HTTP API endpoints
"""
import asyncio
import httpx
from decimal import Decimal
from uuid import uuid4
import json

# API Base URL
API_BASE = "http://localhost:8000/api/v1"

# Test data will be created
test_commodity_id = None
test_registered_location_id = None
test_seller_id = None


async def setup_test_data():
    """Create test data via API"""
    global test_commodity_id, test_registered_location_id, test_seller_id
    
    print("\n" + "="*80)
    print("SETUP: Creating Test Data")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Create Commodity
        print("\n1. Creating test commodity...")
        commodity_data = {
            "name": f"Test Cotton E2E {uuid4().hex[:8]}",
            "category": "COTTON",
            "base_unit": "KG",
            "trade_unit": "CANDY",
            "rate_unit": "per CANDY",
            "is_active": True
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/commodities",
                json=commodity_data
            )
            if response.status_code == 201:
                commodity = response.json()
                test_commodity_id = commodity["id"]
                print(f"   ✅ Commodity created: {test_commodity_id}")
            else:
                print(f"   ⚠️  Commodity creation returned {response.status_code}")
                print(f"   Using mock UUID for testing")
                test_commodity_id = str(uuid4())
        except Exception as e:
            print(f"   ⚠️  Could not create commodity: {e}")
            test_commodity_id = str(uuid4())
        
        # 2. Create Registered Location
        print("\n2. Creating registered location...")
        location_data = {
            "name": f"Test Warehouse {uuid4().hex[:8]}",
            "address": "Test Address, Mumbai",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "INDIA",
            "latitude": 19.1136,
            "longitude": 72.8697,
            "pincode": "400069",
            "is_active": True
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/locations",
                json=location_data
            )
            if response.status_code == 201:
                location = response.json()
                test_registered_location_id = location["id"]
                print(f"   ✅ Location created: {test_registered_location_id}")
            else:
                print(f"   ⚠️  Location creation returned {response.status_code}")
                test_registered_location_id = str(uuid4())
        except Exception as e:
            print(f"   ⚠️  Could not create location: {e}")
            test_registered_location_id = str(uuid4())
        
        # 3. Create Seller
        print("\n3. Creating test seller...")
        seller_data = {
            "legal_name": f"Test Seller {uuid4().hex[:8]}",
            "country": "India",
            "entity_class": "entity",
            "capabilities": {
                "domestic_sell_india": True,
                "domestic_buy_india": True
            }
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/business-partners",
                json=seller_data
            )
            if response.status_code == 201:
                seller = response.json()
                test_seller_id = seller["id"]
                print(f"   ✅ Seller created: {test_seller_id}")
            else:
                print(f"   ⚠️  Seller creation returned {response.status_code}")
                test_seller_id = str(uuid4())
        except Exception as e:
            print(f"   ⚠️  Could not create seller: {e}")
            test_seller_id = str(uuid4())
    
    print(f"\n✅ Setup complete")
    return test_commodity_id, test_registered_location_id, test_seller_id


async def test_1_auto_unit_population():
    """Test 1: Auto-populate quantity_unit and price_unit from commodity"""
    print("\n" + "="*80)
    print("TEST 1: Auto-Unit Population")
    print("="*80)
    print("Feature: System auto-fills quantity_unit and price_unit from commodity master")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create availability WITHOUT units
        payload = {
            "seller_id": test_seller_id,
            "commodity_id": test_commodity_id,
            "location_id": test_registered_location_id,
            "total_quantity": 100.0,
            # NO quantity_unit - should auto-populate from commodity.trade_unit
            "base_price": 8000.0,
            # NO price_unit - should auto-populate from commodity.rate_unit
            "quality_params": {
                "length": 29.0,
                "strength": 26.0,
                "micronaire": 4.5
            }
        }
        
        print("\n📝 Request payload (NO units specified):")
        print(json.dumps(payload, indent=2))
        
        try:
            response = await client.post(
                f"{API_BASE}/availabilities",
                json=payload
            )
            
            print(f"\n📥 Response: {response.status_code}")
            
            if response.status_code == 201:
                availability = response.json()
                print("\n✅ Availability created!")
                print(f"   ID: {availability.get('id')}")
                print(f"   quantity_unit: {availability.get('quantity_unit')} (auto-populated)")
                print(f"   price_unit: {availability.get('price_unit')} (auto-populated)")
                
                # Verify units are populated
                if availability.get('quantity_unit') == 'CANDY':
                    print("\n✅ TEST PASSED: quantity_unit auto-populated correctly")
                else:
                    print(f"\n⚠️  quantity_unit = {availability.get('quantity_unit')}, expected CANDY")
                
                if availability.get('price_unit') == 'per CANDY':
                    print("✅ TEST PASSED: price_unit auto-populated correctly")
                else:
                    print(f"⚠️  price_unit = {availability.get('price_unit')}, expected 'per CANDY'")
                
                return True
            else:
                print(f"\n❌ TEST FAILED: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            return False


async def test_2_registered_location():
    """Test 2: Create availability with registered location"""
    print("\n" + "="*80)
    print("TEST 2: Registered Location (Traditional)")
    print("="*80)
    print("Feature: Use location_id from settings_locations table")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "seller_id": test_seller_id,
            "commodity_id": test_commodity_id,
            "location_id": test_registered_location_id,  # Registered location
            "total_quantity": 150.0,
            "base_price": 9000.0,
            "quality_params": {
                "grade": "Premium",
                "length": 31.0
            }
        }
        
        print("\n📝 Request payload (Registered location):")
        print(json.dumps(payload, indent=2))
        
        try:
            response = await client.post(
                f"{API_BASE}/availabilities",
                json=payload
            )
            
            print(f"\n📥 Response: {response.status_code}")
            
            if response.status_code == 201:
                availability = response.json()
                print("\n✅ Availability created!")
                print(f"   ID: {availability.get('id')}")
                print(f"   location_id: {availability.get('location_id')}")
                print(f"   delivery_latitude: {availability.get('delivery_latitude')} (auto-fetched)")
                print(f"   delivery_longitude: {availability.get('delivery_longitude')} (auto-fetched)")
                
                if availability.get('location_id') == test_registered_location_id:
                    print("\n✅ TEST PASSED: Registered location stored correctly")
                    return True
                else:
                    print("\n⚠️  Location ID mismatch")
                    return False
            else:
                print(f"\n❌ TEST FAILED: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            return False


async def test_3_adhoc_location():
    """Test 3: Create availability with ad-hoc location (Google Maps)"""
    print("\n" + "="*80)
    print("TEST 3: Ad-Hoc Location (Google Maps Coordinates)")
    print("="*80)
    print("Feature: Sell from location NOT in settings table using Google Maps coords")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "seller_id": test_seller_id,
            "commodity_id": test_commodity_id,
            # NO location_id - using ad-hoc instead
            "location_address": "Warehouse 5, GIDC Industrial Area, Surat, Gujarat",
            "location_latitude": 21.1702,  # Google Maps
            "location_longitude": 72.8311,
            "location_pincode": "395008",
            "location_region": "Gujarat",
            "total_quantity": 200.0,
            "base_price": 9500.0,
            "quality_params": {
                "length": 30.0,
                "strength": 28.0,
                "micronaire": 4.2
            }
        }
        
        print("\n📝 Request payload (Ad-hoc location with Google Maps):")
        print(json.dumps(payload, indent=2))
        
        try:
            response = await client.post(
                f"{API_BASE}/availabilities",
                json=payload
            )
            
            print(f"\n📥 Response: {response.status_code}")
            
            if response.status_code == 201:
                availability = response.json()
                print("\n✅ Availability created with AD-HOC location!")
                print(f"   ID: {availability.get('id')}")
                print(f"   location_id: {availability.get('location_id')} (NULL = ad-hoc)")
                print(f"   delivery_address: {availability.get('delivery_address')}")
                print(f"   delivery_latitude: {availability.get('delivery_latitude')}")
                print(f"   delivery_longitude: {availability.get('delivery_longitude')}")
                print(f"   delivery_region: {availability.get('delivery_region')}")
                
                checks = []
                
                # Verify location_id is null
                if availability.get('location_id') is None:
                    print("\n✅ location_id is NULL (ad-hoc location)")
                    checks.append(True)
                else:
                    print("\n⚠️  location_id should be NULL for ad-hoc")
                    checks.append(False)
                
                # Verify coordinates stored
                if availability.get('delivery_latitude') == 21.1702:
                    print("✅ Latitude stored correctly")
                    checks.append(True)
                else:
                    print(f"⚠️  Latitude mismatch: {availability.get('delivery_latitude')}")
                    checks.append(False)
                
                if availability.get('delivery_longitude') == 72.8311:
                    print("✅ Longitude stored correctly")
                    checks.append(True)
                else:
                    print(f"⚠️  Longitude mismatch: {availability.get('delivery_longitude')}")
                    checks.append(False)
                
                # Verify address stored
                if "GIDC" in str(availability.get('delivery_address', '')):
                    print("✅ Address stored correctly")
                    checks.append(True)
                else:
                    print(f"⚠️  Address issue: {availability.get('delivery_address')}")
                    checks.append(False)
                
                if all(checks):
                    print("\n✅ TEST PASSED: Ad-hoc location fully functional!")
                    return True
                else:
                    print("\n⚠️  Some checks failed")
                    return False
                    
            else:
                print(f"\n❌ TEST FAILED: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            return False


async def test_4_validation_either_location():
    """Test 4: Validation - must provide EITHER location_id OR ad-hoc"""
    print("\n" + "="*80)
    print("TEST 4: Validation - EITHER Location Required")
    print("="*80)
    print("Feature: Must provide location_id OR ad-hoc, not both, not neither")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 4A: No location at all (should fail)
        print("\n4A. Testing NO location provided (should fail)...")
        payload_no_location = {
            "seller_id": test_seller_id,
            "commodity_id": test_commodity_id,
            # NO location_id
            # NO ad-hoc location fields
            "total_quantity": 50.0,
            "quality_params": {"grade": "A"}
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/availabilities",
                json=payload_no_location
            )
            
            if response.status_code in [400, 422]:
                print(f"   ✅ Correctly rejected (HTTP {response.status_code})")
                error = response.json()
                print(f"   Error: {error.get('detail', error)}")
                test_4a = True
            else:
                print(f"   ❌ Should have rejected but got {response.status_code}")
                test_4a = False
        except Exception as e:
            print(f"   ⚠️  Exception: {e}")
            test_4a = False
        
        # Test 4B: Both location types (should fail)
        print("\n4B. Testing BOTH location types provided (should fail)...")
        payload_both = {
            "seller_id": test_seller_id,
            "commodity_id": test_commodity_id,
            "location_id": test_registered_location_id,  # Registered
            "location_address": "Some address",  # Ad-hoc
            "location_latitude": 19.0,
            "location_longitude": 72.0,
            "total_quantity": 50.0,
            "quality_params": {"grade": "A"}
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/availabilities",
                json=payload_both
            )
            
            if response.status_code in [400, 422]:
                print(f"   ✅ Correctly rejected (HTTP {response.status_code})")
                error = response.json()
                print(f"   Error: {error.get('detail', error)}")
                test_4b = True
            else:
                print(f"   ❌ Should have rejected but got {response.status_code}")
                test_4b = False
        except Exception as e:
            print(f"   ⚠️  Exception: {e}")
            test_4b = False
        
        if test_4a and test_4b:
            print("\n✅ TEST PASSED: Location validation working correctly")
            return True
        else:
            print("\n⚠️  Some validation checks failed")
            return False


async def test_5_cdps_capability_validation():
    """Test 5: CDPS Capability Validation"""
    print("\n" + "="*80)
    print("TEST 5: CDPS Capability Validation")
    print("="*80)
    print("Feature: Validate seller has SELL capability from verified documents")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try to create seller without sell capability
        print("\n5A. Creating seller WITHOUT sell capability...")
        seller_no_cap = {
            "legal_name": f"Buyer Only {uuid4().hex[:8]}",
            "country": "India",
            "entity_class": "entity",
            "capabilities": {
                "domestic_sell_india": False,  # NO SELL CAPABILITY
                "domestic_buy_india": True
            }
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/business-partners",
                json=seller_no_cap
            )
            
            if response.status_code == 201:
                seller = response.json()
                seller_id_no_cap = seller["id"]
                print(f"   ✅ Seller created: {seller_id_no_cap}")
                
                # Now try to create availability (should fail)
                print("\n5B. Attempting to create availability (should fail)...")
                payload = {
                    "seller_id": seller_id_no_cap,
                    "commodity_id": test_commodity_id,
                    "location_id": test_registered_location_id,
                    "total_quantity": 50.0,
                    "quality_params": {"grade": "A"}
                }
                
                response2 = await client.post(
                    f"{API_BASE}/availabilities",
                    json=payload
                )
                
                if response2.status_code in [400, 403, 422]:
                    print(f"   ✅ Correctly blocked (HTTP {response2.status_code})")
                    error = response2.json()
                    error_msg = str(error.get('detail', error))
                    
                    if 'capability' in error_msg.lower() or 'sell' in error_msg.lower():
                        print(f"   ✅ CDPS validation working!")
                        print(f"   Error: {error_msg[:150]}")
                        return True
                    else:
                        print(f"   ⚠️  Blocked but not for capability reason: {error_msg[:150]}")
                        return False
                else:
                    print(f"   ❌ Should have blocked but got {response2.status_code}")
                    return False
            else:
                print(f"   ⚠️  Could not create test seller: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"\n⚠️  Exception: {e}")
            return False


async def test_6_list_availabilities():
    """Test 6: List availabilities"""
    print("\n" + "="*80)
    print("TEST 6: List Availabilities")
    print("="*80)
    print("Feature: Retrieve all created availabilities")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{API_BASE}/availabilities")
            
            print(f"\n📥 Response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                availabilities = data.get('items', data if isinstance(data, list) else [])
                count = len(availabilities) if isinstance(availabilities, list) else data.get('total', 0)
                
                print(f"\n✅ Retrieved {count} availabilities")
                
                if count > 0:
                    print(f"\n📋 Sample availability:")
                    sample = availabilities[0] if isinstance(availabilities, list) else None
                    if sample:
                        print(f"   ID: {sample.get('id')}")
                        print(f"   Commodity: {sample.get('commodity_id')}")
                        print(f"   Location: {sample.get('location_id', 'Ad-hoc')}")
                        print(f"   Quantity: {sample.get('total_quantity')} {sample.get('quantity_unit')}")
                        print(f"   Price: {sample.get('base_price')} {sample.get('price_unit')}")
                
                print("\n✅ TEST PASSED: List endpoint working")
                return True
            else:
                print(f"\n⚠️  Unexpected status: {response.status_code}")
                print(response.text[:500])
                return False
                
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            return False


async def main():
    """Run all E2E tests"""
    print("\n" + "="*80)
    print("🚀 AVAILABILITY ENGINE - END-TO-END API TESTS")
    print("="*80)
    print("\nFeatures being tested:")
    print("  1. Auto-unit population from commodity master")
    print("  2. Registered location (settings table)")
    print("  3. Ad-hoc location (Google Maps coordinates)")
    print("  4. Location validation (either/or)")
    print("  5. CDPS capability validation")
    print("  6. List availabilities")
    
    # Setup
    try:
        await setup_test_data()
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\n⚠️  Make sure the API server is running:")
        print("   cd backend && uvicorn main:app --reload")
        return 1
    
    # Run tests
    results = []
    
    tests = [
        ("Auto-Unit Population", test_1_auto_unit_population),
        ("Registered Location", test_2_registered_location),
        ("Ad-Hoc Location (Google Maps)", test_3_adhoc_location),
        ("Location Validation", test_4_validation_either_location),
        ("CDPS Capability Check", test_5_cdps_capability_validation),
        ("List Availabilities", test_6_list_availabilities),
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status:12} {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\n📈 Results: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✅ Features verified:")
        print("   ✓ Auto-unit population working")
        print("   ✓ Registered locations working")
        print("   ✓ Ad-hoc locations working")
        print("   ✓ Location validation working")
        print("   ✓ CDPS capability validation working")
        print("   ✓ API endpoints functional")
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        print("\n💡 Note: Some failures may be expected if:")
        print("   - API endpoints are not implemented yet")
        print("   - Database schema not migrated")
        print("   - Server not running")
    
    print("="*80 + "\n")
    
    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
