"""
Location Module Schemas

Pydantic schemas for request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ==================== Google Maps Schemas ====================

class GooglePlaceSuggestion(BaseModel):
    """Single suggestion from Google Places Autocomplete"""
    description: str = Field(..., description="Human-readable place description")
    place_id: str = Field(..., description="Google Place ID")


class LocationSearchRequest(BaseModel):
    """Request schema for searching locations via Google"""
    query: str = Field(..., min_length=2, description="Search query (min 2 characters)")


class LocationSearchResponse(BaseModel):
    """Response schema for location search"""
    suggestions: List[GooglePlaceSuggestion]


class FetchDetailsRequest(BaseModel):
    """Request schema for fetching place details from Google"""
    place_id: str = Field(..., description="Google Place ID")


class GooglePlaceDetails(BaseModel):
    """Full location details from Google Place Details API"""
    place_id: str
    formatted_address: str
    name: Optional[str] = None
    latitude: float
    longitude: float
    address_components: dict
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None


# ==================== Location CRUD Schemas ====================

class LocationBase(BaseModel):
    """Base location fields"""
    name: str = Field(..., min_length=1, max_length=255)


class LocationCreate(LocationBase):
    """Schema for creating a location"""
    google_place_id: str = Field(..., description="Google Place ID (required)")


class LocationUpdate(BaseModel):
    """Schema for updating a location (only name and status allowed)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class LocationResponse(BaseModel):
    """Schema for location response"""
    id: UUID
    name: str
    google_place_id: str
    
    # Address
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    
    # Location details
    pincode: Optional[str]
    city: Optional[str]
    district: Optional[str]
    state: Optional[str]
    state_code: Optional[str]
    country: Optional[str]
    region: Optional[str]
    
    # Status
    is_active: bool
    
    # Audit
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[UUID]
    updated_by: Optional[UUID]
    
    model_config = {"from_attributes": True}


class LocationListResponse(BaseModel):
    """Schema for list of locations"""
    total: int
    locations: List[LocationResponse]


# ==================== Filter Schemas ====================

class LocationFilterParams(BaseModel):
    """Query parameters for filtering locations"""
    city: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    is_active: Optional[bool] = True
    search: Optional[str] = None  # Search in name, city, state
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)
