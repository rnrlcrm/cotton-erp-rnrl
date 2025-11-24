"""
Integration Tests - API Endpoints

Tests:
- All 11 REST endpoints
- Authentication
- Full workflows: create→approve→reserve→release, create→reserve→mark-sold
- Error handling
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.db.async_session import get_db


@pytest.mark.asyncio
class TestAvailabilityAPI:
    """Test Availability REST API endpoints."""
    
    @pytest.fixture
    def mock_get_current_user(self, mock_user):
        """Mock authentication dependency."""
        async def _mock():
            return mock_user
        return _mock
    
    @pytest.fixture
    def client_with_auth(self, async_db, mock_get_current_user):
        """Create test client with mocked auth."""
        from backend.core.auth.dependencies import get_current_user
        
        app = create_app()
        app.dependency_overrides[get_db] = lambda: async_db
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        return TestClient(app)
    
    async def test_create_availability_endpoint(
        self,
        client_with_auth,
        sample_commodity,
        sample_location,
        sample_seller
    ):
        """Test POST /availabilities."""
        payload = {
            "commodity_id": str(sample_commodity.id),
            "location_id": str(sample_location.id),
            "total_quantity": "5000",
            "base_price": "75000",
            "price_matrix": {"29mm": 75000, "30mm": 77000},
            "quality_params": {"staple_length": "29mm"},
            "market_visibility": "PUBLIC",
            "allow_partial_order": True,
            "min_order_quantity": "500",
            "delivery_terms": "EX-WAREHOUSE",
            "delivery_address": "Test Address",
            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
        
        response = client_with_auth.post("/api/v1/availabilities", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["total_quantity"] == "5000"
        assert data["status"] == "DRAFT"
    
    async def test_search_availabilities_endpoint(
        self,
        client_with_auth,
        sample_availability,
        sample_commodity
    ):
        """Test POST /availabilities/search."""
        payload = {
            "commodity_id": str(sample_commodity.id),
            "min_price": "70000",
            "max_price": "80000"
        }
        
        response = client_with_auth.post("/api/v1/availabilities/search", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert isinstance(data["results"], list)
    
    async def test_get_my_availabilities_endpoint(
        self,
        client_with_auth,
        sample_availability
    ):
        """Test GET /availabilities/my."""
        response = client_with_auth.get("/api/v1/availabilities/my")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_availability_by_id_endpoint(
        self,
        client_with_auth,
        sample_availability
    ):
        """Test GET /availabilities/{id}."""
        response = client_with_auth.get(f"/api/v1/availabilities/{sample_availability.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_availability.id)
    
    async def test_get_availability_not_found(self, client_with_auth):
        """Test GET /availabilities/{id} with invalid ID."""
        from uuid import uuid4
        
        response = client_with_auth.get(f"/api/v1/availabilities/{uuid4()}")
        
        assert response.status_code == 404
    
    async def test_update_availability_endpoint(
        self,
        client_with_auth,
        sample_availability
    ):
        """Test PUT /availabilities/{id}."""
        payload = {
            "base_price": "78000"
        }
        
        response = client_with_auth.put(
            f"/api/v1/availabilities/{sample_availability.id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["base_price"] == "78000"
    
    async def test_approve_availability_endpoint(
        self,
        client_with_auth,
        sample_availability,
        mock_user
    ):
        """Test POST /availabilities/{id}/approve."""
        # Mock permission check
        from backend.core.auth.dependencies import require_permissions
        client_with_auth.app.dependency_overrides[require_permissions("availability.approve")] = lambda: None
        
        payload = {
            "notes": "Approved for testing"
        }
        
        response = client_with_auth.post(
            f"/api/v1/availabilities/{sample_availability.id}/approve",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["approval_status"] == "APPROVED"
    
    async def test_reserve_quantity_endpoint(
        self,
        client_with_auth,
        sample_availability,
        mock_buyer_user
    ):
        """Test POST /availabilities/{id}/reserve (internal API)."""
        # Mock permission check
        from backend.core.auth.dependencies import require_permissions
        client_with_auth.app.dependency_overrides[require_permissions("availability.reserve")] = lambda: None
        
        payload = {
            "quantity": "500",
            "buyer_id": str(mock_buyer_user.business_partner_id)
        }
        
        response = client_with_auth.post(
            f"/api/v1/availabilities/{sample_availability.id}/reserve",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["reserved_quantity"] == "500"
    
    async def test_release_quantity_endpoint(
        self,
        client_with_auth,
        sample_availability,
        mock_buyer_user
    ):
        """Test POST /availabilities/{id}/release (internal API)."""
        # First reserve
        from backend.core.auth.dependencies import require_permissions
        client_with_auth.app.dependency_overrides[require_permissions("availability.reserve")] = lambda: None
        client_with_auth.app.dependency_overrides[require_permissions("availability.release")] = lambda: None
        
        reserve_payload = {
            "quantity": "500",
            "buyer_id": str(mock_buyer_user.business_partner_id)
        }
        client_with_auth.post(
            f"/api/v1/availabilities/{sample_availability.id}/reserve",
            json=reserve_payload
        )
        
        # Then release
        release_payload = {
            "quantity": "500"
        }
        
        response = client_with_auth.post(
            f"/api/v1/availabilities/{sample_availability.id}/release",
            json=release_payload
        )
        
        assert response.status_code == 200
    
    async def test_mark_sold_endpoint(
        self,
        client_with_auth,
        sample_availability,
        mock_buyer_user
    ):
        """Test POST /availabilities/{id}/mark-sold (internal API)."""
        # First reserve
        from backend.core.auth.dependencies import require_permissions
        client_with_auth.app.dependency_overrides[require_permissions("availability.reserve")] = lambda: None
        client_with_auth.app.dependency_overrides[require_permissions("availability.mark_sold")] = lambda: None
        
        reserve_payload = {
            "quantity": "500",
            "buyer_id": str(mock_buyer_user.business_partner_id)
        }
        client_with_auth.post(
            f"/api/v1/availabilities/{sample_availability.id}/reserve",
            json=reserve_payload
        )
        
        # Then mark sold
        sold_payload = {
            "quantity": "500",
            "trade_id": "TRADE-001"
        }
        
        response = client_with_auth.post(
            f"/api/v1/availabilities/{sample_availability.id}/mark-sold",
            json=sold_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sold_quantity"] == "500"
    
    async def test_get_negotiation_score_endpoint(
        self,
        client_with_auth,
        sample_availability
    ):
        """Test GET /availabilities/{id}/negotiation-score."""
        response = client_with_auth.get(
            f"/api/v1/availabilities/{sample_availability.id}/negotiation-score"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "negotiation_readiness_score" in data
        assert "factors" in data
        assert "recommendations" in data
    
    async def test_get_similar_commodities_endpoint(
        self,
        client_with_auth,
        sample_availability
    ):
        """Test GET /availabilities/{id}/similar."""
        response = client_with_auth.get(
            f"/api/v1/availabilities/{sample_availability.id}/similar?limit=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_full_workflow_create_approve_reserve_release(
        self,
        client_with_auth,
        sample_commodity,
        sample_location,
        mock_buyer_user
    ):
        """Test complete workflow: create → approve → reserve → release."""
        from backend.core.auth.dependencies import require_permissions
        client_with_auth.app.dependency_overrides[require_permissions("availability.approve")] = lambda: None
        client_with_auth.app.dependency_overrides[require_permissions("availability.reserve")] = lambda: None
        client_with_auth.app.dependency_overrides[require_permissions("availability.release")] = lambda: None
        
        # Step 1: Create
        create_payload = {
            "commodity_id": str(sample_commodity.id),
            "location_id": str(sample_location.id),
            "total_quantity": "1000",
            "base_price": "75000",
            "quality_params": {"staple_length": "29mm"},
            "market_visibility": "PUBLIC",
            "allow_partial_order": True,
            "min_order_quantity": "100",
            "delivery_terms": "EX-WAREHOUSE",
            "delivery_address": "Test",
            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
        create_response = client_with_auth.post("/api/v1/availabilities", json=create_payload)
        assert create_response.status_code == 201
        availability_id = create_response.json()["id"]
        
        # Step 2: Approve
        approve_payload = {"notes": "Approved"}
        approve_response = client_with_auth.post(
            f"/api/v1/availabilities/{availability_id}/approve",
            json=approve_payload
        )
        assert approve_response.status_code == 200
        
        # Step 3: Reserve
        reserve_payload = {
            "quantity": "500",
            "buyer_id": str(mock_buyer_user.business_partner_id)
        }
        reserve_response = client_with_auth.post(
            f"/api/v1/availabilities/{availability_id}/reserve",
            json=reserve_payload
        )
        assert reserve_response.status_code == 200
        
        # Step 4: Release
        release_payload = {"quantity": "500"}
        release_response = client_with_auth.post(
            f"/api/v1/availabilities/{availability_id}/release",
            json=release_payload
        )
        assert release_response.status_code == 200
    
    async def test_full_workflow_create_reserve_mark_sold(
        self,
        client_with_auth,
        sample_commodity,
        sample_location,
        mock_buyer_user
    ):
        """Test complete workflow: create → reserve → mark sold."""
        from backend.core.auth.dependencies import require_permissions
        client_with_auth.app.dependency_overrides[require_permissions("availability.reserve")] = lambda: None
        client_with_auth.app.dependency_overrides[require_permissions("availability.mark_sold")] = lambda: None
        
        # Step 1: Create
        create_payload = {
            "commodity_id": str(sample_commodity.id),
            "location_id": str(sample_location.id),
            "total_quantity": "1000",
            "base_price": "75000",
            "quality_params": {"staple_length": "29mm"},
            "market_visibility": "PUBLIC",
            "allow_partial_order": True,
            "min_order_quantity": "100",
            "delivery_terms": "EX-WAREHOUSE",
            "delivery_address": "Test",
            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
        create_response = client_with_auth.post("/api/v1/availabilities", json=create_payload)
        assert create_response.status_code == 201
        availability_id = create_response.json()["id"]
        
        # Step 2: Reserve
        reserve_payload = {
            "quantity": "1000",
            "buyer_id": str(mock_buyer_user.business_partner_id)
        }
        reserve_response = client_with_auth.post(
            f"/api/v1/availabilities/{availability_id}/reserve",
            json=reserve_payload
        )
        assert reserve_response.status_code == 200
        
        # Step 3: Mark sold
        sold_payload = {
            "quantity": "1000",
            "trade_id": "TRADE-FULL-001"
        }
        sold_response = client_with_auth.post(
            f"/api/v1/availabilities/{availability_id}/mark-sold",
            json=sold_payload
        )
        assert sold_response.status_code == 200
        
        # Verify status is SOLD_OUT
        get_response = client_with_auth.get(f"/api/v1/availabilities/{availability_id}")
        assert get_response.json()["status"] == "SOLD_OUT"
