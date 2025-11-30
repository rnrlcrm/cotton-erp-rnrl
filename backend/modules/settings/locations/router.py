"""
Location Module Router

API endpoints for location management.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.capabilities.decorators import RequireCapability
from backend.core.auth.capabilities.definitions import Capabilities
from backend.core.events.emitter import EventEmitter
from backend.db.session import get_db
from backend.modules.settings.locations.schemas import (
    FetchDetailsRequest,
    GooglePlaceDetails,
    GooglePlaceSuggestion,
    LocationCreate,
    LocationFilterParams,
    LocationListResponse,
    LocationResponse,
    LocationSearchRequest,
    LocationUpdate,
)
from backend.modules.settings.locations.services import LocationService

router = APIRouter(prefix="/locations", tags=["locations"])


async def get_event_emitter(db: AsyncSession = Depends(get_db)) -> EventEmitter:
    """Get event emitter instance"""
    return EventEmitter(db)


async def get_location_service(
    db: AsyncSession = Depends(get_db),
    event_emitter: EventEmitter = Depends(get_event_emitter)
) -> LocationService:
    """Dependency to get LocationService instance"""
    return LocationService(db, event_emitter)


# ==================== Google Maps Integration Endpoints ====================

@router.post("/search-google", response_model=List[GooglePlaceSuggestion])
def search_google_places(
    request: LocationSearchRequest,
    service: LocationService = Depends(get_location_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.LOCATION_CREATE))
) -> List[GooglePlaceSuggestion]:
    """
    Search for places using Google Maps Autocomplete API. Requires LOCATION_CREATE capability. Supports idempotency.
    
    - **query**: Search string (min 2 characters)
    
    Returns list of place suggestions with descriptions and place_ids.
    """
    return service.search_google_places(request.query)


@router.post("/fetch-details", response_model=GooglePlaceDetails)
def fetch_place_details(
    request: FetchDetailsRequest,
    service: LocationService = Depends(get_location_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.LOCATION_CREATE))
) -> GooglePlaceDetails:
    """
    Fetch full location details from Google Place Details API. Requires LOCATION_CREATE capability. Supports idempotency.
    
    - **place_id**: Google Place ID from autocomplete
    
    Returns complete location information including lat/long, city, state, etc.
    """
    return service.fetch_google_place_details(request.place_id)


# ==================== Location CRUD Endpoints ====================

@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    data: LocationCreate,
    service: LocationService = Depends(get_location_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.LOCATION_CREATE))
    # current_user_id: UUID = Depends(get_current_user)  # TODO: Uncomment when auth is ready
) -> LocationResponse:
    """
    Create a new location or return existing if google_place_id already exists. Requires LOCATION_CREATE capability. Supports idempotency.
    
    This prevents duplicate locations in the system.
    
    - **name**: Location name
    - **google_place_id**: Google Place ID (from fetch-details endpoint)
    
    Returns the created or existing location.
    """
    # TODO: Replace with actual current_user_id from auth
    current_user_id = UUID("00000000-0000-0000-0000-000000000000")
    
    return service.create_or_get_location(data, current_user_id)


@router.get("/", response_model=LocationListResponse)
def list_locations(
    city: str = Query(None, description="Filter by city"),
    state: str = Query(None, description="Filter by state"),
    region: str = Query(None, description="Filter by region (WEST, SOUTH, NORTH, etc.)"),
    is_active: bool = Query(True, description="Filter by active status"),
    search: str = Query(None, description="Search in name, city, state"),
    limit: int = Query(100, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    service: LocationService = Depends(get_location_service)
) -> LocationListResponse:
    """
    List all locations with optional filters.
    
    Supports filtering by:
    - city
    - state
    - region
    - is_active
    - search (searches name, city, state)
    
    Returns paginated list of locations.
    """
    locations, total = service.list_locations(
        city=city,
        state=state,
        region=region,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset
    )
    
    return LocationListResponse(total=total, locations=locations)


@router.get("/{location_id}", response_model=LocationResponse)
def get_location(
    location_id: UUID,
    service: LocationService = Depends(get_location_service)
) -> LocationResponse:
    """
    Get a single location by ID.
    
    Returns full location details.
    """
    return service.get_location(location_id)


@router.put("/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: UUID,
    data: LocationUpdate,
    service: LocationService = Depends(get_location_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.LOCATION_UPDATE))
    # current_user_id: UUID = Depends(get_current_user)  # TODO: Uncomment when auth is ready
) -> LocationResponse:
    """
    Update a location (only name and is_active can be updated). Requires LOCATION_UPDATE capability. Supports idempotency.
    
    Google Maps data (address, lat/long, city, state, etc.) cannot be manually edited.
    
    - **name**: New name (optional)
    - **is_active**: Active status (optional)
    
    Returns updated location.
    """
    # TODO: Replace with actual current_user_id from auth
    current_user_id = UUID("00000000-0000-0000-0000-000000000000")
    
    return service.update_location(location_id, data, current_user_id)


@router.delete("/{location_id}")
def delete_location(
    location_id: UUID,
    service: LocationService = Depends(get_location_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.LOCATION_DELETE))
    # current_user_id: UUID = Depends(get_current_user)  # TODO: Uncomment when auth is ready
) -> dict:
    """
    Soft delete a location (sets is_active=False). Requires LOCATION_DELETE capability. Supports idempotency.
    
    Cannot delete if location is referenced by other entities
    (organizations, trades, buyers, etc.)
    
    Returns success message.
    """
    # TODO: Replace with actual current_user_id from auth
    current_user_id = UUID("00000000-0000-0000-0000-000000000000")
    
    return service.delete_location(location_id, current_user_id)
