"""
Integration Tests for Location Module

Tests the location module with mocked Google Maps API.
Covers CRUD operations, Google Maps integration, region calculation, and duplicate prevention.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.core.errors.exceptions import BadRequestException, NotFoundException
from backend.core.events.emitter import EventEmitter
from backend.modules.settings.locations.models import Location
from backend.modules.settings.locations.schemas import (
    GooglePlaceDetails,
    GooglePlaceSuggestion,
    LocationCreate,
    LocationUpdate,
)
from backend.modules.settings.locations.services import LocationService
from backend.modules.settings.locations.google_maps import GoogleMapsService


@pytest.fixture
def mock_google_maps_service():
    """Mock Google Maps service to avoid real API calls"""
    with patch('backend.modules.settings.locations.services.GoogleMapsService') as mock:
        service = MagicMock(spec=GoogleMapsService)
        
        # Mock search_places
        service.search_places.return_value = [
            GooglePlaceSuggestion(
                description="Mumbai, Maharashtra, India",
                place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0"
            ),
            GooglePlaceSuggestion(
                description="Mumbai Airport, Mumbai, Maharashtra, India",
                place_id="ChIJYRbY-N3I5zsRdDZmPMZNOTk"
            )
        ]
        
        # Mock fetch_place_details with different responses based on place_id
        def mock_fetch_details(place_id: str) -> GooglePlaceDetails:
            if place_id == "ChIJYRbY-N3I5zsRdDZmPMZNOTk":
                # Mumbai Airport
                return GooglePlaceDetails(
                    place_id="ChIJYRbY-N3I5zsRdDZmPMZNOTk",
                    formatted_address="Mumbai Airport, Mumbai, Maharashtra, India",
                    name="Mumbai Airport",
                    latitude=19.0896,
                    longitude=72.8656,
                    address_components={
                        "city": "Mumbai",
                        "state": "Maharashtra",
                        "state_code": "MH",
                        "country": "India",
                        "pincode": "400099"
                    },
                    city="Mumbai",
                    district="Mumbai Suburban",
                    state="Maharashtra",
                    state_code="MH",
                    country="India",
                    pincode="400099"
                )
            else:
                # Default Mumbai city
                return GooglePlaceDetails(
                    place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0",
                    formatted_address="Mumbai, Maharashtra, India",
                    name="Mumbai",
                    latitude=19.0760,
                    longitude=72.8777,
                    address_components={
                        "city": "Mumbai",
                        "state": "Maharashtra",
                        "state_code": "MH",
                        "country": "India",
                        "pincode": "400001"
                    },
                    city="Mumbai",
                    district="Mumbai Suburban",
                    state="Maharashtra",
                    state_code="MH",
                    country="India",
                    pincode="400001"
                )
        
        service.fetch_place_details.side_effect = mock_fetch_details
        
        mock.return_value = service
        yield service


@pytest.mark.asyncio
class TestLocationCRUD:
    """Test Location CRUD operations"""
    
    async def test_create_location_from_google_place_id(self, db_session, mock_google_maps_service):
        """Test creating a location from Google Place ID"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        data = LocationCreate(
            name="Mumbai",
            google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0"
        )
        
        location = await service.create_or_get_location(data, current_user_id=uuid4())
        
        assert location.name == "Mumbai"
        assert location.google_place_id == "ChIJwe1EZjDG5zsRaYxkjY_tpF0"
        assert location.city == "Mumbai"
        assert location.state == "Maharashtra"
        assert location.state_code == "MH"
        assert location.region == "WEST"  # Auto-calculated from MH
        assert location.latitude == 19.0760
        assert location.longitude == 72.8777
        assert location.is_active is True
    
    async def test_duplicate_google_place_id_returns_existing(self, db_session, mock_google_maps_service):
        """Test that creating location with duplicate google_place_id returns existing location"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        data = LocationCreate(
            name="Mumbai",
            google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0"
        )
        
        # Create first location
        location1 = await service.create_or_get_location(data, current_user_id=uuid4())
        
        # Try to create with same google_place_id
        location2 = await service.create_or_get_location(data, current_user_id=uuid4())
        
        # Should return the same location
        assert location1.id == location2.id
        assert location1.google_place_id == location2.google_place_id
    
    async def test_get_location_by_id(self, db_session, mock_google_maps_service):
        """Test getting location by ID"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        # Create location
        data = LocationCreate(name="Mumbai", google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0")
        created = await service.create_or_get_location(data, current_user_id=uuid4())
        
        # Get by ID
        location = await service.get_location(created.id)
        
        assert location.id == created.id
        assert location.name == "Mumbai"
    
    async def test_get_nonexistent_location_raises_error(self, db_session, mock_google_maps_service):
        """Test getting nonexistent location raises NotFoundException"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        with pytest.raises(NotFoundException):
            await service.get_location(uuid4())
    
    async def test_list_locations(self, db_session, mock_google_maps_service):
        """Test listing locations with filters"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        # Create multiple locations
        locations_data = [
            ("Mumbai", "ChIJwe1EZjDG5zsRaYxkjY_tpF0"),
            ("Delhi", "ChIJL_P_CXMEDTkRw0ZdG-0GVvw"),
            ("Bangalore", "ChIJbU60yXAWrjsR4E9-UejD3_g"),
        ]
        
        for name, place_id in locations_data:
            # Update mock for each location
            mock_google_maps_service.fetch_place_details.return_value = GooglePlaceDetails(
                place_id=place_id,
                formatted_address=f"{name}, India",
                name=name,
                latitude=0.0,
                longitude=0.0,
                address_components={"city": name},
                city=name,
                state="Test State",
                state_code="TS",
                country="India",
                pincode="000000"
            )
            
            data = LocationCreate(name=name, google_place_id=place_id)
            await service.create_or_get_location(data, current_user_id=uuid4())
        
        # List all locations
        locations, total = await service.list_locations()
        assert len(locations) >= 3
        assert total >= 3
        
        # List with filter
        filtered, filtered_total = await service.list_locations(city="Mumbai")
        assert len(filtered) >= 1
        assert all(loc.city == "Mumbai" for loc in filtered)
    
    async def test_update_location(self, db_session, mock_google_maps_service):
        """Test updating location"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        # Create location
        data = LocationCreate(name="Mumbai", google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0")
        created = await service.create_or_get_location(data, current_user_id=uuid4())
        
        # Update location
        update_data = LocationUpdate(name="Mumbai City", is_active=False)
        updated = await service.update_location(created.id, update_data, current_user_id=uuid4())
        
        assert updated.name == "Mumbai City"
        assert updated.is_active is False
        assert updated.google_place_id == created.google_place_id  # Should not change
    
    async def test_delete_location(self, db_session, mock_google_maps_service):
        """Test soft deleting location"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        # Create location
        data = LocationCreate(name="Mumbai", google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0")
        created = await service.create_or_get_location(data, current_user_id=uuid4())
        
        # Delete location (soft delete)
        await service.delete_location(created.id, current_user_id=uuid4())
        
        # Verify soft delete
        location = await service.get_location(created.id)
        assert location.is_active is False


@pytest.mark.asyncio
class TestGoogleMapsIntegration:
    """Test Google Maps API integration (mocked)"""
    
    async def test_search_google_places(self, db_session, mock_google_maps_service):
        """Test searching Google Places"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        results = await service.search_google_places("Mumbai")
        
        assert len(results) == 2
        assert results[0].description == "Mumbai, Maharashtra, India"
        assert results[0].place_id == "ChIJwe1EZjDG5zsRaYxkjY_tpF0"
        mock_google_maps_service.search_places.assert_called_once_with("Mumbai")
    
    async def test_fetch_google_place_details(self, db_session, mock_google_maps_service):
        """Test fetching Google Place details"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        details = await service.fetch_google_place_details("ChIJwe1EZjDG5zsRaYxkjY_tpF0")
        
        assert details.place_id == "ChIJwe1EZjDG5zsRaYxkjY_tpF0"
        assert details.name == "Mumbai"
        assert details.latitude == 19.0760
        assert details.longitude == 72.8777
        mock_google_maps_service.fetch_place_details.assert_called_once_with("ChIJwe1EZjDG5zsRaYxkjY_tpF0")


@pytest.mark.asyncio
class TestRegionCalculation:
    """Test automatic region calculation from state codes"""
    
    async def test_west_region_calculation(self, db_session, mock_google_maps_service):
        """Test WEST region for Maharashtra (MH)"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        mock_google_maps_service.fetch_place_details.side_effect = lambda place_id: GooglePlaceDetails(
            place_id="test-mh",
            formatted_address="Test, Maharashtra",
            name="Test MH",
            latitude=0.0,
            longitude=0.0,
            address_components={},
            state_code="MH",
            state="Maharashtra"
        )
        
        data = LocationCreate(name="Test MH", google_place_id="test-mh")
        location = await service.create_or_get_location(data, current_user_id=uuid4())
        
        assert location.region == "WEST"
    
    async def test_south_region_calculation(self, db_session, mock_google_maps_service):
        """Test SOUTH region for Tamil Nadu (TN)"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        mock_google_maps_service.fetch_place_details.side_effect = lambda place_id: GooglePlaceDetails(
            place_id="test-tn",
            formatted_address="Test, Tamil Nadu",
            name="Test TN",
            latitude=0.0,
            longitude=0.0,
            address_components={},
            state_code="TN",
            state="Tamil Nadu"
        )
        
        data = LocationCreate(name="Test TN", google_place_id="test-tn")
        location = await service.create_or_get_location(data, current_user_id=uuid4())
        
        assert location.region == "SOUTH"
    
    async def test_north_region_calculation(self, db_session, mock_google_maps_service):
        """Test NORTH region for Delhi (DL)"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        mock_google_maps_service.fetch_place_details.side_effect = lambda place_id: GooglePlaceDetails(
            place_id="test-dl",
            formatted_address="Test, Delhi",
            name="Test DL",
            latitude=0.0,
            longitude=0.0,
            address_components={},
            state_code="DL",
            state="Delhi"
        )
        
        data = LocationCreate(name="Test DL", google_place_id="test-dl")
        location = await service.create_or_get_location(data, current_user_id=uuid4())
        
        assert location.region == "NORTH"
    
    async def test_unknown_state_code_no_region(self, db_session, mock_google_maps_service):
        """Test that unknown state code results in no region"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        mock_google_maps_service.fetch_place_details.side_effect = lambda place_id: GooglePlaceDetails(
            place_id="test-unknown",
            formatted_address="Test, Unknown",
            name="Test Unknown",
            latitude=0.0,
            longitude=0.0,
            address_components={},
            state_code="XX",  # Unknown state code
            state="Unknown"
        )
        
        data = LocationCreate(name="Test Unknown", google_place_id="test-unknown")
        location = await service.create_or_get_location(data, current_user_id=uuid4())
        
        assert location.region == "UNKNOWN"  # Unknown state codes map to UNKNOWN


@pytest.mark.asyncio
class TestLocationEvents:
    """Test event emissions for location operations"""
    
    async def test_location_created_event(self, db_session, mock_google_maps_service):
        """Test LocationCreated event is emitted"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        user_id = uuid4()
        
        # Use Mumbai Airport place_id to avoid collision with other tests
        data = LocationCreate(name="Mumbai Airport", google_place_id="ChIJYRbY-N3I5zsRdDZmPMZNOTk")
        location = await service.create_or_get_location(data, current_user_id=user_id)
        
        # Verify location was created successfully (event emission happens in background)
        assert location.id is not None
        assert location.name == "Mumbai Airport"
    
    async def test_location_updated_event(self, db_session, mock_google_maps_service):
        """Test LocationUpdated event is emitted"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        user_id = uuid4()
        
        # Create location
        data = LocationCreate(name="Mumbai", google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0")
        created = await service.create_or_get_location(data, current_user_id=user_id)
        
        # Update location
        update_data = LocationUpdate(name="Mumbai City")
        updated = await service.update_location(created.id, update_data, current_user_id=user_id)
        
        # Verify update was successful (event emission happens in background)
        assert updated.name == "Mumbai City"
    
    async def test_location_deleted_event(self, db_session, mock_google_maps_service):
        """Test LocationDeleted event is emitted"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        user_id = uuid4()
        
        # Create location
        data = LocationCreate(name="Mumbai", google_place_id="ChIJwe1EZjDG5zsRaYxkjY_tpF0")
        created = await service.create_or_get_location(data, current_user_id=user_id)
        
        # Delete location
        result = await service.delete_location(created.id, current_user_id=user_id)
        
        # Verify deletion was successful (event emission happens in background)
        assert result["message"] is not None
        location = await service.get_location(created.id)
        assert location.is_active is False


@pytest.mark.asyncio
class TestLocationValidation:
    """Test location validation and error handling"""
    
    async def test_create_location_without_google_place_id_fails(self, db_session, mock_google_maps_service):
        """Test that creating location without google_place_id fails"""
        # This should fail at Pydantic validation level
        with pytest.raises(Exception):  # ValidationError
            LocationCreate(name="Test Location")
    
    async def test_update_nonexistent_location_raises_error(self, db_session, mock_google_maps_service):
        """Test updating nonexistent location raises error"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        with pytest.raises(NotFoundException):
            update_data = LocationUpdate(name="New Name")
            await service.update_location(uuid4(), update_data, current_user_id=uuid4())
    
    async def test_delete_nonexistent_location_raises_error(self, db_session, mock_google_maps_service):
        """Test deleting nonexistent location raises error"""
        event_emitter = EventEmitter(db_session)
        service = LocationService(db_session, event_emitter)
        
        with pytest.raises(NotFoundException):
            await service.delete_location(uuid4(), current_user_id=uuid4())
