"""
Unit tests for Location Master module.
Tests models, repositories, services, and API endpoints.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.modules.settings.locations.models import Location
from backend.modules.settings.locations.repositories import LocationRepository
from backend.modules.settings.locations.services import LocationService, map_state_to_region
from backend.modules.settings.locations.schemas import (
    GooglePlaceSuggestion,
    GooglePlaceDetails,
    LocationCreate,
    LocationUpdate,
    LocationResponse,
)
from backend.modules.settings.locations.google_maps import GoogleMapsService
from backend.core.errors.exceptions import BadRequestException, NotFoundException


# ============================================================================
# MODEL TESTS
# ============================================================================

class TestLocationModel:
    """Test Location model."""

    def test_create_location(self, db_session: Session):
        """Test creating a location."""
        location = Location(
            name="Mumbai, Maharashtra",
            google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0",
            address="Mumbai, Maharashtra, India",
            latitude=19.0760,
            longitude=72.8777,
            city="Mumbai",
            state="Maharashtra",
            state_code="MH",
            country="India",
            region="WEST",
            pincode="400001",
            is_active=True
        )
        db_session.add(location)
        db_session.commit()
        db_session.refresh(location)

        assert location.id is not None
        assert location.name == "Mumbai, Maharashtra"
        assert location.google_place_id == "ChIJwe1EZjDG5zsRaYxkjY_tpF0"
        assert location.city == "Mumbai"
        assert location.state == "Maharashtra"
        assert location.state_code == "MH"
        assert location.region == "WEST"
        assert location.is_active is True

    def test_unique_google_place_id(self, db_session: Session):
        """Test that google_place_id is unique."""
        location1 = Location(
            name="Mumbai",
            google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0",
            is_active=True
        )
        db_session.add(location1)
        db_session.commit()

        # Try to create another location with same google_place_id
        location2 = Location(
            name="Mumbai Duplicate",
            google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0",
            is_active=True
        )
        db_session.add(location2)
        
        with pytest.raises(Exception):  # Will raise IntegrityError
            db_session.commit()


# ============================================================================
# REPOSITORY TESTS
# ============================================================================

class TestLocationRepository:
    """Test LocationRepository."""

    def test_create_location(self, db_session: Session):
        """Test creating a location via repository."""
        repo = LocationRepository(db_session)
        
        location = Location(
            name="Delhi",
            google_place_id="ChIJL_P_CXMEDTkRw0ZdG-0GVvw",
            city="New Delhi",
            state="Delhi",
            state_code="DL",
            region="NORTH",
            is_active=True
        )
        
        created = repo.create(location)
        
        assert created.id is not None
        assert created.name == "Delhi"
        assert created.city == "New Delhi"

    def test_get_by_id(self, db_session: Session):
        """Test getting location by ID."""
        repo = LocationRepository(db_session)
        
        location = Location(
            name="Bangalore",
            google_place_id="ChIJbU60yXAWrjsR4E9-UejD3_g",
            city="Bangalore",
            state="Karnataka",
            state_code="KA",
            region="SOUTH",
            is_active=True
        )
        created = repo.create(location)
        db_session.commit()
        
        found = repo.get_by_id(created.id)
        
        assert found is not None
        assert found.id == created.id
        assert found.name == "Bangalore"

    def test_get_by_google_place_id(self, db_session: Session):
        """Test getting location by Google Place ID."""
        repo = LocationRepository(db_session)
        
        place_id = "ChIJwe1EZjDG5zsRaYxkjY_tpF0"
        location = Location(
            name="Mumbai",
            google_place_id=place_id,
            is_active=True
        )
        repo.create(location)
        db_session.commit()
        
        found = repo.get_by_google_place_id(place_id)
        
        assert found is not None
        assert found.google_place_id == place_id
        assert found.name == "Mumbai"

    def test_list_locations(self, db_session: Session):
        """Test listing locations with filters."""
        repo = LocationRepository(db_session)
        
        # Create multiple locations
        locations_data = [
            {"name": "Mumbai", "google_place_id": "place1", "city": "Mumbai", "state": "Maharashtra", "region": "WEST"},
            {"name": "Pune", "google_place_id": "place2", "city": "Pune", "state": "Maharashtra", "region": "WEST"},
            {"name": "Bangalore", "google_place_id": "place3", "city": "Bangalore", "state": "Karnataka", "region": "SOUTH"},
        ]
        
        for data in locations_data:
            location = Location(**data, is_active=True)
            repo.create(location)
        db_session.commit()
        
        # Test list all
        all_locations, total = repo.list()
        assert total == 3
        assert len(all_locations) == 3
        
        # Test filter by state
        mh_locations, mh_total = repo.list(state="Maharashtra")
        assert mh_total == 2
        
        # Test filter by region
        south_locations, south_total = repo.list(region="SOUTH")
        assert south_total == 1
        
        # Test search
        search_locations, search_total = repo.list(search="Mum")
        assert search_total == 1
        assert search_locations[0].city == "Mumbai"

    def test_update_location(self, db_session: Session):
        """Test updating a location."""
        repo = LocationRepository(db_session)
        
        location = Location(
            name="Old Name",
            google_place_id="place123",
            is_active=True
        )
        created = repo.create(location)
        db_session.commit()
        
        # Update
        created.name = "New Name"
        updated = repo.update(created)
        db_session.commit()
        
        # Verify
        found = repo.get_by_id(created.id)
        assert found.name == "New Name"

    def test_soft_delete(self, db_session: Session):
        """Test soft deleting a location."""
        repo = LocationRepository(db_session)
        
        location = Location(
            name="To Delete",
            google_place_id="place456",
            is_active=True
        )
        created = repo.create(location)
        db_session.commit()
        
        # Soft delete
        repo.soft_delete(created)
        db_session.commit()
        
        # Verify is_active is False
        found = repo.get_by_id(created.id)
        assert found.is_active is False


# ============================================================================
# SERVICE TESTS
# ============================================================================

class TestRegionMapping:
    """Test region mapping functionality."""

    def test_map_maharashtra_to_west(self):
        """Test Maharashtra maps to WEST."""
        assert map_state_to_region("MH") == "WEST"

    def test_map_tamil_nadu_to_south(self):
        """Test Tamil Nadu maps to SOUTH."""
        assert map_state_to_region("TN") == "SOUTH"

    def test_map_delhi_to_north(self):
        """Test Delhi maps to NORTH."""
        assert map_state_to_region("DL") == "NORTH"

    def test_map_madhya_pradesh_to_central(self):
        """Test Madhya Pradesh maps to CENTRAL."""
        assert map_state_to_region("MP") == "CENTRAL"

    def test_map_west_bengal_to_east(self):
        """Test West Bengal maps to EAST."""
        assert map_state_to_region("WB") == "EAST"

    def test_map_assam_to_northeast(self):
        """Test Assam maps to NORTHEAST."""
        assert map_state_to_region("AS") == "NORTHEAST"

    def test_map_unknown_state(self):
        """Test unknown state code returns UNKNOWN."""
        assert map_state_to_region("XX") == "UNKNOWN"

    def test_map_none_returns_unknown(self):
        """Test None state code returns UNKNOWN."""
        assert map_state_to_region(None) == "UNKNOWN"


class TestGoogleMapsService:
    """Test GoogleMapsService."""

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    @patch('httpx.Client')
    def test_search_places_success(self, mock_client):
        """Test successful place search."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "predictions": [
                {
                    "description": "Mumbai, Maharashtra, India",
                    "place_id": "ChIJwe1EZjDG5zsRaYxkjY_tpF0"
                }
            ]
        }
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        service = GoogleMapsService()
        results = service.search_places("Mumbai")
        
        assert len(results) == 1
        assert results[0].description == "Mumbai, Maharashtra, India"
        assert results[0].place_id == "ChIJwe1EZjDG5zsRaYxkjY_tpF0"

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    @patch('httpx.Client')
    def test_search_places_no_results(self, mock_client):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ZERO_RESULTS"}
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        service = GoogleMapsService()
        results = service.search_places("XYZ123456")
        
        assert len(results) == 0

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    @patch('httpx.Client')
    def test_fetch_place_details_success(self, mock_client):
        """Test successful place details fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "result": {
                "place_id": "ChIJwe1EZjDG5zsRaYxkjY_tpF0",
                "formatted_address": "Mumbai, Maharashtra, India",
                "name": "Mumbai",
                "geometry": {
                    "location": {"lat": 19.0760, "lng": 72.8777}
                },
                "address_components": [
                    {"long_name": "Mumbai", "short_name": "Mumbai", "types": ["locality"]},
                    {"long_name": "Maharashtra", "short_name": "MH", "types": ["administrative_area_level_1"]},
                    {"long_name": "India", "short_name": "IN", "types": ["country"]},
                    {"long_name": "400001", "short_name": "400001", "types": ["postal_code"]},
                ]
            }
        }
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        service = GoogleMapsService()
        details = service.fetch_place_details("ChIJwe1EZjDG5zsRaYxkjY_tpF0")
        
        assert details is not None
        assert details.place_id == "ChIJwe1EZjDG5zsRaYxkjY_tpF0"
        assert details.city == "Mumbai"
        assert details.state == "Maharashtra"
        assert details.state_code == "MH"
        assert details.latitude == 19.0760
        assert details.longitude == 72.8777


class TestLocationService:
    """Test LocationService."""

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_search_google_places(self, db_session: Session):
        """Test searching Google places."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        
        with patch.object(service.google_maps, 'search_places') as mock_search:
            mock_search.return_value = [
                GooglePlaceSuggestion(
                    description="Mumbai, Maharashtra, India",
                    place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0"
                )
            ]
            
            results = service.search_google_places("Mumbai")
            
            assert len(results) == 1
            assert results[0].description == "Mumbai, Maharashtra, India"

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_search_with_short_query(self, db_session: Session):
        """Test search with query less than 2 characters."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        
        with pytest.raises(BadRequestException):
            service.search_google_places("M")

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_fetch_google_place_details(self, db_session: Session):
        """Test fetching place details."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        
        mock_details = GooglePlaceDetails(
            place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0",
            formatted_address="Mumbai, Maharashtra, India",
            name="Mumbai",
            latitude=19.0760,
            longitude=72.8777,
            address_components={},
            city="Mumbai",
            state="Maharashtra",
            state_code="MH",
            country="India",
            pincode="400001"
        )
        
        with patch.object(service.google_maps, 'fetch_place_details') as mock_fetch:
            mock_fetch.return_value = mock_details
            
            details = service.fetch_google_place_details("ChIJwe1EZjDG5zsRaYxkjY_tpF0")
            
            assert details.city == "Mumbai"
            assert details.state_code == "MH"

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_create_location_success(self, db_session: Session):
        """Test creating a new location."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        user_id = uuid4()
        
        mock_details = GooglePlaceDetails(
            place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0",
            formatted_address="Mumbai, Maharashtra, India",
            name="Mumbai",
            latitude=19.0760,
            longitude=72.8777,
            address_components={},
            city="Mumbai",
            state="Maharashtra",
            state_code="MH",
            country="India",
            pincode="400001"
        )
        
        with patch.object(service.google_maps, 'fetch_place_details') as mock_fetch:
            mock_fetch.return_value = mock_details
            
            data = LocationCreate(
                name="Mumbai, Maharashtra",
                google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0"
            )
            
            location = service.create_or_get_location(data, user_id)
            
            assert location.name == "Mumbai, Maharashtra"
            assert location.city == "Mumbai"
            assert location.state == "Maharashtra"
            assert location.region == "WEST"  # Auto-assigned

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_create_location_returns_existing(self, db_session: Session):
        """Test that creating duplicate returns existing location."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        user_id = uuid4()
        
        # Create first location
        place_id = "ChIJwe1EZjDG5zsRaYxkjY_tpF0"
        location = Location(
            name="Existing",
            google_place_id=place_id,
            is_active=True
        )
        service.repository.create(location)
        db_session.commit()
        
        # Try to create again
        data = LocationCreate(name="Duplicate", google_place_id=place_id)
        result = service.create_or_get_location(data, user_id)
        
        # Should return existing
        assert result.name == "Existing"
        assert result.google_place_id == place_id

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_get_location(self, db_session: Session):
        """Test getting a location by ID."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        
        location = Location(
            name="Test Location",
            google_place_id="place123",
            is_active=True
        )
        created = service.repository.create(location)
        db_session.commit()
        
        result = service.get_location(created.id)
        
        assert result.id == created.id
        assert result.name == "Test Location"

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_get_location_not_found(self, db_session: Session):
        """Test getting non-existent location raises NotFoundException."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        
        with pytest.raises(NotFoundException):
            service.get_location(uuid4())

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_list_locations(self, db_session: Session):
        """Test listing locations."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        
        # Create test locations
        for i in range(5):
            location = Location(
                name=f"Location {i}",
                google_place_id=f"place{i}",
                is_active=True
            )
            service.repository.create(location)
        db_session.commit()
        
        locations, total = service.list_locations(limit=10)
        
        assert total == 5
        assert len(locations) == 5

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_update_location(self, db_session: Session):
        """Test updating a location."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        user_id = uuid4()
        
        location = Location(
            name="Old Name",
            google_place_id="place123",
            is_active=True
        )
        created = service.repository.create(location)
        db_session.commit()
        
        # Update
        update_data = LocationUpdate(name="New Name", is_active=False)
        updated = service.update_location(created.id, update_data, user_id)
        
        assert updated.name == "New Name"
        assert updated.is_active is False

    @patch.dict('os.environ', {'GOOGLE_MAPS_API_KEY': 'test_api_key'})
    def test_delete_location(self, db_session: Session):
        """Test deleting a location."""
        mock_event_emitter = Mock()
        service = LocationService(db_session, mock_event_emitter)
        user_id = uuid4()
        
        location = Location(
            name="To Delete",
            google_place_id="place123",
            is_active=True
        )
        created = service.repository.create(location)
        db_session.commit()
        
        # Delete
        result = service.delete_location(created.id, user_id)
        
        assert "deleted successfully" in result["message"]
        
        # Verify soft delete
        deleted = service.repository.get_by_id(created.id)
        assert deleted.is_active is False


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================

@pytest.mark.skip(reason="Requires full app integration - run as integration test")
class TestLocationAPI:
    """Test Location API endpoints."""

    def test_search_google_endpoint(self, client: TestClient):
        """Test POST /locations/search-google endpoint."""
        response = client.post(
            "/api/v1/settings/locations/search-google",
            json={"query": "Mumbai"}
        )
        assert response.status_code == 200

    def test_create_location_endpoint(self, client: TestClient):
        """Test POST /locations/ endpoint."""
        response = client.post(
            "/api/v1/settings/locations/",
            json={
                "name": "Mumbai, Maharashtra",
                "google_place_id": "ChIJwe1EZjDG5zsRaYxkjY_tpF0"
            }
        )
        assert response.status_code == 201

    def test_list_locations_endpoint(self, client: TestClient):
        """Test GET /locations/ endpoint."""
        response = client.get("/api/v1/settings/locations/")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "locations" in data
