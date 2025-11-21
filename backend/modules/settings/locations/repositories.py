"""
Location Module Repository

Data access layer for Location model.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.modules.settings.locations.models import Location


class LocationRepository:
    """Repository for Location database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, location: Location) -> Location:
        """Create a new location"""
        self.db.add(location)
        self.db.flush()
        self.db.refresh(location)
        return location
    
    def get_by_id(self, location_id: UUID) -> Optional[Location]:
        """Get location by ID"""
        return self.db.query(Location).filter(Location.id == location_id).first()
    
    def get_by_google_place_id(self, place_id: str) -> Optional[Location]:
        """Get location by Google Place ID (prevents duplicates)"""
        return self.db.query(Location).filter(Location.google_place_id == place_id).first()
    
    def list(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        region: Optional[str] = None,
        is_active: Optional[bool] = True,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Location], int]:
        """
        List locations with optional filters.
        
        Returns:
            Tuple of (locations list, total count)
        """
        query = self.db.query(Location)
        
        # Apply filters
        if city:
            query = query.filter(Location.city.ilike(f"%{city}%"))
        
        if state:
            query = query.filter(Location.state.ilike(f"%{state}%"))
        
        if region:
            query = query.filter(Location.region == region)
        
        if is_active is not None:
            query = query.filter(Location.is_active == is_active)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Location.name.ilike(search_pattern),
                    Location.city.ilike(search_pattern),
                    Location.state.ilike(search_pattern)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        locations = query.order_by(Location.name).offset(offset).limit(limit).all()
        
        return locations, total
    
    def update(self, location: Location) -> Location:
        """Update an existing location"""
        self.db.flush()
        self.db.refresh(location)
        return location
    
    def soft_delete(self, location: Location) -> Location:
        """Soft delete a location (set is_active=False)"""
        location.is_active = False
        return self.update(location)
    
    def count_references(self, location_id: UUID) -> int:
        """
        Count how many other entities reference this location.
        Used to prevent deletion of locations in use.
        
        Checks:
        - organizations.location_id (when implemented)
        - users.business_location_id (when implemented)
        - buyers.location_id (TODO: when buyers module is built)
        - sellers.location_id (TODO: when sellers module is built) 
        - trades.loading_location_id (TODO: when trades module is built)
        - trades.delivery_location_id (TODO: when trades module is built)
        """
        from backend.modules.settings.organization.models import Organization
        from backend.modules.settings.models.settings_models import User
        
        count = 0
        
        # Check organizations table (if location_id column exists)
        # TODO: Uncomment when organizations.location_id is added
        # count += self.db.query(Organization).filter(
        #     Organization.location_id == location_id
        # ).count()
        
        # Check users table (if business_location_id column exists)
        # TODO: Uncomment when users.business_location_id is added
        # count += self.db.query(User).filter(
        #     User.business_location_id == location_id
        # ).count()
        
        # TODO: Add checks for buyers table when module is created
        # from backend.modules.buyers.models import Buyer
        # count += self.db.query(Buyer).filter(
        #     Buyer.location_id == location_id
        # ).count()
        
        # TODO: Add checks for sellers table when module is created
        # from backend.modules.sellers.models import Seller
        # count += self.db.query(Seller).filter(
        #     Seller.location_id == location_id
        # ).count()
        
        # TODO: Add checks for trades table when module is created
        # from backend.modules.trades.models import Trade
        # count += self.db.query(Trade).filter(
        #     or_(
        #         Trade.loading_location_id == location_id,
        #         Trade.delivery_location_id == location_id
        #     )
        # ).count()
        
        return count
