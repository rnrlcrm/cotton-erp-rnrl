"""
Integration tests for Location Master module.
Tests full end-to-end flows with database and API.
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.modules.settings.locations.models import Location


class TestLocationIntegration:
    """Integration tests for Location module."""

    def test_full_location_lifecycle(self, db_session: Session):
        """Test complete location lifecycle: create, read, update, delete."""
        # Create
        location = Location(
            name="Test City",
            google_place_id="test_place_123",
            city="Test City",
            state="Test State",
            state_code="TS",
            region="NORTH",
            is_active=True
        )
        db_session.add(location)
        db_session.commit()
        db_session.refresh(location)
        
        location_id = location.id
        assert location_id is not None
        
        # Read
        found = db_session.query(Location).filter(Location.id == location_id).first()
        assert found is not None
        assert found.name == "Test City"
        assert found.is_active is True
        
        # Update
        found.name = "Updated City"
        db_session.commit()
        db_session.refresh(found)
        assert found.name == "Updated City"
        
        # Soft Delete
        found.is_active = False
        db_session.commit()
        db_session.refresh(found)
        assert found.is_active is False
        
        # Verify still exists but inactive
        exists = db_session.query(Location).filter(Location.id == location_id).first()
        assert exists is not None
        assert exists.is_active is False

    def test_duplicate_google_place_id_prevention(self, db_session: Session):
        """Test that duplicate google_place_id is prevented by unique constraint."""
        place_id = "unique_place_123"
        
        # Create first location
        location1 = Location(
            name="First Location",
            google_place_id=place_id,
            is_active=True
        )
        db_session.add(location1)
        db_session.commit()
        
        # Try to create duplicate
        location2 = Location(
            name="Second Location",
            google_place_id=place_id,
            is_active=True
        )
        db_session.add(location2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
        
        db_session.rollback()

    def test_location_filtering_by_region(self, db_session: Session):
        """Test filtering locations by region."""
        # Create locations in different regions
        locations_data = [
            {"name": "Mumbai", "google_place_id": "place1", "region": "WEST"},
            {"name": "Ahmedabad", "google_place_id": "place2", "region": "WEST"},
            {"name": "Chennai", "google_place_id": "place3", "region": "SOUTH"},
            {"name": "Delhi", "google_place_id": "place4", "region": "NORTH"},
        ]
        
        for data in locations_data:
            location = Location(**data, is_active=True)
            db_session.add(location)
        db_session.commit()
        
        # Filter by WEST region
        west_locations = db_session.query(Location).filter(
            Location.region == "WEST",
            Location.is_active == True
        ).all()
        
        assert len(west_locations) == 2
        assert all(loc.region == "WEST" for loc in west_locations)

    def test_location_search_functionality(self, db_session: Session):
        """Test search across name, city, state."""
        # Create locations
        locations_data = [
            {"name": "Mumbai Central", "google_place_id": "p1", "city": "Mumbai", "state": "Maharashtra"},
            {"name": "Mumbai Airport", "google_place_id": "p2", "city": "Mumbai", "state": "Maharashtra"},
            {"name": "Pune Station", "google_place_id": "p3", "city": "Pune", "state": "Maharashtra"},
        ]
        
        for data in locations_data:
            location = Location(**data, is_active=True)
            db_session.add(location)
        db_session.commit()
        
        # Search for "Mumbai"
        results = db_session.query(Location).filter(
            (Location.name.ilike("%Mumbai%")) |
            (Location.city.ilike("%Mumbai%")) |
            (Location.state.ilike("%Mumbai%"))
        ).all()
        
        assert len(results) == 2
        assert all("Mumbai" in loc.name or loc.city == "Mumbai" for loc in results)

    def test_location_pagination(self, db_session: Session):
        """Test pagination of location list."""
        # Create 25 locations
        for i in range(25):
            location = Location(
                name=f"Location {i:02d}",
                google_place_id=f"place_{i}",
                is_active=True
            )
            db_session.add(location)
        db_session.commit()
        
        # Get first page (10 items)
        page1 = db_session.query(Location).order_by(Location.name).limit(10).offset(0).all()
        assert len(page1) == 10
        
        # Get second page (10 items)
        page2 = db_session.query(Location).order_by(Location.name).limit(10).offset(10).all()
        assert len(page2) == 10
        
        # Get third page (5 items)
        page3 = db_session.query(Location).order_by(Location.name).limit(10).offset(20).all()
        assert len(page3) == 5
        
        # Verify no overlap
        page1_ids = {loc.id for loc in page1}
        page2_ids = {loc.id for loc in page2}
        assert len(page1_ids & page2_ids) == 0

    def test_location_indexes_exist(self, db_session: Session):
        """Test that indexes exist on key columns."""
        from sqlalchemy import inspect
        
        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes('settings_locations')
        
        index_columns = [idx['column_names'] for idx in indexes]
        
        # Check key indexes exist
        assert any('google_place_id' in cols for cols in index_columns)
        assert any('city' in cols for cols in index_columns)
        assert any('state' in cols for cols in index_columns)
        assert any('region' in cols for cols in index_columns)

    def test_location_audit_fields(self, db_session: Session):
        """Test that audit fields are populated correctly."""
        user_id = uuid4()
        
        location = Location(
            name="Audit Test",
            google_place_id="audit_place_123",
            created_by=user_id,
            is_active=True
        )
        db_session.add(location)
        db_session.commit()
        db_session.refresh(location)
        
        # Check created_at is set
        assert location.created_at is not None
        assert location.created_by == user_id
        
        # Update and check updated fields
        location.name = "Updated Name"
        location.updated_by = user_id
        db_session.commit()
        db_session.refresh(location)
        
        assert location.updated_by == user_id

    def test_inactive_locations_filtering(self, db_session: Session):
        """Test filtering active vs inactive locations."""
        # Create active and inactive locations
        active = Location(name="Active", google_place_id="act1", is_active=True)
        inactive = Location(name="Inactive", google_place_id="inact1", is_active=False)
        
        db_session.add(active)
        db_session.add(inactive)
        db_session.commit()
        
        # Query only active
        active_locs = db_session.query(Location).filter(Location.is_active == True).all()
        assert len(active_locs) >= 1
        assert all(loc.is_active for loc in active_locs)
        
        # Query only inactive
        inactive_locs = db_session.query(Location).filter(Location.is_active == False).all()
        assert len(inactive_locs) >= 1
        assert all(not loc.is_active for loc in inactive_locs)


@pytest.mark.skip(reason="Requires Google Maps API key")
class TestLocationGoogleMapsIntegration:
    """Integration tests with Google Maps API (requires API key)."""

    def test_real_google_maps_search(self):
        """Test actual Google Maps API search."""
        # This test requires GOOGLE_MAPS_API_KEY environment variable
        # Skip in CI/CD unless API key is available
        pass

    def test_real_google_maps_fetch_details(self):
        """Test actual Google Maps API place details fetch."""
        # This test requires GOOGLE_MAPS_API_KEY environment variable
        # Skip in CI/CD unless API key is available
        pass
