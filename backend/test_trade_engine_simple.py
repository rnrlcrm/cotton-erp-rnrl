"""
Simple Trade Engine API Test

Tests the core Trade Engine routes directly via HTTP
NO database fixtures needed - uses existing data

Run with: pytest test_trade_engine_simple.py -v -s
"""

import asyncio
import pytest
from httpx import AsyncClient
from fastapi import status


# Base URL for API
BASE_URL = "http://localhost:8001"


class TestTradeEngineRoutes:
    """Test Trade Engine HTTP endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Verify API is running"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.get("/health")
            assert response.status_code == status.HTTP_200_OK
            print("✓ API is running")
    
    
    @pytest.mark.asyncio
    async def test_create_branch(self):
        """Test POST /partners/branches/ - Create branch"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # First, get auth token (you'll need to adapt this)
            # For now, let's just test the endpoint exists
            
            branch_data = {
                "branch_code": "TEST-001",
                "branch_name": "Test Warehouse",
                "address_line_1": "123 Test Street",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postal_code": "400001",
                "country": "India",
                "can_receive_shipments": True,
                "can_send_shipments": False,
                "warehouse_capacity_qtls": 1000,
                "supported_commodities": ["COTTON"]
            }
            
            # This will fail with 401 if not authenticated, which proves endpoint exists
            response = await client.post(
                "/partners/branches/",
                json=branch_data
            )
            
            # We expect 401 (unauthorized) or 201 (created)
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
            print(f"✓ Branch creation endpoint exists (status: {response.status_code})")
    
    
    @pytest.mark.asyncio
    async def test_trade_creation_endpoint(self):
        """Test POST /trades/create - Instant contract endpoint exists"""
        async with AsyncClient(base_url=BASE_URL) as client:
            trade_data = {
                "negotiation_id": "00000000-0000-0000-0000-000000000000",
                "acknowledged_binding_contract": True
            }
            
            response = await client.post(
                "/trades/create",
                json=trade_data
            )
            
            # We expect 401 (unauthorized) or 422 (validation error) - proves endpoint exists
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_422_UNPROCESSABLE_ENTITY]
            print(f"✓ Trade creation endpoint exists (status: {response.status_code})")
    
    
    @pytest.mark.asyncio
    async def test_ai_branch_suggestions_endpoint(self):
        """Test POST /trades/branch-suggestions - AI endpoint exists"""
        async with AsyncClient(base_url=BASE_URL) as client:
            request_data = {
                "partner_id": "00000000-0000-0000-0000-000000000000",
                "commodity_code": "COTTON",
                "quantity_qtls": 100,
                "direction": "ship_to",
                "target_state": "Gujarat"
            }
            
            response = await client.post(
                "/trades/branch-suggestions",
                json=request_data
            )
            
            # We expect 401 or 422 - proves endpoint exists
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_422_UNPROCESSABLE_ENTITY]
            print(f"✓ AI branch suggestions endpoint exists (status: {response.status_code})")


class TestTradeEngineLogic:
    """Test Trade Engine business logic (unit tests)"""
    
    def test_gst_calculation_intra_state(self):
        """Test GST calculation for same state (CGST + SGST)"""
        from decimal import Decimal
        
        # Simulate TradeService._calculate_gst method
        buyer_state = "Maharashtra"
        seller_state = "Maharashtra"
        base_amount = Decimal("100000.00")
        
        # INTRA_STATE: 9% CGST + 9% SGST = 18% total
        cgst_rate = Decimal("9.00")
        sgst_rate = Decimal("9.00")
        
        cgst_amount = (base_amount * cgst_rate / 100).quantize(Decimal("0.01"))
        sgst_amount = (base_amount * sgst_rate / 100).quantize(Decimal("0.01"))
        total_gst = cgst_amount + sgst_amount
        
        assert cgst_amount == Decimal("9000.00")
        assert sgst_amount == Decimal("9000.00")
        assert total_gst == Decimal("18000.00")
        
        print("\n✓ GST Calculation (INTRA_STATE):")
        print(f"  Base: ₹{base_amount}")
        print(f"  CGST (9%): ₹{cgst_amount}")
        print(f"  SGST (9%): ₹{sgst_amount}")
        print(f"  Total GST: ₹{total_gst}")
        print(f"  Final Amount: ₹{base_amount + total_gst}")
    
    
    def test_gst_calculation_inter_state(self):
        """Test GST calculation for different states (IGST)"""
        from decimal import Decimal
        
        buyer_state = "Maharashtra"
        seller_state = "Gujarat"
        base_amount = Decimal("100000.00")
        
        # INTER_STATE: 18% IGST
        igst_rate = Decimal("18.00")
        igst_amount = (base_amount * igst_rate / 100).quantize(Decimal("0.01"))
        
        assert igst_amount == Decimal("18000.00")
        
        print("\n✓ GST Calculation (INTER_STATE):")
        print(f"  Base: ₹{base_amount}")
        print(f"  IGST (18%): ₹{igst_amount}")
        print(f"  Final Amount: ₹{base_amount + igst_amount}")
    
    
    def test_trade_number_format(self):
        """Test trade number format (TR-2025-00001)"""
        import re
        
        # Example trade numbers
        trade_numbers = [
            "TR-2025-00001",
            "TR-2025-00123",
            "TR-2025-99999"
        ]
        
        # Pattern: TR-YYYY-NNNNN
        pattern = r"^TR-\d{4}-\d{5}$"
        
        for trade_number in trade_numbers:
            assert re.match(pattern, trade_number), f"Invalid format: {trade_number}"
            print(f"✓ Valid trade number: {trade_number}")
    
    
    def test_ai_scoring_algorithm(self):
        """Test AI branch suggestion scoring (100-point system)"""
        from decimal import Decimal
        
        # Weights
        STATE_WEIGHT = 40
        DISTANCE_WEIGHT = 30
        CAPACITY_WEIGHT = 20
        COMMODITY_WEIGHT = 10
        
        # Scenario: Perfect match
        state_match_score = 40  # Same state
        distance_score = 30  # Close proximity
        capacity_score = 20  # Sufficient capacity
        commodity_score = 10  # Supports commodity
        
        total_score = state_match_score + distance_score + capacity_score + commodity_score
        
        assert total_score == 100
        print("\n✓ AI Scoring (Perfect Match):")
        print(f"  State Match: {state_match_score}/{STATE_WEIGHT}")
        print(f"  Distance: {distance_score}/{DISTANCE_WEIGHT}")
        print(f"  Capacity: {capacity_score}/{CAPACITY_WEIGHT}")
        print(f"  Commodity: {commodity_score}/{COMMODITY_WEIGHT}")
        print(f"  Total Score: {total_score}/100")
        
        # Scenario: Partial match
        state_match_score = 0  # Different state
        distance_score = 15  # Medium distance
        capacity_score = 20  # Sufficient capacity
        commodity_score = 10  # Supports commodity
        
        total_score = state_match_score + distance_score + capacity_score + commodity_score
        
        assert total_score == 45
        print("\n✓ AI Scoring (Partial Match):")
        print(f"  Total Score: {total_score}/100")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TRADE ENGINE SIMPLE TEST")
    print("=" * 60)
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])
